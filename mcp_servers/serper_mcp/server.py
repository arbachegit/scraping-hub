"""
Serper MCP Server
Google Search via Serper.dev

Encapsula o SerperClient existente como MCP Server.
"""

from typing import Any

from mcp.types import TextContent, Tool

from src.scrapers.serper import SerperClient

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class SerperMCPServer(BaseMCPServer):
    """
    MCP Server para Google Search via Serper.

    Reutiliza o SerperClient existente, expondo suas
    funcionalidades como tools MCP padronizadas.

    Tools disponíveis:
    - search_company: Busca empresa por nome e cidade
    - find_cnpj: Encontra CNPJ de uma empresa
    - find_linkedin: Encontra LinkedIn de empresa ou pessoa
    - find_website: Encontra website oficial de empresa
    - search_news: Busca notícias sobre um tema
    """

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("serper-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Inicializar cliente Serper
        if not self.config.serper_api_key:
            self.logger.warning("serper_not_configured")
            self._client: SerperClient | None = None
        else:
            self._client = SerperClient(api_key=self.config.serper_api_key)

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="search_company",
                description="Busca empresa por nome e cidade via Google Search. Retorna resultados orgânicos, knowledge graph e informações básicas.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa para buscar",
                        },
                        "cidade": {
                            "type": "string",
                            "description": "Cidade da empresa (opcional, melhora precisão)",
                        },
                    },
                    "required": ["company_name"],
                },
            ),
            Tool(
                name="find_cnpj",
                description="Encontra CNPJ de uma empresa pelo nome. Busca em sites especializados como cnpj.info e consultacnpj.com.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                        "cidade": {
                            "type": "string",
                            "description": "Cidade (opcional, melhora precisão)",
                        },
                    },
                    "required": ["company_name"],
                },
            ),
            Tool(
                name="find_linkedin",
                description="Encontra página LinkedIn de empresa ou pessoa",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nome da empresa ou pessoa",
                        },
                        "company": {
                            "type": "string",
                            "description": "Empresa (apenas para busca de pessoa)",
                        },
                        "type": {
                            "type": "string",
                            "description": "Tipo de busca: 'company' ou 'person'",
                            "enum": ["company", "person"],
                            "default": "company",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="find_website",
                description="Encontra website oficial de uma empresa",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                    },
                    "required": ["company_name"],
                },
            ),
            Tool(
                name="search_news",
                description="Busca notícias sobre um tema ou empresa",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Termo de busca",
                        },
                        "period": {
                            "type": "string",
                            "description": "Período: 'day', 'week', 'month'",
                            "enum": ["day", "week", "month"],
                            "default": "week",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Número de resultados (max 10)",
                            "default": 5,
                            "maximum": 10,
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._client:
            return self._error_response(
                "Serper não configurado. Configure SERPER_API_KEY no .env"
            )

        try:
            if name == "search_company":
                return await self._search_company(
                    arguments["company_name"],
                    arguments.get("cidade"),
                )

            elif name == "find_cnpj":
                return await self._find_cnpj(
                    arguments["company_name"],
                    arguments.get("cidade"),
                )

            elif name == "find_linkedin":
                return await self._find_linkedin(
                    arguments["name"],
                    arguments.get("company"),
                    arguments.get("type", "company"),
                )

            elif name == "find_website":
                return await self._find_website(arguments["company_name"])

            elif name == "search_news":
                return await self._search_news(
                    arguments["query"],
                    arguments.get("period", "week"),
                    arguments.get("num_results", 5),
                )

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("serper_tool_error", tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    async def _search_company(
        self, company_name: str, cidade: str | None = None
    ) -> list[TextContent]:
        """Busca informações completas de uma empresa"""
        query = f'"{company_name}"'
        if cidade:
            query += f" {cidade}"
        query += " empresa Brasil"

        result = await self._client.find_company_info(company_name)

        return self._success_response(
            data={
                "company_name": company_name,
                "cidade": cidade,
                "website": result.get("website"),
                "description": result.get("description"),
                "industry": result.get("industry"),
                "founded": result.get("founded"),
                "headquarters": result.get("headquarters"),
                "employees": result.get("employees"),
                "knowledge_graph": result.get("knowledge_graph"),
                "search_results": result.get("search_results", [])[:5],
                "news": result.get("news", [])[:3],
            },
            message=f"Busca concluída para {company_name}",
        )

    async def _find_cnpj(
        self, company_name: str, cidade: str | None = None
    ) -> list[TextContent]:
        """Encontra CNPJ de uma empresa"""
        # SerperClient não usa cidade no find_company_cnpj
        # Mas podemos melhorar a busca incluindo cidade na query
        if cidade:
            # Fazer busca customizada com cidade
            query = f'"{company_name}" "{cidade}" CNPJ site:cnpj.info OR site:consultacnpj.com'
            results = await self._client.search(query, num=5)

            import re

            cnpj_pattern = r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"

            for item in results.get("organic", []):
                text = f"{item.get('title', '')} {item.get('snippet', '')}"
                match = re.search(cnpj_pattern, text)
                if match:
                    cnpj = "".join(filter(str.isdigit, match.group()))
                    return self._success_response(
                        data={"cnpj": cnpj, "source": "serper"},
                        message=f"CNPJ encontrado para {company_name}",
                    )

        # Fallback para método padrão
        cnpj = await self._client.find_company_cnpj(company_name)

        if cnpj:
            return self._success_response(
                data={"cnpj": cnpj, "source": "serper"},
                message=f"CNPJ encontrado para {company_name}",
            )

        return self._error_response(f"CNPJ não encontrado para {company_name}")

    async def _find_linkedin(
        self, name: str, company: str | None = None, search_type: str = "company"
    ) -> list[TextContent]:
        """Encontra LinkedIn de empresa ou pessoa"""
        if search_type == "person":
            linkedin_url = await self._client.find_person_linkedin(name, company)
        else:
            linkedin_url = await self._client.find_company_linkedin(name)

        if linkedin_url:
            return self._success_response(
                data={
                    "linkedin_url": linkedin_url,
                    "type": search_type,
                    "name": name,
                },
                message=f"LinkedIn encontrado para {name}",
            )

        return self._success_response(
            data={
                "linkedin_url": "inexistente",
                "type": search_type,
                "name": name,
            },
            message=f"LinkedIn não encontrado para {name}",
        )

    async def _find_website(self, company_name: str) -> list[TextContent]:
        """Encontra website oficial de uma empresa"""
        website = await self._client.find_company_website(company_name)

        if website:
            return self._success_response(
                data={"website": website},
                message=f"Website encontrado para {company_name}",
            )

        return self._error_response(f"Website não encontrado para {company_name}")

    async def _search_news(
        self, query: str, period: str = "week", num_results: int = 5
    ) -> list[TextContent]:
        """Busca notícias"""
        # Mapear período para formato Serper
        tbs_map = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}

        result = await self._client.search_news(
            query=query,
            num=min(num_results, 10),
            tbs=tbs_map.get(period, "qdr:w"),
        )

        return self._success_response(
            data={
                "query": query,
                "period": period,
                "news": result.get("news", []),
                "total": result.get("total_results", 0),
            },
            message=f"Encontradas {result.get('total_results', 0)} notícias",
        )


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = SerperMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
