/**
 * Graph Pipeline Service
 * Detects and manages relationships between entities in the graph.
 *
 * Relationship detection strategies:
 * - socios_qsa: From BrasilAPI QSA data (societária)
 * - cnae_match: Companies with same CNAE principal (cnae_similar)
 * - geo_match: Companies in same city (geográfico)
 * - news_mention: Entities mentioned in same news (mencionado_em)
 * - manual: User-created relationships
 */

import { createClient } from '@supabase/supabase-js';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';

// Brasil Data Hub client (políticos, emendas, mandatos)
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
  : null;

// Strength mapping for sócio roles
const SOCIO_STRENGTH = {
  'ADMINISTRADOR': 1.0,
  'PRESIDENTE': 1.0,
  'DIRETOR': 0.9,
  'SOCIO-ADMINISTRADOR': 0.9,
  'SOCIO': 0.8,
  'CONSELHEIRO': 0.6,
  'PROCURADOR': 0.5,
  'COLABORADOR': 0.4,
  'DEFAULT': 0.5
};

/**
 * Upsert a relationship in fato_relacoes_entidades.
 * Uses ON CONFLICT to update if edge already exists.
 *
 * @param {Object} rel - Relationship data
 * @returns {Promise<Object|null>} Inserted/updated row or null on error
 */
export async function upsertRelationship(rel) {
  try {
    const { data, error } = await supabase
      .from('fato_relacoes_entidades')
      .upsert({
        source_type: rel.source_type,
        source_id: String(rel.source_id),
        target_type: rel.target_type,
        target_id: String(rel.target_id),
        tipo_relacao: rel.tipo_relacao,
        strength: rel.strength ?? 0.5,
        confidence: rel.confidence ?? 0.5,
        bidirecional: rel.bidirecional ?? false,
        source: rel.source ?? 'system',
        detection_method: rel.detection_method ?? null,
        metadata: rel.metadata ?? {},
        descricao: rel.descricao ?? null,
        data_inicio: rel.data_inicio ?? null,
        data_fim: rel.data_fim ?? null,
        ativo: rel.ativo ?? true
      }, {
        onConflict: 'source_type,source_id,target_type,target_id,tipo_relacao',
        ignoreDuplicates: false
      })
      .select()
      .single();

    if (error) {
      logger.warn('upsert_relationship_error', {
        error: error.message,
        code: error.code,
        source: `${rel.source_type}:${rel.source_id}`,
        target: `${rel.target_type}:${rel.target_id}`,
        tipo: rel.tipo_relacao
      });
      return null;
    }

    return data;
  } catch (err) {
    logger.error('upsert_relationship_exception', {
      error: err.message,
      rel: { source_type: rel.source_type, source_id: rel.source_id, target_type: rel.target_type, target_id: rel.target_id }
    });
    return null;
  }
}

/**
 * Detect societária relationships from sócios/QSA data.
 * Creates pessoa->empresa edges with strength based on role.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {Array} socios - Array of sócio objects with { id, cargo, qualificacao, data_entrada }
 * @returns {Promise<number>} Number of relationships created
 */
export async function detectRelationshipsFromSocios(empresa_id, socios) {
  if (!socios || socios.length === 0) return 0;

  let created = 0;

  for (const socio of socios) {
    if (!socio.id) continue;

    // Determine strength from cargo/qualificação
    const cargo = (socio.cargo || socio.qualificacao || '').toUpperCase();
    let strength = SOCIO_STRENGTH.DEFAULT;

    for (const [keyword, value] of Object.entries(SOCIO_STRENGTH)) {
      if (keyword !== 'DEFAULT' && cargo.includes(keyword)) {
        strength = value;
        break;
      }
    }

    const result = await upsertRelationship({
      source_type: 'pessoa',
      source_id: socio.id,
      target_type: 'empresa',
      target_id: empresa_id,
      tipo_relacao: 'societaria',
      strength,
      confidence: 0.95, // High confidence: from official QSA data
      bidirecional: true,
      source: 'brasilapi',
      detection_method: 'socios_qsa',
      metadata: {
        cargo: socio.cargo || socio.qualificacao,
        data_entrada: socio.data_entrada
      },
      descricao: `${socio.cargo || socio.qualificacao || 'Sócio'} da empresa`,
      data_inicio: socio.data_entrada || null
    });

    if (result) created++;
  }

  logger.info('detect_socios_complete', { empresa_id, total_socios: socios.length, created });
  return created;
}

/**
 * Detect CNAE similarity relationships.
 * Finds other companies with the same CNAE principal and creates edges.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {string} cnae_principal - CNAE code (e.g. "6201-5/01")
 * @returns {Promise<number>} Number of relationships created
 */
export async function detectRelationshipsFromCnae(empresa_id, cnae_principal) {
  if (!cnae_principal) return 0;

  try {
    // Find companies with same CNAE (limit to avoid explosion)
    const { data: similar, error } = await supabase
      .from('fato_regime_tributario')
      .select('empresa_id')
      .eq('cnae_principal', cnae_principal)
      .eq('ativo', true)
      .neq('empresa_id', empresa_id)
      .limit(50);

    if (error || !similar || similar.length === 0) return 0;

    let created = 0;
    const uniqueIds = [...new Set(similar.map(s => s.empresa_id))];

    for (const targetId of uniqueIds) {
      const result = await upsertRelationship({
        source_type: 'empresa',
        source_id: empresa_id,
        target_type: 'empresa',
        target_id: targetId,
        tipo_relacao: 'cnae_similar',
        strength: 0.3,
        confidence: 0.9, // High: exact CNAE match
        bidirecional: true,
        source: 'system',
        detection_method: 'cnae_match',
        metadata: { cnae: cnae_principal },
        descricao: `Mesmo CNAE: ${cnae_principal}`
      });

      if (result) created++;
    }

    logger.info('detect_cnae_complete', { empresa_id, cnae: cnae_principal, matches: uniqueIds.length, created });
    return created;
  } catch (err) {
    logger.error('detect_cnae_error', { empresa_id, cnae: cnae_principal, error: err.message });
    return 0;
  }
}

/**
 * Detect geographic relationships.
 * Finds other companies in the same city and creates edges.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {string} cidade - City name
 * @param {string} estado - State code (UF)
 * @returns {Promise<number>} Number of relationships created
 */
export async function detectRelationshipsFromGeo(empresa_id, cidade, estado) {
  if (!cidade) return 0;

  try {
    let query = supabase
      .from('dim_empresas')
      .select('id')
      .ilike('cidade', cidade)
      .neq('id', empresa_id)
      .limit(50);

    if (estado) {
      query = query.ilike('estado', estado);
    }

    const { data: nearby, error } = await query;

    if (error || !nearby || nearby.length === 0) return 0;

    let created = 0;

    for (const target of nearby) {
      const result = await upsertRelationship({
        source_type: 'empresa',
        source_id: empresa_id,
        target_type: 'empresa',
        target_id: target.id,
        tipo_relacao: 'geografico',
        strength: 0.2,
        confidence: 0.85,
        bidirecional: true,
        source: 'system',
        detection_method: 'geo_match',
        metadata: { cidade, estado },
        descricao: `Mesma cidade: ${cidade}/${estado || ''}`
      });

      if (result) created++;
    }

    logger.info('detect_geo_complete', { empresa_id, cidade, estado, matches: nearby.length, created });
    return created;
  } catch (err) {
    logger.error('detect_geo_error', { empresa_id, cidade, error: err.message });
    return 0;
  }
}

/**
 * Detect news mention relationships.
 * Searches dim_noticias for mentions of the company name.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {string} nome - Company name to search for
 * @returns {Promise<number>} Number of relationships created
 */
export async function detectRelationshipsFromNews(empresa_id, nome) {
  if (!nome || nome.length < 3) return 0;

  try {
    // Search news that mention this company
    const { data: news, error } = await supabase
      .from('dim_noticias')
      .select('id, titulo')
      .or(`titulo.ilike.%${nome}%,conteudo.ilike.%${nome}%`)
      .limit(20);

    if (error || !news || news.length === 0) return 0;

    let created = 0;

    for (const noticia of news) {
      const result = await upsertRelationship({
        source_type: 'empresa',
        source_id: empresa_id,
        target_type: 'noticia',
        target_id: noticia.id,
        tipo_relacao: 'mencionado_em',
        strength: 0.6,
        confidence: 0.7, // Medium: text match, could be false positive
        bidirecional: false,
        source: 'system',
        detection_method: 'news_mention',
        metadata: { titulo_noticia: noticia.titulo },
        descricao: `Mencionado em: ${noticia.titulo?.substring(0, 100)}`
      });

      if (result) created++;
    }

    logger.info('detect_news_complete', { empresa_id, nome, matches: news.length, created });
    return created;
  } catch (err) {
    logger.error('detect_news_error', { empresa_id, nome, error: err.message });
    return 0;
  }
}

/**
 * Escape special characters for ILIKE patterns.
 * @param {string} str
 * @returns {string}
 */
function escapeLike(str) {
  if (!str) return '';
  return str.replace(/[%_\\]/g, '\\$&');
}

/**
 * Detect emenda_beneficiario relationships.
 * Searches fato_emendas_parlamentares from Brasil Data Hub for emendas
 * that mention the company name or city.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {string} nome - Company name
 * @param {string} cidade - City name
 * @returns {Promise<{emendas: number, autores: string[]}>} Created count + autor names for politico lookup
 */
export async function detectRelationshipsFromEmendas(empresa_id, nome, cidade) {
  if (!brasilDataHub || !nome || nome.length < 3) return { emendas: 0, autores: [] };

  try {
    const hubEsc = `%${escapeLike(nome)}%`;
    const filters = [`autor.ilike.${hubEsc}`, `descricao.ilike.${hubEsc}`];

    if (cidade) {
      const cidadeEsc = `%${escapeLike(cidade)}%`;
      filters.push(`localidade.ilike.${cidadeEsc}`);
    }

    const { data: emendas, error } = await brasilDataHub
      .from('fato_emendas_parlamentares')
      .select('id, autor, descricao, localidade, uf, ano, tipo, valor_empenhado')
      .or(filters.join(','))
      .limit(20);

    if (error || !emendas || emendas.length === 0) {
      if (error) logger.warn('detect_emendas_error', { empresa_id, error: error.message });
      return { emendas: 0, autores: [] };
    }

    let created = 0;
    const autores = new Set();

    for (const emenda of emendas) {
      const result = await upsertRelationship({
        source_type: 'empresa',
        source_id: empresa_id,
        target_type: 'emenda',
        target_id: String(emenda.id),
        tipo_relacao: 'emenda_beneficiario',
        strength: 0.5,
        confidence: 0.7,
        bidirecional: false,
        source: 'brasil_data_hub',
        detection_method: 'emenda_mention',
        metadata: {
          autor: emenda.autor,
          tipo: emenda.tipo,
          ano: emenda.ano,
          uf: emenda.uf,
          valor: emenda.valor_empenhado,
          localidade: emenda.localidade,
        },
        descricao: `Emenda: ${(emenda.autor || '').substring(0, 50)} - ${emenda.tipo || ''} ${emenda.ano || ''}`
      });

      if (result) created++;
      if (emenda.autor) autores.add(emenda.autor);
    }

    logger.info('detect_emendas_complete', { empresa_id, nome, matches: emendas.length, created });
    return { emendas: created, autores: [...autores] };
  } catch (err) {
    logger.error('detect_emendas_exception', { empresa_id, nome, error: err.message });
    return { emendas: 0, autores: [] };
  }
}

/**
 * Detect politico_empresarial relationships.
 * Searches dim_politicos from Brasil Data Hub matching emenda autores.
 * Also connects políticos back to their emendas.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {string[]} autores - Autor names from emendas
 * @returns {Promise<{politicos: number, politicoIds: number[]}>} Created count + raw DB IDs for mandato lookup
 */
export async function detectRelationshipsFromPoliticos(empresa_id, autores) {
  if (!brasilDataHub || !autores || autores.length === 0) return { politicos: 0, politicoIds: [] };

  try {
    const autorFilters = autores
      .map(a => {
        const e = `%${escapeLike(a)}%`;
        return `nome_completo.ilike.${e},nome_urna.ilike.${e}`;
      })
      .join(',');

    const { data: politicos, error } = await brasilDataHub
      .from('dim_politicos')
      .select('id, nome_completo, nome_urna, partido_sigla, cargo_atual')
      .or(autorFilters)
      .limit(20);

    if (error || !politicos || politicos.length === 0) {
      if (error) logger.warn('detect_politicos_error', { empresa_id, error: error.message });
      return { politicos: 0, politicoIds: [] };
    }

    let created = 0;
    const politicoIds = [];

    for (const pol of politicos) {
      const polName = pol.nome_urna || pol.nome_completo;

      // Connect politico to empresa
      const result = await upsertRelationship({
        source_type: 'politico',
        source_id: String(pol.id),
        target_type: 'empresa',
        target_id: empresa_id,
        tipo_relacao: 'politico_empresarial',
        strength: 0.5,
        confidence: 0.6,
        bidirecional: false,
        source: 'brasil_data_hub',
        detection_method: 'politico_emenda_link',
        metadata: {
          partido: pol.partido_sigla,
          cargo: pol.cargo_atual,
        },
        descricao: `${polName} (${pol.partido_sigla || ''}) - conexão via emendas`
      });

      if (result) created++;
      politicoIds.push(pol.id);
    }

    logger.info('detect_politicos_complete', { empresa_id, matches: politicos.length, created });
    return { politicos: created, politicoIds };
  } catch (err) {
    logger.error('detect_politicos_exception', { empresa_id, error: err.message });
    return { politicos: 0, politicoIds: [] };
  }
}

/**
 * Detect mandato relationships.
 * Fetches mandatos from fato_politicos_mandatos for connected políticos.
 * Connects mandatos to their políticos, and to the empresa if same city.
 *
 * @param {number|string} empresa_id - dim_empresas.id
 * @param {number[]} politicoIds - Raw DB IDs from dim_politicos
 * @param {string} cidade - Empresa city for geographic matching
 * @returns {Promise<number>} Number of relationships created
 */
export async function detectRelationshipsFromMandatos(empresa_id, politicoIds, cidade) {
  if (!brasilDataHub || !politicoIds || politicoIds.length === 0) return 0;

  try {
    const { data: mandatos, error } = await brasilDataHub
      .from('fato_politicos_mandatos')
      .select('id, cargo, partido_sigla, municipio, codigo_ibge, ano_eleicao, eleito, politico_id')
      .in('politico_id', politicoIds)
      .limit(30);

    if (error || !mandatos || mandatos.length === 0) {
      if (error) logger.warn('detect_mandatos_error', { empresa_id, error: error.message });
      return 0;
    }

    let created = 0;

    for (const mandato of mandatos) {
      // Connect mandato to its politico
      const polResult = await upsertRelationship({
        source_type: 'politico',
        source_id: String(mandato.politico_id),
        target_type: 'mandato',
        target_id: String(mandato.id),
        tipo_relacao: 'societaria',
        strength: 1.0,
        confidence: 0.95,
        bidirecional: false,
        source: 'brasil_data_hub',
        detection_method: 'mandato_link',
        metadata: {
          cargo: mandato.cargo,
          municipio: mandato.municipio,
          ano: mandato.ano_eleicao,
          partido: mandato.partido_sigla,
        },
        descricao: `${mandato.cargo || 'Mandato'} ${mandato.municipio || ''} ${mandato.ano_eleicao || ''}`
      });

      if (polResult) created++;

      // If mandato municipality matches empresa city, connect to empresa too
      const municipioMatch = mandato.municipio && cidade &&
        mandato.municipio.toLowerCase().includes(cidade.toLowerCase());

      if (municipioMatch) {
        const geoResult = await upsertRelationship({
          source_type: 'empresa',
          source_id: empresa_id,
          target_type: 'mandato',
          target_id: String(mandato.id),
          tipo_relacao: 'mencionado_em',
          strength: 0.3,
          confidence: 0.6,
          bidirecional: false,
          source: 'brasil_data_hub',
          detection_method: 'mandato_geo_match',
          metadata: { municipio: mandato.municipio, cidade },
          descricao: `Mandato na mesma cidade: ${mandato.municipio}`
        });

        if (geoResult) created++;
      }
    }

    logger.info('detect_mandatos_complete', { empresa_id, matches: mandatos.length, created });
    return created;
  } catch (err) {
    logger.error('detect_mandatos_exception', { empresa_id, error: err.message });
    return 0;
  }
}

/**
 * Orchestrate all relationship detection after a company is approved.
 * Called from POST /api/companies/approve endpoint.
 *
 * @param {Object} params
 * @param {number|string} params.empresa_id - Inserted company ID
 * @param {Array} params.socios - Inserted sócios with IDs
 * @param {string} params.cnae_principal - CNAE code
 * @param {string} params.cidade - City
 * @param {string} params.estado - State
 * @param {string} params.nome - Company name for news search
 * @returns {Promise<Object>} Summary of detected relationships
 */
export async function enrichRelationshipsAfterApproval({
  empresa_id,
  socios = [],
  cnae_principal = null,
  cidade = null,
  estado = null,
  nome = null
}) {
  logger.info('graph_enrichment_start', { empresa_id });

  const results = {
    societaria: 0,
    cnae_similar: 0,
    geografico: 0,
    mencionado_em: 0,
    emenda_beneficiario: 0,
    politico_empresarial: 0,
    mandatos: 0,
    total: 0
  };

  // Run detections (sequentially to avoid overwhelming the DB)
  results.societaria = await detectRelationshipsFromSocios(empresa_id, socios);
  results.cnae_similar = await detectRelationshipsFromCnae(empresa_id, cnae_principal);
  results.geografico = await detectRelationshipsFromGeo(empresa_id, cidade, estado);
  results.mencionado_em = await detectRelationshipsFromNews(empresa_id, nome);

  // Brasil Data Hub: emendas → políticos → mandatos (chained)
  const emendasResult = await detectRelationshipsFromEmendas(empresa_id, nome, cidade);
  results.emenda_beneficiario = emendasResult.emendas;

  const politicosResult = await detectRelationshipsFromPoliticos(empresa_id, emendasResult.autores);
  results.politico_empresarial = politicosResult.politicos;

  results.mandatos = await detectRelationshipsFromMandatos(empresa_id, politicosResult.politicoIds, cidade);

  results.total = results.societaria + results.cnae_similar + results.geografico
    + results.mencionado_em + results.emenda_beneficiario
    + results.politico_empresarial + results.mandatos;

  logger.info('graph_enrichment_complete', { empresa_id, ...results });
  return results;
}

/**
 * Get all relationships for an entity (both directions).
 *
 * @param {string} entityType - Entity type
 * @param {string} entityId - Entity ID
 * @param {Object} filters - Optional filters
 * @returns {Promise<Array>} Array of relationships
 */
export async function getEntityRelationships(entityType, entityId, filters = {}) {
  try {
    let query = supabase
      .from('fato_relacoes_entidades')
      .select('*')
      .eq('ativo', true);

    // Get both outgoing and incoming edges
    query = query.or(
      `and(source_type.eq.${entityType},source_id.eq.${entityId}),and(target_type.eq.${entityType},target_id.eq.${entityId})`
    );

    if (filters.tipo_relacao) {
      query = query.eq('tipo_relacao', filters.tipo_relacao);
    }

    if (filters.min_strength) {
      query = query.gte('strength', filters.min_strength);
    }

    const { data, error } = await query
      .order('strength', { ascending: false })
      .limit(filters.limit || 100);

    if (error) {
      logger.error('get_entity_relationships_error', { entityType, entityId, error: error.message });
      return [];
    }

    return data || [];
  } catch (err) {
    logger.error('get_entity_relationships_exception', { entityType, entityId, error: err.message });
    return [];
  }
}
