-- =============================================
-- Migration 010: Notícias e Tópicos
-- Data: 2026-02-16
-- Descrição: Schema para notícias econômicas com análise Claude
-- =============================================

-- ===========================================
-- DIMENSÃO: FONTES DE NOTÍCIAS (Twitter/X)
-- ===========================================

CREATE TABLE IF NOT EXISTS dim_fontes_noticias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identificação
    handle VARCHAR(100) UNIQUE NOT NULL,  -- @aosfatos, @agencialupa
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,  -- agencia_checagem, veiculo, jornalista, instituicao

    -- Categorias de cobertura
    categorias TEXT[] DEFAULT '{}',  -- economia, politica, tecnologia

    -- Credibilidade
    confiabilidade VARCHAR(20) DEFAULT 'alta',  -- alta, media, baixa
    verificado BOOLEAN DEFAULT false,
    membro_ifcn BOOLEAN DEFAULT false,  -- International Fact-Checking Network

    -- URLs
    twitter_url VARCHAR(500),
    website_url VARCHAR(500),

    -- Status
    ativo BOOLEAN DEFAULT true,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inserir fontes confiáveis iniciais
INSERT INTO dim_fontes_noticias (handle, nome, tipo, categorias, confiabilidade, verificado, membro_ifcn, twitter_url, website_url) VALUES
-- Agências de Checagem
('@aosfatos', 'Aos Fatos', 'agencia_checagem', ARRAY['politica', 'economia', 'saude'], 'alta', true, true, 'https://x.com/aosfatos', 'https://aosfatos.org'),
('@agencialupa', 'Agência Lupa', 'agencia_checagem', ARRAY['politica', 'economia', 'saude'], 'alta', true, true, 'https://x.com/agencialupa', 'https://lupa.uol.com.br'),
('@projetocomprova', 'Projeto Comprova', 'agencia_checagem', ARRAY['politica', 'economia'], 'alta', true, true, 'https://x.com/projetocomprova', 'https://projetocomprova.com.br'),
('@EstadaoVerifica', 'Estadão Verifica', 'agencia_checagem', ARRAY['politica', 'economia'], 'alta', true, false, 'https://x.com/EstadaoVerifica', 'https://estadao.com.br/estadao-verifica'),

-- Veículos Tradicionais
('@folha', 'Folha de S.Paulo', 'veiculo', ARRAY['politica', 'economia', 'internacional'], 'alta', true, false, 'https://x.com/folha', 'https://folha.uol.com.br'),
('@estadao', 'O Estado de S. Paulo', 'veiculo', ARRAY['politica', 'economia', 'internacional'], 'alta', true, false, 'https://x.com/estadao', 'https://estadao.com.br'),
('@gaborioGlobo', 'O Globo', 'veiculo', ARRAY['politica', 'economia', 'internacional'], 'alta', true, false, 'https://x.com/oglobo', 'https://oglobo.globo.com'),
('@valoreconomico', 'Valor Econômico', 'veiculo', ARRAY['economia', 'mercado', 'empresas'], 'alta', true, false, 'https://x.com/valoreconomico', 'https://valor.globo.com'),
('@InfoMoney', 'InfoMoney', 'veiculo', ARRAY['economia', 'investimentos', 'mercado'], 'alta', true, false, 'https://x.com/InfoMoney', 'https://infomoney.com.br'),
('@exaborioame', 'Exame', 'veiculo', ARRAY['economia', 'negocios', 'tecnologia'], 'alta', true, false, 'https://x.com/exaborioame', 'https://exame.com'),

-- Jornalistas Referência
('@marilizpj', 'Mariliz Pereira Jorge', 'jornalista', ARRAY['politica', 'economia'], 'alta', true, false, 'https://x.com/marilizpj', NULL),
('@juliaduailibi', 'Julia Duailibi', 'jornalista', ARRAY['politica', 'economia'], 'alta', true, false, 'https://x.com/juliaduailibi', NULL),
('@gugachacra', 'Guga Chacra', 'jornalista', ARRAY['internacional', 'economia'], 'alta', true, false, 'https://x.com/gugachacra', NULL),
('@arielpalacios', 'Ariel Palacios', 'jornalista', ARRAY['internacional', 'economia'], 'alta', true, false, 'https://x.com/arielpalacios', NULL)

ON CONFLICT (handle) DO NOTHING;

-- Índices
CREATE INDEX IF NOT EXISTS idx_fontes_noticias_tipo ON dim_fontes_noticias(tipo);
CREATE INDEX IF NOT EXISTS idx_fontes_noticias_confiabilidade ON dim_fontes_noticias(confiabilidade);
CREATE INDEX IF NOT EXISTS idx_fontes_noticias_ativo ON dim_fontes_noticias(ativo);

-- ===========================================
-- DIMENSÃO: NOTÍCIAS
-- ===========================================

CREATE TABLE IF NOT EXISTS dim_noticias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Conteúdo
    titulo TEXT NOT NULL,
    subtitulo TEXT,
    conteudo TEXT,
    resumo TEXT,  -- Gerado pelo Claude

    -- Fonte
    fonte_id UUID REFERENCES dim_fontes_noticias(id),
    fonte_nome VARCHAR(255),  -- Nome da fonte (backup se não houver cadastro)
    fonte_handle VARCHAR(100),  -- @handle do Twitter
    url TEXT,
    url_hash VARCHAR(64) UNIQUE,  -- SHA256 da URL para evitar duplicatas

    -- Classificação
    segmento VARCHAR(100),  -- tecnologia, varejo, industria, servicos
    categorias TEXT[] DEFAULT '{}',  -- Tags adicionais

    -- Temporal
    data_publicacao TIMESTAMPTZ,
    data_coleta TIMESTAMPTZ DEFAULT NOW(),

    -- Perplexity metadata
    perplexity_citations JSONB DEFAULT '[]',  -- Citações originais do Perplexity
    perplexity_query TEXT,  -- Query usada na busca

    -- Status
    processado_claude BOOLEAN DEFAULT false,
    relevancia_geral INT DEFAULT 0,  -- 0-100

    -- Dados brutos
    raw_perplexity JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_noticias_segmento ON dim_noticias(segmento);
CREATE INDEX IF NOT EXISTS idx_noticias_data_pub ON dim_noticias(data_publicacao DESC);
CREATE INDEX IF NOT EXISTS idx_noticias_fonte ON dim_noticias(fonte_id);
CREATE INDEX IF NOT EXISTS idx_noticias_processado ON dim_noticias(processado_claude);
CREATE INDEX IF NOT EXISTS idx_noticias_relevancia ON dim_noticias(relevancia_geral DESC);

-- ===========================================
-- FATO: TÓPICOS DE NOTÍCIAS (Análise Claude)
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_noticias_topicos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves
    noticia_id UUID NOT NULL REFERENCES dim_noticias(id) ON DELETE CASCADE,

    -- Tópico gerado pelo Claude
    topico VARCHAR(255) NOT NULL,
    topico_slug VARCHAR(100),  -- slug para agrupamento

    -- Relevância
    relevancia INT NOT NULL CHECK (relevancia BETWEEN 1 AND 10),  -- 1-10
    relevancia_segmento INT CHECK (relevancia_segmento BETWEEN 1 AND 10),  -- Relevância específica para o segmento

    -- Análise Claude
    analise_resumo TEXT,  -- Resumo do Claude sobre este tópico na notícia
    sentimento VARCHAR(20),  -- positivo, negativo, neutro
    impacto_mercado VARCHAR(20),  -- alto, medio, baixo

    -- Keywords extraídas
    keywords TEXT[] DEFAULT '{}',
    entidades TEXT[] DEFAULT '{}',  -- Empresas, pessoas, locais mencionados

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_topicos_noticia ON fato_noticias_topicos(noticia_id);
CREATE INDEX IF NOT EXISTS idx_topicos_topico ON fato_noticias_topicos(topico_slug);
CREATE INDEX IF NOT EXISTS idx_topicos_relevancia ON fato_noticias_topicos(relevancia DESC);
CREATE INDEX IF NOT EXISTS idx_topicos_sentimento ON fato_noticias_topicos(sentimento);

-- ===========================================
-- FATO: NOTÍCIAS x EMPRESAS (Relação)
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_noticias_empresas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves
    noticia_id UUID NOT NULL REFERENCES dim_noticias(id) ON DELETE CASCADE,
    empresa_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,

    -- Tipo de relação
    tipo_relacao VARCHAR(50) DEFAULT 'mencao',  -- mencao, protagonista, setor, concorrente

    -- Relevância para a empresa
    relevancia INT CHECK (relevancia BETWEEN 1 AND 10),

    -- Contexto da menção
    contexto TEXT,  -- Trecho onde a empresa é mencionada

    -- Sentimento específico para a empresa
    sentimento_empresa VARCHAR(20),  -- positivo, negativo, neutro

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint única
    CONSTRAINT uk_noticia_empresa UNIQUE(noticia_id, empresa_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_not_emp_noticia ON fato_noticias_empresas(noticia_id);
CREATE INDEX IF NOT EXISTS idx_not_emp_empresa ON fato_noticias_empresas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_not_emp_relevancia ON fato_noticias_empresas(relevancia DESC);

-- ===========================================
-- FATO: NOTÍCIAS x PESSOAS (Relação)
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_noticias_pessoas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves
    noticia_id UUID NOT NULL REFERENCES dim_noticias(id) ON DELETE CASCADE,
    pessoa_id UUID NOT NULL REFERENCES dim_pessoas(id) ON DELETE CASCADE,

    -- Tipo de relação
    tipo_relacao VARCHAR(50) DEFAULT 'mencao',  -- mencao, autor, entrevistado, protagonista

    -- Contexto
    contexto TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint única
    CONSTRAINT uk_noticia_pessoa UNIQUE(noticia_id, pessoa_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_not_pes_noticia ON fato_noticias_pessoas(noticia_id);
CREATE INDEX IF NOT EXISTS idx_not_pes_pessoa ON fato_noticias_pessoas(pessoa_id);

-- ===========================================
-- VIEW: Notícias com Tópicos Agregados
-- ===========================================

CREATE OR REPLACE VIEW vw_noticias_completas AS
SELECT
    n.id,
    n.titulo,
    n.resumo,
    n.fonte_nome,
    n.url,
    n.segmento,
    n.data_publicacao,
    n.relevancia_geral,
    COALESCE(
        json_agg(
            json_build_object(
                'topico', t.topico,
                'relevancia', t.relevancia,
                'sentimento', t.sentimento
            )
        ) FILTER (WHERE t.id IS NOT NULL),
        '[]'::json
    ) as topicos,
    COUNT(DISTINCT e.empresa_id) as empresas_relacionadas,
    COUNT(DISTINCT p.pessoa_id) as pessoas_relacionadas
FROM dim_noticias n
LEFT JOIN fato_noticias_topicos t ON t.noticia_id = n.id
LEFT JOIN fato_noticias_empresas e ON e.noticia_id = n.id
LEFT JOIN fato_noticias_pessoas p ON p.noticia_id = n.id
GROUP BY n.id;

-- ===========================================
-- Registrar fontes de dados (compliance)
-- ===========================================

INSERT INTO fontes_dados (
    nome,
    categoria,
    fonte_primaria,
    url,
    confiabilidade,
    api_key_necessaria,
    periodicidade,
    formato,
    documentacao_url
) VALUES
(
    'Perplexity AI - Notícias',
    'ia',
    'Perplexity AI',
    'https://api.perplexity.ai',
    'alta',
    true,
    'tempo_real',
    'JSON',
    'https://docs.perplexity.ai'
),
(
    'Twitter/X - Perfis Jornalísticos',
    'rede_social',
    'Twitter/X',
    'https://x.com',
    'media',
    false,
    'tempo_real',
    'JSON',
    'https://developer.x.com'
)
ON CONFLICT (nome) DO NOTHING;

-- ===========================================
-- Comentários nas tabelas
-- ===========================================

COMMENT ON TABLE dim_fontes_noticias IS 'Fontes confiáveis de notícias (Twitter, veículos, jornalistas)';
COMMENT ON TABLE dim_noticias IS 'Notícias econômicas coletadas via Perplexity + Twitter';
COMMENT ON TABLE fato_noticias_topicos IS 'Tópicos extraídos pelo Claude com análise de relevância';
COMMENT ON TABLE fato_noticias_empresas IS 'Relação entre notícias e empresas (menções, setor)';
COMMENT ON TABLE fato_noticias_pessoas IS 'Relação entre notícias e pessoas (menções, autoria)';
