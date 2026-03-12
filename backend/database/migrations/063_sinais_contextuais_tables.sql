-- ============================================================
-- Migration 063: Create dim_sinais_contextuais + fato_noticias_sinais
--
-- Migration 051 only had INSERTs but no CREATE TABLE.
-- This migration creates the tables first, then 051 can populate them.
-- ============================================================

-- 1. TABELA DE SINAIS CONTEXTUAIS
CREATE TABLE IF NOT EXISTS dim_sinais_contextuais (
  id SERIAL PRIMARY KEY,
  nome TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  categoria TEXT NOT NULL,          -- economia, politica, mercado, saude, educacao, etc.
  tipo TEXT NOT NULL DEFAULT 'sinal', -- alerta, positivo, sinal
  keywords_regex TEXT,              -- regex pattern para detecção automática
  descricao TEXT,
  prioridade INTEGER DEFAULT 50,    -- 0-100, maior = mais relevante
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sinais_categoria ON dim_sinais_contextuais (categoria);
CREATE INDEX IF NOT EXISTS idx_sinais_ativo ON dim_sinais_contextuais (ativo) WHERE ativo = true;

-- 2. TABELA JUNCTION: NOTÍCIA ↔ SINAL
CREATE TABLE IF NOT EXISTS fato_noticias_sinais (
  id SERIAL PRIMARY KEY,
  noticia_id UUID NOT NULL REFERENCES dim_noticias(id) ON DELETE CASCADE,
  sinal_id INTEGER NOT NULL REFERENCES dim_sinais_contextuais(id) ON DELETE CASCADE,
  confidence NUMERIC(3,2) DEFAULT 0.50,  -- 0.0 a 1.0
  detection_method VARCHAR(30) DEFAULT 'regex', -- 'ia', 'regex', 'manual'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uk_noticia_sinal UNIQUE (noticia_id, sinal_id)
);

CREATE INDEX IF NOT EXISTS idx_noticias_sinais_noticia ON fato_noticias_sinais (noticia_id);
CREATE INDEX IF NOT EXISTS idx_noticias_sinais_sinal ON fato_noticias_sinais (sinal_id);

-- 3. RPC para buscar sinais de uma notícia com detalhes
CREATE OR REPLACE FUNCTION get_noticias_sinais(p_noticia_id UUID)
RETURNS TABLE (
  sinal_id INTEGER,
  slug TEXT,
  nome TEXT,
  categoria TEXT,
  tipo TEXT,
  prioridade INTEGER,
  confianca NUMERIC,
  metodo VARCHAR
) LANGUAGE sql STABLE AS $$
  SELECT
    s.id AS sinal_id,
    s.slug,
    s.nome,
    s.categoria,
    s.tipo,
    s.prioridade,
    ns.confidence AS confianca,
    ns.detection_method AS metodo
  FROM fato_noticias_sinais ns
  JOIN dim_sinais_contextuais s ON s.id = ns.sinal_id
  WHERE ns.noticia_id = p_noticia_id
  ORDER BY s.prioridade DESC;
$$;

-- 4. RPC para buscar notícias por sinal
CREATE OR REPLACE FUNCTION get_noticias_by_sinal(p_sinal_slug TEXT, p_limit INTEGER DEFAULT 20)
RETURNS TABLE (
  noticia_id UUID,
  titulo TEXT,
  resumo TEXT,
  fonte_nome TEXT,
  data_publicacao TIMESTAMPTZ,
  tema_principal TEXT,
  credibilidade_score FLOAT,
  confianca NUMERIC
) LANGUAGE sql STABLE AS $$
  SELECT
    n.id AS noticia_id,
    n.titulo,
    n.resumo,
    n.fonte_nome,
    n.data_publicacao,
    n.tema_principal,
    n.credibilidade_score,
    ns.confidence AS confianca
  FROM fato_noticias_sinais ns
  JOIN dim_noticias n ON n.id = ns.noticia_id
  JOIN dim_sinais_contextuais s ON s.id = ns.sinal_id
  WHERE s.slug = p_sinal_slug
  ORDER BY n.data_publicacao DESC
  LIMIT p_limit;
$$;
