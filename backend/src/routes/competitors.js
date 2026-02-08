/**
 * Competitor Routes
 */

import { Router } from 'express';
import pino from 'pino';
import { EmpresaRepository, ConcorrenteRepository } from '../database/supabase.js';
import { CompetitorService } from '../services/competitorService.js';

const router = Router();
const logger = pino({ name: 'competitor-routes' });

const empresaRepo = new EmpresaRepository();
const concorrenteRepo = new ConcorrenteRepository();
const competitorService = new CompetitorService();

/**
 * POST /search
 * Buscar concorrentes de uma empresa
 */
router.post('/search', async (req, res) => {
  try {
    const { empresa_id, company_name, cidade, estado, setor, porte, keywords } = req.body;

    if (!empresa_id && !company_name) {
      return res.status(400).json({ error: 'empresa_id ou company_name é obrigatório' });
    }

    let empresa;

    if (empresa_id) {
      empresa = await empresaRepo.getById(empresa_id);
    } else {
      empresa = await empresaRepo.getByNome(company_name);
    }

    if (!empresa) {
      // Criar empresa temporária para busca
      empresa = {
        nome_fantasia: company_name,
        cidade,
        estado,
        setor,
        porte,
        palavras_chave: keywords || []
      };
    }

    logger.info({ company: empresa.nome_fantasia }, 'Buscando concorrentes');

    const competitors = await competitorService.searchCompetitors(empresa);

    res.json({
      empresa: empresa.nome_fantasia,
      concorrentes: competitors,
      count: competitors.length
    });

  } catch (error) {
    logger.error({ error: error.message }, 'Erro na busca de concorrentes');
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /analyze
 * Analisar e salvar concorrentes
 */
router.post('/analyze', async (req, res) => {
  try {
    const { empresa_id, competitors, keywords } = req.body;

    if (!empresa_id || !competitors?.length) {
      return res.status(400).json({ error: 'empresa_id e competitors são obrigatórios' });
    }

    const empresa = await empresaRepo.getById(empresa_id);
    if (!empresa) {
      return res.status(404).json({ error: 'Empresa não encontrada' });
    }

    logger.info({
      empresa: empresa.nome_fantasia,
      count: competitors.length
    }, 'Analisando concorrentes');

    const saved = await competitorService.analyzeAndSaveCompetitors(
      empresa_id,
      empresa.nome_fantasia,
      competitors,
      keywords || empresa.palavras_chave || []
    );

    res.json({
      empresa: empresa.nome_fantasia,
      saved,
      count: saved.length
    });

  } catch (error) {
    logger.error({ error: error.message }, 'Erro na análise de concorrentes');
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /empresa/:empresaId
 * Listar concorrentes de uma empresa
 */
router.get('/empresa/:empresaId', async (req, res) => {
  try {
    const concorrentes = await concorrenteRepo.getByEmpresa(req.params.empresaId);
    res.json({
      empresaId: req.params.empresaId,
      concorrentes,
      count: concorrentes.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
