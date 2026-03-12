/**
 * News Classifier Service
 * Batch classification of news articles using Claude AI.
 *
 * Assigns:
 *   - tipo_classificacao: factual | analitica | investigativa | setorial | tendencia | sinal
 *   - tema_principal: economia | mercado | politica | saude | educacao | tecnologia |
 *                     infraestrutura | energia | agricultura | seguranca_publica | geral
 *
 * Follows the Intelligence Architecture plan (5-layer credibility + classification).
 */

import Anthropic from '@anthropic-ai/sdk';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';
import { sanitizeUUID, sanitizeForLog } from '../utils/sanitize.js';

const BATCH_SIZE = 25;
const DELAY_BETWEEN_BATCHES_MS = 1000;

const VALID_TIPOS = [
  'factual', 'analitica', 'investigativa', 'setorial', 'tendencia', 'sinal',
];

const VALID_TEMAS = [
  'economia', 'mercado', 'politica', 'saude', 'educacao', 'tecnologia',
  'infraestrutura', 'energia', 'agricultura', 'seguranca_publica', 'geral',
];

let anthropicClient = null;

function getClient() {
  if (!anthropicClient) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      throw new Error('ANTHROPIC_API_KEY is required for news classification');
    }
    anthropicClient = new Anthropic({ apiKey });
  }
  return anthropicClient;
}

function getModel() {
  return process.env.ANTHROPIC_CLASSIFIER_MODEL || 'claude-haiku-4-5-20251001';
}

/**
 * Build the classification prompt for a batch of news.
 * @param {Array<{id: string, titulo: string, resumo: string, fonte_nome: string}>} batch
 * @returns {string}
 */
function buildPrompt(batch) {
  const newsBlock = batch.map((n, i) => (
    `[${i}] id="${n.id}"
Título: ${(n.titulo || '').substring(0, 200)}
Resumo: ${(n.resumo || '').substring(0, 300)}
Fonte: ${(n.fonte_nome || 'desconhecida').substring(0, 100)}`
  )).join('\n\n');

  return `Você é um classificador de notícias brasileiro. Classifique cada notícia abaixo em DUAS dimensões.

DIMENSÃO 1 — tipo_classificacao (escolha UMA):
- factual: reportagem objetiva de fatos
- analitica: análise aprofundada com opinião especializada
- investigativa: denúncia ou investigação jornalística
- setorial: notícia específica de um setor econômico
- tendencia: tendência de mercado ou comportamento
- sinal: sinal fraco ou alerta antecipado

DIMENSÃO 2 — tema_principal (escolha UM):
- economia: macroeconomia, PIB, inflação, juros, câmbio
- mercado: bolsa, ações, fundos, investimentos, empresas
- politica: governo, legislação, eleições, políticas públicas
- saude: saúde pública, SUS, indústria farmacêutica
- educacao: ensino, universidades, ENEM, políticas educacionais
- tecnologia: TI, startups, IA, telecomunicações
- infraestrutura: obras, saneamento, transporte, logística
- energia: petróleo, gás, energia elétrica, renováveis
- agricultura: agronegócio, safra, exportações agrícolas
- seguranca_publica: criminalidade, polícia, justiça
- geral: quando não se encaixa claramente em nenhum acima

NOTÍCIAS:
${newsBlock}

RESPONDA APENAS com um JSON array. Cada elemento: {"id":"<uuid>","tipo":"<tipo_classificacao>","tema":"<tema_principal>"}
Exemplo: [{"id":"abc-123","tipo":"factual","tema":"economia"}]`;
}

/**
 * Call Claude to classify a batch of news articles.
 * @param {Array} batch
 * @returns {Promise<Array<{id: string, tipo: string, tema: string}>>}
 */
async function classifyBatch(batch) {
  const client = getClient();
  const prompt = buildPrompt(batch);

  const message = await client.messages.create({
    model: getModel(),
    max_tokens: 2048,
    temperature: 0.1,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = message.content[0]?.text || '';

  // Extract JSON array from response
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) {
    logger.warn('Failed to parse classifier response', { text: sanitizeForLog(text.substring(0, 200)) });
    return [];
  }

  try {
    const results = JSON.parse(jsonMatch[0]);
    // Validate and sanitize
    return results
      .filter(r => r.id && r.tipo && r.tema)
      .map(r => {
        const safeId = sanitizeUUID(r.id);
        if (!safeId) return null;
        return {
          id: safeId,
          tipo: VALID_TIPOS.includes(r.tipo) ? r.tipo : 'factual',
          tema: VALID_TEMAS.includes(r.tema) ? r.tema : 'geral',
        };
      })
      .filter(Boolean);
  } catch (e) {
    logger.error('JSON parse error in classifier', { error: e.message });
    return [];
  }
}

/**
 * Persist classification results to dim_noticias.
 * @param {Array<{id: string, tipo: string, tema: string}>} results
 * @returns {Promise<{updated: number, errors: number}>}
 */
async function persistResults(results) {
  let updated = 0;
  let errors = 0;

  for (const r of results) {
    const { error } = await supabase
      .from('dim_noticias')
      .update({
        tipo_classificacao: r.tipo,
        tema_principal: r.tema,
      })
      .eq('id', r.id);

    if (error) {
      logger.error('Update failed', { id: r.id, error: error.message });
      errors++;
    } else {
      updated++;
    }
  }

  return { updated, errors };
}

/**
 * Fetch unclassified news from the database.
 * @param {number} limit
 * @param {number} offset
 * @returns {Promise<Array>}
 */
export async function fetchUnclassified(limit = BATCH_SIZE, offset = 0) {
  const { data, error } = await supabase
    .from('dim_noticias')
    .select('id, titulo, resumo, fonte_nome')
    .is('tipo_classificacao', null)
    .order('data_publicacao', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    logger.error('Error fetching unclassified news', { error: error.message });
    return [];
  }

  return data || [];
}

/**
 * Count unclassified news articles.
 * @returns {Promise<number>}
 */
export async function countUnclassified() {
  const { count, error } = await supabase
    .from('dim_noticias')
    .select('id', { count: 'exact', head: true })
    .is('tipo_classificacao', null);

  if (error) {
    logger.error('Error counting unclassified', { error: error.message });
    return 0;
  }

  return count || 0;
}

/**
 * Run the classification pipeline for a given number of batches.
 * @param {Object} options
 * @param {number} [options.maxBatches=10] — max batches to process (0 = unlimited)
 * @param {number} [options.batchSize=25]
 * @param {function} [options.onProgress] — callback(stats) after each batch
 * @returns {Promise<Object>} Final statistics
 */
export async function runClassificationPipeline({
  maxBatches = 10,
  batchSize = BATCH_SIZE,
  onProgress = null,
} = {}) {
  const stats = {
    total_unclassified: await countUnclassified(),
    batches_processed: 0,
    classified: 0,
    errors: 0,
    started_at: new Date().toISOString(),
  };

  logger.info('Classification pipeline starting', {
    unclassified: stats.total_unclassified,
    maxBatches,
    batchSize,
  });

  if (stats.total_unclassified === 0) {
    stats.finished_at = new Date().toISOString();
    logger.info('No unclassified news to process');
    return stats;
  }

  let batchesRun = 0;

  while (maxBatches === 0 || batchesRun < maxBatches) {
    const batch = await fetchUnclassified(batchSize);

    if (batch.length === 0) {
      logger.info('No more unclassified news');
      break;
    }

    logger.info('Processing batch', {
      batch: batchesRun + 1,
      size: batch.length,
    });

    try {
      const classifications = await classifyBatch(batch);
      const { updated, errors } = await persistResults(classifications);

      stats.classified += updated;
      stats.errors += errors;
      stats.batches_processed++;
      batchesRun++;

      if (onProgress) {
        onProgress({ ...stats });
      }

      logger.info('Batch complete', {
        batch: batchesRun,
        classified: updated,
        errors,
        total_classified: stats.classified,
      });
    } catch (error) {
      logger.error('Batch failed', { batch: batchesRun + 1, error: error.message });
      stats.errors += batch.length;
      stats.batches_processed++;
      batchesRun++;
    }

    // Rate limit between batches
    if (maxBatches === 0 || batchesRun < maxBatches) {
      await new Promise(r => setTimeout(r, DELAY_BETWEEN_BATCHES_MS));
    }
  }

  stats.finished_at = new Date().toISOString();
  stats.remaining = await countUnclassified();

  logger.info('Classification pipeline finished', stats);
  return stats;
}

export default {
  classifyBatch,
  runClassificationPipeline,
  countUnclassified,
  fetchUnclassified,
  VALID_TIPOS,
  VALID_TEMAS,
};
