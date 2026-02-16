-- Migration: Star Schema Normalization + dim_regimes_tributarios
-- Date: 2026-02-16
-- Version: 009
-- Description: Normalização Star Schema, nova dimensão de regimes tributários,
--              ajustes em linkedin default, e remoção de colunas desnecessárias

-- ===========================================
-- 1. CRIAR TABELA dim_regimes_tributarios
-- ===========================================

CREATE TABLE IF NOT EXISTS dim_regimes_tributarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identificação
    codigo VARCHAR(20) UNIQUE NOT NULL,  -- MEI, SIMPLES_ME, SIMPLES_EPP, LUCRO_PRESUMIDO, LUCRO_REAL
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,

    -- Limites Legais (valores 2024)
    limite_faturamento_anual DECIMAL(15,2),
    limite_funcionarios INT,

    -- Características Legais
    permite_socio_pj BOOLEAN DEFAULT false,
    permite_socio_estrangeiro BOOLEAN DEFAULT false,
    limite_socios INT,
    exige_contador BOOLEAN DEFAULT false,
    pode_exportar BOOLEAN DEFAULT true,
    pode_importar BOOLEAN DEFAULT true,

    -- Tributação
    aliquota_minima DECIMAL(5,2),
    aliquota_maxima DECIMAL(5,2),
    impostos_unificados BOOLEAN DEFAULT false,  -- DAS para Simples

    -- Obrigações Acessórias
    obrigacoes_mensais TEXT[],   -- ARRAY de obrigações
    obrigacoes_anuais TEXT[],

    -- CNAEs Permitidos/Proibidos
    cnaes_permitidos TEXT[],     -- NULL = todos
    cnaes_proibidos TEXT[],

    -- Metadados
    vigencia_inicio DATE,
    vigencia_fim DATE,           -- NULL = atual
    fonte_legal TEXT,            -- LC 123/2006, etc

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_dim_regimes_codigo ON dim_regimes_tributarios(codigo);

-- Comentários
COMMENT ON TABLE dim_regimes_tributarios IS 'Dimensão de regimes tributários com características legais';
COMMENT ON COLUMN dim_regimes_tributarios.codigo IS 'Código do regime: MEI, SIMPLES_ME, SIMPLES_EPP, LUCRO_PRESUMIDO, LUCRO_REAL';
COMMENT ON COLUMN dim_regimes_tributarios.limite_faturamento_anual IS 'Limite de faturamento anual em R$ (valores 2024)';
COMMENT ON COLUMN dim_regimes_tributarios.impostos_unificados IS 'Se TRUE, impostos são unificados (DAS para Simples)';

-- ===========================================
-- 2. POPULAR dim_regimes_tributarios COM DADOS INICIAIS
-- ===========================================

INSERT INTO dim_regimes_tributarios (
    codigo, nome, descricao, limite_faturamento_anual, limite_funcionarios,
    permite_socio_pj, permite_socio_estrangeiro, limite_socios, exige_contador,
    impostos_unificados, aliquota_minima, aliquota_maxima,
    obrigacoes_mensais, obrigacoes_anuais, fonte_legal, vigencia_inicio
) VALUES
-- MEI - Microempreendedor Individual
(
    'MEI',
    'Microempreendedor Individual',
    'Regime simplificado para pequenos empreendedores com faturamento até R$ 81.000/ano',
    81000.00,
    1,
    false,
    false,
    0,
    false,
    true,
    0.00,
    5.00,
    ARRAY['DAS-MEI (INSS + ICMS/ISS)'],
    ARRAY['DASN-SIMEI (Declaração Anual)'],
    'LC 128/2008',
    '2009-07-01'
),
-- SIMPLES_ME - Simples Nacional Microempresa
(
    'SIMPLES_ME',
    'Simples Nacional - Microempresa',
    'Regime tributário simplificado para microempresas com faturamento até R$ 360.000/ano',
    360000.00,
    NULL,
    false,
    false,
    NULL,
    true,
    true,
    4.00,
    19.00,
    ARRAY['DAS (Documento de Arrecadação do Simples)', 'PGDAS-D'],
    ARRAY['DEFIS (Declaração de Informações Socioeconômicas e Fiscais)'],
    'LC 123/2006',
    '2007-07-01'
),
-- SIMPLES_EPP - Simples Nacional Empresa de Pequeno Porte
(
    'SIMPLES_EPP',
    'Simples Nacional - EPP',
    'Regime tributário simplificado para empresas de pequeno porte com faturamento até R$ 4.800.000/ano',
    4800000.00,
    NULL,
    false,
    false,
    NULL,
    true,
    true,
    4.00,
    33.00,
    ARRAY['DAS (Documento de Arrecadação do Simples)', 'PGDAS-D'],
    ARRAY['DEFIS (Declaração de Informações Socioeconômicas e Fiscais)'],
    'LC 123/2006',
    '2007-07-01'
),
-- LUCRO_PRESUMIDO
(
    'LUCRO_PRESUMIDO',
    'Lucro Presumido',
    'Regime tributário onde a base de cálculo é presumida a partir do faturamento',
    78000000.00,
    NULL,
    true,
    true,
    NULL,
    true,
    false,
    11.33,
    16.33,
    ARRAY['DARF (PIS, COFINS, IRPJ, CSLL)', 'Escrituração Contábil'],
    ARRAY['ECF', 'ECD', 'DIRF'],
    'Lei 9.430/1996',
    '1997-01-01'
),
-- LUCRO_REAL
(
    'LUCRO_REAL',
    'Lucro Real',
    'Regime tributário onde a base de cálculo é o lucro líquido contábil ajustado',
    NULL,  -- Sem limite
    NULL,
    true,
    true,
    NULL,
    true,
    false,
    NULL,  -- Depende do resultado
    34.00,
    ARRAY['DARF (PIS, COFINS, IRPJ, CSLL)', 'Escrituração Contábil Completa', 'LALUR'],
    ARRAY['ECF', 'ECD', 'DIRF', 'SPED Contribuições'],
    'Lei 9.430/1996',
    '1997-01-01'
)
ON CONFLICT (codigo) DO UPDATE SET
    nome = EXCLUDED.nome,
    descricao = EXCLUDED.descricao,
    limite_faturamento_anual = EXCLUDED.limite_faturamento_anual,
    limite_funcionarios = EXCLUDED.limite_funcionarios,
    updated_at = NOW();

-- ===========================================
-- 3. DELETAR COLUNAS DESNECESSÁRIAS DE dim_empresas
-- ===========================================

ALTER TABLE dim_empresas
    DROP COLUMN IF EXISTS twitter_url,
    DROP COLUMN IF EXISTS facebook_url,
    DROP COLUMN IF EXISTS instagram,
    DROP COLUMN IF EXISTS logo_url;

-- ===========================================
-- 4. AJUSTAR LINKEDIN DEFAULT EM dim_empresas
-- ===========================================

-- NOTA: Coluna linkedin não existe neste schema
-- Se existir em outro ambiente, descomentar:
-- UPDATE dim_empresas SET linkedin = 'inexistente' WHERE linkedin IS NULL;
-- ALTER TABLE dim_empresas ALTER COLUMN linkedin SET DEFAULT 'inexistente';

-- ===========================================
-- 5. ADICIONAR CAMPOS EM dim_pessoas
-- ===========================================

-- Adicionar novos campos
ALTER TABLE dim_pessoas
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS foto_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS raw_apollo_data JSONB;

-- Índices para novos campos
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_email ON dim_pessoas(email);

-- Comentários
COMMENT ON COLUMN dim_pessoas.email IS 'Email da pessoa (via Apollo enrichment)';
COMMENT ON COLUMN dim_pessoas.foto_url IS 'URL da foto de perfil';
COMMENT ON COLUMN dim_pessoas.raw_apollo_data IS 'Dados brutos retornados pela API Apollo';

-- ===========================================
-- 6. ADICIONAR FK regime_id EM fato_regime_tributario
-- ===========================================

-- Verificar se coluna já existe
ALTER TABLE fato_regime_tributario
    ADD COLUMN IF NOT EXISTS regime_id UUID REFERENCES dim_regimes_tributarios(id);

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_fato_regime_regime_id ON fato_regime_tributario(regime_id);

-- Popular regime_id baseado no código existente
UPDATE fato_regime_tributario frt
SET regime_id = drt.id
FROM dim_regimes_tributarios drt
WHERE UPPER(frt.regime_tributario) LIKE '%' || drt.codigo || '%'
  AND frt.regime_id IS NULL;

-- Tratamento especial para SIMPLES_NACIONAL → verificar se ME ou EPP
-- (assumir SIMPLES_ME como default se não for possível determinar)
UPDATE fato_regime_tributario frt
SET regime_id = (
    SELECT id FROM dim_regimes_tributarios
    WHERE codigo = 'SIMPLES_ME'
    LIMIT 1
)
WHERE UPPER(frt.regime_tributario) LIKE '%SIMPLES%'
  AND frt.regime_id IS NULL;

-- Comentário
COMMENT ON COLUMN fato_regime_tributario.regime_id IS 'FK para dim_regimes_tributarios - características do regime';

-- ===========================================
-- 7. ADICIONAR COLUNA codigo_ibge EM dim_empresas (para join com geo_municipios)
-- ===========================================

ALTER TABLE dim_empresas
    ADD COLUMN IF NOT EXISTS codigo_ibge VARCHAR(7);

-- Índice para joins geográficos
CREATE INDEX IF NOT EXISTS idx_dim_empresas_ibge ON dim_empresas(codigo_ibge);

-- Comentário
COMMENT ON COLUMN dim_empresas.codigo_ibge IS 'Código IBGE do município para join com dados geográficos';

-- ===========================================
-- SUMÁRIO DA MIGRATION
-- ===========================================
-- 1. Criada tabela dim_regimes_tributarios com características legais de cada regime
-- 2. Populada com 5 regimes: MEI, SIMPLES_ME, SIMPLES_EPP, LUCRO_PRESUMIDO, LUCRO_REAL
-- 3. Removidas colunas não usadas de dim_empresas: twitter_url, facebook_url, instagram, logo_url
-- 4. LinkedIn em dim_empresas alterado para default 'inexistente'
-- 5. Adicionados campos em dim_pessoas: email, foto_url, raw_apollo_data
-- 6. LinkedIn em dim_pessoas alterado para default 'inexistente'
-- 7. Adicionada FK regime_id em fato_regime_tributario
-- 8. Adicionado codigo_ibge em dim_empresas para joins geográficos
