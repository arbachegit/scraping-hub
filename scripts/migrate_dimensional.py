#!/usr/bin/env python3
"""
Migrate Dimensional Schema - Executa o schema dimensional no Supabase
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
SCHEMA_FILE = ROOT_DIR / "database" / "schema_dimensional.sql"


def load_env():
    """Carrega .env"""
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = value


def get_database_url():
    """Obtém DATABASE_URL"""
    load_env()
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    supabase_url = os.getenv("SUPABASE_URL", "")
    db_password = os.getenv("SUPABASE_DB_PASSWORD", "")
    if supabase_url and db_password:
        project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")
        return f"postgresql://postgres.{project_ref}:{db_password}@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
    return None


def copy_to_clipboard(text: str) -> bool:
    """Copia para clipboard (macOS)"""
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode("utf-8"))
        return p.returncode == 0
    except Exception:
        return False


def execute_sql(database_url: str, sql: str) -> bool:
    """Executa SQL com psycopg2"""
    try:
        import psycopg2
    except ImportError:
        print("Instalando psycopg2-binary...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
        import psycopg2

    print("Conectando ao PostgreSQL...")

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Executando schema (pode levar alguns segundos)...")

        # Executar o SQL inteiro de uma vez
        cursor.execute(sql)

        cursor.close()
        conn.close()
        print("Schema executado com sucesso!")
        return True

    except psycopg2.Error as e:
        error_msg = str(e)
        # Se for erro de "já existe", tudo bem
        if "already exists" in error_msg:
            print("Algumas tabelas ja existiam (OK)")
            return True
        print(f"\nErro: {error_msg}")
        return False
    except Exception as e:
        print(f"\nErro: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migra schema dimensional")
    parser.add_argument("--url", help="DATABASE_URL")
    parser.add_argument("--copy", action="store_true", help="Copia SQL para clipboard")
    args = parser.parse_args()

    if not SCHEMA_FILE.exists():
        print(f"Arquivo nao encontrado: {SCHEMA_FILE}")
        sys.exit(1)

    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    print(f"Schema: {SCHEMA_FILE.name} ({len(sql):,} bytes)")

    if args.copy:
        if copy_to_clipboard(sql):
            print("\nSQL copiado para o clipboard!")
            print("Cole no SQL Editor do Supabase e execute.")
        else:
            print(f"Copie manualmente: {SCHEMA_FILE}")
        sys.exit(0)

    database_url = args.url or get_database_url()
    if not database_url:
        print("\nDATABASE_URL nao encontrada!")
        print("\nAdicione ao .env:")
        print(
            "  DATABASE_URL=postgresql://postgres.[ref]:[pass]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
        )
        print("\nOu use: python scripts/migrate_dimensional.py --copy")
        sys.exit(1)

    print(f"Conectando: {database_url[:50]}...")
    success = execute_sql(database_url, sql)

    if success:
        print("\nTabelas criadas com sucesso!")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
