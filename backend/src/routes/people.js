/**
 * People Routes
 */

import { Router } from 'express';
import pino from 'pino';
import { PessoaRepository } from '../database/supabase.js';
import { PeopleService } from '../services/peopleService.js';

const router = Router();
const logger = pino({ name: 'people-routes' });

const pessoaRepo = new PessoaRepository();
const peopleService = new PeopleService();

/**
 * POST /search
 * Buscar pessoas de uma empresa
 */
router.post('/search', async (req, res) => {
  try {
    const { company_name, domain } = req.body;

    if (!company_name) {
      return res.status(400).json({ error: 'Nome da empresa é obrigatório' });
    }

    logger.info({ company: company_name }, 'Buscando pessoas');

    const result = await peopleService.searchPeople(company_name, domain);

    res.json({
      company: company_name,
      employees: result.employees,
      fonte: result.fonte,
      fallbackUsed: result.fallbackUsed,
      count: result.employees.length
    });

  } catch (error) {
    logger.error({ error: error.message }, 'Erro na busca de pessoas');
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /empresa/:empresaId
 * Listar pessoas de uma empresa
 */
router.get('/empresa/:empresaId', async (req, res) => {
  try {
    const pessoas = await pessoaRepo.getByEmpresa(req.params.empresaId);
    res.json({
      empresaId: req.params.empresaId,
      pessoas,
      count: pessoas.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
