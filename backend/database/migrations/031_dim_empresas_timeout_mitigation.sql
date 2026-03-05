-- =============================================
-- Migration 031: dim_empresas timeout mitigation
-- Data: 2026-03-05
-- Objetivo: eliminar timeouts recorrentes em busca/listagem sobre dim_empresas
-- Segurança: nao altera dados, nao remove registros
--
-- IMPORTANTE:
--   - CREATE INDEX CONCURRENTLY nao pode rodar dentro de transacao explicita
--   - Execute esta migration em ambiente que respeite autocommit
-- =============================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Busca textual com ILIKE '%termo%' nas colunas principais.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_empresas_razao_social_trgm
  ON dim_empresas USING gin (razao_social gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_empresas_nome_fantasia_trgm
  ON dim_empresas USING gin (nome_fantasia gin_trgm_ops);

-- Ordenacao deterministica por created_at/id para listas "recentes".
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_empresas_created_at_id_desc
  ON dim_empresas (created_at DESC, id DESC)
  INCLUDE (cnpj, razao_social, nome_fantasia, cidade, estado, situacao_cadastral)
  WHERE created_at IS NOT NULL;

-- Lookup frequente por CNPJ sem heap lookup para payload basico.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_empresas_cnpj_cover_v1
  ON dim_empresas (cnpj)
  INCLUDE (id, razao_social, nome_fantasia, cidade, estado, situacao_cadastral);

-- RPC: busca ranqueada por nome sem depender de descricao.
CREATE OR REPLACE FUNCTION search_empresas_ranked_v1(
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
  situacao_cadastral TEXT,
  search_score REAL
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    e.id,
    e.cnpj::text,
    e.razao_social::text,
    e.nome_fantasia::text,
    e.cidade::text,
    e.estado::text,
    e.situacao_cadastral::text,
    (
      CASE
        WHEN lower(coalesce(e.nome_fantasia, '')) = lower(p_query)
          OR lower(coalesce(e.razao_social, '')) = lower(p_query) THEN 10
        WHEN lower(coalesce(e.nome_fantasia, '')) LIKE lower(p_query) || '%'
          OR lower(coalesce(e.razao_social, '')) LIKE lower(p_query) || '%' THEN 7
        ELSE 0
      END
      +
      GREATEST(
        similarity(coalesce(e.nome_fantasia, ''), p_query),
        similarity(coalesce(e.razao_social, ''), p_query)
      )
    )::real AS search_score
  FROM dim_empresas e
  WHERE (
    e.nome_fantasia ILIKE '%' || p_query || '%'
    OR e.razao_social ILIKE '%' || p_query || '%'
  )
  AND (p_estado IS NULL OR e.estado = upper(p_estado))
  AND (p_cidade IS NULL OR e.cidade ILIKE '%' || p_cidade || '%')
  ORDER BY
    search_score DESC,
    lower(coalesce(e.nome_fantasia, e.razao_social)) ASC,
    e.id ASC
  LIMIT LEAST(GREATEST(p_limit, 1), 50);
$$;

-- RPC: listagem deterministica com keyset imediato.
-- Usa id DESC para funcionar mesmo antes de migracoes adicionais na ordenacao temporal.
CREATE OR REPLACE FUNCTION list_empresas_recent_v1(
  p_cursor_id UUID DEFAULT NULL,
  p_limit INT DEFAULT 25
)
RETURNS TABLE (
  id UUID,
  cnpj TEXT,
  razao_social TEXT,
  nome_fantasia TEXT,
  cidade TEXT,
  estado TEXT,
  situacao_cadastral TEXT
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    e.id,
    e.cnpj::text,
    e.razao_social::text,
    e.nome_fantasia::text,
    e.cidade::text,
    e.estado::text,
    e.situacao_cadastral::text
  FROM dim_empresas e
  WHERE p_cursor_id IS NULL OR e.id < p_cursor_id
  ORDER BY e.id DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 50);
$$;

COMMENT ON FUNCTION search_empresas_ranked_v1 IS
  'Busca textual ranqueada em dim_empresas usando razao_social/nome_fantasia com suporte a trigram.';

COMMENT ON FUNCTION list_empresas_recent_v1 IS
  'Listagem keyset de dim_empresas por id DESC para evitar timeout de OFFSET/sort nao indexado.';
