"""
Coresignal Client
Cliente para API do Coresignal - dados de empresas e profissionais
"""

from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings

from .base import BaseScraper

logger = structlog.get_logger()


class CoresignalClient(BaseScraper):
    """
    Cliente para API Coresignal v2

    Endpoints principais:
    - /v2/company_base/search/es_dsl - Buscar empresas (retorna IDs)
    - /v2/company_base/collect/{id} - Detalhes de empresa
    - /v2/member/search/es_dsl - Buscar profissionais (retorna IDs)
    - /v2/member/collect/{id} - Detalhes de profissional
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        # Usar v2 como base
        default_base = settings.coresignal_base_url.replace("/v1", "/v2")
        if "/v2" not in default_base:
            default_base = default_base.rstrip("/") + "/v2" if "/cdapi" in default_base else "https://api.coresignal.com/cdapi/v2"

        super().__init__(
            api_key=api_key or settings.coresignal_api_key,
            base_url=base_url or default_base,
            rate_limit=settings.coresignal_rate_limit
        )

    def _get_headers(self) -> Dict[str, str]:
        # Coresignal usa header 'apikey' (não Bearer)
        return {
            "apikey": self.api_key,
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
        Busca empresas por varios criterios usando Elasticsearch DSL

        Args:
            name: Nome da empresa
            website: Website da empresa
            industry: Setor de atuacao
            country: Pais
            size: Tamanho (1-10, 11-50, 51-200, etc)
            limit: Numero maximo de resultados

        Returns:
            Lista de empresas com detalhes completos
        """
        # Construir query Elasticsearch
        must_clauses = []

        if name:
            must_clauses.append({"match": {"name": name}})
        if website:
            must_clauses.append({"match": {"website": website}})
        if industry:
            must_clauses.append({"match": {"industry": industry}})
        if country:
            must_clauses.append({"match": {"country": country}})
        if size:
            must_clauses.append({"match": {"size": size}})

        query = {"match_all": {}} if not must_clauses else {
            "bool": {"must": must_clauses}
        }

        logger.info("coresignal_search_companies", query=query, limit=limit)

        # Buscar IDs
        ids = await self.post(
            "/company_base/search/es_dsl",
            json={"query": query}
        )

        if not ids or not isinstance(ids, list):
            return []

        # Limitar resultados
        ids = ids[:limit]

        # Coletar detalhes de cada empresa
        companies = []
        for company_id in ids:
            try:
                company = await self.get_company(str(company_id))
                if company:
                    companies.append(company)
            except Exception as e:
                logger.warning("coresignal_collect_error", id=company_id, error=str(e))

        return companies

    async def search_company_ids(
        self,
        name: Optional[str] = None,
        website: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None
    ) -> List[int]:
        """
        Busca apenas IDs de empresas (mais rapido)

        Returns:
            Lista de IDs de empresas
        """
        must_clauses = []

        if name:
            must_clauses.append({"match": {"name": name}})
        if website:
            must_clauses.append({"match": {"website": website}})
        if industry:
            must_clauses.append({"match": {"industry": industry}})
        if country:
            must_clauses.append({"match": {"country": country}})

        query = {"match_all": {}} if not must_clauses else {
            "bool": {"must": must_clauses}
        }

        ids = await self.post(
            "/company_base/search/es_dsl",
            json={"query": query}
        )

        return ids if isinstance(ids, list) else []

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Obtem detalhes completos de uma empresa

        Args:
            company_id: ID da empresa no Coresignal

        Returns:
            Dados completos da empresa
        """
        logger.info("coresignal_get_company", company_id=company_id)
        return await self.get(f"/company_base/collect/{company_id}")

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

        # Buscar por shorthand_name extraido da URL
        shorthand = linkedin_url.rstrip("/").split("/")[-1]

        ids = await self.post(
            "/company_base/search/es_dsl",
            json={
                "query": {
                    "match": {"shorthand_name": shorthand}
                }
            }
        )

        if ids and isinstance(ids, list):
            return await self.get_company(str(ids[0]))

        return {}

    async def get_company_employees(
        self,
        company_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista funcionarios de uma empresa

        Args:
            company_id: ID da empresa
            limit: Numero maximo de resultados

        Returns:
            Lista de funcionarios
        """
        logger.info(
            "coresignal_get_employees",
            company_id=company_id,
            limit=limit
        )

        # Buscar membros pela company_id
        ids = await self.post(
            "/member/search/es_dsl",
            json={
                "query": {
                    "match": {"company_id": company_id}
                }
            }
        )

        if not ids or not isinstance(ids, list):
            return []

        # Limitar e coletar detalhes
        ids = ids[:limit]
        members = []

        for member_id in ids:
            try:
                member = await self.get_member(str(member_id))
                if member:
                    members.append(member)
            except Exception as e:
                logger.warning("coresignal_member_error", id=member_id, error=str(e))

        return members

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
        must_clauses = []

        if name:
            must_clauses.append({"match": {"name": name}})
        if title:
            must_clauses.append({"match": {"title": title}})
        if company:
            must_clauses.append({"match": {"company_name": company}})
        if location:
            must_clauses.append({"match": {"location": location}})
        if skills:
            for skill in skills:
                must_clauses.append({"match": {"skills": skill}})

        query = {"match_all": {}} if not must_clauses else {
            "bool": {"must": must_clauses}
        }

        logger.info("coresignal_search_members", query=query, limit=limit)

        ids = await self.post(
            "/member/search/es_dsl",
            json={"query": query}
        )

        if not ids or not isinstance(ids, list):
            return []

        ids = ids[:limit]
        members = []

        for member_id in ids:
            try:
                member = await self.get_member(str(member_id))
                if member:
                    members.append(member)
            except Exception as e:
                logger.warning("coresignal_member_error", id=member_id, error=str(e))

        return members

    async def get_member(self, member_id: str) -> Dict[str, Any]:
        """
        Obtem detalhes de um profissional

        Args:
            member_id: ID do profissional no Coresignal

        Returns:
            Dados completos do profissional
        """
        logger.info("coresignal_get_member", member_id=member_id)
        return await self.get(f"/member/collect/{member_id}")

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

        # Extrair username da URL
        username = linkedin_url.rstrip("/").split("/")[-1]

        ids = await self.post(
            "/member/search/es_dsl",
            json={
                "query": {
                    "match": {"canonical_url": username}
                }
            }
        )

        if ids and isinstance(ids, list):
            return await self.get_member(str(ids[0]))

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
            return companies[0]

        return {}
