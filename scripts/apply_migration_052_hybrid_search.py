"""
Apply migration 052: Hybrid Search for all tables.

Creates normalized columns, trigram indexes, and hybrid search RPCs
on both Main Supabase and Brasil Data Hub instances.

- 052a: dim_empresas, dim_pessoas, dim_noticias (Main)
- 052b: dim_politicos, fato_politicos_mandatos, fato_emendas_parlamentares (BDH)

Usage:
    python scripts/apply_migration_052_hybrid_search.py
    python scripts/apply_migration_052_hybrid_search.py --main-only
    python scripts/apply_migration_052_hybrid_search.py --bdh-only
"""

import os
import sys
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BRASIL_DATA_HUB_URL = os.getenv("BRASIL_DATA_HUB_URL", "")
BRASIL_DATA_HUB_KEY = os.getenv("BRASIL_DATA_HUB_KEY", "")

MIGRATIONS_DIR = Path(__file__).parent.parent / "backend" / "database" / "migrations"
MIGRATION_MAIN = MIGRATIONS_DIR / "052a_hybrid_search_main.sql"
MIGRATION_BDH = MIGRATIONS_DIR / "052b_hybrid_search_brasil_data_hub.sql"


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL respecting $$ delimited blocks (PL/pgSQL functions)."""
    statements: list[str] = []
    current: list[str] = []
    in_dollar_block = False

    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            current.append(line)
            continue

        dollar_count = line.count("$$")
        if dollar_count % 2 == 1:
            in_dollar_block = not in_dollar_block

        current.append(line)

        if not in_dollar_block and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and not all(
                sql_line.strip().startswith("--") or not sql_line.strip()
                for sql_line in current
            ):
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip()
        if stmt and not all(
            sql_line.strip().startswith("--") or not sql_line.strip()
            for sql_line in current
        ):
            statements.append(stmt)

    return statements


def execute_sql(sql: str, url: str, key: str, timeout: int = 120) -> dict:
    """Execute SQL via Supabase HTTP API."""
    endpoint = f"{url}/pg/query"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "apikey": key,
    }

    response = httpx.post(endpoint, json={"query": sql}, headers=headers, timeout=timeout)

    if response.status_code >= 400:
        logger.error("sql_error", status=response.status_code, body=response.text[:200])
        return {"error": response.text}

    return response.json() if response.text else {}


def apply_migration(
    migration_file: Path, url: str, key: str, instance_name: str
) -> int:
    """Apply a migration file to a Supabase instance. Returns error count."""
    if not migration_file.exists():
        logger.error("file_not_found", path=str(migration_file))
        return 1

    if not url or not key:
        logger.error("missing_env", instance=instance_name)
        return 1

    sql = migration_file.read_text()
    statements = split_sql_statements(sql)

    logger.info(
        "migration_start",
        instance=instance_name,
        file=migration_file.name,
        statements=len(statements),
    )

    success = 0
    errors = 0

    for i, stmt in enumerate(statements, 1):
        first_line = stmt.strip().split("\n")[0][:80]
        logger.info("executing", instance=instance_name, step=f"{i}/{len(statements)}", sql=first_line)

        # Longer timeout for ALTER TABLE on large tables (generated columns)
        timeout = 600 if "ALTER TABLE" in stmt.upper() or "CREATE INDEX" in stmt.upper() else 120
        result = execute_sql(stmt, url, key, timeout=timeout)

        if "error" in result:
            error_text = str(result["error"])
            if "already exists" in error_text or "duplicate" in error_text.lower():
                logger.warning("skipped_exists", step=i, detail=error_text[:100])
                success += 1
            else:
                logger.error("statement_failed", step=i, error=error_text[:200])
                errors += 1
        else:
            success += 1

    logger.info(
        "migration_complete",
        instance=instance_name,
        success=success,
        errors=errors,
        total=len(statements),
    )
    return errors


def main() -> None:
    args = set(sys.argv[1:])
    run_main = "--bdh-only" not in args
    run_bdh = "--main-only" not in args

    total_errors = 0

    if run_main:
        logger.info("=== Applying 052a: Hybrid Search — Main Supabase ===")
        total_errors += apply_migration(
            MIGRATION_MAIN, SUPABASE_URL, SUPABASE_SERVICE_KEY, "main"
        )

    if run_bdh:
        logger.info("=== Applying 052b: Hybrid Search — Brasil Data Hub ===")
        total_errors += apply_migration(
            MIGRATION_BDH, BRASIL_DATA_HUB_URL, BRASIL_DATA_HUB_KEY, "brasil-data-hub"
        )

    if total_errors > 0:
        logger.error("migration_failed", total_errors=total_errors)
        sys.exit(1)
    else:
        logger.info("all_migrations_applied_successfully")


if __name__ == "__main__":
    main()
