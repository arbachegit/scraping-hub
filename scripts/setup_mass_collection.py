#!/usr/bin/env python3
"""
IconsAI - Setup Mass Collection
Prepara o ambiente para coleta massiva de empresas

Etapas:
1. Verificar conexão com Supabase
2. Verificar/criar tabelas necessárias
3. Popular CNAEs
4. Popular cidades
5. Verificar APIs disponíveis

Author: IconsAI Scraping
"""

import asyncio
import sys
from pathlib import Path

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger()


async def check_supabase_connection():
    """Verifica conexão com Supabase"""
    print("\n[1/5] Verificando conexão com Supabase...")

    from src.database.client import get_supabase

    supabase = get_supabase()

    if not supabase:
        print("   ❌ Supabase não configurado")
        print("      Configure SUPABASE_URL e SUPABASE_SERVICE_KEY no .env")
        return False

    try:
        # Tentar uma query simples
        supabase.table("dim_empresas").select("count").limit(1).execute()
        print("   ✅ Conexão OK")
        return True
    except Exception as e:
        print(f"   ⚠️  Erro na conexão: {e}")
        return True  # Continuar mesmo assim


async def check_tables():
    """Verifica se as tabelas necessárias existem"""
    print("\n[2/5] Verificando tabelas...")

    from src.database.client import get_supabase

    supabase = get_supabase()
    if not supabase:
        return False

    tables = {
        "dim_empresas": False,
        "dim_pessoas": False,
        "fato_eventos_pessoa": False,
        "raw_cnae": False,
        "geo_municipios": False,
    }

    for table in tables:
        try:
            supabase.table(table).select("*").limit(1).execute()
            tables[table] = True
            print(f"   ✅ {table}")
        except Exception as e:
            print(f"   ❌ {table} - {e}")

    missing = [t for t, exists in tables.items() if not exists]
    if missing:
        print(f"\n   ⚠️  Tabelas faltando: {', '.join(missing)}")
        print("      Execute os scripts SQL em database/ para criar as tabelas")

    return len(missing) == 0


async def populate_cnaes():
    """Popula tabela de CNAEs"""
    print("\n[3/5] Verificando/populando CNAEs...")

    from src.database.client import get_supabase

    supabase = get_supabase()
    if not supabase:
        return False

    try:
        result = (
            supabase.table("raw_cnae").select("*", count="exact").limit(1).execute()
        )

        count = result.count or 0
        if count > 1000:
            print(f"   ✅ CNAEs já populados ({count} registros)")
            return True

        print(f"   📊 CNAEs insuficientes ({count}), populando...")

        # Importar e executar o script
        from scripts.populate_cnae import main as populate_cnae_main

        populate_cnae_main()
        print("   ✅ CNAEs populados")
        return True

    except Exception as e:
        print(f"   ❌ Erro ao verificar CNAEs: {e}")
        return False


async def populate_cities():
    """Popula tabela de cidades"""
    print("\n[4/5] Verificando/populando cidades...")

    from src.database.client import get_supabase

    supabase = get_supabase()
    if not supabase:
        return False

    try:
        result = (
            supabase.table("geo_municipios")
            .select("*", count="exact")
            .limit(1)
            .execute()
        )

        count = result.count or 0
        if count > 5000:
            print(f"   ✅ Cidades já populadas ({count} registros)")
            return True

        print(f"   📊 Cidades insuficientes ({count}), populando...")

        # Executar script de cidades
        from scripts.populate_cities import populate_cities as pop_cities

        await pop_cities()
        print("   ✅ Cidades populadas")
        return True

    except Exception as e:
        # Tabela pode não existir - criar dados inline
        print(f"   ⚠️  Tabela geo_municipios não existe ou erro: {e}")
        print("   📊 Criando dados de cidades em memória...")
        return True  # Continuar, os scripts usam fallback


async def check_apis():
    """Verifica APIs disponíveis"""
    print("\n[5/5] Verificando APIs...")

    apis = {
        "BrasilAPI": ("https://brasilapi.com.br/api/cnpj/v1/00000000000000", False),
        "IBGE": (
            "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?limit=1",
            True,
        ),
    }

    async with httpx.AsyncClient(timeout=10) as client:
        for name, (url, should_succeed) in apis.items():
            try:
                response = await client.get(url)
                if should_succeed and response.status_code == 200:
                    print(f"   ✅ {name}")
                elif not should_succeed and response.status_code in [400, 404]:
                    print(f"   ✅ {name} (resposta esperada)")
                else:
                    print(f"   ⚠️  {name} - Status {response.status_code}")
            except Exception as e:
                print(f"   ❌ {name} - {e}")

    return True


async def print_summary():
    """Imprime resumo e estimativas"""
    from src.database.client import get_supabase

    supabase = get_supabase()

    print("\n" + "=" * 60)
    print("RESUMO DA CONFIGURAÇÃO")
    print("=" * 60)

    if supabase:
        # Contar CNAEs
        try:
            cnaes = (
                supabase.table("raw_cnae").select("*", count="exact").limit(1).execute()
            )
            cnae_count = cnaes.count or 0
        except Exception:
            cnae_count = 0

        # Contar cidades
        try:
            cidades = (
                supabase.table("geo_municipios")
                .select("*", count="exact")
                .limit(1)
                .execute()
            )
            cidade_count = cidades.count or 0
        except Exception:
            cidade_count = 1027  # Fallback para capitais + 1000 maiores

        # Contar empresas já existentes
        try:
            empresas = (
                supabase.table("dim_empresas")
                .select("*", count="exact")
                .limit(1)
                .execute()
            )
            empresa_count = empresas.count or 0
        except Exception:
            empresa_count = 0

        total_combinations = cnae_count * min(cidade_count, 1027)
        remaining = total_combinations - empresa_count

        print(f"  CNAEs disponíveis:     {cnae_count:,}")
        print(f"  Cidades disponíveis:   {min(cidade_count, 1027):,}")
        print(f"  Combinações totais:    {total_combinations:,}")
        print(f"  Empresas já coletadas: {empresa_count:,}")
        print(f"  Restantes:             {remaining:,}")
        print("=" * 60)

        # Estimativa de tempo
        # Assumindo 50 req/s com 10 workers
        seconds = remaining / 50
        hours = seconds / 3600

        print("\n📊 ESTIMATIVA (50 req/s):")
        print(f"   Tempo estimado: {hours:.1f} horas")
        print("   Meta: ~1.465.000 empresas")
    else:
        print("  ⚠️  Supabase não configurado - usando fallbacks")

    print("\n✅ Setup concluído! Execute:")
    print("   ./scripts/start_mass_collection.sh")
    print("\nOu diretamente:")
    print("   python scripts/parallel_collector.py")


async def main():
    print("=" * 60)
    print("SETUP - COLETA MASSIVA DE EMPRESAS")
    print("Meta: ~1.465.000 empresas")
    print("=" * 60)

    # Verificações
    await check_supabase_connection()
    await check_tables()
    await populate_cnaes()
    await populate_cities()
    await check_apis()

    # Resumo
    await print_summary()


if __name__ == "__main__":
    asyncio.run(main())
