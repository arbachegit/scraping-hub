"""
Apollo.io Client
B2B data platform para dados de LinkedIn e contatos
https://www.apollo.io/
"""

from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings

from .base import BaseScraper

logger = structlog.get_logger()


class ApolloClient(BaseScraper):
    """
    Cliente para Apollo.io - B2B Intelligence

    Funcionalidades:
    - Busca de pessoas/contatos
    - Busca de empresas
    - Enriquecimento de dados
    - Dados de LinkedIn
    """

    # Metadados da fonte para rastreabilidade (CLAUDE.md)
    SOURCE_NAME = "Apollo - B2B Intelligence"
    SOURCE_PROVIDER = "Apollo.io"
    SOURCE_CATEGORY = "api"
    SOURCE_COVERAGE = "Dados B2B, contatos profissionais, empresas"
    SOURCE_DOC_URL = "https://apolloio.github.io/apollo-api-docs"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        super().__init__(
            api_key=api_key or settings.apollo_api_key,
            base_url="https://api.apollo.io/v1",
            rate_limit=100,
            timeout=timeout
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.api_key  # Apollo agora exige chave no header
        }

    async def _request_with_key(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Request com API key no header (novo padrão Apollo)"""
        if json is None:
            json = {}
        # Removido: json["api_key"] = self.api_key
        # Agora a chave vai no header via _get_headers()

        return await self._request(method, endpoint, params=params, json=json)

    # ===========================================
    # BUSCA DE PESSOAS
    # ===========================================

    async def search_people(
        self,
        q_person_name: Optional[str] = None,
        q_organization_name: Optional[str] = None,
        person_titles: Optional[List[str]] = None,
        person_seniorities: Optional[List[str]] = None,
        organization_locations: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Busca pessoas/contatos

        Args:
            q_person_name: Nome da pessoa
            q_organization_name: Nome da empresa
            person_titles: Lista de cargos
            person_seniorities: Níveis (owner, founder, c_suite, partner, vp, head, director, manager, senior, entry)
            organization_locations: Localizações
            organization_num_employees_ranges: Tamanhos ("1,10", "11,50", "51,200", etc)
            page: Página
            per_page: Resultados por página

        Returns:
            Lista de pessoas encontradas
        """
        logger.info(
            "apollo_search_people",
            name=q_person_name,
            org=q_organization_name
        )

        payload = {
            "page": page,
            "per_page": min(per_page, 100)
        }

        if q_person_name:
            payload["q_person_name"] = q_person_name
        if q_organization_name:
            payload["q_organization_name"] = q_organization_name
        if person_titles:
            payload["person_titles"] = person_titles
        if person_seniorities:
            payload["person_seniorities"] = person_seniorities
        if organization_locations:
            payload["organization_locations"] = organization_locations
        if organization_num_employees_ranges:
            payload["organization_num_employees_ranges"] = organization_num_employees_ranges

        result = await self._request_with_key("POST", "/mixed_people/search", json=payload)

        people = result.get("people", [])
        return {
            "people": [self._normalize_person(p) for p in people],
            "pagination": result.get("pagination", {}),
            "total": result.get("pagination", {}).get("total_entries", 0)
        }

    def _normalize_person(self, data: Dict) -> Dict[str, Any]:
        """Normaliza dados de pessoa"""
        if not data:
            return {}

        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "title": data.get("title"),
            "seniority": data.get("seniority"),
            "departments": data.get("departments", []),

            # Empresa atual
            "company": {
                "name": data.get("organization_name") or data.get("organization", {}).get("name"),
                "website": data.get("organization", {}).get("website_url"),
                "linkedin_url": data.get("organization", {}).get("linkedin_url"),
                "industry": data.get("organization", {}).get("industry"),
                "employee_count": data.get("organization", {}).get("estimated_num_employees")
            },

            # Contato
            "email": data.get("email"),
            "email_status": data.get("email_status"),
            "phone_numbers": data.get("phone_numbers", []),

            # Social
            "linkedin_url": data.get("linkedin_url"),
            "twitter_url": data.get("twitter_url"),
            "facebook_url": data.get("facebook_url"),
            "github_url": data.get("github_url"),

            # Localização
            "city": data.get("city"),
            "state": data.get("state"),
            "country": data.get("country"),

            # Metadados
            "photo_url": data.get("photo_url"),
            "headline": data.get("headline"),

            "raw_data": data
        }

    async def enrich_person(
        self,
        email: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enriquece dados de uma pessoa

        Args:
            email: Email da pessoa
            linkedin_url: URL do LinkedIn
            first_name: Primeiro nome
            last_name: Sobrenome
            organization_name: Nome da empresa
            domain: Domínio da empresa

        Returns:
            Dados enriquecidos
        """
        logger.info("apollo_enrich_person", email=email, linkedin=linkedin_url)

        payload = {}
        if email:
            payload["email"] = email
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if organization_name:
            payload["organization_name"] = organization_name
        if domain:
            payload["domain"] = domain

        result = await self._request_with_key("POST", "/people/match", json=payload)

        person = result.get("person")
        if person:
            return self._normalize_person(person)
        return {}

    # ===========================================
    # BUSCA DE EMPRESAS
    # ===========================================

    async def search_organizations(
        self,
        q_organization_name: Optional[str] = None,
        organization_locations: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        organization_industries: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Busca empresas

        Args:
            q_organization_name: Nome da empresa
            organization_locations: Localizações
            organization_num_employees_ranges: Tamanhos
            organization_industries: Setores
            page: Página
            per_page: Resultados por página

        Returns:
            Lista de empresas
        """
        logger.info("apollo_search_organizations", name=q_organization_name)

        payload = {
            "page": page,
            "per_page": min(per_page, 100)
        }

        if q_organization_name:
            payload["q_organization_name"] = q_organization_name
        if organization_locations:
            payload["organization_locations"] = organization_locations
        if organization_num_employees_ranges:
            payload["organization_num_employees_ranges"] = organization_num_employees_ranges
        if organization_industries:
            payload["organization_industries"] = organization_industries

        result = await self._request_with_key("POST", "/mixed_companies/search", json=payload)

        orgs = result.get("organizations", [])
        return {
            "organizations": [self._normalize_organization(o) for o in orgs],
            "pagination": result.get("pagination", {}),
            "total": result.get("pagination", {}).get("total_entries", 0)
        }

    def _normalize_organization(self, data: Dict) -> Dict[str, Any]:
        """Normaliza dados de empresa"""
        if not data:
            return {}

        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "website_url": data.get("website_url"),
            "linkedin_url": data.get("linkedin_url"),
            "twitter_url": data.get("twitter_url"),
            "facebook_url": data.get("facebook_url"),

            "industry": data.get("industry"),
            "keywords": data.get("keywords", []),
            "estimated_num_employees": data.get("estimated_num_employees"),
            "employee_count_range": self._get_employee_range(data.get("estimated_num_employees")),

            "founded_year": data.get("founded_year"),
            "annual_revenue": data.get("annual_revenue"),
            "annual_revenue_printed": data.get("annual_revenue_printed"),

            # Localização
            "city": data.get("city"),
            "state": data.get("state"),
            "country": data.get("country"),
            "street_address": data.get("street_address"),
            "postal_code": data.get("postal_code"),

            "phone": data.get("phone"),
            "logo_url": data.get("logo_url"),
            "primary_domain": data.get("primary_domain"),

            "short_description": data.get("short_description"),

            "technologies": data.get("technologies", []),

            "raw_data": data
        }

    def _get_employee_range(self, count: Optional[int]) -> str:
        """Converte contagem para faixa"""
        if not count:
            return "unknown"
        if count <= 10:
            return "1-10"
        if count <= 50:
            return "11-50"
        if count <= 200:
            return "51-200"
        if count <= 500:
            return "201-500"
        if count <= 1000:
            return "501-1000"
        if count <= 5000:
            return "1001-5000"
        return "5000+"

    async def enrich_organization(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enriquece dados de uma empresa

        Args:
            domain: Domínio da empresa
            name: Nome da empresa

        Returns:
            Dados enriquecidos
        """
        logger.info("apollo_enrich_organization", domain=domain, name=name)

        payload = {}
        if domain:
            payload["domain"] = domain
        if name:
            payload["name"] = name

        result = await self._request_with_key("POST", "/organizations/enrich", json=payload)

        org = result.get("organization")
        if org:
            return self._normalize_organization(org)
        return {}

    # ===========================================
    # BUSCA DE FUNCIONÁRIOS
    # ===========================================

    async def get_company_employees(
        self,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None,
        person_seniorities: Optional[List[str]] = None,
        person_titles: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Busca funcionários de uma empresa

        Args:
            organization_name: Nome da empresa
            domain: Domínio da empresa
            person_seniorities: Filtrar por senioridade
            person_titles: Filtrar por cargo
            page: Página
            per_page: Resultados por página

        Returns:
            Lista de funcionários
        """
        logger.info(
            "apollo_get_employees",
            org=organization_name,
            domain=domain
        )

        payload = {
            "page": page,
            "per_page": min(per_page, 100)
        }

        if organization_name:
            payload["q_organization_name"] = organization_name
        if domain:
            payload["organization_domains"] = [domain]
        if person_seniorities:
            payload["person_seniorities"] = person_seniorities
        if person_titles:
            payload["person_titles"] = person_titles

        result = await self._request_with_key("POST", "/mixed_people/search", json=payload)

        people = result.get("people", [])
        return {
            "employees": [self._normalize_person(p) for p in people],
            "pagination": result.get("pagination", {}),
            "total": result.get("pagination", {}).get("total_entries", 0)
        }

    async def get_executives(
        self,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca executivos (C-level, VPs, Diretores) de uma empresa

        Args:
            organization_name: Nome da empresa
            domain: Domínio

        Returns:
            Lista de executivos
        """
        return await self.get_company_employees(
            organization_name=organization_name,
            domain=domain,
            person_seniorities=["c_suite", "vp", "director", "head", "partner"],
            per_page=50
        )

    async def get_decision_makers(
        self,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None,
        departments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Busca tomadores de decisão de uma empresa

        Args:
            organization_name: Nome da empresa
            domain: Domínio
            departments: Departamentos específicos

        Returns:
            Lista de decision makers
        """
        # Busca por seniority ao invés de títulos específicos
        return await self.get_company_employees(
            organization_name=organization_name,
            domain=domain,
            person_seniorities=["owner", "founder", "c_suite", "partner", "vp", "director"],
            per_page=50
        )

    # ===========================================
    # MÉTODOS PARA BRASIL
    # ===========================================

    async def search_brazil_companies(
        self,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        min_employees: Optional[int] = None,
        max_employees: Optional[int] = None,
        states: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Busca empresas brasileiras

        Args:
            name: Nome da empresa
            industry: Setor
            min_employees: Mínimo de funcionários
            max_employees: Máximo de funcionários
            states: Estados (SP, RJ, MG, etc)
            page: Página
            per_page: Resultados

        Returns:
            Empresas encontradas
        """
        locations = ["Brazil"]
        if states:
            locations.extend([f"{state}, Brazil" for state in states])

        employee_ranges = None
        if min_employees or max_employees:
            employee_ranges = self._build_employee_ranges(min_employees, max_employees)

        industries = [industry] if industry else None

        return await self.search_organizations(
            q_organization_name=name,
            organization_locations=locations,
            organization_num_employees_ranges=employee_ranges,
            organization_industries=industries,
            page=page,
            per_page=per_page
        )

    def _build_employee_ranges(
        self,
        min_emp: Optional[int],
        max_emp: Optional[int]
    ) -> List[str]:
        """Constrói ranges de funcionários"""
        ranges = []
        all_ranges = [
            (1, 10), (11, 50), (51, 200), (201, 500),
            (501, 1000), (1001, 5000), (5001, 10000), (10001, None)
        ]

        for r_min, r_max in all_ranges:
            if min_emp and r_max and r_max < min_emp:
                continue
            if max_emp and r_min > max_emp:
                continue
            if r_max:
                ranges.append(f"{r_min},{r_max}")
            else:
                ranges.append(f"{r_min},")

        return ranges or None

    async def search_brazil_people(
        self,
        name: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        seniority: Optional[str] = None,
        state: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict[str, Any]:
        """
        Busca pessoas no Brasil

        Args:
            name: Nome da pessoa
            company: Empresa
            title: Cargo
            seniority: Senioridade
            state: Estado

        Returns:
            Pessoas encontradas
        """
        locations = ["Brazil"]
        if state:
            locations = [f"{state}, Brazil"]

        titles = [title] if title else None
        seniorities = [seniority] if seniority else None

        return await self.search_people(
            q_person_name=name,
            q_organization_name=company,
            person_titles=titles,
            person_seniorities=seniorities,
            organization_locations=locations,
            page=page,
            per_page=per_page
        )
