/**
 * Fix stats_historico - comprehensive data repair
 *
 * Strategy: Linear interpolation from last natural data (Feb 3)
 * to today's actual snapshot (Feb 24) for Feb 4-23.
 *
 * Natural daily growth (Jan 26-Feb 3):
 *   empresas:  ~1,814/day
 *   pessoas:   ~682/day
 *   politicos: ~146/day
 *   mandatos:  ~329/day
 *
 * Usage: cd backend && node scripts/fix_stats_historico.js
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '../../.env') });

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

async function upsert(date, categoria, total) {
  const { error } = await supabase
    .from('stats_historico')
    .upsert({ data: date, categoria, total }, { onConflict: 'data,categoria' });
  if (error) console.error(`  ERROR ${date}/${categoria}:`, error.message);
}

async function main() {
  console.log('=== Fix stats_historico (comprehensive) ===\n');

  // 1. Fetch current data
  const { data: allData, error } = await supabase
    .from('stats_historico')
    .select('*')
    .order('data', { ascending: true });

  if (error) { console.error('Fetch error:', error.message); process.exit(1); }

  const byCategory = {};
  for (const row of allData) {
    if (!byCategory[row.categoria]) byCategory[row.categoria] = {};
    byCategory[row.categoria][row.data] = row.total;
  }

  const categories = ['empresas', 'pessoas', 'politicos', 'mandatos', 'noticias'];

  // 2. For each category, get anchor points
  for (const cat of categories) {
    const data = byCategory[cat] || {};
    console.log(`--- ${cat} ---`);

    const feb3 = data['2026-02-03'] ?? 0;
    const feb24 = data['2026-02-24'] ?? 0;

    console.log(`  Anchor Feb 3:  ${feb3.toLocaleString()}`);
    console.log(`  Anchor Feb 24: ${feb24.toLocaleString()}`);

    if (cat === 'noticias') {
      console.log('  Noticias: all zeros, skipping\n');
      continue;
    }

    // 3. Linear interpolation Feb 4 through Feb 23
    // Feb 3 = day 0, Feb 24 = day 21
    const totalDays = 21; // Feb 3 to Feb 24
    const dailyGrowth = (feb24 - feb3) / totalDays;

    console.log(`  Daily growth: +${Math.round(dailyGrowth).toLocaleString()}/day`);

    for (let day = 1; day <= 20; day++) { // day 1 = Feb 4, day 20 = Feb 23
      const date = new Date('2026-02-03');
      date.setUTCDate(date.getUTCDate() + day);
      const dateStr = date.toISOString().split('T')[0];

      const interpolated = Math.round(feb3 + dailyGrowth * day);
      await upsert(dateStr, cat, interpolated);
    }

    // Show some sample values
    const feb4 = Math.round(feb3 + dailyGrowth * 1);
    const feb14 = Math.round(feb3 + dailyGrowth * 11);
    const feb23 = Math.round(feb3 + dailyGrowth * 20);
    console.log(`  Feb 4:  ${feb4.toLocaleString()}`);
    console.log(`  Feb 14: ${feb14.toLocaleString()}`);
    console.log(`  Feb 23: ${feb23.toLocaleString()}`);
    console.log(`  Feb 24: ${feb24.toLocaleString()} (actual)`);
    console.log('');
  }

  // 4. Verify
  console.log('=== Verification (Feb 3-7 + Feb 22-24) ===\n');

  const { data: verify } = await supabase
    .from('stats_historico')
    .select('*')
    .or('data.gte.2026-02-03,data.lte.2026-02-07,data.gte.2026-02-22')
    .in('data', ['2026-02-03','2026-02-04','2026-02-05','2026-02-06','2026-02-07','2026-02-22','2026-02-23','2026-02-24'])
    .order('data', { ascending: true });

  for (const row of (verify || [])) {
    console.log(`  ${row.data} | ${row.categoria.padEnd(10)} | ${row.total.toLocaleString()}`);
  }

  console.log('\n=== Done ===');
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
