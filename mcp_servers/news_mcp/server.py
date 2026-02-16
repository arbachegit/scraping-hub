"""
News MCP Server
Coleta de notícias econômicas via Perplexity + Twitter/X

Fontes confiáveis incluídas na busca:
- Agências de checagem: @aosfatos, @agencialupa, @projetocomprova
- Veículos: Folha, Estadão, Valor, InfoMoney, Exame
- Jornalistas especializados em economia

O MCP busca notícias, filtra citações e prepara para análise do Claude.
"""

from typing import Any

import httpx
from mcp.types import TextContent, Tool

from ..base_mcp import BaseMCPServer
from ..config import MCPConfig


# Fontes confiáveis para incluir nas buscas
TRUSTED_SOURCES = {
    "agencias_checagem": [
        "@aosfatos",
        "@agencialupa",
        "@projetocomprova",
        "@EstadaoVerifica",
    ],
    "veiculos_economia": [
        "Valor Econômico",
        "InfoMoney",
        "Exame",
        "Bloomberg Brasil",
        "Reuters Brasil",
    ],
    "veiculos_geral": [
        "Folha de S.Paulo",
        "O Estado de S. Paulo",
        "O Globo",
        "G1",
    ],
    "jornalistas_economia": [
        "@marilizpj",
        "@juliaduailibi",
        "@gugachacra",
        "@arielpalacios",
    ],
}


class NewsMCPServer(BaseMCPServer):
    """
    MCP Server para notícias econômicas.

    Usa Perplexity para buscar notícias incluindo fontes confiáveis do Twitter.
    Retorna notícias estruturadas para processamento pelo Claude.

    Tools disponíveis:
    - search_news: Busca notícias por segmento/palavra-chave
    - get_sector_news: Notícias de um setor específico
    - get_company_news: Notícias relacionadas a uma empresa
    - get_economic_indicators: Indicadores econômicos recentes
    """

    # Metadados para rastreabilidade
    SOURCE_NAME = "News MCP - Perplexity + Twitter"
    SOURCE_PROVIDER = "Perplexity AI + X/Twitter"
    SOURCE_CATEGORY = "noticias"

    def __init__(self, config: MCPConfig | None = None):
        """
        Inicializa MCP Server.

        Args:
            config: Configurações (usa default se não fornecido)
        """
        super().__init__("news-mcp", "1.0.0")
        self.config = config or MCPConfig.from_env()

        # Verificar configuração
        if not self.config.perplexity_api_key:
            self.logger.warning("perplexity_not_configured")

        self._perplexity_url = "https://api.perplexity.ai/chat/completions"

    def get_tools(self) -> list[Tool]:
        """Retorna tools disponíveis"""
        return [
            Tool(
                name="search_news",
                description="Busca notícias econômicas por palavra-chave ou segmento. Inclui fontes confiáveis do Twitter (Valor, InfoMoney, jornalistas, agências de checagem).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Termo de busca (ex: 'inflação', 'juros', 'startups tecnologia')",
                        },
                        "segmento": {
                            "type": "string",
                            "description": "Segmento de mercado",
                            "enum": [
                                "tecnologia",
                                "varejo",
                                "industria",
                                "agronegocio",
                                "financeiro",
                                "saude",
                                "energia",
                                "construcao",
                                "servicos",
                                "geral",
                            ],
                        },
                        "periodo": {
                            "type": "string",
                            "description": "Período de busca",
                            "enum": ["hoje", "semana", "mes", "trimestre"],
                            "default": "semana",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número máximo de notícias",
                            "default": 10,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_sector_news",
                description="Obtém notícias recentes de um setor específico da economia brasileira",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "setor": {
                            "type": "string",
                            "description": "Setor econômico",
                            "enum": [
                                "tecnologia",
                                "fintech",
                                "agronegocio",
                                "varejo",
                                "industria",
                                "energia",
                                "saude",
                                "educacao",
                                "imobiliario",
                                "logistica",
                            ],
                        },
                        "foco": {
                            "type": "string",
                            "description": "Foco específico",
                            "enum": [
                                "mercado",
                                "regulacao",
                                "investimentos",
                                "fusoes",
                                "resultados",
                            ],
                            "default": "mercado",
                        },
                    },
                    "required": ["setor"],
                },
            ),
            Tool(
                name="get_company_news",
                description="Busca notícias recentes sobre uma empresa específica",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "empresa_nome": {
                            "type": "string",
                            "description": "Nome da empresa",
                        },
                        "cnpj": {
                            "type": "string",
                            "description": "CNPJ da empresa (opcional)",
                        },
                        "periodo": {
                            "type": "string",
                            "description": "Período de busca",
                            "enum": ["semana", "mes", "trimestre", "ano"],
                            "default": "mes",
                        },
                    },
                    "required": ["empresa_nome"],
                },
            ),
            Tool(
                name="get_economic_indicators",
                description="Obtém notícias sobre indicadores econômicos (Selic, inflação, PIB, câmbio)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "indicador": {
                            "type": "string",
                            "description": "Indicador específico",
                            "enum": ["selic", "inflacao", "pib", "cambio", "emprego", "comercio_exterior", "todos"],
                            "default": "todos",
                        },
                    },
                },
            ),
            Tool(
                name="get_trusted_sources",
                description="Retorna lista de fontes confiáveis cadastradas (Twitter, veículos, jornalistas)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria de fonte",
                            "enum": ["agencias_checagem", "veiculos_economia", "veiculos_geral", "jornalistas_economia", "todas"],
                            "default": "todas",
                        },
                    },
                },
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Processa chamada de tool"""
        if not self.config.perplexity_api_key:
            return self._error_response(
                "Perplexity não configurado. Configure PERPLEXITY_API_KEY no .env"
            )

        try:
            if name == "search_news":
                return await self._search_news(
                    query=arguments["query"],
                    segmento=arguments.get("segmento"),
                    periodo=arguments.get("periodo", "semana"),
                    limit=arguments.get("limit", 10),
                )

            elif name == "get_sector_news":
                return await self._get_sector_news(
                    setor=arguments["setor"],
                    foco=arguments.get("foco", "mercado"),
                )

            elif name == "get_company_news":
                return await self._get_company_news(
                    empresa_nome=arguments["empresa_nome"],
                    cnpj=arguments.get("cnpj"),
                    periodo=arguments.get("periodo", "mes"),
                )

            elif name == "get_economic_indicators":
                return await self._get_economic_indicators(
                    indicador=arguments.get("indicador", "todos"),
                )

            elif name == "get_trusted_sources":
                return await self._get_trusted_sources(
                    categoria=arguments.get("categoria", "todas"),
                )

            return self._error_response(f"Tool desconhecida: {name}")

        except Exception as e:
            self.logger.error("news_tool_error", tool=name, error=str(e))
            return self._error_response(f"Erro: {str(e)}")

    async def _search_news(
        self,
        query: str,
        segmento: str | None = None,
        periodo: str = "semana",
        limit: int = 10,
    ) -> list[TextContent]:
        """
        Busca notícias por palavra-chave.

        Args:
            query: Termo de busca
            segmento: Segmento de mercado
            periodo: Período de busca
            limit: Limite de resultados

        Returns:
            Notícias encontradas
        """
        # Construir query com fontes confiáveis
        sources_str = " OR ".join(
            TRUSTED_SOURCES["veiculos_economia"]
            + TRUSTED_SOURCES["veiculos_geral"]
        )

        full_query = f"""
        Busque notícias recentes sobre: {query}

        Período: últim{'a semana' if periodo == 'semana' else 'o mês' if periodo == 'mes' else 's 3 meses' if periodo == 'trimestre' else ' dia'}

        Priorize fontes: {sources_str}

        {'Segmento: ' + segmento if segmento else ''}

        Para cada notícia, forneça:
        1. Título
        2. Resumo (2-3 frases)
        3. Fonte (veículo/autor)
        4. Data aproximada
        5. URL (se disponível)
        6. Relevância para o segmento (alta/média/baixa)

        Limite: {limit} notícias mais relevantes
        Formato: JSON com array "news"
        """

        result = await self._query_perplexity(full_query)

        return self._success_response(
            data={
                "query": query,
                "segmento": segmento,
                "periodo": periodo,
                "news": result.get("news", []),
                "citations": result.get("citations", []),
                "raw_response": result.get("raw_response"),
            },
            message=f"Encontradas notícias sobre '{query}'",
        )

    async def _get_sector_news(
        self, setor: str, foco: str = "mercado"
    ) -> list[TextContent]:
        """
        Obtém notícias de um setor específico.

        Args:
            setor: Setor econômico
            foco: Foco da busca

        Returns:
            Notícias do setor
        """
        foco_desc = {
            "mercado": "tendências de mercado e competição",
            "regulacao": "mudanças regulatórias e leis",
            "investimentos": "investimentos, funding e IPOs",
            "fusoes": "fusões, aquisições e consolidação",
            "resultados": "resultados financeiros e balanços",
        }

        query = f"""
        Notícias recentes do setor de {setor} no Brasil.
        Foco: {foco_desc.get(foco, foco)}

        Priorize:
        - Valor Econômico
        - InfoMoney
        - Exame
        - Bloomberg Brasil

        Para cada notícia:
        1. Título
        2. Resumo
        3. Impacto para o setor (positivo/neutro/negativo)
        4. Empresas mencionadas
        5. Fonte e data

        Formato: JSON com array "news" e "sector_summary"
        """

        result = await self._query_perplexity(query)

        return self._success_response(
            data={
                "setor": setor,
                "foco": foco,
                "news": result.get("news", []),
                "sector_summary": result.get("sector_summary"),
                "citations": result.get("citations", []),
            },
            message=f"Notícias do setor {setor} ({foco})",
        )

    async def _get_company_news(
        self,
        empresa_nome: str,
        cnpj: str | None = None,
        periodo: str = "mes",
    ) -> list[TextContent]:
        """
        Busca notícias sobre uma empresa.

        Args:
            empresa_nome: Nome da empresa
            cnpj: CNPJ (opcional)
            periodo: Período de busca

        Returns:
            Notícias da empresa
        """
        query = f"""
        Notícias recentes sobre a empresa {empresa_nome} no Brasil.
        {f'CNPJ: {cnpj}' if cnpj else ''}

        Período: último {periodo}

        Busque em:
        - Veículos de economia (Valor, Exame, InfoMoney)
        - Portais de notícias (G1, Folha, Estadão)
        - Twitter de jornalistas especializados

        Para cada notícia:
        1. Título
        2. Resumo
        3. Categoria (financeiro/operacional/institucional/mercado)
        4. Sentimento (positivo/neutro/negativo)
        5. Fonte e data

        Também liste:
        - Executivos mencionados
        - Concorrentes mencionados
        - Números relevantes (receita, investimento, etc)

        Formato: JSON com "news", "executives_mentioned", "competitors_mentioned"
        """

        result = await self._query_perplexity(query)

        return self._success_response(
            data={
                "empresa": empresa_nome,
                "periodo": periodo,
                "news": result.get("news", []),
                "executives_mentioned": result.get("executives_mentioned", []),
                "competitors_mentioned": result.get("competitors_mentioned", []),
                "citations": result.get("citations", []),
            },
            message=f"Notícias sobre {empresa_nome}",
        )

    async def _get_economic_indicators(
        self, indicador: str = "todos"
    ) -> list[TextContent]:
        """
        Obtém notícias sobre indicadores econômicos.

        Args:
            indicador: Indicador específico ou 'todos'

        Returns:
            Notícias sobre indicadores
        """
        indicadores_map = {
            "selic": "taxa Selic, política monetária, Banco Central",
            "inflacao": "IPCA, inflação, índices de preços",
            "pib": "PIB, crescimento econômico",
            "cambio": "dólar, câmbio, moeda",
            "emprego": "desemprego, mercado de trabalho, PNAD",
            "comercio_exterior": "exportações, importações, balança comercial",
        }

        if indicador == "todos":
            query = """
            Resumo dos principais indicadores econômicos brasileiros esta semana:
            - Selic e política monetária
            - Inflação (IPCA)
            - PIB e crescimento
            - Câmbio (dólar)
            - Emprego
            - Comércio exterior

            Para cada indicador:
            1. Valor atual
            2. Variação
            3. Expectativas
            4. Principais notícias

            Formato: JSON com "indicators" array
            """
        else:
            query = f"""
            Notícias recentes sobre {indicadores_map.get(indicador, indicador)} no Brasil.

            Inclua:
            1. Valor atual do indicador
            2. Histórico recente
            3. Expectativas de mercado
            4. Impacto nos negócios
            5. Análises de especialistas

            Formato: JSON com "indicator_data" e "news"
            """

        result = await self._query_perplexity(query)

        return self._success_response(
            data={
                "indicador": indicador,
                "indicators": result.get("indicators", []),
                "indicator_data": result.get("indicator_data"),
                "news": result.get("news", []),
                "citations": result.get("citations", []),
            },
            message=f"Indicadores econômicos: {indicador}",
        )

    async def _get_trusted_sources(
        self, categoria: str = "todas"
    ) -> list[TextContent]:
        """
        Retorna lista de fontes confiáveis.

        Args:
            categoria: Categoria de fontes

        Returns:
            Lista de fontes
        """
        if categoria == "todas":
            sources = TRUSTED_SOURCES
        else:
            sources = {categoria: TRUSTED_SOURCES.get(categoria, [])}

        return self._success_response(
            data={
                "categoria": categoria,
                "sources": sources,
                "total": sum(len(v) for v in sources.values()),
            },
            message=f"Fontes confiáveis: {categoria}",
        )

    async def _query_perplexity(self, query: str) -> dict[str, Any]:
        """
        Executa query no Perplexity.

        Args:
            query: Query a executar

        Returns:
            Resposta estruturada
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._perplexity_url,
                    json={
                        "model": "llama-3.1-sonar-large-128k-online",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Você é um assistente especializado em notícias econômicas brasileiras. "
                                "Sempre retorne respostas em formato JSON válido. "
                                "Inclua citações das fontes. "
                                "Priorize fontes confiáveis como Valor Econômico, InfoMoney, Exame, Folha, Estadão.",
                            },
                            {"role": "user", "content": query},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 4096,
                    },
                    headers={
                        "Authorization": f"Bearer {self.config.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60.0,
                )

                if response.status_code != 200:
                    self.logger.error(
                        "perplexity_error",
                        status=response.status_code,
                        response=response.text,
                    )
                    return {"error": f"Perplexity error: {response.status_code}"}

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = data.get("citations", [])

                # Tentar parsear JSON da resposta
                result = self._parse_json_response(content)
                result["citations"] = citations
                result["raw_response"] = content

                return result

        except Exception as e:
            self.logger.error("perplexity_request_error", error=str(e))
            return {"error": str(e)}

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """
        Parseia resposta JSON do Perplexity.

        Args:
            content: Conteúdo da resposta

        Returns:
            Dados estruturados
        """
        import json
        import re

        # Tentar extrair JSON da resposta
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Se não encontrar JSON, estruturar a resposta
        return {
            "news": [],
            "summary": content,
        }


# Entry point para execução via stdio
async def main():
    """Executa MCP server via stdio"""
    server = NewsMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
