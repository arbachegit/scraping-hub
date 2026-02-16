#!/usr/bin/env python3
"""
Apply migration 011: Add extended enrichment fields.

This migration adds:
- raw_enrichment_extended column to dim_pessoas
- Index for checking enrichment status
- Registers new data sources (GitHub, Google Scholar, Google News, Reclame Aqui)
"""

import os
from pathlib import Path

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

    # Read migration SQL
    migration_file = Path(__file__).parent.parent / "backend/database/migrations/011_add_extended_enrichment.sql"

    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        return

    sql = migration_file.read_text()

    print("\nMigration SQL:")
    print("-" * 60)
    print(sql[:500] + "..." if len(sql) > 500 else sql)
    print("-" * 60)

    # Connect to Supabase
    supabase = create_client(supabase_url, supabase_key)

    # Execute migration statements one by one
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    print(f"\nExecuting {len(statements)} statements...")

    for i, statement in enumerate(statements, 1):
        try:
            # Skip empty statements
            if not statement or statement.isspace():
                continue

            print(f"\n[{i}/{len(statements)}] Executing...")
            print(f"    {statement[:80]}..." if len(statement) > 80 else f"    {statement}")

            # Execute via RPC
            supabase.rpc("exec_sql", {"sql": statement + ";"}).execute()
            print("    ✓ Success")

        except Exception as e:
            error_msg = str(e)
            # Ignore "already exists" errors
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                print(f"    ⚠ Already exists (skipped)")
            else:
                print(f"    ✗ Error: {error_msg[:100]}")

    print("\n" + "=" * 60)
    print("Migration 011 completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
