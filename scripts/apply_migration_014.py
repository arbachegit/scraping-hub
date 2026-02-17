#!/usr/bin/env python3
"""
Apply migration 014: Standardize CNAE FK in fato_regime_tributario.
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
    print("MIGRATION 014: Standardize CNAE FK")
    print("=" * 60)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("ERRO: SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Check current state
    print("\n[1/3] Verificando estado atual...")

    try:
        # Check raw_cnae count
        result = supabase.table("raw_cnae").select("id", count="exact").limit(1).execute()
        print(f"    ✓ raw_cnae: {result.count} CNAEs cadastrados")
    except Exception as e:
        print(f"    ✗ raw_cnae não encontrada: {e}")
        print("    → Execute primeiro: python scripts/populate_cnae.py")
        sys.exit(1)

    try:
        # Check fato_regime_tributario
        result = supabase.table("fato_regime_tributario").select("id, cnae_principal", count="exact").limit(5).execute()
        print(f"    ✓ fato_regime_tributario: {result.count} registros")

        # Sample cnae_principal values
        if result.data:
            cnaes = [r.get("cnae_principal") for r in result.data if r.get("cnae_principal")]
            if cnaes:
                print(f"    → Exemplos de cnae_principal: {cnaes[:3]}")
    except Exception as e:
        print(f"    ✗ fato_regime_tributario: {e}")

    try:
        # Check dim_empresas
        result = supabase.table("dim_empresas").select("id", count="exact").limit(1).execute()
        print(f"    ✓ dim_empresas: {result.count} empresas")
    except Exception as e:
        print(f"    ✗ dim_empresas: {e}")

    print("\n" + "=" * 60)
    print("AÇÃO MANUAL NECESSÁRIA")
    print("=" * 60)
    print("\nExecute este SQL no Supabase Studio (SQL Editor):\n")

    sql_file = Path(__file__).parent.parent / "backend" / "database" / "migrations" / "014_standardize_cnae_fk.sql"
    print(sql_file.read_text())

    print("\n" + "=" * 60)
    print("Após executar, verifique com:")
    print("=" * 60)
    print("""
SELECT
    'fato_regime_tributario' as tabela,
    COUNT(*) FILTER (WHERE cnae_id IS NOT NULL) as com_cnae,
    COUNT(*) FILTER (WHERE cnae_id IS NULL AND cnae_principal IS NOT NULL) as sem_match,
    COUNT(*) as total
FROM fato_regime_tributario
UNION ALL
SELECT
    'dim_empresas' as tabela,
    COUNT(*) FILTER (WHERE cnae_id IS NOT NULL) as com_cnae,
    COUNT(*) FILTER (WHERE cnae_id IS NULL) as sem_match,
    COUNT(*) as total
FROM dim_empresas;
""")


if __name__ == "__main__":
    main()
