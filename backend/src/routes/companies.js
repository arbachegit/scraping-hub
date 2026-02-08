/**
 * Company Routes
 */

import { Router } from 'express';
import pino from 'pino';
import { EmpresaRepository, AnaliseRepository } from '../database/supabase.js';
import { PeopleService } from '../services/peopleService.js';
import { CompetitorService } from '../services/competitorService.js';
import { SerperClient, BrasilAPIClient } from '../services/apiClients.js';

const router = Router();
const logger = pino({ name: 'company-routes' });

const empresaRepo = new EmpresaRepository();
const analiseRepo = new AnaliseRepository();
const peopleService = new PeopleService();
const competitorService = new CompetitorService();
const serper = new SerperClient();
const brasilApi = new BrasilAPIClient();

/**
 * POST /analyze-complete
 * Análise completa de empresa
 */
router.post('/analyze-complete', async (req, res) => {
  try {
    const { name, cnpj } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Nome da empresa é obrigatório' });
    }

    logger.info({ name, cnpj }, 'Iniciando análise completa');

    const result = {
      metadata: {
        company_name: name,
        cnpj,
        analysis_date: new Date().toISOString(),
        sources_used: []
      },
      empresa: null,
      pessoas: { employees: [], fonte: null },
      concorrentes: [],
      status: 'processing'
    };

    // 1. Buscar informações da empresa
    const companyInfo = await serper.findCompanyInfo(name);
    if (companyInfo) {
      result.metadata.sources_used.push('Google Search');
    }

    // 2. Buscar CNPJ se não fornecido
    let cnpjData = null;
    if (cnpj) {
      cnpjData = await brasilApi.getCNPJ(cnpj);
    } else {
      const cnpjSearch = await serper.search(`${name} CNPJ`);
      const cnpjMatch = cnpjSearch?.organic?.[0]?.snippet?.match(/\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/);
      if (cnpjMatch) {
        cnpjData = await brasilApi.getCNPJ(cnpjMatch[0]);
      }
    }

    if (cnpjData) {
      result.metadata.sources_used.push('BrasilAPI (CNPJ)');
      result.metadata.cnpj = cnpjData.cnpj;
    }

    // 3. Salvar empresa
    const empresaData = {
      cnpj: cnpjData?.cnpj || cnpj,
      nome_fantasia: cnpjData?.nome_fantasia || name,
      razao_social: cnpjData?.razao_social,
      cnae_principal: cnpjData?.cnae_fiscal,
      cnae_descricao: cnpjData?.cnae_fiscal_descricao,
      logradouro: cnpjData?.logradouro,
      numero: cnpjData?.numero,
      bairro: cnpjData?.bairro,
      cidade: cnpjData?.municipio,
      estado: cnpjData?.uf,
      cep: cnpjData?.cep,
      website: companyInfo?.website,
      setor: companyInfo?.industry,
      porte: cnpjData?.porte,
      raw_cnpj_data: cnpjData || {},
      raw_search_data: companyInfo || {}
    };

    const empresaId = await empresaRepo.upsert(empresaData);
    result.empresa = { id: empresaId, ...empresaData };

    // 4. Buscar pessoas (com fallback)
    const domain = companyInfo?.website?.replace(/^https?:\/\//, '').split('/')[0];
    result.pessoas = await peopleService.searchPeople(name, domain);
    result.metadata.sources_used.push(`Pessoas (${result.pessoas.fonte})`);

    // 5. Salvar pessoas
    if (empresaId && result.pessoas.employees.length > 0) {
      const savedCount = await peopleService.savePeople(empresaId, result.pessoas.employees);
      result.pessoas.savedCount = savedCount;
    }

    // 6. Buscar concorrentes
    if (empresaId) {
      const empresa = await empresaRepo.getById(empresaId);
      const competitors = await competitorService.searchCompetitors(empresa);

      // 7. Analisar e salvar concorrentes
      result.concorrentes = await competitorService.analyzeAndSaveCompetitors(
        empresaId,
        name,
        competitors,
        empresa.palavras_chave || []
      );

      result.metadata.sources_used.push(`Concorrentes (${competitors.length} encontrados)`);
    }

    result.status = 'completed';
    result.metadata.processing_time_seconds = ((Date.now() - new Date(result.metadata.analysis_date).getTime()) / 1000).toFixed(2);

    logger.info({
      empresa: name,
      pessoas: result.pessoas.employees.length,
      concorrentes: result.concorrentes.length
    }, 'Análise concluída');

    res.json(result);

  } catch (error) {
    logger.error({ error: error.message }, 'Erro na análise');
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /:id
 * Buscar empresa por ID
 */
router.get('/:id', async (req, res) => {
  try {
    const empresa = await empresaRepo.getById(req.params.id);
    if (!empresa) {
      return res.status(404).json({ error: 'Empresa não encontrada' });
    }
    res.json(empresa);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /search
 * Buscar empresa por nome
 */
router.get('/search', async (req, res) => {
  try {
    const { name } = req.query;
    if (!name) {
      return res.status(400).json({ error: 'Nome é obrigatório' });
    }
    const empresa = await empresaRepo.getByNome(name);
    res.json(empresa || { message: 'Empresa não encontrada' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
