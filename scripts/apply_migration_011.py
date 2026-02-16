#!/usr/bin/env python3
"""
Apply migration 011: Add extended enrichment fields.

This migration adds:
- raw_enrichment_extended column to dim_pessoas
- Registers new data sources (GitHub, Google Scholar, Google News, Reclame Aqui)
"""

import os

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()


def main():
    """Apply migration 011."""
    print("=" * 60)
    print("MIGRATION 011: Add Extended Enrichment Fields")
    print("=" * 60)

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        return

    # Connect to Supabase
    supabase = create_client(supabase_url, supabase_key)

    # Test if column exists by trying to select it
    print("\n[1/2] Checking if column exists...")
    try:
        result = supabase.table("dim_pessoas").select("id, raw_enrichment_extended").limit(1).execute()
        print("    ✓ Column raw_enrichment_extended already exists")
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("    ⚠ Column does not exist - needs to be created via Supabase Studio")
            print("\n" + "=" * 60)
            print("MANUAL STEP REQUIRED")
            print("=" * 60)
            print("\nRun this SQL in Supabase Studio (SQL Editor):\n")
            print("ALTER TABLE dim_pessoas")
            print("ADD COLUMN IF NOT EXISTS raw_enrichment_extended JSONB;")
            print("\n" + "=" * 60)
            return
        else:
            print(f"    ✗ Error: {str(e)[:100]}")
            return

    # Register data sources
    print("\n[2/2] Registering data sources...")

    sources = [
        {
            "nome": "GitHub API",
            "categoria": "competencias",
            "fonte_primaria": "GitHub",
            "url": "https://api.github.com",
            "documentacao_url": "https://docs.github.com/en/rest",
            "formato": "JSON",
            "api_key_necessaria": False,
            "confiabilidade": "alta",
            "observacoes": "Perfil técnico de desenvolvedores - repositórios, linguagens, contribuições"
        },
        {
            "nome": "Google Scholar (via Serper)",
            "categoria": "competencias",
            "fonte_primaria": "Google Scholar",
            "url": "https://scholar.google.com",
            "documentacao_url": "https://serper.dev/docs",
            "formato": "JSON",
            "api_key_necessaria": True,
            "confiabilidade": "alta",
            "observacoes": "Publicações acadêmicas, citações, h-index"
        },
        {
            "nome": "Google News (via Serper)",
            "categoria": "reputacional",
            "fonte_primaria": "Google News",
            "url": "https://news.google.com",
            "documentacao_url": "https://serper.dev/docs",
            "formato": "JSON",
            "api_key_necessaria": True,
            "confiabilidade": "media",
            "observacoes": "Notícias e menções na mídia"
        },
        {
            "nome": "Reclame Aqui (via Serper)",
            "categoria": "reputacional",
            "fonte_primaria": "Reclame Aqui",
            "url": "https://www.reclameaqui.com.br",
            "formato": "HTML",
            "api_key_necessaria": False,
            "confiabilidade": "media",
            "observacoes": "Reclamações de consumidores - busca por nome de pessoa/empresa"
        }
    ]

    for source in sources:
        try:
            supabase.table("fontes_dados").upsert(
                source,
                on_conflict="nome"
            ).execute()
            print(f"    ✓ {source['nome']}")
        except Exception as e:
            print(f"    ⚠ {source['nome']}: {str(e)[:50]}")

    print("\n" + "=" * 60)
    print("Migration 011 completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
