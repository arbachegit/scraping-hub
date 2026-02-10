-- Migration: Create dimension tables for companies and people
-- Date: 2026-02-10

-- Table: dim_empresas (Companies)
CREATE TABLE IF NOT EXISTS dim_empresas (
  id SERIAL PRIMARY KEY,
  cnpj VARCHAR(14) UNIQUE NOT NULL,
  razao_social VARCHAR(255),
  nome_fantasia VARCHAR(255),
  website VARCHAR(500),
  linkedin VARCHAR(500),  -- LinkedIn da EMPRESA (nao dos fundadores)
  endereco TEXT,
  cidade VARCHAR(100),
  estado VARCHAR(2),
  setor VARCHAR(100),
  descricao TEXT,
  data_fundacao VARCHAR(50),
  num_funcionarios VARCHAR(50),
  fonte VARCHAR(50) DEFAULT 'serper',
  data_coleta TIMESTAMP DEFAULT NOW(),
  aprovado_por VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for CNPJ lookups
CREATE INDEX IF NOT EXISTS idx_empresas_cnpj ON dim_empresas(cnpj);

-- Table: dim_pessoas (People - founders, executives, etc)
CREATE TABLE IF NOT EXISTS dim_pessoas (
  id SERIAL PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  linkedin VARCHAR(500),  -- LinkedIn PESSOAL
  cargo VARCHAR(100),
  empresa_id INTEGER REFERENCES dim_empresas(id),
  tipo VARCHAR(50) DEFAULT 'fundador',  -- fundador, executivo, colaborador
  fonte VARCHAR(50) DEFAULT 'serper',
  data_coleta TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for company lookups
CREATE INDEX IF NOT EXISTS idx_pessoas_empresa ON dim_pessoas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_pessoas_tipo ON dim_pessoas(tipo);

-- Comments
COMMENT ON TABLE dim_empresas IS 'Dimensao de empresas cadastradas';
COMMENT ON TABLE dim_pessoas IS 'Dimensao de pessoas (fundadores, executivos)';
COMMENT ON COLUMN dim_empresas.linkedin IS 'LinkedIn da empresa, nao dos fundadores';
COMMENT ON COLUMN dim_pessoas.linkedin IS 'LinkedIn pessoal da pessoa';
