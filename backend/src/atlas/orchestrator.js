/**
 * Atlas Orchestrator
 * Main coordinator that handles chat messages, manages sessions,
 * and coordinates the intent → query → response flow.
 */

import logger from '../utils/logger.js';
import { parseIntent, INTENTS } from './intent-parser.js';
import { executeQuery, isConfigured as isDbConfigured } from './query-builder.js';
import {
  getOrCreateSession,
  addMessage,
  updateLastQuery,
  resolveReferences,
  getConversationContext,
  clearSession,
  getStats as getSessionStats
} from './context-manager.js';
import { formatResponse, formatSimpleMessage } from './response-formatter.js';
import { getConfig as getLLMConfig } from './llm-service.js';

/**
 * Process a chat message from the user
 * @param {Object} request - Chat request
 * @param {string} request.message - User message
 * @param {string|null} request.sessionId - Optional session ID
 * @returns {Promise<Object>} - Chat response
 */
export async function processChat(request) {
  const startTime = Date.now();
  const { message, sessionId } = request;

  // Validate message
  if (!message || typeof message !== 'string' || message.trim().length === 0) {
    return {
      success: false,
      error: 'Mensagem não pode estar vazia',
      sessionId: null
    };
  }

  // Get or create session
  const session = getOrCreateSession(sessionId);

  // Add user message to history
  addMessage(session.id, 'user', message.trim());

  // Check database configuration
  if (!isDbConfigured()) {
    const response = formatSimpleMessage('NOT_CONFIGURED');
    addMessage(session.id, 'assistant', response.text);

    return {
      success: false,
      sessionId: session.id,
      error: 'Serviço de dados não configurado',
      response: {
        text: response.text,
        data: null,
        suggestions: response.suggestions
      }
    };
  }

  try {
    // Step 1: Parse intent
    logger.debug('Processing chat message', {
      sessionId: session.id,
      messageLength: message.length
    });

    const parsedIntent = parseIntent(message.trim(), {
      lastQuery: session.lastQuery
    });

    // Step 2: Resolve references from context
    const resolvedEntities = resolveReferences(parsedIntent.entities, session);
    parsedIntent.entities = resolvedEntities;

    logger.debug('Intent parsed', {
      intent: parsedIntent.intent,
      confidence: parsedIntent.confidence,
      entities: parsedIntent.entities
    });

    // Step 3: Execute query
    const queryResult = await executeQuery(parsedIntent);
    queryResult.intent = parsedIntent.intent;
    queryResult.entities = parsedIntent.entities;

    // Step 4: Update session context
    updateLastQuery(session.id, queryResult);

    // Step 5: Format response
    const conversationHistory = getConversationContext(session.id);
    const formattedResponse = await formatResponse(
      queryResult,
      message.trim(),
      conversationHistory
    );

    // Add assistant response to history
    addMessage(session.id, 'assistant', formattedResponse.text);

    const totalTime = Date.now() - startTime;

    logger.info('Chat processed', {
      sessionId: session.id,
      intent: parsedIntent.intent,
      resultCount: Array.isArray(queryResult.data) ? queryResult.data.length : 1,
      usedLLM: formattedResponse.usedLLM,
      totalTime
    });

    return {
      success: true,
      sessionId: session.id,
      response: {
        text: formattedResponse.text,
        data: formattedResponse.data,
        suggestions: formattedResponse.suggestions
      },
      metadata: {
        intent: parsedIntent.intent,
        entities: parsedIntent.entities,
        confidence: parsedIntent.confidence,
        usedLLM: formattedResponse.usedLLM,
        processingTime: totalTime
      }
    };

  } catch (error) {
    logger.error('Chat processing error', {
      sessionId: session.id,
      error: error.message,
      stack: error.stack
    });

    const response = formatSimpleMessage('GENERAL_ERROR');
    addMessage(session.id, 'assistant', response.text);

    return {
      success: false,
      sessionId: session.id,
      error: error.message,
      response: {
        text: response.text,
        data: null,
        suggestions: response.suggestions
      }
    };
  }
}

/**
 * Clear a session
 * @param {string} sessionId - Session ID to clear
 * @returns {Object} - Result
 */
export function clearChatSession(sessionId) {
  if (!sessionId) {
    return { success: false, error: 'Session ID required' };
  }

  clearSession(sessionId);

  return { success: true };
}

/**
 * Get Atlas service status
 * @returns {Object} - Service status
 */
export function getStatus() {
  const llmConfig = getLLMConfig();
  const sessionStats = getSessionStats();

  return {
    status: 'healthy',
    database: {
      configured: isDbConfigured()
    },
    llm: {
      provider: llmConfig.provider,
      anthropic_configured: llmConfig.anthropic_configured,
      openai_configured: llmConfig.openai_configured,
      available: llmConfig.available
    },
    sessions: sessionStats
  };
}

export default {
  processChat,
  clearChatSession,
  getStatus
};
