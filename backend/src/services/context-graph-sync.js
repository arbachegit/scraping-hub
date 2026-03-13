/**
 * Context Graph Sync Service
 * Syncs contextual associations (fato_associacoes_contextuais)
 * into the unified graph (fato_relacoes_entidades).
 *
 * Also creates emenda→politico edges from entity resolution.
 *
 * Flow:
 *   1. Fetch unsynced associations (not yet in fato_relacoes_entidades)
 *   2. Map association types to graph relationship types
 *   3. Upsert into fato_relacoes_entidades
 *   4. Fetch resolved emenda→politico links and create edges
 */

import { createClient } from '@supabase/supabase-js';
import { supabase } from '../database/supabase.js';
import { upsertRelationship } from './graph-pipeline.js';
import logger from '../utils/logger.js';

const BATCH_SIZE = 50;

// Brasil Data Hub client
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
  : null;

// Map association types to graph relationship types
const ASSOC_TO_RELACAO = {
  'tema_comum': 'mencionado_em',
  'territorio_comum': 'geografico',
  'mencao': 'mencionado_em',
  'autor_citado': 'politico_empresarial',
};

/**
 * Sync contextual associations into unified graph.
 * Reads from fato_associacoes_contextuais (scraping DB),
 * writes to fato_relacoes_entidades (scraping DB).
 *
 * @param {Object} options
 * @param {number} [options.maxAssociations=500] - Max associations to process
 * @returns {Promise<Object>} Sync stats
 */
export async function syncAssociationsToGraph({ maxAssociations = 500 } = {}) {
  const stats = {
    processed: 0,
    synced: 0,
    skipped: 0,
    errors: 0,
    started_at: new Date().toISOString(),
  };

  logger.info('context_graph_sync_start', { maxAssociations });

  // 1. Fetch associations not yet synced
  //    We use metodo != 'grafo' as a marker — associations created by this sync
  //    have metodo='grafo', so we skip those.
  const { data: associations, error: fetchErr } = await supabase
    .from('fato_associacoes_contextuais')
    .select('id, origem_tipo, origem_id, destino_tipo, destino_id, tipo_associacao, taxonomia_slug, confianca, evidencia')
    .neq('metodo', 'grafo')
    .order('created_at', { ascending: false })
    .limit(maxAssociations);

  if (fetchErr) {
    logger.error('context_graph_sync_fetch_error', { error: fetchErr.message });
    stats.errors++;
    stats.finished_at = new Date().toISOString();
    return stats;
  }

  if (!associations || associations.length === 0) {
    logger.info('context_graph_sync_nothing_to_sync');
    stats.finished_at = new Date().toISOString();
    return stats;
  }

  // 2. Check which associations already exist in fato_relacoes_entidades
  //    by looking for matching source/target pairs
  for (let i = 0; i < associations.length; i += BATCH_SIZE) {
    const batch = associations.slice(i, i + BATCH_SIZE);

    for (const assoc of batch) {
      stats.processed++;

      const tipoRelacao = ASSOC_TO_RELACAO[assoc.tipo_associacao] || 'mencionado_em';

      const result = await upsertRelationship({
        source_type: assoc.origem_tipo,
        source_id: assoc.origem_id,
        target_type: assoc.destino_tipo,
        target_id: assoc.destino_id,
        tipo_relacao: tipoRelacao,
        strength: assoc.confianca || 0.5,
        confidence: assoc.confianca || 0.5,
        bidirecional: false,
        source: 'context_engine',
        detection_method: `context_assoc_${assoc.tipo_associacao}`,
        metadata: {
          taxonomia_slug: assoc.taxonomia_slug,
          association_id: assoc.id,
          evidencia: assoc.evidencia,
        },
        descricao: assoc.evidencia,
      });

      if (result) {
        stats.synced++;
      } else {
        stats.skipped++;
      }
    }

    logger.info('context_graph_sync_batch', {
      batch: Math.floor(i / BATCH_SIZE) + 1,
      processed: batch.length,
    });
  }

  stats.finished_at = new Date().toISOString();
  logger.info('context_graph_sync_complete', stats);
  return stats;
}

/**
 * Sync emenda→politico edges from entity resolution.
 * Reads politico_id from fato_emendas_parlamentares (Brasil Data Hub),
 * creates edges in fato_relacoes_entidades (scraping DB).
 *
 * @param {Object} options
 * @param {number} [options.maxEmendas=500] - Max emendas to process
 * @returns {Promise<Object>} Sync stats
 */
export async function syncEmendaPoliticoEdges({ maxEmendas = 500 } = {}) {
  const stats = {
    processed: 0,
    edges_created: 0,
    errors: 0,
    started_at: new Date().toISOString(),
  };

  if (!brasilDataHub) {
    logger.warn('context_graph_sync_no_brasil_data_hub');
    stats.finished_at = new Date().toISOString();
    return stats;
  }

  logger.info('emenda_politico_sync_start', { maxEmendas });

  // 1. Fetch emendas with resolved politico_id
  const { data: emendas, error: fetchErr } = await brasilDataHub
    .from('fato_emendas_parlamentares')
    .select('id, autor, politico_id, funcao, ano, tipo_emenda, localidade')
    .not('politico_id', 'is', null)
    .order('ano', { ascending: false })
    .limit(maxEmendas);

  if (fetchErr || !emendas || emendas.length === 0) {
    if (fetchErr) logger.error('emenda_politico_fetch_error', { error: fetchErr.message });
    stats.finished_at = new Date().toISOString();
    return stats;
  }

  // 2. Get existing edges to avoid redundant upserts
  const emendaIds = emendas.map(e => String(e.id));
  const { data: existing } = await supabase
    .from('fato_relacoes_entidades')
    .select('target_id')
    .eq('source_type', 'politico')
    .eq('target_type', 'emenda')
    .eq('tipo_relacao', 'emenda_beneficiario')
    .in('target_id', emendaIds);

  const existingSet = new Set((existing || []).map(e => e.target_id));

  // 3. Create edges for new ones
  const newEmendas = emendas.filter(e => !existingSet.has(String(e.id)));

  for (const emenda of newEmendas) {
    stats.processed++;

    const result = await upsertRelationship({
      source_type: 'politico',
      source_id: String(emenda.politico_id),
      target_type: 'emenda',
      target_id: String(emenda.id),
      tipo_relacao: 'emenda_beneficiario',
      strength: 0.9,
      confidence: 0.85,
      bidirecional: false,
      source: 'brasil_data_hub',
      detection_method: 'entity_resolution',
      metadata: {
        autor: emenda.autor,
        funcao: emenda.funcao,
        ano: emenda.ano,
        tipo_emenda: emenda.tipo_emenda,
      },
      descricao: `${emenda.autor} - ${emenda.funcao || ''} (${emenda.ano})`,
    });

    if (result) stats.edges_created++;
  }

  stats.finished_at = new Date().toISOString();
  logger.info('emenda_politico_sync_complete', stats);
  return stats;
}

/**
 * Full context graph sync: associations + entity resolution edges.
 */
export async function runContextGraphSync(options = {}) {
  const assocStats = await syncAssociationsToGraph(options);
  const politicoStats = await syncEmendaPoliticoEdges(options);

  return {
    associations: assocStats,
    emenda_politico: politicoStats,
  };
}

export default {
  syncAssociationsToGraph,
  syncEmendaPoliticoEdges,
  runContextGraphSync,
};
