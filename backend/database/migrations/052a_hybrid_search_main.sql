-- =============================================
-- Migration 052a: Hybrid Search — Main Supabase
-- Data: 2026-03-12
-- Instancia: Main Supabase (SUPABASE_URL)
-- Tabelas: dim_empresas, dim_pessoas, dim_noticias
--
-- Arquitetura: busca hibrida com scoring multicamada
--   1. Match exato (1000 pts)
--   2. Match por prefixo (300 pts)
--   3. Match por trecho (100 pts) — somente query >= 3 chars
--   4. Similaridade trigram (0-100 pts) — somente query > 5 chars
--   5. Bonus FTS tsvector (0-50 pts)
--
-- IMPORTANTE:
--   - Execute cada bloco separadamente no SQL Editor
--   - CREATE INDEX em tabelas grandes pode levar varios minutos
--   - Colunas GENERATED ALWAYS AS em 64M rows = rewrite completo (~30 min)
-- =============================================


-- =============================================
-- BLOCO 1: EXTENSOES (verificar se ja existem)
-- =============================================
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- =============================================
-- BLOCO 2: FUNCAO DE NORMALIZACAO (compartilhada)
-- =============================================
CREATE OR REPLACE FUNCTION normalize_text(input text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT lower(
    unaccent(
      regexp_replace(
        trim(coalesce(input, '')),
        '\s+', ' ', 'g'
      )
    )
  );
$$;

COMMENT ON FUNCTION normalize_text IS
  'Normaliza texto: trim + remove espacos duplos + unaccent + lowercase. IMMUTABLE para uso em colunas geradas.';


-- =============================================
-- BLOCO 3: dim_empresas — colunas normalizadas + indices
-- =============================================

-- 3a. Colunas normalizadas
ALTER TABLE dim_empresas
ADD COLUMN IF NOT EXISTS razao_social_norm text
GENERATED ALWAYS AS (normalize_text(razao_social)) STORED;

ALTER TABLE dim_empresas
ADD COLUMN IF NOT EXISTS nome_fantasia_norm text
GENERATED ALWAYS AS (normalize_text(nome_fantasia)) STORED;

-- 3b. Indices btree para prefixo (text_pattern_ops)
CREATE INDEX IF NOT EXISTS idx_empresas_razao_norm_prefix
  ON dim_empresas (razao_social_norm text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_empresas_fantasia_norm_prefix
  ON dim_empresas (nome_fantasia_norm text_pattern_ops);

-- 3c. Indices GIN trigram para busca aproximada
CREATE INDEX IF NOT EXISTS idx_empresas_razao_norm_trgm
  ON dim_empresas USING gin(razao_social_norm gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_empresas_fantasia_norm_trgm
  ON dim_empresas USING gin(nome_fantasia_norm gin_trgm_ops);

-- 3d. RPC busca hibrida de empresas
CREATE OR REPLACE FUNCTION buscar_empresas(
  p_query TEXT,
  p_cidade TEXT DEFAULT NULL,
  p_estado TEXT DEFAULT NULL,
  p_limit INT DEFAULT 25
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
  situacao_cadastral TEXT,
  search_score REAL
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_norm TEXT;
  v_len INT;
  v_tsquery tsquery;
BEGIN
  SET LOCAL statement_timeout = '30s';

  v_norm := normalize_text(p_query);
  v_len := length(v_norm);
  v_tsquery := plainto_tsquery('portuguese', p_query);

  IF v_len < 2 THEN
    RETURN;
  END IF;

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
    e.situacao_cadastral::text,
    (
      -- Tier 1: Match exato (1000 pts)
      CASE
        WHEN e.razao_social_norm = v_norm OR e.nome_fantasia_norm = v_norm THEN 1000
        ELSE 0
      END
      +
      -- Tier 2: Prefixo (300 pts)
      CASE
        WHEN e.razao_social_norm LIKE v_norm || '%'
          OR e.nome_fantasia_norm LIKE v_norm || '%' THEN 300
        ELSE 0
      END
      +
      -- Tier 3: Contem (100 pts) — somente query >= 3 chars
      CASE
        WHEN v_len >= 3 AND (
          e.razao_social_norm LIKE '%' || v_norm || '%'
          OR e.nome_fantasia_norm LIKE '%' || v_norm || '%'
        ) THEN 100
        ELSE 0
      END
      +
      -- Tier 4: Similaridade trigram (0-100 pts) — somente query > 5 chars
      CASE
        WHEN v_len > 5 THEN
          GREATEST(
            similarity(e.razao_social_norm, v_norm),
            similarity(e.nome_fantasia_norm, v_norm)
          ) * 100
        ELSE 0
      END
      +
      -- Tier 5: FTS bonus (0-50 pts)
      CASE
        WHEN e.search_vector @@ v_tsquery THEN
          ts_rank(e.search_vector, v_tsquery) * 50
        ELSE 0
      END
    )::real AS search_score
  FROM dim_empresas e
  WHERE
    -- Gate: pelo menos uma estrategia deve casar
    (
      e.search_vector @@ v_tsquery
      OR e.razao_social_norm LIKE v_norm || '%'
      OR e.nome_fantasia_norm LIKE v_norm || '%'
      OR (v_len >= 3 AND (
        e.razao_social_norm LIKE '%' || v_norm || '%'
        OR e.nome_fantasia_norm LIKE '%' || v_norm || '%'
      ))
      OR (v_len > 5 AND (
        similarity(e.razao_social_norm, v_norm) > 0.3
        OR similarity(e.nome_fantasia_norm, v_norm) > 0.3
      ))
    )
    AND (p_cidade IS NULL OR e.cidade ILIKE '%' || p_cidade || '%')
    AND (p_estado IS NULL OR e.estado = p_estado)
  ORDER BY search_score DESC, e.razao_social ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
END;
$$;

COMMENT ON FUNCTION buscar_empresas IS
  'Busca hibrida em dim_empresas: exato → prefixo → contem → trigram → FTS. Scoring multicamada otimizado para 64M+ rows.';


-- =============================================
-- BLOCO 4: dim_pessoas — colunas normalizadas + indices
-- =============================================

-- 4a. Coluna normalizada
ALTER TABLE dim_pessoas
ADD COLUMN IF NOT EXISTS nome_completo_norm text
GENERATED ALWAYS AS (normalize_text(nome_completo)) STORED;

-- 4b. Indice btree para prefixo
CREATE INDEX IF NOT EXISTS idx_pessoas_nome_norm_prefix
  ON dim_pessoas (nome_completo_norm text_pattern_ops);

-- 4c. Indice GIN trigram
CREATE INDEX IF NOT EXISTS idx_pessoas_nome_norm_trgm
  ON dim_pessoas USING gin(nome_completo_norm gin_trgm_ops);

-- 4d. RPC busca hibrida de pessoas
CREATE OR REPLACE FUNCTION buscar_pessoas(
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
STABLE
AS $$
DECLARE
  v_norm TEXT;
  v_len INT;
  v_tsquery tsquery;
BEGIN
  SET LOCAL statement_timeout = '30s';

  v_norm := normalize_text(p_query);
  v_len := length(v_norm);
  v_tsquery := plainto_tsquery('portuguese', p_query);

  IF v_len < 2 THEN
    RETURN;
  END IF;

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
    (
      CASE
        WHEN p.nome_completo_norm = v_norm THEN 1000
        ELSE 0
      END
      +
      CASE
        WHEN p.nome_completo_norm LIKE v_norm || '%' THEN 300
        ELSE 0
      END
      +
      CASE
        WHEN v_len >= 3 AND p.nome_completo_norm LIKE '%' || v_norm || '%' THEN 100
        ELSE 0
      END
      +
      CASE
        WHEN v_len > 5 THEN
          similarity(p.nome_completo_norm, v_norm) * 100
        ELSE 0
      END
      +
      CASE
        WHEN p.search_vector @@ v_tsquery THEN
          ts_rank(p.search_vector, v_tsquery) * 50
        ELSE 0
      END
    )::real AS search_score
  FROM dim_pessoas p
  WHERE
    (
      p.search_vector @@ v_tsquery
      OR p.nome_completo_norm LIKE v_norm || '%'
      OR (v_len >= 3 AND p.nome_completo_norm LIKE '%' || v_norm || '%')
      OR (v_len > 5 AND similarity(p.nome_completo_norm, v_norm) > 0.3)
    )
  ORDER BY search_score DESC, p.nome_completo ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
END;
$$;

COMMENT ON FUNCTION buscar_pessoas IS
  'Busca hibrida em dim_pessoas: exato → prefixo → contem → trigram → FTS. Scoring multicamada otimizado para 22M+ rows.';


-- =============================================
-- BLOCO 5: dim_noticias — colunas normalizadas + indices
-- =============================================

-- 5a. Coluna normalizada (titulo)
ALTER TABLE dim_noticias
ADD COLUMN IF NOT EXISTS titulo_norm text
GENERATED ALWAYS AS (normalize_text(titulo)) STORED;

-- 5b. Indice btree para prefixo
CREATE INDEX IF NOT EXISTS idx_noticias_titulo_norm_prefix
  ON dim_noticias (titulo_norm text_pattern_ops);

-- 5c. Indice GIN trigram
CREATE INDEX IF NOT EXISTS idx_noticias_titulo_norm_trgm
  ON dim_noticias USING gin(titulo_norm gin_trgm_ops);

-- 5d. RPC busca hibrida de noticias
CREATE OR REPLACE FUNCTION buscar_noticias(
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
STABLE
AS $$
DECLARE
  v_norm TEXT;
  v_len INT;
  v_tsquery tsquery;
BEGIN
  SET LOCAL statement_timeout = '30s';

  v_norm := normalize_text(p_query);
  v_len := length(v_norm);
  v_tsquery := plainto_tsquery('portuguese', p_query);

  IF v_len < 2 THEN
    RETURN;
  END IF;

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
    (
      CASE
        WHEN n.titulo_norm = v_norm THEN 1000
        ELSE 0
      END
      +
      CASE
        WHEN n.titulo_norm LIKE v_norm || '%' THEN 300
        ELSE 0
      END
      +
      CASE
        WHEN v_len >= 3 AND n.titulo_norm LIKE '%' || v_norm || '%' THEN 100
        ELSE 0
      END
      +
      CASE
        WHEN v_len > 5 THEN
          similarity(n.titulo_norm, v_norm) * 100
        ELSE 0
      END
      +
      CASE
        WHEN n.search_vector @@ v_tsquery THEN
          ts_rank(n.search_vector, v_tsquery) * 50
        ELSE 0
      END
    )::real AS search_score
  FROM dim_noticias n
  WHERE
    (
      n.search_vector @@ v_tsquery
      OR n.titulo_norm LIKE v_norm || '%'
      OR (v_len >= 3 AND n.titulo_norm LIKE '%' || v_norm || '%')
      OR (v_len > 5 AND similarity(n.titulo_norm, v_norm) > 0.3)
    )
  ORDER BY search_score DESC, n.data_publicacao DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
END;
$$;

COMMENT ON FUNCTION buscar_noticias IS
  'Busca hibrida em dim_noticias: exato → prefixo → contem → trigram → FTS. Scoring multicamada.';
