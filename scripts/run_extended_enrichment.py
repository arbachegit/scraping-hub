#!/usr/bin/env python3
"""
Script para executar enriquecimento estendido de pessoas.

Fontes:
- GitHub (perfil técnico)
- Google Scholar (publicações acadêmicas)
- Google News (análise reputacional)
- Reclame Aqui (reclamações)

Uso:
    python scripts/run_extended_enrichment.py [--limit N]

Exemplo:
    python scripts/run_extended_enrichment.py --limit 10
"""
# ruff: noqa: E402

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402
from supabase import create_client  # noqa: E402

# Load environment variables
load_dotenv()

# Import after path setup
from backend.src.services.person_enrichment_extended import (  # noqa: E402
    ExtendedPersonEnrichmentService,
)


async def main(limit: int = 10):
    """Run extended person enrichment."""
    print("=" * 60)
    print("EXTENDED PERSON ENRICHMENT")
    print("GitHub + Google Scholar + Google News + Reclame Aqui")
    print("=" * 60)

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    serper_api_key = os.getenv("SERPER_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        return

    print("\nConfiguration:")
    print(f"  - Supabase: {supabase_url[:30]}...")
    print(f"  - Serper API: {'Configured' if serper_api_key else 'NOT CONFIGURED'}")
    print(f"  - GitHub Token: {'Configured' if github_token else 'NOT CONFIGURED (lower rate limit)'}")
    print(f"  - Limit: {limit} pessoas")

    if not serper_api_key:
        print("\nWARNING: SERPER_API_KEY not configured.")
        print("  Scholar, News, and Reclame Aqui enrichment will be skipped.")

    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Get people without extended enrichment
    print("\n[1/3] Buscando pessoas sem enriquecimento estendido...")

    # Query with join to get company name
    result = (
        supabase.table("dim_pessoas")
        .select("id, nome, empresa_id, dim_empresas(razao_social)")
        .is_("raw_enrichment_extended", "null")
        .limit(limit)
        .execute()
    )

    people = result.data
    print(f"      Encontradas: {len(people)} pessoas pendentes")

    if not people:
        print("\nNenhuma pessoa pendente para enriquecimento estendido.")
        return

    # Create service
    service = ExtendedPersonEnrichmentService(
        supabase=supabase,
        serper_api_key=serper_api_key,
        github_token=github_token,
    )

    # Run enrichment
    print("\n[2/3] Executando enriquecimento...")

    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "github_found": 0,
        "scholar_found": 0,
        "news_found": 0,
        "reclameaqui_found": 0,
    }

    for i, pessoa in enumerate(people, 1):
        nome = pessoa.get("nome", "Unknown")
        # Get company name from join
        empresa_data = pessoa.get("dim_empresas")
        empresa = empresa_data.get("razao_social") if empresa_data else None
        print(f"\n      [{i}/{len(people)}] {nome}...")

        try:
            result = await service.enrich_person_full(
                pessoa_id=pessoa["id"],
                nome=nome,
                empresa_nome=empresa,
                enrich_github=True,
                enrich_scholar=bool(serper_api_key),
                enrich_news=bool(serper_api_key),
                enrich_reclameaqui=bool(serper_api_key),
            )

            stats["processed"] += 1
            stats["success"] += 1

            # Count sources found
            sources_found = []
            if result.get("github", {}).get("found"):
                stats["github_found"] += 1
                sources_found.append("GitHub")
            if result.get("scholar", {}).get("found"):
                stats["scholar_found"] += 1
                sources_found.append("Scholar")
            if result.get("news", {}).get("found"):
                stats["news_found"] += 1
                sources_found.append("News")
            if result.get("reclameaqui", {}).get("found"):
                stats["reclameaqui_found"] += 1
                sources_found.append("ReclameAqui")

            # Print result
            if sources_found:
                print(f"               OK - Found: {', '.join(sources_found)}")

                # Print risk if exists
                risk = result.get("risk_analysis", {}).get("nivel_geral")
                if risk and risk != "baixo":
                    print(f"               ⚠️  RISK LEVEL: {risk.upper()}")
            else:
                print("               OK - No data found in sources")

        except Exception as e:
            stats["failed"] += 1
            print(f"               ERROR: {str(e)[:50]}")

        # Rate limiting
        await asyncio.sleep(2)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Processed:        {stats['processed']}")
    print(f"  Success:          {stats['success']}")
    print(f"  Failed:           {stats['failed']}")
    print("-" * 60)
    print(f"  GitHub found:     {stats['github_found']}")
    print(f"  Scholar found:    {stats['scholar_found']}")
    print(f"  News found:       {stats['news_found']}")
    print(f"  ReclameAqui found:{stats['reclameaqui_found']}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run extended person enrichment")
    parser.add_argument("--limit", type=int, default=10, help="Number of people to process")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit))
