-- =============================================
-- Migration 035: dim_pessoas search RPC + trigram index
-- Data: 2026-03-11
-- Objetivo: eliminar timeouts em busca de pessoas (22M+ rows)
-- Segurança: nao altera dados, nao remove registros
--
-- IMPORTANTE:
--   - CREATE INDEX CONCURRENTLY nao pode rodar dentro de transacao explicita
--   - Execute cada statement separadamente no SQL Editor
-- =============================================

-- 1. Garantir extensao pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. Indice trigram para busca textual em nome_completo
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_pessoas_nome_completo_trgm
  ON dim_pessoas USING gin (nome_completo gin_trgm_ops);

-- 3. RPC: busca ranqueada por nome em dim_pessoas
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
LANGUAGE sql
STABLE
AS $$
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
        WHEN lower(coalesce(p.nome_completo, '')) = lower(p_query) THEN 10
        WHEN lower(coalesce(p.nome_completo, '')) LIKE lower(p_query) || '%' THEN 7
        ELSE 0
      END
      +
      similarity(coalesce(p.nome_completo, ''), p_query)
    )::real AS search_score
  FROM dim_pessoas p
  WHERE p.nome_completo ILIKE '%' || p_query || '%'
  ORDER BY
    search_score DESC,
    p.nome_completo ASC,
    p.id ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);
$$;

COMMENT ON FUNCTION search_pessoas_ranked_v1 IS
  'Busca textual ranqueada em dim_pessoas usando nome_completo com suporte a trigram (22M+ rows).';
