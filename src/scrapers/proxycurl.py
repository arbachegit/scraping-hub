"""
Proxycurl Client
Cliente para API do Proxycurl - dados de LinkedIn
"""

from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings

from .base import BaseScraper

logger = structlog.get_logger()


class ProxycurlClient(BaseScraper):
    """
    Cliente para API Proxycurl

    Endpoints principais:
    - /linkedin/person - Perfil de pessoa
    - /linkedin/company - Perfil de empresa
    - /linkedin/company/employees - Funcionarios
    - /linkedin/school - Perfil de escola
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(
            api_key=api_key or settings.proxycurl_api_key,
            base_url=base_url or settings.proxycurl_base_url,
            rate_limit=settings.proxycurl_rate_limit
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ===========================================
    # PERSON PROFILE
    # ===========================================

    async def get_person_profile(
        self,
        linkedin_url: str,
        extra: Optional[str] = None,
        skills: bool = True,
        inferred_salary: bool = False,
        personal_email: bool = False,
        personal_contact_number: bool = False
    ) -> Dict[str, Any]:
        """
        Obtem perfil completo de uma pessoa no LinkedIn

        Args:
            linkedin_url: URL do perfil LinkedIn
            extra: Campos extras (include ou exclude)
            skills: Incluir skills
            inferred_salary: Incluir salario inferido
            personal_email: Incluir email pessoal
            personal_contact_number: Incluir telefone pessoal

        Returns:
            Dados do perfil
        """
        logger.info("proxycurl_get_person", url=linkedin_url)

        params = {
            "url": linkedin_url,
            "skills": "include" if skills else "exclude",
            "inferred_salary": "include" if inferred_salary else "exclude",
            "personal_email": "include" if personal_email else "exclude",
            "personal_contact_number": "include" if personal_contact_number else "exclude"
        }

        if extra:
            params["extra"] = extra

        return await self.get("/linkedin/person", params=params)

    async def lookup_person(
        self,
        first_name: str,
        last_name: str,
        company_domain: Optional[str] = None,
        location: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca pessoa no LinkedIn por nome e outros criterios

        Args:
            first_name: Primeiro nome
            last_name: Sobrenome
            company_domain: Dominio da empresa
            location: Localizacao
            title: Cargo

        Returns:
            Dados do perfil encontrado
        """
        logger.info(
            "proxycurl_lookup_person",
            first_name=first_name,
            last_name=last_name
        )

        params = {
            "first_name": first_name,
            "last_name": last_name
        }

        if company_domain:
            params["company_domain"] = company_domain
        if location:
            params["location"] = location
        if title:
            params["title"] = title

        return await self.get("/linkedin/person/lookup", params=params)

    # ===========================================
    # COMPANY PROFILE
    # ===========================================

    async def get_company_profile(
        self,
        linkedin_url: str,
        resolve_numeric_id: bool = False,
        categories: bool = True,
        funding_data: bool = True,
        extra: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtem perfil completo de uma empresa no LinkedIn

        Args:
            linkedin_url: URL do perfil da empresa
            resolve_numeric_id: Resolver ID numerico
            categories: Incluir categorias
            funding_data: Incluir dados de funding
            extra: Campos extras

        Returns:
            Dados da empresa
        """
        logger.info("proxycurl_get_company", url=linkedin_url)

        params = {
            "url": linkedin_url,
            "resolve_numeric_id": str(resolve_numeric_id).lower(),
            "categories": "include" if categories else "exclude",
            "funding_data": "include" if funding_data else "exclude"
        }

        if extra:
            params["extra"] = extra

        return await self.get("/linkedin/company", params=params)

    async def lookup_company(
        self,
        company_domain: Optional[str] = None,
        company_name: Optional[str] = None,
        company_location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca empresa no LinkedIn por dominio ou nome

        Args:
            company_domain: Dominio da empresa
            company_name: Nome da empresa
            company_location: Localizacao

        Returns:
            Dados da empresa encontrada
        """
        logger.info(
            "proxycurl_lookup_company",
            domain=company_domain,
            name=company_name
        )

        params = {}

        if company_domain:
            params["company_domain"] = company_domain
        if company_name:
            params["company_name"] = company_name
        if company_location:
            params["company_location"] = company_location

        return await self.get("/linkedin/company/lookup", params=params)

    # ===========================================
    # EMPLOYEES
    # ===========================================

    async def get_company_employees(
        self,
        linkedin_url: str,
        page_size: int = 10,
        employment_status: str = "current",
        resolve_numeric_id: bool = False
    ) -> Dict[str, Any]:
        """
        Lista funcionarios de uma empresa

        Args:
            linkedin_url: URL da empresa no LinkedIn
            page_size: Tamanho da pagina
            employment_status: current, past, ou all
            resolve_numeric_id: Resolver IDs numericos

        Returns:
            Lista de funcionarios com total e paginacao
        """
        logger.info(
            "proxycurl_get_employees",
            url=linkedin_url,
            status=employment_status
        )

        params = {
            "url": linkedin_url,
            "page_size": page_size,
            "employment_status": employment_status,
            "resolve_numeric_id": str(resolve_numeric_id).lower()
        }

        return await self.get("/linkedin/company/employees", params=params)

    async def search_employees(
        self,
        linkedin_url: str,
        keyword_regex: Optional[str] = None,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Busca funcionarios por keyword

        Args:
            linkedin_url: URL da empresa
            keyword_regex: Regex para buscar em cargos
            page_size: Tamanho da pagina

        Returns:
            Funcionarios que correspondem ao filtro
        """
        logger.info(
            "proxycurl_search_employees",
            url=linkedin_url,
            keyword=keyword_regex
        )

        params = {
            "url": linkedin_url,
            "page_size": page_size
        }

        if keyword_regex:
            params["keyword_regex"] = keyword_regex

        return await self.get("/linkedin/company/employee/search", params=params)

    # ===========================================
    # JOB LISTINGS
    # ===========================================

    async def get_company_jobs(
        self,
        linkedin_url: str
    ) -> List[Dict[str, Any]]:
        """
        Lista vagas de uma empresa

        Args:
            linkedin_url: URL da empresa no LinkedIn

        Returns:
            Lista de vagas abertas
        """
        logger.info("proxycurl_get_jobs", url=linkedin_url)

        response = await self.get(
            "/linkedin/company/jobs",
            params={"url": linkedin_url}
        )

        return response.get("jobs", [])

    # ===========================================
    # ENRICHMENT
    # ===========================================

    async def enrich_person(
        self,
        linkedin_url: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enriquece dados de pessoa com multiplas tentativas

        Args:
            linkedin_url: URL do LinkedIn (preferencial)
            first_name: Primeiro nome
            last_name: Sobrenome
            company_domain: Dominio da empresa

        Returns:
            Dados enriquecidos
        """
        # Tentar por URL primeiro
        if linkedin_url:
            return await self.get_person_profile(linkedin_url)

        # Tentar lookup por nome
        if first_name and last_name:
            result = await self.lookup_person(
                first_name=first_name,
                last_name=last_name,
                company_domain=company_domain
            )

            url = result.get("linkedin_profile_url")
            if url:
                return await self.get_person_profile(url)

        return {}

    async def enrich_company(
        self,
        linkedin_url: Optional[str] = None,
        domain: Optional[str] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enriquece dados de empresa com multiplas tentativas

        Args:
            linkedin_url: URL do LinkedIn (preferencial)
            domain: Dominio da empresa
            name: Nome da empresa

        Returns:
            Dados enriquecidos
        """
        # Tentar por URL primeiro
        if linkedin_url:
            return await self.get_company_profile(linkedin_url)

        # Tentar lookup
        result = await self.lookup_company(
            company_domain=domain,
            company_name=name
        )

        url = result.get("linkedin_profile_url")
        if url:
            return await self.get_company_profile(url)

        return {}
