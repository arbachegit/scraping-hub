#!/usr/bin/env python3
"""
Aplica migration 016 - dim_tema_pessoas e ajustes em fato_pessoas

Esta migration:
1. Cria tabela dim_tema_pessoas com temas/categorias
2. Insere os 13 temas definidos
3. Adiciona coluna id_tema em fato_pessoas (FK para dim_tema_pessoas)
4. Renomeia coluna contexto para ano em fato_pessoas
5. Adiciona coluna id_fonte_dados em fato_pessoas (FK para fontes_dados)

Uso:
    python scripts/apply_migration_016.py
    python scripts/apply_migration_016.py --dry-run
    python scripts/apply_migration_016.py --verify
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
    Aplica a migration 016.

    Args:
        dry_run: Se True, apenas mostra o SQL sem executar
    """
    migration_file = (
        Path(__file__).parent.parent
        / "backend/database/migrations/016_dim_tema_pessoas.sql"
    )

    if not migration_file.exists():
        print(f"Erro: Arquivo de migration não encontrado: {migration_file}")
        sys.exit(1)

    sql = migration_file.read_text()

    print("=" * 60)
    print("Migration 016 - dim_tema_pessoas e ajustes em fato_pessoas")
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
        result = client.table("dim_tema_pessoas").select("tema").execute()
        if result.data:
            print(f"dim_tema_pessoas já existe com {len(result.data)} temas:")
            for r in result.data:
                print(f"  - {r['tema']}")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("Tabela dim_tema_pessoas NÃO existe. Execute a migration!")
        else:
            print(f"Erro ao verificar: {e}")


def verify_migration() -> None:
    """Verifica se a migration foi aplicada corretamente"""
    print()
    print("Verificando migration 016...")
    print("-" * 60)

    if not settings.has_supabase:
        print("Erro: Supabase não configurado")
        return

    client = create_client(settings.supabase_url, settings.supabase_service_key)

    # 1. Verificar tabela dim_tema_pessoas
    try:
        result = client.table("dim_tema_pessoas").select("tema").execute()
        print(f"dim_tema_pessoas: OK - {len(result.data)} temas")
        for r in result.data:
            print(f"  - {r['tema']}")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("dim_tema_pessoas: NAO EXISTE")
        else:
            print(f"dim_tema_pessoas: ERRO - {e}")

    # 2. Verificar colunas em fato_pessoas
    print()
    print("Verificando colunas em fato_pessoas:")

    # Testar id_tema
    try:
        client.table("fato_pessoas").select("id_tema").limit(1).execute()
        print("  id_tema: OK")
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("  id_tema: NAO EXISTE")
        else:
            print(f"  id_tema: ERRO - {e}")

    # Testar ano (antiga contexto)
    try:
        client.table("fato_pessoas").select("ano").limit(1).execute()
        print("  ano: OK")
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            # Verificar se ainda existe contexto
            try:
                client.table("fato_pessoas").select("contexto").limit(1).execute()
                print("  ano: NAO EXISTE (contexto ainda existe - migration não aplicada)")
            except Exception:
                print("  ano: NAO EXISTE")
        else:
            print(f"  ano: ERRO - {e}")

    # Testar id_fonte_dados
    try:
        client.table("fato_pessoas").select("id_fonte_dados").limit(1).execute()
        print("  id_fonte_dados: OK")
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("  id_fonte_dados: NAO EXISTE")
        else:
            print(f"  id_fonte_dados: ERRO - {e}")

    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Aplica migration 016 - dim_tema_pessoas e ajustes em fato_pessoas"
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
