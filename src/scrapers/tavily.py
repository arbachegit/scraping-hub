"""
Tavily Client
AI-powered search API para pesquisas contextuais
https://tavily.com/
"""

from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings

from .base import BaseScraper

logger = structlog.get_logger()


class TavilyClient(BaseScraper):
    """
    Cliente para Tavily - AI Search API

    Funcionalidades:
    - Busca com contexto AI
    - Extração de conteúdo
    - Resumo automático
    - Busca em profundidade
    """

    # Metadados da fonte para rastreabilidade (CLAUDE.md)
    SOURCE_NAME = "Tavily - AI Search"
    SOURCE_PROVIDER = "Tavily"
    SOURCE_CATEGORY = "api"
    SOURCE_COVERAGE = "Busca com contexto AI, extração de conteúdo"
    SOURCE_DOC_URL = "https://docs.tavily.com"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 60.0):
        super().__init__(
            api_key=api_key or settings.tavily_api_key,
            base_url="https://api.tavily.com",
            rate_limit=60,  # ~1000/mês grátis
            timeout=timeout,
        )

    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        topic: str = "general",
    ) -> Dict[str, Any]:
        """
        Busca com AI

        Args:
            query: Termo de busca
            search_depth: "basic" ou "advanced" (mais tokens)
            include_answer: Incluir resposta AI
            include_raw_content: Incluir conteúdo bruto das páginas
            max_results: Máximo de resultados (1-10)
            include_domains: Domínios para incluir
            exclude_domains: Domínios para excluir
            topic: "general" ou "news"

        Returns:
            Resultados com resposta AI
        """
        logger.info("tavily_search", query=query[:50], depth=search_depth)

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "max_results": min(max_results, 10),
            "topic": topic,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        result = await self.post("/search", json=payload)

        return {
            "query": query,
            "answer": result.get("answer"),
            "results": result.get("results", []),
            "follow_up_questions": result.get("follow_up_questions", []),
            "response_time": result.get("response_time"),
        }

    async def search_news(
        self, query: str, max_results: int = 5, days: int = 7
    ) -> Dict[str, Any]:
        """
        Busca de notícias recentes

        Args:
            query: Termo de busca
            max_results: Máximo de resultados
            days: Dias para buscar (1-30)

        Returns:
            Notícias encontradas
        """
        # Adicionar filtro de tempo à query
        time_filter = f"últimos {days} dias" if days <= 7 else "último mês"
        enhanced_query = f"{query} notícias {time_filter}"

        return await self.search(
            query=enhanced_query,
            search_depth="basic",
            include_answer=True,
            max_results=max_results,
            topic="news",
        )

    async def research(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Pesquisa em profundidade

        Args:
            query: Pergunta ou tópico
            max_results: Máximo de resultados

        Returns:
            Pesquisa detalhada com resposta AI
        """
        logger.info("tavily_research", query=query[:50])

        return await self.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True,
            max_results=max_results,
        )

    async def extract_content(self, urls: List[str]) -> Dict[str, Any]:
        """
        Extrai conteúdo de URLs

        Args:
            urls: Lista de URLs para extrair

        Returns:
            Conteúdo extraído
        """
        logger.info("tavily_extract", urls_count=len(urls))

        result = await self.post(
            "/extract",
            json={
                "api_key": self.api_key,
                "urls": urls[:5],  # Limite de 5 URLs
            },
        )

        return {
            "results": result.get("results", []),
            "failed_urls": result.get("failed_urls", []),
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA EMPRESAS
    # ===========================================

    async def research_company(
        self, company_name: str, aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Pesquisa aprofundada sobre uma empresa

        Args:
            company_name: Nome da empresa
            aspects: Aspectos para pesquisar

        Returns:
            Informações detalhadas da empresa
        """
        if aspects is None:
            aspects = [
                "história e fundação",
                "produtos e serviços",
                "mercado e concorrentes",
                "notícias recentes",
                "cultura organizacional",
            ]

        results = {}

        for aspect in aspects:
            query = f"{company_name} {aspect} Brasil"
            search_result = await self.search(
                query=query, search_depth="basic", include_answer=True, max_results=3
            )
            results[aspect] = {
                "answer": search_result.get("answer"),
                "sources": [
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "content": r.get("content", "")[:500],
                    }
                    for r in search_result.get("results", [])
                ],
            }

        # Consolidar resposta
        return {
            "company_name": company_name,
            "research": results,
            "summary": await self._generate_summary(company_name, results),
        }

    async def _generate_summary(self, company_name: str, research: Dict) -> str:
        """Gera resumo da pesquisa (placeholder - usar Claude)"""
        parts = []
        for aspect, data in research.items():
            if data.get("answer"):
                parts.append(f"**{aspect.title()}**: {data['answer']}")
        return "\n\n".join(parts)

    async def get_company_news(
        self, company_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Busca notícias recentes sobre uma empresa

        Args:
            company_name: Nome da empresa
            days: Dias para buscar

        Returns:
            Notícias com análise
        """
        result = await self.search_news(
            query=f'"{company_name}" Brasil', max_results=10, days=days
        )

        # Categorizar notícias
        news_items = []
        for item in result.get("results", []):
            content = item.get("content", "").lower()

            # Detectar sentimento básico
            positive_words = [
                "crescimento",
                "sucesso",
                "investimento",
                "expansão",
                "lucro",
                "inovação",
            ]
            negative_words = [
                "crise",
                "demissão",
                "prejuízo",
                "processo",
                "escândalo",
                "queda",
            ]

            sentiment = "neutral"
            if any(word in content for word in positive_words):
                sentiment = "positive"
            elif any(word in content for word in negative_words):
                sentiment = "negative"

            news_items.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content", "")[:300],
                    "published_date": item.get("published_date"),
                    "sentiment": sentiment,
                }
            )

        return {
            "company_name": company_name,
            "news": news_items,
            "summary": result.get("answer"),
            "total_news": len(news_items),
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA PESSOAS
    # ===========================================

    async def research_person(
        self, name: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pesquisa sobre uma pessoa

        Args:
            name: Nome da pessoa
            context: Contexto (empresa, cargo, etc)

        Returns:
            Informações encontradas
        """
        query = f'"{name}"'
        if context:
            query += f" {context}"
        query += " Brasil perfil profissional"

        result = await self.research(query, max_results=8)

        return {
            "name": name,
            "context": context,
            "summary": result.get("answer"),
            "sources": result.get("results", []),
            "follow_up": result.get("follow_up_questions", []),
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA POLÍTICOS
    # ===========================================

    async def research_politician(
        self, name: str, role: Optional[str] = None, state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pesquisa sobre um político (foco em perfil pessoal, não político)

        Args:
            name: Nome do político
            role: Cargo político
            state: Estado

        Returns:
            Informações do perfil pessoal
        """
        queries = [
            f'"{name}" biografia história pessoal',
            f'"{name}" família educação formação',
            f'"{name}" carreira trajetória profissional',
            f'"{name}" redes sociais Instagram Twitter',
        ]

        if role:
            queries.append(f'"{name}" {role} realizações')
        if state:
            queries.append(f'"{name}" {state} atuação')

        results = {}
        for query in queries:
            search_result = await self.search(
                query=query,
                search_depth="basic",
                include_answer=True,
                max_results=3,
                exclude_domains=[
                    "twitter.com",
                    "facebook.com",
                ],  # Evitar ruído de posts
            )

            key = query.split('"')[-1].strip().split()[0] if '"' in query else "general"
            results[key] = {
                "answer": search_result.get("answer"),
                "sources": search_result.get("results", []),
            }

        # Buscar notícias
        news_query = f'"{name}"'
        if role:
            news_query += f" {role}"
        news = await self.search_news(news_query, max_results=10, days=30)

        return {
            "name": name,
            "role": role,
            "state": state,
            "research": results,
            "news": news.get("results", []),
            "news_summary": news.get("answer"),
        }

    # ===========================================
    # MÉTODOS DE MERCADO
    # ===========================================

    async def get_market_trends(
        self, industry: str, country: str = "Brasil"
    ) -> Dict[str, Any]:
        """
        Busca tendências de mercado

        Args:
            industry: Setor/indústria
            country: País

        Returns:
            Tendências e insights
        """
        query = f"tendências mercado {industry} {country} 2024 2025"

        result = await self.research(query, max_results=10)

        return {
            "industry": industry,
            "country": country,
            "trends": result.get("answer"),
            "sources": result.get("results", []),
            "follow_up_questions": result.get("follow_up_questions", []),
        }

    async def get_economic_scenario(
        self, sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca cenário econômico brasileiro

        Args:
            sector: Setor específico (opcional)

        Returns:
            Análise econômica
        """
        query = "cenário econômico Brasil previsões"
        if sector:
            query += f" setor {sector}"

        result = await self.research(query, max_results=10)

        return {
            "sector": sector,
            "analysis": result.get("answer"),
            "sources": result.get("results", []),
            "follow_up_questions": result.get("follow_up_questions", []),
        }
