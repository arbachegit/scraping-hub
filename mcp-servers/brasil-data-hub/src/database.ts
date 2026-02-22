/**
 * Database client for brasil-data-hub
 * Connects to external Supabase instance
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';
import type {
  ListPoliticosInput,
  ListMandatosInput,
  Politico,
  Mandato,
  PoliticoComMandatos,
} from './schemas.js';

let supabase: SupabaseClient | null = null;

/**
 * Get or create Supabase client for brasil-data-hub
 */
export function getClient(): SupabaseClient {
  if (supabase) return supabase;

  const url = process.env.BRASIL_DATA_HUB_URL;
  const key = process.env.BRASIL_DATA_HUB_KEY;

  if (!url || !key) {
    throw new Error('BRASIL_DATA_HUB_URL and BRASIL_DATA_HUB_KEY are required');
  }

  supabase = createClient(url, key);
  return supabase;
}

/**
 * List politicians with optional filters
 */
export async function listPoliticos(
  params: ListPoliticosInput
): Promise<{ data: Politico[]; count: number }> {
  const client = getClient();

  let query = client
    .from('dim_politicos')
    .select('*', { count: 'exact' });

  if (params.nome) {
    query = query.ilike('nome_completo', `%${params.nome}%`);
  }

  if (params.uf) {
    query = query.eq('uf_nascimento', params.uf);
  }

  // Apply pagination
  query = query
    .range(params.offset, params.offset + params.limit - 1)
    .order('nome_completo', { ascending: true });

  const { data, error, count } = await query;

  if (error) {
    throw new Error(`Failed to list politicos: ${error.message}`);
  }

  return { data: data || [], count: count || 0 };
}

/**
 * Get politician by ID
 */
export async function getPolitico(id: string): Promise<Politico | null> {
  const client = getClient();

  const { data, error } = await client
    .from('dim_politicos')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    if (error.code === 'PGRST116') return null; // Not found
    throw new Error(`Failed to get politico: ${error.message}`);
  }

  return data;
}

/**
 * Get politician with all mandates
 */
export async function getPoliticoComMandatos(
  id: string
): Promise<PoliticoComMandatos | null> {
  const client = getClient();

  // Get politician
  const { data: politico, error: politicoError } = await client
    .from('dim_politicos')
    .select('*')
    .eq('id', id)
    .single();

  if (politicoError) {
    if (politicoError.code === 'PGRST116') return null;
    throw new Error(`Failed to get politico: ${politicoError.message}`);
  }

  // Get mandates
  const { data: mandatos, error: mandatosError } = await client
    .from('fato_politicos_mandatos')
    .select('*')
    .eq('politico_id', id)
    .order('data_inicio', { ascending: false });

  if (mandatosError) {
    throw new Error(`Failed to get mandatos: ${mandatosError.message}`);
  }

  return { ...politico, mandatos: mandatos || [] };
}

/**
 * List mandates with optional filters
 */
export async function listMandatos(
  params: ListMandatosInput
): Promise<{ data: Mandato[]; count: number }> {
  const client = getClient();

  let query = client
    .from('fato_politicos_mandatos')
    .select('*', { count: 'exact' });

  if (params.politico_id) {
    query = query.eq('politico_id', params.politico_id);
  }

  if (params.legislatura) {
    query = query.eq('legislatura', params.legislatura);
  }

  if (params.cargo) {
    query = query.ilike('cargo', `%${params.cargo}%`);
  }

  if (params.uf) {
    query = query.eq('uf', params.uf);
  }

  if (params.situacao !== 'todos') {
    query = query.eq('situacao', params.situacao);
  }

  // Apply pagination
  query = query
    .range(params.offset, params.offset + params.limit - 1)
    .order('data_inicio', { ascending: false });

  const { data, error, count } = await query;

  if (error) {
    throw new Error(`Failed to list mandatos: ${error.message}`);
  }

  return { data: data || [], count: count || 0 };
}

/**
 * Get mandate by ID
 */
export async function getMandato(id: string): Promise<Mandato | null> {
  const client = getClient();

  const { data, error } = await client
    .from('fato_politicos_mandatos')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    if (error.code === 'PGRST116') return null;
    throw new Error(`Failed to get mandato: ${error.message}`);
  }

  return data;
}

/**
 * Search politicians by name (fuzzy search)
 */
export async function searchPoliticos(
  query: string,
  limit: number = 20
): Promise<Politico[]> {
  const client = getClient();

  const { data, error } = await client
    .from('dim_politicos')
    .select('*')
    .or(`nome_completo.ilike.%${query}%,nome_urna.ilike.%${query}%`)
    .limit(limit)
    .order('nome_completo', { ascending: true });

  if (error) {
    throw new Error(`Failed to search politicos: ${error.message}`);
  }

  return data || [];
}

/**
 * Get statistics for dashboard
 */
export async function getStats(): Promise<{
  politicos: number;
  mandatos: number;
}> {
  const client = getClient();

  const [politicosResult, mandatosResult] = await Promise.all([
    client.from('dim_politicos').select('id', { count: 'exact', head: true }),
    client.from('fato_politicos_mandatos').select('id', { count: 'exact', head: true }),
  ]);

  return {
    politicos: politicosResult.count || 0,
    mandatos: mandatosResult.count || 0,
  };
}
