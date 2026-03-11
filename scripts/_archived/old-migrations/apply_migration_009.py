#!/usr/bin/env python3
"""
Aplica migration 009 - Star Schema Normalization

Esta migration:
1. Cria tabela dim_regimes_tributarios
2. Popula com 5 regimes (MEI, SIMPLES_ME, SIMPLES_EPP, LUCRO_PRESUMIDO, LUCRO_REAL)
3. Remove colunas não usadas de dim_empresas
4. Ajusta linkedin default para 'inexistente'
5. Adiciona campos em dim_pessoas
6. Adiciona FK regime_id em fato_regime_tributario
7. Adiciona codigo_ibge em dim_empresas

Uso:
    python scripts/apply_migration_009.py
    python scripts/apply_migration_009.py --dry-run
"""

import argparse
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client

from config.settings import settings


def apply_migration(dry_run: bool = False) -> None:
    """
    Aplica a migration 009.

    Args:
        dry_run: Se True, apenas mostra o SQL sem executar
    """
    migration_file = (
        Path(__file__).parent.parent
        / "backend/database/migrations/009_star_schema_normalization.sql"
    )

    if not migration_file.exists():
        print(f"Erro: Arquivo de migration não encontrado: {migration_file}")
        sys.exit(1)

    sql = migration_file.read_text()

    print("=" * 60)
    print("Migration 009 - Star Schema Normalization")
    print("=" * 60)
    print()

    if dry_run:
        print("MODO DRY-RUN - SQL que seria executado:")
        print("-" * 60)
        print(sql)
        print("-" * 60)
        return

    if not settings.has_supabase:
        print(
            "Erro: Supabase não configurado. Configure SUPABASE_URL e SUPABASE_SERVICE_KEY"
        )
        sys.exit(1)

    print("Conectando ao Supabase...")
    client = create_client(settings.supabase_url, settings.supabase_service_key)

    print("Aplicando migration...")

    # Executar SQL via RPC (função personalizada) ou query direta
    # Nota: Supabase Python SDK não suporta executar SQL arbitrário diretamente
    # Precisamos usar a conexão direta com PostgreSQL ou executar via dashboard

    print()
    print("ATENÇÃO: A migration SQL precisa ser executada diretamente no Supabase:")
    print()
    print("1. Acesse o Supabase Dashboard")
    print("2. Vá para SQL Editor")
    print("3. Cole e execute o conteúdo de:")
    print(f"   {migration_file}")
    print()
    print("Ou use a connection string para executar via psql:")
    print(
        f"   psql {settings.supabase_url.replace('https://', 'postgresql://postgres:PASSWORD@').replace('.supabase.co', '.supabase.co:5432/postgres')}"
    )
    print()

    # Verificar se migration já foi aplicada
    try:
        result = (
            client.table("dim_regimes_tributarios").select("codigo").limit(1).execute()
        )
        if result.data:
            print("Migration já foi aplicada! Tabela dim_regimes_tributarios existe.")
            print(f"Regimes encontrados: {len(result.data)}")
        else:
            print("Tabela dim_regimes_tributarios existe mas está vazia.")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("Tabela dim_regimes_tributarios NÃO existe. Execute a migration!")
        else:
            print(f"Erro ao verificar: {e}")


def verify_migration() -> None:
    """Verifica se a migration foi aplicada corretamente"""
    print()
    print("Verificando migration...")
    print("-" * 60)

    if not settings.has_supabase:
        print("Erro: Supabase não configurado")
        return

    client = create_client(settings.supabase_url, settings.supabase_service_key)

    # 1. Verificar tabela dim_regimes_tributarios
    try:
        result = (
            client.table("dim_regimes_tributarios").select("codigo, nome").execute()
        )
        print(f"dim_regimes_tributarios: {len(result.data)} registros")
        for r in result.data:
            print(f"  - {r['codigo']}: {r['nome']}")
    except Exception as e:
        print(f"dim_regimes_tributarios: ERRO - {e}")

    # 2. Verificar dim_empresas (linkedin default)
    try:
        result = (
            client.table("dim_empresas")
            .select("linkedin")
            .is_("linkedin", "null")
            .limit(1)
            .execute()
        )
        if result.data:
            print("dim_empresas: AVISO - Ainda existem registros com linkedin NULL")
        else:
            print("dim_empresas: OK - Nenhum registro com linkedin NULL")
    except Exception as e:
        print(f"dim_empresas: ERRO - {e}")

    # 3. Verificar dim_pessoas (novos campos)
    try:
        result = (
            client.table("dim_pessoas").select("email, foto_url").limit(1).execute()
        )
        print("dim_pessoas: OK - Campos email e foto_url existem")
    except Exception as e:
        print(f"dim_pessoas: ERRO - {e}")

    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Aplica migration 009 - Star Schema")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o SQL sem executar",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verifica se a migration foi aplicada",
    )

    args = parser.parse_args()

    if args.verify:
        verify_migration()
    else:
        apply_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
