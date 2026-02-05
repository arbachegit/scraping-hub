-- ===========================================
-- Scraping Hub v2.0 - Database Schema
-- Business Intelligence Brasil
-- ===========================================

-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- EMPRESAS
-- ===========================================

-- Tabela principal de empresas
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cnpj VARCHAR(14) UNIQUE,
    razao_social VARCHAR(255),
    nome_fantasia VARCHAR(255),
    website VARCHAR(500),
    linkedin_url VARCHAR(500),
    industry VARCHAR(100),
    size VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(2),
    country VARCHAR(50) DEFAULT 'Brasil',
    founded_year INT,
    employee_count INT,
    revenue_range VARCHAR(100),
    description TEXT,
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para empresas
CREATE INDEX IF NOT EXISTS idx_companies_cnpj ON companies(cnpj);
CREATE INDEX IF NOT EXISTS idx_companies_nome ON companies(nome_fantasia);
CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies(industry);
CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(state);

-- ===========================================
-- ANÁLISES DE EMPRESAS
-- ===========================================

CREATE TABLE IF NOT EXISTS company_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL, -- 'client', 'competitor', 'prospect'

    -- SWOT Analysis
    strengths JSONB DEFAULT '[]',
    weaknesses JSONB DEFAULT '[]',
    opportunities JSONB DEFAULT '[]',
    threats JSONB DEFAULT '[]',

    -- Estratégia
    focus_areas JSONB DEFAULT '[]',
    suggested_okrs JSONB DEFAULT '[]',
    market_position TEXT,
    competitive_advantages JSONB DEFAULT '[]',

    -- Análises detalhadas
    website_analysis JSONB DEFAULT '{}',
    news_analysis JSONB DEFAULT '{}',
    social_analysis JSONB DEFAULT '{}',
    financial_analysis JSONB DEFAULT '{}',

    -- Metadados
    confidence_score FLOAT DEFAULT 0,
    sources JSONB DEFAULT '[]',
    ai_model VARCHAR(50),
    processing_time_ms INT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_analyses_company ON company_analyses(company_id);
CREATE INDEX IF NOT EXISTS idx_company_analyses_type ON company_analyses(analysis_type);

-- ===========================================
-- PESSOAS
-- ===========================================

CREATE TABLE IF NOT EXISTS people (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(255) NOT NULL,
    person_type VARCHAR(50) DEFAULT 'professional', -- 'employee', 'executive', 'politician', 'professional'

    -- Identificação
    linkedin_url VARCHAR(500),
    instagram_url VARCHAR(500),
    twitter_url VARCHAR(500),
    facebook_url VARCHAR(500),
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Profissional
    current_title VARCHAR(255),
    current_company VARCHAR(255),
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    seniority VARCHAR(50), -- 'junior', 'mid', 'senior', 'director', 'c-level'
    department VARCHAR(100),

    -- Para políticos
    political_role VARCHAR(100),
    political_party VARCHAR(50),
    state VARCHAR(2),
    city VARCHAR(100),
    mandate_start DATE,
    mandate_end DATE,

    -- Dados adicionais
    photo_url VARCHAR(500),
    bio TEXT,
    location VARCHAR(255),
    raw_data JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_people_name ON people(full_name);
CREATE INDEX IF NOT EXISTS idx_people_type ON people(person_type);
CREATE INDEX IF NOT EXISTS idx_people_company ON people(company_id);
CREATE INDEX IF NOT EXISTS idx_people_linkedin ON people(linkedin_url);

-- ===========================================
-- ANÁLISES DE PESSOAS
-- ===========================================

CREATE TABLE IF NOT EXISTS people_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES people(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    analysis_type VARCHAR(50) DEFAULT 'profile', -- 'profile', 'fit', 'background'

    -- Perfil
    strengths JSONB DEFAULT '[]',
    skills JSONB DEFAULT '[]',
    experience_years INT,
    education JSONB DEFAULT '[]',
    career_history JSONB DEFAULT '[]',

    -- Fit Analysis
    cultural_fit_score FLOAT,
    role_fit_score FLOAT,
    fit_analysis TEXT,
    fit_details JSONB DEFAULT '{}',

    -- Para políticos
    public_perception JSONB DEFAULT '{}',
    key_actions JSONB DEFAULT '[]',
    controversies JSONB DEFAULT '[]',
    voting_history JSONB DEFAULT '[]',

    -- Social Media Analysis
    social_presence JSONB DEFAULT '{}',
    engagement_metrics JSONB DEFAULT '{}',

    -- Metadados
    confidence_score FLOAT DEFAULT 0,
    sources JSONB DEFAULT '[]',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_people_analyses_person ON people_analyses(person_id);
CREATE INDEX IF NOT EXISTS idx_people_analyses_company ON people_analyses(company_id);

-- ===========================================
-- CONCORRENTES
-- ===========================================

CREATE TABLE IF NOT EXISTS company_competitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    overlap_areas JSONB DEFAULT '[]',
    comparison JSONB DEFAULT '{}',
    competitive_analysis TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(company_id, competitor_id)
);

CREATE INDEX IF NOT EXISTS idx_competitors_company ON company_competitors(company_id);

-- ===========================================
-- HISTÓRICO DE BUSCAS
-- ===========================================

CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    user_email VARCHAR(255),
    search_type VARCHAR(50) NOT NULL, -- 'company', 'person', 'politician', 'news'
    query JSONB NOT NULL,
    results_count INT DEFAULT 0,
    credits_used INT DEFAULT 1,
    processing_time_ms INT,
    status VARCHAR(20) DEFAULT 'completed', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    result_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_history_user ON search_history(user_email);
CREATE INDEX IF NOT EXISTS idx_search_history_type ON search_history(search_type);
CREATE INDEX IF NOT EXISTS idx_search_history_created ON search_history(created_at DESC);

-- ===========================================
-- NOTÍCIAS E INSIGHTS
-- ===========================================

CREATE TABLE IF NOT EXISTS news_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000),
    source VARCHAR(255),
    source_type VARCHAR(50), -- 'news', 'blog', 'official', 'social'
    published_at TIMESTAMP WITH TIME ZONE,

    content TEXT,
    summary TEXT,

    sentiment VARCHAR(20), -- 'positive', 'negative', 'neutral', 'mixed'
    sentiment_score FLOAT,

    entities JSONB DEFAULT '[]', -- empresas/pessoas mencionadas
    categories JSONB DEFAULT '[]', -- economia, política, tecnologia, etc
    keywords JSONB DEFAULT '[]',

    relevance_score FLOAT,
    credibility_score FLOAT,

    -- Relacionamentos
    company_ids JSONB DEFAULT '[]',
    person_ids JSONB DEFAULT '[]',

    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_insights(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_insights(source);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_insights(sentiment);

-- ===========================================
-- CACHE DE APIs
-- ===========================================

CREATE TABLE IF NOT EXISTS api_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    api_name VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255),
    response_data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_cache_key ON api_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_api_cache_expires ON api_cache(expires_at);

-- ===========================================
-- CRÉDITOS E USO
-- ===========================================

CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email VARCHAR(255) UNIQUE NOT NULL,
    credits_total INT DEFAULT 1000,
    credits_used INT DEFAULT 0,
    credits_remaining INT GENERATED ALWAYS AS (credits_total - credits_used) STORED,
    plan VARCHAR(50) DEFAULT 'free', -- 'free', 'basic', 'pro', 'enterprise'
    last_reset_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_credits_email ON user_credits(user_email);

-- ===========================================
-- FUNCTIONS
-- ===========================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
DROP TRIGGER IF EXISTS update_companies_updated_at ON companies;
CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_people_updated_at ON people;
CREATE TRIGGER update_people_updated_at
    BEFORE UPDATE ON people
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_credits_updated_at ON user_credits;
CREATE TRIGGER update_user_credits_updated_at
    BEFORE UPDATE ON user_credits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Função para limpar cache expirado
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM api_cache WHERE expires_at < NOW();
END;
$$ language 'plpgsql';

-- ===========================================
-- VIEWS
-- ===========================================

-- View de empresas com última análise
CREATE OR REPLACE VIEW v_companies_with_analysis AS
SELECT
    c.*,
    ca.analysis_type,
    ca.strengths,
    ca.weaknesses,
    ca.opportunities,
    ca.threats,
    ca.confidence_score,
    ca.created_at as analysis_date
FROM companies c
LEFT JOIN LATERAL (
    SELECT * FROM company_analyses
    WHERE company_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) ca ON true;

-- View de pessoas com empresa
CREATE OR REPLACE VIEW v_people_with_company AS
SELECT
    p.*,
    c.nome_fantasia as company_name,
    c.industry as company_industry
FROM people p
LEFT JOIN companies c ON p.company_id = c.id;

-- ===========================================
-- ROW LEVEL SECURITY (RLS)
-- ===========================================

-- Habilitar RLS nas tabelas sensíveis
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- Políticas básicas (ajustar conforme autenticação)
-- Por enquanto, permitir acesso total para service_role

-- ===========================================
-- DADOS INICIAIS
-- ===========================================

-- Usuário admin inicial
INSERT INTO user_credits (user_email, credits_total, plan)
VALUES ('admin@iconsai.ai', 10000, 'enterprise')
ON CONFLICT (user_email) DO NOTHING;

-- ===========================================
-- COMENTÁRIOS
-- ===========================================

COMMENT ON TABLE companies IS 'Empresas brasileiras com dados cadastrais e de mercado';
COMMENT ON TABLE company_analyses IS 'Análises SWOT, OKRs e inteligência competitiva';
COMMENT ON TABLE people IS 'Pessoas - funcionários, executivos e políticos';
COMMENT ON TABLE people_analyses IS 'Análises de perfil, fit cultural e histórico';
COMMENT ON TABLE company_competitors IS 'Relações de concorrência entre empresas';
COMMENT ON TABLE search_history IS 'Histórico de pesquisas e uso de créditos';
COMMENT ON TABLE news_insights IS 'Notícias e insights do mercado brasileiro';
COMMENT ON TABLE api_cache IS 'Cache de respostas de APIs externas';
COMMENT ON TABLE user_credits IS 'Controle de créditos e planos de usuários';
