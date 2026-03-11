/**
 * BI Graph Sync Service
 * Syncs ecosystem relationships from dim_ecossistema_empresas
 * into fato_relacoes_entidades so they appear in the graph visualization.
 *
 * Also syncs opportunity-based edges for high-score opportunities.
 *
 * Triggered alongside the existing graph-sync (via stats snapshot).
 */

import { supabase } from '../database/supabase.js';
import { upsertRelationship } from './graph-pipeline.js';
import logger from '../utils/logger.js';
import { RELATIONSHIP_TYPES } from '../constants.js';

const SYNC_KEY = 'bi_graph_sync_last_run';
const BATCH_SIZE = 20;

// Map ecosystem tipo_relacao → graph relationship type
const ECOSYSTEM_TO_GRAPH = {
  cliente: RELATIONSHIP_TYPES.CLIENTE_DE,
  fornecedor: RELATIONSHIP_TYPES.FORNECEDOR_DE,
  concorrente: RELATIONSHIP_TYPES.CONCORRENTE_DE,
  parceiro: RELATIONSHIP_TYPES.PARCEIRO_DE,
};

/**
 * Sync BI ecosystem relationships to the graph.
 * Finds new ecosystem records not yet in fato_relacoes_entidades and inserts them.
 *
 * @returns {Promise<Object>} { synced, opportunities_synced, errors }
 */
export async function syncBiToGraph() {
  const startTime = Date.now();
  let synced = 0;
  let opportunitiesSynced = 0;
  let errors = 0;

  try {
    const since = await getLastSyncTime();

    // 1. Sync ecosystem relationships
    const { data: ecoRecords, error: ecoError } = await supabase
      .from('dim_ecossistema_empresas')
      .select('id, empresa_id, empresa_relacionada_id, tipo_relacao, fonte_deteccao, evidencia_id')
      .eq('ativo', true)
      .not('empresa_relacionada_id', 'is', null)
      .gte('created_at', since)
      .limit(BATCH_SIZE);

    if (ecoError) {
      logger.error('bi_graph_sync_eco_error', { error: ecoError.message });
    } else {
      for (const eco of (ecoRecords || [])) {
        const tipoRelacao = ECOSYSTEM_TO_GRAPH[eco.tipo_relacao];
        if (!tipoRelacao) continue;

        // Get evidence confidence if available
        let confidence = 0.5;
        if (eco.evidencia_id) {
          const { data: ev } = await supabase
            .from('fato_evidencias')
            .select('confianca')
            .eq('id', eco.evidencia_id)
            .single();
          if (ev) confidence = ev.confianca;
        }

        const result = await upsertRelationship({
          source_type: 'empresa',
          source_id: eco.empresa_id,
          target_type: 'empresa',
          target_id: eco.empresa_relacionada_id,
          tipo_relacao: tipoRelacao,
          strength: confidence,
          confidence,
          bidirecional: eco.tipo_relacao === 'concorrente' || eco.tipo_relacao === 'parceiro',
          source: 'bi_pipeline',
          detection_method: `bi_${eco.fonte_deteccao}`,
          metadata: { ecossistema_id: eco.id, fonte_deteccao: eco.fonte_deteccao },
        });

        if (result) synced++;
        else errors++;
      }
    }

    // 2. Sync high-score opportunities as weak edges
    const { data: opportunities, error: opError } = await supabase
      .from('fato_oportunidades')
      .select('id, empresa_origem_id, empresa_alvo_id, tipo_oportunidade, score_oportunidade, lead_temperatura')
      .not('empresa_alvo_id', 'is', null)
      .gte('score_oportunidade', 60) // Only sync high-score opportunities
      .gte('created_at', since)
      .limit(BATCH_SIZE);

    if (opError) {
      logger.error('bi_graph_sync_opp_error', { error: opError.message });
    } else {
      for (const opp of (opportunities || [])) {
        const result = await upsertRelationship({
          source_type: 'empresa',
          source_id: opp.empresa_origem_id,
          target_type: 'empresa',
          target_id: opp.empresa_alvo_id,
          tipo_relacao: RELATIONSHIP_TYPES.OPORTUNIDADE,
          strength: opp.score_oportunidade / 100,
          confidence: 0.5,
          bidirecional: false,
          source: 'bi_pipeline',
          detection_method: `bi_opportunity_${opp.tipo_oportunidade}`,
          metadata: {
            oportunidade_id: opp.id,
            score: opp.score_oportunidade,
            temperatura: opp.lead_temperatura,
            tipo: opp.tipo_oportunidade,
          },
        });

        if (result) opportunitiesSynced++;
        else errors++;
      }
    }

    await setLastSyncTime(new Date().toISOString());

    const duration = Date.now() - startTime;
    if (synced > 0 || opportunitiesSynced > 0) {
      logger.info('bi_graph_sync_complete', {
        synced,
        opportunities_synced: opportunitiesSynced,
        errors,
        duration_ms: duration,
      });
    }

    return { synced, opportunities_synced: opportunitiesSynced, errors, duration_ms: duration };
  } catch (err) {
    logger.error('bi_graph_sync_error', { error: err.message });
    return { synced, opportunities_synced: opportunitiesSynced, errors: errors + 1, duration_ms: Date.now() - startTime };
  }
}

async function getLastSyncTime() {
  try {
    const { data } = await supabase
      .from('config_kv')
      .select('value')
      .eq('key', SYNC_KEY)
      .maybeSingle();

    if (data?.value) return data.value;
  } catch {
    // Table may not exist
  }

  const d = new Date();
  d.setHours(d.getHours() - 24);
  return d.toISOString();
}

async function setLastSyncTime(timestamp) {
  try {
    await supabase
      .from('config_kv')
      .upsert({ key: SYNC_KEY, value: timestamp }, { onConflict: 'key' });
  } catch {
    // Non-critical
  }
}
