#!/usr/bin/env python3
"""
Apply migration 008: Create fontes_dados table
Run: python scripts/apply_migration_008.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from supabase import create_client

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    exit(1)

# Read migration SQL
migration_path = (
    Path(__file__).parent.parent
    / "backend/database/migrations/008_create_fontes_dados.sql"
)
sql = migration_path.read_text()

print(f"Applying migration: {migration_path.name}")
print("-" * 50)

# Connect to Supabase
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Execute migration via RPC (requires a function in Supabase)
# Alternative: Use psycopg2 directly or Supabase SQL Editor
try:
    # Try using postgrest to check if table exists
    result = client.table("fontes_dados").select("id").limit(1).execute()
    print("Table fontes_dados already exists!")
    print(f"Records: {len(result.data)}")
except Exception as e:
    if "relation" in str(e).lower() and "does not exist" in str(e).lower():
        print(
            "Table does not exist. Please run the SQL manually in Supabase SQL Editor:"
        )
        print("-" * 50)
        print(sql)
        print("-" * 50)
        print("\nSteps:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Go to SQL Editor")
        print("4. Paste the SQL above and run")
    else:
        print(f"Error: {e}")
        print("\nSQL to run manually:")
        print("-" * 50)
        print(sql)
