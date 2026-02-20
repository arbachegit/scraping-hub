/**
 * Zod validation schemas for API endpoints
 * CLAUDE.md Rule: "✅ ALWAYS: Validação com Zod (TS) ou Pydantic (Python)"
 */
import { z } from 'zod';

// CNPJ validation (14 digits)
const cnpjSchema = z.string()
  .transform(val => val.replace(/[^\d]/g, ''))
  .refine(val => val.length === 14, { message: 'CNPJ deve ter 14 dígitos' });

// Company search request - mínimo 3 de 4 campos preenchidos
export const searchCompanySchema = z.object({
  nome: z.string()
    .max(200, 'Nome deve ter no máximo 200 caracteres')
    .transform(val => val?.trim())
    .optional()
    .nullable(),
  cidade: z.string()
    .max(100)
    .transform(val => val?.trim())
    .optional()
    .nullable(),
  segmento: z.string()
    .max(200)
    .transform(val => val?.trim())
    .optional()
    .nullable(),
  regime: z.string()
    .max(100)
    .transform(val => val?.trim())
    .optional()
    .nullable()
}).refine(data => {
  // Contar campos preenchidos com pelo menos 2 caracteres
  const campos = [data.nome, data.cidade, data.segmento, data.regime];
  const preenchidos = campos.filter(c => c && c.length >= 2).length;
  return preenchidos >= 3;
}, {
  message: 'Preencha pelo menos 3 dos 4 campos (nome, cidade, segmento, regime)'
});

// Company details request
export const detailsCompanySchema = z.object({
  cnpj: cnpjSchema
});

// Socios enrichment request
export const sociosSchema = z.object({
  socios: z.array(z.object({
    nome: z.string().min(1),
    cpf: z.string().optional().nullable(),
    cargo: z.string().optional().nullable(),
    qualificacao: z.string().optional().nullable(),
    data_entrada: z.string().optional().nullable(),
    faixa_etaria: z.string().optional().nullable(),
    pais_origem: z.string().optional().nullable()
  })).min(1, 'Lista de sócios é obrigatória'),
  empresa_nome: z.string().optional()
});

// Company approval request
export const approveCompanySchema = z.object({
  empresa: z.object({
    cnpj: cnpjSchema,
    razao_social: z.string().min(1),
    nome_fantasia: z.string().optional().nullable(),
    situacao_cadastral: z.string().optional().nullable(),
    data_abertura: z.string().optional().nullable(),
    logradouro: z.string().optional().nullable(),
    numero: z.string().optional().nullable(),
    complemento: z.string().optional().nullable(),
    bairro: z.string().optional().nullable(),
    cidade: z.string().optional().nullable(),
    estado: z.string().optional().nullable(),
    cep: z.string().optional().nullable(),
    codigo_municipio_ibge: z.string().optional().nullable(),
    telefone_1: z.string().optional().nullable(),
    telefone_2: z.string().optional().nullable(),
    email: z.string().email().optional().nullable(),
    website: z.string().url().optional().nullable(),
    linkedin: z.string().optional().nullable(),
    logo_url: z.string().url().optional().nullable(),
    twitter: z.string().optional().nullable(),
    facebook: z.string().optional().nullable(),
    instagram: z.string().optional().nullable(),
    porte: z.string().optional().nullable(),
    natureza_juridica: z.string().optional().nullable(),
    capital_social: z.number().optional().nullable(),
    cnae_principal: z.string().optional().nullable(),
    cnae_descricao: z.string().optional().nullable(),
    regime_tributario: z.string().optional().nullable(),
    setor: z.string().optional().nullable(),
    descricao: z.string().optional().nullable(),
    num_funcionarios: z.union([z.string(), z.number()]).optional().nullable(),
    simples_optante: z.boolean().optional().nullable(),
    simples_desde: z.string().optional().nullable(),
    mei_optante: z.boolean().optional().nullable(),
    mei_desde: z.string().optional().nullable(),
    historico_regimes: z.array(z.any()).optional().nullable(),
    qtd_mudancas_regime: z.number().optional().nullable(),
    raw_brasilapi: z.any().optional(),
    raw_apollo: z.any().optional(),
    raw_cnpja: z.any().optional()
  }),
  socios: z.array(z.any()).optional().nullable(),
  aprovado_por: z.string().min(1, 'Aprovador é obrigatório')
});

// VAR recalculation request
export const recalculateSchema = z.object({
  qtd_funcionarios: z.number().int().min(0).optional(),
  capital_social: z.number().min(0).optional()
});

// UUID param validation
export const uuidParamSchema = z.object({
  id: z.string().uuid('ID inválido')
});

/**
 * Validate request body with Zod schema
 * @param {z.ZodSchema} schema - Zod schema to validate against
 * @returns {Function} Express middleware
 */
export function validateBody(schema) {
  return (req, res, next) => {
    try {
      req.body = schema.parse(req.body);
      next();
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({
          error: 'Dados inválidos',
          details: error.errors.map(e => ({
            field: e.path.join('.'),
            message: e.message
          }))
        });
      }
      next(error);
    }
  };
}

/**
 * Validate request params with Zod schema
 * @param {z.ZodSchema} schema - Zod schema to validate against
 * @returns {Function} Express middleware
 */
export function validateParams(schema) {
  return (req, res, next) => {
    try {
      req.params = schema.parse(req.params);
      next();
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({
          error: 'Parâmetros inválidos',
          details: error.errors.map(e => ({
            field: e.path.join('.'),
            message: e.message
          }))
        });
      }
      next(error);
    }
  };
}
