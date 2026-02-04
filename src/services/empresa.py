"""
Empresa Service
Servico de enriquecimento de dados de empresas
"""

import structlog
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.scrapers import CoresignalClient, ProxycurlClient, FirecrawlClient


logger = structlog.get_logger()


@dataclass
class EmpresaEnriquecida:
    """Dados enriquecidos de empresa"""
    # Identificacao
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None

    # LinkedIn
    linkedin_url: Optional[str] = None
    linkedin_followers: Optional[int] = None

    # Contato
    website: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    # Localizacao
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = None

    # Detalhes
    setor: Optional[str] = None
    descricao: Optional[str] = None
    num_funcionarios: Optional[int] = None
    faixa_funcionarios: Optional[str] = None
    ano_fundacao: Optional[int] = None

    # Financeiro (se disponivel)
    receita_estimada: Optional[str] = None
    funding_total: Optional[float] = None

    # Fontes
    fontes: List[str] = None

    def __post_init__(self):
        if self.fontes is None:
            self.fontes = []


class EmpresaService:
    """
    Servico para enriquecimento de dados de empresas

    Combina dados de multiplas fontes:
    - Coresignal (dados de mercado)
    - Proxycurl (LinkedIn)
    - Firecrawl (website)
    """

    def __init__(self):
        self.coresignal = CoresignalClient()
        self.proxycurl = ProxycurlClient()
        self.firecrawl = FirecrawlClient()

    async def enrich_company(
        self,
        cnpj: Optional[str] = None,
        name: Optional[str] = None,
        website: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> EmpresaEnriquecida:
        """
        Enriquece dados de uma empresa usando multiplas fontes

        Args:
            cnpj: CNPJ da empresa
            name: Nome da empresa
            website: Website da empresa
            linkedin_url: URL do LinkedIn
            sources: Fontes a usar (coresignal, proxycurl, firecrawl)

        Returns:
            Dados enriquecidos da empresa
        """
        sources = sources or ["coresignal", "proxycurl", "firecrawl"]
        empresa = EmpresaEnriquecida(cnpj=cnpj)

        logger.info(
            "empresa_enrich_start",
            cnpj=cnpj,
            name=name,
            sources=sources
        )

        # Coresignal
        if "coresignal" in sources:
            await self._enrich_from_coresignal(
                empresa, name, website, linkedin_url
            )

        # Proxycurl (LinkedIn)
        if "proxycurl" in sources:
            await self._enrich_from_proxycurl(
                empresa, linkedin_url, website, name
            )

        # Firecrawl (Website)
        if "firecrawl" in sources and (website or empresa.website):
            await self._enrich_from_firecrawl(
                empresa, website or empresa.website
            )

        logger.info(
            "empresa_enrich_complete",
            cnpj=cnpj,
            fontes=empresa.fontes
        )

        return empresa

    async def _enrich_from_coresignal(
        self,
        empresa: EmpresaEnriquecida,
        name: Optional[str],
        website: Optional[str],
        linkedin_url: Optional[str]
    ) -> None:
        """Enriquece com dados do Coresignal"""
        try:
            data = await self.coresignal.enrich_company(
                name=name,
                website=website,
                linkedin_url=linkedin_url
            )

            if data:
                empresa.nome_fantasia = empresa.nome_fantasia or data.get("name")
                empresa.website = empresa.website or data.get("website")
                empresa.linkedin_url = empresa.linkedin_url or data.get("linkedin_url")
                empresa.setor = empresa.setor or data.get("industry")
                empresa.descricao = empresa.descricao or data.get("description")
                empresa.num_funcionarios = empresa.num_funcionarios or data.get("employees_count")
                empresa.faixa_funcionarios = empresa.faixa_funcionarios or data.get("size")
                empresa.ano_fundacao = empresa.ano_fundacao or data.get("founded_year")
                empresa.cidade = empresa.cidade or data.get("city")
                empresa.pais = empresa.pais or data.get("country")

                empresa.fontes.append("coresignal")

        except Exception as e:
            logger.error("coresignal_enrich_error", error=str(e))

    async def _enrich_from_proxycurl(
        self,
        empresa: EmpresaEnriquecida,
        linkedin_url: Optional[str],
        website: Optional[str],
        name: Optional[str]
    ) -> None:
        """Enriquece com dados do Proxycurl/LinkedIn"""
        try:
            data = await self.proxycurl.enrich_company(
                linkedin_url=linkedin_url or empresa.linkedin_url,
                domain=website or empresa.website,
                name=name or empresa.nome_fantasia
            )

            if data:
                empresa.nome_fantasia = empresa.nome_fantasia or data.get("name")
                empresa.linkedin_url = empresa.linkedin_url or data.get("linkedin_internal_id")
                empresa.linkedin_followers = data.get("follower_count")
                empresa.website = empresa.website or data.get("website")
                empresa.descricao = empresa.descricao or data.get("description")
                empresa.setor = empresa.setor or data.get("industry")
                empresa.num_funcionarios = empresa.num_funcionarios or data.get("company_size")
                empresa.faixa_funcionarios = empresa.faixa_funcionarios or data.get("company_size_on_linkedin")
                empresa.ano_fundacao = empresa.ano_fundacao or data.get("founded_year")

                # Funding
                funding_data = data.get("funding_data")
                if funding_data:
                    empresa.funding_total = funding_data.get("total_funding_amount")

                # Localizacao
                hq = data.get("hq")
                if hq:
                    empresa.cidade = empresa.cidade or hq.get("city")
                    empresa.estado = empresa.estado or hq.get("state")
                    empresa.pais = empresa.pais or hq.get("country")

                empresa.fontes.append("proxycurl")

        except Exception as e:
            logger.error("proxycurl_enrich_error", error=str(e))

    async def _enrich_from_firecrawl(
        self,
        empresa: EmpresaEnriquecida,
        website: str
    ) -> None:
        """Enriquece com dados do website via Firecrawl"""
        try:
            # Extrair informacoes estruturadas do site
            schema = {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "description": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "address": {"type": "string"}
                }
            }

            data = await self.firecrawl.scrape_with_extraction(
                url=website,
                schema=schema,
                prompt="Extract company information from this website."
            )

            if data:
                empresa.nome_fantasia = empresa.nome_fantasia or data.get("company_name")
                empresa.descricao = empresa.descricao or data.get("description")
                empresa.telefone = empresa.telefone or data.get("phone")
                empresa.email = empresa.email or data.get("email")
                empresa.endereco = empresa.endereco or data.get("address")

                empresa.fontes.append("firecrawl")

        except Exception as e:
            logger.error("firecrawl_enrich_error", error=str(e))

    async def get_employees(
        self,
        linkedin_url: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista funcionarios de uma empresa

        Args:
            linkedin_url: URL do LinkedIn da empresa
            company_id: ID no Coresignal
            limit: Numero maximo de funcionarios

        Returns:
            Lista de funcionarios
        """
        employees = []

        # Tentar Coresignal primeiro
        if company_id:
            try:
                cs_employees = await self.coresignal.get_company_employees(
                    company_id=company_id,
                    limit=limit
                )
                employees.extend(cs_employees)
            except Exception as e:
                logger.error("get_employees_coresignal_error", error=str(e))

        # Complementar com Proxycurl
        if linkedin_url and len(employees) < limit:
            try:
                pc_result = await self.proxycurl.get_company_employees(
                    linkedin_url=linkedin_url,
                    page_size=min(limit - len(employees), 10)
                )
                employees.extend(pc_result.get("employees", []))
            except Exception as e:
                logger.error("get_employees_proxycurl_error", error=str(e))

        return employees[:limit]

    async def close(self):
        """Fecha todos os clientes"""
        await self.coresignal.close()
        await self.proxycurl.close()
        await self.firecrawl.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
