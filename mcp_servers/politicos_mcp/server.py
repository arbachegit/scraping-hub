"""
Politicos MCP Server
Acesso a dados de politicos brasileiros via brasil-data-hub

Fonte: Supabase brasil-data-hub (mnfjkegtynjtgesfphge)
Tabelas: dim_politicos, fato_politicos_mandatos
"""

from typing import Any

from mcp.types import TextContent, Tool
from supabase import Client, create_client

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class PoliticosMCPServer(BaseMCPServer):
    """
    MCP Server para dados de politicos brasileiros via brasil-data-hub.

    Acessa as tabelas dim_politicos e fato_politicos_mandatos do Supabase
    brasil-data-hub para fornecer informacoes sobre politicos e mandatos.

    Tools disponiveis:
    - search_politicos: Busca politicos por nome
    - get_politico: Retorna dados de um politico especifico
    - list_mandatos: Lista mandatos de um politico
    - get_politicos_por_municipio: Lista politicos de um municipio
    - get_politicos_por_cargo: Lista politicos por cargo
    - get_politicos_por_partido: Lista politicos de um partido
    """

    # Metadados para rastreabilidade
    SOURCE_NAME = "Brasil Data Hub - Politicos"
    SOURCE_PROVIDER = "TSE via brasil-data-hub"
    SOURCE_CATEGORY = "eleitoral"

    # Schema das tabelas no brasil-data-hub
    SCHEMA = "public"  # Ajustar se estiver em outro schema

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configuracoes (usa default se nao fornecido)
        """
        super().__init__("politicos-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Inicializar cliente Supabase (brasil-data-hub)
        if not self.config.brasil_data_hub_url or not self.config.brasil_data_hub_key:
            self.logger.warning("brasil_data_hub_not_configured")
            self._client: Client | None = None
        else:
            self._client = create_client(
                self.config.brasil_data_hub_url,
                self.config.brasil_data_hub_key,
            )

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponiveis"""
        return [
            Tool(
                name="search_politicos",
                description="Busca politicos por nome, retornando dados cadastrais",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "nome": {
                            "type": "string",
                            "description": "Nome do politico (busca parcial em nome_completo ou nome_urna)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limite de resultados (default: 20, max: 100)",
                            "default": 20,
                        },
                    },
                    "required": ["nome"],
                },
            ),
            Tool(
                name="get_politico",
                description="Retorna dados completos de um politico por ID ou CPF",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "ID (UUID) do politico no banco",
                        },
                        "cpf": {
                            "type": "string",
                            "description": "CPF do politico (apenas numeros)",
                        },
                    },
                },
            ),
            Tool(
                name="list_mandatos",
                description="Lista historico de mandatos de um politico",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "politico_id": {
                            "type": "string",
                            "description": "ID (UUID) do politico",
                        },
                        "apenas_eleitos": {
                            "type": "boolean",
                            "description": "Filtrar apenas mandatos eleitos (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["politico_id"],
                },
            ),
            Tool(
                name="get_politicos_por_municipio",
                description="Lista politicos com mandatos em um municipio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "codigo_ibge": {
                            "type": "string",
                            "description": "Codigo IBGE do municipio (7 digitos)",
                        },
                        "municipio": {
                            "type": "string",
                            "description": "Nome do municipio (busca parcial)",
                        },
                        "cargo": {
                            "type": "string",
                            "description": "Filtrar por cargo (ex: PREFEITO, VEREADOR)",
                        },
                        "ano_eleicao": {
                            "type": "integer",
                            "description": "Filtrar por ano da eleicao",
                        },
                        "apenas_eleitos": {
                            "type": "boolean",
                            "description": "Filtrar apenas eleitos (default: true)",
                            "default": True,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limite de resultados (default: 50)",
                            "default": 50,
                        },
                    },
                },
            ),
            Tool(
                name="get_politicos_por_cargo",
                description="Lista politicos por cargo",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cargo": {
                            "type": "string",
                            "description": "Cargo (ex: PREFEITO, VICE-PREFEITO, VEREADOR)",
                        },
                        "codigo_ibge_uf": {
                            "type": "string",
                            "description": "Codigo IBGE da UF (2 digitos) para filtrar",
                        },
                        "ano_eleicao": {
                            "type": "integer",
                            "description": "Filtrar por ano da eleicao",
                        },
                        "apenas_eleitos": {
                            "type": "boolean",
                            "description": "Filtrar apenas eleitos (default: true)",
                            "default": True,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limite de resultados (default: 50)",
                            "default": 50,
                        },
                    },
                    "required": ["cargo"],
                },
            ),
            Tool(
                name="get_politicos_por_partido",
                description="Lista politicos de um partido",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "partido_sigla": {
                            "type": "string",
                            "description": "Sigla do partido (ex: PT, PL, MDB, PSDB)",
                        },
                        "partido_nome": {
                            "type": "string",
                            "description": "Nome do partido (busca parcial)",
                        },
                        "codigo_ibge_uf": {
                            "type": "string",
                            "description": "Codigo IBGE da UF (2 digitos) para filtrar",
                        },
                        "cargo": {
                            "type": "string",
                            "description": "Filtrar por cargo",
                        },
                        "ano_eleicao": {
                            "type": "integer",
                            "description": "Filtrar por ano da eleicao",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Limite de resultados (default: 50)",
                            "default": 50,
                        },
                    },
                },
            ),
        ]

    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._client:
            return self._error_response(
                "Brasil Data Hub nao configurado. "
                "Configure BRASIL_DATA_HUB_URL e BRASIL_DATA_HUB_KEY no .env"
            )

        if name == "search_politicos":
            return await self._search_politicos(
                nome=arguments["nome"],
                limit=min(arguments.get("limit", 20), 100),
            )

        elif name == "get_politico":
            return await self._get_politico(
                politico_id=arguments.get("id"),
                cpf=arguments.get("cpf"),
            )

        elif name == "list_mandatos":
            return await self._list_mandatos(
                politico_id=arguments["politico_id"],
                apenas_eleitos=arguments.get("apenas_eleitos", False),
            )

        elif name == "get_politicos_por_municipio":
            return await self._get_politicos_por_municipio(
                codigo_ibge=arguments.get("codigo_ibge"),
                municipio=arguments.get("municipio"),
                cargo=arguments.get("cargo"),
                ano_eleicao=arguments.get("ano_eleicao"),
                apenas_eleitos=arguments.get("apenas_eleitos", True),
                limit=arguments.get("limit", 50),
            )

        elif name == "get_politicos_por_cargo":
            return await self._get_politicos_por_cargo(
                cargo=arguments["cargo"],
                codigo_ibge_uf=arguments.get("codigo_ibge_uf"),
                ano_eleicao=arguments.get("ano_eleicao"),
                apenas_eleitos=arguments.get("apenas_eleitos", True),
                limit=arguments.get("limit", 50),
            )

        elif name == "get_politicos_por_partido":
            return await self._get_politicos_por_partido(
                partido_sigla=arguments.get("partido_sigla"),
                partido_nome=arguments.get("partido_nome"),
                codigo_ibge_uf=arguments.get("codigo_ibge_uf"),
                cargo=arguments.get("cargo"),
                ano_eleicao=arguments.get("ano_eleicao"),
                limit=arguments.get("limit", 50),
            )

        return self._error_response(f"Tool desconhecida: {name}")

    async def _search_politicos(
        self,
        nome: str,
        limit: int = 20,
    ) -> list[TextContent]:
        """
        Busca politicos por nome.

        Args:
            nome: Nome do politico (busca parcial)
            limit: Limite de resultados

        Returns:
            Lista de politicos encontrados
        """
        try:
            # Busca em nome_completo e nome_urna
            query = (
                self._client.table("dim_politicos")
                .select("id, nome_completo, nome_urna, sexo, ocupacao, grau_instrucao")
                .or_(f"nome_completo.ilike.%{nome}%,nome_urna.ilike.%{nome}%")
                .limit(limit)
            )

            result = query.execute()

            return self._success_response(
                data=result.data,
                message=f"Encontrados {len(result.data)} politicos",
            )

        except Exception as e:
            self.logger.error("search_politicos_error", error=str(e))
            return self._error_response(f"Erro ao buscar politicos: {str(e)}")

    async def _get_politico(
        self,
        politico_id: str | None = None,
        cpf: str | None = None,
    ) -> list[TextContent]:
        """
        Retorna dados completos de um politico.

        Args:
            politico_id: ID do politico
            cpf: CPF do politico (apenas numeros)

        Returns:
            Dados completos do politico
        """
        if not politico_id and not cpf:
            return self._error_response("Informe id ou cpf")

        try:
            query = self._client.table("dim_politicos").select(
                "id, nome_completo, nome_urna, sexo, data_nascimento, "
                "ocupacao, grau_instrucao, criado_em, atualizado_em"
            )

            if politico_id:
                query = query.eq("id", politico_id)
            elif cpf:
                cpf_clean = cpf.replace(".", "").replace("-", "")
                query = query.eq("cpf", cpf_clean)

            result = query.single().execute()

            if not result.data:
                return self._error_response("Politico nao encontrado")

            return self._success_response(
                data=result.data,
                message="Politico encontrado",
            )

        except Exception as e:
            self.logger.error("get_politico_error", error=str(e))
            return self._error_response(f"Erro ao buscar politico: {str(e)}")

    async def _list_mandatos(
        self,
        politico_id: str,
        apenas_eleitos: bool = False,
    ) -> list[TextContent]:
        """
        Lista historico de mandatos de um politico.

        Args:
            politico_id: ID do politico
            apenas_eleitos: Filtrar apenas mandatos eleitos

        Returns:
            Lista de mandatos
        """
        try:
            query = (
                self._client.table("fato_politicos_mandatos")
                .select(
                    "id, cargo, municipio, codigo_ibge, partido_sigla, partido_nome, "
                    "coligacao, ano_eleicao, turno, numero_candidato, eleito, "
                    "situacao_turno, data_inicio_mandato, data_fim_mandato"
                )
                .eq("politico_id", politico_id)
            )

            if apenas_eleitos:
                query = query.eq("eleito", True)

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
        municipio: str | None = None,
        cargo: str | None = None,
        ano_eleicao: int | None = None,
        apenas_eleitos: bool = True,
        limit: int = 50,
    ) -> list[TextContent]:
        """
        Lista politicos com mandatos em um municipio.

        Args:
            codigo_ibge: Codigo IBGE do municipio
            municipio: Nome do municipio
            cargo: Filtrar por cargo
            ano_eleicao: Filtrar por ano da eleicao
            apenas_eleitos: Retornar apenas eleitos
            limit: Limite de resultados

        Returns:
            Lista de politicos do municipio com dados do mandato
        """
        if not codigo_ibge and not municipio:
            return self._error_response("Informe codigo_ibge ou municipio")

        try:
            # Buscar mandatos com join em dim_politicos
            query = self._client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, coligacao, "
                "ano_eleicao, turno, numero_candidato, eleito, situacao_turno, "
                "municipio, codigo_ibge, "
                "politico:politico_id (id, nome_completo, nome_urna, sexo, ocupacao)"
            )

            if codigo_ibge:
                query = query.eq("codigo_ibge", codigo_ibge)
            elif municipio:
                query = query.ilike("municipio", f"%{municipio}%")

            if cargo:
                query = query.ilike("cargo", f"%{cargo}%")

            if ano_eleicao:
                query = query.eq("ano_eleicao", ano_eleicao)

            if apenas_eleitos:
                query = query.eq("eleito", True)

            result = query.order("cargo").limit(limit).execute()

            # Flatten politico data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {}) or {}
                politicos.append(
                    {
                        **politico_data,
                        "mandato": {
                            "id": mandato["id"],
                            "cargo": mandato["cargo"],
                            "partido_sigla": mandato["partido_sigla"],
                            "partido_nome": mandato["partido_nome"],
                            "coligacao": mandato["coligacao"],
                            "ano_eleicao": mandato["ano_eleicao"],
                            "turno": mandato["turno"],
                            "numero_candidato": mandato["numero_candidato"],
                            "eleito": mandato["eleito"],
                            "situacao_turno": mandato["situacao_turno"],
                            "municipio": mandato["municipio"],
                            "codigo_ibge": mandato["codigo_ibge"],
                        },
                    }
                )

            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} politicos no municipio",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_municipio_error", error=str(e))
            return self._error_response(f"Erro ao buscar politicos: {str(e)}")

    async def _get_politicos_por_cargo(
        self,
        cargo: str,
        codigo_ibge_uf: str | None = None,
        ano_eleicao: int | None = None,
        apenas_eleitos: bool = True,
        limit: int = 50,
    ) -> list[TextContent]:
        """
        Lista politicos por cargo.

        Args:
            cargo: Cargo (ex: PREFEITO, VEREADOR)
            codigo_ibge_uf: Codigo IBGE da UF para filtrar
            ano_eleicao: Filtrar por ano da eleicao
            apenas_eleitos: Retornar apenas eleitos
            limit: Limite de resultados

        Returns:
            Lista de politicos por cargo
        """
        try:
            query = self._client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, ano_eleicao, "
                "eleito, situacao_turno, municipio, codigo_ibge, codigo_ibge_uf, "
                "politico:politico_id (id, nome_completo, nome_urna, sexo)"
            )

            query = query.ilike("cargo", f"%{cargo}%")

            if codigo_ibge_uf:
                query = query.eq("codigo_ibge_uf", codigo_ibge_uf)

            if ano_eleicao:
                query = query.eq("ano_eleicao", ano_eleicao)

            if apenas_eleitos:
                query = query.eq("eleito", True)

            result = query.order("municipio").limit(limit).execute()

            # Flatten politico data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {}) or {}
                politicos.append(
                    {
                        **politico_data,
                        "mandato": {
                            "cargo": mandato["cargo"],
                            "partido_sigla": mandato["partido_sigla"],
                            "ano_eleicao": mandato["ano_eleicao"],
                            "eleito": mandato["eleito"],
                            "situacao_turno": mandato["situacao_turno"],
                            "municipio": mandato["municipio"],
                            "codigo_ibge": mandato["codigo_ibge"],
                        },
                    }
                )

            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} politicos com cargo {cargo}",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_cargo_error", error=str(e))
            return self._error_response(f"Erro ao buscar politicos: {str(e)}")

    async def _get_politicos_por_partido(
        self,
        partido_sigla: str | None = None,
        partido_nome: str | None = None,
        codigo_ibge_uf: str | None = None,
        cargo: str | None = None,
        ano_eleicao: int | None = None,
        limit: int = 50,
    ) -> list[TextContent]:
        """
        Lista politicos de um partido.

        Args:
            partido_sigla: Sigla do partido
            partido_nome: Nome do partido (busca parcial)
            codigo_ibge_uf: Codigo IBGE da UF para filtrar
            cargo: Filtrar por cargo
            ano_eleicao: Filtrar por ano da eleicao
            limit: Limite de resultados

        Returns:
            Lista de politicos do partido
        """
        if not partido_sigla and not partido_nome:
            return self._error_response("Informe partido_sigla ou partido_nome")

        try:
            query = self._client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, ano_eleicao, "
                "eleito, situacao_turno, municipio, codigo_ibge, codigo_ibge_uf, "
                "politico:politico_id (id, nome_completo, nome_urna, sexo)"
            )

            if partido_sigla:
                query = query.eq("partido_sigla", partido_sigla.upper())
            elif partido_nome:
                query = query.ilike("partido_nome", f"%{partido_nome}%")

            if codigo_ibge_uf:
                query = query.eq("codigo_ibge_uf", codigo_ibge_uf)

            if cargo:
                query = query.ilike("cargo", f"%{cargo}%")

            if ano_eleicao:
                query = query.eq("ano_eleicao", ano_eleicao)

            result = query.order("municipio").limit(limit).execute()

            # Flatten politico data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {}) or {}
                politicos.append(
                    {
                        **politico_data,
                        "mandato": {
                            "cargo": mandato["cargo"],
                            "partido_sigla": mandato["partido_sigla"],
                            "partido_nome": mandato["partido_nome"],
                            "ano_eleicao": mandato["ano_eleicao"],
                            "eleito": mandato["eleito"],
                            "situacao_turno": mandato["situacao_turno"],
                            "municipio": mandato["municipio"],
                            "codigo_ibge": mandato["codigo_ibge"],
                        },
                    }
                )

            partido_display = partido_sigla or partido_nome
            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} politicos do partido {partido_display}",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_partido_error", error=str(e))
            return self._error_response(f"Erro ao buscar politicos: {str(e)}")


# Entry point para execucao via stdio
async def main():
    """Executa MCP server via stdio"""
    server = PoliticosMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
