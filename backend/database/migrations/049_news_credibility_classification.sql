-- ============================================================
-- Migration 049: News Source Credibility & News Classification
-- Adds credibility scoring (5 layers) and news type classification
-- Based on Intelligence Architecture specification
-- ============================================================

-- 1. Add credibility columns to dim_fontes_noticias
ALTER TABLE dim_fontes_noticias
  ADD COLUMN IF NOT EXISTS camada VARCHAR(30),
  ADD COLUMN IF NOT EXISTS credibilidade_score NUMERIC(2,1) DEFAULT 0.5;

COMMENT ON COLUMN dim_fontes_noticias.camada IS 'Source layer: institucional, jornalismo_premium, setorial, think_tank, rede_social';
COMMENT ON COLUMN dim_fontes_noticias.credibilidade_score IS 'Credibility score 0.0-1.0: institucional=1.0, premium=0.9, profissional=0.8, analise=0.6, social=0.5, desconhecida=0.3';

-- Add CHECK constraint for valid layers
ALTER TABLE dim_fontes_noticias
  ADD CONSTRAINT chk_fontes_camada
  CHECK (camada IS NULL OR camada IN ('institucional', 'jornalismo_premium', 'setorial', 'think_tank', 'rede_social'));

-- Add CHECK constraint for score range
ALTER TABLE dim_fontes_noticias
  ADD CONSTRAINT chk_fontes_credibilidade_score
  CHECK (credibilidade_score >= 0.0 AND credibilidade_score <= 1.0);

-- Index on credibility score for sorting/filtering
CREATE INDEX IF NOT EXISTS idx_fontes_camada ON dim_fontes_noticias(camada);
CREATE INDEX IF NOT EXISTS idx_fontes_credibilidade_score ON dim_fontes_noticias(credibilidade_score);

-- 2. Add classification columns to dim_noticias
ALTER TABLE dim_noticias
  ADD COLUMN IF NOT EXISTS tipo_classificacao VARCHAR(30),
  ADD COLUMN IF NOT EXISTS credibilidade_score NUMERIC(2,1),
  ADD COLUMN IF NOT EXISTS tema_principal VARCHAR(50);

COMMENT ON COLUMN dim_noticias.tipo_classificacao IS 'News type: factual, analitica, investigativa, setorial, tendencia, sinal';
COMMENT ON COLUMN dim_noticias.credibilidade_score IS 'Inherited from source or overridden. Score 0.0-1.0';
COMMENT ON COLUMN dim_noticias.tema_principal IS 'Primary theme: economia, mercado, politica, saude, educacao, tecnologia, infraestrutura, energia, agricultura, seguranca_publica';

-- Add CHECK constraints
ALTER TABLE dim_noticias
  ADD CONSTRAINT chk_noticias_tipo_classificacao
  CHECK (tipo_classificacao IS NULL OR tipo_classificacao IN ('factual', 'analitica', 'investigativa', 'setorial', 'tendencia', 'sinal'));

ALTER TABLE dim_noticias
  ADD CONSTRAINT chk_noticias_credibilidade_score
  CHECK (credibilidade_score IS NULL OR (credibilidade_score >= 0.0 AND credibilidade_score <= 1.0));

ALTER TABLE dim_noticias
  ADD CONSTRAINT chk_noticias_tema_principal
  CHECK (tema_principal IS NULL OR tema_principal IN (
    'economia', 'mercado', 'politica', 'saude', 'educacao',
    'tecnologia', 'infraestrutura', 'energia', 'agricultura', 'seguranca_publica'
  ));

-- Indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_noticias_tipo_classificacao ON dim_noticias(tipo_classificacao);
CREATE INDEX IF NOT EXISTS idx_noticias_credibilidade_score ON dim_noticias(credibilidade_score);
CREATE INDEX IF NOT EXISTS idx_noticias_tema_principal ON dim_noticias(tema_principal);

-- 3. Populate credibility for known sources
-- Layer: institucional (score 1.0)
UPDATE dim_fontes_noticias SET camada = 'institucional', credibilidade_score = 1.0
WHERE LOWER(nome) SIMILAR TO '%(portal da transparencia|camara dos deputados|senado federal|tribunal de contas|ministerio|banco central|ibge|datasus|ipea|bndes|inep|fnde|agencia brasil)%'
  AND camada IS NULL;

-- Layer: jornalismo_premium (score 0.9)
UPDATE dim_fontes_noticias SET camada = 'jornalismo_premium', credibilidade_score = 0.9
WHERE LOWER(nome) SIMILAR TO '%(valor economico|folha|estadao|o globo|jota|poder360|brazil journal|infomoney|exame)%'
  AND camada IS NULL;

-- Layer: setorial (score 0.8)
UPDATE dim_fontes_noticias SET camada = 'setorial', credibilidade_score = 0.8
WHERE LOWER(nome) SIMILAR TO '%(bloomberg|reuters|financial times|neofeed|agfeed|canal rural|globo rural|saude business|capital aberto)%'
  AND camada IS NULL;

-- Layer: think_tank (score 0.6)
UPDATE dim_fontes_noticias SET camada = 'think_tank', credibilidade_score = 0.6
WHERE LOWER(nome) SIMILAR TO '%(fgv|insper|fundacao dom cabral|brookings|rand|instituto millenium|nexo)%'
  AND camada IS NULL;

-- Layer: rede_social (score 0.5)
UPDATE dim_fontes_noticias SET camada = 'rede_social', credibilidade_score = 0.5
WHERE tipo = 'jornalista' AND camada IS NULL;

-- Default remaining to 0.3 (desconhecida)
UPDATE dim_fontes_noticias SET credibilidade_score = 0.3
WHERE credibilidade_score IS NULL OR credibilidade_score = 0.5;

-- 4. Propagate credibility score from fonte to noticias
UPDATE dim_noticias n
SET credibilidade_score = f.credibilidade_score
FROM dim_fontes_noticias f
WHERE n.fonte_id = f.id
  AND n.credibilidade_score IS NULL
  AND f.credibilidade_score IS NOT NULL;

-- 5. Register this enhancement in fontes_dados (compliance)
INSERT INTO fontes_dados (nome, categoria, fonte_primaria, url, confiabilidade, api_key_necessaria)
VALUES (
  'News Intelligence Architecture v1',
  'classificacao',
  'IconsAI Internal',
  'https://iconsai.dev/docs/news-intelligence',
  'alta',
  false
) ON CONFLICT (nome) DO NOTHING;
