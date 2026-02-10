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
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`);
  console.log(`Health: http://localhost:${PORT}/health`);
  console.log(`Apollo API Key: ${process.env.APOLLO_API_KEY ? 'configured' : 'NOT configured'}`);
});
