/**
 * Atlas Intent Parser
 * Parses user messages to extract intent and entities for political data queries.
 * Uses pattern matching first, with LLM fallback for complex queries.
 */

import logger from '../utils/logger.js';

/**
 * Intent types for political data queries
 */
export const INTENTS = {
  SEARCH_POLITICIAN: 'search_politician',
  POLITICIAN_DETAILS: 'politician_details',
  BY_PARTY: 'by_party',
  BY_MUNICIPALITY: 'by_municipality',
  STATISTICS: 'statistics',
  PARTY_LIST: 'party_list',
  COMPARE: 'compare',
  FOLLOW_UP: 'follow_up',
  GENERAL: 'general'
};

/**
 * Common Brazilian political party acronyms
 */
const PARTY_ACRONYMS = [
  'PT', 'PSDB', 'MDB', 'PMDB', 'PL', 'PP', 'PDT', 'PSB', 'PSOL', 'PCdoB',
  'PSD', 'REPUBLICANOS', 'UNIÃO', 'CIDADANIA', 'PODEMOS', 'PSC', 'AVANTE',
  'SOLIDARIEDADE', 'PTB', 'PSL', 'DEM', 'PPS', 'PRB', 'PROS', 'REDE',
  'NOVO', 'PATRIOTA', 'PMN', 'PV', 'PC DO B', 'DC', 'PCB', 'PSTU', 'PCO'
];

/**
 * Common political positions
 */
const POSITIONS = [
  'PREFEITO', 'PREFEITA', 'VEREADOR', 'VEREADORA', 'DEPUTADO', 'DEPUTADA',
  'SENADOR', 'SENADORA', 'GOVERNADOR', 'GOVERNADORA', 'PRESIDENTE',
  'VICE-PREFEITO', 'VICE-PREFEITA', 'VICE-GOVERNADOR', 'VICE-GOVERNADORA',
  'DEPUTADO FEDERAL', 'DEPUTADO ESTADUAL', 'DEPUTADA FEDERAL', 'DEPUTADA ESTADUAL'
];

/**
 * Patterns for intent detection
 */
const PATTERNS = {
  // Search politician by name
  searchPolitician: [
    /quem\s+(?:é|eh|e)\s+(?:o\s+|a\s+)?(.+?)\??$/i,
    /(?:buscar?|procurar?|encontrar?|pesquisar?)\s+(?:o\s+|a\s+)?(?:político|politico|candidato|deputado|vereador|prefeito|senador)\s+(.+?)(?:\?|$)/i,
    /(?:informações?|informacoes?|dados?)\s+(?:sobre|do|da|de)\s+(?:o\s+|a\s+)?(.+?)(?:\?|$)/i,
    /(?:me\s+)?(?:fale?|conte?|diga?)\s+(?:sobre|do|da|de)\s+(?:o\s+|a\s+)?(.+?)(?:\?|$)/i
  ],

  // Get politician details (usually follow-up)
  politicianDetails: [
    /(?:mais\s+)?(?:detalhes?|informações?|informacoes?)\s+(?:sobre|do|da|dele|dela)(?:\s+(.+?))?(?:\?|$)/i,
    /(?:quero\s+)?saber\s+mais\s+(?:sobre|do|da|dele|dela)(?:\s+(.+?))?(?:\?|$)/i,
    /(?:qual|quais)\s+(?:é|eh|e|são|sao)\s+(?:o|os|a|as)\s+(?:mandatos?|cargos?|partidos?)\s+(?:d[eo]|da)\s+(.+?)(?:\?|$)/i
  ],

  // By party
  byParty: [
    /(?:políticos?|politicos?|candidatos?|deputados?|vereadores?|eleitos?)\s+d[oa]\s+(PT|PSDB|MDB|PL|PP|PDT|PSB|PSOL|PSD|REPUBLICANOS|UNIÃO|NOVO|[A-Z]{2,})\b/i,
    /(?:quem\s+é|quem\s+são|quais\s+são)\s+(?:os\s+)?(?:políticos?|candidatos?|eleitos?)\s+d[oa]\s+(PT|PSDB|MDB|PL|PP|PDT|PSB|PSOL|PSD|REPUBLICANOS|UNIÃO|NOVO|[A-Z]{2,})\b/i,
    /(?:membros?|integrantes?|filiados?)\s+d[oa]\s+(PT|PSDB|MDB|PL|PP|PDT|PSB|PSOL|PSD|REPUBLICANOS|UNIÃO|NOVO|[A-Z]{2,})\b/i,
    /(?:mostrar?|listar?|exibir?)\s+(?:os\s+)?(?:políticos?|candidatos?)\s+d[oa]\s+(PT|PSDB|MDB|PL|PP|PDT|PSB|PSOL|PSD|REPUBLICANOS|UNIÃO|NOVO|[A-Z]{2,})\b/i
  ],

  // By municipality
  byMunicipality: [
    /(?:políticos?|politicos?|vereadores?|prefeitos?|deputados?|candidatos?|eleitos?)\s+(?:de|em|no|na)\s+(.+?)(?:\?|$)/i,
    /(?:quem\s+(?:são|sao)|quais\s+(?:são|sao))\s+(?:os\s+)?(?:políticos?|vereadores?|eleitos?)\s+(?:de|em)\s+(.+?)(?:\?|$)/i,
    /(?:câmara|camara)\s+(?:de\s+)?(?:vereadores?\s+)?(?:de|em)\s+(.+?)(?:\?|$)/i,
    /(?:prefeito|prefeita)\s+(?:de|em|d[oa])\s+(.+?)(?:\?|$)/i
  ],

  // Statistics
  statistics: [
    /(?:quantos?|quantas?)\s+(?:políticos?|candidatos?|deputados?|vereadores?|eleitos?)/i,
    /(?:total|número|numero|quantidade)\s+(?:de\s+)?(?:políticos?|candidatos?|deputados?|eleitos?)/i,
    /(?:estatísticas?|estatisticas?|números?|numeros?)\s+(?:de|do|da|sobre)/i,
    /(?:qual|quais)\s+(?:é|são|sao)\s+(?:o|os)\s+(?:partido|partidos?)\s+(?:com\s+)?(?:mais|maior)/i
  ],

  // Party list
  partyList: [
    /(?:quais?|listar?|mostrar?|exibir?)\s+(?:são\s+)?(?:os\s+)?partidos?(?:\s+(?:existentes?|políticos?|cadastrados?))?/i,
    /(?:lista|listagem)\s+(?:de\s+)?partidos?/i,
    /partidos?\s+(?:políticos?|existentes?|no\s+brasil)?/i
  ],

  // Follow-up patterns (reference to previous context)
  followUp: [
    /^(?:e\s+)?(?:ele|ela|esse|essa|este|esta|o\s+mesmo|a\s+mesma)/i,
    /^(?:e\s+)?(?:quantos?|quantas?|qual|quais|quando|onde|como)/i,
    /(?:mais\s+sobre|continua|prossiga|e\s+depois|e\s+então)/i,
    /^(?:sim|ok|certo|continua|prossiga)/i
  ]
};

/**
 * Extract year from message
 * @param {string} message - User message
 * @returns {number|null} - Year if found
 */
function extractYear(message) {
  const yearMatch = message.match(/\b(19\d{2}|20[0-3]\d)\b/);
  if (yearMatch) {
    const year = parseInt(yearMatch[1], 10);
    if (year >= 1990 && year <= 2030) {
      return year;
    }
  }
  return null;
}

/**
 * Extract party acronym from message
 * @param {string} message - User message
 * @returns {string|null} - Party acronym if found
 */
function extractParty(message) {
  const upperMessage = message.toUpperCase();
  for (const party of PARTY_ACRONYMS) {
    // Match party as whole word
    const regex = new RegExp(`\\b${party}\\b`, 'i');
    if (regex.test(upperMessage)) {
      return party;
    }
  }
  return null;
}

/**
 * Extract position/cargo from message
 * @param {string} message - User message
 * @returns {string|null} - Position if found
 */
function extractPosition(message) {
  const upperMessage = message.toUpperCase();
  for (const position of POSITIONS) {
    if (upperMessage.includes(position)) {
      return position;
    }
  }
  return null;
}

/**
 * Extract election status from message
 * @param {string} message - User message
 * @returns {boolean|null} - Elected status if mentioned
 */
function extractElectedStatus(message) {
  const lowerMessage = message.toLowerCase();
  if (/\beleitos?\b/.test(lowerMessage) || /\bfoi\s+eleito\b/.test(lowerMessage)) {
    return true;
  }
  if (/\bnão\s+eleitos?\b/.test(lowerMessage) || /\bperdeu\b/.test(lowerMessage)) {
    return false;
  }
  return null;
}

/**
 * Clean and extract politician name from message
 * @param {string} rawName - Raw name from pattern match
 * @returns {string} - Cleaned name
 */
function cleanName(rawName) {
  if (!rawName) return '';

  return rawName
    .trim()
    .replace(/[?!.,;:]+$/, '')  // Remove trailing punctuation
    .replace(/\s+/g, ' ')       // Normalize whitespace
    .replace(/^(o|a|os|as)\s+/i, '')  // Remove articles
    .trim();
}

/**
 * Parse user message to extract intent and entities
 * @param {string} message - User message
 * @param {Object} context - Current conversation context
 * @returns {Object} - Parsed intent and entities
 */
export function parseIntent(message, context = {}) {
  const startTime = Date.now();
  const normalizedMessage = message.trim();

  // Default result
  const result = {
    intent: INTENTS.GENERAL,
    entities: {},
    confidence: 0,
    requiresLLM: false
  };

  // Extract common entities regardless of intent
  const year = extractYear(normalizedMessage);
  const party = extractParty(normalizedMessage);
  const position = extractPosition(normalizedMessage);
  const elected = extractElectedStatus(normalizedMessage);

  if (year) result.entities.ano_eleicao = year;
  if (party) result.entities.partido = party;
  if (position) result.entities.cargo = position;
  if (elected !== null) result.entities.eleito = elected;

  // Check for follow-up patterns first (needs context)
  if (context.lastQuery) {
    for (const pattern of PATTERNS.followUp) {
      if (pattern.test(normalizedMessage)) {
        result.intent = INTENTS.FOLLOW_UP;
        result.confidence = 0.7;
        // Merge with previous entities
        result.entities = { ...context.lastQuery.entities, ...result.entities };
        break;
      }
    }
  }

  // Check party list patterns
  if (result.intent === INTENTS.GENERAL) {
    for (const pattern of PATTERNS.partyList) {
      if (pattern.test(normalizedMessage)) {
        result.intent = INTENTS.PARTY_LIST;
        result.confidence = 0.9;
        break;
      }
    }
  }

  // Check statistics patterns
  if (result.intent === INTENTS.GENERAL) {
    for (const pattern of PATTERNS.statistics) {
      if (pattern.test(normalizedMessage)) {
        result.intent = INTENTS.STATISTICS;
        result.confidence = 0.85;
        break;
      }
    }
  }

  // Check by party patterns
  if (result.intent === INTENTS.GENERAL) {
    for (const pattern of PATTERNS.byParty) {
      const match = normalizedMessage.match(pattern);
      if (match) {
        result.intent = INTENTS.BY_PARTY;
        result.entities.partido = match[1]?.toUpperCase() || party;
        result.confidence = 0.9;
        break;
      }
    }
  }

  // Check by municipality patterns
  if (result.intent === INTENTS.GENERAL) {
    for (const pattern of PATTERNS.byMunicipality) {
      const match = normalizedMessage.match(pattern);
      if (match) {
        const municipio = cleanName(match[1]);
        // Don't treat years as municipalities
        if (municipio && !/^\d{4}$/.test(municipio)) {
          result.intent = INTENTS.BY_MUNICIPALITY;
          result.entities.municipio = municipio;
          result.confidence = 0.85;
          break;
        }
      }
    }
  }

  // Check politician details patterns
  if (result.intent === INTENTS.GENERAL) {
    for (const pattern of PATTERNS.politicianDetails) {
      const match = normalizedMessage.match(pattern);
      if (match) {
        result.intent = INTENTS.POLITICIAN_DETAILS;
        if (match[1]) {
          result.entities.nome = cleanName(match[1]);
        }
        result.confidence = 0.8;
        break;
      }
    }
  }

  // Check search politician patterns
  if (result.intent === INTENTS.GENERAL) {
    for (const pattern of PATTERNS.searchPolitician) {
      const match = normalizedMessage.match(pattern);
      if (match) {
        result.intent = INTENTS.SEARCH_POLITICIAN;
        result.entities.nome = cleanName(match[1]);
        result.confidence = 0.9;
        break;
      }
    }
  }

  // If still general intent but has party entity, assume by_party
  if (result.intent === INTENTS.GENERAL && result.entities.partido) {
    result.intent = INTENTS.BY_PARTY;
    result.confidence = 0.6;
  }

  // If still general intent and has municipality, assume by_municipality
  if (result.intent === INTENTS.GENERAL && result.entities.municipio) {
    result.intent = INTENTS.BY_MUNICIPALITY;
    result.confidence = 0.6;
  }

  // Low confidence = suggest LLM fallback
  if (result.confidence < 0.5) {
    result.requiresLLM = true;
  }

  const processingTime = Date.now() - startTime;
  logger.debug('Intent parsed', {
    message: normalizedMessage.substring(0, 50),
    intent: result.intent,
    confidence: result.confidence,
    entities: result.entities,
    processingTime
  });

  return result;
}

/**
 * Format intent result for LLM prompt
 * @param {Object} parsedIntent - Result from parseIntent
 * @returns {string} - Formatted string for LLM
 */
export function formatIntentForLLM(parsedIntent) {
  const parts = [`Intent: ${parsedIntent.intent}`];

  if (Object.keys(parsedIntent.entities).length > 0) {
    parts.push(`Entities: ${JSON.stringify(parsedIntent.entities)}`);
  }

  parts.push(`Confidence: ${parsedIntent.confidence}`);

  return parts.join('\n');
}

export default {
  parseIntent,
  formatIntentForLLM,
  INTENTS
};
