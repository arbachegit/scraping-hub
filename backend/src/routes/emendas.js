import { Router } from 'express';
import { createClient } from '@supabase/supabase-js';
import logger from '../utils/logger.js';
import { escapeLike } from '../utils/sanitize.js';
import {
  validateQuery,
  validateParams,
  listEmendasSchema,
  searchEmendasSchema,
  integerIdParamSchema
} from '../validation/schemas.js';

const router = Router();

// Cliente Supabase para brasil-data-hub (fato_emendas_parlamentares)
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
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
 * Search emendas by text (autor, descricao, localidade, etc.)
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
          .or(`autor.ilike.%${escaped}%,descricao.ilike.%${escaped}%,localidade.ilike.%${escaped}%`)
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
        .or(`autor.ilike.%${escaped}%,descricao.ilike.%${escaped}%,localidade.ilike.%${escaped}%`)
        .order('ano', { ascending: false })
        .limit(limit);
      data = result.data;
      error = result.error;
      count = result.data?.length || 0;
    }

    if (error) {
      logger.error('Error searching emendas', { error: error.message, query: q });
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
 * Aggregated stats for emendas dashboard
 */
router.get('/aggregation', async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({ success: false, error: 'Brasil Data Hub not configured.' });
    }

    // Run all queries in parallel
    const [byFuncao, byAno, byTipo, byLocalidade, topAutores, totals] = await Promise.all([
      // By funcao
      brasilDataHub.rpc('get_emendas_by_funcao'),
      // By ano
      brasilDataHub.rpc('get_emendas_by_ano'),
      // By tipo
      brasilDataHub.rpc('get_emendas_by_tipo'),
      // By localidade (top 15)
      brasilDataHub.rpc('get_emendas_by_localidade'),
      // Top autores
      brasilDataHub.rpc('get_emendas_top_autores'),
      // Totals
      brasilDataHub.rpc('get_emendas_totals'),
    ]);

    // Fallback: if RPCs don't exist, use direct queries
    let funcaoData = byFuncao.data;
    let anoData = byAno.data;
    let tipoData = byTipo.data;
    let localidadeData = byLocalidade.data;
    let autoresData = topAutores.data;
    let totalsData = totals.data;

    // If any RPC fails, run fallback queries
    if (byFuncao.error || byAno.error || byTipo.error) {
      logger.warn('Emendas aggregation RPCs not available, using fallback');

      const [fRes, aRes, tRes, lRes, auRes] = await Promise.all([
        brasilDataHub.from('fato_emendas_parlamentares').select('funcao').not('funcao', 'is', null),
        brasilDataHub.from('fato_emendas_parlamentares').select('ano'),
        brasilDataHub.from('fato_emendas_parlamentares').select('tipo_emenda').not('tipo_emenda', 'is', null),
        brasilDataHub.from('fato_emendas_parlamentares').select('localidade').not('localidade', 'is', null),
        brasilDataHub.from('fato_emendas_parlamentares').select('autor, valor_empenhado').order('valor_empenhado', { ascending: false }).limit(500),
      ]);

      // Aggregate in memory
      if (!byFuncao.data && fRes.data) {
        const grouped = {};
        for (const r of fRes.data) { grouped[r.funcao] = (grouped[r.funcao] || 0) + 1; }
        funcaoData = Object.entries(grouped).map(([funcao, count]) => ({ funcao, count })).sort((a, b) => b.count - a.count);
      }
      if (!byAno.data && aRes.data) {
        const grouped = {};
        for (const r of aRes.data) { grouped[r.ano] = (grouped[r.ano] || 0) + 1; }
        anoData = Object.entries(grouped).map(([ano, count]) => ({ ano: Number(ano), count })).sort((a, b) => a.ano - b.ano);
      }
      if (!byTipo.data && tRes.data) {
        const grouped = {};
        for (const r of tRes.data) { grouped[r.tipo_emenda] = (grouped[r.tipo_emenda] || 0) + 1; }
        tipoData = Object.entries(grouped).map(([tipo, count]) => ({ tipo, count })).sort((a, b) => b.count - a.count);
      }
      if (!byLocalidade.data && lRes.data) {
        const grouped = {};
        for (const r of lRes.data) { grouped[r.localidade] = (grouped[r.localidade] || 0) + 1; }
        localidadeData = Object.entries(grouped).map(([localidade, count]) => ({ localidade, count })).sort((a, b) => b.count - a.count).slice(0, 15);
      }
      if (!topAutores.data && auRes.data) {
        const grouped = {};
        for (const r of auRes.data) {
          if (!grouped[r.autor]) grouped[r.autor] = { count: 0, valor_total: 0 };
          grouped[r.autor].count++;
          grouped[r.autor].valor_total += Number(r.valor_empenhado) || 0;
        }
        autoresData = Object.entries(grouped).map(([autor, d]) => ({ autor, count: d.count, valor_total: d.valor_total })).sort((a, b) => b.valor_total - a.valor_total).slice(0, 15);
      }
    }

    // Calculate totals from the data if RPC not available
    if (!totalsData) {
      const { count } = await brasilDataHub.from('fato_emendas_parlamentares').select('*', { count: 'exact', head: true });
      totalsData = [{ total_emendas: count || 0, total_empenhado: 0, total_pago: 0 }];
    }

    res.json({
      success: true,
      totals: Array.isArray(totalsData) ? totalsData[0] : totalsData,
      by_funcao: funcaoData || [],
      by_ano: anoData || [],
      by_tipo: tipoData || [],
      by_localidade: localidadeData || [],
      top_autores: autoresData || [],
    });
  } catch (error) {
    logger.error('Error getting emendas aggregation', { error: error.message });
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

export default router;
