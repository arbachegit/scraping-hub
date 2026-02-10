#!/bin/bash
# Run migrations on Supabase
# Usage: ./scripts/run_migrations.sh <database_password>

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <database_password>"
  echo ""
  echo "Get your database password from:"
  echo "  Supabase Dashboard > Settings > Database > Connection string"
  exit 1
fi

DB_PASSWORD="$1"
DB_URL="postgresql://postgres.redivrmeajmktenwshmn:${DB_PASSWORD}@aws-0-us-west-2.pooler.supabase.com:5432/postgres"
MIGRATIONS_DIR="$(dirname "$0")/../backend/database/migrations"

echo "=== Running Migrations ==="
echo ""

for migration in "$MIGRATIONS_DIR"/*.sql; do
  if [ -f "$migration" ]; then
    filename=$(basename "$migration")
    echo "Running: $filename"
    psql "$DB_URL" -f "$migration" 2>&1 | grep -v "^NOTICE:" || true
    echo "Done: $filename"
    echo ""
  fi
done

echo "=== All migrations completed ==="
