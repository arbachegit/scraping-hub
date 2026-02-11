/**
 * Structured logger for Node.js backend
 * Consistent with Python structlog pattern
 */

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
};

const currentLevel = LOG_LEVELS[process.env.LOG_LEVEL?.toUpperCase()] || LOG_LEVELS.INFO;

/**
 * Format log entry as structured JSON
 */
function formatLog(level, message, context = {}) {
  return JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    message,
    ...context,
    service: 'scraping-hub-backend'
  });
}

/**
 * Logger with structured output
 */
export const logger = {
  debug(message, context = {}) {
    if (currentLevel <= LOG_LEVELS.DEBUG) {
      console.log(formatLog('DEBUG', message, context));
    }
  },

  info(message, context = {}) {
    if (currentLevel <= LOG_LEVELS.INFO) {
      console.log(formatLog('INFO', message, context));
    }
  },

  warn(message, context = {}) {
    if (currentLevel <= LOG_LEVELS.WARN) {
      console.warn(formatLog('WARN', message, context));
    }
  },

  error(message, context = {}) {
    if (currentLevel <= LOG_LEVELS.ERROR) {
      // Extract error details if Error object provided
      if (context.error instanceof Error) {
        context.error = {
          message: context.error.message,
          stack: context.error.stack,
          name: context.error.name
        };
      }
      console.error(formatLog('ERROR', message, context));
    }
  },

  /**
   * Create child logger with bound context
   */
  child(baseContext) {
    return {
      debug: (msg, ctx = {}) => logger.debug(msg, { ...baseContext, ...ctx }),
      info: (msg, ctx = {}) => logger.info(msg, { ...baseContext, ...ctx }),
      warn: (msg, ctx = {}) => logger.warn(msg, { ...baseContext, ...ctx }),
      error: (msg, ctx = {}) => logger.error(msg, { ...baseContext, ...ctx })
    };
  }
};

/**
 * Express middleware for request logging
 */
export function requestLogger(req, res, next) {
  const startTime = Date.now();
  const requestId = Math.random().toString(36).substring(7);

  req.requestId = requestId;
  req.log = logger.child({ requestId, path: req.path, method: req.method });

  res.on('finish', () => {
    const duration = Date.now() - startTime;
    const level = res.statusCode >= 400 ? 'warn' : 'info';

    logger[level]('Request completed', {
      requestId,
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      duration_ms: duration
    });
  });

  next();
}

export default logger;
