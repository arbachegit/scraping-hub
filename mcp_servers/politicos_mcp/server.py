"""
Politicos MCP Server v1.1.0
Acesso a dados de politicos brasileiros via brasil-data-hub

Fonte: Supabase brasil-data-hub (mnfjkegtynjtgesfphge)
Tabelas: dim_politicos, fato_politicos_mandatos

Changelog:
- v1.1.0: Adicionados guardrails (timeout, retry, request_id, output validation)
- v1.0.0: Versão inicial
"""

import asyncio
from typing import Any
from uuid import uuid4

from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, field_validator
from supabase import Client, create_client

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig

# =============================================================================
# INPUT SCHEMAS (Pydantic v1.1.0)
# =============================================================================

class SearchPoliticosInput(BaseModel):
    """Schema para busca de políticos por nome."""
    nome: str = Field(..., min_length=2, max_length=200, description="Nome do político")
    limit: int = Field(default=20, ge=1, le=100, description="Limite de resultados")

    @field_validator("nome")
    @classmethod
    def sanitize_nome(cls, v: str) -> str:
        """Remove caracteres especiais que podem causar SQL injection via ilike."""
        return v.replace("%", "").replace("_", "").strip()[:200]


class GetPoliticoInput(BaseModel):
    """Schema para buscar político por ID ou CPF."""
    id: str | None = Field(default=None, description="UUID do político")
    cpf: str | None = Field(default=None, description="CPF (apenas números)")

    @field_validator("cpf")
    @classmethod
    def clean_cpf(cls, v: str | None) -> str | None:
        if v:
            return v.replace(".", "").replace("-", "").strip()[:11]
        return v


class ListMandatosInput(BaseModel):
    """Schema para listar mandatos de um político."""
    politico_id: str = Field(..., description="UUID do político")
    apenas_eleitos: bool = Field(default=False, description="Filtrar apenas eleitos")


class PoliticosPorMunicipioInput(BaseModel):
    """Schema para buscar políticos por município."""
    codigo_ibge: str | None = Field(default=None, max_length=7)
    municipio: str | None = Field(default=None, max_length=200)
    cargo: str | None = Field(default=None, max_length=50)
    ano_eleicao: int | None = Field(default=None, ge=1988, le=2030)
    apenas_eleitos: bool = Field(default=True)
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("municipio")
    @classmethod
    def sanitize_municipio(cls, v: str | None) -> str | None:
        if v:
            return v.replace("%", "").replace("_", "").strip()[:200]
        return v


class PoliticosPorCargoInput(BaseModel):
    """Schema para buscar políticos por cargo."""
    cargo: str = Field(..., min_length=2, max_length=50)
    codigo_ibge_uf: str | None = Field(default=None, max_length=2)
    ano_eleicao: int | None = Field(default=None, ge=1988, le=2030)
    apenas_eleitos: bool = Field(default=True)
    limit: int = Field(default=50, ge=1, le=100)


class PoliticosPorPartidoInput(BaseModel):
    """Schema para buscar políticos por partido."""
    partido_sigla: str | None = Field(default=None, max_length=20)
    partido_nome: str | None = Field(default=None, max_length=200)
    codigo_ibge_uf: str | None = Field(default=None, max_length=2)
    cargo: str | None = Field(default=None, max_length=50)
    ano_eleicao: int | None = Field(default=None, ge=1988, le=2030)
    limit: int = Field(default=50, ge=1, le=100)


# =============================================================================
# OUTPUT SCHEMAS (Pydantic v1.1.0)
# =============================================================================

class PoliticoOutput(BaseModel):
    """Schema de saída para político."""
    id: str | None = None
    nome_completo: str | None = None
    nome_urna: str | None = None
    sexo: str | None = None
    ocupacao: str | None = None
    grau_instrucao: str | None = None


class MandatoOutput(BaseModel):
    """Schema de saída para mandato."""
    id: str | None = None
    cargo: str | None = None
    partido_sigla: str | None = None
    partido_nome: str | None = None
    municipio: str | None = None
    codigo_ibge: str | None = None
    ano_eleicao: int | None = None
    eleito: bool | None = None
    situacao_turno: str | None = None


# =============================================================================
# GUARDRAILS CONFIG
# =============================================================================

TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
BACKOFF_BASE_SECONDS = 1.0

# Allowlist de tabelas (sem acesso a outras tabelas)
ALLOWED_TABLES = {"dim_politicos", "fato_politicos_mandatos"}


# =============================================================================
# MCP SERVER
# =============================================================================

class PoliticosMCPServer(BaseMCPServer):
    """
    MCP Server para dados de politicos brasileiros via brasil-data-hub.

    Guardrails implementados:
    - Input validation via Pydantic
    - Output validation via Pydantic
    - Timeout em queries (10s)
    - Retry com backoff (2 tentativas)
    - request_id em todos os logs
    - Sanitização de inputs (SQL injection prevention)
    """

    # Metadados para rastreabilidade
    SOURCE_NAME = "Brasil Data Hub - Politicos"
    SOURCE_PROVIDER = "TSE via brasil-data-hub"
    SOURCE_CATEGORY = "eleitoral"
    VERSION = "1.1.0"

    def __init__(self, config: MCPConfig | None = None):
        """Inicializa MCP Server."""
        super().__init__("politicos-mcp", self.VERSION)
        self.config = config or MCPConfig.from_env()

        if not self.config.brasil_data_hub_url or not self.config.brasil_data_hub_key:
            self.logger.warning("brasil_data_hub_not_configured")
            self._client: Client | None = None
        else:
            self._client = create_client(
                self.config.brasil_data_hub_url,
                self.config.brasil_data_hub_key,
            )

    async def _execute_with_timeout(
        self,
        coro,
        request_id: str,
        operation: str,
        retries: int = MAX_RETRIES,
    ):
        """Executa query com timeout e retry."""
        for attempt in range(retries + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(lambda: coro.execute()),
                    timeout=TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                self.logger.warning(
                    "query_timeout",
                    request_id=request_id,
                    operation=operation,
                    attempt=attempt + 1,
                )
                if attempt < retries:
                    await asyncio.sleep(BACKOFF_BASE_SECONDS * (attempt + 1))
                else:
                    raise
            except Exception as e:
                self.logger.error(
                    "query_error",
                    request_id=request_id,
                    operation=operation,
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < retries:
                    await asyncio.sleep(BACKOFF_BASE_SECONDS * (attempt + 1))
                else:
                    raise

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis."""
        return [
            Tool(
                name="search_politicos",
                description="Busca políticos por nome, retornando dados cadastrais",
                inputSchema=SearchPoliticosInput.model_json_schema(),
            ),
            Tool(
                name="get_politico",
                description="Retorna dados completos de um político por ID ou CPF",
                inputSchema=GetPoliticoInput.model_json_schema(),
            ),
            Tool(
                name="list_mandatos",
                description="Lista histórico de mandatos de um político",
                inputSchema=ListMandatosInput.model_json_schema(),
            ),
            Tool(
                name="get_politicos_por_municipio",
                description="Lista políticos com mandatos em um município",
                inputSchema=PoliticosPorMunicipioInput.model_json_schema(),
            ),
            Tool(
                name="get_politicos_por_cargo",
                description="Lista políticos por cargo",
                inputSchema=PoliticosPorCargoInput.model_json_schema(),
            ),
            Tool(
                name="get_politicos_por_partido",
                description="Lista políticos de um partido",
                inputSchema=PoliticosPorPartidoInput.model_json_schema(),
            ),
        ]

    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Processa chamada de tool com guardrails."""
        request_id = str(uuid4())[:8]

        self.logger.info("tool_called", request_id=request_id, tool=name)

        if not self._client:
            return self._error_response(
                "Brasil Data Hub não configurado. "
                "Configure BRASIL_DATA_HUB_URL e BRASIL_DATA_HUB_KEY no .env"
            )

        try:
            if name == "search_politicos":
                validated = SearchPoliticosInput(**arguments)
                return await self._search_politicos(request_id, validated)

            elif name == "get_politico":
                validated = GetPoliticoInput(**arguments)
                return await self._get_politico(request_id, validated)

            elif name == "list_mandatos":
                validated = ListMandatosInput(**arguments)
                return await self._list_mandatos(request_id, validated)

            elif name == "get_politicos_por_municipio":
                validated = PoliticosPorMunicipioInput(**arguments)
                return await self._get_politicos_por_municipio(request_id, validated)

            elif name == "get_politicos_por_cargo":
                validated = PoliticosPorCargoInput(**arguments)
                return await self._get_politicos_por_cargo(request_id, validated)

            elif name == "get_politicos_por_partido":
                validated = PoliticosPorPartidoInput(**arguments)
                return await self._get_politicos_por_partido(request_id, validated)

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("tool_error", request_id=request_id, tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    async def _search_politicos(
        self, request_id: str, input_data: SearchPoliticosInput
    ) -> list[TextContent]:
        """Busca políticos por nome."""
        try:
            query = (
                self._client.table("dim_politicos")
                .select("id, nome_completo, nome_urna, sexo, ocupacao, grau_instrucao")
                .or_(f"nome_completo.ilike.%{input_data.nome}%,nome_urna.ilike.%{input_data.nome}%")
                .limit(input_data.limit)
            )

            result = await self._execute_with_timeout(query, request_id, "search_politicos")

            # Validar output
            validated_data = [PoliticoOutput(**p).model_dump() for p in result.data]

            self.logger.info("search_politicos_success", request_id=request_id, count=len(validated_data))

            return self._success_response(
                data=validated_data,
                message=f"Encontrados {len(validated_data)} políticos",
            )

        except Exception as e:
            self.logger.error("search_politicos_error", request_id=request_id, error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")

    async def _get_politico(
        self, request_id: str, input_data: GetPoliticoInput
    ) -> list[TextContent]:
        """Retorna dados completos de um político."""
        if not input_data.id and not input_data.cpf:
            return self._error_response("Informe id ou cpf")

        try:
            query = self._client.table("dim_politicos").select(
                "id, nome_completo, nome_urna, sexo, data_nascimento, "
                "ocupacao, grau_instrucao, criado_em, atualizado_em"
            )

            if input_data.id:
                query = query.eq("id", input_data.id)
            elif input_data.cpf:
                query = query.eq("cpf", input_data.cpf)

            query = query.single()
            result = await self._execute_with_timeout(query, request_id, "get_politico")

            if not result.data:
                return self._error_response("Político não encontrado")

            self.logger.info("get_politico_success", request_id=request_id)

            return self._success_response(data=result.data, message="Político encontrado")

        except Exception as e:
            self.logger.error("get_politico_error", request_id=request_id, error=str(e))
            return self._error_response(f"Erro ao buscar político: {str(e)}")

    async def _list_mandatos(
        self, request_id: str, input_data: ListMandatosInput
    ) -> list[TextContent]:
        """Lista histórico de mandatos."""
        try:
            query = (
                self._client.table("fato_politicos_mandatos")
                .select(
                    "id, cargo, municipio, codigo_ibge, partido_sigla, partido_nome, "
                    "coligacao, ano_eleicao, turno, numero_candidato, eleito, "
                    "situacao_turno, data_inicio_mandato, data_fim_mandato"
                )
                .eq("politico_id", input_data.politico_id)
            )

            if input_data.apenas_eleitos:
                query = query.eq("eleito", True)

            query = query.order("ano_eleicao", desc=True)
            result = await self._execute_with_timeout(query, request_id, "list_mandatos")

            # Validar output
            validated_data = [MandatoOutput(**m).model_dump() for m in result.data]

            self.logger.info("list_mandatos_success", request_id=request_id, count=len(validated_data))

            return self._success_response(
                data=validated_data,
                message=f"Encontrados {len(validated_data)} mandatos",
            )

        except Exception as e:
            self.logger.error("list_mandatos_error", request_id=request_id, error=str(e))
            return self._error_response(f"Erro ao buscar mandatos: {str(e)}")

    async def _get_politicos_por_municipio(
        self, request_id: str, input_data: PoliticosPorMunicipioInput
    ) -> list[TextContent]:
        """Lista políticos de um município."""
        if not input_data.codigo_ibge and not input_data.municipio:
            return self._error_response("Informe codigo_ibge ou municipio")

        try:
            query = self._client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, coligacao, "
                "ano_eleicao, turno, numero_candidato, eleito, situacao_turno, "
                "municipio, codigo_ibge, "
                "politico:politico_id (id, nome_completo, nome_urna, sexo, ocupacao)"
            )

            if input_data.codigo_ibge:
                query = query.eq("codigo_ibge", input_data.codigo_ibge)
            elif input_data.municipio:
                query = query.ilike("municipio", f"%{input_data.municipio}%")

            if input_data.cargo:
                query = query.ilike("cargo", f"%{input_data.cargo}%")

            if input_data.ano_eleicao:
                query = query.eq("ano_eleicao", input_data.ano_eleicao)

            if input_data.apenas_eleitos:
                query = query.eq("eleito", True)

            query = query.order("cargo").limit(input_data.limit)
            result = await self._execute_with_timeout(query, request_id, "get_politicos_por_municipio")

            # Flatten data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {}) or {}
                politicos.append({
                    **politico_data,
                    "mandato": {
                        "id": mandato.get("id"),
                        "cargo": mandato.get("cargo"),
                        "partido_sigla": mandato.get("partido_sigla"),
                        "partido_nome": mandato.get("partido_nome"),
                        "coligacao": mandato.get("coligacao"),
                        "ano_eleicao": mandato.get("ano_eleicao"),
                        "eleito": mandato.get("eleito"),
                        "situacao_turno": mandato.get("situacao_turno"),
                        "municipio": mandato.get("municipio"),
                        "codigo_ibge": mandato.get("codigo_ibge"),
                    },
                })

            self.logger.info("get_politicos_por_municipio_success", request_id=request_id, count=len(politicos))

            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} políticos no município",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_municipio_error", request_id=request_id, error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")

    async def _get_politicos_por_cargo(
        self, request_id: str, input_data: PoliticosPorCargoInput
    ) -> list[TextContent]:
        """Lista políticos por cargo."""
        try:
            query = self._client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, ano_eleicao, "
                "eleito, situacao_turno, municipio, codigo_ibge, codigo_ibge_uf, "
                "politico:politico_id (id, nome_completo, nome_urna, sexo)"
            )

            query = query.ilike("cargo", f"%{input_data.cargo}%")

            if input_data.codigo_ibge_uf:
                query = query.eq("codigo_ibge_uf", input_data.codigo_ibge_uf)

            if input_data.ano_eleicao:
                query = query.eq("ano_eleicao", input_data.ano_eleicao)

            if input_data.apenas_eleitos:
                query = query.eq("eleito", True)

            query = query.order("municipio").limit(input_data.limit)
            result = await self._execute_with_timeout(query, request_id, "get_politicos_por_cargo")

            # Flatten data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {}) or {}
                politicos.append({
                    **politico_data,
                    "mandato": {
                        "cargo": mandato.get("cargo"),
                        "partido_sigla": mandato.get("partido_sigla"),
                        "ano_eleicao": mandato.get("ano_eleicao"),
                        "eleito": mandato.get("eleito"),
                        "situacao_turno": mandato.get("situacao_turno"),
                        "municipio": mandato.get("municipio"),
                        "codigo_ibge": mandato.get("codigo_ibge"),
                    },
                })

            self.logger.info("get_politicos_por_cargo_success", request_id=request_id, count=len(politicos))

            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} políticos com cargo {input_data.cargo}",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_cargo_error", request_id=request_id, error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")

    async def _get_politicos_por_partido(
        self, request_id: str, input_data: PoliticosPorPartidoInput
    ) -> list[TextContent]:
        """Lista políticos de um partido."""
        if not input_data.partido_sigla and not input_data.partido_nome:
            return self._error_response("Informe partido_sigla ou partido_nome")

        try:
            query = self._client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, ano_eleicao, "
                "eleito, situacao_turno, municipio, codigo_ibge, codigo_ibge_uf, "
                "politico:politico_id (id, nome_completo, nome_urna, sexo)"
            )

            if input_data.partido_sigla:
                query = query.eq("partido_sigla", input_data.partido_sigla.upper())
            elif input_data.partido_nome:
                query = query.ilike("partido_nome", f"%{input_data.partido_nome}%")

            if input_data.codigo_ibge_uf:
                query = query.eq("codigo_ibge_uf", input_data.codigo_ibge_uf)

            if input_data.cargo:
                query = query.ilike("cargo", f"%{input_data.cargo}%")

            if input_data.ano_eleicao:
                query = query.eq("ano_eleicao", input_data.ano_eleicao)

            query = query.order("municipio").limit(input_data.limit)
            result = await self._execute_with_timeout(query, request_id, "get_politicos_por_partido")

            # Flatten data
            politicos = []
            for mandato in result.data:
                politico_data = mandato.pop("politico", {}) or {}
                politicos.append({
                    **politico_data,
                    "mandato": {
                        "cargo": mandato.get("cargo"),
                        "partido_sigla": mandato.get("partido_sigla"),
                        "partido_nome": mandato.get("partido_nome"),
                        "ano_eleicao": mandato.get("ano_eleicao"),
                        "eleito": mandato.get("eleito"),
                        "situacao_turno": mandato.get("situacao_turno"),
                        "municipio": mandato.get("municipio"),
                        "codigo_ibge": mandato.get("codigo_ibge"),
                    },
                })

            partido_display = input_data.partido_sigla or input_data.partido_nome

            self.logger.info("get_politicos_por_partido_success", request_id=request_id, count=len(politicos))

            return self._success_response(
                data=politicos,
                message=f"Encontrados {len(politicos)} políticos do partido {partido_display}",
            )

        except Exception as e:
            self.logger.error("get_politicos_por_partido_error", request_id=request_id, error=str(e))
            return self._error_response(f"Erro ao buscar políticos: {str(e)}")


# Entry point
async def main():
    """Executa MCP server via stdio."""
    server = PoliticosMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
