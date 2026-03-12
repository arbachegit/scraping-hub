#!/usr/bin/env node

/**
 * Standalone script: Batch classify all unclassified news.
 *
 * Usage:
 *   node scripts/classify_news_batch.js                  # default: 10 batches × 25
 *   node scripts/classify_news_batch.js --max 50         # 50 batches × 25 = 1250 articles
 *   node scripts/classify_news_batch.js --max 0          # unlimited — process ALL
 *   node scripts/classify_news_batch.js --max 20 --size 40  # 20 batches × 40
 *
 * Requires: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY in .env
 */

/**
 * This script must be run from the project root or backend/ directory.
 * The service itself loads .env via supabase.js dotenv.config().
 *
 * Run: cd backend && node ../scripts/classify_news_batch.js --max 0
 *  or: node -e "..." from backend/
 */
import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const backendDir = resolve(__dirname, '../backend');

// Load dotenv from backend's node_modules
const require = createRequire(join(backendDir, 'package.json'));
const dotenv = require('dotenv');
dotenv.config({ path: resolve(__dirname, '../.env') });

const { runClassificationPipeline, countUnclassified } = await import(
  join(backendDir, 'src/services/news-classifier.js')
);

function parseArgs() {
  const args = process.argv.slice(2);
  let maxBatches = 10;
  let batchSize = 25;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--max' && args[i + 1] !== undefined) {
      maxBatches = parseInt(args[i + 1], 10);
      i++;
    }
    if (args[i] === '--size' && args[i + 1] !== undefined) {
      batchSize = parseInt(args[i + 1], 10);
      i++;
    }
  }

  return { maxBatches, batchSize };
}

async function main() {
  const { maxBatches, batchSize } = parseArgs();

  console.log('=== News Classification Pipeline ===');
  console.log(`Model: ${process.env.ANTHROPIC_CLASSIFIER_MODEL || 'claude-haiku-4-5-20251001'}`);

  const unclassified = await countUnclassified();
  console.log(`Unclassified: ${unclassified.toLocaleString()}`);
  console.log(`Batches: ${maxBatches === 0 ? 'unlimited' : maxBatches} × ${batchSize}`);
  console.log('');

  if (unclassified === 0) {
    console.log('All news are already classified!');
    process.exit(0);
  }

  const stats = await runClassificationPipeline({
    maxBatches,
    batchSize,
    onProgress: (s) => {
      const pct = ((s.classified / s.total_unclassified) * 100).toFixed(1);
      process.stdout.write(
        `\r  Batch ${s.batches_processed} | Classified: ${s.classified} (${pct}%) | Errors: ${s.errors}`
      );
    },
  });

  console.log('\n');
  console.log('=== Results ===');
  console.log(`Classified: ${stats.classified}`);
  console.log(`Errors: ${stats.errors}`);
  console.log(`Batches: ${stats.batches_processed}`);
  console.log(`Remaining: ${stats.remaining?.toLocaleString()}`);
  console.log(`Duration: ${stats.started_at} → ${stats.finished_at}`);

  process.exit(stats.errors > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
