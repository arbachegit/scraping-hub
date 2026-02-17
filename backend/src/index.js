import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load .env from parent directory (project root)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '../../.env') });

import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import companiesRouter from './routes/companies.js';
import peopleRouter from './routes/people.js';
import newsRouter from './routes/news.js';
import politiciansRouter from './routes/politicians.js';
import geoRouter from './routes/geo.js';
import { logger, requestLogger } from './utils/logger.js';

const app = express();
const PORT = process.env.BACKEND_PORT || 3001;

// Rate limiter - 100 requests per minute per IP
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100,
  message: { error: 'Muitas requisições. Tente novamente em 1 minuto.' },
  standardHeaders: true,
  legacyHeaders: false
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(requestLogger);
app.use('/companies', limiter);
app.use('/people', limiter);
app.use('/news', limiter);
app.use('/politicians', limiter);
app.use('/geo', limiter);

// Routes (nginx strips /api/ prefix, so use /companies directly)
app.use('/companies', companiesRouter);
app.use('/people', peopleRouter);
app.use('/news', newsRouter);
app.use('/politicians', politiciansRouter);
app.use('/geo', geoRouter);

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'iconsai-scraping-backend',
    timestamp: new Date().toISOString(),
    git_sha: process.env.GIT_SHA || 'unknown',
    build_date: process.env.BUILD_DATE || 'unknown',
    apollo_configured: !!process.env.APOLLO_API_KEY,
    fiscal_configured: !!(process.env.FISCAL_SUPABASE_URL && process.env.FISCAL_SUPABASE_KEY),
    brasil_data_hub_configured: !!(process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY)
  });
});

// Version endpoint for deployment verification
app.get('/version', (req, res) => {
  res.json({
    version: process.env.npm_package_version || '1.0.0',
    git_sha: process.env.GIT_SHA || 'unknown',
    build_date: process.env.BUILD_DATE || 'unknown',
    service: 'iconsai-scraping-backend'
  });
});

// Apollo test endpoint
app.get('/test-apollo', async (req, res) => {
  try {
    const apiKey = process.env.APOLLO_API_KEY;
    if (!apiKey) {
      return res.json({ error: 'Apollo API key not configured' });
    }

    const response = await fetch('https://api.apollo.io/v1/mixed_companies/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'X-Api-Key': apiKey
      },
      body: JSON.stringify({
        q_organization_name: 'Petrobras',
        organization_locations: ['Brazil'],
        page: 1,
        per_page: 1
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return res.json({ error: `Apollo API error: ${response.status}`, details: errorText });
    }

    const data = await response.json();
    const org = data.organizations?.[0];
    res.json({
      success: true,
      found: data.organizations?.length || 0,
      sample: org ? { name: org.name, linkedin: org.linkedin_url, website: org.website_url } : null
    });
  } catch (error) {
    res.json({ error: error.message });
  }
});

// Start server
app.listen(PORT, () => {
  logger.info('Backend started', {
    port: PORT,
    apollo_configured: !!process.env.APOLLO_API_KEY,
    cnpja_configured: !!process.env.CNPJA_API_KEY,
    perplexity_configured: !!process.env.PERPLEXITY_API_KEY
  });
});
