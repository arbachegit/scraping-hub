/**
 * People Agent - Intent Parser
 * Parses user messages in PT-BR to extract intent and named entities
 * for people search queries.
 */

import logger from '../utils/logger.js';

export const INTENTS = {
  SEARCH_PERSON: 'SEARCH_PERSON',
  PERSON_DETAILS: 'PERSON_DETAILS',
  PERSON_PROFESSIONAL: 'PERSON_PROFESSIONAL',
  PERSON_ACADEMIC: 'PERSON_ACADEMIC',
  PERSON_SOCIAL: 'PERSON_SOCIAL',
  PERSON_REPUTATION: 'PERSON_REPUTATION',
  PERSON_CONNECTIONS: 'PERSON_CONNECTIONS',
  FOLLOW_UP: 'FOLLOW_UP',
  GENERAL: 'GENERAL'
};

// Follow-up patterns (pronouns, references to previous context)
const FOLLOW_UP_PATTERNS = [
  /^(e |mas |tambem |também)\b/i,
  /\b(dele|dela|dessa pessoa|desse|dessa|do mesmo|da mesma)\b/i,
  /\b(mais (sobre|detalhes|informacoes|informações))\b/i,
  /\b(continua|continue|prossiga)\b/i,
  /^(sim|ok|isso|exato)\b/i
];

// Intent patterns - ordered by specificity (most specific first)
const PATTERNS = {
  person_connections: [
    /\b(empresas|companhias|negocios|negócios|sociedades)\s+(de|do|da|que)\b/i,
    /\b(socios|sócios|parceiros|associados)\s+(de|do|da)\b/i,
    /\b(conexoes|conexões|relacoes|relações|vinculos|vínculos)\s+(de|do|da)\b/i,
    /\b(onde|em que empresa)\s+(trabalh[ao]|atuo?[ua])\b/i
  ],
  person_reputation: [
    /\b(noticias|notícias|news)\s+(sobre|de|do|da)\b/i,
    /\b(reputacao|reputação|historico|histórico)\s+(de|do|da)\b/i,
    /\b(reclamacoes|reclamações|processos|acusacoes|acusações)\s+(de|do|da|contra)\b/i,
    /\b(o que (falam|dizem|publicam))\s+(sobre|de|do|da)\b/i
  ],
  person_social: [
    /\b(linkedin|github|twitter|instagram|redes\s*sociais?|perfil\s*(social|online))\s+(de|do|da)\b/i,
    /\b(linkedin|github|twitter|instagram)\b.*\b(de|do|da)\b/i,
    /\b(perfil|redes)\b/i
  ],
  person_academic: [
    /\b(formacao|formação|educacao|educação|academico|acadêmico|estudos|graduacao|graduação)\s+(de|do|da)\b/i,
    /\b(publicacoes|publicações|artigos|papers|pesquisas)\s+(de|do|da)\b/i,
    /\b(onde (estud|form))\b/i
  ],
  person_professional: [
    /\b(carreira|experiencia|experiência|trabalho|profissional|curriculum|currículo)\s+(de|do|da)\b/i,
    /\b(onde trabalh[ao]|cargo|funcao|função|posicao|posição)\s+(de|do|da)\b/i,
    /\b(historico|histórico)\s+(profissional|de carreira|de trabalho)\b/i
  ],
  person_details: [
    /\b(quem (e|é)|perfil (completo |)?(de|do|da)|tudo sobre|detalhes (de|do|da|sobre))\b/i,
    /\b(me (fale|conte|diga) (tudo |mais )?(sobre|de|do|da))\b/i,
    /\b(informacoes|informações) (completas |detalhadas |)?(de|do|da|sobre)\b/i
  ],
  search_person: [
    /\b(buscar|procurar|encontrar|pesquisar|achar)\s+(pessoa|alguem|alguém)\b/i,
    /\b(buscar|procurar|encontrar|pesquisar|achar)\s+/i,
    /\b(conhece|sabe quem (e|é))\b/i
  ]
};

// CPF pattern (11 digits with optional formatting)
const CPF_PATTERN = /\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b/;

// Email pattern
const EMAIL_PATTERN = /\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b/;

/**
 * Extract a person name from the message
 * Removes common prepositions, intent words, etc.
 */
function extractName(message) {
  let cleaned = message
    // Remove intent trigger words
    .replace(/\b(quem (e|é)|perfil (completo )?(de|do|da)|tudo sobre|detalhes (de|do|da|sobre))\b/gi, '')
    .replace(/\b(me (fale|conte|diga) (tudo |mais )?(sobre|de|do|da))\b/gi, '')
    .replace(/\b(buscar|procurar|encontrar|pesquisar|achar)\s+(pessoa\s+)?/gi, '')
    .replace(/\b(carreira|experiencia|experiência|trabalho|profissional|linkedin|github|noticias|notícias|empresas|conexoes|conexões|reputacao|reputação|formacao|formação)\s+(de|do|da)\b/gi, '')
    .replace(/\b(informacoes|informações)\s+(completas |detalhadas )?(de|do|da|sobre)\b/gi, '')
    .replace(/\b(redes\s*sociais?|perfil\s*(social|online))\s+(de|do|da)\b/gi, '')
    .replace(/\b(onde trabalh[ao]|cargo|funcao|função)\s+(de|do|da)\b/gi, '')
    .replace(/\b(historico|histórico)\s+(profissional|de carreira)?\s*(de|do|da)\b/gi, '')
    .replace(/\b(socios|sócios|parceiros)\s+(de|do|da)\b/gi, '')
    .replace(/\b(reclamacoes|reclamações|processos)\s+(de|do|da|contra)\b/gi, '')
    .replace(/\b(o que (falam|dizem))\s+(sobre|de|do|da)\b/gi, '')
    .replace(/\b(publicacoes|publicações|artigos)\s+(de|do|da)\b/gi, '')
    // Remove loose prepositions at start/end
    .replace(/^(de|do|da|o|a|os|as|um|uma|sobre|para|com|que|e)\s+/gi, '')
    .replace(/\s+(de|do|da|o|a|os|as)$/gi, '')
    // Remove CPF
    .replace(CPF_PATTERN, '')
    // Remove email
    .replace(EMAIL_PATTERN, '')
    // Clean whitespace
    .replace(/\s+/g, ' ')
    .trim();

  // Only return if it looks like a name (at least 2 chars, starts with letter)
  if (cleaned.length >= 2 && /^[a-zA-ZÀ-ÿ]/.test(cleaned)) {
    return cleaned;
  }

  return null;
}

/**
 * Extract CPF from message
 */
function extractCpf(message) {
  const match = message.match(CPF_PATTERN);
  if (match) {
    return match[1].replace(/[^\d]/g, '');
  }
  return null;
}

/**
 * Extract email from message
 */
function extractEmail(message) {
  const match = message.match(EMAIL_PATTERN);
  return match ? match[1] : null;
}

/**
 * Extract company name from message context
 */
function extractCompany(message) {
  const patterns = [
    /\b(?:da|de|na|em)\s+(?:empresa\s+)?([A-Z][A-Za-zÀ-ÿ\s&.]+(?:S\.?A\.?|Ltda\.?|LLC|Inc\.?|Corp\.?))/,
    /\b(?:empresa|companhia)\s+([A-Z][A-Za-zÀ-ÿ\s&.]+)/i
  ];

  for (const pattern of patterns) {
    const match = message.match(pattern);
    if (match) {
      return match[1].trim();
    }
  }

  return null;
}

/**
 * Extract city from message
 */
function extractCity(message) {
  const patterns = [
    /\b(?:de|em|na cidade de|em)\s+([A-Z][a-zÀ-ÿ]+(?:\s+[a-zÀ-ÿ]+)*(?:\s*[-/]\s*[A-Z]{2})?)/,
    /\b([A-Z][a-zÀ-ÿ]+(?:\s+[a-zÀ-ÿ]+)*)\s*[-/]\s*([A-Z]{2})\b/
  ];

  for (const pattern of patterns) {
    const match = message.match(pattern);
    if (match) {
      return match[0].replace(/^(de|em|na cidade de)\s+/i, '').trim();
    }
  }

  return null;
}

/**
 * Parse user message to extract intent and entities
 * @param {string} message - User message in PT-BR
 * @param {Object} context - Previous context (lastQuery, etc.)
 * @returns {Object} - { intent, entities, confidence, requiresLLM }
 */
export function parseIntent(message, context = {}) {
  const normalizedMessage = message.trim();

  // Extract entities regardless of intent
  const entities = {};

  const cpf = extractCpf(normalizedMessage);
  if (cpf) entities.cpf = cpf;

  const email = extractEmail(normalizedMessage);
  if (email) entities.email = email;

  const company = extractCompany(normalizedMessage);
  if (company) entities.empresa = company;

  const city = extractCity(normalizedMessage);
  if (city) entities.cidade = city;

  // Check follow-up first
  for (const pattern of FOLLOW_UP_PATTERNS) {
    if (pattern.test(normalizedMessage)) {
      const name = extractName(normalizedMessage);
      if (name) entities.nome = name;

      return {
        intent: INTENTS.FOLLOW_UP,
        entities,
        confidence: 0.7,
        requiresLLM: false
      };
    }
  }

  // Check patterns in priority order
  const intentOrder = [
    'person_connections',
    'person_reputation',
    'person_social',
    'person_academic',
    'person_professional',
    'person_details',
    'search_person'
  ];

  const intentMap = {
    person_connections: INTENTS.PERSON_CONNECTIONS,
    person_reputation: INTENTS.PERSON_REPUTATION,
    person_social: INTENTS.PERSON_SOCIAL,
    person_academic: INTENTS.PERSON_ACADEMIC,
    person_professional: INTENTS.PERSON_PROFESSIONAL,
    person_details: INTENTS.PERSON_DETAILS,
    search_person: INTENTS.SEARCH_PERSON
  };

  for (const key of intentOrder) {
    for (const pattern of PATTERNS[key]) {
      if (pattern.test(normalizedMessage)) {
        const name = extractName(normalizedMessage);
        if (name) entities.nome = name;

        return {
          intent: intentMap[key],
          entities,
          confidence: 0.8,
          requiresLLM: false
        };
      }
    }
  }

  // No pattern matched - try to extract a name and default to search/details
  const name = extractName(normalizedMessage);
  if (name) {
    entities.nome = name;

    // If message is just a name (possibly with CPF), treat as details request
    const isJustName = normalizedMessage.replace(CPF_PATTERN, '').replace(EMAIL_PATTERN, '').trim() === name;

    return {
      intent: isJustName ? INTENTS.PERSON_DETAILS : INTENTS.SEARCH_PERSON,
      entities,
      confidence: 0.5,
      requiresLLM: true
    };
  }

  // CPF only → search
  if (cpf) {
    return {
      intent: INTENTS.SEARCH_PERSON,
      entities,
      confidence: 0.7,
      requiresLLM: false
    };
  }

  // Nothing matched
  return {
    intent: INTENTS.GENERAL,
    entities,
    confidence: 0.3,
    requiresLLM: true
  };
}

/**
 * Format parsed intent as string for LLM consumption
 * @param {Object} parsedIntent - Result from parseIntent
 * @returns {string}
 */
export function formatIntentForLLM(parsedIntent) {
  const { intent, entities, confidence } = parsedIntent;
  const parts = [`Intent: ${intent} (confiança: ${(confidence * 100).toFixed(0)}%)`];

  if (entities.nome) parts.push(`Nome: ${entities.nome}`);
  if (entities.cpf) parts.push(`CPF: ***${entities.cpf.slice(-4)}`);
  if (entities.email) parts.push(`Email: ${entities.email}`);
  if (entities.empresa) parts.push(`Empresa: ${entities.empresa}`);
  if (entities.cidade) parts.push(`Cidade: ${entities.cidade}`);

  return parts.join(' | ');
}

export default {
  parseIntent,
  formatIntentForLLM,
  INTENTS
};
