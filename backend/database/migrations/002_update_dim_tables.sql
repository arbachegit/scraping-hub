-- Migration: Update dim tables with BrasilAPI and Serper fields
-- Date: 2026-02-09

-- ===========================================
-- UPDATE dim_empresas with BrasilAPI fields
-- ===========================================

-- Add new columns from BrasilAPI
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS cnae_principal VARCHAR(10);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS cnae_descricao VARCHAR(255);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS porte VARCHAR(50);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS natureza_juridica VARCHAR(100);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS situacao_cadastral VARCHAR(50);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS capital_social DECIMAL(15,2);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS telefone_1 VARCHAR(20);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS telefone_2 VARCHAR(20);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS cep VARCHAR(10);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS logradouro VARCHAR(255);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS numero VARCHAR(20);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS complemento VARCHAR(100);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS bairro VARCHAR(100);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS codigo_municipio_ibge VARCHAR(7);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS simples_nacional BOOLEAN;
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS simei BOOLEAN;

-- Add Serper fields not yet used
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS faturamento VARCHAR(100);

-- Raw data storage
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS raw_brasilapi JSONB DEFAULT '{}';
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS raw_serper JSONB DEFAULT '{}';

-- Indexes for new columns
CREATE INDEX IF NOT EXISTS idx_empresas_cnae ON dim_empresas(cnae_principal);
CREATE INDEX IF NOT EXISTS idx_empresas_situacao ON dim_empresas(situacao_cadastral);
CREATE INDEX IF NOT EXISTS idx_empresas_porte ON dim_empresas(porte);

-- ===========================================
-- UPDATE dim_pessoas with CPF (from QSA)
-- ===========================================

ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS cpf VARCHAR(11);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS data_entrada_sociedade DATE;
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS faixa_etaria VARCHAR(20);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS pais_origem VARCHAR(50);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS qualificacao VARCHAR(100);

-- Unique index for CPF (when available)
CREATE INDEX IF NOT EXISTS idx_pessoas_cpf ON dim_pessoas(cpf) WHERE cpf IS NOT NULL;

-- ===========================================
-- COMMENTS
-- ===========================================

COMMENT ON COLUMN dim_empresas.cnae_principal IS 'Codigo CNAE principal (BrasilAPI)';
COMMENT ON COLUMN dim_empresas.porte IS 'MEI, MICRO_EMPRESA, EMPRESA_PEQUENO_PORTE, DEMAIS';
COMMENT ON COLUMN dim_empresas.natureza_juridica IS 'Natureza juridica (ex: LTDA, S.A.)';
COMMENT ON COLUMN dim_empresas.situacao_cadastral IS 'ATIVA, INAPTA, BAIXADA, SUSPENSA';
COMMENT ON COLUMN dim_empresas.capital_social IS 'Capital social em R$';
COMMENT ON COLUMN dim_empresas.simples_nacional IS 'Optante pelo Simples Nacional';
COMMENT ON COLUMN dim_empresas.simei IS 'Microempreendedor Individual (MEI)';
COMMENT ON COLUMN dim_empresas.raw_brasilapi IS 'Dados brutos da BrasilAPI';
COMMENT ON COLUMN dim_empresas.raw_serper IS 'Dados brutos do Serper';

COMMENT ON COLUMN dim_pessoas.cpf IS 'CPF do socio (quando disponivel no QSA)';
COMMENT ON COLUMN dim_pessoas.qualificacao IS 'Qualificacao do socio (Administrador, Socio, etc)';
