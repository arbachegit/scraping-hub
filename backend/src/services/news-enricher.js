/**
 * News Enricher Service
 * Batch enrichment of classified news using Claude AI.
 *
 * Handles Intelligence Architecture sections 10, 12, 13:
 *   - Section 10: Multi-factor relevance scoring
 *   - Section 12: Contextual signal detection
 *   - Section 13: Entity extraction (pessoas, empresas, órgãos, municípios, partidos)
 *
 * Processes news that already have tipo_classificacao (from classifier)
 * but haven't been enriched yet (processado_claude = false or relevancia_geral = 50).
 */

import Anthropic from '@anthropic-ai/sdk';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';
import { escapeLike, sanitizeUUID, sanitizeForLog, maskPII } from '../utils/sanitize.js';

const BATCH_SIZE = 15;
const DELAY_BETWEEN_BATCHES_MS = 1500;

let anthropicClient = null;
let cachedSignals = null;

function getClient() {
  if (!anthropicClient) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new Error('ANTHROPIC_API_KEY is required');
    anthropicClient = new Anthropic({ apiKey });
  }
  return anthropicClient;
}

function getModel() {
  return process.env.ANTHROPIC_ENRICHER_MODEL || 'claude-haiku-4-5-20251001';
}

/**
 * Load predefined signals from dim_sinais_contextuais (cached).
 */
async function loadSignals() {
  if (cachedSignals) return cachedSignals;

  const { data, error } = await supabase
    .from('dim_sinais_contextuais')
    .select('id, slug, categoria, nome')
    .eq('ativo', true)
    .order('categoria');

  if (error) {
    logger.error('Failed to load signals', { error: error.message });
    return [];
  }

  cachedSignals = data || [];
  return cachedSignals;
}

/**
 * Build enrichment prompt for a batch.
 */
function buildPrompt(batch, signals) {
  const signalList = signals
    .map(s => `  ${s.id}|${s.slug}|${s.categoria}`)
    .join('\n');

  const newsBlock = batch.map((n, i) => (
    `[${i}] id="${n.id}"
Título: ${(n.titulo || '').substring(0, 200)}
Resumo: ${(n.resumo || '').substring(0, 400)}
Fonte: ${(n.fonte_nome || '').substring(0, 80)}
Tema: ${n.tema_principal || 'geral'}
Tipo: ${n.tipo_classificacao || 'factual'}`
  )).join('\n\n');

  return `Você é um analista de inteligência brasileiro. Para cada notícia abaixo, extraia 3 dimensões.

## DIMENSÃO 1 — SINAIS CONTEXTUAIS
Identifique quais sinais (da lista abaixo) a notícia ativa. Uma notícia pode ativar 0-3 sinais.

SINAIS DISPONÍVEIS (id|slug|categoria):
${signalList}

## DIMENSÃO 2 — ENTIDADES MENCIONADAS
Extraia entidades citadas na notícia:
- pessoas: nomes de pessoas citadas (parlamentares, ministros, empresários, especialistas)
- empresas: nomes de empresas ou organizações privadas
- orgaos: órgãos públicos (ministérios, autarquias, tribunais)
- municipios: cidades mencionadas
- estados: UFs mencionadas (sigla de 2 letras)
- partidos: siglas de partidos políticos
- programas: programas públicos (Bolsa Família, PAC, etc.)

## DIMENSÃO 3 — RELEVÂNCIA (0-100)
Calcule score baseado em:
- impacto_economico (0-20): afeta PIB, emprego, inflação?
- impacto_politico (0-20): afeta governo, legislação, eleições?
- cobertura_midiatica (0-20): tema amplamente coberto?
- proximidade_temporal (0-20): evento recente ou iminente?
- recorrencia_tematica (0-20): tema frequente nas últimas semanas?

NOTÍCIAS:
${newsBlock}

RESPONDA APENAS com JSON array. Cada elemento:
{
  "id": "<uuid>",
  "sinais": [1, 7],
  "entidades": {
    "pessoas": ["Nome Pessoa"],
    "empresas": ["Empresa X"],
    "orgaos": ["Ministério Y"],
    "municipios": ["São Paulo"],
    "estados": ["SP"],
    "partidos": ["PT"],
    "programas": ["PAC"]
  },
  "relevancia": {
    "impacto_economico": 15,
    "impacto_politico": 10,
    "cobertura_midiatica": 12,
    "proximidade_temporal": 18,
    "recorrencia_tematica": 8,
    "total": 63
  }
}

Se não houver sinais, use array vazio. Se não houver entidades de um tipo, use array vazio.`;
}

/**
 * Call Claude to enrich a batch.
 */
async function enrichBatch(batch, signals) {
  const client = getClient();
  const prompt = buildPrompt(batch, signals);

  const message = await client.messages.create({
    model: getModel(),
    max_tokens: 4096,
    temperature: 0.1,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = message.content[0]?.text || '';
  const jsonMatch = text.match(/\[[\s\S]*\]/);

  if (!jsonMatch) {
    logger.warn('Failed to parse enricher response', { text: sanitizeForLog(text.substring(0, 200)) });
    return [];
  }

  try {
    return JSON.parse(jsonMatch[0]);
  } catch (e) {
    logger.error('JSON parse error in enricher', { error: e.message });
    return [];
  }
}

/**
 * Persist enrichment results.
 */
async function persistEnrichment(results, signalMap) {
  let updated = 0;
  let signalsInserted = 0;
  let entitiesLinked = 0;
  let errors = 0;

  for (const r of results) {
    const safeId = sanitizeUUID(r.id);
    if (!safeId) continue;

    try {
      // 1. Update relevancia_geral
      const total = r.relevancia?.total;
      if (typeof total === 'number' && total >= 0 && total <= 100) {
        const { error } = await supabase
          .from('dim_noticias')
          .update({ relevancia_geral: total })
          .eq('id', safeId);

        if (error) {
          logger.error('Relevance update failed', { id: safeId, error: error.message });
          errors++;
        } else {
          updated++;
        }
      }

      // 2. Insert signals
      if (Array.isArray(r.sinais) && r.sinais.length > 0) {
        const validSignalIds = new Set(signalMap.map(s => s.id));
        const signalRows = r.sinais
          .filter(sid => validSignalIds.has(sid))
          .map(sid => ({ noticia_id: safeId, sinal_id: sid }));

        if (signalRows.length > 0) {
          const { error } = await supabase
            .from('fato_noticias_sinais')
            .upsert(signalRows, { onConflict: 'noticia_id,sinal_id', ignoreDuplicates: true });

          if (error) {
            logger.error('Signal insert failed', { id: safeId, error: error.message });
          } else {
            signalsInserted += signalRows.length;
          }
        }
      }

      // 3. Link entities — pessoas
      if (r.entidades?.pessoas?.length > 0) {
        for (const nome of r.entidades.pessoas.slice(0, 5)) {
          const escaped = escapeLike(String(nome).substring(0, 200));
          const { data: pessoa } = await supabase
            .from('dim_pessoas')
            .select('id')
            .ilike('nome_completo', `%${escaped}%`)
            .limit(1)
            .single();

          if (pessoa) {
            await supabase
              .from('fato_pessoas')
              .upsert({
                noticia_id: safeId,
                pessoa_id: pessoa.id,
                tipo_relacao: 'mencao',
              }, { onConflict: 'noticia_id,pessoa_id', ignoreDuplicates: true });
            entitiesLinked++;
          }
        }
      }

      // 4. Link entities — empresas
      if (r.entidades?.empresas?.length > 0) {
        for (const nome of r.entidades.empresas.slice(0, 5)) {
          const escaped = escapeLike(String(nome).substring(0, 200));
          const { data: empresa } = await supabase
            .from('dim_empresas')
            .select('id')
            .or(`razao_social.ilike.%${escaped}%,nome_fantasia.ilike.%${escaped}%`)
            .limit(1)
            .single();

          if (empresa) {
            await supabase
              .from('fato_noticias_empresas')
              .upsert({
                noticia_id: safeId,
                empresa_id: empresa.id,
                tipo_relacao: 'mencao',
                relevancia: 5,
              }, { onConflict: 'noticia_id,empresa_id', ignoreDuplicates: true });
            entitiesLinked++;
          }
        }
      }

    } catch (err) {
      logger.error('Enrichment persist error', { id: safeId, error: err.message });
      errors++;
    }
  }

  return { updated, signalsInserted, entitiesLinked, errors };
}

/**
 * Fetch classified but un-enriched news.
 * Criteria: has tipo_classificacao but relevancia_geral = 50 (default).
 */
export async function fetchUnenriched(limit = BATCH_SIZE) {
  const { data, error } = await supabase
    .from('dim_noticias')
    .select('id, titulo, resumo, fonte_nome, tema_principal, tipo_classificacao')
    .not('tipo_classificacao', 'is', null)
    .eq('relevancia_geral', 50)
    .order('data_publicacao', { ascending: false })
    .limit(limit);

  if (error) {
    logger.error('Error fetching unenriched news', { error: error.message });
    return [];
  }

  return data || [];
}

/**
 * Count un-enriched news.
 */
export async function countUnenriched() {
  const { count, error } = await supabase
    .from('dim_noticias')
    .select('id', { count: 'exact', head: true })
    .not('tipo_classificacao', 'is', null)
    .eq('relevancia_geral', 50);

  if (error) {
    logger.error('Error counting unenriched', { error: error.message });
    return 0;
  }

  return count || 0;
}

/**
 * Run the enrichment pipeline.
 * @param {Object} options
 * @param {number} [options.maxBatches=10]
 * @param {number} [options.batchSize=15]
 * @param {function} [options.onProgress]
 * @returns {Promise<Object>}
 */
export async function runEnrichmentPipeline({
  maxBatches = 10,
  batchSize = BATCH_SIZE,
  onProgress = null,
} = {}) {
  const signals = await loadSignals();
  const stats = {
    total_unenriched: await countUnenriched(),
    batches_processed: 0,
    updated: 0,
    signals_inserted: 0,
    entities_linked: 0,
    errors: 0,
    started_at: new Date().toISOString(),
  };

  logger.info('Enrichment pipeline starting', {
    unenriched: stats.total_unenriched,
    signals_available: signals.length,
    maxBatches,
    batchSize,
  });

  if (stats.total_unenriched === 0) {
    stats.finished_at = new Date().toISOString();
    logger.info('No unenriched news to process');
    return stats;
  }

  let batchesRun = 0;

  while (maxBatches === 0 || batchesRun < maxBatches) {
    const batch = await fetchUnenriched(batchSize);

    if (batch.length === 0) {
      logger.info('No more unenriched news');
      break;
    }

    logger.info('Processing enrichment batch', {
      batch: batchesRun + 1,
      size: batch.length,
    });

    try {
      const enrichments = await enrichBatch(batch, signals);
      const result = await persistEnrichment(enrichments, signals);

      stats.updated += result.updated;
      stats.signals_inserted += result.signalsInserted;
      stats.entities_linked += result.entitiesLinked;
      stats.errors += result.errors;
      stats.batches_processed++;
      batchesRun++;

      if (onProgress) onProgress({ ...stats });

      logger.info('Enrichment batch complete', {
        batch: batchesRun,
        ...result,
      });
    } catch (error) {
      logger.error('Enrichment batch failed', { batch: batchesRun + 1, error: error.message });
      stats.errors += batch.length;
      stats.batches_processed++;
      batchesRun++;
    }

    if (maxBatches === 0 || batchesRun < maxBatches) {
      await new Promise(r => setTimeout(r, DELAY_BETWEEN_BATCHES_MS));
    }
  }

  stats.finished_at = new Date().toISOString();
  stats.remaining = await countUnenriched();

  logger.info('Enrichment pipeline finished', stats);
  return stats;
}

export default {
  runEnrichmentPipeline,
  countUnenriched,
  fetchUnenriched,
};
