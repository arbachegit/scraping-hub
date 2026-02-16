"""
Apollo MCP Server
B2B Intelligence via Apollo.io

Fonte: https://www.apollo.io
Requer API key.
"""

from typing import Any

from mcp.types import TextContent, Tool

from src.scrapers.apollo import ApolloClient

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


class ApolloMCPServer(BaseMCPServer):
    """
    MCP Server para Apollo.io.

    Acessa dados B2B:
    - Busca e enriquecimento de empresas
    - Busca e enriquecimento de pessoas/contatos
    - Dados de LinkedIn
    - Executivos e decision makers

    Tools disponíveis:
    - search_company: Busca empresas por nome e filtros
    - enrich_person: Enriquece dados de uma pessoa
    - get_executives: Lista executivos de uma empresa
    - search_brazil_companies: Busca empresas brasileiras
    """

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("apollo-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Inicializar cliente Apollo
        if not self.config.apollo_api_key:
            self.logger.warning("apollo_not_configured")
            self._client: ApolloClient | None = None
        else:
            self._client = ApolloClient(api_key=self.config.apollo_api_key)

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="search_company",
                description="Busca empresas por nome e filtros. Retorna dados de LinkedIn, website, funcionários e mais.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                        "industry": {
                            "type": "string",
                            "description": "Setor/indústria (opcional)",
                        },
                        "location": {
                            "type": "string",
                            "description": "Localização (ex: 'São Paulo, Brazil')",
                        },
                        "min_employees": {
                            "type": "integer",
                            "description": "Mínimo de funcionários (opcional)",
                        },
                        "max_employees": {
                            "type": "integer",
                            "description": "Máximo de funcionários (opcional)",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="enrich_person",
                description="Enriquece dados de uma pessoa usando email ou LinkedIn URL. Retorna cargo, empresa, contato e mais.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email da pessoa",
                        },
                        "linkedin_url": {
                            "type": "string",
                            "description": "URL do LinkedIn (ex: https://linkedin.com/in/username)",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Primeiro nome (se não tiver email/linkedin)",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Sobrenome (se não tiver email/linkedin)",
                        },
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa (melhora precisão)",
                        },
                    },
                },
            ),
            Tool(
                name="get_executives",
                description="Lista executivos (C-level, VPs, Diretores) de uma empresa",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Domínio da empresa (ex: empresa.com.br)",
                        },
                    },
                },
            ),
            Tool(
                name="search_brazil_companies",
                description="Busca empresas brasileiras com filtros específicos",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nome da empresa (opcional)",
                        },
                        "industry": {
                            "type": "string",
                            "description": "Setor/indústria",
                        },
                        "states": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Estados (ex: ['SP', 'RJ'])",
                        },
                        "min_employees": {
                            "type": "integer",
                            "description": "Mínimo de funcionários",
                        },
                        "max_employees": {
                            "type": "integer",
                            "description": "Máximo de funcionários",
                        },
                    },
                },
            ),
            Tool(
                name="search_person",
                description="Busca pessoas por nome, cargo ou empresa",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nome da pessoa",
                        },
                        "company": {
                            "type": "string",
                            "description": "Empresa onde trabalha",
                        },
                        "title": {
                            "type": "string",
                            "description": "Cargo (ex: 'CEO', 'Diretor')",
                        },
                        "seniority": {
                            "type": "string",
                            "description": "Senioridade",
                            "enum": [
                                "owner",
                                "founder",
                                "c_suite",
                                "partner",
                                "vp",
                                "head",
                                "director",
                                "manager",
                                "senior",
                                "entry",
                            ],
                        },
                    },
                },
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self._client:
            return self._error_response(
                "Apollo não configurado. Configure APOLLO_API_KEY no .env"
            )

        try:
            if name == "search_company":
                return await self._search_company(arguments)

            elif name == "enrich_person":
                return await self._enrich_person(arguments)

            elif name == "get_executives":
                return await self._get_executives(arguments)

            elif name == "search_brazil_companies":
                return await self._search_brazil_companies(arguments)

            elif name == "search_person":
                return await self._search_person(arguments)

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("apollo_tool_error", tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    async def _search_company(self, args: dict[str, Any]) -> list[TextContent]:
        """Busca empresas por nome e filtros"""
        locations = None
        if args.get("location"):
            locations = [args["location"]]

        employee_ranges = None
        if args.get("min_employees") or args.get("max_employees"):
            employee_ranges = self._client._build_employee_ranges(
                args.get("min_employees"),
                args.get("max_employees"),
            )

        industries = None
        if args.get("industry"):
            industries = [args["industry"]]

        result = await self._client.search_organizations(
            q_organization_name=args.get("name"),
            organization_locations=locations,
            organization_num_employees_ranges=employee_ranges,
            organization_industries=industries,
        )

        organizations = result.get("organizations", [])

        return self._success_response(
            data={
                "organizations": organizations[:10],
                "total": result.get("total", 0),
            },
            message=f"Encontradas {len(organizations)} empresas",
        )

    async def _enrich_person(self, args: dict[str, Any]) -> list[TextContent]:
        """Enriquece dados de uma pessoa"""
        if not any([args.get("email"), args.get("linkedin_url"), args.get("first_name")]):
            return self._error_response(
                "Forneça email, linkedin_url ou first_name+last_name"
            )

        result = await self._client.enrich_person(
            email=args.get("email"),
            linkedin_url=args.get("linkedin_url"),
            first_name=args.get("first_name"),
            last_name=args.get("last_name"),
            organization_name=args.get("company_name"),
        )

        if not result:
            return self._error_response("Pessoa não encontrada")

        return self._success_response(
            data={
                "name": result.get("name"),
                "title": result.get("title"),
                "seniority": result.get("seniority"),
                "company": result.get("company"),
                "email": result.get("email"),
                "linkedin_url": result.get("linkedin_url") or "inexistente",
                "city": result.get("city"),
                "state": result.get("state"),
                "country": result.get("country"),
                "photo_url": result.get("photo_url"),
                "headline": result.get("headline"),
            },
            message=f"Dados enriquecidos para {result.get('name')}",
        )

    async def _get_executives(self, args: dict[str, Any]) -> list[TextContent]:
        """Lista executivos de uma empresa"""
        if not args.get("company_name") and not args.get("domain"):
            return self._error_response("Forneça company_name ou domain")

        result = await self._client.get_executives(
            organization_name=args.get("company_name"),
            domain=args.get("domain"),
        )

        employees = result.get("employees", [])

        return self._success_response(
            data={
                "executives": [
                    {
                        "name": e.get("name"),
                        "title": e.get("title"),
                        "seniority": e.get("seniority"),
                        "linkedin_url": e.get("linkedin_url") or "inexistente",
                        "email": e.get("email"),
                    }
                    for e in employees
                ],
                "total": result.get("total", 0),
            },
            message=f"Encontrados {len(employees)} executivos",
        )

    async def _search_brazil_companies(self, args: dict[str, Any]) -> list[TextContent]:
        """Busca empresas brasileiras"""
        result = await self._client.search_brazil_companies(
            name=args.get("name"),
            industry=args.get("industry"),
            min_employees=args.get("min_employees"),
            max_employees=args.get("max_employees"),
            states=args.get("states"),
        )

        organizations = result.get("organizations", [])

        return self._success_response(
            data={
                "organizations": organizations[:10],
                "total": result.get("total", 0),
            },
            message=f"Encontradas {len(organizations)} empresas brasileiras",
        )

    async def _search_person(self, args: dict[str, Any]) -> list[TextContent]:
        """Busca pessoas por nome, cargo ou empresa"""
        result = await self._client.search_brazil_people(
            name=args.get("name"),
            company=args.get("company"),
            title=args.get("title"),
            seniority=args.get("seniority"),
        )

        people = result.get("people", [])

        return self._success_response(
            data={
                "people": [
                    {
                        "name": p.get("name"),
                        "title": p.get("title"),
                        "company": p.get("company", {}).get("name"),
                        "linkedin_url": p.get("linkedin_url") or "inexistente",
                        "email": p.get("email"),
                        "city": p.get("city"),
                    }
                    for p in people
                ],
                "total": result.get("total", 0),
            },
            message=f"Encontradas {len(people)} pessoas",
        )


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = ApolloMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
