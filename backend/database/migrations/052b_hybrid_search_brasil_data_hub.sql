-- =============================================
-- Migration 052b: Hybrid Search — Brasil Data Hub
-- Data: 2026-03-12
-- Instancia: Brasil Data Hub (BRASIL_DATA_HUB_URL)
-- Tabelas: dim_politicos, fato_politicos_mandatos, fato_emendas_parlamentares
--
-- Arquitetura: busca hibrida com scoring multicamada
--   1. Match exato (1000 pts)
--   2. Match por prefixo (300 pts)
--   3. Match por trecho (100 pts) — somente query >= 3 chars
--   4. Similaridade trigram (0-100 pts) — somente query > 5 chars
--   5. Bonus FTS tsvector (0-50 pts)
--
-- IMPORTANTE:
--   - Executar no SQL Editor da instancia Brasil Data Hub
--   - Execute cada bloco separadamente
-- =============================================


-- =============================================
-- BLOCO 1: EXTENSOES
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
-- BLOCO 3: dim_politicos — colunas normalizadas + indices
-- =============================================

-- 3a. Colunas normalizadas
ALTER TABLE dim_politicos
ADD COLUMN IF NOT EXISTS nome_completo_norm text
GENERATED ALWAYS AS (normalize_text(nome_completo)) STORED;

ALTER TABLE dim_politicos
ADD COLUMN IF NOT EXISTS nome_urna_norm text
GENERATED ALWAYS AS (normalize_text(nome_urna)) STORED;

-- 3b. Indices btree para prefixo
CREATE INDEX IF NOT EXISTS idx_politicos_nome_norm_prefix
  ON dim_politicos (nome_completo_norm text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_politicos_urna_norm_prefix
  ON dim_politicos (nome_urna_norm text_pattern_ops);

-- 3c. Indices GIN trigram
CREATE INDEX IF NOT EXISTS idx_politicos_nome_norm_trgm
  ON dim_politicos USING gin(nome_completo_norm gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_politicos_urna_norm_trgm
  ON dim_politicos USING gin(nome_urna_norm gin_trgm_ops);

-- 3d. RPC busca hibrida de politicos
CREATE OR REPLACE FUNCTION buscar_politicos(
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
    p.nome_urna::text,
    p.sexo::text,
    p.ocupacao::text,
    p.grau_instrucao::text,
    (
      CASE
        WHEN p.nome_completo_norm = v_norm OR p.nome_urna_norm = v_norm THEN 1000
        ELSE 0
      END
      +
      CASE
        WHEN p.nome_completo_norm LIKE v_norm || '%'
          OR p.nome_urna_norm LIKE v_norm || '%' THEN 300
        ELSE 0
      END
      +
      CASE
        WHEN v_len >= 3 AND (
          p.nome_completo_norm LIKE '%' || v_norm || '%'
          OR p.nome_urna_norm LIKE '%' || v_norm || '%'
        ) THEN 100
        ELSE 0
      END
      +
      CASE
        WHEN v_len > 5 THEN
          GREATEST(
            similarity(p.nome_completo_norm, v_norm),
            similarity(p.nome_urna_norm, v_norm)
          ) * 100
        ELSE 0
      END
      +
      CASE
        WHEN p.search_vector @@ v_tsquery THEN
          ts_rank(p.search_vector, v_tsquery) * 50
        ELSE 0
      END
    )::real AS search_score
  FROM dim_politicos p
  WHERE
    (
      p.search_vector @@ v_tsquery
      OR p.nome_completo_norm LIKE v_norm || '%'
      OR p.nome_urna_norm LIKE v_norm || '%'
      OR (v_len >= 3 AND (
        p.nome_completo_norm LIKE '%' || v_norm || '%'
        OR p.nome_urna_norm LIKE '%' || v_norm || '%'
      ))
      OR (v_len > 5 AND (
        similarity(p.nome_completo_norm, v_norm) > 0.3
        OR similarity(p.nome_urna_norm, v_norm) > 0.3
      ))
    )
  ORDER BY search_score DESC, p.nome_completo ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
END;
$$;

COMMENT ON FUNCTION buscar_politicos IS
  'Busca hibrida em dim_politicos: exato → prefixo → contem → trigram → FTS. Scoring multicamada.';


-- =============================================
-- BLOCO 4: fato_politicos_mandatos — colunas normalizadas + indices
-- =============================================

-- 4a. Colunas normalizadas
ALTER TABLE fato_politicos_mandatos
ADD COLUMN IF NOT EXISTS cargo_norm text
GENERATED ALWAYS AS (normalize_text(cargo)) STORED;

ALTER TABLE fato_politicos_mandatos
ADD COLUMN IF NOT EXISTS municipio_norm text
GENERATED ALWAYS AS (normalize_text(municipio)) STORED;

ALTER TABLE fato_politicos_mandatos
ADD COLUMN IF NOT EXISTS partido_nome_norm text
GENERATED ALWAYS AS (normalize_text(partido_nome)) STORED;

-- 4b. Coluna tsvector (se nao existir)
ALTER TABLE fato_politicos_mandatos
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese',
    coalesce(cargo, '') || ' ' || coalesce(municipio, '') || ' ' || coalesce(partido_nome, '')
  )
) STORED;

-- 4c. Indices
CREATE INDEX IF NOT EXISTS idx_mandatos_fts
  ON fato_politicos_mandatos USING gin(search_vector);

CREATE INDEX IF NOT EXISTS idx_mandatos_cargo_norm_prefix
  ON fato_politicos_mandatos (cargo_norm text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_mandatos_municipio_norm_prefix
  ON fato_politicos_mandatos (municipio_norm text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_mandatos_cargo_norm_trgm
  ON fato_politicos_mandatos USING gin(cargo_norm gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_mandatos_municipio_norm_trgm
  ON fato_politicos_mandatos USING gin(municipio_norm gin_trgm_ops);

-- 4d. RPC busca hibrida de mandatos
CREATE OR REPLACE FUNCTION buscar_mandatos(
  p_query TEXT,
  p_limit INT DEFAULT 25
)
RETURNS TABLE (
  id BIGINT,
  cargo TEXT,
  municipio TEXT,
  codigo_ibge TEXT,
  ano_eleicao INT,
  partido_sigla TEXT,
  partido_nome TEXT,
  eleito BOOLEAN,
  situacao_turno TEXT,
  politico_id UUID,
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
    m.id,
    m.cargo::text,
    m.municipio::text,
    m.codigo_ibge::text,
    m.ano_eleicao,
    m.partido_sigla::text,
    m.partido_nome::text,
    m.eleito,
    m.situacao_turno::text,
    m.politico_id,
    (
      CASE
        WHEN m.cargo_norm = v_norm OR m.municipio_norm = v_norm THEN 1000
        ELSE 0
      END
      +
      CASE
        WHEN m.cargo_norm LIKE v_norm || '%'
          OR m.municipio_norm LIKE v_norm || '%' THEN 300
        ELSE 0
      END
      +
      CASE
        WHEN v_len >= 3 AND (
          m.cargo_norm LIKE '%' || v_norm || '%'
          OR m.municipio_norm LIKE '%' || v_norm || '%'
        ) THEN 100
        ELSE 0
      END
      +
      CASE
        WHEN v_len > 5 THEN
          GREATEST(
            similarity(m.cargo_norm, v_norm),
            similarity(m.municipio_norm, v_norm)
          ) * 100
        ELSE 0
      END
      +
      CASE
        WHEN m.search_vector @@ v_tsquery THEN
          ts_rank(m.search_vector, v_tsquery) * 50
        ELSE 0
      END
    )::real AS search_score
  FROM fato_politicos_mandatos m
  WHERE
    (
      m.search_vector @@ v_tsquery
      OR m.cargo_norm LIKE v_norm || '%'
      OR m.municipio_norm LIKE v_norm || '%'
      OR (v_len >= 3 AND (
        m.cargo_norm LIKE '%' || v_norm || '%'
        OR m.municipio_norm LIKE '%' || v_norm || '%'
      ))
      OR (v_len > 5 AND (
        similarity(m.cargo_norm, v_norm) > 0.3
        OR similarity(m.municipio_norm, v_norm) > 0.3
      ))
    )
  ORDER BY search_score DESC, m.ano_eleicao DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
END;
$$;

COMMENT ON FUNCTION buscar_mandatos IS
  'Busca hibrida em fato_politicos_mandatos: exato → prefixo → contem → trigram → FTS. Scoring multicamada.';


-- =============================================
-- BLOCO 5: fato_emendas_parlamentares — colunas normalizadas + indices
-- =============================================

-- 5a. Colunas normalizadas
ALTER TABLE fato_emendas_parlamentares
ADD COLUMN IF NOT EXISTS autor_norm text
GENERATED ALWAYS AS (normalize_text(autor)) STORED;

ALTER TABLE fato_emendas_parlamentares
ADD COLUMN IF NOT EXISTS descricao_norm text
GENERATED ALWAYS AS (normalize_text(descricao)) STORED;

ALTER TABLE fato_emendas_parlamentares
ADD COLUMN IF NOT EXISTS localidade_norm text
GENERATED ALWAYS AS (normalize_text(localidade)) STORED;

-- 5b. Indices
CREATE INDEX IF NOT EXISTS idx_emendas_autor_norm_prefix
  ON fato_emendas_parlamentares (autor_norm text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_emendas_autor_norm_trgm
  ON fato_emendas_parlamentares USING gin(autor_norm gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_emendas_descricao_norm_trgm
  ON fato_emendas_parlamentares USING gin(descricao_norm gin_trgm_ops);

-- 5c. RPC busca hibrida de emendas
CREATE OR REPLACE FUNCTION buscar_emendas(
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
    e.autor::text,
    e.tipo::text,
    e.descricao::text,
    e.localidade::text,
    e.uf::text,
    e.ano,
    e.valor_empenhado,
    e.valor_liquidado,
    e.valor_pago,
    (
      CASE
        WHEN e.autor_norm = v_norm THEN 1000
        ELSE 0
      END
      +
      CASE
        WHEN e.autor_norm LIKE v_norm || '%' THEN 300
        ELSE 0
      END
      +
      CASE
        WHEN v_len >= 3 AND (
          e.autor_norm LIKE '%' || v_norm || '%'
          OR e.descricao_norm LIKE '%' || v_norm || '%'
          OR e.localidade_norm LIKE '%' || v_norm || '%'
        ) THEN 100
        ELSE 0
      END
      +
      CASE
        WHEN v_len > 5 THEN
          GREATEST(
            similarity(e.autor_norm, v_norm),
            similarity(e.descricao_norm, v_norm),
            similarity(e.localidade_norm, v_norm)
          ) * 100
        ELSE 0
      END
      +
      CASE
        WHEN e.search_vector @@ v_tsquery THEN
          ts_rank(e.search_vector, v_tsquery) * 50
        ELSE 0
      END
    )::real AS search_score
  FROM fato_emendas_parlamentares e
  WHERE
    (
      e.search_vector @@ v_tsquery
      OR e.autor_norm LIKE v_norm || '%'
      OR (v_len >= 3 AND (
        e.autor_norm LIKE '%' || v_norm || '%'
        OR e.descricao_norm LIKE '%' || v_norm || '%'
        OR e.localidade_norm LIKE '%' || v_norm || '%'
      ))
      OR (v_len > 5 AND (
        similarity(e.autor_norm, v_norm) > 0.3
        OR similarity(e.descricao_norm, v_norm) > 0.3
      ))
    )
  ORDER BY search_score DESC, e.ano DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
END;
$$;

COMMENT ON FUNCTION buscar_emendas IS
  'Busca hibrida em fato_emendas_parlamentares: exato → prefixo → contem → trigram → FTS. Scoring multicamada.';
