-- =============================================
-- Migration 070: fato_emendas_subnacionais
-- Data: 2026-03-12
-- Instancia: Brasil Data Hub (BRASIL_DATA_HUB_URL)
--
-- Tabela para emendas estaduais e municipais coletadas
-- de portais de transparência subnacionais.
--
-- Fontes Phase 1:
--   - GO Estado (CKAN DataStore API)
--   - MG Estado (ALMG CSV)
--   - RJ Capital (Transparência Prefeitura XLSX)
--   - SP Capital (CKAN ODS)
--
-- Fontes Phase 2+:
--   - BA Estado, PR Estado, AM Estado
--   - BH, Curitiba, Salvador, Goiânia, Manaus, SP Cidade (mais)
--
-- IMPORTANTE: Executar no SQL Editor da instancia Brasil Data Hub
-- =============================================

-- =============================================
-- BLOCO 1: TABELA PRINCIPAL
-- =============================================

CREATE TABLE IF NOT EXISTS fato_emendas_subnacionais (
  id BIGSERIAL PRIMARY KEY,

  -- Identificação
  codigo_emenda TEXT,                  -- Código original da fonte (pode variar por estado)
  numero_emenda TEXT,                  -- Número da emenda na casa legislativa

  -- Classificação
  esfera TEXT NOT NULL,                -- 'estadual' | 'municipal'
  uf TEXT NOT NULL,                    -- Sigla do estado (GO, MG, RJ, SP, BA, PR, AM)
  municipio TEXT,                      -- Nome do município (NULL se estadual)
  codigo_ibge TEXT,                    -- Código IBGE do município/estado

  -- Autoria
  autor TEXT,                          -- Nome do parlamentar/autor
  partido TEXT,                        -- Partido do autor
  tipo_autor TEXT,                     -- 'deputado_estadual' | 'vereador' | 'bancada' | 'comissao'

  -- Detalhes da emenda
  tipo TEXT,                           -- Tipo da emenda (individual, bancada, comissão, etc.)
  descricao TEXT,                      -- Descrição/objeto da emenda
  funcao TEXT,                         -- Função programática (Saúde, Educação, etc.)
  subfuncao TEXT,                      -- Subfunção programática
  programa TEXT,                       -- Programa orçamentário
  acao TEXT,                           -- Ação orçamentária
  natureza_despesa TEXT,               -- Natureza da despesa

  -- Beneficiário
  beneficiario TEXT,                   -- Nome do beneficiário (órgão, entidade, município)
  cnpj_beneficiario TEXT,             -- CNPJ do beneficiário (quando disponível)

  -- Valores (em R$)
  ano INT NOT NULL,                    -- Ano do orçamento
  valor_aprovado NUMERIC(18,2),        -- Valor aprovado/autorizado
  valor_empenhado NUMERIC(18,2),       -- Valor empenhado
  valor_liquidado NUMERIC(18,2),       -- Valor liquidado
  valor_pago NUMERIC(18,2),            -- Valor efetivamente pago

  -- Rastreamento de fonte
  fonte TEXT NOT NULL,                 -- Ex: 'go_ckan', 'mg_almg', 'rj_transparencia', 'sp_ckan'
  fonte_url TEXT,                      -- URL exata do dado
  data_coleta TIMESTAMPTZ DEFAULT NOW(),

  -- Metadados
  dados_extras JSONB DEFAULT '{}',     -- Campos extras específicos de cada fonte
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  atualizado_em TIMESTAMPTZ DEFAULT NOW(),

  -- Unicidade: combinação fonte + código + ano para evitar duplicatas
  CONSTRAINT uq_emenda_subnacional UNIQUE (fonte, codigo_emenda, ano)
);

-- =============================================
-- BLOCO 2: ÍNDICES
-- =============================================

CREATE INDEX IF NOT EXISTS idx_emendas_sub_esfera ON fato_emendas_subnacionais(esfera);
CREATE INDEX IF NOT EXISTS idx_emendas_sub_uf ON fato_emendas_subnacionais(uf);
CREATE INDEX IF NOT EXISTS idx_emendas_sub_ano ON fato_emendas_subnacionais(ano);
CREATE INDEX IF NOT EXISTS idx_emendas_sub_autor ON fato_emendas_subnacionais(autor);
CREATE INDEX IF NOT EXISTS idx_emendas_sub_fonte ON fato_emendas_subnacionais(fonte);
CREATE INDEX IF NOT EXISTS idx_emendas_sub_municipio ON fato_emendas_subnacionais(municipio);
CREATE INDEX IF NOT EXISTS idx_emendas_sub_criado_em ON fato_emendas_subnacionais(criado_em);

-- Índice composto para queries frequentes
CREATE INDEX IF NOT EXISTS idx_emendas_sub_uf_ano ON fato_emendas_subnacionais(uf, ano);

-- =============================================
-- BLOCO 3: FULL-TEXT SEARCH
-- =============================================

ALTER TABLE fato_emendas_subnacionais
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('portuguese',
    coalesce(autor, '') || ' ' ||
    coalesce(descricao, '') || ' ' ||
    coalesce(beneficiario, '') || ' ' ||
    coalesce(municipio, '')
  )
) STORED;

CREATE INDEX IF NOT EXISTS idx_emendas_sub_fts
  ON fato_emendas_subnacionais USING gin(search_vector);

-- =============================================
-- BLOCO 4: RPC para busca
-- =============================================

CREATE OR REPLACE FUNCTION search_emendas_subnacionais_v1(
  p_query TEXT,
  p_uf TEXT DEFAULT NULL,
  p_esfera TEXT DEFAULT NULL,
  p_ano INT DEFAULT NULL,
  p_limit INT DEFAULT 50
)
RETURNS TABLE (
  id BIGINT,
  autor TEXT,
  tipo TEXT,
  descricao TEXT,
  esfera TEXT,
  uf TEXT,
  municipio TEXT,
  ano INT,
  valor_aprovado NUMERIC,
  valor_empenhado NUMERIC,
  valor_pago NUMERIC,
  fonte TEXT,
  search_score REAL
)
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  v_tsquery tsquery;
  v_count INT;
BEGIN
  SET LOCAL statement_timeout = '30s';
  v_tsquery := plainto_tsquery('portuguese', p_query);

  RETURN QUERY
  SELECT
    e.id,
    e.autor::text,
    e.tipo::text,
    e.descricao::text,
    e.esfera::text,
    e.uf::text,
    e.municipio::text,
    e.ano,
    e.valor_aprovado,
    e.valor_empenhado,
    e.valor_pago,
    e.fonte::text,
    ts_rank(e.search_vector, v_tsquery)::real AS search_score
  FROM fato_emendas_subnacionais e
  WHERE e.search_vector @@ v_tsquery
    AND (p_uf IS NULL OR e.uf = p_uf)
    AND (p_esfera IS NULL OR e.esfera = p_esfera)
    AND (p_ano IS NULL OR e.ano = p_ano)
  ORDER BY search_score DESC, e.ano DESC
  LIMIT LEAST(GREATEST(p_limit, 1), 500);

  GET DIAGNOSTICS v_count = ROW_COUNT;

  -- Fallback: ilike
  IF v_count = 0 THEN
    RETURN QUERY
    SELECT
      e.id,
      e.autor::text,
      e.tipo::text,
      e.descricao::text,
      e.esfera::text,
      e.uf::text,
      e.municipio::text,
      e.ano,
      e.valor_aprovado,
      e.valor_empenhado,
      e.valor_pago,
      e.fonte::text,
      0.1::real AS search_score
    FROM fato_emendas_subnacionais e
    WHERE (e.autor ILIKE '%' || p_query || '%'
       OR e.descricao ILIKE '%' || p_query || '%'
       OR e.beneficiario ILIKE '%' || p_query || '%')
      AND (p_uf IS NULL OR e.uf = p_uf)
      AND (p_esfera IS NULL OR e.esfera = p_esfera)
      AND (p_ano IS NULL OR e.ano = p_ano)
    ORDER BY e.ano DESC
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
  END IF;
END;
$$;

COMMENT ON FUNCTION search_emendas_subnacionais_v1 IS
  'Busca em fato_emendas_subnacionais: FTS → ilike. Filtros opcionais: uf, esfera, ano.';

-- =============================================
-- BLOCO 5: trigger atualizado_em
-- =============================================

CREATE OR REPLACE FUNCTION update_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_emendas_sub_atualizado ON fato_emendas_subnacionais;
CREATE TRIGGER trg_emendas_sub_atualizado
  BEFORE UPDATE ON fato_emendas_subnacionais
  FOR EACH ROW EXECUTE FUNCTION update_atualizado_em();
