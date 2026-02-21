import { Router } from 'express';
import { createClient } from '@supabase/supabase-js';
import logger from '../utils/logger.js';
import {
  validateQuery,
  validateParams,
  politiciansListSchema,
  politiciansSearchSchema,
  politicosByMunicipioSchema,
  politicosByMunicipioQuerySchema,
  politicosByPartidoSchema,
  politicosByPartidoQuerySchema,
  uuidParamSchema
} from '../validation/schemas.js';

const router = Router();

// Cliente Supabase para brasil-data-hub (dim_politicos, fato_politicos_mandatos)
const brasilDataHub = process.env.BRASIL_DATA_HUB_URL && process.env.BRASIL_DATA_HUB_KEY
  ? createClient(process.env.BRASIL_DATA_HUB_URL, process.env.BRASIL_DATA_HUB_KEY)
  : null;

/**
 * GET /api/politicians/list
 * List politicians with optional filters
 */
router.get('/list', validateQuery(politiciansListSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Query params already validated and transformed by Zod
    const { limit, offset, partido, cargo, municipio, ano_eleicao } = req.query;

    // Se tem filtros de mandato, buscar via fato_politicos_mandatos
    if (partido || cargo || municipio || ano_eleicao) {
      let query = brasilDataHub
        .from('fato_politicos_mandatos')
        .select(`
          id, cargo, partido_sigla, partido_nome, municipio, codigo_ibge,
          ano_eleicao, eleito, situacao_turno,
          politico:politico_id (id, nome_completo, nome_urna, sexo, ocupacao)
        `, { count: 'exact' })
        .order('ano_eleicao', { ascending: false })
        .range(offset, offset + limit - 1);

      // All query params already validated and sanitized by Zod
      if (partido) {
        query = query.eq('partido_sigla', partido);  // Already uppercase from Zod
      }
      if (cargo) {
        query = query.ilike('cargo', `%${cargo}%`);  // Sanitized by Zod
      }
      if (municipio) {
        query = query.ilike('municipio', `%${municipio}%`);  // Sanitized by Zod
      }
      if (ano_eleicao) {
        query = query.eq('ano_eleicao', ano_eleicao);  // Already number from Zod
      }

      const { data, error, count } = await query;

      if (error) {
        logger.error('Error listing politicians via mandatos', { error: error.message });
        return res.status(500).json({ success: false, error: error.message });
      }

      // Flatten data and remove duplicates
      const seen = new Set();
      const politicians = [];
      for (const mandato of data || []) {
        const politico = mandato.politico || {};
        const politicoId = politico.id;
        if (politicoId && !seen.has(politicoId)) {
          seen.add(politicoId);
          politicians.push({
            id: politicoId,
            nome_completo: politico.nome_completo,
            nome_urna: politico.nome_urna,
            sexo: politico.sexo,
            ocupacao: politico.ocupacao,
            partido_sigla: mandato.partido_sigla,
            cargo_atual: mandato.cargo,
            municipio: mandato.municipio,
            codigo_ibge: mandato.codigo_ibge,
            ano_eleicao: mandato.ano_eleicao,
            eleito: mandato.eleito
          });
        }
      }

      return res.json({
        success: true,
        count: politicians.length,
        total: count,
        politicians
      });
    }

    // Sem filtros de mandato, buscar direto em dim_politicos
    let query = brasilDataHub
      .from('dim_politicos')
      .select('id, nome_completo, nome_urna, sexo, ocupacao, grau_instrucao', { count: 'exact' })
      .order('nome_completo', { ascending: true })
      .range(offset, offset + limit - 1);

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
router.get('/search', validateQuery(politiciansSearchSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Query params already validated by Zod (nome >= 2 chars, sanitized)
    const { nome } = req.query;

    // Search in dim_politicos (nome already sanitized by Zod)
    const { data: politicos, error } = await brasilDataHub
      .from('dim_politicos')
      .select('id, nome_completo, nome_urna, sexo, ocupacao, grau_instrucao')
      .or(`nome_completo.ilike.%${nome}%,nome_urna.ilike.%${nome}%`)
      .limit(20);

    if (error) {
      logger.error('Error searching politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    // Enrich with latest mandato
    const enrichedPoliticians = [];
    for (const politico of politicos || []) {
      const { data: mandatos } = await brasilDataHub
        .from('fato_politicos_mandatos')
        .select('cargo, partido_sigla, municipio, ano_eleicao, eleito')
        .eq('politico_id', politico.id)
        .order('ano_eleicao', { ascending: false })
        .limit(1);

      const latest = mandatos?.[0] || {};
      enrichedPoliticians.push({
        ...politico,
        partido_sigla: latest.partido_sigla,
        cargo_atual: latest.cargo,
        municipio: latest.municipio,
        ano_eleicao: latest.ano_eleicao,
        eleito: latest.eleito
      });
    }

    res.json({
      success: true,
      count: enrichedPoliticians.length,
      politicians: enrichedPoliticians
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
router.get('/:id', validateParams(uuidParamSchema), async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // ID already validated as UUID by Zod
    const { id } = req.params;

    // Get politician data from dim_politicos
    const { data: politico, error: politicoError } = await brasilDataHub
      .from('dim_politicos')
      .select('id, nome_completo, nome_urna, data_nascimento, sexo, grau_instrucao, ocupacao')
      .eq('id', id)
      .single();

    if (politicoError || !politico) {
      return res.status(404).json({ success: false, error: 'Politician not found' });
    }

    // Get mandates from fato_politicos_mandatos
    const { data: mandatos } = await brasilDataHub
      .from('fato_politicos_mandatos')
      .select(`
        id, cargo, partido_sigla, partido_nome, municipio, codigo_ibge,
        ano_eleicao, turno, numero_candidato, eleito, coligacao, situacao_turno,
        data_inicio_mandato, data_fim_mandato
      `)
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
router.get('/by-municipio/:codigoIbge',
  validateParams(politicosByMunicipioSchema),
  validateQuery(politicosByMunicipioQuerySchema),
  async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Params and query already validated by Zod
    const { codigoIbge } = req.params;
    const apenasEleitos = req.query.eleitos !== 'false';
    const ano = req.query.ano || null;

    let query = brasilDataHub
      .from('fato_politicos_mandatos')
      .select(`
        id, cargo, partido_sigla, ano_eleicao, eleito, situacao_turno,
        politico:politico_id (id, nome_completo, nome_urna, sexo)
      `)
      .eq('codigo_ibge', codigoIbge);

    if (apenasEleitos) {
      query = query.eq('eleito', true);
    }
    if (ano) {
      query = query.eq('ano_eleicao', ano);
    }

    const { data, error } = await query.order('cargo');

    if (error) {
      logger.error('Error fetching municipality politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    // Flatten data
    const politicians = (data || []).map(mandato => ({
      id: mandato.politico?.id,
      nome_completo: mandato.politico?.nome_completo,
      nome_urna: mandato.politico?.nome_urna,
      sexo: mandato.politico?.sexo,
      cargo: mandato.cargo,
      partido_sigla: mandato.partido_sigla,
      ano_eleicao: mandato.ano_eleicao,
      eleito: mandato.eleito,
      situacao_turno: mandato.situacao_turno
    }));

    res.json({
      success: true,
      count: politicians.length,
      codigo_ibge: codigoIbge,
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
router.get('/by-partido/:sigla',
  validateParams(politicosByPartidoSchema),
  validateQuery(politicosByPartidoQuerySchema),
  async (req, res) => {
  try {
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Params and query already validated by Zod (sigla transformed to uppercase)
    const { sigla } = req.params;
    const { cargo, ano_eleicao, limit } = req.query;

    // sigla already transformed to uppercase by Zod
    let query = brasilDataHub
      .from('fato_politicos_mandatos')
      .select(`
        id, cargo, partido_sigla, municipio, ano_eleicao, eleito,
        politico:politico_id (id, nome_completo, nome_urna, sexo)
      `)
      .eq('partido_sigla', sigla)
      .limit(limit);

    // cargo already sanitized by Zod (no SQL injection chars)
    if (cargo) {
      query = query.ilike('cargo', `%${cargo}%`);
    }
    // ano_eleicao already validated as number by Zod
    if (ano_eleicao) {
      query = query.eq('ano_eleicao', ano_eleicao);
    }

    const { data, error } = await query.order('municipio');

    if (error) {
      logger.error('Error fetching party politicians', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    // Flatten and deduplicate
    const seen = new Set();
    const politicians = [];
    for (const mandato of data || []) {
      const politico = mandato.politico || {};
      const politicoId = politico.id;
      if (politicoId && !seen.has(politicoId)) {
        seen.add(politicoId);
        politicians.push({
          id: politicoId,
          nome_completo: politico.nome_completo,
          nome_urna: politico.nome_urna,
          sexo: politico.sexo,
          cargo: mandato.cargo,
          municipio: mandato.municipio,
          ano_eleicao: mandato.ano_eleicao,
          eleito: mandato.eleito
        });
      }
    }

    res.json({
      success: true,
      count: politicians.length,
      partido: sigla,  // Already uppercase from Zod
      politicians
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
    if (!brasilDataHub) {
      return res.status(503).json({
        success: false,
        error: 'Brasil Data Hub not configured. Set BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY.'
      });
    }

    // Get distinct parties from mandatos
    const { data, error } = await brasilDataHub
      .from('fato_politicos_mandatos')
      .select('partido_sigla, partido_nome')
      .not('partido_sigla', 'is', null);

    if (error) {
      logger.error('Error listing parties', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    // Count by party
    const partyCounts = {};
    const partyNames = {};
    for (const row of data || []) {
      const sigla = row.partido_sigla;
      partyCounts[sigla] = (partyCounts[sigla] || 0) + 1;
      if (row.partido_nome) {
        partyNames[sigla] = row.partido_nome;
      }
    }

    // Convert to array and sort
    const parties = Object.entries(partyCounts)
      .map(([sigla, count]) => ({
        sigla,
        nome: partyNames[sigla] || sigla,
        count
      }))
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
