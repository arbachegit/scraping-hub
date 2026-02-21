/**
 * Atlas LLM Service
 * Handles LLM integration for natural language generation.
 * Primary: Claude API (Anthropic)
 * Fallback: OpenAI GPT-4
 */

import logger from '../utils/logger.js';

// LLM provider configuration
const PROVIDER = process.env.ATLAS_LLM_PROVIDER || 'anthropic';
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// Model configurations
const MODELS = {
  anthropic: {
    model: 'claude-3-haiku-20240307',  // Fast and cost-effective for chat
    maxTokens: 1024
  },
  openai: {
    model: 'gpt-4o-mini',  // Fast and cost-effective
    maxTokens: 1024
  }
};

/**
 * Check if LLM is configured
 * @returns {Object} - Configuration status
 */
export function getConfig() {
  return {
    provider: PROVIDER,
    anthropic_configured: !!ANTHROPIC_API_KEY,
    openai_configured: !!OPENAI_API_KEY,
    available: !!(ANTHROPIC_API_KEY || OPENAI_API_KEY)
  };
}

/**
 * Call Anthropic Claude API
 * @param {string} systemPrompt - System prompt
 * @param {Array} messages - Conversation messages
 * @returns {Promise<string>} - Model response
 */
async function callAnthropic(systemPrompt, messages) {
  if (!ANTHROPIC_API_KEY) {
    throw new Error('Anthropic API key not configured');
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: MODELS.anthropic.model,
      max_tokens: MODELS.anthropic.maxTokens,
      system: systemPrompt,
      messages: messages.map(m => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content
      }))
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    logger.error('Anthropic API error', { status: response.status, error: errorText });
    throw new Error(`Anthropic API error: ${response.status}`);
  }

  const data = await response.json();
  return data.content?.[0]?.text || '';
}

/**
 * Call OpenAI API
 * @param {string} systemPrompt - System prompt
 * @param {Array} messages - Conversation messages
 * @returns {Promise<string>} - Model response
 */
async function callOpenAI(systemPrompt, messages) {
  if (!OPENAI_API_KEY) {
    throw new Error('OpenAI API key not configured');
  }

  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content
    }))
  ];

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${OPENAI_API_KEY}`
    },
    body: JSON.stringify({
      model: MODELS.openai.model,
      max_tokens: MODELS.openai.maxTokens,
      messages: formattedMessages
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    logger.error('OpenAI API error', { status: response.status, error: errorText });
    throw new Error(`OpenAI API error: ${response.status}`);
  }

  const data = await response.json();
  return data.choices?.[0]?.message?.content || '';
}

/**
 * Generate response using LLM
 * @param {string} systemPrompt - System prompt
 * @param {Array} messages - Conversation messages
 * @returns {Promise<Object>} - Response with text and metadata
 */
export async function generate(systemPrompt, messages) {
  const startTime = Date.now();

  // Determine which provider to use
  let provider = PROVIDER;
  let text = '';
  let success = false;

  // Try primary provider first
  try {
    if (provider === 'anthropic' && ANTHROPIC_API_KEY) {
      text = await callAnthropic(systemPrompt, messages);
      success = true;
    } else if (provider === 'openai' && OPENAI_API_KEY) {
      text = await callOpenAI(systemPrompt, messages);
      success = true;
    } else if (ANTHROPIC_API_KEY) {
      // Default to Anthropic if available
      provider = 'anthropic';
      text = await callAnthropic(systemPrompt, messages);
      success = true;
    } else if (OPENAI_API_KEY) {
      // Fallback to OpenAI
      provider = 'openai';
      text = await callOpenAI(systemPrompt, messages);
      success = true;
    }
  } catch (primaryError) {
    logger.warn('Primary LLM failed, trying fallback', { provider, error: primaryError.message });

    // Try fallback
    try {
      if (provider === 'anthropic' && OPENAI_API_KEY) {
        provider = 'openai';
        text = await callOpenAI(systemPrompt, messages);
        success = true;
      } else if (provider === 'openai' && ANTHROPIC_API_KEY) {
        provider = 'anthropic';
        text = await callAnthropic(systemPrompt, messages);
        success = true;
      }
    } catch (fallbackError) {
      logger.error('Both LLM providers failed', {
        primary: primaryError.message,
        fallback: fallbackError.message
      });
    }
  }

  const processingTime = Date.now() - startTime;

  if (!success) {
    return {
      success: false,
      text: null,
      error: 'Nenhum provedor de LLM disponível',
      processingTime
    };
  }

  logger.debug('LLM response generated', {
    provider,
    responseLength: text.length,
    processingTime
  });

  return {
    success: true,
    text,
    provider,
    processingTime
  };
}

/**
 * Generate response without LLM (fallback for when no LLM is available)
 * @param {Object} queryResult - Data from query builder
 * @returns {string} - Simple formatted response
 */
export function generateFallbackResponse(queryResult) {
  const { data, queryType, error } = queryResult;

  if (error) {
    return `Desculpe, ocorreu um erro: ${error}`;
  }

  if (!data) {
    return 'Não encontrei informações para sua consulta.';
  }

  switch (queryType) {
    case 'search_politician':
    case 'by_party':
    case 'by_municipality': {
      const items = Array.isArray(data) ? data : [data];
      if (items.length === 0) {
        return 'Não encontrei nenhum político com esses critérios.';
      }

      const lines = [`Encontrei ${items.length} resultado(s):\n`];
      for (const p of items.slice(0, 5)) {
        const cargo = p.cargo_atual || p.cargo || '';
        const partido = p.partido_sigla ? ` (${p.partido_sigla})` : '';
        const municipio = p.municipio ? ` - ${p.municipio}` : '';
        lines.push(`- ${p.nome_completo || p.nome_urna}${partido}${cargo ? ` - ${cargo}` : ''}${municipio}`);
      }

      if (items.length > 5) {
        lines.push(`\n... e mais ${items.length - 5} resultados.`);
      }

      return lines.join('\n');
    }

    case 'politician_details': {
      const { politico, mandatos } = data;
      const lines = [
        `**${politico.nome_completo}**`,
        politico.nome_urna ? `Nome de urna: ${politico.nome_urna}` : '',
        politico.sexo ? `Sexo: ${politico.sexo}` : '',
        politico.ocupacao ? `Ocupação: ${politico.ocupacao}` : '',
        politico.grau_instrucao ? `Escolaridade: ${politico.grau_instrucao}` : '',
        '',
        `**Mandatos (${mandatos?.length || 0}):**`
      ].filter(Boolean);

      for (const m of (mandatos || []).slice(0, 5)) {
        const eleito = m.eleito ? 'Eleito' : 'Não eleito';
        lines.push(`- ${m.ano_eleicao}: ${m.cargo} - ${m.partido_sigla} (${eleito})`);
      }

      return lines.join('\n');
    }

    case 'statistics': {
      const lines = [
        `**Estatísticas:**`,
        `Total de mandatos: ${data.total_mandatos || 0}`,
        `Total de eleitos: ${data.total_eleitos || 0}`,
        '',
        '**Top partidos:**'
      ];

      for (const [sigla, count] of (data.partidos_ordenados || []).slice(0, 5)) {
        lines.push(`- ${sigla}: ${count} mandatos`);
      }

      return lines.join('\n');
    }

    case 'party_list': {
      const items = Array.isArray(data) ? data : [];
      const lines = [`**Partidos cadastrados (${items.length}):**`, ''];

      for (const p of items.slice(0, 10)) {
        lines.push(`- ${p.sigla}${p.nome !== p.sigla ? ` (${p.nome})` : ''}: ${p.count} mandatos`);
      }

      if (items.length > 10) {
        lines.push(`\n... e mais ${items.length - 10} partidos.`);
      }

      return lines.join('\n');
    }

    default:
      return 'Consulta processada com sucesso.';
  }
}

export default {
  generate,
  generateFallbackResponse,
  getConfig
};
