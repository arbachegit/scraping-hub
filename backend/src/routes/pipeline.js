/**
 * Pipeline API Routes
 * Endpoints to trigger, monitor, and manage the BI intelligence pipeline.
 */

import { Router } from 'express';
import { z } from 'zod';
import logger from '../utils/logger.js';
import { sanitizeForLog } from '../utils/sanitize.js';
import {
  executePipeline,
  executeBatchPipeline,
  getPipelineStatus,
  listPipelineRuns,
  PIPELINE_PHASES,
} from '../services/pipeline-orchestrator.js';

const router = Router();

// ── Validation schemas ──

const uuidParam = z.object({
  empresaId: z.string().uuid(),
});

const runIdParam = z.object({
  runId: z.string().uuid(),
});

const pipelineBody = z.object({
  skip_crawl: z.boolean().optional().default(false),
  skip_graph: z.boolean().optional().default(false),
  force_crawl: z.boolean().optional().default(false),
  only_phases: z.array(z.string()).optional(),
});

const batchBody = z.object({
  empresa_ids: z.array(z.string().uuid()).min(1).max(50),
  skip_crawl: z.boolean().optional().default(false),
  skip_graph: z.boolean().optional().default(false),
});

// ── Endpoints ──

/**
 * GET /api/pipeline/phases
 * List all pipeline phases with descriptions.
 */
router.get('/phases', (_req, res) => {
  res.json({ success: true, data: PIPELINE_PHASES });
});

/**
 * POST /api/pipeline/execute/:empresaId
 * Execute the full BI pipeline for a single company.
 * Returns immediately with runId — poll /status/:runId for progress.
 */
router.post('/execute/:empresaId', async (req, res) => {
  try {
    const { empresaId } = uuidParam.parse(req.params);
    const options = pipelineBody.parse(req.body || {});

    logger.info('pipeline_execute_request', {
      empresaId: sanitizeForLog(empresaId),
      options,
    });

    // Run pipeline asynchronously — respond with runId immediately
    const runPromise = executePipeline(empresaId, {
      skipCrawl: options.skip_crawl,
      skipGraph: options.skip_graph,
      forceCrawl: options.force_crawl,
      onlyPhases: options.only_phases,
    });

    // Wait a short time for fast pipelines to complete
    const timeout = new Promise((resolve) => setTimeout(() => resolve(null), 500));
    const result = await Promise.race([runPromise, timeout]);

    if (result) {
      // Pipeline completed within 500ms
      return res.json({ success: true, data: result });
    }

    // Pipeline still running — get the runId from the in-memory tracker
    // The run was created synchronously, so we can find it
    const recentRuns = listPipelineRuns(empresaId, 1);
    const runId = recentRuns[0]?.id || null;

    res.status(202).json({
      success: true,
      message: 'Pipeline iniciado. Use o runId para acompanhar o progresso.',
      data: { runId, status: 'running' },
    });

    // Let the promise complete in the background
    runPromise.catch((err) => {
      logger.error('pipeline_background_error', {
        empresaId: sanitizeForLog(empresaId),
        error: err.message,
      });
    });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: 'Dados inválidos', details: err.errors });
    }
    logger.error('pipeline_execute_error', { error: err.message });
    res.status(500).json({ error: 'Erro ao iniciar pipeline' });
  }
});

/**
 * GET /api/pipeline/status/:runId
 * Get the current status of a pipeline run.
 */
router.get('/status/:runId', (req, res) => {
  try {
    const { runId } = runIdParam.parse(req.params);
    const status = getPipelineStatus(runId);

    if (!status) {
      return res.status(404).json({ error: 'Execução não encontrada' });
    }

    res.json({ success: true, data: status });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: 'ID inválido', details: err.errors });
    }
    res.status(500).json({ error: 'Erro ao buscar status' });
  }
});

/**
 * GET /api/pipeline/history/:empresaId
 * List recent pipeline runs for a company.
 */
router.get('/history/:empresaId', (req, res) => {
  try {
    const { empresaId } = uuidParam.parse(req.params);
    const limit = Math.min(parseInt(req.query.limit) || 10, 50);
    const history = listPipelineRuns(empresaId, limit);

    res.json({ success: true, data: history, total: history.length });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: 'ID inválido', details: err.errors });
    }
    res.status(500).json({ error: 'Erro ao buscar histórico' });
  }
});

/**
 * POST /api/pipeline/batch
 * Execute pipeline for multiple companies.
 */
router.post('/batch', async (req, res) => {
  try {
    const { empresa_ids, skip_crawl, skip_graph } = batchBody.parse(req.body);

    logger.info('pipeline_batch_request', {
      count: empresa_ids.length,
      skip_crawl,
      skip_graph,
    });

    const result = await executeBatchPipeline(empresa_ids, {
      skipCrawl: skip_crawl,
      skipGraph: skip_graph,
    });

    res.json({ success: true, data: result });
  } catch (err) {
    if (err instanceof z.ZodError) {
      return res.status(400).json({ error: 'Dados inválidos', details: err.errors });
    }
    logger.error('pipeline_batch_error', { error: err.message });
    res.status(500).json({ error: 'Erro no batch pipeline' });
  }
});

export default router;
