import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('SUPABASE_URL and SUPABASE_SERVICE_KEY are required');
}

export const supabase = createClient(supabaseUrl, supabaseKey);

/**
 * Insert company into dim_empresas
 * @param {Object} company - Company data
 * @returns {Promise<Object>} Inserted company
 */
export async function insertCompany(company) {
  const { data, error } = await supabase
    .from('dim_empresas')
    .insert([{
      cnpj: company.cnpj,
      razao_social: company.razao_social,
      nome_fantasia: company.nome_fantasia,
      website: company.website,
      linkedin: company.linkedin,
      endereco: company.endereco,
      cidade: company.cidade,
      estado: company.estado,
      setor: company.setor,
      descricao: company.descricao,
      data_fundacao: company.data_fundacao,
      num_funcionarios: company.num_funcionarios,
      fonte: 'serper',
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
 * @param {Object} person - Person data
 * @returns {Promise<Object>} Inserted person
 */
export async function insertPerson(person) {
  const { data, error } = await supabase
    .from('dim_pessoas')
    .insert([{
      nome: person.nome,
      linkedin: person.linkedin,
      cargo: person.cargo,
      empresa_id: person.empresa_id,
      tipo: person.tipo || 'fundador',
      fonte: 'serper',
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
