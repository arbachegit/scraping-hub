-- Migration 008: Create fontes_dados table for compliance (ISO 27001/27701)
-- All data sources must be registered for traceability

CREATE TABLE IF NOT EXISTS fontes_dados (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Identification
  nome TEXT NOT NULL UNIQUE,
  categoria TEXT NOT NULL,

  -- Origin
  fonte_primaria TEXT NOT NULL,
  url TEXT NOT NULL,
  documentacao_url TEXT,

  -- Tracking
  data_primeira_coleta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  data_ultima_atualizacao TIMESTAMPTZ,
  periodicidade TEXT DEFAULT 'sob_demanda',

  -- Metadata
  formato TEXT DEFAULT 'JSON',
  autenticacao_requerida BOOLEAN DEFAULT false,
  api_key_necessaria BOOLEAN DEFAULT false,

  -- Quality
  confiabilidade TEXT DEFAULT 'alta',
  cobertura_temporal TEXT,
  observacoes TEXT,

  -- Audit
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_fontes_categoria ON fontes_dados(categoria);
CREATE INDEX IF NOT EXISTS idx_fontes_periodicidade ON fontes_dados(periodicidade);
CREATE INDEX IF NOT EXISTS idx_fontes_nome ON fontes_dados(nome);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_fontes_dados_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_fontes_dados_updated_at ON fontes_dados;
CREATE TRIGGER trigger_fontes_dados_updated_at
  BEFORE UPDATE ON fontes_dados
  FOR EACH ROW
  EXECUTE FUNCTION update_fontes_dados_updated_at();

-- Comments
COMMENT ON TABLE fontes_dados IS 'Registro de fontes de dados para compliance ISO 27001/27701';
COMMENT ON COLUMN fontes_dados.nome IS 'Nome único da fonte (ex: BrasilAPI - Receita Federal)';
COMMENT ON COLUMN fontes_dados.categoria IS 'Categoria: busca, governamental, enrichment, fiscal, ia';
COMMENT ON COLUMN fontes_dados.fonte_primaria IS 'Origem primária dos dados (ex: Receita Federal)';
COMMENT ON COLUMN fontes_dados.periodicidade IS 'Frequência de atualização: diaria, semanal, mensal, sob_demanda';
COMMENT ON COLUMN fontes_dados.confiabilidade IS 'Nível de confiabilidade: alta, media, baixa';
