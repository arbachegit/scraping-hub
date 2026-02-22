#!/usr/bin/env python3
"""
Aplica migration 015 - Renomear fato_noticias_pessoas para fato_pessoas

Esta migration:
1. Renomeia a tabela fato_noticias_pessoas para fato_pessoas
2. Renomeia os índices para manter consistência

Uso:
    python scripts/apply_migration_015.py
    python scripts/apply_migration_015.py --dry-run
    python scripts/apply_migration_015.py --verify
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
    Aplica a migration 015.

    Args:
        dry_run: Se True, apenas mostra o SQL sem executar
    """
    migration_file = (
        Path(__file__).parent.parent
        / "backend/database/migrations/015_rename_fato_noticias_pessoas.sql"
    )

    if not migration_file.exists():
        print(f"Erro: Arquivo de migration não encontrado: {migration_file}")
        sys.exit(1)

    sql = migration_file.read_text()

    print("=" * 60)
    print("Migration 015 - Renomear fato_noticias_pessoas para fato_pessoas")
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

    print()
    print("ATENÇÃO: A migration SQL precisa ser executada diretamente no Supabase:")
    print()
    print("1. Acesse o Supabase Dashboard")
    print("2. Vá para SQL Editor")
    print("3. Cole e execute o conteúdo de:")
    print(f"   {migration_file}")
    print()

    # Verificar se migration já foi aplicada
    try:
        result = client.table("fato_pessoas").select("id").limit(1).execute()
        print("Migration já foi aplicada! Tabela fato_pessoas existe.")
    except Exception as e:
        if "does not exist" in str(e).lower():
            # Verificar se tabela antiga ainda existe
            try:
                client.table("fato_noticias_pessoas").select("id").limit(1).execute()
                print("Tabela fato_noticias_pessoas ainda existe. Execute a migration!")
            except Exception:
                print("Nenhuma das tabelas existe. Verifique se a migration 010 foi aplicada.")
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

    # 1. Verificar tabela fato_pessoas (nova)
    try:
        result = client.table("fato_pessoas").select("id").limit(1).execute()
        print("fato_pessoas: OK - Tabela existe (migration aplicada)")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("fato_pessoas: NAO EXISTE - Migration não foi aplicada")
        else:
            print(f"fato_pessoas: ERRO - {e}")

    # 2. Verificar se tabela antiga não existe mais
    try:
        client.table("fato_noticias_pessoas").select("id").limit(1).execute()
        print("fato_noticias_pessoas: AINDA EXISTE - Migration não foi aplicada")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("fato_noticias_pessoas: NAO EXISTE (correto - foi renomeada)")
        else:
            print(f"fato_noticias_pessoas: ERRO - {e}")

    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Aplica migration 015 - Renomear fato_noticias_pessoas para fato_pessoas"
    )
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
