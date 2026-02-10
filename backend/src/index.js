import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load .env from parent directory (project root)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '../../.env') });

import express from 'express';
import cors from 'cors';
import companiesRouter from './routes/companies.js';

const app = express();
const PORT = process.env.BACKEND_PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Routes (nginx strips /api/ prefix, so use /companies directly)
app.use('/companies', companiesRouter);

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'iconsai-scraping-backend',
    timestamp: new Date().toISOString(),
    apollo_configured: !!process.env.APOLLO_API_KEY
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
  console.log(`Backend running on port ${PORT}`);
  console.log(`Health: http://localhost:${PORT}/health`);
  console.log(`Apollo API Key: ${process.env.APOLLO_API_KEY ? 'configured' : 'NOT configured'}`);
});
