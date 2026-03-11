#!/usr/bin/env python3
"""
Apply migration 012: Create raw_cnae table.
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
    print("MIGRATION 012: Create raw_cnae table")
    print("=" * 60)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("ERRO: SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Test if table exists
    print("\n[1/2] Verificando se tabela existe...")
    try:
        supabase.table("raw_cnae").select("id").limit(1).execute()
        print("    ✓ Tabela raw_cnae já existe")
        return
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            print("    ⚠ Tabela não existe - precisa ser criada via Supabase Studio")
        else:
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
        / "012_create_raw_cnae.sql"
    )
    print(sql_file.read_text())

    print("\n" + "=" * 60)
    print("Após executar o SQL, rode: python scripts/populate_cnae.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
