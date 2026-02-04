"""
Governo Service
Servico para scraping de dados governamentais
"""

import structlog
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.scrapers import FirecrawlClient


logger = structlog.get_logger()


@dataclass
class PortalConfig:
    """Configuracao de portal governamental"""
    nome: str
    url_base: str
    paths: Dict[str, str]


# Portais conhecidos
PORTAIS = {
    "transparencia_federal": PortalConfig(
        nome="Portal da Transparencia",
        url_base="https://portaldatransparencia.gov.br",
        paths={
            "despesas": "/despesas",
            "receitas": "/receitas",
            "contratos": "/contratos",
            "licitacoes": "/licitacoes",
            "servidores": "/servidores"
        }
    ),
    "compras_gov": PortalConfig(
        nome="Compras.gov.br",
        url_base="https://www.gov.br/compras",
        paths={
            "contratos": "/contratos",
            "licitacoes": "/licitacoes",
            "fornecedores": "/fornecedores"
        }
    ),
    "siconfi": PortalConfig(
        nome="Siconfi",
        url_base="https://siconfi.tesouro.gov.br",
        paths={
            "rreo": "/siconfi/pages/public/conteudo",
            "rgf": "/siconfi/pages/public/conteudo",
            "dca": "/siconfi/pages/public/conteudo"
        }
    )
}


class GovernoService:
    """
    Servico para scraping de portais governamentais

    Funcionalidades:
    - Scraping de portais de transparencia
    - Extracao de licitacoes
    - Dados de servidores
    - Informacoes orcamentarias
    """

    def __init__(self):
        self.firecrawl = FirecrawlClient()

    async def scrape_transparency_portal(
        self,
        uf: Optional[str] = None,
        tipo: str = "licitacoes",
        filtros: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Scrape de portal de transparencia

        Args:
            uf: Estado (se None, usa portal federal)
            tipo: Tipo de dado (licitacoes, contratos, despesas, etc)
            filtros: Filtros adicionais

        Returns:
            Dados extraidos do portal
        """
        logger.info("governo_scrape_transparency", uf=uf, tipo=tipo)

        if uf:
            url = self._get_state_portal_url(uf, tipo)
        else:
            portal = PORTAIS["transparencia_federal"]
            path = portal.paths.get(tipo, "/")
            url = f"{portal.url_base}{path}"

        # Schema para extracao
        schema = self._get_extraction_schema(tipo)

        try:
            data = await self.firecrawl.scrape_with_extraction(
                url=url,
                schema=schema,
                prompt=f"Extract all {tipo} information from this government transparency portal."
            )

            return {
                "fonte": url,
                "tipo": tipo,
                "dados": data,
                "filtros_aplicados": filtros
            }

        except Exception as e:
            logger.error("governo_scrape_error", url=url, error=str(e))
            return {"erro": str(e), "url": url}

    def _get_state_portal_url(self, uf: str, tipo: str) -> str:
        """Retorna URL do portal estadual"""
        # Mapeamento de portais estaduais
        state_portals = {
            "SP": "https://transparencia.sp.gov.br",
            "RJ": "https://transparencia.rj.gov.br",
            "MG": "https://transparencia.mg.gov.br",
            "RS": "https://transparencia.rs.gov.br",
            "PR": "https://transparencia.pr.gov.br",
            "BA": "https://transparencia.ba.gov.br",
            "SC": "https://transparencia.sc.gov.br",
            "PE": "https://transparencia.pe.gov.br",
            "GO": "https://transparencia.go.gov.br",
            "CE": "https://transparencia.ce.gov.br"
        }

        base_url = state_portals.get(uf.upper(), "https://transparencia.gov.br")
        return f"{base_url}/{tipo}"

    def _get_extraction_schema(self, tipo: str) -> Dict[str, Any]:
        """Retorna schema de extracao para o tipo de dado"""
        schemas = {
            "licitacoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {"type": "string"},
                        "modalidade": {"type": "string"},
                        "objeto": {"type": "string"},
                        "valor_estimado": {"type": "number"},
                        "orgao": {"type": "string"},
                        "data_abertura": {"type": "string"},
                        "situacao": {"type": "string"}
                    }
                }
            },
            "contratos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {"type": "string"},
                        "fornecedor": {"type": "string"},
                        "cnpj_fornecedor": {"type": "string"},
                        "objeto": {"type": "string"},
                        "valor": {"type": "number"},
                        "vigencia_inicio": {"type": "string"},
                        "vigencia_fim": {"type": "string"},
                        "orgao": {"type": "string"}
                    }
                }
            },
            "despesas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "funcao": {"type": "string"},
                        "subfuncao": {"type": "string"},
                        "programa": {"type": "string"},
                        "acao": {"type": "string"},
                        "valor_empenhado": {"type": "number"},
                        "valor_liquidado": {"type": "number"},
                        "valor_pago": {"type": "number"}
                    }
                }
            },
            "servidores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nome": {"type": "string"},
                        "cargo": {"type": "string"},
                        "orgao": {"type": "string"},
                        "remuneracao_bruta": {"type": "number"},
                        "remuneracao_liquida": {"type": "number"},
                        "vinculo": {"type": "string"}
                    }
                }
            }
        }

        return schemas.get(tipo, {"type": "object", "additionalProperties": True})

    async def crawl_portal(
        self,
        url: str,
        max_pages: int = 50,
        include_paths: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl completo de um portal

        Args:
            url: URL inicial
            max_pages: Numero maximo de paginas
            include_paths: Paths a incluir

        Returns:
            Lista de paginas crawled
        """
        logger.info("governo_crawl_portal", url=url, max_pages=max_pages)

        try:
            pages = await self.firecrawl.crawl_and_wait(
                url=url,
                max_depth=3,
                limit=max_pages,
                include_paths=include_paths
            )

            return pages

        except Exception as e:
            logger.error("governo_crawl_error", url=url, error=str(e))
            return []

    async def map_portal_urls(
        self,
        url: str,
        search_term: Optional[str] = None
    ) -> List[str]:
        """
        Mapeia URLs de um portal

        Args:
            url: URL do portal
            search_term: Termo para filtrar URLs

        Returns:
            Lista de URLs encontradas
        """
        logger.info("governo_map_urls", url=url)

        try:
            urls = await self.firecrawl.map_site(
                url=url,
                search=search_term,
                limit=1000
            )

            return urls

        except Exception as e:
            logger.error("governo_map_error", url=url, error=str(e))
            return []

    async def extract_table_from_page(
        self,
        url: str,
        table_description: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrai dados de tabela de uma pagina

        Args:
            url: URL da pagina com tabela
            table_description: Descricao da tabela a extrair

        Returns:
            Lista de linhas da tabela
        """
        logger.info("governo_extract_table", url=url)

        try:
            data = await self.firecrawl.extract_table_data(
                url=url,
                table_selector=None  # Deixa o LLM encontrar a tabela
            )

            return data

        except Exception as e:
            logger.error("governo_table_error", url=url, error=str(e))
            return []

    async def get_siconfi_data(
        self,
        codigo_ibge: int,
        exercicio: int,
        relatorio: str = "rreo"
    ) -> Dict[str, Any]:
        """
        Obtem dados do Siconfi

        Args:
            codigo_ibge: Codigo IBGE do municipio
            exercicio: Ano fiscal
            relatorio: Tipo de relatorio (rreo, rgf, dca)

        Returns:
            Dados do relatorio
        """
        logger.info(
            "governo_siconfi",
            municipio=codigo_ibge,
            exercicio=exercicio,
            relatorio=relatorio
        )

        # URL do Siconfi
        base_url = "https://siconfi.tesouro.gov.br/siconfi/pages/public"
        url = f"{base_url}/conteudo.jsf?declaracao={relatorio}"

        schema = {
            "type": "object",
            "properties": {
                "municipio": {"type": "string"},
                "exercicio": {"type": "integer"},
                "periodo": {"type": "string"},
                "dados": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True
                    }
                }
            }
        }

        try:
            data = await self.firecrawl.scrape_with_extraction(
                url=url,
                schema=schema,
                prompt=f"Extract fiscal data for municipality {codigo_ibge} year {exercicio}"
            )

            return data

        except Exception as e:
            logger.error("governo_siconfi_error", error=str(e))
            return {}

    async def close(self):
        """Fecha o cliente"""
        await self.firecrawl.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
