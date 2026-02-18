"""
Brasil Data Hub MCP Server
Acesso a dados geográficos brasileiros via Supabase externo

Fonte: Supabase brasil-data-hub (mnfjkegtynjtgesfphge)
Tabela: raw.geo_municipios
"""

from typing import Any

from mcp.types import TextContent, Tool
from supabase import Client, create_client

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class BrasilDataHubMCPServer(BaseMCPServer):
    """
    MCP Server para dados geográficos brasileiros.

    Acessa a tabela geo_municipios do Supabase brasil-data-hub
    para fornecer informações sobre municípios e capitais.

    Tools disponíveis:
    - get_capitais: Lista as 27 capitais brasileiras
    - get_municipio: Busca município por código IBGE ou nome
    - get_municipios_por_uf: Lista municípios de um estado
    """

    # Metadados para rastreabilidade
    SOURCE_NAME = "Brasil Data Hub - Geo Municípios"
    SOURCE_PROVIDER = "IBGE via Supabase"
    SOURCE_CATEGORY = "governamental"

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("brasil-data-hub-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Inicializar cliente Supabase
        if not self.config.brasil_data_hub_url or not self.config.brasil_data_hub_key:
            self.logger.warning("brasil_data_hub_not_configured")
            self._client: Client | None = None
        else:
            self._client = create_client(
                self.config.brasil_data_hub_url,
                self.config.brasil_data_hub_key,
            )

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="get_capitais",
                description="Retorna lista das 27 capitais brasileiras com código IBGE, nome, UF e região",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "regiao": {
                            "type": "string",
                            "description": "Filtrar por região (opcional)",
                            "enum": [
                                "Norte",
                                "Nordeste",
                                "Centro-Oeste",
                                "Sudeste",
                                "Sul",
                            ],
                        }
                    },
                },
            ),
            Tool(
                name="get_municipio",
                description="Busca município por código IBGE ou nome",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "codigo_ibge": {
                            "type": "string",
                            "description": "Código IBGE de 7 dígitos",
                        },
                        "nome": {
                            "type": "string",
                            "description": "Nome do município (busca parcial)",
                        },
                        "uf": {
                            "type": "string",
                            "description": "UF para filtrar (2 letras)",
                            "maxLength": 2,
                        },
                    },
                },
            ),
            Tool(
                name="get_municipios_por_uf",
                description="Lista todos os municípios de um estado",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "uf": {
                            "type": "string",
                            "description": "Sigla do estado (2 letras)",
                            "maxLength": 2,
                        },
                        "apenas_capitais": {
                            "type": "boolean",
                            "description": "Retornar apenas capitais (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["uf"],
                },
            ),
        ]

    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._client:
            return self._error_response(
                "Brasil Data Hub não configurado. "
                "Configure BRASIL_DATA_HUB_URL e BRASIL_DATA_HUB_KEY no .env"
            )

        if name == "get_capitais":
            return await self._get_capitais(arguments.get("regiao"))

        elif name == "get_municipio":
            return await self._get_municipio(
                codigo_ibge=arguments.get("codigo_ibge"),
                nome=arguments.get("nome"),
                uf=arguments.get("uf"),
            )

        elif name == "get_municipios_por_uf":
            return await self._get_municipios_por_uf(
                uf=arguments["uf"],
                apenas_capitais=arguments.get("apenas_capitais", False),
            )

        return self._error_response(f"Tool desconhecida: {name}")

    async def _get_capitais(self, regiao: str | None = None) -> list[TextContent]:
        """
        Retorna lista das 27 capitais brasileiras.

        Args:
            regiao: Filtrar por região (opcional)

        Returns:
            Lista de capitais com codigo_ibge, nome, uf, regiao
        """
        try:
            query = (
                self._client.schema("raw")
                .table("geo_municipios")
                .select("codigo_ibge, nome, uf, regiao, populacao")
                .eq("eh_capital", True)
            )

            if regiao:
                query = query.eq("regiao", regiao)

            result = query.order("nome").execute()

            return self._success_response(
                data=result.data,
                message=f"Encontradas {len(result.data)} capitais",
            )

        except Exception as e:
            self.logger.error("get_capitais_error", error=str(e))
            return self._error_response(f"Erro ao buscar capitais: {str(e)}")

    async def _get_municipio(
        self,
        codigo_ibge: str | None = None,
        nome: str | None = None,
        uf: str | None = None,
    ) -> list[TextContent]:
        """
        Busca município por código IBGE ou nome.

        Args:
            codigo_ibge: Código IBGE de 7 dígitos
            nome: Nome do município (busca parcial)
            uf: UF para filtrar

        Returns:
            Dados do(s) município(s) encontrado(s)
        """
        if not codigo_ibge and not nome:
            return self._error_response("Informe codigo_ibge ou nome")

        try:
            query = self._client.schema("raw").table("geo_municipios").select("*")

            if codigo_ibge:
                query = query.eq("codigo_ibge", codigo_ibge)
            elif nome:
                query = query.ilike("nome", f"%{nome}%")
                if uf:
                    query = query.eq("uf", uf.upper())

            result = query.limit(10).execute()

            if not result.data:
                return self._error_response("Município não encontrado")

            return self._success_response(
                data=result.data,
                message=f"Encontrados {len(result.data)} municípios",
            )

        except Exception as e:
            self.logger.error("get_municipio_error", error=str(e))
            return self._error_response(f"Erro ao buscar município: {str(e)}")

    async def _get_municipios_por_uf(
        self, uf: str, apenas_capitais: bool = False
    ) -> list[TextContent]:
        """
        Lista municípios de um estado.

        Args:
            uf: Sigla do estado (2 letras)
            apenas_capitais: Se True, retorna apenas capitais

        Returns:
            Lista de municípios
        """
        try:
            query = (
                self._client.schema("raw")
                .table("geo_municipios")
                .select("codigo_ibge, nome, eh_capital, populacao, regiao")
                .eq("uf", uf.upper())
            )

            if apenas_capitais:
                query = query.eq("eh_capital", True)

            result = query.order("nome").execute()

            return self._success_response(
                data=result.data,
                message=f"Encontrados {len(result.data)} municípios em {uf.upper()}",
            )

        except Exception as e:
            self.logger.error("get_municipios_por_uf_error", error=str(e))
            return self._error_response(f"Erro ao buscar municípios: {str(e)}")


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = BrasilDataHubMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
