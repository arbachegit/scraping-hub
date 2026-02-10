import { Router } from 'express';
import * as serper from '../services/serper.js';
import { insertCompany, insertPerson, findCompanyByCnpj } from '../database/supabase.js';

const router = Router();

/**
 * POST /api/companies/search
 * Search for company by name, return candidates with CNPJ
 */
router.post('/search', async (req, res) => {
  try {
    const { nome } = req.body;

    if (!nome || nome.trim().length < 2) {
      return res.status(400).json({
        error: 'Nome da empresa e obrigatorio (minimo 2 caracteres)'
      });
    }

    console.log(`[SEARCH] Buscando empresa: ${nome}`);

    // Search for company candidates
    const candidates = await serper.searchCompanyByName(nome.trim());

    if (candidates.length === 0) {
      return res.json({
        found: false,
        message: 'Nenhuma empresa encontrada com este nome',
        candidates: []
      });
    }

    if (candidates.length === 1) {
      // Single result - get details for approval
      const details = await serper.getCompanyDetails(candidates[0].cnpj);
      return res.json({
        found: true,
        single_match: true,
        message: 'Empresa encontrada. Aguardando aprovacao.',
        company: {
          ...candidates[0],
          ...details
        }
      });
    }

    // Multiple results - return list for selection
    return res.json({
      found: true,
      single_match: false,
      message: `${candidates.length} empresas encontradas. Selecione a correta.`,
      candidates: candidates.map(c => ({
        cnpj: c.cnpj,
        cnpj_formatted: c.cnpj_formatted,
        razao_social: c.razao_social,
        localizacao: c.localizacao
      }))
    });

  } catch (error) {
    console.error('[SEARCH ERROR]', error);
    res.status(500).json({
      error: 'Erro ao buscar empresa',
      details: error.message
    });
  }
});

/**
 * POST /api/companies/details
 * Get detailed info for a specific CNPJ
 */
router.post('/details', async (req, res) => {
  try {
    const { cnpj } = req.body;

    if (!cnpj) {
      return res.status(400).json({ error: 'CNPJ e obrigatorio' });
    }

    const cleanCnpj = cnpj.replace(/[^\d]/g, '');
    if (cleanCnpj.length !== 14) {
      return res.status(400).json({ error: 'CNPJ invalido' });
    }

    // Check if already exists
    const existing = await findCompanyByCnpj(cleanCnpj);
    if (existing) {
      return res.json({
        exists: true,
        message: 'Empresa ja cadastrada',
        company: existing
      });
    }

    // Get details from Serper
    const details = await serper.getCompanyDetails(cleanCnpj);

    // Search LinkedIn for founders
    if (details.fundadores) {
      for (const founder of details.fundadores) {
        if (!founder.linkedin) {
          founder.linkedin = await serper.findPersonLinkedin(
            founder.nome,
            details.razao_social
          );
        }
      }
    }

    return res.json({
      exists: false,
      message: 'Detalhes da empresa. Aguardando aprovacao.',
      company: details
    });

  } catch (error) {
    console.error('[DETAILS ERROR]', error);
    res.status(500).json({
      error: 'Erro ao buscar detalhes',
      details: error.message
    });
  }
});

/**
 * POST /api/companies/approve
 * Approve and insert company into database
 */
router.post('/approve', async (req, res) => {
  try {
    const { company, fundadores, aprovado_por } = req.body;

    if (!company || !company.cnpj) {
      return res.status(400).json({ error: 'Dados da empresa sao obrigatorios' });
    }

    if (!aprovado_por) {
      return res.status(400).json({ error: 'Aprovador e obrigatorio' });
    }

    const cleanCnpj = company.cnpj.replace(/[^\d]/g, '');

    // Check if already exists
    const existing = await findCompanyByCnpj(cleanCnpj);
    if (existing) {
      return res.status(409).json({
        error: 'Empresa ja cadastrada',
        company: existing
      });
    }

    // Insert company (without founders)
    const insertedCompany = await insertCompany({
      cnpj: cleanCnpj,
      razao_social: company.razao_social,
      nome_fantasia: company.nome_fantasia,
      website: company.website,
      linkedin: company.linkedin, // LinkedIn da empresa
      endereco: company.endereco,
      cidade: company.cidade,
      estado: company.estado,
      setor: company.setor,
      descricao: company.descricao,
      data_fundacao: company.data_fundacao,
      num_funcionarios: company.num_funcionarios,
      aprovado_por: aprovado_por
    });

    // Insert founders as separate people
    const insertedFounders = [];
    if (fundadores && fundadores.length > 0) {
      for (const founder of fundadores) {
        const person = await insertPerson({
          nome: founder.nome,
          linkedin: founder.linkedin, // LinkedIn pessoal do fundador
          cargo: founder.cargo || 'Fundador',
          empresa_id: insertedCompany.id,
          tipo: 'fundador'
        });
        insertedFounders.push(person);
      }
    }

    console.log(`[APPROVED] Empresa ${cleanCnpj} aprovada por ${aprovado_por}`);

    return res.json({
      success: true,
      message: 'Empresa aprovada e cadastrada com sucesso',
      company: insertedCompany,
      fundadores: insertedFounders
    });

  } catch (error) {
    console.error('[APPROVE ERROR]', error);
    res.status(500).json({
      error: 'Erro ao aprovar empresa',
      details: error.message
    });
  }
});

export default router;
