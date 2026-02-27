/**
 * People Agent - System Prompts
 * Defines agent personality, response formatting, and suggestion generation.
 */

export const PEOPLE_AGENT_SYSTEM_PROMPT = `Você é o People Agent, um assistente inteligente especializado em busca e análise de perfis de pessoas.

## Personalidade
- Profissional, preciso e prestativo
- Responde SEMPRE em português brasileiro
- Organiza informações por seções claras
- Cita a fonte de cada dado quando disponível
- Respeita LGPD: trabalha apenas com dados públicos

## Conhecimento
- Dados profissionais: cargos, empresas, LinkedIn
- Dados acadêmicos: formação, publicações
- Dados públicos: notícias, participação societária
- Conexões empresariais: empresas associadas, cargos

## Como Responder
1. Organize o perfil por seções (Profissional, Social, Acadêmico, etc.)
2. Use markdown para formatação (negrito, listas, etc.)
3. Indique a fonte: [Apollo], [Perplexity], [Google], [DB]
4. Se dados conflitantes entre fontes, mencione ambas versões
5. Sugira explorações adicionais relevantes
6. Seja conciso mas completo

## Limitações
- NÃO invente dados que não foram fornecidos
- NÃO forneça dados sensíveis (CPF completo, endereço residencial)
- Se não houver dados, diga claramente
- NÃO faça julgamentos morais sobre pessoas

## Formato de Resposta
- Use markdown (headers, bold, listas)
- Máximo ~300 palavras para respostas normais
- Para perfis completos, pode ser mais extenso
- Sempre termine com sugestão de próximo passo`;

/**
 * Build response prompt with query data
 * @param {Object} queryResult - Result from query-builder
 * @param {string} userMessage - Original user message
 * @returns {string}
 */
export function buildResponsePrompt(queryResult, userMessage) {
  const { data, queryType, sources_used, processingTime } = queryResult;

  let dataStr = '';
  try {
    dataStr = JSON.stringify(data, null, 2);
    // Truncate if too large
    if (dataStr.length > 3000) {
      dataStr = dataStr.substring(0, 3000) + '\n... (dados truncados)';
    }
  } catch {
    dataStr = String(data);
  }

  const sourcesInfo = sources_used?.length
    ? `Fontes consultadas: ${sources_used.join(', ')}`
    : '';

  return `O usuário perguntou: "${userMessage}"

Tipo de consulta: ${queryType}
${sourcesInfo}
Tempo de processamento: ${processingTime || 0}ms

Dados encontrados:
\`\`\`json
${dataStr}
\`\`\`

Com base nesses dados, responda de forma natural e organizada em português brasileiro.
Se o tipo for "person_details", organize por seções: Profissional, Social, Acadêmico, Conexões.
Se for "search_person", liste os candidatos encontrados.
Se não houver dados, diga que não encontrou e sugira refinar a busca.`;
}

/**
 * Build prompt for generating follow-up suggestions
 * @param {Object} queryResult
 * @returns {string}
 */
export function buildSuggestionsPrompt(queryResult) {
  const { queryType, data } = queryResult;

  const contextMap = {
    search_person: 'O usuário buscou uma pessoa e recebeu resultados. Sugira aprofundamentos.',
    person_details: 'O usuário viu o perfil completo. Sugira explorações adicionais (conexões, reputação, carreira).',
    person_professional: 'O usuário viu a carreira profissional. Sugira conexões, reputação ou redes sociais.',
    person_social: 'O usuário viu redes sociais. Sugira carreira profissional ou conexões empresariais.',
    person_reputation: 'O usuário viu notícias/reputação. Sugira perfil completo ou conexões.',
    person_connections: 'O usuário viu conexões empresariais. Sugira detalhes de alguma empresa ou perfil completo.',
    person_academic: 'O usuário viu informações acadêmicas. Sugira carreira profissional ou publicações.'
  };

  const context = contextMap[queryType] || 'O usuário fez uma consulta genérica sobre pessoas.';

  return `${context}

Gere exatamente 3 sugestões curtas (máximo 6 palavras cada) de perguntas que o usuário poderia fazer em seguida.
Responda APENAS com as 3 sugestões, uma por linha, sem numeração ou bullets.
As sugestões devem ser em português brasileiro.`;
}

export const DEFAULT_SUGGESTIONS = [
  'Buscar pessoa por nome',
  'Ver perfil profissional',
  'Conexões empresariais'
];

export const ERROR_MESSAGES = {
  NO_DATA: 'Não encontrei informações para essa pessoa. Tente fornecer mais detalhes como nome completo, empresa ou CPF.',
  DATABASE_ERROR: 'Desculpe, ocorreu um erro ao consultar os dados. Tente novamente em alguns instantes.',
  NOT_CONFIGURED: 'O People Agent não está configurado corretamente. Entre em contato com o administrador.',
  GENERAL_ERROR: 'Desculpe, ocorreu um erro inesperado. Tente reformular sua pergunta.'
};

export default {
  PEOPLE_AGENT_SYSTEM_PROMPT,
  buildResponsePrompt,
  buildSuggestionsPrompt,
  DEFAULT_SUGGESTIONS,
  ERROR_MESSAGES
};
