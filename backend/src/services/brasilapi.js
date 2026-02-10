const BRASIL_API_URL = 'https://brasilapi.com.br/api';

/**
 * Fetch company data from BrasilAPI by CNPJ
 * @param {string} cnpj - CNPJ (14 digits only)
 * @returns {Promise<Object>} Company data from Receita Federal
 */
export async function getCompanyByCnpj(cnpj) {
  const cleanCnpj = cnpj.replace(/[^\d]/g, '');

  const response = await fetch(`${BRASIL_API_URL}/cnpj/v1/${cleanCnpj}`);

  if (!response.ok) {
    if (response.status === 404) {
      return null;
    }
    throw new Error(`BrasilAPI error: ${response.status}`);
  }

  const data = await response.json();
  return transformBrasilApiData(data);
}

/**
 * Transform BrasilAPI response to our dim_empresas format
 * @param {Object} data - Raw BrasilAPI response
 * @returns {Object} Transformed data
 */
function transformBrasilApiData(data) {
  // Extract socios (partners/founders) for dim_pessoas
  const socios = (data.qsa || []).map(socio => ({
    nome: socio.nome_socio,
    cpf: socio.cnpj_cpf_do_socio, // CPF when available
    cargo: socio.qualificacao_socio,
    data_entrada: socio.data_entrada_sociedade,
    faixa_etaria: socio.faixa_etaria,
    pais_origem: socio.pais,
    linkedin: null // Will be enriched later via Serper
  }));

  return {
    // Identification
    cnpj: data.cnpj,
    razao_social: data.razao_social,
    nome_fantasia: data.nome_fantasia || data.razao_social,

    // Classification
    porte: mapPorte(data.porte),
    natureza_juridica: data.natureza_juridica,
    situacao_cadastral: data.descricao_situacao_cadastral,
    data_situacao_cadastral: data.data_situacao_cadastral,

    // CNAE
    cnae_principal: data.cnae_fiscal?.toString(),
    cnae_descricao: data.cnae_fiscal_descricao,
    cnaes_secundarios: data.cnaes_secundarios || [],

    // Address
    logradouro: data.logradouro,
    numero: data.numero,
    complemento: data.complemento,
    bairro: data.bairro,
    cidade: data.municipio,
    estado: data.uf,
    cep: data.cep,
    codigo_municipio_ibge: data.codigo_municipio_ibge,

    // Contact
    telefone_1: data.ddd_telefone_1,
    telefone_2: data.ddd_telefone_2,
    fax: data.ddd_fax,
    email: data.email?.toLowerCase(),

    // Financial
    capital_social: data.capital_social,

    // Dates
    data_abertura: data.data_inicio_atividade,

    // Tax regime
    simples_nacional: data.opcao_pelo_simples,
    simei: data.opcao_pelo_mei,

    // Partners/Founders
    socios: socios,

    // Raw data for future reference
    raw_brasilapi: data,
    fonte: 'brasilapi'
  };
}

/**
 * Map porte code to description
 * @param {string} porte - Porte code
 * @returns {string} Porte description
 */
function mapPorte(porte) {
  const porteMap = {
    '00': 'NAO_INFORMADO',
    '01': 'MICRO_EMPRESA',
    '03': 'EMPRESA_PEQUENO_PORTE',
    '05': 'DEMAIS'
  };
  return porteMap[porte] || porte;
}

/**
 * Fetch address data by CEP
 * @param {string} cep - CEP (8 digits)
 * @returns {Promise<Object>} Address data
 */
export async function getAddressByCep(cep) {
  const cleanCep = cep.replace(/[^\d]/g, '');

  const response = await fetch(`${BRASIL_API_URL}/cep/v2/${cleanCep}`);

  if (!response.ok) {
    if (response.status === 404) {
      return null;
    }
    throw new Error(`BrasilAPI CEP error: ${response.status}`);
  }

  return response.json();
}

/**
 * Get bank info by code
 * @param {string} code - Bank code
 * @returns {Promise<Object>} Bank data
 */
export async function getBankByCode(code) {
  const response = await fetch(`${BRASIL_API_URL}/banks/v1/${code}`);

  if (!response.ok) {
    return null;
  }

  return response.json();
}
