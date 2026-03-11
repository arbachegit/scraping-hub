-- =============================================
-- Migration 036b: Full-Text Search for Brasil Data Hub tables
-- Data: 2026-03-11
-- Instancia: Brasil Data Hub (BRASIL_DATA_HUB_URL)
-- Tabelas: dim_politicos, fato_emendas_parlamentares
--
-- IMPORTANTE: Executar no SQL Editor da instancia Brasil Data Hub
-- =============================================

-- =============================================
-- BLOCO 1: EXTENSOES
-- =============================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================
-- BLOCO 2: dim_politicos — tsvector + RPC
-- =============================================

-- 2a. Coluna tsvector combinando nome_completo + nome_urna
ALTER TABLE dim_politicos
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese',
    coalesce(nome_completo, '') || ' ' || coalesce(nome_urna, '')
  )
) STORED;

-- 2b. Indice GIN
CREATE INDEX IF NOT EXISTS idx_dim_politicos_fts
  ON dim_politicos USING gin(search_vector);

-- 2c. RPC para busca de politicos
CREATE OR REPLACE FUNCTION search_politicos_ranked_v1(
  p_query TEXT,
  p_limit INT DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  nome_completo TEXT,
  nome_urna TEXT,
  sexo TEXT,
  ocupacao TEXT,
  grau_instrucao TEXT,
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
    p.id,
    p.nome_completo::text,
    p.nome_urna::text,
    p.sexo::text,
    p.ocupacao::text,
    p.grau_instrucao::text,
    ts_rank(p.search_vector, v_tsquery)::real AS search_score
  FROM dim_politicos p
  WHERE p.search_vector @@ v_tsquery
  ORDER BY search_score DESC, p.nome_completo ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);

  GET DIAGNOSTICS v_count = ROW_COUNT;

  -- Strategy 2: ilike fallback
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      p.id,
      p.nome_completo::text,
      p.nome_urna::text,
      p.sexo::text,
      p.ocupacao::text,
      p.grau_instrucao::text,
      0.1::real AS search_score
    FROM dim_politicos p
    WHERE p.nome_completo ILIKE '%' || p_query || '%'
       OR p.nome_urna ILIKE '%' || p_query || '%'
    ORDER BY p.nome_completo ASC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
  END IF;
END;
$$;

COMMENT ON FUNCTION search_politicos_ranked_v1 IS
  'Busca em dim_politicos: FTS → ilike. Busca em nome_completo + nome_urna.';


-- =============================================
-- BLOCO 3: fato_emendas_parlamentares — tsvector + RPC
-- =============================================

-- 3a. Coluna tsvector combinando autor + descricao + localidade
ALTER TABLE fato_emendas_parlamentares
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese',
    coalesce(autor, '') || ' ' || coalesce(descricao, '') || ' ' || coalesce(localidade, '')
  )
) STORED;

-- 3b. Indice GIN
CREATE INDEX IF NOT EXISTS idx_fato_emendas_fts
  ON fato_emendas_parlamentares USING gin(search_vector);

-- 3c. RPC para busca de emendas
CREATE OR REPLACE FUNCTION search_emendas_ranked_v1(
  p_query TEXT,
  p_limit INT DEFAULT 50
)
RETURNS TABLE (
  id BIGINT,
  autor TEXT,
  tipo TEXT,
  descricao TEXT,
  localidade TEXT,
  uf TEXT,
  ano INT,
  valor_empenhado NUMERIC,
  valor_liquidado NUMERIC,
  valor_pago NUMERIC,
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
    e.autor::text,
    e.tipo::text,
    e.descricao::text,
    e.localidade::text,
    e.uf::text,
    e.ano,
    e.valor_empenhado,
    e.valor_liquidado,
    e.valor_pago,
    ts_rank(e.search_vector, v_tsquery)::real AS search_score
  FROM fato_emendas_parlamentares e
  WHERE e.search_vector @@ v_tsquery
  ORDER BY search_score DESC, e.ano DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);

  GET DIAGNOSTICS v_count = ROW_COUNT;

  -- Strategy 2: ilike fallback
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      e.id,
      e.autor::text,
      e.tipo::text,
      e.descricao::text,
      e.localidade::text,
      e.uf::text,
      e.ano,
      e.valor_empenhado,
      e.valor_liquidado,
      e.valor_pago,
      0.1::real AS search_score
    FROM fato_emendas_parlamentares e
    WHERE e.autor ILIKE '%' || p_query || '%'
       OR e.descricao ILIKE '%' || p_query || '%'
       OR e.localidade ILIKE '%' || p_query || '%'
    ORDER BY e.ano DESC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
  END IF;
END;
$$;

COMMENT ON FUNCTION search_emendas_ranked_v1 IS
  'Busca em fato_emendas_parlamentares: FTS → ilike. Busca em autor + descricao + localidade.';
