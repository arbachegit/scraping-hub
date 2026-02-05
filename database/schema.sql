-- ===========================================
-- Scraping Hub - Database Schema
-- ===========================================

-- Usuarios
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pesquisas de Empresas
CREATE TABLE IF NOT EXISTS empresa_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    search_type VARCHAR(50) NOT NULL, -- 'name', 'website', 'linkedin'
    search_query JSONB NOT NULL,
    results_count INTEGER DEFAULT 0,
    results JSONB,
    credits_used INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pesquisas de LinkedIn
CREATE TABLE IF NOT EXISTS linkedin_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    search_type VARCHAR(50) NOT NULL, -- 'profile', 'company', 'employees'
    search_query JSONB NOT NULL,
    results_count INTEGER DEFAULT 0,
    results JSONB,
    credits_used INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scrapes realizados
CREATE TABLE IF NOT EXISTS scrapes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    url VARCHAR(2048) NOT NULL,
    scrape_type VARCHAR(50) NOT NULL, -- 'page', 'crawl', 'map', 'extract'
    options JSONB,
    content_length INTEGER,
    result JSONB,
    credits_used INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Logs de API
CREATE TABLE IF NOT EXISTS api_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_body JSONB,
    response_status INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Creditos do usuario
CREATE TABLE IF NOT EXISTS user_credits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    total_credits INTEGER DEFAULT 1000,
    used_credits INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_empresa_searches_user ON empresa_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_empresa_searches_created ON empresa_searches(created_at);
CREATE INDEX IF NOT EXISTS idx_linkedin_searches_user ON linkedin_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_scrapes_user ON scrapes(user_id);
CREATE INDEX IF NOT EXISTS idx_scrapes_url ON scrapes(url);
CREATE INDEX IF NOT EXISTS idx_api_logs_user ON api_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_created ON api_logs(created_at);

-- Usuario admin padrao (senha: admin123)
-- Hash gerado com: from passlib.hash import bcrypt; bcrypt.hash("admin123")
INSERT INTO users (email, password_hash, name, role)
VALUES ('admin@iconsai.ai', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.4qtOxwOT3cWvGi', 'Admin', 'admin')
ON CONFLICT (email) DO NOTHING;

-- Creditos iniciais para admin
INSERT INTO user_credits (user_id, total_credits)
SELECT id, 10000 FROM users WHERE email = 'admin@iconsai.ai'
ON CONFLICT (user_id) DO NOTHING;
