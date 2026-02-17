-- Migration 012: Create raw_cnae table for Brazilian CNAE codes
-- Source: IBGE/Concla

-- Create table
CREATE TABLE IF NOT EXISTS raw_cnae (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Código completo
  codigo VARCHAR(10) UNIQUE NOT NULL,      -- Ex: "0111-3/01"
  codigo_numerico VARCHAR(7) NOT NULL,     -- Ex: "0111301"

  -- Hierarquia CNAE
  secao VARCHAR(1),                         -- Ex: "A"
  divisao VARCHAR(2),                       -- Ex: "01"
  grupo VARCHAR(3),                         -- Ex: "011"
  classe VARCHAR(5),                        -- Ex: "01113"
  subclasse VARCHAR(7),                     -- Ex: "0111301"

  -- Descrições
  descricao TEXT NOT NULL,                  -- Descrição da atividade
  descricao_secao TEXT,
  descricao_divisao TEXT,
  descricao_grupo TEXT,
  descricao_classe TEXT,

  -- Metadados
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para busca rápida
CREATE INDEX IF NOT EXISTS idx_cnae_codigo ON raw_cnae(codigo);
CREATE INDEX IF NOT EXISTS idx_cnae_codigo_numerico ON raw_cnae(codigo_numerico);
CREATE INDEX IF NOT EXISTS idx_cnae_secao ON raw_cnae(secao);
CREATE INDEX IF NOT EXISTS idx_cnae_divisao ON raw_cnae(divisao);
CREATE INDEX IF NOT EXISTS idx_cnae_grupo ON raw_cnae(grupo);
CREATE INDEX IF NOT EXISTS idx_cnae_classe ON raw_cnae(classe);
CREATE INDEX IF NOT EXISTS idx_cnae_descricao ON raw_cnae USING gin(to_tsvector('portuguese', descricao));

-- Comentários
COMMENT ON TABLE raw_cnae IS 'Tabela de CNAEs (Classificação Nacional de Atividades Econômicas) do Brasil';
COMMENT ON COLUMN raw_cnae.codigo IS 'Código CNAE formatado (ex: 0111-3/01)';
COMMENT ON COLUMN raw_cnae.codigo_numerico IS 'Código CNAE apenas números (ex: 0111301)';
COMMENT ON COLUMN raw_cnae.secao IS 'Seção CNAE (1 letra: A-U)';
COMMENT ON COLUMN raw_cnae.divisao IS 'Divisão CNAE (2 dígitos)';
COMMENT ON COLUMN raw_cnae.grupo IS 'Grupo CNAE (3 dígitos)';
COMMENT ON COLUMN raw_cnae.classe IS 'Classe CNAE (5 dígitos)';
COMMENT ON COLUMN raw_cnae.subclasse IS 'Subclasse CNAE (7 dígitos)';
