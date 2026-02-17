-- Migration 013: Standardize location columns and add CNAE FK
-- Date: 2026-02-17
-- Version: 013
-- Description: Padronizar codigo_ibge como unica referencia geografica,
--              remover colunas redundantes (cidade, estado, codigo_municipio_ibge),
--              adicionar FK para raw_cnae

-- ===========================================
-- 1. GARANTIR QUE codigo_ibge EXISTE
-- ===========================================

ALTER TABLE dim_empresas
    ADD COLUMN IF NOT EXISTS codigo_ibge VARCHAR(7);

-- Migrar dados de codigo_municipio_ibge para codigo_ibge (se existir)
UPDATE dim_empresas
SET codigo_ibge = codigo_municipio_ibge
WHERE codigo_ibge IS NULL
  AND codigo_municipio_ibge IS NOT NULL;

-- Indice para joins geograficos
CREATE INDEX IF NOT EXISTS idx_dim_empresas_codigo_ibge ON dim_empresas(codigo_ibge);

-- ===========================================
-- 2. REMOVER COLUNAS REDUNDANTES
-- ===========================================

-- cidade e estado serao obtidos via MCP brasil-data-hub (join com geo_municipios)
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS cidade;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS estado;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS codigo_municipio_ibge;

-- ===========================================
-- 3. ADICIONAR CNAE FK
-- ===========================================

-- Adicionar coluna cnae_id referenciando raw_cnae
ALTER TABLE dim_empresas
    ADD COLUMN IF NOT EXISTS cnae_id UUID REFERENCES raw_cnae(id);

-- Indice para joins com CNAE
CREATE INDEX IF NOT EXISTS idx_dim_empresas_cnae_id ON dim_empresas(cnae_id);

-- Comentarios
COMMENT ON COLUMN dim_empresas.codigo_ibge IS 'Codigo IBGE do municipio (7 digitos) - FK para geo_municipios via brasil-data-hub MCP';
COMMENT ON COLUMN dim_empresas.cnae_id IS 'FK para raw_cnae - atividade economica principal da empresa';

-- ===========================================
-- 4. CRIAR VIEW PARA DADOS COMPLETOS (com cidade/estado)
-- ===========================================

-- Esta view sera usada quando precisar dos dados geograficos completos
-- Os dados de municipio/estado virao via MCP brasil-data-hub
-- A view serve como documentacao da estrutura esperada

-- DROP VIEW IF EXISTS vw_empresas_completas;
-- CREATE VIEW vw_empresas_completas AS
-- SELECT
--     e.*,
--     -- Dados geograficos virao do brasil-data-hub via MCP
--     NULL::VARCHAR(100) as municipio_nome,
--     NULL::VARCHAR(2) as uf,
--     NULL::VARCHAR(50) as regiao,
--     -- Dados CNAE
--     c.codigo as cnae_codigo,
--     c.descricao as cnae_descricao,
--     c.secao as cnae_secao,
--     c.descricao_secao as cnae_secao_nome
-- FROM dim_empresas e
-- LEFT JOIN raw_cnae c ON e.cnae_id = c.id;

-- ===========================================
-- SUMARIO DA MIGRATION
-- ===========================================
-- 1. Padronizado codigo_ibge como unica coluna de referencia geografica
-- 2. Removidas colunas redundantes: cidade, estado, codigo_municipio_ibge
-- 3. Adicionada FK cnae_id para raw_cnae
-- 4. Dados de municipio/estado serao obtidos via MCP brasil-data-hub
