"""
Perplexity MCP Server
AI Research com citações via Perplexity

Fonte: https://www.perplexity.ai
Requer API key.
"""

from typing import Any

from mcp.types import TextContent, Tool

from src.scrapers.perplexity import PerplexityClient

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class PerplexityMCPServer(BaseMCPServer):
    """
    MCP Server para Perplexity AI.

    Pesquisa com IA e citações de fontes.

    Tools disponíveis:
    - research_company: Pesquisa detalhada sobre uma empresa
    - analyze_market: Análise de mercado/setor
    - find_competitors: Encontra concorrentes de uma empresa
    - search_ai: Pesquisa geral com IA
    """

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("perplexity-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Inicializar cliente Perplexity
        if not self.config.perplexity_api_key:
            self.logger.warning("perplexity_not_configured")
            self._client: PerplexityClient | None = None
        else:
            self._client = PerplexityClient(api_key=self.config.perplexity_api_key)

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="research_company",
                description="Pesquisa detalhada sobre uma empresa usando IA. Retorna análise com citações de fontes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                        "analysis_type": {
                            "type": "string",
                            "description": "Tipo de análise",
                            "enum": ["full", "swot", "competitors", "market"],
                            "default": "full",
                        },
                    },
                    "required": ["company_name"],
                },
            ),
            Tool(
                name="analyze_market",
                description="Análise de mercado/setor no Brasil. Inclui tamanho, tendências, players e perspectivas.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "industry": {
                            "type": "string",
                            "description": "Setor/indústria para analisar (ex: 'fintech', 'agronegócio')",
                        },
                        "aspects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Aspectos específicos para cobrir",
                        },
                    },
                    "required": ["industry"],
                },
            ),
            Tool(
                name="find_competitors",
                description="Encontra e analisa concorrentes diretos de uma empresa no Brasil",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                        "industry": {
                            "type": "string",
                            "description": "Setor (melhora precisão)",
                        },
                    },
                    "required": ["company_name"],
                },
            ),
            Tool(
                name="search_ai",
                description="Pesquisa geral com IA. Retorna resposta com citações de fontes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Pergunta ou tópico para pesquisar",
                        },
                        "depth": {
                            "type": "string",
                            "description": "Profundidade da pesquisa",
                            "enum": ["brief", "detailed", "comprehensive"],
                            "default": "detailed",
                        },
                        "focus_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Áreas específicas para focar",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="research_person",
                description="Pesquisa sobre uma pessoa (profissional, acadêmico ou público)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nome da pessoa",
                        },
                        "context": {
                            "type": "string",
                            "description": "Contexto (empresa, cargo)",
                        },
                        "focus": {
                            "type": "string",
                            "description": "Foco da pesquisa",
                            "enum": ["professional", "academic", "public"],
                            "default": "professional",
                        },
                    },
                    "required": ["name"],
                },
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._client:
            return self._error_response(
                "Perplexity não configurado. Configure PERPLEXITY_API_KEY no .env"
            )

        try:
            if name == "research_company":
                return await self._research_company(
                    arguments["company_name"],
                    arguments.get("analysis_type", "full"),
                )

            elif name == "analyze_market":
                return await self._analyze_market(
                    arguments["industry"],
                    arguments.get("aspects"),
                )

            elif name == "find_competitors":
                return await self._find_competitors(
                    arguments["company_name"],
                    arguments.get("industry"),
                )

            elif name == "search_ai":
                return await self._search_ai(
                    arguments["query"],
                    arguments.get("depth", "detailed"),
                    arguments.get("focus_areas"),
                )

            elif name == "research_person":
                return await self._research_person(
                    arguments["name"],
                    arguments.get("context"),
                    arguments.get("focus", "professional"),
                )

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("perplexity_tool_error", tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    async def _research_company(
        self, company_name: str, analysis_type: str = "full"
    ) -> list[TextContent]:
        """Pesquisa detalhada sobre uma empresa"""
        result = await self._client.analyze_company(company_name, analysis_type)

        return self._success_response(
            data={
                "company_name": company_name,
                "analysis_type": analysis_type,
                "analysis": result.get("analysis"),
                "citations": result.get("citations", []),
            },
            message=f"Análise {analysis_type} concluída para {company_name}",
        )

    async def _analyze_market(
        self, industry: str, aspects: list[str] | None = None
    ) -> list[TextContent]:
        """Análise de mercado/setor"""
        result = await self._client.analyze_market(industry, aspects)

        return self._success_response(
            data={
                "industry": industry,
                "aspects": aspects or result.get("aspects"),
                "analysis": result.get("analysis"),
                "citations": result.get("citations", []),
            },
            message=f"Análise de mercado concluída para {industry}",
        )

    async def _find_competitors(
        self, company_name: str, industry: str | None = None
    ) -> list[TextContent]:
        """Encontra concorrentes"""
        result = await self._client.find_competitors(company_name, industry)

        return self._success_response(
            data={
                "company_name": company_name,
                "industry": industry,
                "competitors_analysis": result.get("competitors_analysis"),
                "citations": result.get("citations", []),
            },
            message=f"Concorrentes identificados para {company_name}",
        )

    async def _search_ai(
        self,
        query: str,
        depth: str = "detailed",
        focus_areas: list[str] | None = None,
    ) -> list[TextContent]:
        """Pesquisa geral com IA"""
        result = await self._client.research(query, depth, focus_areas)

        return self._success_response(
            data={
                "query": query,
                "depth": depth,
                "answer": result.get("answer"),
                "citations": result.get("citations", []),
            },
            message="Pesquisa concluída",
        )

    async def _research_person(
        self, name: str, context: str | None = None, focus: str = "professional"
    ) -> list[TextContent]:
        """Pesquisa sobre uma pessoa"""
        result = await self._client.research_person(name, context, focus)

        return self._success_response(
            data={
                "name": name,
                "context": context,
                "focus": focus,
                "profile": result.get("profile"),
                "citations": result.get("citations", []),
            },
            message=f"Perfil encontrado para {name}",
        )


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = PerplexityMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
