#!/usr/bin/env python3
"""
Script de migração para criar tabela fontes_dados.

Execute após configurar o Supabase:
    python scripts/migrate_fontes_dados.py

Este script cria a tabela de rastreabilidade de fontes de dados
conforme requisito do CLAUDE.md.
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

MIGRATION_SQL = """
-- ===========================================
-- Fontes de Dados - Rastreabilidade (OBRIGATÓRIO)
-- Conforme CLAUDE.md: ALWAYS registrar fontes de dados
-- ===========================================

CREATE TABLE IF NOT EXISTS fontes_dados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificação
    nome VARCHAR(255) NOT NULL,
    categoria VARCHAR(50) NOT NULL,

    -- Origem
    fonte_primaria VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    documentacao_url TEXT,

    -- Rastreamento
    data_primeira_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_ultima_atualizacao TIMESTAMP,
    periodicidade VARCHAR(50),

    -- Metadados
    formato VARCHAR(50) DEFAULT 'JSON',
    autenticacao_requerida BOOLEAN DEFAULT true,
    api_key_necessaria BOOLEAN DEFAULT true,

    -- Qualidade
    confiabilidade VARCHAR(20) DEFAULT 'alta',
    cobertura TEXT,
    observacoes TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(nome, categoria)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_fontes_categoria ON fontes_dados(categoria);
CREATE INDEX IF NOT EXISTS idx_fontes_fonte ON fontes_dados(fonte_primaria);
CREATE INDEX IF NOT EXISTS idx_fontes_confiabilidade ON fontes_dados(confiabilidade);
"""


INITIAL_DATA = [
    {
        "nome": "BrasilAPI - CNPJ",
        "categoria": "api",
        "fonte_primaria": "BrasilAPI",
        "url": "https://brasilapi.com.br/api/cnpj/v1",
        "documentacao_url": "https://brasilapi.com.br/docs",
        "formato": "JSON",
        "autenticacao_requerida": False,
        "api_key_necessaria": False,
        "confiabilidade": "alta",
        "cobertura": "CNPJs de empresas brasileiras",
        "periodicidade": "tempo_real",
    },
    {
        "nome": "BrasilAPI - CEP",
        "categoria": "api",
        "fonte_primaria": "BrasilAPI",
        "url": "https://brasilapi.com.br/api/cep/v2",
        "documentacao_url": "https://brasilapi.com.br/docs",
        "formato": "JSON",
        "autenticacao_requerida": False,
        "api_key_necessaria": False,
        "confiabilidade": "alta",
        "cobertura": "CEPs brasileiros",
        "periodicidade": "tempo_real",
    },
    {
        "nome": "Serper - Google Search",
        "categoria": "api",
        "fonte_primaria": "Serper.dev",
        "url": "https://google.serper.dev/search",
        "documentacao_url": "https://serper.dev/docs",
        "formato": "JSON",
        "autenticacao_requerida": True,
        "api_key_necessaria": True,
        "confiabilidade": "alta",
        "cobertura": "Resultados de busca Google",
        "periodicidade": "tempo_real",
    },
    {
        "nome": "Tavily - AI Search",
        "categoria": "api",
        "fonte_primaria": "Tavily",
        "url": "https://api.tavily.com/search",
        "documentacao_url": "https://docs.tavily.com",
        "formato": "JSON",
        "autenticacao_requerida": True,
        "api_key_necessaria": True,
        "confiabilidade": "alta",
        "cobertura": "Busca com contexto AI",
        "periodicidade": "tempo_real",
    },
    {
        "nome": "Apollo - People Search",
        "categoria": "api",
        "fonte_primaria": "Apollo.io",
        "url": "https://api.apollo.io/v1/mixed_people/search",
        "documentacao_url": "https://apolloio.github.io/apollo-api-docs",
        "formato": "JSON",
        "autenticacao_requerida": True,
        "api_key_necessaria": True,
        "confiabilidade": "media",
        "cobertura": "Profissionais e contatos B2B",
        "periodicidade": "tempo_real",
    },
    {
        "nome": "Perplexity - Research",
        "categoria": "api",
        "fonte_primaria": "Perplexity AI",
        "url": "https://api.perplexity.ai/chat/completions",
        "documentacao_url": "https://docs.perplexity.ai",
        "formato": "JSON",
        "autenticacao_requerida": True,
        "api_key_necessaria": True,
        "confiabilidade": "alta",
        "cobertura": "Pesquisa com AI avançada",
        "periodicidade": "tempo_real",
    },
    {
        "nome": "Anthropic - Claude",
        "categoria": "api",
        "fonte_primaria": "Anthropic",
        "url": "https://api.anthropic.com/v1/messages",
        "documentacao_url": "https://docs.anthropic.com",
        "formato": "JSON",
        "autenticacao_requerida": True,
        "api_key_necessaria": True,
        "confiabilidade": "alta",
        "cobertura": "Análise e geração de texto com AI",
        "periodicidade": "tempo_real",
    },
]


def run_migration():
    """Executa a migração."""
    print("=" * 50)
    print("Migração: Criar tabela fontes_dados")
    print("=" * 50)

    client = get_supabase()
    if not client:
        print("ERRO: Supabase não configurado!")
        print("Configure SUPABASE_URL e SUPABASE_SERVICE_KEY no .env")
        return False

    print("\n1. Criando tabela fontes_dados...")

    # Nota: Supabase não suporta SQL raw diretamente via SDK
    # A tabela deve ser criada via Supabase Dashboard ou SQL Editor
    print("   IMPORTANTE: Execute o SQL em database/schema.sql")
    print("   no Supabase Dashboard > SQL Editor")

    print("\n2. Inserindo dados iniciais...")

    for fonte in INITIAL_DATA:
        try:
            client.table("fontes_dados").upsert(fonte, on_conflict="nome,categoria").execute()
            print(f"   OK: {fonte['nome']}")
        except Exception as e:
            print(f"   ERRO em {fonte['nome']}: {e}")

    print("\n3. Verificando dados...")

    try:
        result = client.table("fontes_dados").select("nome, categoria, fonte_primaria").execute()
        print(f"   Total de fontes registradas: {len(result.data)}")
        for r in result.data:
            print(f"   - {r['nome']} ({r['fonte_primaria']})")
    except Exception as e:
        print(f"   ERRO ao verificar: {e}")
        print("   A tabela pode não existir ainda. Crie-a no Supabase Dashboard.")
        return False

    print("\n" + "=" * 50)
    print("Migração concluída!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
