-- Migration 014: Standardize CNAE FK in fato_regime_tributario
-- Date: 2026-02-17
-- Version: 014
-- Description: Adicionar FK cnae_id em fato_regime_tributario referenciando raw_cnae,
--              popular baseado no cnae_principal existente, e depois propagar para dim_empresas

-- ===========================================
-- 1. ADICIONAR cnae_id EM fato_regime_tributario
-- ===========================================

ALTER TABLE fato_regime_tributario
    ADD COLUMN IF NOT EXISTS cnae_id UUID REFERENCES raw_cnae(id);

-- Indice para joins
CREATE INDEX IF NOT EXISTS idx_fato_regime_cnae_id ON fato_regime_tributario(cnae_id);

-- Comentario
COMMENT ON COLUMN fato_regime_tributario.cnae_id IS 'FK para raw_cnae - substitui cnae_principal e cnae_descricao';

-- ===========================================
-- 2. POPULAR cnae_id BASEADO NO cnae_principal EXISTENTE
-- ===========================================

-- Match por codigo formatado (ex: 6201-5/00)
UPDATE fato_regime_tributario frt
SET cnae_id = rc.id
FROM raw_cnae rc
WHERE frt.cnae_principal IS NOT NULL
  AND frt.cnae_id IS NULL
  AND rc.codigo = frt.cnae_principal;

-- Match por codigo numerico (ex: 6201500)
UPDATE fato_regime_tributario frt
SET cnae_id = rc.id
FROM raw_cnae rc
WHERE frt.cnae_principal IS NOT NULL
  AND frt.cnae_id IS NULL
  AND rc.codigo_numerico = REPLACE(REPLACE(REPLACE(frt.cnae_principal, '-', ''), '/', ''), '.', '');

-- Match parcial - apenas classe (5 digitos) quando subclasse nao encontrada
UPDATE fato_regime_tributario frt
SET cnae_id = (
    SELECT rc.id
    FROM raw_cnae rc
    WHERE rc.classe = LEFT(REPLACE(REPLACE(REPLACE(frt.cnae_principal, '-', ''), '/', ''), '.', ''), 5)
    LIMIT 1
)
WHERE frt.cnae_principal IS NOT NULL
  AND frt.cnae_id IS NULL
  AND LENGTH(REPLACE(REPLACE(REPLACE(frt.cnae_principal, '-', ''), '/', ''), '.', '')) >= 5;

-- ===========================================
-- 3. PROPAGAR cnae_id PARA dim_empresas
-- ===========================================

-- Atualiza dim_empresas.cnae_id com o CNAE mais recente de cada empresa
UPDATE dim_empresas e
SET cnae_id = latest.cnae_id
FROM (
    SELECT DISTINCT ON (frt.empresa_id)
        frt.empresa_id,
        frt.cnae_id
    FROM fato_regime_tributario frt
    WHERE frt.cnae_id IS NOT NULL
    ORDER BY frt.empresa_id, frt.data_registro DESC
) latest
WHERE e.id = latest.empresa_id
  AND e.cnae_id IS NULL;

-- ===========================================
-- 4. REMOVER COLUNAS REDUNDANTES (OPCIONAL - COMENTADO)
-- ===========================================

-- Descomentar quando tiver certeza que cnae_id esta populado corretamente
-- ALTER TABLE fato_regime_tributario DROP COLUMN IF EXISTS cnae_principal;
-- ALTER TABLE fato_regime_tributario DROP COLUMN IF EXISTS cnae_descricao;

-- ===========================================
-- 5. VERIFICACAO
-- ===========================================

-- Executar para verificar resultado:
-- SELECT
--     'fato_regime_tributario' as tabela,
--     COUNT(*) FILTER (WHERE cnae_id IS NOT NULL) as com_cnae,
--     COUNT(*) FILTER (WHERE cnae_id IS NULL AND cnae_principal IS NOT NULL) as sem_match,
--     COUNT(*) as total
-- FROM fato_regime_tributario
-- UNION ALL
-- SELECT
--     'dim_empresas' as tabela,
--     COUNT(*) FILTER (WHERE cnae_id IS NOT NULL) as com_cnae,
--     COUNT(*) FILTER (WHERE cnae_id IS NULL) as sem_match,
--     COUNT(*) as total
-- FROM dim_empresas;

-- ===========================================
-- SUMARIO DA MIGRATION
-- ===========================================
-- 1. Adicionada coluna cnae_id em fato_regime_tributario (FK para raw_cnae)
-- 2. Populado cnae_id baseado em cnae_principal existente (match por codigo)
-- 3. Propagado cnae_id para dim_empresas (CNAE mais recente de cada empresa)
-- 4. Colunas cnae_principal e cnae_descricao mantidas por compatibilidade
--    (podem ser removidas futuramente)
