-- Migration: Add missing columns for BrasilAPI integration
-- Date: 2026-02-09
-- Note: Tables dim_empresas and dim_pessoas already exist with schema_star.sql structure

-- ===========================================
-- ADD MISSING COLUMNS TO dim_empresas
-- ===========================================

-- BrasilAPI specific fields
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS telefone_1 VARCHAR(20);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS telefone_2 VARCHAR(20);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS codigo_municipio_ibge VARCHAR(7);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS simples_nacional BOOLEAN;
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS simei BOOLEAN;

-- Serper enrichment fields
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS descricao TEXT;
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS num_funcionarios VARCHAR(50);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS data_fundacao VARCHAR(50);

-- Raw data storage
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS raw_brasilapi JSONB DEFAULT '{}';
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS raw_serper JSONB DEFAULT '{}';

-- Approval tracking
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS fonte VARCHAR(50) DEFAULT 'brasilapi+serper';
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS data_coleta TIMESTAMP DEFAULT NOW();
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS aprovado_por VARCHAR(100);

-- ===========================================
-- ADD MISSING COLUMNS TO dim_pessoas
-- ===========================================

-- CPF from BrasilAPI QSA
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS cpf VARCHAR(11);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS qualificacao VARCHAR(100);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS data_entrada_sociedade DATE;
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS faixa_etaria VARCHAR(20);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS pais_origem VARCHAR(50);
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS tipo VARCHAR(50) DEFAULT 'fundador';
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS data_coleta TIMESTAMP DEFAULT NOW();

-- ===========================================
-- INDEXES
-- ===========================================

CREATE INDEX IF NOT EXISTS idx_empresas_situacao ON dim_empresas(situacao_cadastral);
CREATE INDEX IF NOT EXISTS idx_empresas_simples ON dim_empresas(simples_nacional) WHERE simples_nacional = true;
CREATE INDEX IF NOT EXISTS idx_pessoas_cpf ON dim_pessoas(cpf) WHERE cpf IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pessoas_tipo ON dim_pessoas(tipo);

-- ===========================================
-- COMMENTS
-- ===========================================

COMMENT ON COLUMN dim_empresas.telefone_1 IS 'Telefone principal (BrasilAPI)';
COMMENT ON COLUMN dim_empresas.telefone_2 IS 'Telefone secundario (BrasilAPI)';
COMMENT ON COLUMN dim_empresas.simples_nacional IS 'Optante pelo Simples Nacional';
COMMENT ON COLUMN dim_empresas.simei IS 'Microempreendedor Individual (MEI)';
COMMENT ON COLUMN dim_empresas.raw_brasilapi IS 'Dados brutos da BrasilAPI/Receita Federal';
COMMENT ON COLUMN dim_empresas.raw_serper IS 'Dados brutos do Serper (Google Search)';
COMMENT ON COLUMN dim_pessoas.cpf IS 'CPF do socio (quando disponivel no QSA)';
COMMENT ON COLUMN dim_pessoas.qualificacao IS 'Qualificacao do socio (Administrador, Socio, etc)';
