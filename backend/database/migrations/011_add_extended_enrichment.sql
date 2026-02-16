-- Migration 011: Add extended enrichment fields
-- Adds fields for GitHub, Google Scholar, Google News, and Reclame Aqui enrichment

-- Add raw_enrichment_extended column to dim_pessoas
ALTER TABLE dim_pessoas
ADD COLUMN IF NOT EXISTS raw_enrichment_extended JSONB;

-- Add index for checking if enrichment was done
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_enrichment_extended
ON dim_pessoas ((raw_enrichment_extended IS NOT NULL));

-- Comment explaining the field
COMMENT ON COLUMN dim_pessoas.raw_enrichment_extended IS 'Extended enrichment data from GitHub, Google Scholar, Google News, Reclame Aqui';

-- Register new data sources (if not already exists)
INSERT INTO fontes_dados (nome, categoria, fonte_primaria, url, documentacao_url, formato, api_key_necessaria, confiabilidade, observacoes)
VALUES
  ('GitHub API', 'competencias', 'GitHub', 'https://api.github.com', 'https://docs.github.com/en/rest', 'JSON', false, 'alta', 'Perfil técnico de desenvolvedores - repositórios, linguagens, contribuições'),
  ('Google Scholar (via Serper)', 'competencias', 'Google Scholar', 'https://scholar.google.com', 'https://serper.dev/docs', 'JSON', true, 'alta', 'Publicações acadêmicas, citações, h-index'),
  ('Google News (via Serper)', 'reputacional', 'Google News', 'https://news.google.com', 'https://serper.dev/docs', 'JSON', true, 'media', 'Notícias e menções na mídia'),
  ('Reclame Aqui (via Serper)', 'reputacional', 'Reclame Aqui', 'https://www.reclameaqui.com.br', NULL, 'HTML', false, 'media', 'Reclamações de consumidores - busca por nome de pessoa/empresa')
ON CONFLICT (nome) DO NOTHING;
