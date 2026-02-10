import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('SUPABASE_URL and SUPABASE_SERVICE_KEY are required');
}

export const supabase = createClient(supabaseUrl, supabaseKey);

/**
 * Insert company into dim_empresas
 * Sources: BrasilAPI (official) + Serper (enrichment)
 * @param {Object} company - Company data
 * @returns {Promise<Object>} Inserted company
 */
export async function insertCompany(company) {
  const { data, error } = await supabase
    .from('dim_empresas')
    .insert([{
      // Identification
      cnpj: company.cnpj,
      razao_social: company.razao_social,
      nome_fantasia: company.nome_fantasia,

      // Status
      situacao_cadastral: company.situacao_cadastral,
      data_abertura: company.data_fundacao,
      data_fundacao: company.data_fundacao,

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
      telefone: company.telefone_1,
      telefone_1: company.telefone_1,
      telefone_2: company.telefone_2,
      email: company.email,

      // Digital presence
      website: company.website,
      linkedin_url: company.linkedin,
      logo_url: company.logo_url,

      // Social media (Apollo/Serper)
      twitter_url: company.twitter,
      facebook_url: company.facebook,
      instagram: company.instagram,

      // Raw data
      raw_cnpj_data: company.raw_brasilapi,
      raw_brasilapi: company.raw_brasilapi,
      raw_apollo: company.raw_apollo,

      // Metadata
      fonte: 'brasilapi+serper+apollo',
      data_coleta: new Date().toISOString(),
      aprovado_por: company.aprovado_por
    }])
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Insert person into dim_pessoas
 * CPF from BrasilAPI QSA, LinkedIn from Serper
 * @param {Object} person - Person data
 * @returns {Promise<Object>} Inserted person
 */
export async function insertPerson(person) {
  // Extract first and last name
  const nameParts = (person.nome || '').split(' ');
  const firstName = nameParts[0] || '';
  const lastName = nameParts.slice(1).join(' ') || '';

  const { data, error } = await supabase
    .from('dim_pessoas')
    .insert([{
      // Name
      nome_completo: person.nome,
      primeiro_nome: firstName,
      sobrenome: lastName,

      // CPF from BrasilAPI QSA
      cpf: person.cpf,

      // LinkedIn and contact
      linkedin_url: person.linkedin,
      email: person.email,
      foto_url: person.foto_url,

      // BrasilAPI QSA fields
      faixa_etaria: person.faixa_etaria,
      pais: person.pais_origem || 'Brasil',

      // Raw data
      raw_apollo_data: person.raw_apollo,

      // Metadata
      fonte: 'brasilapi+serper+apollo',
      data_coleta: new Date().toISOString()
    }])
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Insert transaction into fato_transacao_empresas
 * @param {Object} transacao - Transaction data
 * @returns {Promise<Object>} Inserted transaction
 */
export async function insertTransacaoEmpresa(transacao) {
  const { data, error } = await supabase
    .from('fato_transacao_empresas')
    .insert([{
      pessoa_id: transacao.pessoa_id,
      empresa_id: transacao.empresa_id,
      tipo_transacao: transacao.tipo_transacao || 'entrada_sociedade',
      data_transacao: transacao.data_transacao,
      qualificacao: transacao.qualificacao,
      cargo: transacao.cargo,
      headline: transacao.headline,
      tipo: transacao.tipo || 'fundador',
      logo_url: transacao.logo_url
    }])
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Insert regime tributario into fato_regime_tributario
 */
export async function insertRegimeTributario(regime) {
  const { data, error } = await supabase
    .from('fato_regime_tributario')
    .insert([{
      empresa_id: regime.empresa_id,
      porte: regime.porte,
      natureza_juridica: regime.natureza_juridica,
      capital_social: regime.capital_social,
      cnae_principal: regime.cnae_principal,
      cnae_descricao: regime.cnae_descricao,
      regime_tributario: regime.regime_tributario,
      setor: regime.setor,
      descricao: regime.descricao,
      qtd_funcionarios: regime.qtd_funcionarios
    }])
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Check if company exists by CNPJ
 * @param {string} cnpj - Company CNPJ
 * @returns {Promise<Object|null>} Company or null
 */
export async function findCompanyByCnpj(cnpj) {
  const { data, error } = await supabase
    .from('dim_empresas')
    .select('*')
    .eq('cnpj', cnpj)
    .single();

  if (error && error.code !== 'PGRST116') throw error;
  return data;
}
