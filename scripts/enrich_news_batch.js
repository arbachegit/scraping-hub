#!/usr/bin/env node

/**
 * Standalone script: Batch enrich classified news (signals + entities + relevance).
 *
 * Usage:
 *   node scripts/enrich_news_batch.js                  # default: 10 batches × 15
 *   node scripts/enrich_news_batch.js --max 50         # 50 batches × 15 = 750 articles
 *   node scripts/enrich_news_batch.js --max 0          # unlimited — process ALL classified
 *   node scripts/enrich_news_batch.js --max 20 --size 20
 *
 * Prerequisites: Run classify_news_batch.js first (enricher needs tipo_classificacao).
 * Requires: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY in .env
 */

import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const backendDir = resolve(__dirname, '../backend');

const require = createRequire(join(backendDir, 'package.json'));
const dotenv = require('dotenv');
dotenv.config({ path: resolve(__dirname, '../.env') });

const { runEnrichmentPipeline, countUnenriched } = await import(
  join(backendDir, 'src/services/news-enricher.js')
);

function parseArgs() {
  const args = process.argv.slice(2);
  let maxBatches = 10;
  let batchSize = 15;

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

  console.log('=== News Enrichment Pipeline ===');
  console.log('Sections: Signal Detection + Entity Extraction + Relevance Scoring');
  console.log(`Model: ${process.env.ANTHROPIC_ENRICHER_MODEL || 'claude-haiku-4-5-20251001'}`);

  const unenriched = await countUnenriched();
  console.log(`Unenriched (classified but not enriched): ${unenriched.toLocaleString()}`);
  console.log(`Batches: ${maxBatches === 0 ? 'unlimited' : maxBatches} × ${batchSize}`);
  console.log('');

  if (unenriched === 0) {
    console.log('All classified news are already enriched!');
    process.exit(0);
  }

  const stats = await runEnrichmentPipeline({
    maxBatches,
    batchSize,
    onProgress: (s) => {
      const pct = ((s.updated / s.total_unenriched) * 100).toFixed(1);
      process.stdout.write(
        `\r  Batch ${s.batches_processed} | Updated: ${s.updated} (${pct}%) | Signals: ${s.signals_inserted} | Entities: ${s.entities_linked} | Errors: ${s.errors}`
      );
    },
  });

  console.log('\n');
  console.log('=== Results ===');
  console.log(`Updated: ${stats.updated}`);
  console.log(`Signals inserted: ${stats.signals_inserted}`);
  console.log(`Entities linked: ${stats.entities_linked}`);
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
