"""
Brasil API Client
Consulta dados de CNPJ, CEP e outros dados brasileiros
https://brasilapi.com.br/
"""

from typing import Any, Dict, Optional

import httpx
import structlog

from .base import BaseScraper

logger = structlog.get_logger()


class BrasilAPIClient(BaseScraper):
    """
    Cliente para BrasilAPI - dados públicos brasileiros

    APIs disponíveis:
    - CNPJ: dados cadastrais de empresas
    - CEP: endereços
    - Bancos: lista de bancos
    - DDD: códigos de área
    - Feriados: feriados nacionais
    """

    # Metadados da fonte para rastreabilidade (CLAUDE.md)
    SOURCE_NAME = "BrasilAPI - Dados Públicos"
    SOURCE_PROVIDER = "BrasilAPI"
    SOURCE_CATEGORY = "api"
    SOURCE_COVERAGE = "CNPJ, CEP, bancos, DDD, feriados brasileiros"
    SOURCE_DOC_URL = "https://brasilapi.com.br/docs"

    def __init__(self, timeout: float = 30.0):
        # BrasilAPI não requer autenticação
        super().__init__(
            api_key="",
            base_url="https://brasilapi.com.br/api",
            rate_limit=60,  # Sem limite oficial, mas ser conservador
            timeout=timeout,
        )

    def _get_headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", "User-Agent": "ScrapingHub/2.0"}

    async def get_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """
        Busca dados de empresa pelo CNPJ

        Args:
            cnpj: CNPJ da empresa (apenas números)

        Returns:
            Dados cadastrais da empresa
        """
        # Limpar CNPJ
        cnpj_clean = "".join(filter(str.isdigit, cnpj))

        if len(cnpj_clean) != 14:
            raise ValueError(f"CNPJ inválido: {cnpj}")

        logger.info("brasil_api_cnpj", cnpj=cnpj_clean[:8] + "****")

        try:
            result = await self.get(f"/cnpj/v1/{cnpj_clean}")
            return self._normalize_company(result)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("cnpj_not_found", cnpj=cnpj_clean[:8])
                return {}
            raise

    def _normalize_company(self, data: Dict) -> Dict[str, Any]:
        """Normaliza dados da empresa para formato padrão"""
        if not data:
            return {}

        # Mapear porte
        porte_map = {
            "MICRO EMPRESA": "micro",
            "EMPRESA DE PEQUENO PORTE": "pequena",
            "DEMAIS": "media_grande",
        }

        return {
            "cnpj": data.get("cnpj"),
            "razao_social": data.get("razao_social"),
            "nome_fantasia": data.get("nome_fantasia") or data.get("razao_social"),
            "natureza_juridica": data.get("natureza_juridica"),
            "situacao_cadastral": data.get("descricao_situacao_cadastral"),
            "data_abertura": data.get("data_inicio_atividade"),
            "capital_social": data.get("capital_social"),
            "porte": porte_map.get(data.get("porte", ""), data.get("porte")),
            # Atividade
            "cnae_principal": {
                "codigo": data.get("cnae_fiscal"),
                "descricao": data.get("cnae_fiscal_descricao"),
            },
            "cnaes_secundarios": data.get("cnaes_secundarios", []),
            # Endereço
            "endereco": {
                "logradouro": data.get("logradouro"),
                "numero": data.get("numero"),
                "complemento": data.get("complemento"),
                "bairro": data.get("bairro"),
                "cep": data.get("cep"),
                "municipio": data.get("municipio"),
                "uf": data.get("uf"),
            },
            # Contato
            "telefone": data.get("ddd_telefone_1"),
            "email": data.get("email"),
            # Sócios
            "socios": [
                {
                    "nome": s.get("nome_socio"),
                    "qualificacao": s.get("qualificacao_socio"),
                    "data_entrada": s.get("data_entrada_sociedade"),
                }
                for s in data.get("qsa", [])
            ],
            # Dados originais
            "raw_data": data,
        }

    async def get_cep(self, cep: str) -> Dict[str, Any]:
        """
        Busca endereço pelo CEP

        Args:
            cep: CEP (apenas números)

        Returns:
            Dados do endereço
        """
        cep_clean = "".join(filter(str.isdigit, cep))

        if len(cep_clean) != 8:
            raise ValueError(f"CEP inválido: {cep}")

        try:
            result = await self.get(f"/cep/v2/{cep_clean}")
            return {
                "cep": result.get("cep"),
                "logradouro": result.get("street"),
                "bairro": result.get("neighborhood"),
                "cidade": result.get("city"),
                "estado": result.get("state"),
                "location": result.get("location", {}),
                "raw_data": result,
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise

    async def get_banks(self) -> list:
        """Lista todos os bancos brasileiros"""
        result = await self.get("/banks/v1")
        return result if isinstance(result, list) else []

    async def get_ddd(self, ddd: str) -> Dict[str, Any]:
        """Busca informações de um DDD"""
        try:
            result = await self.get(f"/ddd/v1/{ddd}")
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise

    async def get_holidays(self, year: int) -> list:
        """Lista feriados nacionais de um ano"""
        result = await self.get(f"/feriados/v1/{year}")
        return result if isinstance(result, list) else []

    async def search_cnpj_by_name(self, name: str) -> Optional[str]:
        """
        BrasilAPI não suporta busca por nome diretamente.
        Esta função é um placeholder para integração com Serper.

        Returns:
            None - use SerperClient para buscar CNPJ por nome
        """
        logger.warning(
            "brasil_api_name_search_not_supported",
            message="Use SerperClient para buscar CNPJ por nome da empresa",
        )
        return None
