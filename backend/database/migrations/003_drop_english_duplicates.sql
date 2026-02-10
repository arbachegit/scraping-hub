-- Migration: Drop duplicate English tables
-- Date: 2026-02-09
-- Keep Portuguese tables: dim_empresas, dim_pessoas, fato_analises_empresa, fato_concorrentes, fato_buscas

-- ===========================================
-- DROP VIEWS FIRST (dependencies)
-- ===========================================

DROP VIEW IF EXISTS v_companies_with_analysis CASCADE;
DROP VIEW IF EXISTS v_people_with_company CASCADE;
DROP VIEW IF EXISTS v_searches_daily CASCADE;
DROP VIEW IF EXISTS v_source_quality CASCADE;
DROP VIEW IF EXISTS v_company_analysis_summary CASCADE;
DROP VIEW IF EXISTS v_user_usage CASCADE;

-- ===========================================
-- DROP ENGLISH DUPLICATE TABLES
-- ===========================================

-- From schema_v2.sql (English equivalents)
DROP TABLE IF EXISTS people_analyses CASCADE;
DROP TABLE IF EXISTS company_analyses CASCADE;
DROP TABLE IF EXISTS company_competitors CASCADE;
DROP TABLE IF EXISTS news_insights CASCADE;
DROP TABLE IF EXISTS search_history CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- From schema_dimensional.sql (English dimensional tables)
DROP TABLE IF EXISTS fact_api_call CASCADE;
DROP TABLE IF EXISTS fact_indicator_query CASCADE;
DROP TABLE IF EXISTS fact_news CASCADE;
DROP TABLE IF EXISTS fact_person_analysis CASCADE;
DROP TABLE IF EXISTS fact_company_analysis CASCADE;
DROP TABLE IF EXISTS fact_search CASCADE;
DROP TABLE IF EXISTS dim_user CASCADE;
DROP TABLE IF EXISTS dim_data_source CASCADE;
DROP TABLE IF EXISTS dim_municipality CASCADE;
DROP TABLE IF EXISTS dim_person CASCADE;
DROP TABLE IF EXISTS dim_company CASCADE;

-- Keep these (no Portuguese equivalent yet):
-- dim_date (used for analytics)
-- dim_time (used for analytics)
-- api_cache (technical)

-- ===========================================
-- RENAME user_credits TO creditos_usuario
-- ===========================================

-- Note: user_credits exists in multiple schemas
-- We will keep only one table
DROP TABLE IF EXISTS user_credits CASCADE;

CREATE TABLE IF NOT EXISTS creditos_usuario (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  creditos_total INTEGER DEFAULT 1000,
  creditos_usados INTEGER DEFAULT 0,
  plano VARCHAR(50) DEFAULT 'free',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert admin default
INSERT INTO creditos_usuario (email, creditos_total, plano)
VALUES ('admin@iconsai.ai', 10000, 'enterprise')
ON CONFLICT (email) DO NOTHING;

-- ===========================================
-- VERIFY REMAINING TABLES
-- ===========================================

-- After running this migration, the following tables should remain:
-- Portuguese (main):
--   dim_empresas, dim_pessoas
--   fato_analises_empresa, fato_eventos_pessoa, fato_concorrentes, fato_buscas
--   fontes_dados
--   users, creditos_usuario
--   empresa_searches, linkedin_searches, scrapes, api_logs
-- Technical:
--   api_cache
--   dim_date, dim_time (for analytics)
