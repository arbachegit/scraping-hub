-- Indexes for fato_emendas_favorecidos to support context RPCs
-- Required because the table has 733k+ rows and GROUP BY queries timeout

-- For get_emendas_top_destinos (GROUP BY uf_favorecido)
CREATE INDEX IF NOT EXISTS idx_fato_emendas_favorecidos_uf
  ON fato_emendas_favorecidos (uf_favorecido)
  WHERE uf_favorecido IS NOT NULL;

-- For get_emendas_beneficiary_focus (GROUP BY tipo_favorecido)
CREATE INDEX IF NOT EXISTS idx_fato_emendas_favorecidos_tipo
  ON fato_emendas_favorecidos (tipo_favorecido)
  WHERE tipo_favorecido IS NOT NULL;

-- Composite for common lookups
CREATE INDEX IF NOT EXISTS idx_fato_emendas_favorecidos_uf_valor
  ON fato_emendas_favorecidos (uf_favorecido, valor_recebido)
  WHERE uf_favorecido IS NOT NULL;
