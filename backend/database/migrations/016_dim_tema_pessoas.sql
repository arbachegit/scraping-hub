-- Migration 016: Criar dim_tema_pessoas e ajustar fato_pessoas
-- Data: 2026-02-22
-- Descrição: Adiciona dimensão de temas para pessoas e reestrutura fato_pessoas

-- ===========================================
-- 1. CRIAR TABELA dim_tema_pessoas
-- ===========================================

CREATE TABLE IF NOT EXISTS dim_tema_pessoas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tema VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para busca por tema
CREATE INDEX IF NOT EXISTS idx_dim_tema_pessoas_tema ON dim_tema_pessoas(tema);

-- Comentário da tabela
COMMENT ON TABLE dim_tema_pessoas IS 'Dimensão de temas/categorias para relacionamentos de pessoas';

-- ===========================================
-- 2. INSERIR TEMAS
-- ===========================================

INSERT INTO dim_tema_pessoas (tema) VALUES
    ('formacao_academica'),
    ('eventos'),
    ('viagens_negocios'),
    ('viagens_passeio'),
    ('cargo'),
    ('empresa'),
    ('cargo_empresa'),
    ('palestra'),
    ('premios'),
    ('artigos'),
    ('congressos'),
    ('cowork'),
    ('producao_intelectual')
ON CONFLICT (tema) DO NOTHING;

-- ===========================================
-- 3. MODIFICAR TABELA fato_pessoas
-- ===========================================

-- 3.1 Adicionar coluna id_tema
ALTER TABLE fato_pessoas
ADD COLUMN IF NOT EXISTS id_tema UUID REFERENCES dim_tema_pessoas(id) ON DELETE SET NULL;

-- 3.2 Renomear coluna contexto para ano
ALTER TABLE fato_pessoas
RENAME COLUMN contexto TO ano;

-- 3.3 Alterar tipo da coluna ano para INTEGER (opcional, se quiser forçar formato numérico)
-- ALTER TABLE fato_pessoas ALTER COLUMN ano TYPE INTEGER USING ano::INTEGER;

-- 3.4 Adicionar coluna id_fonte_dados
ALTER TABLE fato_pessoas
ADD COLUMN IF NOT EXISTS id_fonte_dados UUID REFERENCES fontes_dados(id) ON DELETE SET NULL;

-- ===========================================
-- 4. CRIAR ÍNDICES
-- ===========================================

CREATE INDEX IF NOT EXISTS idx_fato_pessoas_tema ON fato_pessoas(id_tema);
CREATE INDEX IF NOT EXISTS idx_fato_pessoas_fonte ON fato_pessoas(id_fonte_dados);
CREATE INDEX IF NOT EXISTS idx_fato_pessoas_ano ON fato_pessoas(ano);

-- ===========================================
-- 5. COMENTÁRIOS
-- ===========================================

COMMENT ON COLUMN fato_pessoas.id_tema IS 'FK para dim_tema_pessoas - tipo de relacionamento/contexto';
COMMENT ON COLUMN fato_pessoas.ano IS 'Ano do evento/relacionamento';
COMMENT ON COLUMN fato_pessoas.id_fonte_dados IS 'FK para fontes_dados - origem da informação';
