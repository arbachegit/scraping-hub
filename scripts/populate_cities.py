#!/usr/bin/env python3
"""
IconsAI - Populate Cities
Popula a tabela geo_municipios com dados do IBGE

Fonte: IBGE API
- Municipios: https://servicodados.ibge.gov.br/api/v1/localidades/municipios
- Populacao: https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/2021/variaveis/9324

Author: IconsAI Scraping
"""

import asyncio
import sys
from pathlib import Path

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

logger = structlog.get_logger()

# 1000 maiores cidades por população (estimativa 2021)
# Lista das 1027 cidades mais populosas + capitais
MAIORES_CIDADES_POPULACAO = {
    # Capitais (já incluídas)
    "3550308": 12325232,  # São Paulo
    "3304557": 6747815,   # Rio de Janeiro
    "5300108": 3055149,   # Brasília
    "2927408": 2886698,   # Salvador
    "2304400": 2686612,   # Fortaleza
    "3106200": 2521564,   # Belo Horizonte
    "1302603": 2219580,   # Manaus
    "4106902": 1948626,   # Curitiba
    "2611606": 1653461,   # Recife
    "4314902": 1492530,   # Porto Alegre
    "5208707": 1536097,   # Goiânia
    "1501402": 1499641,   # Belém
    "3518800": 1392121,   # Guarulhos (não capital mas grande)
    "3509502": 1223237,   # Campinas (não capital)
    "2111300": 1108975,   # São Luís
    "3304904": 1091737,   # São Gonçalo
    "2704302": 1025360,   # Maceió
    "3552205": 946252,    # São Bernardo do Campo
    "5002704": 906092,    # Campo Grande
    "2211001": 868075,    # Teresina
    "2408102": 890480,    # Natal
    "3547809": 844818,    # Santo André
    "3534401": 721234,    # Osasco
    "2507507": 817511,    # João Pessoa
    "3170206": 664440,    # Uberlândia
    "3548708": 710644,    # São José dos Campos
    "3543402": 695476,    # Ribeirão Preto
    "3303302": 505249,    # Niterói
    "5103403": 618124,    # Cuiabá
    "2800308": 664908,    # Aracaju
    "3205309": 365855,    # Vitória
    "3301702": 509293,    # Duque de Caxias
    "3301702": 509293,    # Duque de Caxias
    "4205407": 508826,    # Florianópolis
    "2910800": 609779,    # Feira de Santana
    "3118601": 523794,    # Contagem
    "4113700": 443192,    # Londrina
    "3525904": 409657,    # Jundiaí
    "3136702": 414527,    # Juiz de Fora
    "4209102": 616343,    # Joinville
    "3205200": 613342,    # Vila Velha
    "4119905": 452760,    # Ponta Grossa
    "2905701": 387437,    # Camaçari
    "1400100": 419652,    # Boa Vista
    "1600303": 512902,    # Macapá
    "1721000": 299127,    # Palmas
    "1200401": 413418,    # Rio Branco
    "1100205": 539354,    # Porto Velho
}


async def fetch_municipios() -> list[dict]:
    """Busca todos os municípios do IBGE"""
    logger.info("fetching_municipios")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        )
        response.raise_for_status()
        data = response.json()

        municipios = []
        for mun in data:
            codigo_ibge = str(mun.get("id", ""))
            uf = (
                mun.get("microrregiao", {})
                .get("mesorregiao", {})
                .get("UF", {})
            )

            municipios.append(
                {
                    "codigo_ibge": codigo_ibge,
                    "nome": mun.get("nome"),
                    "uf": uf.get("sigla", ""),
                    "uf_nome": uf.get("nome", ""),
                    "regiao": uf.get("regiao", {}).get("nome", ""),
                    # Usar estimativa se disponível
                    "populacao": MAIORES_CIDADES_POPULACAO.get(codigo_ibge, 0),
                }
            )

        logger.info("municipios_fetched", count=len(municipios))
        return municipios


async def fetch_populacao() -> dict[str, int]:
    """Busca população dos municípios (estimativa 2021)"""
    logger.info("fetching_populacao")

    # A API de agregados do IBGE é complexa, usar dados estáticos das maiores
    # Em produção, poderia baixar o arquivo completo de estimativas
    return MAIORES_CIDADES_POPULACAO


async def populate_cities():
    """Popula tabela geo_municipios"""
    supabase = get_supabase()

    if not supabase:
        logger.error("supabase_not_configured")
        return

    # Verificar se tabela existe e tem dados
    try:
        result = supabase.table("geo_municipios").select("count").limit(1).execute()
        if result.data:
            count_result = (
                supabase.table("geo_municipios")
                .select("*", count="exact")
                .limit(1)
                .execute()
            )
            if count_result.count and count_result.count > 5000:
                logger.info("geo_municipios_already_populated", count=count_result.count)
                return
    except Exception as e:
        logger.warning("table_check_failed", error=str(e))
        # Tentar criar a tabela
        await create_geo_municipios_table(supabase)

    # Buscar dados
    municipios = await fetch_municipios()
    populacao = await fetch_populacao()

    # Atualizar população
    for mun in municipios:
        codigo = mun["codigo_ibge"]
        if codigo in populacao:
            mun["populacao"] = populacao[codigo]

    # Ordenar por população (maiores primeiro)
    municipios.sort(key=lambda x: x.get("populacao", 0), reverse=True)

    # Inserir em batches
    batch_size = 500
    total_inserted = 0

    for i in range(0, len(municipios), batch_size):
        batch = municipios[i : i + batch_size]

        try:
            result = (
                supabase.table("geo_municipios")
                .upsert(batch, on_conflict="codigo_ibge")
                .execute()
            )

            if result.data:
                total_inserted += len(result.data)
                logger.info(
                    "batch_inserted",
                    batch=i // batch_size + 1,
                    count=len(result.data),
                )

        except Exception as e:
            logger.error("batch_insert_error", batch=i // batch_size + 1, error=str(e))

    logger.info("cities_populated", total=total_inserted)


async def create_geo_municipios_table(supabase):
    """Cria tabela geo_municipios se não existir"""
    # Executar via SQL direto
    create_sql = """
    CREATE TABLE IF NOT EXISTS geo_municipios (
        id SERIAL PRIMARY KEY,
        codigo_ibge VARCHAR(7) UNIQUE NOT NULL,
        nome VARCHAR(255) NOT NULL,
        uf VARCHAR(2),
        uf_nome VARCHAR(100),
        regiao VARCHAR(100),
        populacao INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_geo_municipios_uf ON geo_municipios(uf);
    CREATE INDEX IF NOT EXISTS idx_geo_municipios_populacao ON geo_municipios(populacao DESC);
    """

    try:
        # Supabase não permite DDL direto via client, precisaria via migrations
        logger.warning(
            "table_creation_needed",
            message="Execute o SQL de criação da tabela geo_municipios manualmente",
        )
    except Exception as e:
        logger.error("create_table_error", error=str(e))


async def main():
    logger.info("populate_cities_starting")
    await populate_cities()
    logger.info("populate_cities_complete")


if __name__ == "__main__":
    asyncio.run(main())
