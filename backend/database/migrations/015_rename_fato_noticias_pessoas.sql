-- Migration 015: Renomear fato_noticias_pessoas para fato_pessoas
-- Data: 2026-02-22
-- Descrição: Simplifica o nome da tabela de relação notícia-pessoa

-- 1. Renomear a tabela
ALTER TABLE IF EXISTS fato_noticias_pessoas RENAME TO fato_pessoas;

-- 2. Renomear índices para manter consistência
ALTER INDEX IF EXISTS idx_not_pes_noticia RENAME TO idx_fato_pessoas_noticia;
ALTER INDEX IF EXISTS idx_not_pes_pessoa RENAME TO idx_fato_pessoas_pessoa;

-- 3. Atualizar comentário da tabela
COMMENT ON TABLE fato_pessoas IS 'Relação entre notícias e pessoas (menções, autoria)';
