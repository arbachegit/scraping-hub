-- Migration: Add VAR inference columns
-- Date: 2026-02-10

-- ===========================================
-- 1. COLUNAS PARA INFERÊNCIA DE FATURAMENTO
-- ===========================================

ALTER TABLE fato_inferencia_limites ADD COLUMN IF NOT EXISTS faturamento_estimado_min DECIMAL(15,2);
ALTER TABLE fato_inferencia_limites ADD COLUMN IF NOT EXISTS faturamento_estimado_max DECIMAL(15,2);

-- ===========================================
-- 2. COLUNAS PARA PREVISÃO DE MUDANÇA
-- ===========================================

ALTER TABLE fato_inferencia_limites ADD COLUMN IF NOT EXISTS probabilidade_mudanca_regime DECIMAL(5,2);
ALTER TABLE fato_inferencia_limites ADD COLUMN IF NOT EXISTS regime_provavel_proximo VARCHAR(50);
ALTER TABLE fato_inferencia_limites ADD COLUMN IF NOT EXISTS tempo_estimado_mudanca_meses INT;

-- ===========================================
-- 3. VARIÁVEIS DO MODELO VAR
-- ===========================================

ALTER TABLE fato_inferencia_limites ADD COLUMN IF NOT EXISTS variaveis_correlacionadas JSONB DEFAULT '{}';

-- ===========================================
-- COMENTÁRIOS
-- ===========================================

COMMENT ON COLUMN fato_inferencia_limites.faturamento_estimado_min IS 'Faturamento mínimo estimado baseado no regime e indicadores';
COMMENT ON COLUMN fato_inferencia_limites.faturamento_estimado_max IS 'Faturamento máximo estimado (limite do regime atual)';
COMMENT ON COLUMN fato_inferencia_limites.probabilidade_mudanca_regime IS 'Probabilidade (0-100) de mudar de regime nos próximos 12 meses';
COMMENT ON COLUMN fato_inferencia_limites.regime_provavel_proximo IS 'Regime tributário mais provável após mudança';
COMMENT ON COLUMN fato_inferencia_limites.tempo_estimado_mudanca_meses IS 'Tempo estimado em meses até ultrapassar limite';
COMMENT ON COLUMN fato_inferencia_limites.variaveis_correlacionadas IS 'Pesos das variáveis no modelo VAR: {funcionarios: 0.3, capital: 0.2, ...}';
