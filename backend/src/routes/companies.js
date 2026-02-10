import { Router } from 'express';
import * as serper from '../services/serper.js';
import * as brasilapi from '../services/brasilapi.js';
import * as apollo from '../services/apollo.js';
import { insertCompany, insertPerson, insertTransacaoEmpresa, insertRegimeTributario, findCompanyByCnpj } from '../database/supabase.js';

const router = Router();

/**
 * POST /api/companies/search
 * Search for company by name and optional city, return candidates with CNPJ
 */
router.post('/search', async (req, res) => {
  try {
    const { nome, cidade } = req.body;

    if (!nome || nome.trim().length < 2) {
      return res.status(400).json({
        error: 'Nome da empresa e obrigatorio (minimo 2 caracteres)'
      });
    }

    console.log(`[SEARCH] Buscando empresa: ${nome}${cidade ? ` em ${cidade}` : ''}`);

    // Search for company candidates with optional city filter
    const candidates = await serper.searchCompanyByName(nome.trim(), cidade?.trim() || null);

    if (candidates.length === 0) {
      return res.json({
        found: false,
        message: 'Nenhuma empresa encontrada com este nome',
        candidates: []
      });
    }

    // Enrich candidates with city from BrasilAPI (limit to 10 for performance)
    const limitedCandidates = candidates.slice(0, 10);
    console.log(`[SEARCH] Enriquecendo ${limitedCandidates.length} candidatos com cidade da Receita Federal`);

    const enrichedCandidates = await Promise.all(
      limitedCandidates.map(async (c) => {
        try {
          const brasilData = await brasilapi.getCompanyByCnpj(c.cnpj);
          return {
            cnpj: c.cnpj,
            cnpj_formatted: c.cnpj_formatted,
            razao_social: brasilData?.razao_social || c.razao_social,
            nome_fantasia: brasilData?.nome_fantasia || null,
            localizacao: brasilData ? `${brasilData.cidade} - ${brasilData.estado}` : c.localizacao
          };
        } catch (err) {
          console.warn(`[SEARCH] Erro ao buscar cidade para ${c.cnpj}:`, err.message);
          return {
            cnpj: c.cnpj,
            cnpj_formatted: c.cnpj_formatted,
            razao_social: c.razao_social,
            nome_fantasia: null,
            localizacao: c.localizacao
          };
        }
      })
    );

    if (enrichedCandidates.length === 1) {
      // Single result - redirect to details
      return res.json({
        found: true,
        single_match: true,
        message: 'Empresa encontrada. Selecione para ver detalhes.',
        company: enrichedCandidates[0]
      });
    }

    return res.json({
      found: true,
      single_match: false,
      message: `${enrichedCandidates.length} empresas encontradas. Selecione a correta.`,
      candidates: enrichedCandidates
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
 * Sources: BrasilAPI (official) + Apollo + Serper (enrichment)
 * Returns: empresa (company data) separately from socios (people data)
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
        empresa: existing,
        socios: [] // Load separately via /socios endpoint
      });
    }

    // ========================================
    // 1. DADOS OFICIAIS - BrasilAPI (Receita Federal)
    // ========================================
    console.log(`[BRASILAPI] Buscando CNPJ: ${cleanCnpj}`);
    const brasilData = await brasilapi.getCompanyByCnpj(cleanCnpj);

    if (!brasilData) {
      return res.status(404).json({
        error: 'CNPJ nao encontrado na Receita Federal'
      });
    }

    // Clean company name for searches
    let searchName = brasilData.nome_fantasia || brasilData.razao_social;
    searchName = searchName
      .replace(/\s*[-–]\s*[A-Z0-9\s]+$/gi, '')
      .replace(/\s+(LTDA|S\.?A\.?|S\/A|ME|EPP|EIRELI|SOCIEDADE ANONIMA|LIMITADA)\.?$/gi, '')
      .replace(/\s+(COMERCIO|COMERCIAL|INDUSTRIA|SERVICOS|PARTICIPACOES|BRASILEIRO|BRASILEIRA).*$/gi, '')
      .trim();
    if (searchName.length > 30) {
      searchName = searchName.split(/\s+/)[0];
    }

    // ========================================
    // 2. ENRIQUECIMENTO - Apollo (LinkedIn empresa)
    // ========================================
    console.log(`[APOLLO] Buscando empresa: ${searchName}`);
    const apolloData = await apollo.searchCompany(searchName, brasilData.estado);

    // ========================================
    // 3. ENRIQUECIMENTO - Serper (Website via Google)
    // ========================================
    console.log(`[SERPER] Buscando website: ${searchName}`);
    let website = apolloData?.website || null;
    if (!website) {
      website = await serper.findCompanyWebsite(searchName, brasilData.cidade);
    }

    // ========================================
    // 4. ENRIQUECIMENTO - LinkedIn empresa (Apollo → Serper → NAO_POSSUI)
    // ========================================
    let linkedin = apolloData?.linkedin || null;
    if (!linkedin) {
      console.log(`[SERPER] Buscando LinkedIn empresa: ${searchName}`);
      linkedin = await serper.findCompanyLinkedin(searchName);
    }
    // Mark as NAO_POSSUI if not found (important for analysis)
    if (!linkedin) {
      linkedin = 'NAO_POSSUI';
    }

    // ========================================
    // 5. EXTRAIR CONTATOS DO WEBSITE
    // ========================================
    let websiteContacts = { emails: [], phones: [], social: {} };
    if (website && website !== 'NAO_POSSUI') {
      console.log(`[SERPER] Extraindo contatos de: ${website}`);
      websiteContacts = await serper.extractContactsFromWebsite(website);
    }

    // ========================================
    // 6. MONTAR DADOS DA EMPRESA (sem sócios)
    // ========================================
    const empresa = {
      // Identificação
      cnpj: brasilData.cnpj,
      razao_social: brasilData.razao_social,
      nome_fantasia: brasilData.nome_fantasia,

      // Classificação (Receita Federal)
      cnae_principal: brasilData.cnae_principal,
      cnae_descricao: brasilData.cnae_descricao,
      porte: brasilData.porte,
      natureza_juridica: brasilData.natureza_juridica,
      situacao_cadastral: brasilData.situacao_cadastral,
      capital_social: brasilData.capital_social,
      data_abertura: brasilData.data_abertura,
      simples_nacional: brasilData.simples_nacional,
      simei: brasilData.simei,

      // Endereço (Receita Federal)
      logradouro: brasilData.logradouro,
      numero: brasilData.numero,
      complemento: brasilData.complemento,
      bairro: brasilData.bairro,
      cidade: brasilData.cidade,
      estado: brasilData.estado,
      cep: brasilData.cep,
      codigo_municipio_ibge: brasilData.codigo_municipio_ibge,

      // Contato (Receita Federal + Website)
      telefone_1: brasilData.telefone_1,
      telefone_2: brasilData.telefone_2,
      email: brasilData.email || websiteContacts.emails[0] || null,
      emails_website: websiteContacts.emails,
      telefones_website: websiteContacts.phones,

      // Presença Digital (Apollo + Serper)
      website: website,
      linkedin: linkedin, // NAO_POSSUI se não encontrar
      twitter: apolloData?.twitter || websiteContacts.social?.twitter || null,
      facebook: apolloData?.facebook || websiteContacts.social?.facebook || null,
      instagram: websiteContacts.social?.instagram || null,

      // Informações Adicionais (Apollo)
      setor: apolloData?.industry || null,
      descricao: apolloData?.description || null,
      num_funcionarios: apolloData?.num_employees || null,
      logo_url: apolloData?.logo_url || null,
      ano_fundacao: apolloData?.founded_year || null,

      // Quantidade de sócios (para exibir botão "Ver Sócios")
      qtd_socios: brasilData.socios?.length || 0,

      // Raw data
      raw_brasilapi: brasilData.raw_brasilapi,
      raw_apollo: apolloData?.raw_apollo || null
    };

    // ========================================
    // 7. MONTAR DADOS DOS SÓCIOS (separado)
    // ========================================
    const socios = (brasilData.socios || []).map(socio => ({
      nome: socio.nome,
      cpf: socio.cpf, // CPF mascarado da Receita Federal
      cargo: socio.cargo,
      qualificacao: socio.qualificacao,
      data_entrada: socio.data_entrada,
      faixa_etaria: socio.faixa_etaria,
      pais_origem: socio.pais_origem,
      // LinkedIn será buscado sob demanda via /socios endpoint
      linkedin: null,
      email: null
    }));

    return res.json({
      exists: false,
      message: 'Detalhes da empresa. Aguardando aprovacao.',
      empresa: empresa,
      socios: socios
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
 * POST /api/companies/socios
 * Enrich socios with LinkedIn data (called on demand via "Ver Sócios" button)
 */
router.post('/socios', async (req, res) => {
  try {
    const { socios, empresa_nome } = req.body;

    if (!socios || !Array.isArray(socios)) {
      return res.status(400).json({ error: 'Lista de socios e obrigatoria' });
    }

    // Clean company name for searches
    let searchName = empresa_nome || '';
    searchName = searchName
      .replace(/\s*[-–]\s*[A-Z0-9\s]+$/gi, '')
      .replace(/\s+(LTDA|S\.?A\.?|S\/A|ME|EPP|EIRELI|SOCIEDADE ANONIMA|LIMITADA)\.?$/gi, '')
      .trim();
    if (searchName.length > 30) {
      searchName = searchName.split(/\s+/)[0];
    }

    console.log(`[SOCIOS] Enriquecendo ${socios.length} socios de ${searchName}`);

    const enrichedSocios = [];

    for (const socio of socios.slice(0, 10)) { // Limit to 10
      console.log(`[APOLLO] Buscando pessoa: ${socio.nome}`);

      // Try Apollo first
      const apolloPerson = await apollo.searchPerson(socio.nome, searchName);

      if (apolloPerson) {
        enrichedSocios.push({
          ...socio,
          linkedin: apolloPerson.linkedin || 'NAO_POSSUI',
          email: apolloPerson.email,
          foto_url: apolloPerson.photo_url,
          headline: apolloPerson.headline,
          titulo: apolloPerson.title,
          fonte_linkedin: 'apollo'
        });
      } else {
        // Fallback to Serper
        const linkedinUrl = await serper.findPersonLinkedin(socio.nome, searchName);
        enrichedSocios.push({
          ...socio,
          linkedin: linkedinUrl || 'NAO_POSSUI',
          email: null,
          foto_url: null,
          headline: null,
          fonte_linkedin: linkedinUrl ? 'serper' : null
        });
      }

      // Rate limit: wait 200ms between requests
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    return res.json({
      success: true,
      socios: enrichedSocios
    });

  } catch (error) {
    console.error('[SOCIOS ERROR]', error);
    res.status(500).json({
      error: 'Erro ao enriquecer socios',
      details: error.message
    });
  }
});

/**
 * POST /api/companies/approve
 * Approve and insert company + socios into database
 * Empresa and Socios are saved separately
 */
router.post('/approve', async (req, res) => {
  try {
    const { empresa, socios, aprovado_por } = req.body;

    if (!empresa || !empresa.cnpj) {
      return res.status(400).json({ error: 'Dados da empresa sao obrigatorios' });
    }

    if (!aprovado_por) {
      return res.status(400).json({ error: 'Aprovador e obrigatorio' });
    }

    const cleanCnpj = empresa.cnpj.replace(/[^\d]/g, '');

    // Check if already exists
    const existing = await findCompanyByCnpj(cleanCnpj);
    if (existing) {
      return res.status(409).json({
        error: 'Empresa ja cadastrada',
        empresa: existing
      });
    }

    // Insert company (dim_empresas)
    const insertedCompany = await insertCompany({
      cnpj: cleanCnpj,
      razao_social: empresa.razao_social,
      nome_fantasia: empresa.nome_fantasia,
      situacao_cadastral: empresa.situacao_cadastral,
      data_fundacao: empresa.data_abertura,
      logradouro: empresa.logradouro,
      numero: empresa.numero,
      complemento: empresa.complemento,
      bairro: empresa.bairro,
      cidade: empresa.cidade,
      estado: empresa.estado,
      cep: empresa.cep,
      codigo_municipio_ibge: empresa.codigo_municipio_ibge,
      telefone_1: empresa.telefone_1,
      telefone_2: empresa.telefone_2,
      email: empresa.email,
      website: empresa.website,
      linkedin: empresa.linkedin,
      logo_url: empresa.logo_url,
      twitter: empresa.twitter,
      facebook: empresa.facebook,
      instagram: empresa.instagram,
      raw_brasilapi: empresa.raw_brasilapi || {},
      raw_apollo: empresa.raw_apollo || {},
      aprovado_por: aprovado_por
    });

    // Insert regime tributario (fato_regime_tributario)
    const regimeTributario = (empresa.simples_nacional || empresa.simei)
      ? (empresa.simei ? 'MEI' : 'SIMPLES_NACIONAL')
      : 'LUCRO_PRESUMIDO';

    await insertRegimeTributario({
      empresa_id: insertedCompany.id,
      porte: empresa.porte,
      natureza_juridica: empresa.natureza_juridica,
      capital_social: empresa.capital_social,
      cnae_principal: empresa.cnae_principal,
      cnae_descricao: empresa.cnae_descricao,
      regime_tributario: regimeTributario,
      setor: empresa.setor,
      descricao: empresa.descricao,
      qtd_funcionarios: empresa.num_funcionarios ? parseInt(empresa.num_funcionarios) : null
    });

    // Insert socios
    const insertedSocios = [];

    if (socios && socios.length > 0) {
      for (const socio of socios) {
        const linkedinValue = socio.linkedin === 'NAO_POSSUI' ? null : socio.linkedin;

        // Insert person (dim_pessoas)
        const person = await insertPerson({
          nome: socio.nome,
          cpf: socio.cpf || null,
          linkedin: linkedinValue,
          email: socio.email || null,
          foto_url: socio.foto_url || null,
          faixa_etaria: socio.faixa_etaria,
          pais_origem: socio.pais_origem
        });

        // Insert transaction (fato_transacao_empresas)
        await insertTransacaoEmpresa({
          pessoa_id: person.id,
          empresa_id: insertedCompany.id,
          tipo_transacao: 'entrada_sociedade',
          data_transacao: socio.data_entrada || null,
          qualificacao: socio.qualificacao,
          cargo: socio.cargo || socio.qualificacao || 'Socio',
          headline: socio.headline || null,
          tipo: 'fundador',
          logo_url: socio.foto_url || null
        });

        insertedSocios.push(person);
      }
    }

    console.log(`[APPROVED] Empresa ${cleanCnpj} aprovada por ${aprovado_por} com ${insertedSocios.length} socios`);

    return res.json({
      success: true,
      message: 'Empresa aprovada e cadastrada com sucesso',
      empresa: insertedCompany,
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
