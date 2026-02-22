/**
 * Zod schemas for brasil-data-hub MCP validation
 * Following /skill-api-validation-zod and /skill-normalize-identifiers
 */

import { z } from 'zod';

// ============================================
// INPUT SCHEMAS (Request Validation)
// ============================================

/**
 * Schema for listing politicians
 * Follows snake_case for database fields
 */
export const listPoliticosInputSchema = z.object({
  nome: z.string().max(200).optional(),
  partido: z.string().max(50).optional(),
  uf: z
    .string()
    .length(2)
    .transform((v) => v.toUpperCase())
    .optional(),
  cargo: z.string().max(100).optional(),
  limit: z.number().int().min(1).max(500).default(50),
  offset: z.number().int().min(0).default(0),
});

/**
 * Schema for getting politician by ID
 */
export const getPoliticoInputSchema = z.object({
  id: z.string().uuid(),
});

/**
 * Schema for listing mandates
 */
export const listMandatosInputSchema = z.object({
  politico_id: z.string().uuid().optional(),
  legislatura: z.number().int().min(1).max(100).optional(),
  cargo: z.string().max(100).optional(),
  uf: z
    .string()
    .length(2)
    .transform((v) => v.toUpperCase())
    .optional(),
  situacao: z.enum(['ativo', 'inativo', 'todos']).default('todos'),
  limit: z.number().int().min(1).max(500).default(50),
  offset: z.number().int().min(0).default(0),
});

/**
 * Schema for getting mandate by ID
 */
export const getMandatoInputSchema = z.object({
  id: z.string().uuid(),
});

/**
 * Schema for searching politicians
 */
export const searchPoliticosInputSchema = z.object({
  query: z.string().min(2).max(200),
  limit: z.number().int().min(1).max(100).default(20),
});

// ============================================
// OUTPUT SCHEMAS (Response Types)
// ============================================

/**
 * Politician entity schema
 * Maps to dim_politicos table
 */
export const politicoSchema = z.object({
  id: z.string().uuid(),
  nome_completo: z.string(),
  nome_urna: z.string().nullable(),
  cpf: z.string().nullable(),
  data_nascimento: z.string().nullable(),
  sexo: z.enum(['M', 'F']).nullable(),
  uf_nascimento: z.string().nullable(),
  municipio_nascimento: z.string().nullable(),
  escolaridade: z.string().nullable(),
  ocupacao: z.string().nullable(),
  email: z.string().email().nullable(),
  foto_url: z.string().url().nullable(),
  created_at: z.string().datetime().optional(),
  updated_at: z.string().datetime().optional(),
});

/**
 * Mandate entity schema
 * Maps to fato_politicos_mandatos table
 */
export const mandatoSchema = z.object({
  id: z.string().uuid(),
  politico_id: z.string().uuid(),
  cargo: z.string(),
  uf: z.string(),
  municipio: z.string().nullable(),
  partido: z.string(),
  numero_candidato: z.string().nullable(),
  legislatura: z.number().int().nullable(),
  data_inicio: z.string().nullable(),
  data_fim: z.string().nullable(),
  situacao: z.string().nullable(),
  votos_totais: z.number().int().nullable(),
  percentual_votos: z.number().nullable(),
  created_at: z.string().datetime().optional(),
});

/**
 * Politician with mandates (joined)
 */
export const politicoComMandatosSchema = politicoSchema.extend({
  mandatos: z.array(mandatoSchema).optional(),
});

// ============================================
// TYPE EXPORTS
// ============================================

export type ListPoliticosInput = z.infer<typeof listPoliticosInputSchema>;
export type GetPoliticoInput = z.infer<typeof getPoliticoInputSchema>;
export type ListMandatosInput = z.infer<typeof listMandatosInputSchema>;
export type GetMandatoInput = z.infer<typeof getMandatoInputSchema>;
export type SearchPoliticosInput = z.infer<typeof searchPoliticosInputSchema>;

export type Politico = z.infer<typeof politicoSchema>;
export type Mandato = z.infer<typeof mandatoSchema>;
export type PoliticoComMandatos = z.infer<typeof politicoComMandatosSchema>;
