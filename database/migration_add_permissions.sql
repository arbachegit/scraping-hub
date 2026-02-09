-- ===========================================
-- Migration: Add permissions to users table
-- Date: 2026-02-09
-- Description: Adiciona campo de permissões por área e role super_admin
-- ===========================================

-- Adicionar coluna de permissões (array de áreas permitidas)
-- Áreas: 'empresas', 'pessoas', 'politicos', 'noticias'
ALTER TABLE users
ADD COLUMN IF NOT EXISTS permissions TEXT[] DEFAULT '{}';

-- Comentário para documentação
COMMENT ON COLUMN users.permissions IS 'Array de áreas permitidas: empresas, pessoas, politicos, noticias';

-- Atualizar usuário admin existente para super_admin com todas as permissões
UPDATE users
SET role = 'super_admin',
    permissions = ARRAY['empresas', 'pessoas', 'politicos', 'noticias']
WHERE email = 'admin@iconsai.ai' OR email = 'arbache@gmail.com';

-- Criar índice para busca por role
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Criar índice para busca por permissões (GIN para arrays)
CREATE INDEX IF NOT EXISTS idx_users_permissions ON users USING GIN(permissions);

-- Inserir usuário arbache@gmail.com se não existir
-- Hash bcrypt para 'admin123'
INSERT INTO users (email, password_hash, name, role, permissions, is_active)
VALUES (
    'arbache@gmail.com',
    '$2b$12$ne84FJ3BdgHPGhNnDQOC3OUZBQHbnStaDalq17VBnQXeX1/4.ZDMm',
    'Fernando Arbache',
    'super_admin',
    ARRAY['empresas', 'pessoas', 'politicos', 'noticias'],
    true
)
ON CONFLICT (email) DO UPDATE SET
    role = 'super_admin',
    permissions = ARRAY['empresas', 'pessoas', 'politicos', 'noticias'];

-- Verificar estrutura
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users';
