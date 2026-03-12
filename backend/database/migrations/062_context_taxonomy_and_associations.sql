-- ============================================================
-- CONTEXT ENGINEERING: Taxonomia compartilhada + Associações
--
-- Roda no iconsai-scraping (redivrmeajmktenwshmn)
-- Conecta emendas e notícias por camada semântica
-- ============================================================

-- 1. TAXONOMIA TEMÁTICA UNIFICADA
-- Vocabulário comum entre emendas (funcao) e notícias (tema_principal)
CREATE TABLE IF NOT EXISTS dim_taxonomia_tematica (
  id SERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,           -- chave canônica: 'saude', 'educacao', etc.
  nome TEXT NOT NULL,                  -- nome para display: 'Saúde', 'Educação', etc.
  descricao TEXT,
  dominio TEXT DEFAULT 'ambos',        -- 'emendas', 'noticias', 'ambos'
  cor TEXT,                            -- cor hex para UI
  icone TEXT,                          -- nome do ícone lucide
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Populate taxonomy
INSERT INTO dim_taxonomia_tematica (slug, nome, descricao, dominio, cor, icone) VALUES
  ('saude', 'Saúde', 'Saúde pública, SUS, hospitais, farmacêutica', 'ambos', '#10b981', 'heart-pulse'),
  ('educacao', 'Educação', 'Ensino, universidades, escolas, ENEM', 'ambos', '#3b82f6', 'graduation-cap'),
  ('economia', 'Economia', 'Macroeconomia, PIB, inflação, juros, câmbio, encargos', 'ambos', '#f59e0b', 'trending-up'),
  ('mercado', 'Mercado', 'Bolsa, ações, comércio, indústria, empresas', 'ambos', '#8b5cf6', 'building-2'),
  ('politica', 'Política', 'Governo, legislação, eleições, políticas públicas', 'noticias', '#ef4444', 'landmark'),
  ('agricultura', 'Agricultura', 'Agronegócio, safra, exportações agrícolas, organização agrária', 'ambos', '#84cc16', 'wheat'),
  ('seguranca_publica', 'Segurança Pública', 'Criminalidade, polícia, justiça, defesa', 'ambos', '#f97316', 'shield'),
  ('tecnologia', 'Tecnologia', 'TI, startups, IA, telecomunicações, ciência', 'ambos', '#06b6d4', 'cpu'),
  ('infraestrutura', 'Infraestrutura', 'Obras, saneamento, transporte, urbanismo, logística, habitação', 'ambos', '#64748b', 'hard-hat'),
  ('energia', 'Energia', 'Petróleo, gás, elétrica, renováveis', 'ambos', '#eab308', 'zap'),
  ('assistencia_social', 'Assistência Social', 'Assistência social, direitos da cidadania, previdência', 'emendas', '#ec4899', 'hand-heart'),
  ('cultura_lazer', 'Cultura e Lazer', 'Cultura, desporto, lazer, comunicações', 'emendas', '#a855f7', 'palette'),
  ('defesa', 'Defesa', 'Defesa nacional, relações exteriores', 'emendas', '#475569', 'shield-alert'),
  ('meio_ambiente', 'Meio Ambiente', 'Gestão ambiental, sustentabilidade', 'ambos', '#22c55e', 'leaf'),
  ('geral', 'Geral', 'Múltiplos temas ou não classificado', 'ambos', '#94a3b8', 'layers')
ON CONFLICT (slug) DO NOTHING;

-- 2. MAPEAMENTO: funcao (emendas) → taxonomia
-- Normaliza as ~46 variantes de funcao para 15 slugs
CREATE TABLE IF NOT EXISTS map_funcao_taxonomia (
  funcao TEXT PRIMARY KEY,             -- valor exato da coluna funcao nas emendas
  taxonomia_slug TEXT NOT NULL REFERENCES dim_taxonomia_tematica(slug)
);

INSERT INTO map_funcao_taxonomia (funcao, taxonomia_slug) VALUES
  -- Saúde
  ('Saúde', 'saude'),
  ('10-Saúde', 'saude'),
  -- Educação
  ('Educação', 'educacao'),
  ('12-Educação', 'educacao'),
  -- Economia
  ('Encargos especiais', 'economia'),
  ('Administração', 'economia'),
  ('Previdência social', 'economia'),
  -- Mercado
  ('Comércio e serviços', 'mercado'),
  ('23-Comércio e Serviços', 'mercado'),
  ('Indústria', 'mercado'),
  ('22-Indústria', 'mercado'),
  -- Agricultura
  ('Agricultura', 'agricultura'),
  ('20-Agricultura', 'agricultura'),
  ('Organização agrária', 'agricultura'),
  ('21-Organização Agrária', 'agricultura'),
  -- Segurança
  ('Segurança pública', 'seguranca_publica'),
  ('6-Segurança Pública', 'seguranca_publica'),
  ('Essencial à justiça', 'seguranca_publica'),
  -- Tecnologia
  ('Ciência e Tecnologia', 'tecnologia'),
  ('19-Ciência e Tecnologia', 'tecnologia'),
  ('Comunicações', 'tecnologia'),
  -- Infraestrutura
  ('Urbanismo', 'infraestrutura'),
  ('15-Urbanismo', 'infraestrutura'),
  ('Transporte', 'infraestrutura'),
  ('26-Transporte', 'infraestrutura'),
  ('Saneamento', 'infraestrutura'),
  ('17-Saneamento', 'infraestrutura'),
  ('Habitação', 'infraestrutura'),
  ('16-Habitação', 'infraestrutura'),
  -- Energia
  ('Energia', 'energia'),
  ('25-Energia', 'energia'),
  -- Assistência social
  ('Assistência social', 'assistencia_social'),
  ('8-Assistência Social', 'assistencia_social'),
  ('Direitos da cidadania', 'assistencia_social'),
  ('14-Direitos da Cidadania', 'assistencia_social'),
  ('Trabalho', 'assistencia_social'),
  ('11-Trabalho', 'assistencia_social'),
  -- Cultura e lazer
  ('Cultura', 'cultura_lazer'),
  ('13-Cultura', 'cultura_lazer'),
  ('Desporto e lazer', 'cultura_lazer'),
  ('27-Desporto e Lazer', 'cultura_lazer'),
  -- Defesa
  ('Defesa nacional', 'defesa'),
  ('Relações exteriores', 'defesa'),
  -- Meio ambiente
  ('Gestão ambiental', 'meio_ambiente'),
  ('18-Gestão Ambiental', 'meio_ambiente'),
  -- Geral
  ('Múltiplo', 'geral')
ON CONFLICT (funcao) DO NOTHING;

-- 3. MAPEAMENTO: tema_principal (noticias) → taxonomia
-- Noticias já usam slugs, mas precisamos garantir mapeamento explícito
CREATE TABLE IF NOT EXISTS map_tema_taxonomia (
  tema_principal TEXT PRIMARY KEY,     -- valor exato da coluna tema_principal nas notícias
  taxonomia_slug TEXT NOT NULL REFERENCES dim_taxonomia_tematica(slug)
);

INSERT INTO map_tema_taxonomia (tema_principal, taxonomia_slug) VALUES
  ('saude', 'saude'),
  ('educacao', 'educacao'),
  ('economia', 'economia'),
  ('mercado', 'mercado'),
  ('politica', 'politica'),
  ('agricultura', 'agricultura'),
  ('seguranca_publica', 'seguranca_publica'),
  ('tecnologia', 'tecnologia'),
  ('infraestrutura', 'infraestrutura'),
  ('energia', 'energia'),
  ('geral', 'geral')
ON CONFLICT (tema_principal) DO NOTHING;

-- 4. TABELA DE ASSOCIAÇÕES CONTEXTUAIS
-- O elo que conecta emendas ↔ notícias ↔ entidades
CREATE TABLE IF NOT EXISTS fato_associacoes_contextuais (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  origem_tipo TEXT NOT NULL,           -- 'emenda', 'noticia', 'pessoa', 'empresa'
  origem_id TEXT NOT NULL,             -- ID na tabela de origem
  destino_tipo TEXT NOT NULL,          -- 'emenda', 'noticia', 'pessoa', 'empresa'
  destino_id TEXT NOT NULL,            -- ID na tabela de destino
  tipo_associacao TEXT NOT NULL,       -- 'tema_comum', 'territorio_comum', 'mencao', 'autor_citado'
  taxonomia_slug TEXT REFERENCES dim_taxonomia_tematica(slug),
  confianca FLOAT DEFAULT 0.5,        -- 0.0 a 1.0
  metodo TEXT DEFAULT 'regra',        -- 'manual', 'ia', 'regra', 'grafo'
  evidencia TEXT,                      -- descrição da evidência da associação
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_assoc_origem ON fato_associacoes_contextuais (origem_tipo, origem_id);
CREATE INDEX IF NOT EXISTS idx_assoc_destino ON fato_associacoes_contextuais (destino_tipo, destino_id);
CREATE INDEX IF NOT EXISTS idx_assoc_tipo ON fato_associacoes_contextuais (tipo_associacao);
CREATE INDEX IF NOT EXISTS idx_assoc_taxonomia ON fato_associacoes_contextuais (taxonomia_slug);
-- Prevent duplicate associations
CREATE UNIQUE INDEX IF NOT EXISTS idx_assoc_unique
  ON fato_associacoes_contextuais (origem_tipo, origem_id, destino_tipo, destino_id, tipo_associacao);
