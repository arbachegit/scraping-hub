#!/usr/bin/env python3
"""
Script para executar enriquecimento de pessoas via Apollo/Perplexity.

Uso:
    python scripts/run_person_enrichment.py [--limit N]

Exemplo:
    python scripts/run_person_enrichment.py --limit 20
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Import after path setup
from backend.src.services.person_enrichment import (
    PersonEnrichmentService,
    enrich_all_pending_persons,
)


async def main(limit: int = 20):
    """Run person enrichment."""
    print("=" * 50)
    print("PERSON ENRICHMENT - Apollo + Perplexity")
    print("=" * 50)

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    apollo_api_key = os.getenv("APOLLO_API_KEY")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        return

    print(f"\nConfiguration:")
    print(f"  - Supabase: {supabase_url[:30]}...")
    print(f"  - Apollo API: {'Configured' if apollo_api_key else 'NOT CONFIGURED'}")
    print(f"  - Perplexity API: {'Configured' if perplexity_api_key else 'NOT CONFIGURED'}")
    print(f"  - Limit: {limit} pessoas")

    if not apollo_api_key and not perplexity_api_key:
        print("\nERROR: At least one API key (Apollo or Perplexity) is required")
        return

    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Get people without enrichment
    print("\n[1/3] Buscando pessoas sem enriquecimento...")

    result = (
        supabase.table("dim_pessoas")
        .select("id, nome_completo, linkedin_url")
        .is_("raw_apollo_data", "null")
        .limit(limit)
        .execute()
    )

    people = result.data
    print(f"      Encontradas: {len(people)} pessoas pendentes")

    if not people:
        print("\nNenhuma pessoa pendente para enriquecimento.")
        return

    # Run enrichment
    print("\n[2/3] Executando enriquecimento...")

    service = PersonEnrichmentService(
        supabase=supabase,
        apollo_api_key=apollo_api_key,
        perplexity_api_key=perplexity_api_key,
    )

    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "linkedin_found": 0,
    }

    for i, pessoa in enumerate(people, 1):
        nome = pessoa.get("nome_completo", "Unknown")
        print(f"\n      [{i}/{len(people)}] {nome}...")

        try:
            result = await service.enrich_person(
                pessoa_id=pessoa["id"],
                nome=nome,
                linkedin_url=pessoa.get("linkedin_url"),
            )

            stats["processed"] += 1

            if result["success"]:
                stats["success"] += 1
                source = result.get("source", "unknown")

                # Check if LinkedIn was found
                raw_data = result.get("raw_data", {})
                linkedin = raw_data.get("linkedin_url") if raw_data else None

                if linkedin:
                    stats["linkedin_found"] += 1
                    # Update person with LinkedIn
                    supabase.table("dim_pessoas").update({
                        "linkedin_url": linkedin,
                        "raw_apollo_data": raw_data,
                    }).eq("id", pessoa["id"]).execute()
                    print(f"               OK ({source}) - LinkedIn: {linkedin}")
                else:
                    # Just save raw data
                    supabase.table("dim_pessoas").update({
                        "raw_apollo_data": raw_data,
                    }).eq("id", pessoa["id"]).execute()
                    print(f"               OK ({source}) - sem LinkedIn")
            else:
                stats["failed"] += 1
                print(f"               FAILED - not found")

        except Exception as e:
            stats["failed"] += 1
            print(f"               ERROR: {str(e)[:50]}")

        # Rate limiting - wait between requests
        await asyncio.sleep(1)

    # Print summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"  Processed: {stats['processed']}")
    print(f"  Success:   {stats['success']}")
    print(f"  Failed:    {stats['failed']}")
    print(f"  LinkedIn found: {stats['linkedin_found']}")
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run person enrichment")
    parser.add_argument("--limit", type=int, default=20, help="Number of people to process")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit))
