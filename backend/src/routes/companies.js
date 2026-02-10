import { Router } from 'express';
import * as serper from '../services/serper.js';
import * as brasilapi from '../services/brasilapi.js';
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
 * Uses: BrasilAPI (official data) + Serper (enrichment)
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

    // Get official data from BrasilAPI (Receita Federal)
    console.log(`[BRASILAPI] Buscando CNPJ: ${cleanCnpj}`);
    const brasilData = await brasilapi.getCompanyByCnpj(cleanCnpj);

    if (!brasilData) {
      return res.status(404).json({
        error: 'CNPJ nao encontrado na Receita Federal'
      });
    }

    // Enrich with Serper (LinkedIn, website, etc)
    console.log(`[SERPER] Enriquecendo dados para: ${brasilData.razao_social}`);
    const serperData = await serper.getCompanyDetails(cleanCnpj);

    // Merge data (BrasilAPI = official, Serper = enrichment)
    const merged = {
      // BrasilAPI - Official data
      cnpj: brasilData.cnpj,
      razao_social: brasilData.razao_social,
      nome_fantasia: brasilData.nome_fantasia,
      cnae_principal: brasilData.cnae_principal,
      cnae_descricao: brasilData.cnae_descricao,
      porte: brasilData.porte,
      natureza_juridica: brasilData.natureza_juridica,
      situacao_cadastral: brasilData.situacao_cadastral,
      capital_social: brasilData.capital_social,
      data_abertura: brasilData.data_abertura,
      simples_nacional: brasilData.simples_nacional,
      simei: brasilData.simei,

      // Address (BrasilAPI)
      logradouro: brasilData.logradouro,
      numero: brasilData.numero,
      complemento: brasilData.complemento,
      bairro: brasilData.bairro,
      cidade: brasilData.cidade,
      estado: brasilData.estado,
      cep: brasilData.cep,
      codigo_municipio_ibge: brasilData.codigo_municipio_ibge,

      // Contact (BrasilAPI)
      telefone_1: brasilData.telefone_1,
      telefone_2: brasilData.telefone_2,
      email: brasilData.email,

      // Serper enrichment
      website: serperData.website,
      linkedin: serperData.linkedin,
      setor: serperData.setor,
      descricao: serperData.descricao,
      num_funcionarios: serperData.num_funcionarios,
      logo_url: serperData.imageUrl || null,

      // Founders/Partners from BrasilAPI QSA
      socios: brasilData.socios || [],

      // Raw data
      raw_brasilapi: brasilData.raw_brasilapi,
      raw_serper: serperData
    };

    // Enrich socios with LinkedIn (via Serper)
    if (merged.socios && merged.socios.length > 0) {
      console.log(`[SERPER] Buscando LinkedIn para ${merged.socios.length} socios`);
      for (const socio of merged.socios.slice(0, 5)) { // Limit to 5 to avoid rate limits
        if (!socio.linkedin) {
          socio.linkedin = await serper.findPersonLinkedin(
            socio.nome,
            brasilData.razao_social
          );
        }
      }
    }

    return res.json({
      exists: false,
      message: 'Detalhes da empresa. Aguardando aprovacao.',
      company: merged
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
 * Includes: BrasilAPI fields + Serper enrichment + Socios with CPF
 */
router.post('/approve', async (req, res) => {
  try {
    const { company, socios, aprovado_por } = req.body;

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

    // Insert company with all fields
    const insertedCompany = await insertCompany({
      // Identification
      cnpj: cleanCnpj,
      razao_social: company.razao_social,
      nome_fantasia: company.nome_fantasia,

      // Classification (BrasilAPI)
      cnae_principal: company.cnae_principal,
      cnae_descricao: company.cnae_descricao,
      porte: company.porte,
      natureza_juridica: company.natureza_juridica,
      situacao_cadastral: company.situacao_cadastral,
      capital_social: company.capital_social,
      data_fundacao: company.data_abertura,
      simples_nacional: company.simples_nacional,
      simei: company.simei,

      // Address (BrasilAPI)
      logradouro: company.logradouro,
      numero: company.numero,
      complemento: company.complemento,
      bairro: company.bairro,
      cidade: company.cidade,
      estado: company.estado,
      cep: company.cep,
      codigo_municipio_ibge: company.codigo_municipio_ibge,

      // Contact (BrasilAPI)
      telefone_1: company.telefone_1,
      telefone_2: company.telefone_2,
      email: company.email,

      // Enrichment (Serper)
      website: company.website,
      linkedin: company.linkedin,
      setor: company.setor,
      descricao: company.descricao,
      num_funcionarios: company.num_funcionarios,
      logo_url: company.logo_url,

      // Raw data
      raw_brasilapi: company.raw_brasilapi || {},
      raw_serper: company.raw_serper || {},

      // Approval
      aprovado_por: aprovado_por
    });

    // Insert socios/founders as separate people (dim_pessoas)
    const insertedSocios = [];
    const sociosList = socios || company.socios || [];

    if (sociosList.length > 0) {
      for (const socio of sociosList) {
        const person = await insertPerson({
          nome: socio.nome,
          cpf: socio.cpf || null, // CPF from BrasilAPI QSA
          linkedin: socio.linkedin,
          cargo: socio.cargo || socio.qualificacao || 'Socio',
          qualificacao: socio.qualificacao,
          empresa_id: insertedCompany.id,
          tipo: 'fundador',
          data_entrada_sociedade: socio.data_entrada,
          faixa_etaria: socio.faixa_etaria,
          pais_origem: socio.pais_origem
        });
        insertedSocios.push(person);
      }
    }

    console.log(`[APPROVED] Empresa ${cleanCnpj} aprovada por ${aprovado_por} com ${insertedSocios.length} socios`);

    return res.json({
      success: true,
      message: 'Empresa aprovada e cadastrada com sucesso',
      company: insertedCompany,
      socios: insertedSocios
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
