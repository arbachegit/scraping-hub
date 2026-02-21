/**
 * Atlas Response Formatter
 * Formats query results as natural language responses using LLM.
 */

import logger from '../utils/logger.js';
import { generate, generateFallbackResponse, getConfig as getLLMConfig } from './llm-service.js';
import {
  ATLAS_SYSTEM_PROMPT,
  buildResponsePrompt,
  buildSuggestionsPrompt,
  DEFAULT_SUGGESTIONS,
  ERROR_MESSAGES
} from './prompts/system.js';

/**
 * Generate suggestions based on query result
 * @param {Object} queryResult - Result from query builder
 * @returns {Promise<Array<string>>} - List of suggestions
 */
async function generateSuggestions(queryResult) {
  const llmConfig = getLLMConfig();

  if (!llmConfig.available) {
    return DEFAULT_SUGGESTIONS;
  }

  try {
    const suggestionsPrompt = buildSuggestionsPrompt(queryResult);
    const result = await generate(
      'Você é um assistente que sugere perguntas de acompanhamento sobre dados políticos brasileiros. Responda apenas com as perguntas, uma por linha.',
      [{ role: 'user', content: suggestionsPrompt }]
    );

    if (result.success && result.text) {
      // Parse suggestions from response
      const suggestions = result.text
        .split('\n')
        .map(s => s.replace(/^[\d\-\.\)]+\s*/, '').trim())
        .filter(s => s.length > 5 && s.length < 100)
        .slice(0, 3);

      if (suggestions.length > 0) {
        return suggestions;
      }
    }
  } catch (error) {
    logger.warn('Failed to generate suggestions', { error: error.message });
  }

  return DEFAULT_SUGGESTIONS;
}

/**
 * Format query result into natural language response
 * @param {Object} queryResult - Result from query builder
 * @param {string} userMessage - Original user message
 * @param {Array} conversationHistory - Previous conversation messages
 * @returns {Promise<Object>} - Formatted response
 */
export async function formatResponse(queryResult, userMessage, conversationHistory = []) {
  const startTime = Date.now();
  const llmConfig = getLLMConfig();

  // Handle errors
  if (queryResult.error) {
    logger.warn('Query returned error', { error: queryResult.error });

    const response = {
      text: queryResult.error.includes('não configurado')
        ? ERROR_MESSAGES.NOT_CONFIGURED
        : ERROR_MESSAGES.DATABASE_ERROR,
      data: null,
      suggestions: DEFAULT_SUGGESTIONS,
      usedLLM: false
    };

    return response;
  }

  // Handle no data
  if (!queryResult.data || (Array.isArray(queryResult.data) && queryResult.data.length === 0)) {
    return {
      text: ERROR_MESSAGES.NO_DATA,
      data: null,
      suggestions: DEFAULT_SUGGESTIONS,
      usedLLM: false
    };
  }

  // Try to use LLM for natural response
  let responseText = '';
  let usedLLM = false;

  if (llmConfig.available) {
    try {
      // Build conversation messages for context
      const messages = [
        ...conversationHistory.slice(-4).map(m => ({
          role: m.role,
          content: m.content
        })),
        {
          role: 'user',
          content: buildResponsePrompt(queryResult, userMessage)
        }
      ];

      const llmResult = await generate(ATLAS_SYSTEM_PROMPT, messages);

      if (llmResult.success && llmResult.text) {
        responseText = llmResult.text;
        usedLLM = true;

        logger.debug('LLM response formatted', {
          provider: llmResult.provider,
          processingTime: llmResult.processingTime
        });
      }
    } catch (error) {
      logger.warn('LLM formatting failed, using fallback', { error: error.message });
    }
  }

  // Fallback to simple formatting if LLM failed or not available
  if (!responseText) {
    responseText = generateFallbackResponse(queryResult);
  }

  // Generate suggestions (async but don't block)
  const suggestions = await generateSuggestions(queryResult);

  const processingTime = Date.now() - startTime;

  return {
    text: responseText,
    data: queryResult.data,
    suggestions,
    usedLLM,
    processingTime
  };
}

/**
 * Format a simple message without data
 * @param {string} messageKey - Key from ERROR_MESSAGES
 * @returns {Object} - Simple response object
 */
export function formatSimpleMessage(messageKey) {
  return {
    text: ERROR_MESSAGES[messageKey] || ERROR_MESSAGES.GENERAL_ERROR,
    data: null,
    suggestions: DEFAULT_SUGGESTIONS,
    usedLLM: false
  };
}

export default {
  formatResponse,
  formatSimpleMessage
};
