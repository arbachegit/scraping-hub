import { Router } from 'express';
import { createClient } from '@supabase/supabase-js';
import logger from '../utils/logger.js';

const router = Router();

// Cliente Supabase para iconsai-fiscal
const fiscalSupabase = process.env.FISCAL_SUPABASE_URL && process.env.FISCAL_SUPABASE_KEY
  ? createClient(process.env.FISCAL_SUPABASE_URL, process.env.FISCAL_SUPABASE_KEY)
  : null;

/**
 * GET /api/politicians/list
 * List politicians with optional filters
 */
router.get('/list', async (req, res) => {
  try {
    if (!fiscalSupabase) {
      return res.status(503).json({
        success: false,
        error: 'Fiscal Supabase not configured'
      });
    }

    const limit = Math.min(parseInt(req.query.limit) || 50, 100);
    const offset = parseInt(req.query.offset) || 0;
    const { partido, uf, cargo } = req.query;

    let query = fiscalSupabase
      .from('politico')
      .select('id, nome_completo, nome_urna, partido_sigla, cargo_atual, uf, municipio_nome, foto_url', { count: 'exact' })
      .order('nome_completo', { ascending: true })
      .range(offset, offset + limit - 1);

    if (partido) {
      query = query.eq('partido_sigla', partido.toUpperCase());
    }
    if (uf) {
      query = query.eq('uf', uf.toUpperCase());
    }
    if (cargo) {
      query = query.eq('cargo_atual', cargo);
    }

    const { data, error, count } = await query;

    if (error) {
      logger.error('Error listing politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: count,
      politicians: data
    });

  } catch (error) {
    logger.error('Error listing politicians', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/politicians/search
 * Search politicians by name
 */
router.get('/search', async (req, res) => {
  try {
    if (!fiscalSupabase) {
      return res.status(503).json({
        success: false,
        error: 'Fiscal Supabase not configured'
      });
    }

    const { nome, partido, uf, cargo } = req.query;

    if (!nome || nome.trim().length < 2) {
      return res.status(400).json({
        success: false,
        error: 'Nome is required (minimum 2 characters)'
      });
    }

    let query = fiscalSupabase
      .from('politico')
      .select('id, nome_completo, nome_urna, partido_sigla, cargo_atual, uf, municipio_nome, foto_url')
      .ilike('nome_completo', `%${nome.trim()}%`)
      .limit(20);

    if (partido) {
      query = query.eq('partido_sigla', partido.toUpperCase());
    }
    if (uf) {
      query = query.eq('uf', uf.toUpperCase());
    }
    if (cargo) {
      query = query.eq('cargo_atual', cargo);
    }

    const { data, error } = await query;

    if (error) {
      logger.error('Error searching politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: data.length,
      politicians: data
    });

  } catch (error) {
    logger.error('Error searching politicians', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/politicians/:id
 * Get politician details with mandates
 */
router.get('/:id', async (req, res) => {
  try {
    if (!fiscalSupabase) {
      return res.status(503).json({
        success: false,
        error: 'Fiscal Supabase not configured'
      });
    }

    const { id } = req.params;

    // Get politician data
    const { data: politico, error: politicoError } = await fiscalSupabase
      .from('politico')
      .select('*')
      .eq('id', id)
      .single();

    if (politicoError || !politico) {
      return res.status(404).json({ success: false, error: 'Politician not found' });
    }

    // Mask CPF if present
    if (politico.cpf) {
      politico.cpf_masked = `***.***.${politico.cpf.slice(-5, -2)}-**`;
      delete politico.cpf;
    }

    // Get mandates
    const { data: mandatos } = await fiscalSupabase
      .from('mandato_politico')
      .select('*')
      .eq('politico_id', id)
      .order('ano_eleicao', { ascending: false });

    res.json({
      success: true,
      politico,
      mandatos: mandatos || []
    });

  } catch (error) {
    logger.error('Error getting politician', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/politicians/by-municipio/:codigoIbge
 * Get politicians by municipality
 */
router.get('/by-municipio/:codigoIbge', async (req, res) => {
  try {
    if (!fiscalSupabase) {
      return res.status(503).json({
        success: false,
        error: 'Fiscal Supabase not configured'
      });
    }

    const { codigoIbge } = req.params;
    const apenasAtivos = req.query.ativos !== 'false';

    let query = fiscalSupabase
      .from('mandato_politico')
      .select(`
        id, cargo, partido_sigla, ano_eleicao, votos_recebidos, ativo,
        politico:politico_id (
          id, nome_completo, nome_urna, foto_url
        )
      `)
      .eq('municipio_codigo_ibge', codigoIbge);

    if (apenasAtivos) {
      query = query.eq('ativo', true);
    }

    const { data, error } = await query.order('cargo');

    if (error) {
      logger.error('Error fetching municipality politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    // Flatten data
    const politicians = data.map(mandato => ({
      ...mandato.politico,
      cargo: mandato.cargo,
      partido: mandato.partido_sigla,
      ano_eleicao: mandato.ano_eleicao,
      votos: mandato.votos_recebidos,
      ativo: mandato.ativo
    }));

    res.json({
      success: true,
      count: politicians.length,
      politicians
    });

  } catch (error) {
    logger.error('Error fetching municipality politicians', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/politicians/by-partido/:sigla
 * Get politicians by party
 */
router.get('/by-partido/:sigla', async (req, res) => {
  try {
    if (!fiscalSupabase) {
      return res.status(503).json({
        success: false,
        error: 'Fiscal Supabase not configured'
      });
    }

    const { sigla } = req.params;
    const { uf, cargo } = req.query;
    const limit = Math.min(parseInt(req.query.limit) || 50, 100);

    let query = fiscalSupabase
      .from('politico')
      .select('id, nome_completo, nome_urna, cargo_atual, uf, municipio_nome, foto_url')
      .eq('partido_sigla', sigla.toUpperCase())
      .limit(limit);

    if (uf) {
      query = query.eq('uf', uf.toUpperCase());
    }
    if (cargo) {
      query = query.eq('cargo_atual', cargo);
    }

    const { data, error } = await query;

    if (error) {
      logger.error('Error fetching party politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: data.length,
      partido: sigla.toUpperCase(),
      politicians: data
    });

  } catch (error) {
    logger.error('Error fetching party politicians', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/politicians/partidos/list
 * List all parties with counts
 */
router.get('/partidos/list', async (req, res) => {
  try {
    if (!fiscalSupabase) {
      return res.status(503).json({
        success: false,
        error: 'Fiscal Supabase not configured'
      });
    }

    // Get distinct parties with counts
    const { data, error } = await fiscalSupabase
      .from('politico')
      .select('partido_sigla')
      .not('partido_sigla', 'is', null);

    if (error) {
      logger.error('Error listing parties', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    // Count by party
    const partyCounts = {};
    for (const row of data) {
      const partido = row.partido_sigla;
      partyCounts[partido] = (partyCounts[partido] || 0) + 1;
    }

    // Convert to array and sort
    const parties = Object.entries(partyCounts)
      .map(([sigla, count]) => ({ sigla, count }))
      .sort((a, b) => b.count - a.count);

    res.json({
      success: true,
      count: parties.length,
      partidos: parties
    });

  } catch (error) {
    logger.error('Error listing parties', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
