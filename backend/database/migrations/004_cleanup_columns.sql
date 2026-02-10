-- Migration: Cleanup columns and create fato_transacao_empresas
-- Date: 2026-02-10

-- ===========================================
-- dim_empresas: REMOVER COLUNAS NAO UTILIZADAS
-- ===========================================

ALTER TABLE dim_empresas DROP COLUMN IF EXISTS fundadores;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS subsetor;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS segmento;
ALTER TABLE dim_empresas DROP COLUMN IF EXISTS faixa_faturamento;

-- ===========================================
-- dim_empresas: ADICIONAR INSTAGRAM
-- ===========================================

ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS instagram VARCHAR(500);

COMMENT ON COLUMN dim_empresas.instagram IS 'Instagram da empresa (coletado via Serper)';

-- ===========================================
-- dim_pessoas: REMOVER COLUNAS NAO UTILIZADAS
-- ===========================================

ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS empresa_atual_nome;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS telefone;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS linkedin_id;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS twitter_url;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS github_url;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS cidade;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS estado;
ALTER TABLE dim_pessoas DROP COLUMN IF EXISTS data_entrada_sociedade;

-- ===========================================
-- CRIAR: fato_transacao_empresas
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_transacao_empresas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves estrangeiras
    pessoa_id UUID NOT NULL REFERENCES dim_pessoas(id) ON DELETE CASCADE,
    empresa_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,

    -- Dados da transacao
    tipo_transacao VARCHAR(50) NOT NULL DEFAULT 'entrada_sociedade',
    data_transacao DATE,
    qualificacao VARCHAR(100),

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Evitar duplicatas
    UNIQUE(pessoa_id, empresa_id, tipo_transacao, data_transacao)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_fato_transacao_pessoa ON fato_transacao_empresas(pessoa_id);
CREATE INDEX IF NOT EXISTS idx_fato_transacao_empresa ON fato_transacao_empresas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_fato_transacao_tipo ON fato_transacao_empresas(tipo_transacao);
CREATE INDEX IF NOT EXISTS idx_fato_transacao_data ON fato_transacao_empresas(data_transacao DESC);

-- Comentarios
COMMENT ON TABLE fato_transacao_empresas IS 'Historico de transacoes societarias (entrada, saida, alteracao)';
COMMENT ON COLUMN fato_transacao_empresas.tipo_transacao IS 'entrada_sociedade, saida_sociedade, alteracao_cargo';
COMMENT ON COLUMN fato_transacao_empresas.data_transacao IS 'Data da transacao (ex: data_entrada_sociedade)';
COMMENT ON COLUMN fato_transacao_empresas.qualificacao IS 'Cargo/qualificacao do socio (Administrador, Socio, etc)';
