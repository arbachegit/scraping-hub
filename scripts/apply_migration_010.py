#!/usr/bin/env python3
"""
Aplica migration 010 - Notícias Schema

Esta migration:
1. Cria tabela dim_fontes_noticias (fontes confiáveis Twitter/X)
2. Insere fontes iniciais (aosfatos, agencialupa, veículos, jornalistas)
3. Cria tabela dim_noticias (notícias econômicas)
4. Cria tabela fato_noticias_topicos (análise Claude)
5. Cria tabela fato_noticias_empresas (relação notícia-empresa)
6. Cria tabela fato_noticias_pessoas (relação notícia-pessoa)
7. Cria view vw_noticias_completas

Uso:
    python scripts/apply_migration_010.py
    python scripts/apply_migration_010.py --dry-run
    python scripts/apply_migration_010.py --verify
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
    Aplica a migration 010.

    Args:
        dry_run: Se True, apenas mostra o SQL sem executar
    """
    migration_file = (
        Path(__file__).parent.parent
        / "backend/database/migrations/010_noticias_schema.sql"
    )

    if not migration_file.exists():
        print(f"Erro: Arquivo de migration não encontrado: {migration_file}")
        sys.exit(1)

    sql = migration_file.read_text()

    print("=" * 60)
    print("Migration 010 - Notícias Schema")
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
        result = client.table("dim_fontes_noticias").select("handle").limit(1).execute()
        if result.data:
            print("Migration já foi aplicada! Tabela dim_fontes_noticias existe.")
            print(f"Fontes encontradas: {len(result.data)}")
        else:
            print("Tabela dim_fontes_noticias existe mas está vazia.")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("Tabela dim_fontes_noticias NÃO existe. Execute a migration!")
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

    # 1. Verificar tabela dim_fontes_noticias
    try:
        result = client.table("dim_fontes_noticias").select("handle, nome, tipo").execute()
        print(f"dim_fontes_noticias: {len(result.data)} registros")
        for r in result.data[:5]:
            print(f"  - {r['handle']}: {r['nome']} ({r['tipo']})")
        if len(result.data) > 5:
            print(f"  ... e mais {len(result.data) - 5} fontes")
    except Exception as e:
        print(f"dim_fontes_noticias: ERRO - {e}")

    # 2. Verificar tabela dim_noticias
    try:
        result = client.table("dim_noticias").select("id").limit(1).execute()
        print("dim_noticias: OK - Tabela existe")
    except Exception as e:
        print(f"dim_noticias: ERRO - {e}")

    # 3. Verificar tabela fato_noticias_topicos
    try:
        result = client.table("fato_noticias_topicos").select("id").limit(1).execute()
        print("fato_noticias_topicos: OK - Tabela existe")
    except Exception as e:
        print(f"fato_noticias_topicos: ERRO - {e}")

    # 4. Verificar tabela fato_noticias_empresas
    try:
        result = client.table("fato_noticias_empresas").select("id").limit(1).execute()
        print("fato_noticias_empresas: OK - Tabela existe")
    except Exception as e:
        print(f"fato_noticias_empresas: ERRO - {e}")

    # 5. Verificar tabela fato_noticias_pessoas
    try:
        result = client.table("fato_noticias_pessoas").select("id").limit(1).execute()
        print("fato_noticias_pessoas: OK - Tabela existe")
    except Exception as e:
        print(f"fato_noticias_pessoas: ERRO - {e}")

    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Aplica migration 010 - Notícias Schema")
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
