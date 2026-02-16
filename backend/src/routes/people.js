import { Router } from 'express';
import { supabase } from '../database/supabase.js';
import logger from '../utils/logger.js';

const router = Router();

/**
 * GET /api/people/list
 * List all people in the database
 */
router.get('/list', async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit) || 50, 100);
    const offset = parseInt(req.query.offset) || 0;

    const { data, error, count } = await supabase
      .from('dim_pessoas')
      .select('id, nome_completo, email, linkedin_url, foto_url, cpf, faixa_etaria, pais_origem', { count: 'exact' })
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      logger.error('Error listing people', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: count,
      people: data
    });

  } catch (error) {
    logger.error('Error listing people', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/people/:id
 * Get person details by ID
 */
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;

    // Get person data
    const { data: pessoa, error: pessoaError } = await supabase
      .from('dim_pessoas')
      .select('*')
      .eq('id', id)
      .single();

    if (pessoaError || !pessoa) {
      return res.status(404).json({ success: false, error: 'Pessoa não encontrada' });
    }

    // Get experiences
    const { data: experiencias } = await supabase
      .from('fato_eventos_pessoa')
      .select('*')
      .eq('pessoa_id', id)
      .order('data_inicio', { ascending: false });

    // Get company relationships
    const { data: empresas } = await supabase
      .from('fato_transacao_empresas')
      .select(`
        id,
        tipo_transacao,
        cargo,
        qualificacao,
        data_transacao,
        dim_empresas (
          id,
          cnpj,
          razao_social,
          nome_fantasia,
          cidade,
          estado
        )
      `)
      .eq('pessoa_id', id)
      .order('data_transacao', { ascending: false });

    // Get related news
    const { data: noticias } = await supabase
      .from('fato_noticias_pessoas')
      .select(`
        tipo_relacao,
        dim_noticias (
          id,
          titulo,
          resumo,
          fonte_nome,
          url,
          data_publicacao,
          relevancia_geral
        )
      `)
      .eq('pessoa_id', id)
      .order('created_at', { ascending: false })
      .limit(10);

    res.json({
      success: true,
      pessoa,
      experiencias: experiencias || [],
      empresas: empresas || [],
      noticias: noticias?.map(n => ({
        ...n.dim_noticias,
        tipo_relacao: n.tipo_relacao
      })) || []
    });

  } catch (error) {
    logger.error('Error getting person', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * GET /api/people/by-company/:empresaId
 * Get people related to a company
 */
router.get('/by-company/:empresaId', async (req, res) => {
  try {
    const { empresaId } = req.params;

    const { data, error } = await supabase
      .from('fato_transacao_empresas')
      .select(`
        tipo_transacao,
        cargo,
        qualificacao,
        data_transacao,
        ativo,
        dim_pessoas (
          id,
          nome_completo,
          email,
          linkedin_url,
          foto_url,
          cpf
        )
      `)
      .eq('empresa_id', empresaId)
      .order('data_transacao', { ascending: false });

    if (error) {
      logger.error('Error fetching company people', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: data.length,
      people: data.map(item => ({
        ...item.dim_pessoas,
        tipo_transacao: item.tipo_transacao,
        cargo: item.cargo,
        qualificacao: item.qualificacao,
        data_transacao: item.data_transacao,
        ativo: item.ativo
      }))
    });

  } catch (error) {
    logger.error('Error fetching company people', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * POST /api/people/search
 * Search people by name
 */
router.post('/search', async (req, res) => {
  try {
    const { nome } = req.body;

    if (!nome || nome.trim().length < 2) {
      return res.status(400).json({
        success: false,
        error: 'Nome é obrigatório (mínimo 2 caracteres)'
      });
    }

    // Search in dim_pessoas - empresa filter via fato_transacao_empresas join
    let query = supabase
      .from('dim_pessoas')
      .select('id, nome_completo, email, linkedin_url, foto_url, cpf')
      .ilike('nome_completo', `%${nome.trim()}%`)
      .limit(20);

    const { data, error } = await query;

    if (error) {
      logger.error('Error searching people', { error: error.message });
      return res.status(500).json({ success: false, error: error.message });
    }

    res.json({
      success: true,
      count: data.length,
      people: data
    });

  } catch (error) {
    logger.error('Error searching people', { error: error.message });
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
