/**
 * DELETE all fabricated stats_historico data (Feb 4-23).
 * Keep ONLY real data:
 *   - Jan 26 - Feb 3: real snapshots from previous system
 *   - Feb 24+: real snapshots from current system
 *
 * Usage: cd backend && node scripts/cleanup_fake_stats.js
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '../../.env') });

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

async function main() {
  console.log('=== Cleanup fabricated stats_historico data ===\n');

  // 1. Show what exists BEFORE deletion
  const { data: before } = await supabase
    .from('stats_historico')
    .select('data, categoria, total')
    .order('data', { ascending: true });

  const dates = [...new Set((before || []).map(r => r.data))].sort();
  console.log(`Total rows before: ${(before || []).length}`);
  console.log(`Date range: ${dates[0]} → ${dates[dates.length - 1]}`);
  console.log(`Total unique dates: ${dates.length}\n`);

  // 2. Identify fabricated dates (Feb 4 through Feb 23)
  const fakeDates = dates.filter(d => d >= '2026-02-04' && d <= '2026-02-23');
  console.log(`Fabricated dates to DELETE: ${fakeDates.length} days`);
  console.log(`  ${fakeDates[0]} → ${fakeDates[fakeDates.length - 1]}\n`);

  // 3. DELETE fabricated data
  for (const date of fakeDates) {
    const { error } = await supabase
      .from('stats_historico')
      .delete()
      .eq('data', date);

    if (error) {
      console.error(`  ERROR deleting ${date}:`, error.message);
    } else {
      process.stdout.write('.');
    }
  }
  console.log(' done\n');

  // 4. Show what remains
  const { data: after } = await supabase
    .from('stats_historico')
    .select('data, categoria, total')
    .order('data', { ascending: true });

  console.log('=== Remaining REAL data ===\n');

  const remainingDates = [...new Set((after || []).map(r => r.data))].sort();
  console.log(`Total rows after: ${(after || []).length}`);
  console.log(`Remaining dates: ${remainingDates.length}\n`);

  // Group by date for display
  for (const date of remainingDates) {
    const rows = (after || []).filter(r => r.data === date);
    const cols = rows.map(r => `${r.categoria}=${r.total.toLocaleString()}`).join(' | ');
    console.log(`  ${date}: ${cols}`);
  }

  console.log('\n=== Cleanup complete ===');
  console.log('Only real snapshot data remains.');
  console.log('Future snapshots will be created automatically by the dashboard.');
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
