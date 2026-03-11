-- =============================================
-- Migration 036: Full-Text Search (tsvector) for ALL searchable tables
-- Data: 2026-03-11
-- Objetivo: eliminar timeouts em buscas text com ilike em tabelas grandes
--
-- Estrategia: tsvector + GIN index para busca full-text rapida
-- Fallback: trigram index para busca parcial (contains)
--
-- IMPORTANTE:
--   - Execute cada bloco separadamente no SQL Editor
--   - CREATE INDEX em tabelas grandes pode levar minutos
--   - Nao altera dados existentes, apenas adiciona colunas e indices
-- =============================================

-- =============================================
-- BLOCO 1: EXTENSOES (executar primeiro)
-- =============================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- =============================================
-- BLOCO 2: dim_pessoas — tsvector + RPC (MAIN SUPABASE)
-- =============================================

-- 2a. Adicionar coluna tsvector
ALTER TABLE dim_pessoas
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese', coalesce(nome_completo, ''))
) STORED;

-- 2b. Indice GIN para full-text search
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_fts
  ON dim_pessoas USING gin(search_vector);

-- 2c. Indice btree em lower(nome_completo) para prefix search
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_nome_lower
  ON dim_pessoas (lower(nome_completo) text_pattern_ops);

-- 2d. RPC atualizada: tsvector primeiro, trigram fallback
CREATE OR REPLACE FUNCTION search_pessoas_ranked_v1(
  p_query TEXT,
  p_limit INT DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  nome_completo TEXT,
  cpf TEXT,
  email TEXT,
  primeiro_nome TEXT,
  raw_apollo_data JSONB,
  codigo_ibge TEXT,
  codigo_ibge_uf TEXT,
  created_at TIMESTAMPTZ,
  search_score REAL
)
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  v_tsquery tsquery;
  v_count INT;
BEGIN
  SET LOCAL statement_timeout = '30s';

  -- Build tsquery from input (split words with &)
  v_tsquery := plainto_tsquery('portuguese', p_query);

  -- Strategy 1: Full-text search (fastest, uses GIN index)
  RETURN QUERY
  SELECT
    p.id,
    p.nome_completo::text,
    p.cpf::text,
    p.email::text,
    p.primeiro_nome::text,
    p.raw_apollo_data,
    p.codigo_ibge::text,
    p.codigo_ibge_uf::text,
    p.created_at,
    ts_rank(p.search_vector, v_tsquery)::real AS search_score
  FROM dim_pessoas p
  WHERE p.search_vector @@ v_tsquery
  ORDER BY search_score DESC, p.nome_completo ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);

  -- Check if we got results
  GET DIAGNOSTICS v_count = ROW_COUNT;

  -- Strategy 2: If FTS returned nothing, try prefix match (btree index)
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      p.id,
      p.nome_completo::text,
      p.cpf::text,
      p.email::text,
      p.primeiro_nome::text,
      p.raw_apollo_data,
      p.codigo_ibge::text,
      p.codigo_ibge_uf::text,
      p.created_at,
      0.5::real AS search_score
    FROM dim_pessoas p
    WHERE lower(p.nome_completo) LIKE lower(p_query) || '%'
    ORDER BY p.nome_completo ASC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);

    GET DIAGNOSTICS v_count = ROW_COUNT;
  END IF;

  -- Strategy 3: If still nothing, trigram contains (slowest but most flexible)
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      p.id,
      p.nome_completo::text,
      p.cpf::text,
      p.email::text,
      p.primeiro_nome::text,
      p.raw_apollo_data,
      p.codigo_ibge::text,
      p.codigo_ibge_uf::text,
      p.created_at,
      similarity(coalesce(p.nome_completo, ''), p_query)::real AS search_score
    FROM dim_pessoas p
    WHERE p.nome_completo ILIKE '%' || p_query || '%'
    ORDER BY search_score DESC, p.nome_completo ASC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
  END IF;
END;
$$;

COMMENT ON FUNCTION search_pessoas_ranked_v1 IS
  'Busca em dim_pessoas: FTS → prefix → trigram. Otimizada para 22M+ rows.';


-- =============================================
-- BLOCO 3: dim_empresas — tsvector + RPC (MAIN SUPABASE)
-- =============================================

-- 3a. Coluna tsvector combinando razao_social + nome_fantasia
ALTER TABLE dim_empresas
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese',
    coalesce(razao_social, '') || ' ' || coalesce(nome_fantasia, '')
  )
) STORED;

-- 3b. Indice GIN
CREATE INDEX IF NOT EXISTS idx_dim_empresas_fts
  ON dim_empresas USING gin(search_vector);

-- 3c. Indice trigram para fallback contains
CREATE INDEX IF NOT EXISTS idx_dim_empresas_razao_trgm
  ON dim_empresas USING gin(razao_social gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dim_empresas_fantasia_trgm
  ON dim_empresas USING gin(nome_fantasia gin_trgm_ops);

-- 3d. RPC para busca de empresas
CREATE OR REPLACE FUNCTION search_empresas_ranked_v1(
  p_query TEXT,
  p_cidade TEXT DEFAULT NULL,
  p_estado TEXT DEFAULT NULL,
  p_limit INT DEFAULT 100
)
RETURNS TABLE (
  id UUID,
  cnpj TEXT,
  razao_social TEXT,
  nome_fantasia TEXT,
  cidade TEXT,
  estado TEXT,
  cnae_codigo TEXT,
  cnae_descricao TEXT,
  porte TEXT,
  search_score REAL
)
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  v_tsquery tsquery;
  v_count INT;
BEGIN
  SET LOCAL statement_timeout = '30s';
  v_tsquery := plainto_tsquery('portuguese', p_query);

  -- Strategy 1: Full-text search
  RETURN QUERY
  SELECT
    e.id,
    e.cnpj::text,
    e.razao_social::text,
    e.nome_fantasia::text,
    e.cidade::text,
    e.estado::text,
    e.cnae_codigo::text,
    e.cnae_descricao::text,
    e.porte::text,
    ts_rank(e.search_vector, v_tsquery)::real AS search_score
  FROM dim_empresas e
  WHERE e.search_vector @@ v_tsquery
    AND (p_cidade IS NULL OR e.cidade ILIKE '%' || p_cidade || '%')
    AND (p_estado IS NULL OR e.estado = p_estado)
  ORDER BY search_score DESC, e.razao_social ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);

  GET DIAGNOSTICS v_count = ROW_COUNT;

  -- Strategy 2: Trigram fallback
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      e.id,
      e.cnpj::text,
      e.razao_social::text,
      e.nome_fantasia::text,
      e.cidade::text,
      e.estado::text,
      e.cnae_codigo::text,
      e.cnae_descricao::text,
      e.porte::text,
      GREATEST(
        similarity(coalesce(e.razao_social, ''), p_query),
        similarity(coalesce(e.nome_fantasia, ''), p_query)
      )::real AS search_score
    FROM dim_empresas e
    WHERE (e.razao_social ILIKE '%' || p_query || '%'
           OR e.nome_fantasia ILIKE '%' || p_query || '%')
      AND (p_cidade IS NULL OR e.cidade ILIKE '%' || p_cidade || '%')
      AND (p_estado IS NULL OR e.estado = p_estado)
    ORDER BY search_score DESC, e.razao_social ASC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
  END IF;
END;
$$;

COMMENT ON FUNCTION search_empresas_ranked_v1 IS
  'Busca em dim_empresas: FTS → trigram. Busca em razao_social + nome_fantasia.';


-- =============================================
-- BLOCO 4: dim_noticias — tsvector + RPC (MAIN SUPABASE)
-- =============================================

-- 4a. Coluna tsvector combinando titulo + resumo
ALTER TABLE dim_noticias
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese',
    coalesce(titulo, '') || ' ' || coalesce(resumo, '')
  )
) STORED;

-- 4b. Indice GIN
CREATE INDEX IF NOT EXISTS idx_dim_noticias_fts
  ON dim_noticias USING gin(search_vector);

-- 4c. RPC para busca de noticias
CREATE OR REPLACE FUNCTION search_noticias_ranked_v1(
  p_query TEXT,
  p_limit INT DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  titulo TEXT,
  resumo TEXT,
  fonte_nome TEXT,
  url TEXT,
  segmento TEXT,
  data_publicacao TIMESTAMPTZ,
  relevancia_geral REAL,
  search_score REAL
)
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  v_tsquery tsquery;
  v_count INT;
BEGIN
  SET LOCAL statement_timeout = '30s';
  v_tsquery := plainto_tsquery('portuguese', p_query);

  -- Strategy 1: Full-text search
  RETURN QUERY
  SELECT
    n.id,
    n.titulo::text,
    n.resumo::text,
    n.fonte_nome::text,
    n.url::text,
    n.segmento::text,
    n.data_publicacao,
    n.relevancia_geral::real,
    ts_rank(n.search_vector, v_tsquery)::real AS search_score
  FROM dim_noticias n
  WHERE n.search_vector @@ v_tsquery
  ORDER BY search_score DESC, n.data_publicacao DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);

  GET DIAGNOSTICS v_count = ROW_COUNT;

  -- Strategy 2: ilike fallback
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      n.id,
      n.titulo::text,
      n.resumo::text,
      n.fonte_nome::text,
      n.url::text,
      n.segmento::text,
      n.data_publicacao,
      n.relevancia_geral::real,
      0.1::real AS search_score
    FROM dim_noticias n
    WHERE n.titulo ILIKE '%' || p_query || '%'
       OR n.resumo ILIKE '%' || p_query || '%'
    ORDER BY n.data_publicacao DESC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
  END IF;
END;
$$;

COMMENT ON FUNCTION search_noticias_ranked_v1 IS
  'Busca em dim_noticias: FTS → ilike. Busca em titulo + resumo.';
