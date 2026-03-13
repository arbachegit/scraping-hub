import { Router } from 'express';
import { createClient } from '@supabase/supabase-js';
import logger from '../utils/logger.js';
import { escapeLike } from '../utils/sanitize.js';
import {
  validateQuery,
  validateParams,
  listEmendasSchema,
  searchEmendasSchema,
  timeSeriesEmendasSchema,
  listEmendasSubnacionaisSchema,
  emendasAnomaliesSchema,
  emendasNetworkSchema,
  integerIdParamSchema
} from '../validation/schemas.js';

const router = Router();

// Cliente Supabase para brasil-data-hub (fato_emendas_parlamentares)
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
  : null;

// Cliente Supabase para iconsai-scraping (noticias, taxonomia, associações)
const scrapingDb = process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_KEY
  ? createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY)
  : null;

/**
 * GET /api/emendas/list
 * List emendas with pagination and optional filters
 */
router.get('/list', validateQuery(listEmendasSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Query params already validated and transformed by Zod
    const { limit, offset, autor, uf, ano, tipo } = req.query;

    let query = brasilDataHub
      .from('fato_emendas_parlamentares')
      .select('*', { count: 'exact' })
      .order('ano', { ascending: false })
      .range(offset, offset + limit - 1);

    // All query params already validated and sanitized by Zod
    if (autor) {
      query = query.ilike('autor', `%${escapeLike(autor)}%`);
    }
    if (uf) {
      query = query.eq('uf', uf);
    }
    if (ano) {
      query = query.eq('ano', ano);
    }
    if (tipo) {
      query = query.ilike('tipo', `%${escapeLike(tipo)}%`);
    }

    const { data, error, count } = await query;

    if (error) {
      logger.error('Error listing emendas', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: count,
      emendas: data || []
    });

  } catch (error) {
    logger.error('Error listing emendas', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/search
 * Search emendas by text (autor, funcao, localidade, etc.)
 */
router.get('/search', validateQuery(searchEmendasSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Query params already validated by Zod (q >= 2 chars, sanitized)
    const { q, limit } = req.query;

    // Hybrid search: buscar_emendas (v2) → search_emendas_ranked_v1 (v1) → ilike fallback
    let data, error, count;

    const { data: rpcData, error: rpcError } = await brasilDataHub.rpc('buscar_emendas', {
      p_query: q,
      p_limit: limit,
    });

    if (!rpcError && rpcData) {
      data = rpcData;
      count = rpcData.length;
      error = null;
    } else if (rpcError && (rpcError.code === '42883' || rpcError.code === 'PGRST202')) {
      // buscar_emendas not yet deployed — try v1 fallback
      logger.warn('buscar_emendas not found, falling back to v1', { code: rpcError.code });
      const { data: v1Data, error: v1Error } = await brasilDataHub.rpc('search_emendas_ranked_v1', {
        p_query: q,
        p_limit: limit,
      });
      if (!v1Error && v1Data) {
        data = v1Data;
        count = v1Data.length;
        error = null;
      } else {
        // Final fallback: ilike
        const escaped = escapeLike(q);
        const result = await brasilDataHub
          .from('fato_emendas_parlamentares')
          .select('*', { count: 'exact' })
          .or(`autor.ilike.%${escaped}%,funcao.ilike.%${escaped}%,localidade.ilike.%${escaped}%`)
          .order('ano', { ascending: false })
          .limit(limit);
        data = result.data;
        error = result.error;
        count = result.data?.length || 0;
      }
    } else {
      if (rpcError) {
        logger.warn('buscar_emendas failed, falling back to ilike', { error: rpcError.message });
      }
      const escaped = escapeLike(q);
      const result = await brasilDataHub
        .from('fato_emendas_parlamentares')
        .select('*', { count: 'exact' })
        .or(`autor.ilike.%${escaped}%,funcao.ilike.%${escaped}%,localidade.ilike.%${escaped}%`)
        .order('ano', { ascending: false })
        .limit(limit);
      data = result.data;
      error = result.error;
      count = result.data?.length || 0;
    }

    if (error) {
      logger.error('Error searching emendas', { error: error.message, query: q.replace(/[\r\n]/g, ' ') });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: data?.length || 0,
      query: q,
      emendas: data || []
    });

  } catch (error) {
    logger.error('Error searching emendas', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/aggregation
 * Context Intelligence: aggregated stats across all 4 emendas tables.
 *
 * RPCs answer contextual questions:
 *  - get_emendas_context_totals → "Qual é o panorama?"
 *  - get_emendas_beneficiary_focus → "Pra quem vai o dinheiro?"
 *  - get_emendas_top_funcoes → "Onde mais se investe?"
 *  - get_emendas_context_top_autores → "Quem mais direciona?"
 *  - get_emendas_top_destinos → "Pra onde vai?"
 *  - get_emendas_by_tipo_emenda → "Qual o perfil?"
 *  - get_emendas_mecanismos → "Como o dinheiro flui?"
 */
router.get('/aggregation', async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({ success: false, error: 'Brasil Data Hub not configured.' });
    }

    // All 7 context RPCs in parallel
    const [totals, beneficiaries, funcoes, autores, destinos, tipos, mecanismos] = await Promise.all([
      brasilDataHub.rpc('get_emendas_context_totals'),
      brasilDataHub.rpc('get_emendas_beneficiary_focus'),
      brasilDataHub.rpc('get_emendas_top_funcoes', { p_limit: 10 }),
      brasilDataHub.rpc('get_emendas_context_top_autores', { p_limit: 10 }),
      brasilDataHub.rpc('get_emendas_top_destinos', { p_limit: 10 }),
      brasilDataHub.rpc('get_emendas_by_tipo_emenda'),
      brasilDataHub.rpc('get_emendas_mecanismos'),
    ]);

    // Check for RPC errors
    const rpcErrors = [totals, beneficiaries, funcoes, autores, destinos, tipos, mecanismos]
      .filter(r => r.error);

    if (rpcErrors.length > 0) {
      const firstError = rpcErrors[0].error;
      logger.warn('Emendas context RPCs failed', {
        failed: rpcErrors.length,
        code: firstError.code,
        message: firstError.message,
      });

      // If RPCs don't exist yet, return minimal fallback
      if (firstError.code === '42883' || firstError.code === 'PGRST202') {
        const { count } = await brasilDataHub
          .from('fato_emendas_parlamentares')
          .select('*', { count: 'exact', head: true });

        return res.json({
          success: true,
          rpc_available: false,
          totals: { total_emendas: count || 0 },
          beneficiaries: [],
          top_funcoes: [],
          top_autores: [],
          top_destinos: [],
          by_tipo: [],
          mecanismos: null,
        });
      }
    }

    res.json({
      success: true,
      rpc_available: true,
      totals: totals.data || {},
      beneficiaries: beneficiaries.data || [],
      top_funcoes: funcoes.data || [],
      top_autores: autores.data || [],
      top_destinos: destinos.data || [],
      by_tipo: tipos.data || [],
      mecanismos: mecanismos.data || null,
    });
  } catch (error) {
    logger.error('Error getting emendas aggregation', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/time-series
 * Context Intelligence: temporal evolution of budget execution.
 *
 * Answers: "Como evolui o orçamento ao longo dos anos?"
 * Optional filters: funcao, uf, autor, tipo_emenda
 */
router.get('/time-series', validateQuery(timeSeriesEmendasSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({ success: false, error: 'Brasil Data Hub not configured.' });
    }

    // Query params already validated and trimmed by Zod
    const { funcao, uf, autor, tipo_emenda } = req.query;

    const [general, byFuncao, concentration] = await Promise.all([
      brasilDataHub.rpc('get_emendas_time_series', {
        p_funcao: funcao || null,
        p_uf: uf || null,
        p_autor: autor || null,
        p_tipo_emenda: tipo_emenda || null,
      }),
      brasilDataHub.rpc('get_emendas_funcao_time_series', { p_limit: 8 }),
      brasilDataHub.rpc('get_emendas_concentration'),
    ]);

    // Check if RPCs exist
    const rpcErrors = [general, byFuncao, concentration].filter(r => r.error);
    if (rpcErrors.length > 0) {
      const firstError = rpcErrors[0].error;
      if (firstError.code === '42883' || firstError.code === 'PGRST202') {
        return res.json({ success: true, rpc_available: false, series: [], by_funcao: [], concentration: null });
      }
    }

    res.json({
      success: true,
      rpc_available: true,
      series: general.data || [],
      by_funcao: byFuncao.data || [],
      concentration: concentration.data || null,
    });
  } catch (error) {
    logger.error('Error getting emendas time series', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/subnacionais
 * List subnational emendas (estaduais + municipais) with filters
 */
router.get('/subnacionais', validateQuery(listEmendasSubnacionaisSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured.'
      });
    }

    // All query params (including esfera) validated and trimmed by Zod
    const { limit, offset, autor, uf, ano, tipo, esfera } = req.query;

    let query = brasilDataHub
      .from('fato_emendas_subnacionais')
      .select('*', { count: 'exact' })
      .order('ano', { ascending: false })
      .range(offset, offset + limit - 1);

    if (autor) query = query.ilike('autor', `%${escapeLike(autor)}%`);
    if (uf) query = query.eq('uf', uf);
    if (ano) query = query.eq('ano', ano);
    if (tipo) query = query.ilike('tipo', `%${escapeLike(tipo)}%`);
    if (esfera) query = query.eq('esfera', esfera);

    const { data, error, count } = await query;

    if (error) {
      logger.error('Error listing subnacional emendas', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count,
      emendas: data || []
    });
  } catch (error) {
    logger.error('Error listing subnacional emendas', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/anomalies
 * Context Intelligence: detect outlier emendas.
 *
 * Answers: "Quais emendas merecem atenção?"
 * Types: taxa_execucao (Z-score), valor_empenhado (IQR), concentracao_autor
 */
router.get('/anomalies', validateQuery(emendasAnomaliesSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({ success: false, error: 'Brasil Data Hub not configured.' });
    }

    const { min_zscore, iqr_factor, limit } = req.query;

    const { data, error } = await brasilDataHub.rpc('get_emendas_anomalies', {
      p_min_zscore: min_zscore,
      p_iqr_factor: iqr_factor,
      p_limit: limit,
    });

    if (error) {
      // RPC not deployed yet
      if (error.code === '42883' || error.code === 'PGRST202') {
        return res.json({ success: true, rpc_available: false, execucao: [], valor: [], concentracao: [] });
      }
      logger.error('Error getting emendas anomalies', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      rpc_available: true,
      ...(data || { execucao: [], valor: [], concentracao: [] }),
    });
  } catch (error) {
    logger.error('Error getting emendas anomalies', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/:id/context
 * Context Intelligence: related news, taxonomy, and associations for an emenda.
 * Connects emenda (Brasil Data Hub) with noticias (scraping DB) via shared taxonomy.
 */
router.get('/:id/context', validateParams(integerIdParamSchema), async (req, res) => {
  try {
    if (!brasilDataHub || !scrapingDb) {
      return res.status(503).json({ success: false, error: 'Database clients not configured.' });
    }

    const { id } = req.params;

    // 1. Get emenda + parallel context queries from Brasil Data Hub
    const { data: emenda, error: emendaErr } = await brasilDataHub
      .from('fato_emendas_parlamentares')
      .select('id, autor, funcao, subfuncao, localidade, tipo_emenda, ano, codigo_emenda, numero_emenda, partido, codigo_ibge, is_emenda_pix, valor_empenhado, valor_liquidado, valor_pago, valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago')
      .eq('id', id)
      .single();

    if (emendaErr || !emenda) {
      return res.status(404).json({ success: false, error: 'Emenda not found' });
    }

    // 2. Parallel: taxonomy + favorecidos + author history + associations
    const [mappingResult, favorecidosResult, autorHistoryResult] = await Promise.all([
      // Taxonomy mapping
      scrapingDb
        .from('map_funcao_taxonomia')
        .select('taxonomia_slug')
        .eq('funcao', emenda.funcao)
        .single(),
      // Top beneficiaries for this emenda's author + funcao combo
      brasilDataHub
        .from('fato_emendas_favorecidos')
        .select('tipo_favorecido, favorecido, uf_favorecido, municipio_favorecido, valor_recebido')
        .eq('codigo_emenda', emenda.codigo_emenda)
        .order('valor_recebido', { ascending: false })
        .limit(10),
      // Author time series (try RPC, ignore error)
      brasilDataHub.rpc('get_emendas_autor_time_series', { p_autor: emenda.autor }),
    ]);

    const taxonomiaSlug = mappingResult.data?.taxonomia_slug || null;

    // 3. Get taxonomy info
    let taxonomia = null;
    if (taxonomiaSlug) {
      const { data } = await scrapingDb
        .from('dim_taxonomia_tematica')
        .select('slug, nome, cor, icone')
        .eq('slug', taxonomiaSlug)
        .single();
      taxonomia = data;
    }

    // 4. Get pre-computed associations for this emenda
    const { data: associations } = await scrapingDb
      .from('fato_associacoes_contextuais')
      .select('origem_id, tipo_associacao, confianca, evidencia')
      .eq('destino_tipo', 'emenda')
      .eq('destino_id', String(id))
      .eq('origem_tipo', 'noticia')
      .order('confianca', { ascending: false })
      .limit(10);

    // 5. Fetch the actual noticias for those associations
    let noticias = [];
    if (associations && associations.length > 0) {
      const noticiaIds = associations.map(a => a.origem_id);
      const { data } = await scrapingDb
        .from('dim_noticias')
        .select('id, titulo, resumo, fonte_nome, data_publicacao, tema_principal, url')
        .in('id', noticiaIds)
        .order('data_publicacao', { ascending: false });
      noticias = data || [];
    }

    // 6. If no pre-computed associations, fallback: find noticias by same tema
    if (noticias.length === 0 && taxonomiaSlug) {
      const { data: temaMapping } = await scrapingDb
        .from('map_tema_taxonomia')
        .select('tema_principal')
        .eq('taxonomia_slug', taxonomiaSlug);

      if (temaMapping && temaMapping.length > 0) {
        const temas = temaMapping.map(t => t.tema_principal);
        const { data } = await scrapingDb
          .from('dim_noticias')
          .select('id, titulo, resumo, fonte_nome, data_publicacao, tema_principal, url')
          .in('tema_principal', temas)
          .order('data_publicacao', { ascending: false })
          .limit(5);
        noticias = data || [];
      }
    }

    // 7. Compute execution context for this emenda
    const valorEmpenhado = emenda.valor_empenhado || 0;
    const valorPago = emenda.valor_pago || 0;
    const taxaExecucao = valorEmpenhado > 0 ? Math.round((valorPago / valorEmpenhado) * 1000) / 10 : 0;
    const restoAPagar = (emenda.valor_resto_inscrito || 0) - (emenda.valor_resto_cancelado || 0) - (emenda.valor_resto_pago || 0);

    res.json({
      success: true,
      emenda_id: id,
      // Factual summary
      resumo: {
        autor: emenda.autor,
        partido: emenda.partido || null,
        funcao: emenda.funcao,
        subfuncao: emenda.subfuncao || null,
        tipo_emenda: emenda.tipo_emenda,
        localidade: emenda.localidade,
        ano: emenda.ano,
        is_pix: emenda.is_emenda_pix || false,
        codigo_ibge: emenda.codigo_ibge || null,
      },
      // Execution context
      execucao: {
        empenhado: valorEmpenhado,
        liquidado: emenda.valor_liquidado || 0,
        pago: valorPago,
        resto_a_pagar: restoAPagar,
        taxa_execucao: taxaExecucao,
      },
      // Taxonomy
      taxonomia,
      // Beneficiaries (top 10 for this emenda)
      favorecidos: (favorecidosResult.data || []).map(f => ({
        tipo: f.tipo_favorecido,
        nome: f.favorecido,
        uf: f.uf_favorecido,
        municipio: f.municipio_favorecido,
        valor: f.valor_recebido,
      })),
      // Author time series (may be null if RPC not deployed)
      autor_historico: autorHistoryResult.error ? null : (autorHistoryResult.data || []),
      // Related news
      associations_count: associations?.length || 0,
      noticias,
    });
  } catch (error) {
    logger.error('Error getting emenda context', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/:id
 * Get single emenda by ID
 */
router.get('/:id', validateParams(integerIdParamSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // ID already validated as integer by Zod
    const { id } = req.params;

    const { data: emenda, error } = await brasilDataHub
      .from('fato_emendas_parlamentares')
      .select('*')
      .eq('id', id)
      .single();

    if (error || !emenda) {
      return res.status(404).json({ success: false, error: 'Emenda not found' });
    }

    res.json({
      success: true,
      emenda
    });

  } catch (error) {
    logger.error('Error getting emenda', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/emendas/:id/network
 * Context Intelligence: graph neighborhood of an emenda.
 *
 * Answers: "O que está conectado a esta emenda?"
 * Returns: politico (autor), favorecidos, noticias, taxonomia — as graph nodes + edges.
 */
router.get('/:id/network', validateParams(integerIdParamSchema), validateQuery(emendasNetworkSchema), async (req, res) => {
  try {
    if (!brasilDataHub || !scrapingDb) {
      return res.status(503).json({ success: false, error: 'Database clients not configured.' });
    }

    const { id } = req.params;
    const { hops } = req.query;

    // 1. Get the emenda
    const { data: emenda, error: emendaErr } = await brasilDataHub
      .from('fato_emendas_parlamentares')
      .select('id, autor, funcao, subfuncao, localidade, tipo_emenda, ano, codigo_emenda, politico_id, valor_empenhado, valor_pago')
      .eq('id', id)
      .single();

    if (emendaErr || !emenda) {
      return res.status(404).json({ success: false, error: 'Emenda not found' });
    }

    const nodes = [];
    const edges = [];

    // Center node: the emenda itself
    nodes.push({
      id: `emenda:${emenda.id}`,
      type: 'emenda',
      label: `${emenda.autor} - ${emenda.funcao || ''} (${emenda.ano})`,
      data: {
        autor: emenda.autor,
        funcao: emenda.funcao,
        ano: emenda.ano,
        tipo_emenda: emenda.tipo_emenda,
        localidade: emenda.localidade,
        valor_empenhado: emenda.valor_empenhado,
        valor_pago: emenda.valor_pago,
      },
    });

    // 2. Parallel: politico + favorecidos + associations + taxonomy
    const [politicoResult, favorecidosResult, associationsResult, taxonomyResult] = await Promise.all([
      // Politico (if entity resolution resolved)
      emenda.politico_id
        ? brasilDataHub.from('dim_politicos')
            .select('id, nome_completo, nome_urna, estado, cidade')
            .eq('id', emenda.politico_id)
            .single()
        : Promise.resolve({ data: null }),
      // Top favorecidos
      brasilDataHub.from('fato_emendas_favorecidos')
        .select('tipo_favorecido, favorecido, uf_favorecido, municipio_favorecido, valor_recebido')
        .eq('codigo_emenda', emenda.codigo_emenda)
        .order('valor_recebido', { ascending: false })
        .limit(10),
      // Context associations (noticia ↔ emenda)
      scrapingDb.from('fato_associacoes_contextuais')
        .select('id, origem_tipo, origem_id, destino_tipo, destino_id, tipo_associacao, confianca, evidencia, taxonomia_slug')
        .or(`and(destino_tipo.eq.emenda,destino_id.eq.${id}),and(origem_tipo.eq.emenda,origem_id.eq.${id})`)
        .order('confianca', { ascending: false })
        .limit(20),
      // Taxonomy
      scrapingDb.from('map_funcao_taxonomia')
        .select('taxonomia_slug')
        .eq('funcao', emenda.funcao)
        .single(),
    ]);

    // 3. Add politico node + edge
    const politico = politicoResult.data;
    if (politico) {
      nodes.push({
        id: `politico:${politico.id}`,
        type: 'politico',
        label: politico.nome_urna || politico.nome_completo,
        data: {
          estado: politico.estado,
          cidade: politico.cidade,
        },
      });
      edges.push({
        source: `politico:${politico.id}`,
        target: `emenda:${emenda.id}`,
        type: 'autoria',
        strength: 1.0,
      });

      // Hop 2: politico's other emendas (if hops >= 2)
      if (hops >= 2) {
        const { data: otherEmendas } = await brasilDataHub
          .from('fato_emendas_parlamentares')
          .select('id, funcao, ano, valor_empenhado')
          .eq('politico_id', politico.id)
          .neq('id', emenda.id)
          .order('ano', { ascending: false })
          .limit(5);

        for (const oe of (otherEmendas || [])) {
          const oeId = `emenda:${oe.id}`;
          nodes.push({
            id: oeId,
            type: 'emenda',
            label: `${emenda.autor} - ${oe.funcao || ''} (${oe.ano})`,
            data: { funcao: oe.funcao, ano: oe.ano, valor_empenhado: oe.valor_empenhado },
          });
          edges.push({
            source: `politico:${politico.id}`,
            target: oeId,
            type: 'autoria',
            strength: 0.8,
          });
        }

        // Hop 2: politico's mandatos
        const { data: mandatos } = await brasilDataHub
          .from('fato_politicos_mandatos')
          .select('id, cargo, municipio, ano_eleicao, partido_sigla, eleito')
          .eq('politico_id', politico.id)
          .limit(5);

        for (const m of (mandatos || [])) {
          const mId = `mandato:${m.id}`;
          nodes.push({
            id: mId,
            type: 'mandato',
            label: `${m.cargo} - ${m.municipio || ''} (${m.ano_eleicao})`,
            data: { cargo: m.cargo, municipio: m.municipio, ano: m.ano_eleicao, partido: m.partido_sigla, eleito: m.eleito },
          });
          edges.push({
            source: `politico:${politico.id}`,
            target: mId,
            type: 'mandato',
            strength: 0.9,
          });
        }
      }
    }

    // 4. Add favorecido nodes + edges
    for (const fav of (favorecidosResult.data || [])) {
      const favId = `favorecido:${(fav.favorecido || '').substring(0, 30).replace(/\s/g, '_')}`;
      // Avoid duplicate nodes
      if (!nodes.find(n => n.id === favId)) {
        nodes.push({
          id: favId,
          type: 'favorecido',
          label: fav.favorecido || 'N/A',
          data: {
            tipo: fav.tipo_favorecido,
            uf: fav.uf_favorecido,
            municipio: fav.municipio_favorecido,
            valor: fav.valor_recebido,
          },
        });
      }
      edges.push({
        source: `emenda:${emenda.id}`,
        target: favId,
        type: 'beneficiario',
        strength: 0.7,
        data: { valor: fav.valor_recebido },
      });
    }

    // 5. Add noticia nodes + edges from associations
    const noticiaIds = [];
    for (const assoc of (associationsResult.data || [])) {
      const isOrigin = assoc.origem_tipo === 'emenda';
      const noticiaId = isOrigin ? assoc.destino_id : assoc.origem_id;
      const noticiaTipo = isOrigin ? assoc.destino_tipo : assoc.origem_tipo;
      if (noticiaTipo !== 'noticia') continue;
      noticiaIds.push(noticiaId);

      edges.push({
        source: `emenda:${emenda.id}`,
        target: `noticia:${noticiaId}`,
        type: assoc.tipo_associacao,
        strength: assoc.confianca || 0.5,
        data: { evidencia: assoc.evidencia, taxonomia: assoc.taxonomia_slug },
      });
    }

    // Fetch noticia details
    if (noticiaIds.length > 0) {
      const { data: noticias } = await scrapingDb
        .from('dim_noticias')
        .select('id, titulo, fonte_nome, data_publicacao, tema_principal')
        .in('id', noticiaIds);

      for (const n of (noticias || [])) {
        nodes.push({
          id: `noticia:${n.id}`,
          type: 'noticia',
          label: (n.titulo || '').substring(0, 80),
          data: {
            fonte: n.fonte_nome,
            data: n.data_publicacao,
            tema: n.tema_principal,
          },
        });
      }
    }

    // 6. Add taxonomy node
    const taxSlug = taxonomyResult.data?.taxonomia_slug;
    if (taxSlug) {
      const { data: tax } = await scrapingDb
        .from('dim_taxonomia_tematica')
        .select('slug, nome, cor, icone')
        .eq('slug', taxSlug)
        .single();

      if (tax) {
        nodes.push({
          id: `taxonomia:${tax.slug}`,
          type: 'taxonomia',
          label: tax.nome,
          data: { cor: tax.cor, icone: tax.icone },
        });
        edges.push({
          source: `emenda:${emenda.id}`,
          target: `taxonomia:${tax.slug}`,
          type: 'tema',
          strength: 1.0,
        });
      }
    }

    // 7. Also pull graph edges from fato_relacoes_entidades (hop 2 only)
    if (hops >= 2) {
      const { data: graphEdges } = await scrapingDb
        .from('fato_relacoes_entidades')
        .select('source_type, source_id, target_type, target_id, tipo_relacao, strength, confidence')
        .or(`and(source_type.eq.emenda,source_id.eq.${id}),and(target_type.eq.emenda,target_id.eq.${id})`)
        .eq('ativo', true)
        .limit(30);

      for (const edge of (graphEdges || [])) {
        const sourceNode = `${edge.source_type}:${edge.source_id}`;
        const targetNode = `${edge.target_type}:${edge.target_id}`;

        // Only add edge if we don't already have it
        if (!edges.find(e => e.source === sourceNode && e.target === targetNode && e.type === edge.tipo_relacao)) {
          edges.push({
            source: sourceNode,
            target: targetNode,
            type: edge.tipo_relacao,
            strength: edge.strength,
          });

          // Add placeholder node if not already present
          for (const [nType, nId] of [[edge.source_type, edge.source_id], [edge.target_type, edge.target_id]]) {
            const nodeId = `${nType}:${nId}`;
            if (!nodes.find(n => n.id === nodeId)) {
              nodes.push({ id: nodeId, type: nType, label: nodeId, data: {} });
            }
          }
        }
      }
    }

    res.json({
      success: true,
      emenda_id: id,
      hops,
      graph: {
        nodes,
        edges,
        stats: {
          total_nodes: nodes.length,
          total_edges: edges.length,
          node_types: [...new Set(nodes.map(n => n.type))],
        },
      },
    });
  } catch (error) {
    logger.error('Error getting emenda network', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
