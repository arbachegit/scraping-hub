-- ============================================================
-- EMENDAS CONTEXT INTELLIGENCE RPCs
-- Engenharia de contexto: não são SUMs, são respostas.
--
-- RPC 1: "Qual é o panorama geral?" → totais + taxa execução
-- RPC 2: "Pra quem vai o dinheiro?" → foco do beneficiário
-- RPC 3: "Onde mais se investe?" → top funções com execução
-- RPC 4: "Quem mais direciona?" → top autores com eficiência
-- RPC 5: "Pra onde vai?" → destino geográfico (favorecidos)
-- RPC 6: "Qual o perfil?" → tipos de emenda
-- RPC 7: "Como o dinheiro flui?" → mecanismos (pix/convênio/RP9)
-- ============================================================

-- RPC 1: PANORAMA GERAL
-- Responde: "Quanto existe, quanto foi executado, quanto está parado?"
CREATE OR REPLACE FUNCTION get_emendas_context_totals()
RETURNS JSON AS $$
  SELECT json_build_object(
    'total_emendas', COUNT(*),
    'valor_empenhado', COALESCE(SUM(valor_empenhado), 0),
    'valor_liquidado', COALESCE(SUM(valor_liquidado), 0),
    'valor_pago', COALESCE(SUM(valor_pago), 0),
    'valor_resto_a_pagar',
      COALESCE(SUM(valor_resto_inscrito), 0)
      - COALESCE(SUM(valor_resto_cancelado), 0)
      - COALESCE(SUM(valor_resto_pago), 0),
    'autores_unicos', COUNT(DISTINCT autor),
    'partidos_unicos', COUNT(DISTINCT partido),
    'taxa_execucao', CASE
      WHEN COALESCE(SUM(valor_empenhado), 0) > 0
      THEN ROUND((COALESCE(SUM(valor_pago), 0) / SUM(valor_empenhado) * 100)::numeric, 1)
      ELSE 0
    END,
    'total_emendas_pix', COUNT(*) FILTER (WHERE is_emenda_pix = true),
    'ano_min', MIN(ano),
    'ano_max', MAX(ano)
  )
  FROM fato_emendas_parlamentares;
$$ LANGUAGE sql STABLE;


-- RPC 2: FOCO DO BENEFICIÁRIO
-- Responde: "O dinheiro vai pra mercado (PJ), cidadão (PF) ou governo (UG)?"
CREATE OR REPLACE FUNCTION get_emendas_beneficiary_focus()
RETURNS JSON AS $$
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
  FROM (
    SELECT
      tipo_favorecido,
      COUNT(*) as count,
      COALESCE(SUM(valor_recebido), 0) as valor_total,
      ROUND(
        COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM fato_emendas_favorecidos), 0) * 100,
        1
      ) as percentual
    FROM fato_emendas_favorecidos
    WHERE tipo_favorecido IS NOT NULL
    GROUP BY tipo_favorecido
    ORDER BY valor_total DESC
  ) t;
$$ LANGUAGE sql STABLE;


-- RPC 3: TOP FUNÇÕES (com taxa de execução)
-- Responde: "Onde mais se investe e quão eficiente é cada área?"
CREATE OR REPLACE FUNCTION get_emendas_top_funcoes(p_limit int DEFAULT 10)
RETURNS JSON AS $$
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
  FROM (
    SELECT
      funcao,
      COUNT(*) as count,
      COALESCE(SUM(valor_empenhado), 0) as valor_empenhado,
      COALESCE(SUM(valor_pago), 0) as valor_pago,
      CASE
        WHEN COALESCE(SUM(valor_empenhado), 0) > 0
        THEN ROUND((COALESCE(SUM(valor_pago), 0) / SUM(valor_empenhado) * 100)::numeric, 1)
        ELSE 0
      END as taxa_execucao
    FROM fato_emendas_parlamentares
    WHERE funcao IS NOT NULL
    GROUP BY funcao
    ORDER BY valor_empenhado DESC
    LIMIT p_limit
  ) t;
$$ LANGUAGE sql STABLE;


-- RPC 4: TOP AUTORES (com eficiência)
-- Responde: "Quem mais direciona recursos e com que eficiência?"
CREATE OR REPLACE FUNCTION get_emendas_context_top_autores(p_limit int DEFAULT 10)
RETURNS JSON AS $$
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
  FROM (
    SELECT
      autor,
      COUNT(*) as count,
      COALESCE(SUM(valor_empenhado), 0) as valor_empenhado,
      COALESCE(SUM(valor_pago), 0) as valor_pago,
      COUNT(DISTINCT funcao) as funcoes_distintas,
      CASE
        WHEN COALESCE(SUM(valor_empenhado), 0) > 0
        THEN ROUND((COALESCE(SUM(valor_pago), 0) / SUM(valor_empenhado) * 100)::numeric, 1)
        ELSE 0
      END as taxa_execucao
    FROM fato_emendas_parlamentares
    WHERE autor IS NOT NULL
    GROUP BY autor
    ORDER BY valor_empenhado DESC
    LIMIT p_limit
  ) t;
$$ LANGUAGE sql STABLE;


-- RPC 5: TOP DESTINOS GEOGRÁFICOS (de favorecidos, não origem)
-- Responde: "Pra onde de fato vai o dinheiro?"
CREATE OR REPLACE FUNCTION get_emendas_top_destinos(p_limit int DEFAULT 10)
RETURNS JSON AS $$
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
  FROM (
    SELECT
      uf_favorecido as uf,
      COUNT(*) as count,
      COALESCE(SUM(valor_recebido), 0) as valor_total,
      COUNT(DISTINCT municipio_favorecido) as municipios_distintos
    FROM fato_emendas_favorecidos
    WHERE uf_favorecido IS NOT NULL
    GROUP BY uf_favorecido
    ORDER BY valor_total DESC
    LIMIT p_limit
  ) t;
$$ LANGUAGE sql STABLE;


-- RPC 6: POR TIPO DE EMENDA
-- Responde: "Qual o perfil das emendas? Individual, bancada, comissão?"
CREATE OR REPLACE FUNCTION get_emendas_by_tipo_emenda()
RETURNS JSON AS $$
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
  FROM (
    SELECT
      tipo_emenda,
      COUNT(*) as count,
      COALESCE(SUM(valor_empenhado), 0) as valor_empenhado,
      COALESCE(SUM(valor_pago), 0) as valor_pago,
      CASE
        WHEN COALESCE(SUM(valor_empenhado), 0) > 0
        THEN ROUND((COALESCE(SUM(valor_pago), 0) / SUM(valor_empenhado) * 100)::numeric, 1)
        ELSE 0
      END as taxa_execucao
    FROM fato_emendas_parlamentares
    WHERE tipo_emenda IS NOT NULL
    GROUP BY tipo_emenda
    ORDER BY valor_empenhado DESC
  ) t;
$$ LANGUAGE sql STABLE;


-- RPC 7: MECANISMOS DE TRANSFERÊNCIA
-- Responde: "Como o dinheiro chega? Via convênio, PIX ou apoiamento?"
CREATE OR REPLACE FUNCTION get_emendas_mecanismos()
RETURNS JSON AS $$
  SELECT json_build_object(
    'convenios', (
      SELECT json_build_object(
        'count', COUNT(*),
        'valor_total', COALESCE(SUM(valor_convenio), 0)
      )
      FROM fato_emendas_convenios
    ),
    'emendas_pix', (
      SELECT json_build_object(
        'count', COUNT(*),
        'valor_empenhado', COALESCE(SUM(valor_empenhado), 0),
        'valor_pago', COALESCE(SUM(valor_pago), 0)
      )
      FROM fato_emendas_parlamentares
      WHERE is_emenda_pix = true
    ),
    'apoiamento_rp9', (
      SELECT json_build_object(
        'count', COUNT(*),
        'valor_empenhado', COALESCE(SUM(valor_empenhado), 0),
        'valor_pago', COALESCE(SUM(valor_pago), 0)
      )
      FROM fato_emendas_apoiamento
    )
  );
$$ LANGUAGE sql STABLE;
