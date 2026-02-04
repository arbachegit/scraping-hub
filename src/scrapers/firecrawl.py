"""
Firecrawl Client
Cliente para API do Firecrawl - web scraping estruturado
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings

from .base import BaseScraper

logger = structlog.get_logger()


class FirecrawlClient(BaseScraper):
    """
    Cliente para API Firecrawl

    Endpoints principais:
    - /scrape - Scrape de uma pagina
    - /crawl - Crawl de um site
    - /map - Mapear URLs de um site
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(
            api_key=api_key or settings.firecrawl_api_key,
            base_url=base_url or settings.firecrawl_base_url,
            rate_limit=settings.firecrawl_rate_limit
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ===========================================
    # SCRAPE
    # ===========================================

    async def scrape_url(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        only_main_content: bool = True,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        wait_for: Optional[str] = None,
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Scrape de uma pagina web

        Args:
            url: URL para fazer scrape
            formats: Formatos de saida (markdown, html, rawHtml, links, screenshot)
            only_main_content: Extrair apenas conteudo principal
            include_tags: Tags HTML para incluir
            exclude_tags: Tags HTML para excluir
            wait_for: Seletor CSS para aguardar antes de scrape
            timeout: Timeout em ms

        Returns:
            Conteudo scraped nos formatos solicitados
        """
        logger.info("firecrawl_scrape", url=url, formats=formats)

        payload = {
            "url": url,
            "formats": formats or ["markdown"],
            "onlyMainContent": only_main_content,
            "timeout": timeout
        }

        if include_tags:
            payload["includeTags"] = include_tags
        if exclude_tags:
            payload["excludeTags"] = exclude_tags
        if wait_for:
            payload["waitFor"] = wait_for

        response = await self.post("/v1/scrape", json=payload)

        return response.get("data", {})

    async def scrape_with_extraction(
        self,
        url: str,
        schema: Dict[str, Any],
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape com extracao estruturada usando LLM

        Args:
            url: URL para fazer scrape
            schema: Schema JSON dos dados a extrair
            prompt: Prompt adicional para extracao

        Returns:
            Dados extraidos conforme o schema
        """
        logger.info("firecrawl_extract", url=url)

        payload = {
            "url": url,
            "formats": ["extract"],
            "extract": {
                "schema": schema
            }
        }

        if prompt:
            payload["extract"]["prompt"] = prompt

        response = await self.post("/v1/scrape", json=payload)

        return response.get("data", {}).get("extract", {})

    # ===========================================
    # CRAWL
    # ===========================================

    async def crawl_site(
        self,
        url: str,
        max_depth: int = 2,
        limit: int = 100,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        allow_backward_links: bool = False,
        allow_external_links: bool = False,
        ignore_sitemap: bool = False
    ) -> Dict[str, Any]:
        """
        Inicia crawl de um site

        Args:
            url: URL inicial do crawl
            max_depth: Profundidade maxima de links
            limit: Numero maximo de paginas
            include_paths: Paths a incluir (glob patterns)
            exclude_paths: Paths a excluir (glob patterns)
            allow_backward_links: Permitir links para paginas anteriores
            allow_external_links: Permitir links externos
            ignore_sitemap: Ignorar sitemap.xml

        Returns:
            ID do job de crawl
        """
        logger.info(
            "firecrawl_crawl_start",
            url=url,
            max_depth=max_depth,
            limit=limit
        )

        payload = {
            "url": url,
            "maxDepth": max_depth,
            "limit": limit,
            "allowBackwardLinks": allow_backward_links,
            "allowExternalLinks": allow_external_links,
            "ignoreSitemap": ignore_sitemap
        }

        if include_paths:
            payload["includePaths"] = include_paths
        if exclude_paths:
            payload["excludePaths"] = exclude_paths

        response = await self.post("/v1/crawl", json=payload)

        return response

    async def get_crawl_status(self, crawl_id: str) -> Dict[str, Any]:
        """
        Verifica status de um crawl

        Args:
            crawl_id: ID do job de crawl

        Returns:
            Status e dados do crawl
        """
        return await self.get(f"/v1/crawl/{crawl_id}")

    async def crawl_and_wait(
        self,
        url: str,
        max_depth: int = 2,
        limit: int = 100,
        poll_interval: int = 5,
        max_wait: int = 300,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Executa crawl e aguarda conclusao

        Args:
            url: URL inicial
            max_depth: Profundidade maxima
            limit: Limite de paginas
            poll_interval: Intervalo de polling em segundos
            max_wait: Tempo maximo de espera em segundos
            **kwargs: Argumentos adicionais para crawl_site

        Returns:
            Lista de paginas crawled
        """
        # Iniciar crawl
        result = await self.crawl_site(
            url=url,
            max_depth=max_depth,
            limit=limit,
            **kwargs
        )

        crawl_id = result.get("id")
        if not crawl_id:
            raise ValueError("Crawl ID not returned")

        logger.info("firecrawl_crawl_waiting", crawl_id=crawl_id)

        # Aguardar conclusao
        elapsed = 0
        while elapsed < max_wait:
            status = await self.get_crawl_status(crawl_id)

            if status.get("status") == "completed":
                return status.get("data", [])

            if status.get("status") == "failed":
                raise Exception(f"Crawl failed: {status.get('error')}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Crawl timed out after {max_wait} seconds")

    # ===========================================
    # MAP
    # ===========================================

    async def map_site(
        self,
        url: str,
        search: Optional[str] = None,
        ignore_sitemap: bool = False,
        include_subdomains: bool = False,
        limit: int = 5000
    ) -> List[str]:
        """
        Mapeia todas as URLs de um site

        Args:
            url: URL do site
            search: Filtro de busca nas URLs
            ignore_sitemap: Ignorar sitemap
            include_subdomains: Incluir subdominios
            limit: Limite de URLs

        Returns:
            Lista de URLs mapeadas
        """
        logger.info("firecrawl_map", url=url, limit=limit)

        payload = {
            "url": url,
            "ignoreSitemap": ignore_sitemap,
            "includeSubdomains": include_subdomains,
            "limit": limit
        }

        if search:
            payload["search"] = search

        response = await self.post("/v1/map", json=payload)

        return response.get("links", [])

    # ===========================================
    # UTILITY METHODS
    # ===========================================

    async def scrape_multiple(
        self,
        urls: List[str],
        formats: Optional[List[str]] = None,
        concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scrape de multiplas URLs com concorrencia controlada

        Args:
            urls: Lista de URLs
            formats: Formatos de saida
            concurrency: Numero de requests paralelos

        Returns:
            Lista de resultados de scrape
        """
        logger.info(
            "firecrawl_scrape_multiple",
            count=len(urls),
            concurrency=concurrency
        )

        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def scrape_with_semaphore(url: str):
            async with semaphore:
                try:
                    return await self.scrape_url(url, formats=formats)
                except Exception as e:
                    logger.error("scrape_failed", url=url, error=str(e))
                    return {"url": url, "error": str(e)}

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)

        return results

    async def extract_table_data(
        self,
        url: str,
        table_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrai dados de tabelas HTML

        Args:
            url: URL da pagina
            table_selector: Seletor CSS da tabela

        Returns:
            Lista de linhas da tabela como dicionarios
        """
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True
            }
        }

        prompt = "Extract all rows from the table as JSON objects."
        if table_selector:
            prompt += f" Focus on the table matching selector: {table_selector}"

        return await self.scrape_with_extraction(
            url=url,
            schema=schema,
            prompt=prompt
        )
