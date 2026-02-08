-- ===========================================
-- Scraping Hub - Star Schema
-- Modelo Dimensional para Empresas e Pessoas
-- ===========================================

-- Extensao para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- DIMENSAO: EMPRESAS
-- ===========================================

CREATE TABLE IF NOT EXISTS dim_empresas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identificacao
    cnpj VARCHAR(18) UNIQUE,
    cnae_principal VARCHAR(10),
    cnae_descricao VARCHAR(255),

    -- Nomes
    razao_social VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),

    -- Endereco
    logradouro VARCHAR(255),
    numero VARCHAR(20),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    cep VARCHAR(10),
    endereco_completo TEXT GENERATED ALWAYS AS (
        COALESCE(logradouro, '') ||
        COALESCE(', ' || numero, '') ||
        COALESCE(' - ' || complemento, '') ||
        COALESCE(', ' || bairro, '') ||
        COALESCE(' - ' || cidade, '') ||
        COALESCE('/' || estado, '') ||
        COALESCE(' - CEP: ' || cep, '')
    ) STORED,

    -- Fundadores
    fundadores JSONB DEFAULT '[]',  -- [{nome, cargo, linkedin_url}]

    -- Informacoes adicionais
    website VARCHAR(500),
    linkedin_url VARCHAR(500),
    telefone VARCHAR(50),
    email VARCHAR(255),

    -- Classificacao
    porte VARCHAR(50),  -- MEI, ME, EPP, MEDIO, GRANDE
    natureza_juridica VARCHAR(100),
    situacao_cadastral VARCHAR(50),
    data_abertura DATE,
    capital_social DECIMAL(15,2),

    -- Setor
    setor VARCHAR(100),
    subsetor VARCHAR(100),
    segmento VARCHAR(100),

    -- Metricas
    qtd_funcionarios INT,
    faixa_faturamento VARCHAR(100),

    -- Dados brutos
    raw_cnpj_data JSONB DEFAULT '{}',
    raw_search_data JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_dim_empresas_cnpj ON dim_empresas(cnpj);
CREATE INDEX IF NOT EXISTS idx_dim_empresas_nome ON dim_empresas(nome_fantasia);
CREATE INDEX IF NOT EXISTS idx_dim_empresas_cnae ON dim_empresas(cnae_principal);
CREATE INDEX IF NOT EXISTS idx_dim_empresas_cidade ON dim_empresas(cidade, estado);
CREATE INDEX IF NOT EXISTS idx_dim_empresas_setor ON dim_empresas(setor);

-- ===========================================
-- DIMENSAO: PESSOAS
-- ===========================================

CREATE TABLE IF NOT EXISTS dim_pessoas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identificacao
    nome_completo VARCHAR(255) NOT NULL,
    primeiro_nome VARCHAR(100),
    sobrenome VARCHAR(100),

    -- Contato
    email VARCHAR(255),
    telefone VARCHAR(50),

    -- Redes sociais
    linkedin_url VARCHAR(500) UNIQUE,
    linkedin_id VARCHAR(100),
    twitter_url VARCHAR(500),
    github_url VARCHAR(500),

    -- Foto
    foto_url VARCHAR(500),

    -- Localizacao
    cidade VARCHAR(100),
    estado VARCHAR(2),
    pais VARCHAR(50) DEFAULT 'Brasil',

    -- Profissional atual
    cargo_atual VARCHAR(255),
    empresa_atual_id UUID REFERENCES dim_empresas(id),
    empresa_atual_nome VARCHAR(255),
    senioridade VARCHAR(50),  -- junior, pleno, senior, lead, manager, director, c-level
    departamento VARCHAR(100),

    -- Formacao
    formacao_principal VARCHAR(255),
    instituicao_principal VARCHAR(255),
    ano_formatura INT,

    -- Skills (agregado)
    skills JSONB DEFAULT '[]',
    linguas JSONB DEFAULT '[]',
    certificacoes JSONB DEFAULT '[]',

    -- Resumo
    headline VARCHAR(500),
    sobre TEXT,

    -- Metricas LinkedIn
    conexoes INT,
    seguidores INT,

    -- Dados brutos
    raw_apollo_data JSONB DEFAULT '{}',
    raw_linkedin_data JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_nome ON dim_pessoas(nome_completo);
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_linkedin ON dim_pessoas(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_empresa ON dim_pessoas(empresa_atual_id);
CREATE INDEX IF NOT EXISTS idx_dim_pessoas_cargo ON dim_pessoas(cargo_atual);

-- ===========================================
-- FATO: ANALISES DE EMPRESA
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_analises_empresa (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves
    empresa_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,

    -- Metadados
    data_analise TIMESTAMPTZ DEFAULT NOW(),
    tipo_analise VARCHAR(50) DEFAULT 'completa',  -- completa, rapida, concorrente
    versao_modelo VARCHAR(50),
    tempo_processamento_segundos FLOAT,

    -- Os 11 Blocos (markdown)
    bloco_1_empresa TEXT,
    bloco_2_pessoas TEXT,
    bloco_3_formacao TEXT,
    bloco_4_ativo_humano TEXT,
    bloco_5_capacidade TEXT,
    bloco_6_comunicacao TEXT,
    bloco_7_fraquezas TEXT,
    bloco_8_visao_leigo TEXT,
    bloco_9_visao_profissional TEXT,
    bloco_10_visao_concorrente TEXT,
    bloco_11_visao_fornecedor TEXT,

    -- Sintese
    hipotese_objetivo TEXT,
    okrs_sugeridos JSONB DEFAULT '[]',

    -- SWOT
    swot_forcas JSONB DEFAULT '[]',
    swot_fraquezas JSONB DEFAULT '[]',
    swot_oportunidades JSONB DEFAULT '[]',
    swot_ameacas JSONB DEFAULT '[]',
    tows_estrategias JSONB DEFAULT '{}',

    -- Palavras-chave extraidas (para busca de concorrentes)
    palavras_chave JSONB DEFAULT '[]',
    palavras_chave_por_bloco JSONB DEFAULT '{}',

    -- Qualidade
    score_qualidade FLOAT,
    fontes_utilizadas JSONB DEFAULT '[]',

    -- Dados brutos
    raw_perplexity JSONB DEFAULT '{}',
    raw_tavily JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_fato_analises_empresa ON fato_analises_empresa(empresa_id);
CREATE INDEX IF NOT EXISTS idx_fato_analises_data ON fato_analises_empresa(data_analise DESC);
CREATE INDEX IF NOT EXISTS idx_fato_analises_tipo ON fato_analises_empresa(tipo_analise);

-- ===========================================
-- FATO: EVENTOS DE PESSOA (Portfolio)
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_eventos_pessoa (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves
    pessoa_id UUID NOT NULL REFERENCES dim_pessoas(id) ON DELETE CASCADE,
    empresa_id UUID REFERENCES dim_empresas(id),

    -- Tipo de evento
    tipo_evento VARCHAR(50) NOT NULL,  -- emprego, educacao, certificacao, projeto, publicacao, premio

    -- Periodo
    data_inicio DATE,
    data_fim DATE,
    atual BOOLEAN DEFAULT FALSE,
    duracao_meses INT,

    -- Detalhes
    titulo VARCHAR(255),  -- Cargo ou Curso
    instituicao VARCHAR(255),  -- Empresa ou Universidade
    local VARCHAR(255),
    descricao TEXT,

    -- Para empregos
    departamento VARCHAR(100),
    senioridade VARCHAR(50),

    -- Para educacao
    grau VARCHAR(50),  -- graduacao, pos, mba, mestrado, doutorado
    area_estudo VARCHAR(255),

    -- Para certificacoes
    emissor VARCHAR(255),
    credencial_id VARCHAR(100),
    url_credencial VARCHAR(500),
    validade DATE,

    -- Skills relacionadas
    skills_utilizadas JSONB DEFAULT '[]',

    -- Dados brutos
    raw_data JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_fato_eventos_pessoa ON fato_eventos_pessoa(pessoa_id);
CREATE INDEX IF NOT EXISTS idx_fato_eventos_empresa ON fato_eventos_pessoa(empresa_id);
CREATE INDEX IF NOT EXISTS idx_fato_eventos_tipo ON fato_eventos_pessoa(tipo_evento);
CREATE INDEX IF NOT EXISTS idx_fato_eventos_periodo ON fato_eventos_pessoa(data_inicio DESC);

-- ===========================================
-- FATO: CONCORRENTES
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_concorrentes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chaves
    empresa_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,
    concorrente_id UUID NOT NULL REFERENCES dim_empresas(id) ON DELETE CASCADE,

    -- Relacao
    tipo_concorrencia VARCHAR(50) DEFAULT 'direto',  -- direto, indireto, substituto, potencial

    -- Match de palavras-chave
    palavras_chave_match JSONB DEFAULT '[]',
    score_similaridade FLOAT,

    -- Avaliacao (Stamp)
    stamp VARCHAR(20),  -- Forte, Medio, Fraco
    stamp_justificativa TEXT,

    -- Comparativo
    vantagens_empresa JSONB DEFAULT '[]',
    vantagens_concorrente JSONB DEFAULT '[]',
    areas_sobreposicao JSONB DEFAULT '[]',

    -- Fonte da descoberta
    fonte_descoberta VARCHAR(50),  -- perplexity, serper, manual
    query_utilizada TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Evitar duplicatas
    UNIQUE(empresa_id, concorrente_id)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_fato_concorrentes_empresa ON fato_concorrentes(empresa_id);
CREATE INDEX IF NOT EXISTS idx_fato_concorrentes_concorrente ON fato_concorrentes(concorrente_id);
CREATE INDEX IF NOT EXISTS idx_fato_concorrentes_stamp ON fato_concorrentes(stamp);

-- ===========================================
-- FATO: HISTORICO DE BUSCAS
-- ===========================================

CREATE TABLE IF NOT EXISTS fato_buscas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Usuario
    user_id UUID,
    user_email VARCHAR(255),

    -- Busca
    tipo_busca VARCHAR(50) NOT NULL,  -- empresa, pessoa, concorrente
    termo_busca VARCHAR(255),
    filtros JSONB DEFAULT '{}',

    -- Resultado
    empresa_id UUID REFERENCES dim_empresas(id),
    pessoa_id UUID REFERENCES dim_pessoas(id),

    -- Metricas
    tempo_processamento_ms INT,
    apis_chamadas JSONB DEFAULT '[]',
    custo_estimado DECIMAL(10,4),

    -- Status
    status VARCHAR(20) DEFAULT 'completed',  -- pending, processing, completed, failed
    erro TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_fato_buscas_user ON fato_buscas(user_email);
CREATE INDEX IF NOT EXISTS idx_fato_buscas_tipo ON fato_buscas(tipo_busca);
CREATE INDEX IF NOT EXISTS idx_fato_buscas_data ON fato_buscas(created_at DESC);

-- ===========================================
-- TRIGGERS
-- ===========================================

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION trigger_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers
DROP TRIGGER IF EXISTS trg_dim_empresas_updated ON dim_empresas;
CREATE TRIGGER trg_dim_empresas_updated
    BEFORE UPDATE ON dim_empresas
    FOR EACH ROW EXECUTE FUNCTION trigger_updated_at();

DROP TRIGGER IF EXISTS trg_dim_pessoas_updated ON dim_pessoas;
CREATE TRIGGER trg_dim_pessoas_updated
    BEFORE UPDATE ON dim_pessoas
    FOR EACH ROW EXECUTE FUNCTION trigger_updated_at();

DROP TRIGGER IF EXISTS trg_fato_concorrentes_updated ON fato_concorrentes;
CREATE TRIGGER trg_fato_concorrentes_updated
    BEFORE UPDATE ON fato_concorrentes
    FOR EACH ROW EXECUTE FUNCTION trigger_updated_at();

-- ===========================================
-- VIEWS UTEIS
-- ===========================================

-- Empresas com ultima analise
CREATE OR REPLACE VIEW v_empresas_analises AS
SELECT
    e.*,
    a.data_analise,
    a.score_qualidade,
    a.palavras_chave,
    (SELECT COUNT(*) FROM fato_concorrentes WHERE empresa_id = e.id) as qtd_concorrentes,
    (SELECT COUNT(*) FROM dim_pessoas WHERE empresa_atual_id = e.id) as qtd_funcionarios_mapeados
FROM dim_empresas e
LEFT JOIN LATERAL (
    SELECT * FROM fato_analises_empresa
    WHERE empresa_id = e.id
    ORDER BY data_analise DESC
    LIMIT 1
) a ON true;

-- Pessoas com historico resumido
CREATE OR REPLACE VIEW v_pessoas_portfolio AS
SELECT
    p.*,
    (SELECT COUNT(*) FROM fato_eventos_pessoa WHERE pessoa_id = p.id AND tipo_evento = 'emprego') as qtd_empregos,
    (SELECT COUNT(*) FROM fato_eventos_pessoa WHERE pessoa_id = p.id AND tipo_evento = 'educacao') as qtd_formacoes,
    (SELECT COUNT(*) FROM fato_eventos_pessoa WHERE pessoa_id = p.id AND tipo_evento = 'certificacao') as qtd_certificacoes
FROM dim_pessoas p;

-- Concorrentes com detalhes
CREATE OR REPLACE VIEW v_concorrentes_detalhes AS
SELECT
    fc.*,
    e1.nome_fantasia as empresa_nome,
    e1.setor as empresa_setor,
    e2.nome_fantasia as concorrente_nome,
    e2.setor as concorrente_setor
FROM fato_concorrentes fc
JOIN dim_empresas e1 ON fc.empresa_id = e1.id
JOIN dim_empresas e2 ON fc.concorrente_id = e2.id;

-- ===========================================
-- COMENTARIOS
-- ===========================================

COMMENT ON TABLE dim_empresas IS 'Dimensao de empresas com dados cadastrais, CNPJ, CNAE, endereco e fundadores';
COMMENT ON TABLE dim_pessoas IS 'Dimensao de pessoas com dados profissionais e de contato';
COMMENT ON TABLE fato_analises_empresa IS 'Fato com os 11 blocos de analise, SWOT e palavras-chave';
COMMENT ON TABLE fato_eventos_pessoa IS 'Fato com portfolio: empregos, formacao, certificacoes';
COMMENT ON TABLE fato_concorrentes IS 'Fato de relacao entre empresas concorrentes com stamps';
COMMENT ON TABLE fato_buscas IS 'Historico de buscas realizadas no sistema';
