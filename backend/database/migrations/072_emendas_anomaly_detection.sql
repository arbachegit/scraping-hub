-- ============================================================
-- ANOMALY DETECTION: emendas com comportamento atipico
--
-- Roda no Brasil Data Hub (mnfjkegtynjtgesfphge)
--
-- Detecta 3 tipos de anomalia:
--   1. Taxa de execucao outlier (Z-score por funcao+ano)
--   2. Valor empenhado outlier (IQR por tipo_emenda)
--   3. Concentracao desproporcional por autor
-- ============================================================

-- RPC 13: ANOMALIAS POR TAXA DE EXECUCAO
-- Z-score: quantos desvios-padrao a emenda esta da media do grupo
CREATE OR REPLACE FUNCTION get_emendas_anomalies_execucao(
  p_min_zscore FLOAT DEFAULT 2.0,
  p_limit INT DEFAULT 50
)
RETURNS JSON AS $$
  WITH stats_by_group AS (
    SELECT
      funcao,
      ano,
      AVG(
        CASE WHEN valor_empenhado > 0
        THEN (valor_pago::float / valor_empenhado) * 100
        ELSE 0 END
      ) AS avg_taxa,
      STDDEV_POP(
        CASE WHEN valor_empenhado > 0
        THEN (valor_pago::float / valor_empenhado) * 100
        ELSE 0 END
      ) AS stddev_taxa,
      COUNT(*) AS group_size
    FROM fato_emendas_parlamentares
    WHERE valor_empenhado > 0
      AND funcao IS NOT NULL
      AND ano IS NOT NULL
    GROUP BY funcao, ano
    HAVING COUNT(*) >= 5
      AND STDDEV_POP(
        CASE WHEN valor_empenhado > 0
        THEN (valor_pago::float / valor_empenhado) * 100
        ELSE 0 END
      ) > 0
  )
  SELECT json_agg(row_order)
  FROM (
    SELECT
      e.id,
      e.autor,
      e.funcao,
      e.ano,
      e.tipo_emenda,
      e.localidade,
      e.valor_empenhado,
      e.valor_pago,
      ROUND(
        (CASE WHEN e.valor_empenhado > 0
         THEN (e.valor_pago::float / e.valor_empenhado) * 100
         ELSE 0 END)::numeric, 1
      ) AS taxa_execucao,
      ROUND(s.avg_taxa::numeric, 1) AS media_grupo,
      ROUND(
        (ABS(
          (CASE WHEN e.valor_empenhado > 0
           THEN (e.valor_pago::float / e.valor_empenhado) * 100
           ELSE 0 END) - s.avg_taxa
        ) / s.stddev_taxa)::numeric, 2
      )::float AS zscore,
      CASE
        WHEN (CASE WHEN e.valor_empenhado > 0
              THEN (e.valor_pago::float / e.valor_empenhado) * 100
              ELSE 0 END) > s.avg_taxa
        THEN 'acima'
        ELSE 'abaixo'
      END AS direcao,
      'taxa_execucao' AS tipo_anomalia
    FROM fato_emendas_parlamentares e
    JOIN stats_by_group s ON e.funcao = s.funcao AND e.ano = s.ano
    WHERE e.valor_empenhado > 0
      AND ABS(
        (CASE WHEN e.valor_empenhado > 0
         THEN (e.valor_pago::float / e.valor_empenhado) * 100
         ELSE 0 END) - s.avg_taxa
      ) / s.stddev_taxa >= p_min_zscore
    ORDER BY
      ABS(
        (CASE WHEN e.valor_empenhado > 0
         THEN (e.valor_pago::float / e.valor_empenhado) * 100
         ELSE 0 END) - s.avg_taxa
      ) / s.stddev_taxa DESC
    LIMIT p_limit
  ) row_order;
$$ LANGUAGE sql STABLE;

-- RPC 14: ANOMALIAS POR VALOR EMPENHADO (IQR)
-- Detecta emendas com valor muito acima do percentil 75 + 1.5*IQR
CREATE OR REPLACE FUNCTION get_emendas_anomalies_valor(
  p_iqr_factor FLOAT DEFAULT 1.5,
  p_limit INT DEFAULT 50
)
RETURNS JSON AS $$
  WITH percentiles AS (
    SELECT
      tipo_emenda,
      PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY valor_empenhado) AS q1,
      PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY valor_empenhado) AS mediana,
      PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY valor_empenhado) AS q3,
      COUNT(*) AS group_size
    FROM fato_emendas_parlamentares
    WHERE valor_empenhado > 0
      AND tipo_emenda IS NOT NULL
    GROUP BY tipo_emenda
    HAVING COUNT(*) >= 10
  ),
  bounds AS (
    SELECT
      tipo_emenda,
      q1, mediana, q3,
      (q3 - q1) AS iqr,
      q1 - p_iqr_factor * (q3 - q1) AS lower_bound,
      q3 + p_iqr_factor * (q3 - q1) AS upper_bound,
      group_size
    FROM percentiles
  )
  SELECT json_agg(row_order)
  FROM (
    SELECT
      e.id,
      e.autor,
      e.funcao,
      e.ano,
      e.tipo_emenda,
      e.localidade,
      e.valor_empenhado,
      e.valor_pago,
      ROUND(b.mediana::numeric, 0) AS mediana_grupo,
      ROUND(b.upper_bound::numeric, 0) AS limite_superior,
      ROUND(
        ((e.valor_empenhado - b.q3) / NULLIF(b.iqr, 0))::numeric, 2
      )::float AS iqr_ratio,
      CASE
        WHEN e.valor_empenhado > b.upper_bound THEN 'acima'
        WHEN e.valor_empenhado < b.lower_bound THEN 'abaixo'
      END AS direcao,
      'valor_empenhado' AS tipo_anomalia
    FROM fato_emendas_parlamentares e
    JOIN bounds b ON e.tipo_emenda = b.tipo_emenda
    WHERE e.valor_empenhado > 0
      AND (e.valor_empenhado > b.upper_bound OR e.valor_empenhado < b.lower_bound)
    ORDER BY
      ABS(e.valor_empenhado - b.mediana) / NULLIF(b.iqr, 0) DESC
    LIMIT p_limit
  ) row_order;
$$ LANGUAGE sql STABLE;

-- RPC 15: CONCENTRACAO ANOMALA POR AUTOR
-- Autores cuja participacao percentual excede 2x a media
CREATE OR REPLACE FUNCTION get_emendas_anomalies_concentracao(
  p_limit INT DEFAULT 30
)
RETURNS JSON AS $$
  WITH autor_totals AS (
    SELECT
      autor,
      SUM(valor_empenhado) AS total_autor,
      COUNT(*) AS num_emendas,
      COUNT(DISTINCT funcao) AS funcoes_distintas,
      COUNT(DISTINCT ano) AS anos_ativos
    FROM fato_emendas_parlamentares
    WHERE valor_empenhado > 0
      AND autor IS NOT NULL
    GROUP BY autor
  ),
  global_stats AS (
    SELECT
      SUM(total_autor) AS total_geral,
      AVG(total_autor) AS media_autor,
      STDDEV_POP(total_autor) AS stddev_autor,
      COUNT(*) AS total_autores
    FROM autor_totals
  )
  SELECT json_agg(row_order)
  FROM (
    SELECT
      a.autor,
      a.num_emendas,
      a.total_autor AS valor_total,
      ROUND((a.total_autor / g.total_geral * 100)::numeric, 2) AS share_percentual,
      ROUND((g.media_autor)::numeric, 0) AS media_por_autor,
      ROUND(
        ((a.total_autor - g.media_autor) / NULLIF(g.stddev_autor, 0))::numeric, 2
      )::float AS zscore,
      a.funcoes_distintas,
      a.anos_ativos,
      'concentracao_autor' AS tipo_anomalia
    FROM autor_totals a
    CROSS JOIN global_stats g
    WHERE a.total_autor > g.media_autor * 2
    ORDER BY a.total_autor DESC
    LIMIT p_limit
  ) row_order;
$$ LANGUAGE sql STABLE;

-- RPC 16: WRAPPER — retorna todos os tipos de anomalia
CREATE OR REPLACE FUNCTION get_emendas_anomalies(
  p_min_zscore FLOAT DEFAULT 2.0,
  p_iqr_factor FLOAT DEFAULT 1.5,
  p_limit INT DEFAULT 30
)
RETURNS JSON AS $$
  SELECT json_build_object(
    'execucao', (SELECT get_emendas_anomalies_execucao(p_min_zscore, p_limit)),
    'valor', (SELECT get_emendas_anomalies_valor(p_iqr_factor, p_limit)),
    'concentracao', (SELECT get_emendas_anomalies_concentracao(p_limit)),
    'metadata', json_build_object(
      'min_zscore', p_min_zscore,
      'iqr_factor', p_iqr_factor,
      'limit_per_type', p_limit,
      'generated_at', NOW()
    )
  );
$$ LANGUAGE sql STABLE;
