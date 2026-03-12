"""
Apply migration 049: News Source Credibility & Classification.

Adds credibility scoring (5 layers) and news type classification to
dim_fontes_noticias and dim_noticias tables.

Usage:
    python scripts/apply_migration_049_news_credibility.py
"""

import os
import sys
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

MIGRATION_FILE = Path(__file__).parent.parent / "backend" / "database" / "migrations" / "049_news_credibility_classification.sql"


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL respecting $$ delimited blocks (PL/pgSQL functions)."""
    statements: list[str] = []
    current = []
    in_dollar_block = False

    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            current.append(line)
            continue

        # Toggle $$ block state
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

    # Leftover
    if current:
        stmt = "\n".join(current).strip()
        if stmt and not all(
            sql_line.strip().startswith("--") or not sql_line.strip()
            for sql_line in current
        ):
            statements.append(stmt)

    return statements


def execute_sql_via_supabase(sql: str) -> dict:
    """Execute SQL via Supabase HTTP API."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("missing_env", msg="SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    url = f"{SUPABASE_URL}/pg/query"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_KEY,
    }

    response = httpx.post(url, json={"query": sql}, headers=headers, timeout=30)

    if response.status_code >= 400:
        logger.error("sql_error", status=response.status_code, body=response.text)
        return {"error": response.text}

    return response.json() if response.text else {}


def main() -> None:
    if not MIGRATION_FILE.exists():
        logger.error("file_not_found", path=str(MIGRATION_FILE))
        sys.exit(1)

    sql = MIGRATION_FILE.read_text()
    statements = split_sql_statements(sql)

    logger.info("migration_start", file=MIGRATION_FILE.name, statements=len(statements))

    success = 0
    errors = 0

    for i, stmt in enumerate(statements, 1):
        # Show first line of statement for context
        first_line = stmt.strip().split("\n")[0][:80]
        logger.info("executing", step=f"{i}/{len(statements)}", sql=first_line)

        result = execute_sql_via_supabase(stmt)

        if "error" in result:
            error_text = str(result["error"])
            # Skip "already exists" errors (idempotent)
            if "already exists" in error_text or "duplicate" in error_text.lower():
                logger.warning("skipped_exists", step=i, detail=error_text[:100])
                success += 1
            else:
                logger.error("statement_failed", step=i, error=error_text[:200])
                errors += 1
        else:
            success += 1

    logger.info("migration_complete", success=success, errors=errors, total=len(statements))

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
