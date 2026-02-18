"""
Fiscal MCP Server
Acesso a dados de políticos e mandatos do iconsai-fiscal

Fonte: Supabase iconsai-fiscal (tijadrwimhxlggzxuwna)
Tabelas: politico, mandato_politico
"""

from typing import Any

from mcp.types import TextContent, Tool

from supabase import Client, create_client

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class FiscalMCPServer(BaseMCPServer):
    """
    MCP Server para dados de políticos brasileiros.

    Acessa as tabelas politico e mandato_politico do Supabase iconsai-fiscal
    para fornecer informações sobre políticos eleitos e seus mandatos.

    Tools disponíveis:
    - search_politico: Busca políticos por nome ou cargo
    - get_politico: Retorna dados de um político específico
    - list_mandatos: Lista mandatos de um político
    - get_politicos_por_municipio: Lista políticos de um município
    - get_politicos_por_partido: Lista políticos de um partido
    """

    # Metadados para rastreabilidade
    SOURCE_NAME = "IconsAI Fiscal - Políticos"
    SOURCE_PROVIDER = "TSE via Supabase"
    SOURCE_CATEGORY = "eleitoral"

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("fiscal-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Inicializar cliente Supabase
        if not self.config.fiscal_supabase_url or not self.config.fiscal_supabase_key:
            self.logger.warning("fiscal_supabase_not_configured")
            self._client: Client | None = None
        else:
            self._client = create_client(
                self.config.fiscal_supabase_url,
                self.config.fiscal_supabase_key,
            )

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="search_politico",
                description="Busca políticos por nome, cargo ou partido",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "nome": {
                            "type": "string",
                            "description": "Nome do político (busca parcial)",
                        },
                        "cargo": {
                            "type": "string",
                            "description": "Cargo atual ou pretendido",
                            "enum": [
                                "Prefeito",
                                "Vice-Prefeito",
                                "Vereador",
                                "Governador",
                                "Vice-Governador",
                                "Deputado Estadual",
                                "Deputado Federal",
                                "Senador",
                                "Presidente",
                            ],
                        },
                        "partido": {
                            "type": "string",
                            "description": "Sigla do partido (ex: PT, PSDB, MDB)",
                        },
                        "uf": {
                            "type": "string",
                            "description": "UF para filtrar (2 letras)",
                            "maxLength": 2,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limite de resultados (default: 20)",
                            "default": 20,
                        },
                    },
                },
            ),
            Tool(
                name="get_politico",
                description="Retorna dados completos de um político por ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "ID do político no banco",
                        },
                        "cpf": {
                            "type": "string",
                            "description": "CPF do político (apenas números)",
                        },
                    },
                },
            ),
            Tool(
                name="list_mandatos",
                description="Lista histórico de mandatos de um político",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "politico_id": {
                            "type": "string",
                            "description": "ID do político",
                        },
                        "ativo": {
                            "type": "boolean",
                            "description": "Filtrar apenas mandatos ativos",
                        },
                    },
                    "required": ["politico_id"],
                },
            ),
            Tool(
                name="get_politicos_por_municipio",
                description="Lista políticos eleitos de um município",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "codigo_ibge": {
                            "type": "string",
                            "description": "Código IBGE do município (7 dígitos)",
                        },
                        "municipio_nome": {
                            "type": "string",
                            "description": "Nome do município (busca parcial)",
                        },
                        "uf": {
                            "type": "string",
                            "description": "UF do município (2 letras)",
                            "maxLength": 2,
                        },
                        "cargo": {
                            "type": "string",
                            "description": "Filtrar por cargo",
                        },
                        "apenas_ativos": {
                            "type": "boolean",
                            "description": "Retornar apenas mandatos ativos (default: true)",
                            "default": True,
                        },
                    },
                },
            ),
            Tool(
                name="get_politicos_por_partido",
                description="Lista políticos de um partido",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "partido": {
                            "type": "string",
                            "description": "Sigla do partido (ex: PT, PSDB, MDB)",
                        },
                        "uf": {
                            "type": "string",
                            "description": "Filtrar por UF (2 letras)",
                            "maxLength": 2,
                        },
                        "cargo": {
                            "type": "string",
                            "description": "Filtrar por cargo",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limite de resultados (default: 50)",
                            "default": 50,
                        },
                    },
                    "required": ["partido"],
                },
            ),
        ]

    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._client:
            return self._error_response(
                "Fiscal Supabase não configurado. "
                "Configure FISCAL_SUPABASE_URL e FISCAL_SUPABASE_KEY no .env"
            )

        if name == "search_politico":
            return await self._search_politico(
                nome=arguments.get("nome"),
                cargo=arguments.get("cargo"),
                partido=arguments.get("partido"),
                uf=arguments.get("uf"),
                limit=arguments.get("limit", 20),
            )

        elif name == "get_politico":
            return await self._get_politico(
                politico_id=arguments.get("id"),
                cpf=arguments.get("cpf"),
            )

        elif name == "list_mandatos":
            return await self._list_mandatos(
                politico_id=arguments["politico_id"],
                ativo=arguments.get("ativo"),
            )

        elif name == "get_politicos_por_municipio":
            return await self._get_politicos_por_municipio(
                codigo_ibge=arguments.get("codigo_ibge"),
                municipio_nome=arguments.get("municipio_nome"),
                uf=arguments.get("uf"),
                cargo=arguments.get("cargo"),
                apenas_ativos=arguments.get("apenas_ativos", True),
            )

        elif name == "get_politicos_por_partido":
            return await self._get_politicos_por_partido(
                partido=arguments["partido"],
                uf=arguments.get("uf"),
                cargo=arguments.get("cargo"),
                limit=arguments.get("limit", 50),
            )

        return self._error_response(f"Tool desconhecida: {name}")

    async def _search_politico(
        self,
        nome: str | None = None,
        cargo: str | None = None,
        partido: str | None = None,
        uf: str | None = None,
        limit: int = 20,
    ) -> list[TextContent]:
        """
        Busca políticos por nome, cargo ou partido.

        Args:
            nome: Nome do político (busca parcial)
            cargo: Cargo atual ou pretendido
            partido: Sigla do partido
            uf: UF para filtrar
            limit: Limite de resultados

        Returns:
            Lista de políticos encontrados
        """
        if not nome and not cargo and not partido and not uf:
            return self._error_response("Informe pelo menos um critério de busca")

        try:
            query = self._client.table("politico").select(
                "id, nome_completo, nome_urna, cpf_masked, partido_sigla, "
                "cargo_atual, uf, municipio_nome, foto_url, email"
            )

            if nome:
                query = query.ilike("nome_completo", f"%{nome}%")

            if cargo:
                query = query.eq("cargo_atual", cargo)

            if partido:
                query = query.eq("partido_sigla", partido.upper())

            if uf:
                query = query.eq("uf", uf.upper())

            result = query.limit(limit).execute()

            # Mascarar CPF na resposta
            for politico in result.data:
                if politico.get("cpf_masked"):
                    politico["cpf"] = politico.pop("cpf_masked")

            return self._success_response(
                data=result.data,
                message=f"Encontrados {len(result.data)} políticos",
            )

        except Exception as e:
            self.logger.error("search_politico_error", error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")

    async def _get_politico(
        self,
        politico_id: str | None = None,
        cpf: str | None = None,
    ) -> list[TextContent]:
        """
        Retorna dados completos de um político.

        Args:
            politico_id: ID do político
            cpf: CPF do político (apenas números)

        Returns:
            Dados completos do político
        """
        if not politico_id and not cpf:
            return self._error_response("Informe id ou cpf")

        try:
            query = self._client.table("politico").select("*")

            if politico_id:
                query = query.eq("id", politico_id)
            elif cpf:
                # Busca por CPF (armazenado hasheado ou parcial)
                cpf_clean = cpf.replace(".", "").replace("-", "")
                query = query.eq("cpf", cpf_clean)

            result = query.single().execute()

            if not result.data:
                return self._error_response("Político não encontrado")

            # Mascarar dados sensíveis
            politico = result.data
            if politico.get("cpf"):
                cpf_full = politico["cpf"]
                politico["cpf_masked"] = f"***.***.{cpf_full[-5:-2]}-**"
                del politico["cpf"]

            return self._success_response(
                data=politico,
                message="Político encontrado",
            )

        except Exception as e:
            self.logger.error("get_politico_error", error=str(e))
            return self._error_response(f"Erro ao buscar político: {str(e)}")

    async def _list_mandatos(
        self,
        politico_id: str,
        ativo: bool | None = None,
    ) -> list[TextContent]:
        """
        Lista histórico de mandatos de um político.

        Args:
            politico_id: ID do político
            ativo: Filtrar apenas mandatos ativos

        Returns:
            Lista de mandatos
        """
        try:
            query = (
                self._client.table("mandato_politico")
                .select(
                    "id, cargo, municipio_nome, municipio_codigo_ibge, uf, "
                    "partido_sigla, coligacao, ano_eleicao, data_inicio, data_fim, "
                    "ativo, votos_recebidos, percentual_votos"
                )
                .eq("politico_id", politico_id)
            )

            if ativo is not None:
                query = query.eq("ativo", ativo)

            result = query.order("ano_eleicao", desc=True).execute()

            return self._success_response(
                data=result.data,
                message=f"Encontrados {len(result.data)} mandatos",
            )

        except Exception as e:
            self.logger.error("list_mandatos_error", error=str(e))
            return self._error_response(f"Erro ao buscar mandatos: {str(e)}")

    async def _get_politicos_por_municipio(
        self,
        codigo_ibge: str | None = None,
        municipio_nome: str | None = None,
        uf: str | None = None,
        cargo: str | None = None,
        apenas_ativos: bool = True,
    ) -> list[TextContent]:
        """
        Lista políticos eleitos de um município.

        Args:
            codigo_ibge: Código IBGE do município
            municipio_nome: Nome do município
            uf: UF do município
            cargo: Filtrar por cargo
            apenas_ativos: Retornar apenas mandatos ativos

        Returns:
            Lista de políticos do município
        """
        if not codigo_ibge and not municipio_nome:
            return self._error_response("Informe codigo_ibge ou municipio_nome")

        try:
            # Buscar via mandatos ativos
            query = self._client.table("mandato_politico").select(
                "id, cargo, partido_sigla, ano_eleicao, votos_recebidos, "
                "politico:politico_id ("
                "  id, nome_completo, nome_urna, foto_url, email"
                ")"
            )

            if codigo_ibge:
                query = query.eq("municipio_codigo_ibge", codigo_ibge)
            elif municipio_nome:
                query = query.ilike("municipio_nome", f"%{municipio_nome}%")
                if uf:
                    query = query.eq("uf", uf.upper())

            if cargo:
                query = query.eq("cargo", cargo)

            if apenas_ativos:
                query = query.eq("ativo", True)

            result = query.order("cargo").execute()

            # Flatten politico data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {})
                politicos.append(
                    {
                        **politico_data,
                        "cargo": mandato["cargo"],
                        "partido": mandato["partido_sigla"],
                        "ano_eleicao": mandato["ano_eleicao"],
                        "votos": mandato["votos_recebidos"],
                    }
                )

            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} políticos no município",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_municipio_error", error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")

    async def _get_politicos_por_partido(
        self,
        partido: str,
        uf: str | None = None,
        cargo: str | None = None,
        limit: int = 50,
    ) -> list[TextContent]:
        """
        Lista políticos de um partido.

        Args:
            partido: Sigla do partido
            uf: Filtrar por UF
            cargo: Filtrar por cargo
            limit: Limite de resultados

        Returns:
            Lista de políticos do partido
        """
        try:
            query = (
                self._client.table("politico")
                .select(
                    "id, nome_completo, nome_urna, cargo_atual, uf, "
                    "municipio_nome, foto_url"
                )
                .eq("partido_sigla", partido.upper())
            )

            if uf:
                query = query.eq("uf", uf.upper())

            if cargo:
                query = query.eq("cargo_atual", cargo)

            result = query.limit(limit).execute()

            return self._success_response(
                data=result.data,
                message=f"Encontrados {len(result.data)} políticos do {partido.upper()}",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_partido_error", error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = FiscalMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
