#!/usr/bin/env python3
"""
Script de Migração - Star Schema
Aplica o schema dimensional no Supabase

Uso:
    python scripts/migrate_star_schema.py

Requer DATABASE_URL no .env ou como argumento:
    DATABASE_URL=postgresql://... python scripts/migrate_star_schema.py

Para obter a URL do Supabase:
    1. Acesse o Dashboard do Supabase
    2. Vá em Settings > Database
    3. Copie a "Connection string" (URI)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Adicionar o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    import psycopg2  # noqa: E402
except ImportError:
    print("Instalando psycopg2...")
    os.system(f"{sys.executable} -m pip install psycopg2-binary")
    import psycopg2  # noqa: E402


def get_database_url() -> str:
    """Obtém a URL do banco de dados"""
    load_dotenv(ROOT_DIR / ".env")

    # Tentar DATABASE_URL primeiro
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Construir a partir das variáveis do Supabase
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_password = os.getenv("SUPABASE_DB_PASSWORD", "")

    if supabase_url and supabase_password:
        # Extrair o host do Supabase URL
        # https://xxx.supabase.co -> db.xxx.supabase.co
        host = supabase_url.replace("https://", "").replace(".supabase.co", "")
        db_host = f"db.{host}.supabase.co"
        return f"postgresql://postgres:{supabase_password}@{db_host}:5432/postgres"

    return ""


def run_migration():
    """Executa a migração do star schema"""
    print("=" * 50)
    print("Migração: Star Schema")
    print("=" * 50)

    # Obter conexão
    db_url = get_database_url()

    if not db_url:
        print("\nERRO: DATABASE_URL não configurada!")
        print("\nOpções:")
        print("1. Adicione DATABASE_URL no .env")
        print("2. Adicione SUPABASE_DB_PASSWORD no .env")
        print("3. Execute com: DATABASE_URL=... python scripts/migrate_star_schema.py")
        print("\nPara obter a URL:")
        print("  - Supabase Dashboard > Settings > Database > Connection string")
        sys.exit(1)

    # Ler arquivo SQL
    sql_file = ROOT_DIR / "database" / "schema_star.sql"
    if not sql_file.exists():
        print(f"ERRO: Arquivo não encontrado: {sql_file}")
        sys.exit(1)

    sql_content = sql_file.read_text(encoding="utf-8")
    print(f"\nArquivo SQL: {sql_file}")
    print(f"Tamanho: {len(sql_content)} bytes")

    # Conectar e executar
    print("\nConectando ao banco de dados...")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Conexão estabelecida!")
        print("\nExecutando migração...")

        # Executar o SQL completo
        cursor.execute(sql_content)

        print("\nMigração concluída com sucesso!")

        # Verificar tabelas criadas
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'dim_%' OR table_name LIKE 'fato_%'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print(f"\nTabelas criadas ({len(tables)}):")
        for (table,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} registros")

        cursor.close()
        conn.close()

        print("\n" + "=" * 50)
        print("Migração finalizada!")
        print("=" * 50)

    except psycopg2.Error as e:
        print(f"\nERRO PostgreSQL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERRO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
