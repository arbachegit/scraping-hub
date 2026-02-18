#!/usr/bin/env python3
"""
Apply migration 013: Standardize location columns and add CNAE FK.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from supabase import create_client

load_dotenv()


def main():
    print("=" * 60)
    print("MIGRATION 013: Standardize location columns + CNAE FK")
    print("=" * 60)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("ERRO: SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Test if dim_empresas has cnae_id column
    print("\n[1/2] Verificando estrutura atual de dim_empresas...")
    try:
        supabase.table("dim_empresas").select("id, cnpj, codigo_ibge").limit(
            1
        ).execute()
        print("    ✓ Tabela dim_empresas existe")

        # Check if cnae_id column exists
        try:
            supabase.table("dim_empresas").select("cnae_id").limit(1).execute()
            print("    ✓ Coluna cnae_id já existe")
        except Exception:
            print("    ⚠ Coluna cnae_id não existe - será criada")

    except Exception as e:
        print(f"    Erro: {e}")

    print("\n" + "=" * 60)
    print("AÇÃO MANUAL NECESSÁRIA")
    print("=" * 60)
    print("\nExecute este SQL no Supabase Studio (SQL Editor):\n")

    sql_file = (
        Path(__file__).parent.parent
        / "backend"
        / "database"
        / "migrations"
        / "013_standardize_location_cnae.sql"
    )
    print(sql_file.read_text())

    print("\n" + "=" * 60)
    print("Após executar o SQL, o MCP brasil-data-hub estará disponível")
    print("para buscar dados de municípios e estados.")
    print("=" * 60)


if __name__ == "__main__":
    main()
