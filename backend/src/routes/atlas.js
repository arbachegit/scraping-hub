/**
 * Atlas Routes
 * API endpoints for the Atlas conversational agent.
 */

import { Router } from 'express';
import logger from '../utils/logger.js';
import {
  validateBody,
  atlasChatSchema,
  atlasClearSessionSchema
} from '../validation/schemas.js';
import {
  processChat,
  clearChatSession,
  getStatus
} from '../atlas/orchestrator.js';

const router = Router();

/**
 * POST /api/atlas/chat
 * Main conversation endpoint
 *
 * Request body:
 * {
 *   "message": "Quem é Lula?",
 *   "sessionId": null | "uuid"
 * }
 *
 * Response:
 * {
 *   "success": true,
 *   "sessionId": "uuid",
 *   "response": {
 *     "text": "Natural language response",
 *     "data": { ... },
 *     "suggestions": ["Pergunta 1", "Pergunta 2"]
 *   },
 *   "metadata": {
 *     "intent": "search_politician",
 *     "entities": { "nome": "Lula" },
 *     "processingTime": 245
 *   }
 * }
 */
router.post('/chat', validateBody(atlasChatSchema), async (req, res) => {
  try {
    const { message, sessionId } = req.body;

    logger.info('Atlas chat request', {
      sessionId: sessionId || 'new',
      messageLength: message.length
    });

    const result = await processChat({ message, sessionId });

    if (result.success) {
      res.json(result);
    } else {
      res.status(result.error?.includes('configurado') ? 503 : 400).json(result);
    }

  } catch (error) {
    logger.error('Atlas chat error', { error: error.message });
    res.status(500).json({
      success: false,
      error: 'Erro interno no processamento',
      response: {
        text: 'Desculpe, ocorreu um erro ao processar sua mensagem.',
        data: null,
        suggestions: ['Tente novamente', 'Reformule sua pergunta']
      }
    });
  }
});

/**
 * POST /api/atlas/session/clear
 * Clear session context
 *
 * Request body:
 * {
 *   "sessionId": "uuid"
 * }
 */
router.post('/session/clear', validateBody(atlasClearSessionSchema), async (req, res) => {
  try {
    const { sessionId } = req.body;

    logger.info('Atlas session clear', { sessionId });

    const result = clearChatSession(sessionId);

    res.json(result);

  } catch (error) {
    logger.error('Atlas session clear error', { error: error.message });
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/atlas/status
 * Get Atlas service status
 */
router.get('/status', async (req, res) => {
  try {
    const status = getStatus();
    res.json({
      success: true,
      ...status
    });
  } catch (error) {
    logger.error('Atlas status error', { error: error.message });
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/atlas/health
 * Health check endpoint
 */
router.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'atlas-agent',
    timestamp: new Date().toISOString()
  });
});

export default router;
