/**
 * Association Populator Service
 * Populates fato_associacoes_contextuais by crossing noticias with emendas
 * via shared taxonomy (dim_taxonomia_tematica).
 *
 * Flow:
 *   1. Load taxonomy mappings (tema → slug, funcao → slug)
 *   2. Fetch recent noticias with tema_principal
 *   3. For each noticia, find emendas with matching taxonomy slug
 *   4. Create associations in fato_associacoes_contextuais
 *   5. Optionally run regex-based signal detection
 */

import { createClient } from '@supabase/supabase-js';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';

const BATCH_SIZE = 50;

// Brasil Data Hub client (emendas live here)
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
  : null;

/**
 * Load taxonomy mappings from DB.
 * Returns { temaToSlug, funcaoToSlug, slugToTaxonomia }
 */
async function loadTaxonomyMappings() {
  const [temaResult, funcaoResult, taxResult] = await Promise.all([
    supabase.from('map_tema_taxonomia').select('tema_principal, taxonomia_slug'),
    supabase.from('map_funcao_taxonomia').select('funcao, taxonomia_slug'),
    supabase.from('dim_taxonomia_tematica').select('slug, nome, cor, icone'),
  ]);

  const temaToSlug = new Map();
  for (const row of (temaResult.data || [])) {
    temaToSlug.set(row.tema_principal, row.taxonomia_slug);
  }

  const funcaoToSlug = new Map();
  for (const row of (funcaoResult.data || [])) {
    funcaoToSlug.set(row.funcao, row.taxonomia_slug);
  }

  const slugToTaxonomia = new Map();
  for (const row of (taxResult.data || [])) {
    slugToTaxonomia.set(row.slug, row);
  }

  return { temaToSlug, funcaoToSlug, slugToTaxonomia };
}

/**
 * Find emendas that match a given taxonomy slug.
 * Returns up to `limit` emendas from Brasil Data Hub.
 */
async function findEmendasByTaxonomySlug(slug, funcaoToSlug, limit = 10) {
  if (!brasilDataHub) return [];

  // Reverse lookup: which funcao values map to this slug?
  const matchingFuncoes = [];
  for (const [funcao, s] of funcaoToSlug) {
    if (s === slug) matchingFuncoes.push(funcao);
  }

  if (matchingFuncoes.length === 0) return [];

  // Query emendas with matching funcao
  const { data, error } = await brasilDataHub
    .from('fato_emendas_parlamentares')
    .select('id, autor, funcao, localidade, tipo_emenda, ano')
    .in('funcao', matchingFuncoes)
    .order('ano', { ascending: false })
    .limit(limit);

  if (error) {
    logger.warn('findEmendasByTaxonomySlug error', { slug, error: error.message });
    return [];
  }

  return data || [];
}

/**
 * Compute association confidence based on overlap signals.
 * Base: 0.5 for same taxonomy theme.
 * Bonus: +0.1 per matching entity (state, city, person).
 */
function computeConfianca(noticia, emenda) {
  let confianca = 0.5; // base: same theme

  // State overlap
  // noticias don't have explicit UF, but emendas have localidade
  // This can be enhanced later with entity extraction
  if (emenda.localidade && noticia.fonte_nome) {
    // Basic heuristic: if fonte contains state indicator
    confianca += 0.05;
  }

  // Year proximity: if emenda year matches publication year
  if (emenda.ano && noticia.data_publicacao) {
    const pubYear = new Date(noticia.data_publicacao).getFullYear();
    if (emenda.ano === pubYear) confianca += 0.15;
    else if (Math.abs(emenda.ano - pubYear) <= 1) confianca += 0.05;
  }

  return Math.min(confianca, 1.0);
}

/**
 * Insert associations in batch, ignoring duplicates.
 */
async function insertAssociations(associations) {
  if (associations.length === 0) return 0;

  const { error, count } = await supabase
    .from('fato_associacoes_contextuais')
    .upsert(associations, {
      onConflict: 'origem_tipo,origem_id,destino_tipo,destino_id,tipo_associacao',
      ignoreDuplicates: true,
    });

  if (error) {
    logger.error('insertAssociations error', { error: error.message });
    return 0;
  }

  return associations.length;
}

/**
 * Run regex-based signal detection on a batch of noticias.
 * Matches titulo + resumo against dim_sinais_contextuais.keywords_regex.
 */
async function detectSignals(noticias) {
  // Load active signals
  const { data: signals, error } = await supabase
    .from('dim_sinais_contextuais')
    .select('id, slug, keywords_regex')
    .eq('ativo', true);

  if (error || !signals || signals.length === 0) return 0;

  let inserted = 0;

  for (const noticia of noticias) {
    const text = `${noticia.titulo || ''} ${noticia.resumo || ''}`.toLowerCase();
    const matchedSignals = [];

    for (const signal of signals) {
      if (!signal.keywords_regex) continue;
      try {
        const regex = new RegExp(signal.keywords_regex, 'i');
        if (regex.test(text)) {
          matchedSignals.push({
            noticia_id: noticia.id,
            sinal_id: signal.id,
            confidence: 0.70,
            detection_method: 'regex',
          });
        }
      } catch {
        // Invalid regex, skip
      }
    }

    if (matchedSignals.length > 0) {
      const { error: insertErr } = await supabase
        .from('fato_noticias_sinais')
        .upsert(matchedSignals, {
          onConflict: 'noticia_id,sinal_id',
          ignoreDuplicates: true,
        });

      if (!insertErr) inserted += matchedSignals.length;
    }
  }

  return inserted;
}

/**
 * Main pipeline: populate associations for recent noticias.
 *
 * @param {Object} options
 * @param {number} [options.maxNoticias=200] - Max noticias to process
 * @param {number} [options.emendasPerSlug=5] - Max emendas per taxonomy slug
 * @param {boolean} [options.detectSignalsEnabled=true] - Also run signal detection
 * @returns {Promise<Object>} Pipeline stats
 */
export async function runAssociationPipeline({
  maxNoticias = 200,
  emendasPerSlug = 5,
  detectSignalsEnabled = true,
} = {}) {
  const stats = {
    noticias_processed: 0,
    associations_created: 0,
    signals_detected: 0,
    errors: 0,
    started_at: new Date().toISOString(),
  };

  logger.info('Association pipeline starting', { maxNoticias, emendasPerSlug });

  if (!brasilDataHub) {
    logger.warn('Brasil Data Hub not configured, skipping emenda associations');
  }

  // 1. Load taxonomy
  const { temaToSlug, funcaoToSlug } = await loadTaxonomyMappings();
  logger.info('Taxonomy loaded', {
    temas: temaToSlug.size,
    funcoes: funcaoToSlug.size,
  });

  // 2. Find noticias that don't have associations yet
  //    Left join approach: find noticias NOT IN fato_associacoes_contextuais
  const { data: noticias, error: fetchErr } = await supabase
    .from('dim_noticias')
    .select('id, titulo, resumo, fonte_nome, data_publicacao, tema_principal')
    .not('tema_principal', 'is', null)
    .order('data_publicacao', { ascending: false })
    .limit(maxNoticias);

  if (fetchErr) {
    logger.error('Failed to fetch noticias', { error: fetchErr.message });
    stats.errors++;
    stats.finished_at = new Date().toISOString();
    return stats;
  }

  if (!noticias || noticias.length === 0) {
    logger.info('No noticias to process');
    stats.finished_at = new Date().toISOString();
    return stats;
  }

  // 3. Check which noticias already have associations
  const noticiaIds = noticias.map(n => n.id);
  const { data: existing } = await supabase
    .from('fato_associacoes_contextuais')
    .select('origem_id')
    .eq('origem_tipo', 'noticia')
    .in('origem_id', noticiaIds);

  const existingSet = new Set((existing || []).map(e => e.origem_id));
  const newNoticias = noticias.filter(n => !existingSet.has(n.id));

  logger.info('Noticias to process', {
    total: noticias.length,
    already_associated: existingSet.size,
    new: newNoticias.length,
  });

  // 4. Cache emendas by slug to avoid repeated queries
  const emendasCache = new Map();

  // 5. Process in batches
  for (let i = 0; i < newNoticias.length; i += BATCH_SIZE) {
    const batch = newNoticias.slice(i, i + BATCH_SIZE);
    const batchAssociations = [];

    for (const noticia of batch) {
      const slug = temaToSlug.get(noticia.tema_principal);
      if (!slug) continue;

      // Get emendas for this slug (cached)
      if (!emendasCache.has(slug)) {
        const emendas = await findEmendasByTaxonomySlug(slug, funcaoToSlug, emendasPerSlug);
        emendasCache.set(slug, emendas);
      }

      const emendas = emendasCache.get(slug);

      for (const emenda of emendas) {
        const confianca = computeConfianca(noticia, emenda);
        batchAssociations.push({
          origem_tipo: 'noticia',
          origem_id: noticia.id,
          destino_tipo: 'emenda',
          destino_id: String(emenda.id),
          tipo_associacao: 'tema_comum',
          taxonomia_slug: slug,
          confianca,
          metodo: 'regra',
          evidencia: `Tema compartilhado: ${slug} | Emenda: ${emenda.autor || 'N/A'} (${emenda.ano})`,
        });
      }

      stats.noticias_processed++;
    }

    // Insert batch
    const created = await insertAssociations(batchAssociations);
    stats.associations_created += created;

    // Signal detection
    if (detectSignalsEnabled) {
      try {
        const detected = await detectSignals(batch);
        stats.signals_detected += detected;
      } catch (err) {
        logger.warn('Signal detection error', { error: err.message });
      }
    }

    logger.info('Association batch processed', {
      batch: Math.floor(i / BATCH_SIZE) + 1,
      noticias: batch.length,
      associations: batchAssociations.length,
    });
  }

  stats.finished_at = new Date().toISOString();
  logger.info('Association pipeline finished', stats);
  return stats;
}

/**
 * Get context for a single noticia.
 * Returns taxonomy, associated emendas, and detected signals.
 */
export async function getNoticiaContext(noticiaId) {
  // 1. Get noticia
  const { data: noticia, error: notErr } = await supabase
    .from('dim_noticias')
    .select('id, titulo, resumo, fonte_nome, data_publicacao, tema_principal, tipo_classificacao, credibilidade_score')
    .eq('id', noticiaId)
    .single();

  if (notErr || !noticia) return null;

  // 2. Map tema → taxonomy
  const { data: mapping } = await supabase
    .from('map_tema_taxonomia')
    .select('taxonomia_slug')
    .eq('tema_principal', noticia.tema_principal)
    .single();

  const taxonomiaSlug = mapping?.taxonomia_slug || null;

  // 3. Get taxonomy info
  let taxonomia = null;
  if (taxonomiaSlug) {
    const { data } = await supabase
      .from('dim_taxonomia_tematica')
      .select('slug, nome, cor, icone')
      .eq('slug', taxonomiaSlug)
      .single();
    taxonomia = data;
  }

  // 4. Get pre-computed associations
  const { data: associations } = await supabase
    .from('fato_associacoes_contextuais')
    .select('destino_id, tipo_associacao, confianca, evidencia, taxonomia_slug')
    .eq('origem_tipo', 'noticia')
    .eq('origem_id', noticiaId)
    .eq('destino_tipo', 'emenda')
    .order('confianca', { ascending: false })
    .limit(10);

  // 5. Fetch actual emendas from Brasil Data Hub
  let emendas = [];
  if (brasilDataHub && associations && associations.length > 0) {
    const emendaIds = associations.map(a => parseInt(a.destino_id, 10)).filter(id => !isNaN(id));
    if (emendaIds.length > 0) {
      const { data } = await brasilDataHub
        .from('fato_emendas_parlamentares')
        .select('id, autor, funcao, localidade, tipo_emenda, ano')
        .in('id', emendaIds);
      emendas = (data || []).map(e => {
        const assoc = associations.find(a => a.destino_id === String(e.id));
        return {
          ...e,
          confianca: assoc?.confianca || 0,
          evidencia: assoc?.evidencia || null,
        };
      });
    }
  }

  // 6. Fallback: if no pre-computed associations, find by tema
  if (emendas.length === 0 && taxonomiaSlug && brasilDataHub) {
    const { temaToSlug: _, funcaoToSlug } = await loadTaxonomyMappings();
    const matchingFuncoes = [];
    for (const [funcao, s] of funcaoToSlug) {
      if (s === taxonomiaSlug) matchingFuncoes.push(funcao);
    }
    if (matchingFuncoes.length > 0) {
      const { data } = await brasilDataHub
        .from('fato_emendas_parlamentares')
        .select('id, autor, funcao, localidade, tipo_emenda, ano')
        .in('funcao', matchingFuncoes)
        .order('ano', { ascending: false })
        .limit(5);
      emendas = (data || []).map(e => ({
        ...e,
        confianca: 0.4,
        evidencia: `Tema compartilhado (fallback): ${taxonomiaSlug}`,
      }));
    }
  }

  // 7. Get detected signals
  let sinais = [];
  const { data: sinaisData } = await supabase
    .rpc('get_noticias_sinais', { p_noticia_id: noticiaId });
  sinais = sinaisData || [];

  // 8. Get related entities
  const [empresasRes, pessoasRes, topicosRes] = await Promise.all([
    supabase.from('fato_noticias_empresas')
      .select('tipo_relacao, relevancia, dim_empresas(id, cnpj, razao_social, nome_fantasia)')
      .eq('noticia_id', noticiaId),
    supabase.from('fato_noticias_pessoas')
      .select('tipo_relacao, dim_pessoas(id, nome_completo, cargo_atual)')
      .eq('noticia_id', noticiaId),
    supabase.from('fato_noticias_topicos')
      .select('topico, relevancia, sentimento, impacto_mercado')
      .eq('noticia_id', noticiaId)
      .order('relevancia', { ascending: false }),
  ]);

  return {
    noticia,
    taxonomia,
    emendas_relacionadas: emendas,
    sinais,
    entidades: {
      empresas: (empresasRes.data || []).map(e => ({
        ...e.dim_empresas,
        tipo_relacao: e.tipo_relacao,
        relevancia: e.relevancia,
      })),
      pessoas: (pessoasRes.data || []).map(p => ({
        ...p.dim_pessoas,
        tipo_relacao: p.tipo_relacao,
      })),
    },
    topicos: topicosRes.data || [],
    associations_count: associations?.length || 0,
  };
}

export default {
  runAssociationPipeline,
  getNoticiaContext,
};
