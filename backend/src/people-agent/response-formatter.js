/**
 * People Agent - Response Formatter
 * Takes query results and formats as natural language using LLM,
 * with fallback to template-based formatting.
 * Reuses llm-service from Atlas (data-agnostic).
 */

import logger from '../utils/logger.js';
import { generate, generateFallbackResponse as llmFallback, getConfig } from '../atlas/llm-service.js';
import {
  PEOPLE_AGENT_SYSTEM_PROMPT,
  buildResponsePrompt,
  buildSuggestionsPrompt,
  DEFAULT_SUGGESTIONS,
  ERROR_MESSAGES
} from './prompts/system.js';

/**
 * Generate fallback response without LLM (people-specific templates)
 * @param {Object} queryResult
 * @returns {string}
 */
function generatePeopleFallback(queryResult) {
  const { data, queryType, error } = queryResult;

  if (error) {
    return `Desculpe, ocorreu um erro: ${error}`;
  }

  if (!data) {
    return ERROR_MESSAGES.NO_DATA;
  }

  // Guardrail blocked
  if (data.blocked) {
    return `Busca bloqueada: ${data.reason}${data.requiredFields?.length ? `\nCampos necessários: ${data.requiredFields.join(', ')}` : ''}`;
  }

  switch (queryType) {
    case 'search_person': {
      const items = Array.isArray(data) ? data : [data];
      if (items.length === 0) {
        return 'Não encontrei nenhuma pessoa com esses critérios.';
      }

      const lines = [`Encontrei ${items.length} resultado(s):\n`];
      for (const p of items.slice(0, 5)) {
        const nome = p.nome_completo || p.primeiro_nome || 'Nome não disponível';
        const cargo = p.cargo_atual ? ` - ${p.cargo_atual}` : '';
        const empresa = p.empresa_atual ? ` @ ${p.empresa_atual}` : '';
        lines.push(`- **${nome}**${cargo}${empresa}`);
      }

      if (items.length > 5) {
        lines.push(`\n... e mais ${items.length - 5} resultados.`);
      }

      return lines.join('\n');
    }

    case 'person_details': {
      const profile = data.profile;
      if (!profile) return ERROR_MESSAGES.NO_DATA;

      const lines = [];
      lines.push(`**${profile.nome_completo || 'Nome não disponível'}**\n`);

      if (profile.cargo_atual || profile.empresa_atual) {
        lines.push('**Profissional**');
        if (profile.cargo_atual) lines.push(`Cargo: ${profile.cargo_atual}`);
        if (profile.empresa_atual) lines.push(`Empresa: ${profile.empresa_atual}`);
        if (profile.headline) lines.push(`Bio: ${profile.headline}`);
        lines.push('');
      }

      if (profile.linkedin_url || profile.email) {
        lines.push('**Contato/Social**');
        if (profile.linkedin_url) lines.push(`LinkedIn: ${profile.linkedin_url}`);
        if (profile.email) lines.push(`Email: ${profile.email}`);
        lines.push('');
      }

      if (profile.resumo_profissional) {
        lines.push('**Resumo**');
        lines.push(profile.resumo_profissional);
        lines.push('');
      }

      if (profile.empresas?.length > 0) {
        lines.push(`**Conexões (${profile.empresas.length})**`);
        for (const conn of profile.empresas.slice(0, 5)) {
          const empresa = conn.empresa?.razao_social || conn.empresa?.nome_fantasia || 'Empresa';
          const cargo = conn.cargo ? ` - ${conn.cargo}` : '';
          lines.push(`- ${empresa}${cargo}`);
        }
        lines.push('');
      }

      if (profile.sources_used?.length) {
        lines.push(`_Fontes: ${profile.sources_used.join(', ')}_`);
      }

      return lines.join('\n');
    }

    case 'person_professional': {
      const profile = data.profile;
      if (!profile) return ERROR_MESSAGES.NO_DATA;

      const lines = [
        `**Carreira de ${profile.nome_completo || 'Pessoa'}**\n`,
        profile.cargo_atual ? `Cargo atual: ${profile.cargo_atual}` : '',
        profile.empresa_atual ? `Empresa: ${profile.empresa_atual}` : '',
        profile.headline ? `Headline: ${profile.headline}` : '',
        profile.resumo_profissional ? `\n${profile.resumo_profissional}` : ''
      ].filter(Boolean);

      return lines.join('\n');
    }

    case 'person_connections': {
      if (!data.connections?.length) {
        return 'Não encontrei conexões empresariais para essa pessoa.';
      }

      const lines = [`**Conexões de ${data.person?.nome_completo || 'Pessoa'}** (${data.connections.length})\n`];

      for (const conn of data.connections.slice(0, 10)) {
        const empresa = conn.dim_empresas?.razao_social || conn.dim_empresas?.nome_fantasia || 'Empresa';
        const cargo = conn.cargo ? ` - ${conn.cargo}` : '';
        const status = conn.ativo ? '' : ' (inativo)';
        lines.push(`- ${empresa}${cargo}${status}`);
      }

      return lines.join('\n');
    }

    case 'person_social': {
      const profile = data.profile;
      if (!profile) return ERROR_MESSAGES.NO_DATA;

      const lines = [`**Redes Sociais de ${profile.nome_completo || 'Pessoa'}**\n`];
      if (profile.linkedin_url) lines.push(`LinkedIn: ${profile.linkedin_url}`);
      if (profile.github_url) lines.push(`GitHub: ${profile.github_url}`);
      if (profile.email) lines.push(`Email: ${profile.email}`);

      if (lines.length === 1) {
        lines.push('Nenhuma rede social encontrada.');
      }

      return lines.join('\n');
    }

    case 'person_reputation':
    case 'person_academic': {
      const profile = data.profile;
      if (!profile) return ERROR_MESSAGES.NO_DATA;

      return profile.resumo_profissional ||
        `Informações ${queryType === 'person_academic' ? 'acadêmicas' : 'de reputação'} não disponíveis para ${profile.nome_completo || 'essa pessoa'}.`;
    }

    default:
      return 'Consulta processada. Tente buscar uma pessoa por nome ou CPF.';
  }
}

/**
 * Generate follow-up suggestions
 */
async function generateSuggestions(queryResult, conversationHistory) {
  const config = getConfig();
  if (!config.available) {
    return DEFAULT_SUGGESTIONS;
  }

  try {
    const suggestionsPrompt = buildSuggestionsPrompt(queryResult);
    const result = await generate(PEOPLE_AGENT_SYSTEM_PROMPT, [
      ...conversationHistory.slice(-2),
      { role: 'user', content: suggestionsPrompt }
    ]);

    if (result.success && result.text) {
      const suggestions = result.text
        .split('\n')
        .map(s => s.trim())
        .filter(s => s.length > 0 && s.length < 60)
        .slice(0, 3);

      if (suggestions.length >= 2) {
        return suggestions;
      }
    }
  } catch (error) {
    logger.warn('Failed to generate suggestions', { error: error.message });
  }

  return DEFAULT_SUGGESTIONS;
}

/**
 * Format response using LLM with fallback to templates
 * @param {Object} queryResult - Data from query builder
 * @param {string} userMessage - Original user message
 * @param {Array} conversationHistory - Previous messages
 * @returns {Object} - { text, data, suggestions, usedLLM, processingTime }
 */
export async function formatResponse(queryResult, userMessage, conversationHistory = []) {
  const startTime = Date.now();

  // Handle errors and empty data early
  if (queryResult.error) {
    return {
      text: ERROR_MESSAGES.DATABASE_ERROR,
      data: null,
      suggestions: DEFAULT_SUGGESTIONS,
      usedLLM: false,
      processingTime: Date.now() - startTime
    };
  }

  if (!queryResult.data) {
    return {
      text: ERROR_MESSAGES.NO_DATA,
      data: null,
      suggestions: DEFAULT_SUGGESTIONS,
      usedLLM: false,
      processingTime: Date.now() - startTime
    };
  }

  // Guardrail blocked
  if (queryResult.data.blocked) {
    return {
      text: generatePeopleFallback(queryResult),
      data: queryResult.data,
      suggestions: DEFAULT_SUGGESTIONS,
      usedLLM: false,
      processingTime: Date.now() - startTime
    };
  }

  // Try LLM first
  const config = getConfig();
  let text = '';
  let usedLLM = false;

  if (config.available) {
    try {
      const responsePrompt = buildResponsePrompt(queryResult, userMessage);
      const messages = [
        ...conversationHistory.slice(-4),
        { role: 'user', content: responsePrompt }
      ];

      const llmResult = await generate(PEOPLE_AGENT_SYSTEM_PROMPT, messages);

      if (llmResult.success && llmResult.text) {
        text = llmResult.text;
        usedLLM = true;
      }
    } catch (error) {
      logger.warn('LLM formatting failed, using fallback', { error: error.message });
    }
  }

  // Fallback to templates
  if (!text) {
    text = generatePeopleFallback(queryResult);
  }

  // Generate suggestions (in parallel if LLM is available)
  const suggestions = await generateSuggestions(queryResult, conversationHistory);

  return {
    text,
    data: queryResult.data,
    suggestions,
    usedLLM,
    processingTime: Date.now() - startTime
  };
}

/**
 * Format a simple pre-defined message
 * @param {string} messageKey - Key from ERROR_MESSAGES
 * @returns {string}
 */
export function formatSimpleMessage(messageKey) {
  return ERROR_MESSAGES[messageKey] || ERROR_MESSAGES.GENERAL_ERROR;
}

export default {
  formatResponse,
  formatSimpleMessage
};
