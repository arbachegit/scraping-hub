"""
Coresignal Client
Cliente para API do Coresignal - dados de empresas e profissionais
"""

import structlog
from typing import Any, Dict, List, Optional

from .base import BaseScraper
from config.settings import settings


logger = structlog.get_logger()


class CoresignalClient(BaseScraper):
    """
    Cliente para API Coresignal

    Endpoints principais:
    - /companies/search - Buscar empresas
    - /companies/{id} - Detalhes de empresa
    - /members/search - Buscar profissionais
    - /members/{id} - Detalhes de profissional
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(
            api_key=api_key or settings.coresignal_api_key,
            base_url=base_url or settings.coresignal_base_url,
            rate_limit=settings.coresignal_rate_limit
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    # ===========================================
    # COMPANIES
    # ===========================================

    async def search_companies(
        self,
        name: Optional[str] = None,
        website: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        size: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca empresas por varios criterios

        Args:
            name: Nome da empresa
            website: Website da empresa
            industry: Setor de atuacao
            country: Pais (codigo ISO ou nome)
            size: Tamanho (1-10, 11-50, 51-200, etc)
            limit: Numero maximo de resultados

        Returns:
            Lista de empresas encontradas
        """
        filters = {}

        if name:
            filters["name"] = name
        if website:
            filters["website"] = website
        if industry:
            filters["industry"] = industry
        if country:
            filters["country"] = country
        if size:
            filters["size"] = size

        logger.info("coresignal_search_companies", filters=filters, limit=limit)

        response = await self.post(
            "/companies/search",
            json={
                "filters": filters,
                "limit": limit
            }
        )

        return response.get("data", [])

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Obtem detalhes completos de uma empresa

        Args:
            company_id: ID da empresa no Coresignal

        Returns:
            Dados completos da empresa
        """
        logger.info("coresignal_get_company", company_id=company_id)
        return await self.get(f"/companies/{company_id}")

    async def get_company_by_linkedin(
        self,
        linkedin_url: str
    ) -> Dict[str, Any]:
        """
        Busca empresa pelo URL do LinkedIn

        Args:
            linkedin_url: URL do LinkedIn da empresa

        Returns:
            Dados da empresa
        """
        logger.info("coresignal_get_company_linkedin", url=linkedin_url)

        response = await self.post(
            "/companies/search",
            json={
                "filters": {"linkedin_url": linkedin_url},
                "limit": 1
            }
        )

        companies = response.get("data", [])
        if companies:
            return companies[0]
        return {}

    async def get_company_employees(
        self,
        company_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lista funcionarios de uma empresa

        Args:
            company_id: ID da empresa
            limit: Numero maximo de resultados
            offset: Offset para paginacao

        Returns:
            Lista de funcionarios
        """
        logger.info(
            "coresignal_get_employees",
            company_id=company_id,
            limit=limit
        )

        response = await self.post(
            "/members/search",
            json={
                "filters": {"company_id": company_id},
                "limit": limit,
                "offset": offset
            }
        )

        return response.get("data", [])

    # ===========================================
    # MEMBERS (Profissionais)
    # ===========================================

    async def search_members(
        self,
        name: Optional[str] = None,
        title: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca profissionais por varios criterios

        Args:
            name: Nome do profissional
            title: Cargo atual
            company: Empresa atual
            location: Localizacao
            skills: Lista de habilidades
            limit: Numero maximo de resultados

        Returns:
            Lista de profissionais encontrados
        """
        filters = {}

        if name:
            filters["name"] = name
        if title:
            filters["title"] = title
        if company:
            filters["company"] = company
        if location:
            filters["location"] = location
        if skills:
            filters["skills"] = skills

        logger.info("coresignal_search_members", filters=filters, limit=limit)

        response = await self.post(
            "/members/search",
            json={
                "filters": filters,
                "limit": limit
            }
        )

        return response.get("data", [])

    async def get_member(self, member_id: str) -> Dict[str, Any]:
        """
        Obtem detalhes de um profissional

        Args:
            member_id: ID do profissional no Coresignal

        Returns:
            Dados completos do profissional
        """
        logger.info("coresignal_get_member", member_id=member_id)
        return await self.get(f"/members/{member_id}")

    async def get_member_by_linkedin(
        self,
        linkedin_url: str
    ) -> Dict[str, Any]:
        """
        Busca profissional pelo URL do LinkedIn

        Args:
            linkedin_url: URL do perfil LinkedIn

        Returns:
            Dados do profissional
        """
        logger.info("coresignal_get_member_linkedin", url=linkedin_url)

        response = await self.post(
            "/members/search",
            json={
                "filters": {"linkedin_url": linkedin_url},
                "limit": 1
            }
        )

        members = response.get("data", [])
        if members:
            return members[0]
        return {}

    # ===========================================
    # ENRICHMENT
    # ===========================================

    async def enrich_company(
        self,
        name: Optional[str] = None,
        website: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enriquece dados de empresa com multiplas fontes

        Args:
            name: Nome da empresa
            website: Website
            linkedin_url: URL do LinkedIn

        Returns:
            Dados enriquecidos da empresa
        """
        # Tentar por LinkedIn primeiro
        if linkedin_url:
            result = await self.get_company_by_linkedin(linkedin_url)
            if result:
                return result

        # Tentar por website/nome
        companies = await self.search_companies(
            name=name,
            website=website,
            limit=1
        )

        if companies:
            # Buscar dados completos
            company_id = companies[0].get("id")
            if company_id:
                return await self.get_company(company_id)
            return companies[0]

        return {}
