/**
 * IconsAI Scraping Backend - Node.js
 * Business Intelligence Brasil
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import pino from 'pino';
import dotenv from 'dotenv';

import companyRoutes from './routes/companies.js';
import peopleRoutes from './routes/people.js';
import competitorRoutes from './routes/competitors.js';

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

dotenv.config({ path: join(__dirname, '../../.env') });

const logger = pino({
  transport: {
    target: 'pino-pretty',
    options: { colorize: true }
  }
});

const app = express();
const PORT = process.env.BACKEND_PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Request logging
app.use((req, res, next) => {
  logger.info({ method: req.method, url: req.url }, 'Request');
  next();
});

// Routes
app.use('/api/v2/company', companyRoutes);
app.use('/api/v2/people', peopleRoutes);
app.use('/api/v2/competitors', competitorRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Error handler
app.use((err, req, res, next) => {
  logger.error({ error: err.message, stack: err.stack }, 'Error');
  res.status(500).json({ error: err.message });
});

app.listen(PORT, () => {
  logger.info(`Backend Node.js running on port ${PORT}`);
});

export default app;
