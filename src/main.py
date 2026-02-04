"""
Scraping Hub - Main Entry Point
Ponto de entrada principal do sistema
"""

import asyncio
import structlog
from typing import Optional

from config.settings import settings
from src.scrapers import CoresignalClient, ProxycurlClient, FirecrawlClient
from src.services import EmpresaService, LinkedInService, GovernoService


# Configurar logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.log_level.upper(), structlog.INFO)
    ),
)

logger = structlog.get_logger()


async def demo_empresa_enrichment():
    """Demonstracao de enriquecimento de empresa"""
    logger.info("demo_empresa_start")

    async with EmpresaService() as service:
        empresa = await service.enrich_company(
            name="Iconsai",
            website="https://iconsai.ai",
            sources=["coresignal", "proxycurl"]
        )

        logger.info(
            "demo_empresa_result",
            nome=empresa.nome_fantasia,
            setor=empresa.setor,
            funcionarios=empresa.num_funcionarios,
            fontes=empresa.fontes
        )

        return empresa


async def demo_linkedin_profile():
    """Demonstracao de perfil LinkedIn"""
    logger.info("demo_linkedin_start")

    async with LinkedInService() as service:
        # Buscar profissionais
        profissionais = await service.search_professionals(
            title="CEO",
            location="Brazil",
            limit=5
        )

        logger.info(
            "demo_linkedin_result",
            count=len(profissionais)
        )

        return profissionais


async def demo_governo_scrape():
    """Demonstracao de scraping de governo"""
    logger.info("demo_governo_start")

    async with GovernoService() as service:
        # Mapear URLs do portal de transparencia
        urls = await service.map_portal_urls(
            url="https://portaldatransparencia.gov.br",
            search_term="licitacao"
        )

        logger.info(
            "demo_governo_result",
            urls_found=len(urls)
        )

        return urls


async def health_check() -> dict:
    """Verifica saude dos servicos"""
    status = {
        "status": "healthy",
        "services": {}
    }

    # Verificar configs
    services_config = [
        ("coresignal", bool(settings.coresignal_api_key)),
        ("proxycurl", bool(settings.proxycurl_api_key)),
        ("firecrawl", bool(settings.firecrawl_api_key)),
        ("supabase", bool(settings.supabase_url and settings.supabase_service_key))
    ]

    for service, configured in services_config:
        status["services"][service] = {
            "configured": configured,
            "status": "ready" if configured else "not_configured"
        }

    # Status geral
    configured_count = sum(1 for _, c in services_config if c)
    if configured_count == 0:
        status["status"] = "not_configured"
    elif configured_count < len(services_config):
        status["status"] = "partially_configured"

    return status


async def main():
    """Funcao principal"""
    logger.info(
        "scraping_hub_start",
        environment=settings.environment,
        version="0.1.0"
    )

    # Health check
    health = await health_check()
    logger.info("health_check", **health)

    if health["status"] == "not_configured":
        logger.warning(
            "services_not_configured",
            message="Configure API keys in .env file"
        )
        return

    # Executar demos se em desenvolvimento
    if settings.environment == "development":
        logger.info("running_demos")

        # Apenas roda demos se as chaves estiverem configuradas
        if health["services"]["coresignal"]["configured"]:
            await demo_empresa_enrichment()

        if health["services"]["proxycurl"]["configured"]:
            await demo_linkedin_profile()

        if health["services"]["firecrawl"]["configured"]:
            await demo_governo_scrape()

    logger.info("scraping_hub_ready")


if __name__ == "__main__":
    asyncio.run(main())
