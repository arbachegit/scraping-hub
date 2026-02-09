"""
Serper.dev Client
Google Search API para buscas no Brasil
https://serper.dev/
"""

import re
from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings

from .base import BaseScraper

logger = structlog.get_logger()


class SerperClient(BaseScraper):
    """
    Cliente para Serper.dev - Google Search API

    Funcionalidades:
    - Busca Google padrão
    - Busca de imagens
    - Busca de notícias
    - Busca de lugares
    - Autocomplete
    """

    # Metadados da fonte para rastreabilidade (CLAUDE.md)
    SOURCE_NAME = "Serper - Google Search"
    SOURCE_PROVIDER = "Serper.dev"
    SOURCE_CATEGORY = "api"
    SOURCE_COVERAGE = "Resultados de busca Google, notícias, imagens"
    SOURCE_DOC_URL = "https://serper.dev/docs"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        super().__init__(
            api_key=api_key or settings.serper_api_key,
            base_url="https://google.serper.dev",
            rate_limit=100,
            timeout=timeout
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

    async def search(
        self,
        query: str,
        num: int = 10,
        gl: str = "br",
        hl: str = "pt-br",
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Busca Google padrão

        Args:
            query: Termo de busca
            num: Número de resultados (max 100)
            gl: País (br = Brasil)
            hl: Idioma (pt-br = Português Brasil)
            page: Página de resultados

        Returns:
            Resultados da busca
        """
        logger.info("serper_search", query=query[:50])

        result = await self.post("/search", json={
            "q": query,
            "num": min(num, 100),
            "gl": gl,
            "hl": hl,
            "page": page
        })

        return {
            "query": query,
            "organic": result.get("organic", []),
            "knowledge_graph": result.get("knowledgeGraph"),
            "answer_box": result.get("answerBox"),
            "related_searches": result.get("relatedSearches", []),
            "people_also_ask": result.get("peopleAlsoAsk", []),
            "total_results": len(result.get("organic", []))
        }

    async def search_news(
        self,
        query: str,
        num: int = 10,
        gl: str = "br",
        hl: str = "pt-br",
        tbs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca de notícias

        Args:
            query: Termo de busca
            num: Número de resultados
            gl: País
            hl: Idioma
            tbs: Filtro de tempo (qdr:d = último dia, qdr:w = última semana, qdr:m = último mês)

        Returns:
            Notícias encontradas
        """
        logger.info("serper_news", query=query[:50])

        payload = {
            "q": query,
            "num": min(num, 100),
            "gl": gl,
            "hl": hl
        }
        if tbs:
            payload["tbs"] = tbs

        result = await self.post("/news", json=payload)

        return {
            "query": query,
            "news": result.get("news", []),
            "total_results": len(result.get("news", []))
        }

    async def search_images(
        self,
        query: str,
        num: int = 10,
        gl: str = "br"
    ) -> Dict[str, Any]:
        """Busca de imagens"""
        logger.info("serper_images", query=query[:50])

        result = await self.post("/images", json={
            "q": query,
            "num": min(num, 100),
            "gl": gl
        })

        return {
            "query": query,
            "images": result.get("images", []),
            "total_results": len(result.get("images", []))
        }

    async def search_places(
        self,
        query: str,
        location: str = "Brazil",
        gl: str = "br"
    ) -> Dict[str, Any]:
        """Busca de lugares (Google Maps)"""
        logger.info("serper_places", query=query[:50])

        result = await self.post("/places", json={
            "q": query,
            "location": location,
            "gl": gl
        })

        return {
            "query": query,
            "places": result.get("places", []),
            "total_results": len(result.get("places", []))
        }

    async def autocomplete(
        self,
        query: str,
        gl: str = "br",
        hl: str = "pt-br"
    ) -> List[str]:
        """Google Autocomplete"""
        result = await self.post("/autocomplete", json={
            "q": query,
            "gl": gl,
            "hl": hl
        })

        return result.get("suggestions", [])

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA EMPRESAS
    # ===========================================

    async def find_company_cnpj(self, company_name: str) -> Optional[str]:
        """
        Busca CNPJ de uma empresa pelo nome

        Args:
            company_name: Nome da empresa

        Returns:
            CNPJ encontrado ou None
        """
        query = f'"{company_name}" CNPJ site:cnpj.info OR site:consultacnpj.com OR site:empresascnpj.com'
        results = await self.search(query, num=5)

        # Regex para CNPJ
        cnpj_pattern = r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}'

        for item in results.get("organic", []):
            # Buscar no título e snippet
            text = f"{item.get('title', '')} {item.get('snippet', '')}"
            match = re.search(cnpj_pattern, text)
            if match:
                cnpj = "".join(filter(str.isdigit, match.group()))
                logger.info("cnpj_found", company=company_name, cnpj=cnpj[:8] + "****")
                return cnpj

        # Tentar no knowledge graph
        kg = results.get("knowledge_graph", {})
        if kg:
            for key in ["cnpj", "CNPJ", "registration"]:
                if key in kg:
                    cnpj = "".join(filter(str.isdigit, str(kg[key])))
                    if len(cnpj) == 14:
                        return cnpj

        return None

    async def find_company_website(self, company_name: str) -> Optional[str]:
        """
        Busca o website oficial de uma empresa

        Args:
            company_name: Nome da empresa

        Returns:
            URL do website ou None
        """
        query = f'"{company_name}" site oficial'
        results = await self.search(query, num=5)

        for item in results.get("organic", []):
            url = item.get("link", "")
            # Filtrar sites de consulta e priorizar domínios próprios
            if not any(x in url for x in [
                "cnpj.info", "consultacnpj", "empresascnpj",
                "linkedin.com", "facebook.com", "instagram.com",
                "wikipedia.org", "reclameaqui.com"
            ]):
                return url

        return None

    async def find_company_linkedin(self, company_name: str) -> Optional[str]:
        """
        Busca o perfil LinkedIn de uma empresa

        Args:
            company_name: Nome da empresa

        Returns:
            URL do LinkedIn ou None
        """
        query = f'"{company_name}" site:linkedin.com/company'
        results = await self.search(query, num=3)

        for item in results.get("organic", []):
            url = item.get("link", "")
            if "linkedin.com/company" in url:
                return url

        return None

    async def find_company_info(self, company_name: str) -> Dict[str, Any]:
        """
        Busca informações completas sobre uma empresa

        Args:
            company_name: Nome da empresa

        Returns:
            Dicionário com informações encontradas
        """
        logger.info("serper_company_info", company=company_name)

        # Busca principal
        main_results = await self.search(f'"{company_name}" empresa Brasil', num=10)

        # Busca de notícias
        news_results = await self.search_news(f'"{company_name}"', num=5)

        # Extrair knowledge graph se disponível
        kg = main_results.get("knowledge_graph", {})

        return {
            "company_name": company_name,
            "search_results": main_results.get("organic", []),
            "knowledge_graph": kg,
            "news": news_results.get("news", []),
            "website": kg.get("website") or await self.find_company_website(company_name),
            "description": kg.get("description"),
            "industry": kg.get("industry") or kg.get("type"),
            "founded": kg.get("founded") or kg.get("foundingDate"),
            "headquarters": kg.get("headquarters") or kg.get("address"),
            "employees": kg.get("employees") or kg.get("numberOfEmployees"),
            "related_searches": main_results.get("related_searches", [])
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA PESSOAS
    # ===========================================

    async def find_person_linkedin(self, name: str, company: Optional[str] = None) -> Optional[str]:
        """
        Busca o perfil LinkedIn de uma pessoa

        Args:
            name: Nome da pessoa
            company: Empresa (opcional, melhora precisão)

        Returns:
            URL do LinkedIn ou None
        """
        query = f'"{name}" site:linkedin.com/in'
        if company:
            query += f' "{company}"'

        results = await self.search(query, num=5)

        for item in results.get("organic", []):
            url = item.get("link", "")
            if "linkedin.com/in/" in url:
                return url

        return None

    async def find_person_info(
        self,
        name: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca informações sobre uma pessoa

        Args:
            name: Nome da pessoa
            context: Contexto adicional (empresa, cargo, cidade)

        Returns:
            Informações encontradas
        """
        query = f'"{name}"'
        if context:
            query += f' {context}'

        results = await self.search(query, num=10)
        news = await self.search_news(f'"{name}"', num=5)

        return {
            "name": name,
            "search_results": results.get("organic", []),
            "knowledge_graph": results.get("knowledge_graph"),
            "news": news.get("news", []),
            "linkedin": await self.find_person_linkedin(name),
            "people_also_ask": results.get("people_also_ask", [])
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA POLÍTICOS
    # ===========================================

    async def find_politician_info(
        self,
        name: str,
        role: Optional[str] = None,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca informações sobre um político

        Args:
            name: Nome do político
            role: Cargo (prefeito, senador, deputado, etc)
            state: Estado (UF)

        Returns:
            Informações encontradas
        """
        query_parts = [f'"{name}"']
        if role:
            query_parts.append(role)
        if state:
            query_parts.append(state)
        query_parts.append("político")

        query = " ".join(query_parts)

        results = await self.search(query, num=15)
        news = await self.search_news(f'"{name}" político', num=10)

        # Busca específica em sites de transparência
        gov_query = f'"{name}" site:gov.br OR site:camara.leg.br OR site:senado.leg.br'
        gov_results = await self.search(gov_query, num=5)

        return {
            "name": name,
            "role": role,
            "state": state,
            "search_results": results.get("organic", []),
            "knowledge_graph": results.get("knowledge_graph"),
            "news": news.get("news", []),
            "gov_results": gov_results.get("organic", []),
            "social_media": {
                "instagram": await self._find_social(name, "instagram.com"),
                "twitter": await self._find_social(name, "twitter.com"),
                "facebook": await self._find_social(name, "facebook.com")
            }
        }

    async def _find_social(self, name: str, domain: str) -> Optional[str]:
        """Busca perfil em rede social"""
        query = f'"{name}" site:{domain}'
        results = await self.search(query, num=1)

        organic = results.get("organic", [])
        if organic:
            return organic[0].get("link")
        return None
