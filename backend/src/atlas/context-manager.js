/**
 * Atlas Context Manager
 * Manages conversational context and session storage for Atlas agent.
 */

import { randomUUID } from 'crypto';
import logger from '../utils/logger.js';

// Session TTL in milliseconds (default: 30 minutes)
const SESSION_TTL = (parseInt(process.env.ATLAS_SESSION_TTL, 10) || 1800) * 1000;

// In-memory session storage
const sessions = new Map();

// Cleanup interval (every 5 minutes)
const CLEANUP_INTERVAL = 5 * 60 * 1000;

/**
 * Session structure
 * @typedef {Object} Session
 * @property {string} id - Session ID
 * @property {Object|null} lastQuery - Last query result
 * @property {Array} conversationHistory - Message history
 * @property {Object} resolvedEntities - Entities from context
 * @property {Date} createdAt - Creation timestamp
 * @property {Date} lastActivity - Last activity timestamp
 */

/**
 * Create a new session
 * @returns {Session}
 */
function createSession() {
  const session = {
    id: randomUUID(),
    lastQuery: null,
    conversationHistory: [],
    resolvedEntities: {},
    createdAt: new Date(),
    lastActivity: new Date()
  };

  sessions.set(session.id, session);

  logger.debug('Session created', { sessionId: session.id });

  return session;
}

/**
 * Get or create session
 * @param {string|null} sessionId - Existing session ID or null
 * @returns {Session}
 */
export function getOrCreateSession(sessionId) {
  if (sessionId && sessions.has(sessionId)) {
    const session = sessions.get(sessionId);

    // Check if session is expired
    const now = new Date();
    const elapsed = now - session.lastActivity;

    if (elapsed > SESSION_TTL) {
      logger.debug('Session expired', { sessionId, elapsed });
      sessions.delete(sessionId);
      return createSession();
    }

    // Update last activity
    session.lastActivity = now;
    return session;
  }

  return createSession();
}

/**
 * Get session by ID
 * @param {string} sessionId - Session ID
 * @returns {Session|null}
 */
export function getSession(sessionId) {
  if (!sessionId || !sessions.has(sessionId)) {
    return null;
  }

  const session = sessions.get(sessionId);
  const now = new Date();
  const elapsed = now - session.lastActivity;

  if (elapsed > SESSION_TTL) {
    sessions.delete(sessionId);
    return null;
  }

  return session;
}

/**
 * Add message to conversation history
 * @param {string} sessionId - Session ID
 * @param {string} role - 'user' or 'assistant'
 * @param {string} content - Message content
 */
export function addMessage(sessionId, role, content) {
  const session = sessions.get(sessionId);
  if (!session) return;

  session.conversationHistory.push({
    role,
    content,
    timestamp: new Date()
  });

  // Keep only last 20 messages to prevent memory bloat
  if (session.conversationHistory.length > 20) {
    session.conversationHistory = session.conversationHistory.slice(-20);
  }

  session.lastActivity = new Date();
}

/**
 * Update last query result
 * @param {string} sessionId - Session ID
 * @param {Object} queryResult - Query result to store
 */
export function updateLastQuery(sessionId, queryResult) {
  const session = sessions.get(sessionId);
  if (!session) return;

  session.lastQuery = {
    intent: queryResult.intent,
    entities: queryResult.entities,
    results: queryResult.data,
    timestamp: new Date()
  };

  // Update resolved entities from results
  if (queryResult.data) {
    const data = queryResult.data;

    // If single politician result, store for reference
    if (data.politico) {
      session.resolvedEntities.currentPolitician = {
        id: data.politico.id,
        nome: data.politico.nome_completo || data.politico.nome_urna
      };
    } else if (Array.isArray(data) && data.length === 1) {
      // Single result from search
      const p = data[0];
      session.resolvedEntities.currentPolitician = {
        id: p.id,
        nome: p.nome_completo || p.nome_urna
      };
    }

    // Store municipality if in results
    if (data.municipio) {
      session.resolvedEntities.currentMunicipality = data.municipio;
    }

    // Store party if in results
    if (data.partido || queryResult.entities?.partido) {
      session.resolvedEntities.currentParty = data.partido || queryResult.entities.partido;
    }
  }

  session.lastActivity = new Date();
}

/**
 * Resolve pronouns and references using context
 * @param {Object} entities - Parsed entities
 * @param {Session} session - Current session
 * @returns {Object} - Entities with resolved references
 */
export function resolveReferences(entities, session) {
  if (!session) return entities;

  const resolved = { ...entities };

  // Check for pronoun references
  // If no explicit politician mentioned but context has one
  if (!resolved.nome && !resolved.id && session.resolvedEntities.currentPolitician) {
    resolved.id = session.resolvedEntities.currentPolitician.id;
    resolved.nome = session.resolvedEntities.currentPolitician.nome;
  }

  // Resolve municipality references
  if (!resolved.municipio && session.resolvedEntities.currentMunicipality) {
    resolved.municipio = session.resolvedEntities.currentMunicipality;
  }

  // Resolve party references
  if (!resolved.partido && session.resolvedEntities.currentParty) {
    resolved.partido = session.resolvedEntities.currentParty;
  }

  return resolved;
}

/**
 * Get conversation context for LLM
 * @param {string} sessionId - Session ID
 * @param {number} maxMessages - Maximum messages to include
 * @returns {Array} - Recent conversation messages
 */
export function getConversationContext(sessionId, maxMessages = 6) {
  const session = sessions.get(sessionId);
  if (!session) return [];

  return session.conversationHistory.slice(-maxMessages);
}

/**
 * Clear session
 * @param {string} sessionId - Session ID
 */
export function clearSession(sessionId) {
  if (sessions.has(sessionId)) {
    sessions.delete(sessionId);
    logger.debug('Session cleared', { sessionId });
  }
}

/**
 * Get session stats (for debugging)
 * @returns {Object}
 */
export function getStats() {
  return {
    activeSessions: sessions.size,
    sessionTtl: SESSION_TTL / 1000
  };
}

/**
 * Cleanup expired sessions
 */
function cleanupExpiredSessions() {
  const now = new Date();
  let cleaned = 0;

  for (const [sessionId, session] of sessions.entries()) {
    const elapsed = now - session.lastActivity;
    if (elapsed > SESSION_TTL) {
      sessions.delete(sessionId);
      cleaned++;
    }
  }

  if (cleaned > 0) {
    logger.debug('Expired sessions cleaned', { cleaned, remaining: sessions.size });
  }
}

// Start cleanup interval
setInterval(cleanupExpiredSessions, CLEANUP_INTERVAL);

export default {
  getOrCreateSession,
  getSession,
  addMessage,
  updateLastQuery,
  resolveReferences,
  getConversationContext,
  clearSession,
  getStats
};
