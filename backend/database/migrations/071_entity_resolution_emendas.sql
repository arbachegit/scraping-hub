-- ============================================================
-- ENTITY RESOLUTION: emenda.autor ↔ dim_politicos
--
-- Roda no Brasil Data Hub (mnfjkegtynjtgesfphge)
--
-- Problema: fato_emendas_parlamentares.autor e um TEXT livre
--           ("FULANO DE TAL"), sem FK para dim_politicos.
--           Precisamos resolver essa ligacao para o grafo.
--
-- Solucao: pg_trgm + unaccent para match fuzzy.
-- ============================================================

-- Garante extensoes necessarias
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 1. COLUNA: politico_id na tabela de emendas
ALTER TABLE fato_emendas_parlamentares
  ADD COLUMN IF NOT EXISTS politico_id UUID;

CREATE INDEX IF NOT EXISTS idx_emendas_politico_id
  ON fato_emendas_parlamentares (politico_id)
  WHERE politico_id IS NOT NULL;

-- 2. FUNCAO: normaliza texto para comparacao
CREATE OR REPLACE FUNCTION normalize_name(input TEXT)
RETURNS TEXT AS $$
  SELECT LOWER(TRIM(
    regexp_replace(
      unaccent(COALESCE(input, '')),
      '\s+', ' ', 'g'
    )
  ));
$$ LANGUAGE sql IMMUTABLE;

-- 3. RPC: resolve autores de emendas para politicos
-- Usa similarity() do pg_trgm para match fuzzy
-- Retorna mapeamento autor → politico com score
CREATE OR REPLACE FUNCTION resolve_emenda_autores(
  p_batch_size INT DEFAULT 500,
  p_min_similarity FLOAT DEFAULT 0.4
)
RETURNS JSON AS $$
DECLARE
  v_resolved INT := 0;
  v_skipped INT := 0;
  v_total INT := 0;
  v_rows INT := 0;
  v_rec RECORD;
  v_best_politico UUID;
  v_best_score FLOAT;
  v_best_name TEXT;
BEGIN
  -- Processar emendas sem politico_id
  FOR v_rec IN
    SELECT DISTINCT autor
    FROM fato_emendas_parlamentares
    WHERE politico_id IS NULL
      AND autor IS NOT NULL
      AND LENGTH(autor) >= 3
    LIMIT p_batch_size
  LOOP
    v_total := v_total + 1;

    -- Buscar melhor match em dim_politicos
    SELECT
      p.id,
      GREATEST(
        similarity(normalize_name(p.nome_urna), normalize_name(v_rec.autor)),
        similarity(normalize_name(p.nome_completo), normalize_name(v_rec.autor))
      ) AS score,
      COALESCE(p.nome_urna, p.nome_completo) AS nome
    INTO v_best_politico, v_best_score, v_best_name
    FROM dim_politicos p
    WHERE
      similarity(normalize_name(p.nome_urna), normalize_name(v_rec.autor)) >= p_min_similarity
      OR similarity(normalize_name(p.nome_completo), normalize_name(v_rec.autor)) >= p_min_similarity
    ORDER BY score DESC
    LIMIT 1;

    IF v_best_politico IS NOT NULL AND v_best_score >= p_min_similarity THEN
      -- Atualizar todas as emendas deste autor
      UPDATE fato_emendas_parlamentares
      SET politico_id = v_best_politico
      WHERE autor = v_rec.autor
        AND politico_id IS NULL;

      GET DIAGNOSTICS v_rows = ROW_COUNT;
      v_resolved := v_resolved + v_rows;
    ELSE
      v_skipped := v_skipped + 1;
    END IF;
  END LOOP;

  RETURN json_build_object(
    'autores_processados', v_total,
    'autores_resolvidos', v_total - v_skipped,
    'autores_sem_match', v_skipped,
    'emendas_atualizadas', v_resolved
  );
END;
$$ LANGUAGE plpgsql;

-- 4. RPC: retorna mapeamento autor → politico (read-only, para diagnostico)
CREATE OR REPLACE FUNCTION get_emendas_entity_resolution_status()
RETURNS JSON AS $$
  SELECT json_build_object(
    'total_emendas', (SELECT COUNT(*) FROM fato_emendas_parlamentares),
    'com_politico_id', (SELECT COUNT(*) FROM fato_emendas_parlamentares WHERE politico_id IS NOT NULL),
    'sem_politico_id', (SELECT COUNT(*) FROM fato_emendas_parlamentares WHERE politico_id IS NULL),
    'autores_distintos', (SELECT COUNT(DISTINCT autor) FROM fato_emendas_parlamentares WHERE autor IS NOT NULL),
    'autores_resolvidos', (SELECT COUNT(DISTINCT autor) FROM fato_emendas_parlamentares WHERE politico_id IS NOT NULL),
    'top_nao_resolvidos', (
      SELECT json_agg(row_order)
      FROM (
        SELECT autor, COUNT(*) AS total_emendas
        FROM fato_emendas_parlamentares
        WHERE politico_id IS NULL AND autor IS NOT NULL
        GROUP BY autor
        ORDER BY COUNT(*) DESC
        LIMIT 20
      ) row_order
    )
  );
$$ LANGUAGE sql STABLE;

-- 5. RPC: busca politico para um autor especifico (para context endpoint)
CREATE OR REPLACE FUNCTION find_politico_by_autor(p_autor TEXT)
RETURNS JSON AS $$
  SELECT json_build_object(
    'politico_id', p.id,
    'nome_completo', p.nome_completo,
    'nome_urna', p.nome_urna,
    'estado', p.estado,
    'cidade', p.cidade,
    'similarity_score', GREATEST(
      similarity(normalize_name(p.nome_urna), normalize_name(p_autor)),
      similarity(normalize_name(p.nome_completo), normalize_name(p_autor))
    )
  )
  FROM dim_politicos p
  WHERE
    similarity(normalize_name(p.nome_urna), normalize_name(p_autor)) >= 0.4
    OR similarity(normalize_name(p.nome_completo), normalize_name(p_autor)) >= 0.4
  ORDER BY GREATEST(
    similarity(normalize_name(p.nome_urna), normalize_name(p_autor)),
    similarity(normalize_name(p.nome_completo), normalize_name(p_autor))
  ) DESC
  LIMIT 1;
$$ LANGUAGE sql STABLE;
