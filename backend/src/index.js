import 'dotenv/config';
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
});
