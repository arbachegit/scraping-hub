-- Migration: 016_add_mandatos_category.sql
-- Descricao: Adicionar 'mandatos' como categoria valida em stats_historico
-- Data: 2026-02-23
-- Autor: IconsAI

-- Remover constraint antiga
ALTER TABLE stats_historico DROP CONSTRAINT IF EXISTS stats_historico_categoria_check;

-- Adicionar nova constraint com mandatos
ALTER TABLE stats_historico
ADD CONSTRAINT stats_historico_categoria_check
CHECK (categoria IN ('empresas', 'pessoas', 'politicos', 'mandatos', 'noticias'));

-- Comentario atualizado
COMMENT ON COLUMN stats_historico.categoria IS 'Categoria: empresas, pessoas, politicos, mandatos, noticias';
