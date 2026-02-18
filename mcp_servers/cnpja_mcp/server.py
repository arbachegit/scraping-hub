"""
CNPJá MCP Server
Consulta de regime tributário via CNPJá

Fonte: https://cnpja.com
Requer API key (plano pago).
"""

from typing import Any

import httpx
import structlog
from mcp.types import TextContent, Tool

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig

logger = structlog.get_logger()


class CNPJaMCPServer(BaseMCPServer):
    """
    MCP Server para CNPJá.

    Consulta regime tributário e dados fiscais de empresas.

    Tools disponíveis:
    - get_regime_tributario: Consulta regime tributário pelo CNPJ
    - get_company_details: Detalhes completos da empresa
    """

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("cnpja-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Verificar configuração
        if not self.config.cnpja_api_key:
            self.logger.warning("cnpja_not_configured")
            self._api_key: str | None = None
        else:
            self._api_key = self.config.cnpja_api_key

        self._base_url = self.config.cnpja_base_url or "https://api.cnpja.com"

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="get_regime_tributario",
                description="Consulta regime tributário de uma empresa pelo CNPJ. Retorna se é Simples Nacional, MEI, Lucro Presumido ou Lucro Real.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cnpj": {
                            "type": "string",
                            "description": "CNPJ da empresa (14 dígitos)",
                        },
                    },
                    "required": ["cnpj"],
                },
            ),
            Tool(
                name="get_company_details",
                description="Busca detalhes completos de uma empresa incluindo regime tributário, situação cadastral e dados fiscais.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cnpj": {
                            "type": "string",
                            "description": "CNPJ da empresa (14 dígitos)",
                        },
                    },
                    "required": ["cnpj"],
                },
            ),
        ]

    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._api_key:
            return self._error_response(
                "CNPJá não configurado. Configure CNPJA_API_KEY no .env"
            )

        try:
            if name == "get_regime_tributario":
                return await self._get_regime_tributario(arguments["cnpj"])

            elif name == "get_company_details":
                return await self._get_company_details(arguments["cnpj"])

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("cnpja_tool_error", tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    def _clean_cnpj(self, cnpj: str) -> str:
        """Remove formatação do CNPJ"""
        return "".join(filter(str.isdigit, cnpj))

    async def _request(self, endpoint: str) -> dict[str, Any]:
        """Executa request para CNPJá API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}{endpoint}",
                headers={
                    "Authorization": self._api_key,
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def _get_regime_tributario(self, cnpj: str) -> list[TextContent]:
        """
        Consulta regime tributário pelo CNPJ.

        Args:
            cnpj: CNPJ da empresa

        Returns:
            Regime tributário e informações relacionadas
        """
        cnpj_clean = self._clean_cnpj(cnpj)

        if len(cnpj_clean) != 14:
            return self._error_response(f"CNPJ inválido: {cnpj}")

        try:
            result = await self._request(f"/office/{cnpj_clean}?simples=true")

            # Extrair dados do Simples Nacional
            simples = result.get("company", {}).get("simples", {})
            company = result.get("company", {})

            # Determinar regime tributário
            regime = "LUCRO_PRESUMIDO"  # Default

            if simples.get("simei"):
                regime = "MEI"
            elif simples.get("simples"):
                # Verificar se é ME ou EPP baseado no porte
                porte = company.get("size", {}).get("text", "")
                regime = "SIMPLES_ME" if "MICRO" in porte.upper() else "SIMPLES_EPP"

            return self._success_response(
                data={
                    "cnpj": cnpj_clean,
                    "regime_tributario": regime,
                    "simples_nacional": simples.get("simples", False),
                    "simei": simples.get("simei", False),
                    "data_opcao_simples": simples.get("since"),
                    "data_exclusao_simples": simples.get("until"),
                    "porte": company.get("size", {}).get("text"),
                    "natureza_juridica": company.get("nature", {}).get("text"),
                },
                message=f"Regime tributário: {regime}",
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self._error_response(f"CNPJ {cnpj} não encontrado")
            raise

    async def _get_company_details(self, cnpj: str) -> list[TextContent]:
        """
        Busca detalhes completos da empresa.

        Args:
            cnpj: CNPJ da empresa

        Returns:
            Dados completos da empresa
        """
        cnpj_clean = self._clean_cnpj(cnpj)

        if len(cnpj_clean) != 14:
            return self._error_response(f"CNPJ inválido: {cnpj}")

        try:
            result = await self._request(
                f"/office/{cnpj_clean}?simples=true&simplesHistory=true"
            )

            company = result.get("company", {})
            office = result.get("office", {}) if "office" in result else result

            # Extrair sócios
            members = company.get("members", [])
            socios = [
                {
                    "nome": m.get("person", {}).get("name"),
                    "qualificacao": m.get("role", {}).get("text"),
                    "data_entrada": m.get("since"),
                }
                for m in members
            ]

            return self._success_response(
                data={
                    "cnpj": cnpj_clean,
                    "razao_social": company.get("name"),
                    "nome_fantasia": office.get("alias"),
                    "situacao_cadastral": office.get("status", {}).get("text"),
                    "data_abertura": company.get("founded"),
                    "natureza_juridica": company.get("nature", {}).get("text"),
                    "porte": company.get("size", {}).get("text"),
                    "capital_social": company.get("equity"),
                    "cnae_principal": {
                        "codigo": company.get("mainActivity", {}).get("id"),
                        "descricao": company.get("mainActivity", {}).get("text"),
                    },
                    "endereco": {
                        "logradouro": office.get("address", {}).get("street"),
                        "numero": office.get("address", {}).get("number"),
                        "bairro": office.get("address", {}).get("district"),
                        "cidade": office.get("address", {}).get("city"),
                        "uf": office.get("address", {}).get("state"),
                        "cep": office.get("address", {}).get("zip"),
                    },
                    "simples_nacional": company.get("simples", {}).get(
                        "simples", False
                    ),
                    "simei": company.get("simples", {}).get("simei", False),
                    "socios": socios,
                },
                message=f"Detalhes encontrados para CNPJ {cnpj}",
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self._error_response(f"CNPJ {cnpj} não encontrado")
            raise


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = CNPJaMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
