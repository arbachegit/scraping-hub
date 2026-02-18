"""
BrasilAPI MCP Server
Dados públicos brasileiros via BrasilAPI

Fonte: https://brasilapi.com.br
Não requer autenticação.
"""

from typing import Any

from mcp.types import TextContent, Tool

from src.scrapers.brasil_api import BrasilAPIClient

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class BrasilAPIMCPServer(BaseMCPServer):
    """
    MCP Server para BrasilAPI.

    Acessa dados públicos brasileiros:
    - CNPJ: Dados cadastrais de empresas
    - CEP: Endereços
    - Bancos: Lista de bancos brasileiros

    Tools disponíveis:
    - get_company: Busca dados de empresa pelo CNPJ
    - get_cep: Busca endereço pelo CEP
    - list_banks: Lista bancos brasileiros
    """

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("brasilapi-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # BrasilAPI não requer autenticação
        self._client = BrasilAPIClient()

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="get_company",
                description="Busca dados cadastrais de empresa pelo CNPJ via Receita Federal. Retorna razão social, sócios, endereço, CNAE, capital social e mais.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cnpj": {
                            "type": "string",
                            "description": "CNPJ da empresa (14 dígitos, pode conter formatação)",
                        },
                    },
                    "required": ["cnpj"],
                },
            ),
            Tool(
                name="get_cep",
                description="Busca endereço pelo CEP",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cep": {
                            "type": "string",
                            "description": "CEP (8 dígitos, pode conter formatação)",
                        },
                    },
                    "required": ["cep"],
                },
            ),
            Tool(
                name="list_banks",
                description="Lista todos os bancos brasileiros com código e nome",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Processa chamada de tool"""
        try:
            if name == "get_company":
                return await self._get_company(arguments["cnpj"])

            elif name == "get_cep":
                return await self._get_cep(arguments["cep"])

            elif name == "list_banks":
                return await self._list_banks()

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("brasilapi_tool_error", tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    async def _get_company(self, cnpj: str) -> list[TextContent]:
        """
        Busca dados de empresa pelo CNPJ.

        Args:
            cnpj: CNPJ da empresa (14 dígitos)

        Returns:
            Dados cadastrais da empresa
        """
        try:
            result = await self._client.get_cnpj(cnpj)

            if not result:
                return self._error_response(f"CNPJ {cnpj} não encontrado")

            return self._success_response(
                data={
                    "cnpj": result.get("cnpj"),
                    "razao_social": result.get("razao_social"),
                    "nome_fantasia": result.get("nome_fantasia"),
                    "natureza_juridica": result.get("natureza_juridica"),
                    "situacao_cadastral": result.get("situacao_cadastral"),
                    "data_abertura": result.get("data_abertura"),
                    "capital_social": result.get("capital_social"),
                    "porte": result.get("porte"),
                    "cnae_principal": result.get("cnae_principal"),
                    "endereco": result.get("endereco"),
                    "telefone": result.get("telefone"),
                    "email": result.get("email"),
                    "socios": result.get("socios", []),
                },
                message=f"Dados encontrados para CNPJ {cnpj}",
            )

        except ValueError as e:
            return self._error_response(str(e))

    async def _get_cep(self, cep: str) -> list[TextContent]:
        """
        Busca endereço pelo CEP.

        Args:
            cep: CEP (8 dígitos)

        Returns:
            Dados do endereço
        """
        try:
            result = await self._client.get_cep(cep)

            if not result:
                return self._error_response(f"CEP {cep} não encontrado")

            return self._success_response(
                data={
                    "cep": result.get("cep"),
                    "logradouro": result.get("logradouro"),
                    "bairro": result.get("bairro"),
                    "cidade": result.get("cidade"),
                    "estado": result.get("estado"),
                    "location": result.get("location"),
                },
                message=f"Endereço encontrado para CEP {cep}",
            )

        except ValueError as e:
            return self._error_response(str(e))

    async def _list_banks(self) -> list[TextContent]:
        """
        Lista bancos brasileiros.

        Returns:
            Lista de bancos com código e nome
        """
        banks = await self._client.get_banks()

        return self._success_response(
            data={"banks": banks, "total": len(banks)},
            message=f"Encontrados {len(banks)} bancos",
        )


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = BrasilAPIMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
