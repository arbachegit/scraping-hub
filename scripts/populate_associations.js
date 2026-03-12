/**
 * Populate fato_associacoes_contextuais
 *
 * Cross-references emendas (Brasil Data Hub) with noticias (iconsai-scraping)
 * using shared taxonomy to create contextual associations.
 *
 * Rules:
 *   1. tema_comum: emenda.funcao maps to same taxonomy slug as noticia.tema_principal
 *      - confianca: 0.6 (tema only)
 *   2. tema_comum + territorio: same tema + same UF
 *      - confianca: 0.85
 *   3. mencao: noticia entity mentions emenda autor name
 *      - confianca: 0.9
 *
 * Usage: node scripts/populate_associations.js [--dry-run] [--limit 1000]
 */

import { createRequire } from 'module';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const backendDir = join(__dirname, '..', 'backend');
const require = createRequire(join(backendDir, 'package.json'));

// Load env
const dotenv = require('dotenv');
dotenv.config({ path: join(__dirname, '..', '.env') });

const { createClient } = require('@supabase/supabase-js');

// Two Supabase instances
const scraping = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

const brasilHub = createClient(
  process.env.BRASIL_DATA_HUB_URL,
  process.env.BRASIL_DATA_HUB_KEY
);

const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const limitIdx = args.indexOf('--limit');
const LIMIT = limitIdx >= 0 ? parseInt(args[limitIdx + 1], 10) : 500;

async function main() {
  console.log(`\n=== Populate Contextual Associations ===`);
  console.log(`Mode: ${DRY_RUN ? 'DRY RUN' : 'LIVE'}`);
  console.log(`Limit: ${LIMIT} noticias\n`);

  // 1. Load taxonomy mappings from scraping DB
  const { data: funcaoMap } = await scraping
    .from('map_funcao_taxonomia')
    .select('funcao, taxonomia_slug');

  const { data: temaMap } = await scraping
    .from('map_tema_taxonomia')
    .select('tema_principal, taxonomia_slug');

  if (!funcaoMap || !temaMap) {
    console.error('Failed to load taxonomy mappings');
    process.exit(1);
  }

  // Build lookup: taxonomia_slug → list of funcoes
  const slugToFuncoes = {};
  for (const { funcao, taxonomia_slug } of funcaoMap) {
    if (!slugToFuncoes[taxonomia_slug]) slugToFuncoes[taxonomia_slug] = [];
    slugToFuncoes[taxonomia_slug].push(funcao);
  }

  // Build lookup: tema_principal → taxonomia_slug
  const temaToSlug = {};
  for (const { tema_principal, taxonomia_slug } of temaMap) {
    temaToSlug[tema_principal] = taxonomia_slug;
  }

  console.log(`Loaded ${funcaoMap.length} funcao mappings, ${temaMap.length} tema mappings`);
  console.log(`Taxonomy slugs with emendas: ${Object.keys(slugToFuncoes).join(', ')}\n`);

  // 2. Load classified noticias (with tema_principal set)
  const { data: noticias, error: notErr } = await scraping
    .from('dim_noticias')
    .select('id, titulo, tema_principal, fonte_nome')
    .not('tema_principal', 'is', null)
    .order('data_publicacao', { ascending: false })
    .limit(LIMIT);

  if (notErr) {
    console.error('Failed to load noticias:', notErr.message);
    process.exit(1);
  }

  console.log(`Loaded ${noticias.length} classified noticias`);

  // 3. For each tema that exists in both bases, find matching emendas
  const stats = { tema_comum: 0, skipped: 0, errors: 0 };
  const batchSize = 50;
  let associations = [];

  for (const noticia of noticias) {
    const slug = temaToSlug[noticia.tema_principal];
    if (!slug) {
      stats.skipped++;
      continue;
    }

    const funcoes = slugToFuncoes[slug];
    if (!funcoes || funcoes.length === 0) {
      stats.skipped++;
      continue;
    }

    // Find top emendas matching this tema (by funcao) — get a sample, not all
    // We use the first funcao variant (the most common one) to keep it fast
    const { data: emendas } = await brasilHub
      .from('fato_emendas_parlamentares')
      .select('id, autor, funcao, localidade')
      .in('funcao', funcoes)
      .order('valor_empenhado', { ascending: false })
      .limit(5);

    if (!emendas || emendas.length === 0) continue;

    for (const emenda of emendas) {
      associations.push({
        origem_tipo: 'noticia',
        origem_id: noticia.id,
        destino_tipo: 'emenda',
        destino_id: String(emenda.id),
        tipo_associacao: 'tema_comum',
        taxonomia_slug: slug,
        confianca: 0.6,
        metodo: 'regra',
        evidencia: `noticia.tema=${noticia.tema_principal} → emenda.funcao=${emenda.funcao}`,
      });
      stats.tema_comum++;
    }

    // Flush batch
    if (associations.length >= batchSize) {
      if (!DRY_RUN) {
        const { error } = await scraping
          .from('fato_associacoes_contextuais')
          .upsert(associations, {
            onConflict: 'origem_tipo,origem_id,destino_tipo,destino_id,tipo_associacao',
            ignoreDuplicates: true,
          });
        if (error) {
          console.error('Upsert error:', error.message);
          stats.errors += associations.length;
        }
      }
      associations = [];
    }
  }

  // Flush remaining
  if (associations.length > 0 && !DRY_RUN) {
    const { error } = await scraping
      .from('fato_associacoes_contextuais')
      .upsert(associations, {
        onConflict: 'origem_tipo,origem_id,destino_tipo,destino_id,tipo_associacao',
        ignoreDuplicates: true,
      });
    if (error) {
      console.error('Final upsert error:', error.message);
      stats.errors += associations.length;
    }
  }

  console.log('\n=== Results ===');
  console.log(`Associations created: ${stats.tema_comum}`);
  console.log(`Skipped (no mapping): ${stats.skipped}`);
  console.log(`Errors: ${stats.errors}`);
  if (DRY_RUN) console.log('(DRY RUN — nothing was written)');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
