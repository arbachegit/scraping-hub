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

      // Classification (BrasilAPI)
      cnae_principal: company.cnae_principal,
      cnae_descricao: company.cnae_descricao,
      porte: company.porte,
      natureza_juridica: company.natureza_juridica,
      situacao_cadastral: company.situacao_cadastral,
      capital_social: company.capital_social,
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
      data_fundacao: company.data_fundacao,
      num_funcionarios: company.num_funcionarios,
      logo_url: company.logo_url,

      // Raw data
      raw_brasilapi: company.raw_brasilapi,
      raw_serper: company.raw_serper,

      // Metadata
      fonte: 'brasilapi+serper',
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
  const { data, error } = await supabase
    .from('dim_pessoas')
    .insert([{
      nome: person.nome,
      cpf: person.cpf, // CPF from BrasilAPI QSA
      linkedin: person.linkedin,
      cargo: person.cargo,
      qualificacao: person.qualificacao,
      empresa_id: person.empresa_id,
      tipo: person.tipo || 'fundador',
      data_entrada_sociedade: person.data_entrada_sociedade,
      faixa_etaria: person.faixa_etaria,
      pais_origem: person.pais_origem,
      fonte: 'brasilapi+serper',
      data_coleta: new Date().toISOString()
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
