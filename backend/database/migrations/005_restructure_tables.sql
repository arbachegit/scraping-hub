-- Migration: Restructure tables - move columns to fact tables
-- Date: 2026-02-10

-- ===========================================
-- 1. MODIFICAR fato_transacao_empresas (adicionar colunas)
-- ===========================================

ALTER TABLE fato_transacao_empresas ADD COLUMN IF NOT EXISTS cargo VARCHAR(255);
ALTER TABLE fato_transacao_empresas ADD COLUMN IF NOT EXISTS headline VARCHAR(500);
ALTER TABLE fato_transacao_empresas ADD COLUMN IF NOT EXISTS tipo VARCHAR(50);
ALTER TABLE fato_transacao_empresas ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);

-- ===========================================
-- 2. MODIFICAR dim_pessoas (remover colunas)
-- ===========================================

ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS cargo_atual;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS empresa_atual_id;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS headline;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS qualificacao;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS tipo;

-- ===========================================
-- 3. CRIAR fato_regime_tributario
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_regime_tributario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- FK
    empresa_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,

    -- Classificacao
    porte VARCHAR(50),
    natureza_juridica VARCHAR(100),
    capital_social DECIMAL(15,2),

    -- CNAE
    cnae_principal VARCHAR(10),
    cnae_descricao VARCHAR(255),

    -- Regime Tributario
    regime_tributario VARCHAR(50),  -- SIMPLES_NACIONAL, LUCRO_PRESUMIDO, LUCRO_REAL, MEI

    -- Informacoes Adicionais
    setor VARCHAR(100),
    descricao TEXT,
    qtd_funcionarios INT,

    -- Audit
    data_registro TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Uma empresa pode ter multiplos registros (historico)
    UNIQUE(empresa_id, data_registro)
);

CREATE INDEX idx_fato_regime_empresa ON fato_regime_tributario(empresa_id);
CREATE INDEX idx_fato_regime_tipo ON fato_regime_tributario(regime_tributario);

-- ===========================================
-- 4. MODIFICAR dim_empresas (remover colunas)
-- ===========================================

ALTER TABLE dim_empresas DROP COLUMN IF EXISTS porte;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS natureza_juridica;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS capital_social;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS cnae_principal;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS cnae_descricao;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS simples_nacional;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS simei;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS setor;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS descricao;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS qtd_funcionarios;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS num_funcionarios;

-- ===========================================
-- COMENTARIOS
-- ===========================================

COMMENT ON TABLE fato_regime_tributario IS 'Historico de regime tributario e classificacao da empresa';
COMMENT ON COLUMN fato_regime_tributario.regime_tributario IS 'SIMPLES_NACIONAL, LUCRO_PRESUMIDO, LUCRO_REAL, MEI';
COMMENT ON COLUMN fato_transacao_empresas.cargo IS 'Cargo da pessoa na empresa';
COMMENT ON COLUMN fato_transacao_empresas.headline IS 'Headline do LinkedIn';
COMMENT ON COLUMN fato_transacao_empresas.logo_url IS 'URL do logo/foto';
