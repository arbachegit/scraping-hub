-- =============================================
-- Rollback 031: dim_empresas timeout mitigation
-- Segurança: remove apenas indices/funcoes adicionados pela migration 031
-- Nao remove registros nem altera dados da tabela
-- =============================================

DROP FUNCTION IF EXISTS list_empresas_recent_v1(UUID, INT);
DROP FUNCTION IF EXISTS search_empresas_ranked_v1(TEXT, TEXT, TEXT, INT);

DROP INDEX CONCURRENTLY IF EXISTS idx_dim_empresas_cnpj_cover_v1;
DROP INDEX CONCURRENTLY IF EXISTS idx_dim_empresas_created_at_id_desc;
DROP INDEX CONCURRENTLY IF EXISTS idx_dim_empresas_nome_fantasia_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_dim_empresas_razao_social_trgm;
