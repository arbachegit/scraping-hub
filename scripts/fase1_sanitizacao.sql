-- =============================================
-- FASE 1: SANITIZACAO DO BANCO DE DADOS
-- Data: 2026-03-05
-- Executar no Supabase SQL Editor em ORDEM
-- =============================================

-- =============================================
-- BLOCO 1/3: Migration 020 - pg_trgm + Graph
-- =============================================

-- Enable trigram extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- FATO: RELACOES ENTRE ENTIDADES (Grafo)
CREATE TABLE IF NOT EXISTS fato_relacoes_entidades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('empresa','pessoa','politico','emenda','noticia')),
    source_id TEXT NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('empresa','pessoa','politico','emenda','noticia')),
    target_id TEXT NOT NULL,
    tipo_relacao VARCHAR(30) NOT NULL CHECK (tipo_relacao IN (
        'societaria','fornecedor','concorrente','parceiro','regulador',
        'beneficiario','mencionado_em','cnae_similar','geografico','politico_empresarial'
    )),
    strength NUMERIC(3,2) DEFAULT 0.5 CHECK (strength BETWEEN 0 AND 1),
    confidence NUMERIC(3,2) DEFAULT 0.5 CHECK (confidence BETWEEN 0 AND 1),
    bidirecional BOOLEAN DEFAULT false,
    source VARCHAR(50) DEFAULT 'system',
    detection_method VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    descricao TEXT,
    data_inicio DATE,
    data_fim DATE,
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_relacao_unica UNIQUE(source_type, source_id, target_type, target_id, tipo_relacao)
);

-- INDEXES for graph traversal
CREATE INDEX IF NOT EXISTS idx_rel_source ON fato_relacoes_entidades(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON fato_relacoes_entidades(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_rel_tipo ON fato_relacoes_entidades(tipo_relacao);
CREATE INDEX IF NOT EXISTS idx_rel_strength ON fato_relacoes_entidades(strength DESC);
CREATE INDEX IF NOT EXISTS idx_rel_ativo ON fato_relacoes_entidades(ativo) WHERE ativo = true;
CREATE INDEX IF NOT EXISTS idx_rel_metadata ON fato_relacoes_entidades USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_rel_source_ativo ON fato_relacoes_entidades(source_type, source_id, ativo) WHERE ativo = true;
CREATE INDEX IF NOT EXISTS idx_rel_target_ativo ON fato_relacoes_entidades(target_type, target_id, ativo) WHERE ativo = true;

-- TRIGGER: updated_at auto-update
CREATE OR REPLACE FUNCTION update_relacoes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_relacoes_updated_at ON fato_relacoes_entidades;
CREATE TRIGGER trg_relacoes_updated_at
    BEFORE UPDATE ON fato_relacoes_entidades
    FOR EACH ROW
    EXECUTE FUNCTION update_relacoes_updated_at();

-- COMMENTS
COMMENT ON TABLE fato_relacoes_entidades IS 'Grafo polimorfico de relacionamentos entre entidades (empresa, pessoa, politico, emenda, noticia)';

-- Register data source (compliance)
INSERT INTO fontes_dados (nome, categoria, fonte_primaria, url, confiabilidade, api_key_necessaria, periodicidade, formato, observacoes)
VALUES ('Graph Engine - Relacoes de Entidades', 'inteligencia', 'IconsAI Internal', 'internal://graph-engine', 'alta', false, 'tempo_real', 'JSON', 'Motor de grafo interno que detecta relacionamentos entre empresas, pessoas, politicos, emendas e noticias')
ON CONFLICT (nome) DO NOTHING;

-- =============================================
-- BLOCO 2/3: Migration 021 - Trigram + FTS + SIS
-- =============================================

-- 1. TRIGRAM INDEXES (pg_trgm)
CREATE INDEX IF NOT EXISTS idx_empresas_nome_trgm ON dim_empresas USING gin(nome_fantasia gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_empresas_razao_trgm ON dim_empresas USING gin(razao_social gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_empresas_descricao_trgm ON dim_empresas USING gin(descricao gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_pessoas_nome_trgm ON dim_pessoas USING gin(nome_completo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_noticias_titulo_trgm ON dim_noticias USING gin(titulo gin_trgm_ops);

-- 2. FULL-TEXT SEARCH (tsvector)
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS search_vector tsvector;

UPDATE dim_empresas SET search_vector = (
    setweight(to_tsvector('portuguese', COALESCE(razao_social, '')), 'A') ||
    setweight(to_tsvector('portuguese', COALESCE(nome_fantasia, '')), 'A') ||
    setweight(to_tsvector('portuguese', COALESCE(descricao, '')), 'B') ||
    setweight(to_tsvector('portuguese', COALESCE(cidade, '')), 'C') ||
    setweight(to_tsvector('portuguese', COALESCE(estado, '')), 'C')
)
WHERE search_vector IS NULL;

CREATE INDEX IF NOT EXISTS idx_empresas_search_vector ON dim_empresas USING gin(search_vector);

-- Auto-update trigger
CREATE OR REPLACE FUNCTION update_empresas_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := (
        setweight(to_tsvector('portuguese', COALESCE(NEW.razao_social, '')), 'A') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.nome_fantasia, '')), 'A') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.descricao, '')), 'B') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.cidade, '')), 'C') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.estado, '')), 'C')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_empresas_search_vector ON dim_empresas;
CREATE TRIGGER trg_empresas_search_vector
    BEFORE INSERT OR UPDATE OF razao_social, nome_fantasia, descricao, cidade, estado
    ON dim_empresas
    FOR EACH ROW
    EXECUTE FUNCTION update_empresas_search_vector();

-- 3. PGVECTOR (Semantic Search) - conditional
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        EXECUTE 'ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS embedding vector(1536)';
    ELSE
        RAISE NOTICE 'pgvector extension not enabled. Skipping embedding column.';
    END IF;
END
$$;

-- 4. STRATEGIC IMPACT SCORE (SIS)
CREATE TABLE IF NOT EXISTS fato_sis_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id INTEGER NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,
    text_similarity NUMERIC(4,3) DEFAULT 0,
    geo_proximity NUMERIC(4,3) DEFAULT 0,
    cnae_similarity NUMERIC(4,3) DEFAULT 0,
    political_connections NUMERIC(4,3) DEFAULT 0,
    news_volume NUMERIC(4,3) DEFAULT 0,
    relationship_density NUMERIC(4,3) DEFAULT 0,
    sis_score NUMERIC(5,2) GENERATED ALWAYS AS (
        text_similarity * 15 +
        geo_proximity * 10 +
        cnae_similarity * 15 +
        political_connections * 25 +
        news_volume * 15 +
        relationship_density * 20
    ) STORED,
    query_context TEXT,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_sis_empresa UNIQUE(empresa_id, query_context)
);

CREATE INDEX IF NOT EXISTS idx_sis_empresa ON fato_sis_scores(empresa_id);
CREATE INDEX IF NOT EXISTS idx_sis_score ON fato_sis_scores(sis_score DESC);
CREATE INDEX IF NOT EXISTS idx_sis_calculated ON fato_sis_scores(calculated_at DESC);

COMMENT ON TABLE fato_sis_scores IS 'Strategic Impact Score (SIS) - Pontuacao de impacto estrategico por empresa';
COMMENT ON COLUMN dim_empresas.search_vector IS 'Full-text search vector (Portuguese) for fast text queries';

-- Register data sources (compliance)
INSERT INTO fontes_dados (nome, categoria, fonte_primaria, url, confiabilidade, api_key_necessaria, periodicidade, formato, observacoes)
VALUES
('Hybrid Search Engine', 'inteligencia', 'IconsAI Internal', 'internal://hybrid-search', 'alta', false, 'tempo_real', 'JSON', 'Motor de busca hibrida: trigram + full-text + vector + relational com RRF ranking'),
('OpenAI Embeddings - text-embedding-3-small', 'ia', 'OpenAI', 'https://api.openai.com/v1/embeddings', 'alta', true, 'sob_demanda', 'JSON', 'Embeddings semanticos para busca vetorial (1536 dimensoes)')
ON CONFLICT (nome) DO NOTHING;

-- =============================================
-- BLOCO 3/3: Migration 022 - Composite Indexes
-- =============================================

-- 1. COMPOSITE INDEXES (Common Joins)
CREATE INDEX IF NOT EXISTS idx_empresas_cidade_estado ON dim_empresas(cidade, estado);
CREATE INDEX IF NOT EXISTS idx_empresas_cnae_cidade ON dim_empresas(cnae_principal, cidade) WHERE cnae_principal IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_empresas_situacao_estado ON dim_empresas(situacao_cadastral, estado);

-- 2. PARTIAL INDEXES (Active Records)
CREATE INDEX IF NOT EXISTS idx_empresas_ativas ON dim_empresas(id) WHERE situacao_cadastral = 'ATIVA';
CREATE INDEX IF NOT EXISTS idx_relacoes_ativas ON fato_relacoes_entidades(source_type, source_id) WHERE ativo = true;

-- 3. COMPOSITE INDEXES (fato_transacao_empresas)
CREATE INDEX IF NOT EXISTS idx_transacao_empresa_pessoa ON fato_transacao_empresas(empresa_id, pessoa_id);
CREATE INDEX IF NOT EXISTS idx_transacao_ativo ON fato_transacao_empresas(empresa_id) WHERE ativo = true;

-- 4. COMPOSITE INDEXES (fato_regime_tributario)
CREATE INDEX IF NOT EXISTS idx_regime_empresa_ativo ON fato_regime_tributario(empresa_id, ativo);
CREATE INDEX IF NOT EXISTS idx_regime_cnae ON fato_regime_tributario(cnae_principal) WHERE cnae_principal IS NOT NULL;

-- 5. COMPOSITE INDEXES (stats_historico)
CREATE INDEX IF NOT EXISTS idx_stats_hist_cat_data ON stats_historico(categoria, data DESC);

-- 6. OPTIMIZE dim_noticias
CREATE INDEX IF NOT EXISTS idx_noticias_empresa ON dim_noticias(empresa_id) WHERE empresa_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_noticias_data ON dim_noticias(data_publicacao DESC);

-- COMMENTS
COMMENT ON INDEX idx_empresas_cidade_estado IS 'Composite: geographic search by city+state';
COMMENT ON INDEX idx_empresas_ativas IS 'Partial: only active companies for faster searches';
COMMENT ON INDEX idx_regime_empresa_ativo IS 'Composite: regime lookup by empresa + active flag';
COMMENT ON INDEX idx_stats_hist_cat_data IS 'Composite: dashboard stats by category + date DESC';

-- =============================================
-- VERIFICACAO FINAL
-- =============================================
SELECT 'FASE 1 COMPLETA' AS status,
       (SELECT COUNT(*) FROM pg_indexes WHERE indexname LIKE 'idx_%_trgm') AS trigram_indexes,
       (SELECT COUNT(*) FROM pg_indexes WHERE indexname LIKE 'idx_sis_%') AS sis_indexes,
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'dim_empresas' AND column_name = 'search_vector') AS has_search_vector,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'fato_sis_scores') AS has_sis_table,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'fato_relacoes_entidades') AS has_graph_table;
