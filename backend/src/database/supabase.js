/**
 * Supabase Client - Node.js
 */

import { createClient } from '@supabase/supabase-js';
import pino from 'pino';

const logger = pino({ name: 'supabase' });

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_KEY;

if (!supabaseUrl || !supabaseKey) {
  logger.warn('Supabase não configurado');
}

export const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey)
  : null;

/**
 * Repository para dim_empresas
 */
export class EmpresaRepository {
  constructor() {
    this.tableName = 'dim_empresas';
  }

  async upsert(data) {
    if (!supabase) return null;

    try {
      const record = {
        cnpj: data.cnpj?.replace(/\D/g, ''),
        cnae_principal: data.cnae_principal || data.cnae,
        cnae_descricao: data.cnae_descricao,
        razao_social: data.razao_social || data.nome_fantasia || data.name,
        nome_fantasia: data.nome_fantasia || data.name,
        logradouro: data.logradouro,
        numero: data.numero,
        complemento: data.complemento,
        bairro: data.bairro,
        cidade: data.cidade || data.municipio,
        estado: data.estado || data.uf,
        cep: data.cep,
        fundadores: data.fundadores || [],
        website: data.website,
        telefone: data.telefone,
        email: data.email,
        porte: data.porte,
        setor: data.setor || data.industry,
        palavras_chave: data.palavras_chave || [],
        raw_cnpj_data: data.raw_cnpj_data || {},
        raw_search_data: data.raw_search_data || {},
        updated_at: new Date().toISOString()
      };

      // Remove null values
      Object.keys(record).forEach(key => {
        if (record[key] === null || record[key] === undefined) {
          delete record[key];
        }
      });

      let result;
      if (record.cnpj) {
        result = await supabase
          .from(this.tableName)
          .upsert(record, { onConflict: 'cnpj' })
          .select();
      } else {
        result = await supabase
          .from(this.tableName)
          .upsert(record)
          .select();
      }

      if (result.error) throw result.error;

      logger.info({ id: result.data?.[0]?.id, nome: record.nome_fantasia }, 'Empresa salva');
      return result.data?.[0]?.id;

    } catch (error) {
      logger.error({ error: error.message }, 'Erro ao salvar empresa');
      return null;
    }
  }

  async getById(id) {
    if (!supabase) return null;
    const { data, error } = await supabase
      .from(this.tableName)
      .select('*')
      .eq('id', id)
      .single();
    return error ? null : data;
  }

  async getByNome(nome) {
    if (!supabase) return null;
    const { data, error } = await supabase
      .from(this.tableName)
      .select('*')
      .ilike('nome_fantasia', `%${nome}%`)
      .limit(1);
    return error ? null : data?.[0];
  }

  async updateKeywords(empresaId, keywords) {
    if (!supabase) return false;
    const { error } = await supabase
      .from(this.tableName)
      .update({
        palavras_chave: keywords,
        updated_at: new Date().toISOString()
      })
      .eq('id', empresaId);
    return !error;
  }
}

/**
 * Repository para dim_pessoas
 */
export class PessoaRepository {
  constructor() {
    this.tableName = 'dim_pessoas';
  }

  async upsert(data) {
    if (!supabase) return null;

    try {
      const nomeCompleto = data.name || data.nome_completo || '';
      const partesNome = nomeCompleto.split(' ');

      const record = {
        nome_completo: nomeCompleto,
        primeiro_nome: partesNome[0],
        sobrenome: partesNome.slice(1).join(' ') || null,
        email: data.email,
        telefone: data.phone || data.telefone,
        linkedin_url: data.linkedin_url,
        linkedin_id: data.linkedin_id || data.id,
        foto_url: data.photo_url || data.foto_url,
        cidade: data.city || data.cidade,
        estado: data.state || data.estado,
        cargo_atual: data.title || data.cargo_atual,
        empresa_atual_id: data.empresa_atual_id,
        empresa_atual_nome: data.organization_name || data.empresa_atual_nome,
        senioridade: data.seniority || data.senioridade,
        headline: data.headline,
        fonte: data.fonte || 'apollo',
        raw_apollo_data: data,
        updated_at: new Date().toISOString()
      };

      // Remove null values
      Object.keys(record).forEach(key => {
        if (record[key] === null || record[key] === undefined) {
          delete record[key];
        }
      });

      let result;
      if (record.linkedin_url) {
        result = await supabase
          .from(this.tableName)
          .upsert(record, { onConflict: 'linkedin_url' })
          .select();
      } else {
        result = await supabase
          .from(this.tableName)
          .upsert(record)
          .select();
      }

      if (result.error) throw result.error;

      logger.info({ id: result.data?.[0]?.id, nome: nomeCompleto }, 'Pessoa salva');
      return result.data?.[0]?.id;

    } catch (error) {
      logger.error({ error: error.message }, 'Erro ao salvar pessoa');
      return null;
    }
  }

  async getByEmpresa(empresaId) {
    if (!supabase) return [];
    const { data, error } = await supabase
      .from(this.tableName)
      .select('*')
      .eq('empresa_atual_id', empresaId);
    return error ? [] : data || [];
  }
}

/**
 * Repository para fato_analises_empresa
 */
export class AnaliseRepository {
  constructor() {
    this.tableName = 'fato_analises_empresa';
  }

  async save(empresaId, analise) {
    if (!supabase) return null;

    try {
      const blocks = analise.blocks || {};
      const synthesis = analise.synthesis || {};
      const swot = synthesis.swot || {};

      const record = {
        empresa_id: empresaId,
        tipo_analise: analise.tipo_analise || 'completa',
        tempo_processamento_segundos: analise.metadata?.processing_time_seconds,
        bloco_1_empresa: blocks['1_empresa']?.content,
        bloco_2_pessoas: blocks['2_pessoas']?.content,
        bloco_3_formacao: blocks['3_formacao']?.content,
        bloco_4_ativo_humano: blocks['4_ativo_humano']?.content,
        bloco_5_capacidade: blocks['5_capacidade']?.content,
        bloco_6_comunicacao: blocks['6_comunicacao']?.content,
        bloco_7_fraquezas: blocks['7_fraquezas']?.content,
        bloco_8_visao_leigo: blocks['8_visao_leigo']?.content,
        bloco_9_visao_profissional: blocks['9_visao_profissional']?.content,
        bloco_10_visao_concorrente: blocks['10_visao_concorrente']?.content,
        bloco_11_visao_fornecedor: blocks['11_visao_fornecedor']?.content,
        hipotese_objetivo: synthesis.hypothesis_objective,
        okrs_sugeridos: synthesis.suggested_okr,
        swot_forcas: swot.strengths || [],
        swot_fraquezas: swot.weaknesses || [],
        swot_oportunidades: swot.opportunities || [],
        swot_ameacas: swot.threats || [],
        palavras_chave: analise.palavras_chave || [],
        score_qualidade: analise.metadata?.data_quality_score,
        fontes_utilizadas: analise.metadata?.sources_used || []
      };

      const { data, error } = await supabase
        .from(this.tableName)
        .insert(record)
        .select();

      if (error) throw error;

      logger.info({ id: data?.[0]?.id, empresaId }, 'Análise salva');
      return data?.[0]?.id;

    } catch (error) {
      logger.error({ error: error.message }, 'Erro ao salvar análise');
      return null;
    }
  }
}

/**
 * Repository para fato_concorrentes
 */
export class ConcorrenteRepository {
  constructor() {
    this.tableName = 'fato_concorrentes';
  }

  async save(empresaId, concorrenteId, data) {
    if (!supabase) return null;

    try {
      const record = {
        empresa_id: empresaId,
        concorrente_id: concorrenteId,
        tipo_concorrencia: data.tipo || 'direto',
        palavras_chave_match: data.keywords_match || [],
        score_similaridade: data.similarity_score || 0.5,
        stamp: data.stamp || 'Medio',
        stamp_justificativa: data.justification || '',
        fonte_descoberta: data.fonte || 'google',
        query_utilizada: data.query,
        updated_at: new Date().toISOString()
      };

      const { data: result, error } = await supabase
        .from(this.tableName)
        .upsert(record, { onConflict: 'empresa_id,concorrente_id' })
        .select();

      if (error) throw error;
      return result?.[0]?.id;

    } catch (error) {
      logger.error({ error: error.message }, 'Erro ao salvar concorrente');
      return null;
    }
  }

  async getByEmpresa(empresaId) {
    if (!supabase) return [];
    const { data, error } = await supabase
      .from(this.tableName)
      .select(`
        *,
        concorrente:concorrente_id(id, nome_fantasia, cnpj, setor, website)
      `)
      .eq('empresa_id', empresaId);
    return error ? [] : data || [];
  }
}

export default supabase;
