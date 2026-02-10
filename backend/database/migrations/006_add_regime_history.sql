-- Migration: Add historical regime data and inference fields
-- Date: 2026-02-10

-- ===========================================
-- 1. ADICIONAR COLUNAS HISTÓRICAS
-- ===========================================

ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS data_inicio DATE;
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS data_fim DATE;
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT true;
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS motivo_exclusao TEXT;

-- Simples/MEI specific
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS simples_optante BOOLEAN;
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS simples_desde DATE;
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS mei_optante BOOLEAN;
ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS mei_desde DATE;

-- ===========================================
-- 2. CRIAR TABELA DE INFERÊNCIAS
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_inferencia_limites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- FK
    empresa_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,

    -- Inferência
    provavelmente_ultrapassou_limite BOOLEAN DEFAULT false,
    confianca VARCHAR(20),  -- baixa, media, alta
    sinais JSONB DEFAULT '[]',

    -- Dados usados na inferência
    qtd_mudancas_regime INT DEFAULT 0,
    capital_social DECIMAL(15,2),
    qtd_funcionarios INT,
    anos_operando INT,

    -- Audit
    data_analise TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fato_inferencia_empresa ON fato_inferencia_limites(empresa_id);
CREATE INDEX idx_fato_inferencia_ultrapassou ON fato_inferencia_limites(provavelmente_ultrapassou_limite);

-- ===========================================
-- 3. RAW DATA CNPJá
-- ===========================================

ALTER TABLE fato_regime_tributario ADD COLUMN IF NOT EXISTS raw_cnpja JSONB DEFAULT '{}';

-- ===========================================
-- COMENTÁRIOS
-- ===========================================

COMMENT ON TABLE fato_inferencia_limites IS 'Inferências sobre limites de regime tributário baseado em dados públicos';
COMMENT ON COLUMN fato_inferencia_limites.confianca IS 'baixa, media, alta - baseado nos sinais encontrados';
COMMENT ON COLUMN fato_inferencia_limites.sinais IS 'Lista de sinais que indicam possível ultrapassagem de limite';
COMMENT ON COLUMN fato_regime_tributario.motivo_exclusao IS 'Motivo da exclusão do regime (quando disponível)';