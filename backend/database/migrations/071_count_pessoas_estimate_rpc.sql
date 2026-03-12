-- =============================================
-- RPC: count_pessoas_estimate
-- Fast count for dim_pessoas using pg_class (no table scan)
-- Same pattern as count_empresas_estimate
-- =============================================

CREATE OR REPLACE FUNCTION count_pessoas_estimate()
RETURNS bigint
LANGUAGE sql
STABLE
AS $$
  SELECT GREATEST(
    (SELECT reltuples::bigint FROM pg_class WHERE relname = 'dim_pessoas'),
    0
  );
$$;

-- Grant access
GRANT EXECUTE ON FUNCTION count_pessoas_estimate() TO anon, authenticated, service_role;
