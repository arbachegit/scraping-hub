-- ===========================================
-- Migration 002: Adicionar palavras_chave e corrigir constraints
-- ===========================================

-- 1. Tornar razao_social opcional (pode não ter para todas empresas)
ALTER TABLE dim_empresas ALTER COLUMN razao_social DROP NOT NULL;

-- 2. Adicionar coluna de palavras-chave na dimensão empresa
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS palavras_chave JSONB DEFAULT '[]';

-- 3. Adicionar índice para busca por palavras-chave
CREATE INDEX IF NOT EXISTS idx_dim_empresas_keywords ON dim_empresas USING GIN (palavras_chave);

-- 4. Adicionar coluna fonte em dim_pessoas para rastrear origem
ALTER TABLE dim_pessoas ADD COLUMN IF NOT EXISTS fonte VARCHAR(50) DEFAULT 'apollo';

-- 5. Adicionar coluna fonte em fato_analises_empresa
ALTER TABLE fato_analises_empresa ADD COLUMN IF NOT EXISTS fontes_por_bloco JSONB DEFAULT '{}';

-- 6. Comentários
COMMENT ON COLUMN dim_empresas.palavras_chave IS 'Palavras-chave extraídas da análise para busca de concorrentes';
COMMENT ON COLUMN dim_pessoas.fonte IS 'Fonte dos dados: apollo, perplexity, google, manual';
