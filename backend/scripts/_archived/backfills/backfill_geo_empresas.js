/**
 * Backfill geo data for dim_empresas
 *
 * Preenche codigo_ibge, codigo_ibge_uf, latitude, longitude
 *
 * Estrategia:
 *   1. Busca empresas com codigo_ibge NULL e CEP preenchido
 *   2. Para cada CEP unico, chama BrasilAPI CEP → obtem city + state
 *   3. Match city+state com geo_municipios (brasil-data-hub) → codigo_ibge, lat, lng
 *   4. Update dim_empresas em batch
 *
 * Features:
 *   - Cache persistente em disco (resume se interromper)
 *   - Concurrency limitada (20 requests paralelos)
 *   - Rate limiting com exponential backoff
 *   - Relatorio detalhado
 *
 * Usage: cd backend && node scripts/backfill_geo_empresas.js
 *        cd backend && node scripts/backfill_geo_empresas.js --dry-run
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, writeFileSync, existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '../../.env') });

// Clients
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const brasilDataHub = createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY, {
  db: { schema: 'staging' }
});

// Config
const PAGE_SIZE = 1000;
const CONCURRENT = 20;
const DRY_RUN = process.argv.includes('--dry-run');
const CACHE_FILE = join(__dirname, '.cep_cache.json');

// Caches
const municipioByNomeCache = new Map(); // "nome_lower|SIGLA" → { codigo_ibge, lat, lng }
let cepCache = {}; // "CEP" → { city, state } ou null

/**
 * Carrega cache de CEP do disco
 */
function loadCepCache() {
  if (existsSync(CACHE_FILE)) {
    try {
      cepCache = JSON.parse(readFileSync(CACHE_FILE, 'utf8'));
      console.log(`[INFO] Cache de CEP carregado: ${Object.keys(cepCache).length} entradas`);
    } catch {
      cepCache = {};
    }
  }
}

/**
 * Salva cache de CEP no disco
 */
function saveCepCache() {
  writeFileSync(CACHE_FILE, JSON.stringify(cepCache), 'utf8');
}

/**
 * Carrega geo_municipios + geo_estados em cache
 */
async function preloadMunicipios() {
  console.log('[INFO] Carregando estados...');
  const { data: estados } = await brasilDataHub.from('geo_estados').select('id, codigo_ibge_uf, sigla');
  const estadoById = new Map();
  for (const est of estados || []) {
    estadoById.set(est.id, est);
  }
  console.log(`[INFO] ${estadoById.size} estados carregados`);

  console.log('[INFO] Carregando municipios...');
  let allMunicipios = [];
  let offset = 0;

  while (true) {
    const { data, error } = await brasilDataHub
      .from('geo_municipios')
      .select('codigo_ibge, nome, estado_id, latitude, longitude')
      .range(offset, offset + 999);

    if (error || !data || data.length === 0) break;
    allMunicipios = allMunicipios.concat(data);
    offset += 1000;
    if (data.length < 1000) break;
  }

  for (const mun of allMunicipios) {
    const estado = estadoById.get(mun.estado_id);
    if (!estado) continue;

    const entry = {
      codigo_ibge: mun.codigo_ibge,
      sigla: estado.sigla,
      latitude: mun.latitude,
      longitude: mun.longitude
    };

    // Indexar por nome_lower|SIGLA
    municipioByNomeCache.set(`${mun.nome.toLowerCase()}|${estado.sigla}`, entry);
  }

  console.log(`[INFO] ${allMunicipios.length} municipios carregados`);
  return allMunicipios.length;
}

/**
 * Busca CEP na BrasilAPI com retry
 */
async function fetchCep(cep) {
  const clean = cep.replace(/[^\d]/g, '');
  if (clean.length !== 8) return null;

  // Cache hit
  if (cepCache[clean] !== undefined) return cepCache[clean];

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const resp = await fetch(`https://brasilapi.com.br/api/cep/v1/${clean}`, {
        headers: { 'User-Agent': 'IconsAI-Backfill/1.0' },
        signal: AbortSignal.timeout(10000)
      });

      if (resp.status === 404) {
        cepCache[clean] = null;
        return null;
      }

      if (resp.status === 429) {
        // Rate limited - wait and retry
        const wait = Math.pow(2, attempt) * 2000;
        console.log(`[RATE] CEP ${clean} rate limited, aguardando ${wait}ms...`);
        await new Promise(r => setTimeout(r, wait));
        continue;
      }

      if (!resp.ok) {
        cepCache[clean] = null;
        return null;
      }

      const data = await resp.json();
      const result = { city: data.city, state: data.state };
      cepCache[clean] = result;
      return result;
    } catch {
      if (attempt < 2) {
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
      }
    }
  }

  cepCache[clean] = null;
  return null;
}

/**
 * Resolve CEP → codigo_ibge via BrasilAPI + geo_municipios
 */
function resolveCepToIbge(cepData) {
  if (!cepData?.city || !cepData?.state) return null;

  const key = `${cepData.city.toLowerCase()}|${cepData.state}`;
  return municipioByNomeCache.get(key) || null;
}

/**
 * Processa um batch de CEPs em paralelo (com limite de concurrency)
 */
async function fetchCepsBatch(ceps) {
  const results = new Map();
  const queue = [...ceps];

  const workers = Array.from({ length: Math.min(CONCURRENT, queue.length) }, async () => {
    while (queue.length > 0) {
      const cep = queue.pop();
      if (!cep) break;
      const result = await fetchCep(cep);
      results.set(cep.replace(/[^\d]/g, ''), result);
    }
  });

  await Promise.all(workers);
  return results;
}

/**
 * Executa o backfill
 */
async function main() {
  console.log('='.repeat(60));
  console.log('  BACKFILL GEO EMPRESAS');
  console.log(`  Mode: ${DRY_RUN ? 'DRY RUN (sem escrita)' : 'PRODUCAO'}`);
  console.log('='.repeat(60));
  console.log();

  // Carregar caches
  loadCepCache();
  const totalMunicipios = await preloadMunicipios();
  if (totalMunicipios === 0) {
    console.error('[ERRO] Nenhum municipio encontrado. Abortando.');
    process.exit(1);
  }

  // Contadores
  const stats = {
    total: 0,
    ja_completas: 0,
    atualizadas: 0,
    sem_cep: 0,
    cep_nao_encontrado: 0,
    municipio_nao_match: 0,
    erros: 0,
    cep_api_calls: 0,
    cep_cache_hits: 0
  };

  // Paginar empresas que precisam de geo data
  let offset = 0;
  let hasMore = true;
  let saveCounter = 0;

  while (hasMore) {
    const { data: empresas, error } = await supabase
      .from('dim_empresas')
      .select('id, cnpj, cep, codigo_ibge, codigo_ibge_uf, latitude, longitude')
      .is('codigo_ibge', null)
      .not('cep', 'is', null)
      .neq('cep', '')
      .range(offset, offset + PAGE_SIZE - 1)
      .order('id');

    if (error) {
      console.error(`[ERRO] Falha ao buscar empresas (offset ${offset}):`, error.message);
      // Salvar cache e sair graciosamente
      saveCepCache();
      break;
    }

    if (!empresas || empresas.length === 0) {
      hasMore = false;
      break;
    }

    stats.total += empresas.length;
    const lote = Math.floor(offset / PAGE_SIZE) + 1;
    console.log(`[INFO] Lote ${lote}: ${empresas.length} empresas (offset ${offset})`);

    // Coletar CEPs unicos do lote que nao estao no cache
    const cepsToFetch = new Set();
    for (const e of empresas) {
      const clean = e.cep.replace(/[^\d]/g, '');
      if (clean.length === 8 && cepCache[clean] === undefined) {
        cepsToFetch.add(clean);
      }
    }

    // Buscar CEPs na BrasilAPI
    if (cepsToFetch.size > 0) {
      stats.cep_api_calls += cepsToFetch.size;
      console.log(`  [API] Buscando ${cepsToFetch.size} CEPs na BrasilAPI...`);
      await fetchCepsBatch([...cepsToFetch]);
    }

    const cacheHits = empresas.length - cepsToFetch.size;
    stats.cep_cache_hits += cacheHits;

    // Processar e gerar updates
    const updates = [];

    for (const empresa of empresas) {
      const clean = empresa.cep.replace(/[^\d]/g, '');

      if (clean.length !== 8) {
        stats.sem_cep++;
        continue;
      }

      const cepData = cepCache[clean];
      if (!cepData) {
        stats.cep_nao_encontrado++;
        continue;
      }

      const geo = resolveCepToIbge(cepData);
      if (!geo) {
        stats.municipio_nao_match++;
        continue;
      }

      const codigoIbge = String(geo.codigo_ibge);
      const codigoIbgeUf = codigoIbge.substring(0, 2);

      updates.push({
        id: empresa.id,
        update: {
          codigo_ibge: codigoIbge,
          codigo_ibge_uf: codigoIbgeUf,
          latitude: geo.latitude,
          longitude: geo.longitude
        },
        cnpj: empresa.cnpj
      });
    }

    // Batch update no Supabase
    if (updates.length > 0 && !DRY_RUN) {
      for (let j = 0; j < updates.length; j += CONCURRENT) {
        const chunk = updates.slice(j, j + CONCURRENT);
        const promises = chunk.map(item =>
          supabase.from('dim_empresas').update(item.update).eq('id', item.id)
        );

        const results = await Promise.all(promises);
        for (const res of results) {
          if (res.error) {
            stats.erros++;
          } else {
            stats.atualizadas++;
          }
        }
      }
    } else {
      stats.atualizadas += updates.length;
      if (updates.length > 0 && DRY_RUN) {
        const sample = updates.slice(0, 3);
        for (const item of sample) {
          console.log(`  [DRY] ${item.cnpj} → ibge:${item.update.codigo_ibge} lat:${item.update.latitude} lng:${item.update.longitude}`);
        }
        if (updates.length > 3) {
          console.log(`  [DRY] ... +${updates.length - 3} updates`);
        }
      }
    }

    // Salvar cache periodicamente
    saveCounter++;
    if (saveCounter % 10 === 0) {
      saveCepCache();
      console.log(`  [CACHE] Salvo: ${Object.keys(cepCache).length} CEPs`);
    }

    if (empresas.length < PAGE_SIZE) {
      hasMore = false;
    }

    offset += PAGE_SIZE;
  }

  // Salvar cache final
  saveCepCache();

  // Contar empresas sem CEP (estrangeiras, etc)
  const { data: semCepData } = await supabase
    .from('dim_empresas')
    .select('id')
    .is('codigo_ibge', null)
    .or('cep.is.null,cep.eq.')
    .limit(1);
  const temSemCep = semCepData && semCepData.length > 0;

  // Relatorio final
  console.log();
  console.log('='.repeat(60));
  console.log('  RELATORIO FINAL');
  console.log('='.repeat(60));
  console.log(`  Empresas processadas:     ${stats.total}`);
  console.log(`  Atualizadas:              ${stats.atualizadas}`);
  console.log(`  CEP nao encontrado:       ${stats.cep_nao_encontrado}`);
  console.log(`  Municipio sem match:      ${stats.municipio_nao_match}`);
  console.log(`  Sem CEP valido:           ${stats.sem_cep}`);
  console.log(`  Erros:                    ${stats.erros}`);
  console.log();
  console.log('  BrasilAPI:');
  console.log(`    Chamadas API:           ${stats.cep_api_calls}`);
  console.log(`    Cache hits:             ${stats.cep_cache_hits}`);
  console.log(`    Total cache:            ${Object.keys(cepCache).length} CEPs`);

  if (stats.total > 0) {
    const cobertura = ((stats.atualizadas / stats.total) * 100).toFixed(1);
    console.log();
    console.log(`  Cobertura: ${cobertura}%`);
  }

  if (temSemCep) {
    console.log();
    console.log('  [NOTA] Existem empresas sem CEP (provavelmente estrangeiras).');
    console.log('         Estas nao podem ser geocodificadas por CEP.');
  }

  if (DRY_RUN) {
    console.log();
    console.log('  [DRY RUN] Nenhuma alteracao salva. Rode sem --dry-run para aplicar.');
  }

  console.log('='.repeat(60));
}

main().catch(err => {
  // Salvar cache mesmo em caso de erro
  saveCepCache();
  console.error('[FATAL]', err);
  process.exit(1);
});
