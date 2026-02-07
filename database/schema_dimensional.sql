-- ===========================================
-- Scraping Hub v2.0 - Dimensional Schema
-- Data Warehouse para Analytics
-- Star Schema para Business Intelligence
-- ===========================================

-- Extensao para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- TABELAS DIMENSAO
-- ===========================================

-- -------------------------------------------
-- 1. dim_date - Dimensao de Data
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id INT PRIMARY KEY,  -- YYYYMMDD format
    full_date DATE NOT NULL UNIQUE,
    year SMALLINT NOT NULL,
    quarter SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    week SMALLINT NOT NULL,
    day_of_month SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,  -- 1=Sunday, 7=Saturday
    day_name VARCHAR(15) NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    fiscal_year SMALLINT,
    fiscal_quarter SMALLINT
);

CREATE INDEX IF NOT EXISTS idx_dim_date_full ON dim_date(full_date);
CREATE INDEX IF NOT EXISTS idx_dim_date_year_month ON dim_date(year, month);

-- -------------------------------------------
-- 2. dim_time - Dimensao de Tempo
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_time (
    time_id INT PRIMARY KEY,  -- HHMM format (0000-2359)
    hour SMALLINT NOT NULL,
    minute SMALLINT NOT NULL,
    period VARCHAR(20) NOT NULL,  -- 'madrugada', 'manha', 'tarde', 'noite'
    period_en VARCHAR(20) NOT NULL,  -- 'dawn', 'morning', 'afternoon', 'evening'
    is_business_hours BOOLEAN NOT NULL,  -- 9:00-18:00
    hour_12 SMALLINT NOT NULL,
    am_pm VARCHAR(2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_time_hour ON dim_time(hour);
CREATE INDEX IF NOT EXISTS idx_dim_time_period ON dim_time(period);

-- -------------------------------------------
-- 3. dim_company - Dimensao de Empresas (SCD Type 2)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_company (
    company_sk UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL,  -- Natural key (ref: companies.id)
    cnpj VARCHAR(14),
    razao_social VARCHAR(255),
    nome_fantasia VARCHAR(255),
    industry VARCHAR(100),
    size VARCHAR(50),
    state VARCHAR(2),
    city VARCHAR(100),
    employee_count_range VARCHAR(50),
    revenue_range VARCHAR(100),
    website VARCHAR(500),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP WITH TIME ZONE DEFAULT '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_dim_company_id ON dim_company(company_id);
CREATE INDEX IF NOT EXISTS idx_dim_company_cnpj ON dim_company(cnpj);
CREATE INDEX IF NOT EXISTS idx_dim_company_current ON dim_company(is_current) WHERE is_current = TRUE;

-- -------------------------------------------
-- 4. dim_person - Dimensao de Pessoas (SCD Type 2)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_person (
    person_sk UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL,  -- Natural key (ref: people.id)
    full_name VARCHAR(255) NOT NULL,
    person_type VARCHAR(50) NOT NULL,  -- 'professional', 'politician', 'executive'
    current_title VARCHAR(255),
    current_company VARCHAR(255),
    seniority VARCHAR(50),
    state VARCHAR(2),
    city VARCHAR(100),
    political_party VARCHAR(50),
    political_role VARCHAR(100),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP WITH TIME ZONE DEFAULT '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_dim_person_id ON dim_person(person_id);
CREATE INDEX IF NOT EXISTS idx_dim_person_type ON dim_person(person_type);
CREATE INDEX IF NOT EXISTS idx_dim_person_current ON dim_person(is_current) WHERE is_current = TRUE;

-- -------------------------------------------
-- 5. dim_municipality - Dimensao de Municipios
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_municipality (
    municipality_sk UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ibge_code VARCHAR(7) UNIQUE NOT NULL,
    city_name VARCHAR(100) NOT NULL,
    state_code VARCHAR(2) NOT NULL,
    state_name VARCHAR(50) NOT NULL,
    region VARCHAR(20) NOT NULL,  -- Norte, Nordeste, Sul, Sudeste, Centro-Oeste
    mesoregion VARCHAR(100),
    microregion VARCHAR(100),
    population_range VARCHAR(50),
    pib_range VARCHAR(50),
    idhm_range VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_dim_municipality_ibge ON dim_municipality(ibge_code);
CREATE INDEX IF NOT EXISTS idx_dim_municipality_state ON dim_municipality(state_code);

-- -------------------------------------------
-- 6. dim_data_source - Dimensao de Fontes de Dados
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_data_source (
    source_sk UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_code VARCHAR(50) UNIQUE NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'search', 'social', 'fiscal', 'news', 'ai'
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    cost_per_call DECIMAL(10, 4) DEFAULT 0,
    rate_limit_per_minute INT,
    rate_limit_per_day INT,
    reliability_score DECIMAL(3, 2) DEFAULT 0.80,  -- 0.00 to 1.00
    api_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_source_code ON dim_data_source(source_code);
CREATE INDEX IF NOT EXISTS idx_dim_source_type ON dim_data_source(source_type);

-- -------------------------------------------
-- 7. dim_user - Dimensao de Usuarios (SCD Type 2)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS dim_user (
    user_sk UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,  -- Natural key if available
    user_email VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) NOT NULL DEFAULT 'free',
    first_access_date DATE,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP WITH TIME ZONE DEFAULT '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_dim_user_email ON dim_user(user_email);
CREATE INDEX IF NOT EXISTS idx_dim_user_current ON dim_user(is_current) WHERE is_current = TRUE;


-- ===========================================
-- TABELAS FATO
-- ===========================================

-- -------------------------------------------
-- 1. fact_search - Pesquisas realizadas
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS fact_search (
    search_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    user_sk UUID REFERENCES dim_user(user_sk),

    -- Atributos da pesquisa
    search_type VARCHAR(50) NOT NULL,  -- 'company', 'person', 'politician', 'news', 'indicator'
    query_text TEXT,
    query_params JSONB DEFAULT '{}',

    -- Metricas
    results_count INT DEFAULT 0,
    processing_time_ms INT DEFAULT 0,
    credits_used INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'completed',  -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_search_date ON fact_search(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_search_user ON fact_search(user_sk);
CREATE INDEX IF NOT EXISTS idx_fact_search_type ON fact_search(search_type);
CREATE INDEX IF NOT EXISTS idx_fact_search_created ON fact_search(created_at DESC);

-- -------------------------------------------
-- 2. fact_company_analysis - Analises de empresas
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS fact_company_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    user_sk UUID REFERENCES dim_user(user_sk),
    company_sk UUID REFERENCES dim_company(company_sk),

    -- Tipo de analise
    analysis_type VARCHAR(50) NOT NULL,  -- 'client', 'competitor', 'prospect'

    -- Metricas de qualidade de dados
    sources_attempted INT DEFAULT 0,
    sources_succeeded INT DEFAULT 0,
    sources_failed INT DEFAULT 0,
    completeness_score DECIMAL(5, 2) DEFAULT 0,  -- 0-100%
    confidence_score DECIMAL(5, 2) DEFAULT 0,  -- 0-100%

    -- Performance
    processing_time_ms INT DEFAULT 0,
    ai_tokens_used INT DEFAULT 0,

    -- Flags de dados disponiveis
    has_website_data BOOLEAN DEFAULT FALSE,
    has_linkedin_data BOOLEAN DEFAULT FALSE,
    has_news_data BOOLEAN DEFAULT FALSE,
    has_financial_data BOOLEAN DEFAULT FALSE,
    has_cnpj_data BOOLEAN DEFAULT FALSE,

    -- Resultados
    has_swot BOOLEAN DEFAULT FALSE,
    has_okrs BOOLEAN DEFAULT FALSE,
    has_competitors BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_company_analysis_date ON fact_company_analysis(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_company_analysis_company ON fact_company_analysis(company_sk);
CREATE INDEX IF NOT EXISTS idx_fact_company_analysis_type ON fact_company_analysis(analysis_type);

-- -------------------------------------------
-- 3. fact_person_analysis - Analises de pessoas
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS fact_person_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    user_sk UUID REFERENCES dim_user(user_sk),
    person_sk UUID REFERENCES dim_person(person_sk),

    -- Tipo
    person_type VARCHAR(50) NOT NULL,  -- 'professional', 'politician'
    analysis_type VARCHAR(50) DEFAULT 'profile',  -- 'profile', 'fit', 'background'

    -- Metricas de qualidade
    sources_attempted INT DEFAULT 0,
    sources_succeeded INT DEFAULT 0,
    sources_failed INT DEFAULT 0,
    completeness_score DECIMAL(5, 2) DEFAULT 0,
    confidence_score DECIMAL(5, 2) DEFAULT 0,

    -- Performance
    processing_time_ms INT DEFAULT 0,
    ai_tokens_used INT DEFAULT 0,

    -- Flags de dados disponiveis
    has_linkedin_data BOOLEAN DEFAULT FALSE,
    has_social_data BOOLEAN DEFAULT FALSE,
    has_news_data BOOLEAN DEFAULT FALSE,
    has_photo BOOLEAN DEFAULT FALSE,

    -- Para politicos
    has_voting_history BOOLEAN DEFAULT FALSE,
    has_controversies BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_person_analysis_date ON fact_person_analysis(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_person_analysis_person ON fact_person_analysis(person_sk);
CREATE INDEX IF NOT EXISTS idx_fact_person_analysis_type ON fact_person_analysis(person_type);

-- -------------------------------------------
-- 4. fact_news - Noticias analisadas
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS fact_news (
    news_fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    user_sk UUID REFERENCES dim_user(user_sk),
    source_sk UUID REFERENCES dim_data_source(source_sk),

    -- Parametros da busca
    query_text TEXT,
    query_params JSONB DEFAULT '{}',

    -- Resultados
    results_count INT DEFAULT 0,
    relevant_count INT DEFAULT 0,

    -- Sentimento agregado
    avg_sentiment_score DECIMAL(5, 2),  -- -1.00 a 1.00
    positive_count INT DEFAULT 0,
    negative_count INT DEFAULT 0,
    neutral_count INT DEFAULT 0,

    -- Performance
    processing_time_ms INT DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_news_date ON fact_news(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_news_source ON fact_news(source_sk);

-- -------------------------------------------
-- 5. fact_indicator_query - Consultas de indicadores
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS fact_indicator_query (
    indicator_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    user_sk UUID REFERENCES dim_user(user_sk),
    municipality_sk UUID REFERENCES dim_municipality(municipality_sk),

    -- Tipo de indicador
    indicator_type VARCHAR(50) NOT NULL,  -- 'pib', 'idhm', 'population', 'fiscal', 'education', 'health'
    indicator_subtype VARCHAR(100),

    -- Resultados
    data_found BOOLEAN DEFAULT FALSE,
    data_freshness_days INT,  -- dias desde ultima atualizacao dos dados
    data_year INT,  -- ano de referencia dos dados

    -- Performance
    processing_time_ms INT DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_indicator_date ON fact_indicator_query(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_indicator_municipality ON fact_indicator_query(municipality_sk);
CREATE INDEX IF NOT EXISTS idx_fact_indicator_type ON fact_indicator_query(indicator_type);

-- -------------------------------------------
-- 6. fact_api_call - Chamadas a APIs externas
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS fact_api_call (
    call_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_id INT NOT NULL REFERENCES dim_date(date_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    source_sk UUID NOT NULL REFERENCES dim_data_source(source_sk),

    -- Detalhes da chamada
    endpoint VARCHAR(500),
    http_method VARCHAR(10) DEFAULT 'GET',
    http_status INT,

    -- Performance
    response_time_ms INT DEFAULT 0,
    response_size_bytes INT DEFAULT 0,

    -- Cache
    is_cached BOOLEAN DEFAULT FALSE,
    cache_hit BOOLEAN DEFAULT FALSE,

    -- Erros
    is_error BOOLEAN DEFAULT FALSE,
    error_type VARCHAR(50),
    error_message TEXT,

    -- Custo
    cost_incurred DECIMAL(10, 4) DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_api_call_date ON fact_api_call(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_api_call_source ON fact_api_call(source_sk);
CREATE INDEX IF NOT EXISTS idx_fact_api_call_status ON fact_api_call(http_status);
CREATE INDEX IF NOT EXISTS idx_fact_api_call_error ON fact_api_call(is_error) WHERE is_error = TRUE;


-- ===========================================
-- VIEWS PARA ANALYTICS
-- ===========================================

-- View de pesquisas por dia
CREATE OR REPLACE VIEW v_searches_daily AS
SELECT
    d.full_date,
    d.day_name,
    fs.search_type,
    COUNT(*) as total_searches,
    SUM(fs.results_count) as total_results,
    AVG(fs.processing_time_ms) as avg_processing_time_ms,
    SUM(fs.credits_used) as total_credits_used,
    SUM(CASE WHEN fs.status = 'completed' THEN 1 ELSE 0 END) as successful_searches,
    SUM(CASE WHEN fs.status = 'failed' THEN 1 ELSE 0 END) as failed_searches
FROM fact_search fs
JOIN dim_date d ON fs.date_id = d.date_id
GROUP BY d.full_date, d.day_name, fs.search_type
ORDER BY d.full_date DESC;

-- View de qualidade de dados por fonte
CREATE OR REPLACE VIEW v_source_quality AS
SELECT
    ds.source_name,
    ds.source_type,
    COUNT(*) as total_calls,
    AVG(CASE WHEN fa.is_error THEN 0 ELSE 1 END) * 100 as success_rate,
    AVG(fa.response_time_ms) as avg_response_time_ms,
    SUM(fa.cost_incurred) as total_cost,
    AVG(CASE WHEN fa.cache_hit THEN 1 ELSE 0 END) * 100 as cache_hit_rate
FROM fact_api_call fa
JOIN dim_data_source ds ON fa.source_sk = ds.source_sk
GROUP BY ds.source_name, ds.source_type
ORDER BY total_calls DESC;

-- View de analises de empresas
CREATE OR REPLACE VIEW v_company_analysis_summary AS
SELECT
    d.full_date,
    fca.analysis_type,
    COUNT(*) as total_analyses,
    AVG(fca.completeness_score) as avg_completeness,
    AVG(fca.confidence_score) as avg_confidence,
    AVG(fca.processing_time_ms) as avg_processing_time_ms,
    SUM(fca.ai_tokens_used) as total_tokens_used,
    SUM(CASE WHEN fca.has_swot THEN 1 ELSE 0 END) as with_swot,
    SUM(CASE WHEN fca.has_okrs THEN 1 ELSE 0 END) as with_okrs
FROM fact_company_analysis fca
JOIN dim_date d ON fca.date_id = d.date_id
GROUP BY d.full_date, fca.analysis_type
ORDER BY d.full_date DESC;

-- View de uso por usuario
CREATE OR REPLACE VIEW v_user_usage AS
SELECT
    du.user_email,
    du.plan_type,
    COUNT(DISTINCT fs.search_id) as total_searches,
    SUM(fs.credits_used) as total_credits_used,
    COUNT(DISTINCT fca.analysis_id) as company_analyses,
    COUNT(DISTINCT fpa.analysis_id) as person_analyses
FROM dim_user du
LEFT JOIN fact_search fs ON du.user_sk = fs.user_sk
LEFT JOIN fact_company_analysis fca ON du.user_sk = fca.user_sk
LEFT JOIN fact_person_analysis fpa ON du.user_sk = fpa.user_sk
WHERE du.is_current = TRUE
GROUP BY du.user_email, du.plan_type
ORDER BY total_searches DESC;


-- ===========================================
-- FUNCOES PARA ETL
-- ===========================================

-- Funcao para obter date_id a partir de timestamp
CREATE OR REPLACE FUNCTION get_date_id(ts TIMESTAMP WITH TIME ZONE)
RETURNS INT AS $$
BEGIN
    RETURN CAST(TO_CHAR(ts, 'YYYYMMDD') AS INT);
END;
$$ LANGUAGE plpgsql;

-- Funcao para obter time_id a partir de timestamp
CREATE OR REPLACE FUNCTION get_time_id(ts TIMESTAMP WITH TIME ZONE)
RETURNS INT AS $$
BEGIN
    RETURN CAST(TO_CHAR(ts, 'HH24MI') AS INT);
END;
$$ LANGUAGE plpgsql;

-- Funcao para garantir que user existe na dimensao
CREATE OR REPLACE FUNCTION ensure_dim_user(p_email VARCHAR(255), p_plan VARCHAR(50) DEFAULT 'free')
RETURNS UUID AS $$
DECLARE
    v_user_sk UUID;
BEGIN
    -- Busca usuario atual
    SELECT user_sk INTO v_user_sk
    FROM dim_user
    WHERE user_email = p_email AND is_current = TRUE;

    -- Se nao existe, cria
    IF v_user_sk IS NULL THEN
        INSERT INTO dim_user (user_email, plan_type, first_access_date)
        VALUES (p_email, p_plan, CURRENT_DATE)
        RETURNING user_sk INTO v_user_sk;
    END IF;

    RETURN v_user_sk;
END;
$$ LANGUAGE plpgsql;

-- Funcao para garantir que company existe na dimensao
CREATE OR REPLACE FUNCTION ensure_dim_company(p_company_id UUID)
RETURNS UUID AS $$
DECLARE
    v_company_sk UUID;
BEGIN
    -- Busca empresa atual
    SELECT company_sk INTO v_company_sk
    FROM dim_company
    WHERE company_id = p_company_id AND is_current = TRUE;

    -- Se nao existe, cria a partir da tabela companies
    IF v_company_sk IS NULL THEN
        INSERT INTO dim_company (
            company_id, cnpj, razao_social, nome_fantasia,
            industry, size, state, city, revenue_range, website
        )
        SELECT
            c.id, c.cnpj, c.razao_social, c.nome_fantasia,
            c.industry, c.size, c.state, c.city, c.revenue_range, c.website
        FROM companies c
        WHERE c.id = p_company_id
        RETURNING company_sk INTO v_company_sk;
    END IF;

    RETURN v_company_sk;
END;
$$ LANGUAGE plpgsql;

-- Funcao para garantir que person existe na dimensao
CREATE OR REPLACE FUNCTION ensure_dim_person(p_person_id UUID)
RETURNS UUID AS $$
DECLARE
    v_person_sk UUID;
BEGIN
    SELECT person_sk INTO v_person_sk
    FROM dim_person
    WHERE person_id = p_person_id AND is_current = TRUE;

    IF v_person_sk IS NULL THEN
        INSERT INTO dim_person (
            person_id, full_name, person_type, current_title,
            current_company, seniority, state, city,
            political_party, political_role
        )
        SELECT
            p.id, p.full_name, p.person_type, p.current_title,
            p.current_company, p.seniority, p.state, p.city,
            p.political_party, p.political_role
        FROM people p
        WHERE p.id = p_person_id
        RETURNING person_sk INTO v_person_sk;
    END IF;

    RETURN v_person_sk;
END;
$$ LANGUAGE plpgsql;


-- ===========================================
-- DADOS INICIAIS - DIMENSOES ESTATICAS
-- ===========================================

-- Popula dim_time (todas as horas e minutos)
INSERT INTO dim_time (time_id, hour, minute, period, period_en, is_business_hours, hour_12, am_pm)
SELECT
    h * 100 + m as time_id,
    h as hour,
    m as minute,
    CASE
        WHEN h >= 0 AND h < 6 THEN 'madrugada'
        WHEN h >= 6 AND h < 12 THEN 'manha'
        WHEN h >= 12 AND h < 18 THEN 'tarde'
        ELSE 'noite'
    END as period,
    CASE
        WHEN h >= 0 AND h < 6 THEN 'dawn'
        WHEN h >= 6 AND h < 12 THEN 'morning'
        WHEN h >= 12 AND h < 18 THEN 'afternoon'
        ELSE 'evening'
    END as period_en,
    (h >= 9 AND h < 18) as is_business_hours,
    CASE WHEN h = 0 THEN 12 WHEN h > 12 THEN h - 12 ELSE h END as hour_12,
    CASE WHEN h < 12 THEN 'AM' ELSE 'PM' END as am_pm
FROM generate_series(0, 23) h
CROSS JOIN generate_series(0, 59) m
ON CONFLICT (time_id) DO NOTHING;

-- Popula dim_date (5 anos: 2023-2028)
INSERT INTO dim_date (
    date_id, full_date, year, quarter, month, week,
    day_of_month, day_of_week, day_name, month_name,
    is_weekend, fiscal_year, fiscal_quarter
)
SELECT
    CAST(TO_CHAR(d, 'YYYYMMDD') AS INT) as date_id,
    d as full_date,
    EXTRACT(YEAR FROM d) as year,
    EXTRACT(QUARTER FROM d) as quarter,
    EXTRACT(MONTH FROM d) as month,
    EXTRACT(WEEK FROM d) as week,
    EXTRACT(DAY FROM d) as day_of_month,
    EXTRACT(DOW FROM d) + 1 as day_of_week,
    TO_CHAR(d, 'Day') as day_name,
    TO_CHAR(d, 'Month') as month_name,
    EXTRACT(DOW FROM d) IN (0, 6) as is_weekend,
    EXTRACT(YEAR FROM d) as fiscal_year,
    EXTRACT(QUARTER FROM d) as fiscal_quarter
FROM generate_series('2023-01-01'::date, '2028-12-31'::date, '1 day'::interval) d
ON CONFLICT (date_id) DO NOTHING;

-- Popula dim_data_source (fontes conhecidas)
INSERT INTO dim_data_source (source_code, source_name, source_type, is_paid, cost_per_call, rate_limit_per_minute, reliability_score) VALUES
    ('serper', 'Serper.dev', 'search', TRUE, 0.001, 100, 0.95),
    ('tavily', 'Tavily AI Search', 'search', TRUE, 0.01, 60, 0.92),
    ('perplexity', 'Perplexity AI', 'ai', TRUE, 0.05, 20, 0.90),
    ('brasilapi', 'Brasil API', 'fiscal', FALSE, 0, 60, 0.98),
    ('apollo', 'Apollo.io', 'social', TRUE, 0.10, 30, 0.85),
    ('linkedin', 'LinkedIn', 'social', TRUE, 0.15, 20, 0.88),
    ('claude', 'Claude AI', 'ai', TRUE, 0.015, 50, 0.95),
    ('openai', 'OpenAI GPT', 'ai', TRUE, 0.02, 50, 0.93),
    ('newsapi', 'News API', 'news', TRUE, 0.005, 100, 0.90),
    ('ibge', 'IBGE API', 'fiscal', FALSE, 0, 100, 0.99),
    ('web_scraper', 'Web Scraper', 'search', FALSE, 0, 30, 0.75)
ON CONFLICT (source_code) DO NOTHING;


-- ===========================================
-- COMENTARIOS
-- ===========================================

COMMENT ON TABLE dim_date IS 'Dimensao de data para analytics - padrao data warehouse';
COMMENT ON TABLE dim_time IS 'Dimensao de tempo com periodos do dia';
COMMENT ON TABLE dim_company IS 'Dimensao de empresas com SCD Type 2 para historico';
COMMENT ON TABLE dim_person IS 'Dimensao de pessoas com SCD Type 2';
COMMENT ON TABLE dim_municipality IS 'Dimensao de municipios brasileiros';
COMMENT ON TABLE dim_data_source IS 'Dimensao de fontes de dados e APIs';
COMMENT ON TABLE dim_user IS 'Dimensao de usuarios do sistema';

COMMENT ON TABLE fact_search IS 'Fato de pesquisas realizadas no sistema';
COMMENT ON TABLE fact_company_analysis IS 'Fato de analises de empresas com metricas de qualidade';
COMMENT ON TABLE fact_person_analysis IS 'Fato de analises de pessoas e politicos';
COMMENT ON TABLE fact_news IS 'Fato de buscas de noticias com sentimento';
COMMENT ON TABLE fact_indicator_query IS 'Fato de consultas de indicadores regionais';
COMMENT ON TABLE fact_api_call IS 'Fato de chamadas a APIs externas - metricas operacionais';
