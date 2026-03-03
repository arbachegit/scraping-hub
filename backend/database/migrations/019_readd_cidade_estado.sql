-- Migration 019: Re-add cidade and estado columns to dim_empresas
-- These were removed by migration 013 but are needed for company table display
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);
ALTER TABLE dim_empresas ADD COLUMN IF NOT EXISTS estado VARCHAR(2);

-- Index for city/state search
CREATE INDEX IF NOT EXISTS idx_dim_empresas_cidade ON dim_empresas(cidade);
CREATE INDEX IF NOT EXISTS idx_dim_empresas_estado ON dim_empresas(estado);
