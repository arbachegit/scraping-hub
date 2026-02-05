"""
Competitor Analysis Service
Análise de concorrentes e posicionamento competitivo
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from src.scrapers import SerperClient, TavilyClient, PerplexityClient, WebScraperClient
from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class CompetitorAnalysisService:
    """
    Serviço de análise competitiva

    Funcionalidades:
    - Identificação de concorrentes
    - Comparação de empresas
    - Análise de market share
    - Monitoramento competitivo
    """

    def __init__(self):
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.web_scraper = WebScraperClient()
        self.ai_analyzer = AIAnalyzer()

    async def close(self):
        """Fecha todos os clientes"""
        await asyncio.gather(
            self.serper.close(),
            self.tavily.close(),
            self.perplexity.close(),
            self.web_scraper.close(),
            self.ai_analyzer.close()
        )

    async def identify_competitors(
        self,
        company_name: str,
        industry: Optional[str] = None,
        location: str = "Brasil",
        max_competitors: int = 5
    ) -> Dict[str, Any]:
        """
        Identifica concorrentes de uma empresa

        Args:
            company_name: Nome da empresa
            industry: Setor de atuação
            location: Localização (país/região)
            max_competitors: Número máximo de concorrentes

        Returns:
            Lista de concorrentes identificados
        """
        logger.info(
            "competitor_identify",
            company=company_name,
            industry=industry
        )

        # Buscar concorrentes via múltiplas fontes
        tasks = [
            self.perplexity.find_competitors(company_name, industry),
            self._search_competitors_google(company_name, industry, location)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Consolidar resultados
        competitors = set()

        # Do Perplexity
        if not isinstance(results[0], Exception):
            perplexity_competitors = self._extract_names_from_text(
                results[0].get("competitors_analysis", "")
            )
            competitors.update(perplexity_competitors)

        # Do Google
        if not isinstance(results[1], Exception):
            competitors.update(results[1])

        # Remover a própria empresa
        competitors.discard(company_name)
        competitors.discard(company_name.lower())

        # Limitar número
        competitors_list = list(competitors)[:max_competitors]

        # Buscar informações básicas de cada concorrente
        competitors_data = []
        for comp in competitors_list:
            try:
                info = await self.serper.find_company_info(comp)
                competitors_data.append({
                    "name": comp,
                    "website": info.get("website"),
                    "description": info.get("description"),
                    "industry": info.get("industry"),
                    "linkedin": await self.serper.find_company_linkedin(comp)
                })
            except Exception as e:
                logger.warning("competitor_info_error", competitor=comp, error=str(e))
                competitors_data.append({"name": comp})

        return {
            "company": company_name,
            "industry": industry,
            "competitors": competitors_data,
            "total_found": len(competitors_data),
            "sources": ["Perplexity AI", "Google Search"]
        }

    async def _search_competitors_google(
        self,
        company_name: str,
        industry: Optional[str],
        location: str
    ) -> List[str]:
        """Busca concorrentes via Google"""
        queries = [
            f"concorrentes da {company_name} {location}",
            f"empresas similares a {company_name}",
        ]

        if industry:
            queries.append(f"principais empresas de {industry} {location}")

        competitors = set()

        for query in queries:
            try:
                results = await self.serper.search(query, num=10)

                # Extrair nomes de empresas dos resultados
                for item in results.get("organic", []):
                    names = self._extract_company_names_from_snippet(
                        item.get("snippet", "")
                    )
                    competitors.update(names)

                # Do knowledge graph
                kg = results.get("knowledge_graph", {})
                if kg:
                    related = kg.get("relatedSearches", [])
                    for r in related:
                        if isinstance(r, str):
                            competitors.add(r)

            except Exception as e:
                logger.warning("google_competitor_search_error", query=query, error=str(e))

        return list(competitors)

    def _extract_names_from_text(self, text: str) -> List[str]:
        """Extrai nomes de empresas de texto"""
        import re

        names = []

        # Padrões para identificar nomes de empresas
        patterns = [
            r"(?:concorrentes?|competidores?)(?:\s+(?:diretos?|principais?))?\s*(?:são|incluem|:)\s*([^.]+)",
            r"\d+\.\s*([A-Z][A-Za-z0-9\s&]+?)(?:\s*[-–:]|\s*\(|\n|$)",
            r"(?:empresas?\s+como|como\s+a?)\s+([A-Z][A-Za-z0-9\s&,]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Dividir por vírgulas e "e"
                parts = re.split(r'[,;]|\s+e\s+', match)
                for part in parts:
                    cleaned = part.strip().strip('.')
                    if 2 < len(cleaned) < 50:
                        names.append(cleaned)

        return list(dict.fromkeys(names))

    def _extract_company_names_from_snippet(self, snippet: str) -> List[str]:
        """Extrai nomes de empresas de um snippet de busca"""
        import re

        names = []

        # Padrão para nomes de empresas (capitalização e palavras comuns)
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:S\.?A\.?|Ltda\.?|Inc\.?|Corp\.?))?)\b'

        matches = re.findall(pattern, snippet)
        for match in matches:
            if len(match) > 3 and len(match) < 50:
                # Filtrar palavras comuns que não são empresas
                common_words = {
                    "Brasil", "Brazil", "São Paulo", "Rio Janeiro",
                    "Este", "Esta", "Esse", "Essa", "Como", "Para"
                }
                if match not in common_words:
                    names.append(match)

        return names

    async def compare_companies(
        self,
        company1: str,
        company2: str,
        aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compara duas empresas

        Args:
            company1: Primeira empresa
            company2: Segunda empresa
            aspects: Aspectos para comparar

        Returns:
            Comparação detalhada
        """
        logger.info("competitor_compare", company1=company1, company2=company2)

        if aspects is None:
            aspects = [
                "tamanho e escala",
                "produtos e serviços",
                "presença de mercado",
                "tecnologia e inovação",
                "cultura e employer branding"
            ]

        # Coletar dados de ambas
        data1, data2 = await asyncio.gather(
            self.serper.find_company_info(company1),
            self.serper.find_company_info(company2)
        )

        # Pesquisar comparação direta
        comparison_query = f"comparação {company1} vs {company2}"
        comparison_research = await self.tavily.search(
            comparison_query,
            search_depth="advanced",
            include_answer=True,
            max_results=5
        )

        # Análise por aspecto
        aspect_analysis = {}
        for aspect in aspects:
            query = f"{company1} vs {company2} {aspect}"
            result = await self.tavily.search(query, max_results=3)
            aspect_analysis[aspect] = {
                "answer": result.get("answer"),
                "sources": [r.get("url") for r in result.get("results", [])]
            }

        # Gerar análise comparativa com AI
        ai_comparison = await self.ai_analyzer.analyze_competitors(
            {"name": company1, **data1},
            [{"name": company2, **data2}]
        )

        return {
            "company1": {
                "name": company1,
                "data": data1
            },
            "company2": {
                "name": company2,
                "data": data2
            },
            "comparison_summary": comparison_research.get("answer"),
            "aspect_analysis": aspect_analysis,
            "ai_analysis": ai_comparison,
            "sources": comparison_research.get("results", [])
        }

    async def analyze_competitive_landscape(
        self,
        industry: str,
        location: str = "Brasil",
        depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Analisa o cenário competitivo de um setor

        Args:
            industry: Setor para analisar
            location: Localização
            depth: "quick", "standard", "deep"

        Returns:
            Análise do cenário competitivo
        """
        logger.info("competitor_landscape", industry=industry, location=location)

        # Pesquisa do mercado
        market_research = await self.perplexity.analyze_market(
            industry,
            aspects=[
                "principais players",
                "market share",
                "tendências",
                "barreiras de entrada",
                "fatores de sucesso"
            ]
        )

        # Buscar principais empresas
        top_companies_query = f"maiores empresas de {industry} no {location} 2024"
        top_companies = await self.serper.search(top_companies_query, num=10)

        # Notícias do setor
        sector_news = await self.tavily.search_news(
            f"{industry} {location}",
            max_results=10 if depth != "quick" else 5,
            days=30
        )

        # Tendências
        trends = await self.tavily.get_market_trends(industry, location)

        return {
            "industry": industry,
            "location": location,
            "market_overview": market_research.get("analysis"),
            "top_companies": self._extract_companies_from_search(top_companies),
            "market_structure": {
                "analysis": market_research.get("analysis"),
                "citations": market_research.get("citations", [])
            },
            "recent_news": sector_news.get("results", []),
            "trends": trends,
            "competitive_dynamics": self._analyze_dynamics(market_research)
        }

    def _extract_companies_from_search(self, search_results: Dict) -> List[Dict]:
        """Extrai empresas dos resultados de busca"""
        companies = []

        for item in search_results.get("organic", []):
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # Extrair nomes
            names = self._extract_company_names_from_snippet(f"{title} {snippet}")

            for name in names[:1]:  # Pegar apenas o primeiro de cada resultado
                companies.append({
                    "name": name,
                    "source": item.get("link"),
                    "context": snippet[:200]
                })

        return companies[:10]

    def _analyze_dynamics(self, market_research: Dict) -> Dict[str, str]:
        """Analisa dinâmicas competitivas do mercado"""
        analysis = market_research.get("analysis", "")

        return {
            "rivalry_intensity": self._classify_from_text(
                analysis,
                ["intensa", "alta competição", "acirrada"],
                ["moderada", "estável"],
                ["baixa", "poucos players"]
            ),
            "entry_barriers": self._classify_from_text(
                analysis,
                ["barreiras altas", "difícil entrada", "regulamentação"],
                ["barreiras moderadas"],
                ["baixas barreiras", "fácil entrada"]
            ),
            "market_maturity": self._classify_from_text(
                analysis,
                ["maduro", "consolidado", "saturado"],
                ["crescimento", "expansão"],
                ["emergente", "nascente", "novo"]
            )
        }

    def _classify_from_text(
        self,
        text: str,
        high_keywords: List[str],
        medium_keywords: List[str],
        low_keywords: List[str]
    ) -> str:
        """Classifica baseado em keywords no texto"""
        text_lower = text.lower()

        for keyword in high_keywords:
            if keyword in text_lower:
                return "high"

        for keyword in medium_keywords:
            if keyword in text_lower:
                return "medium"

        for keyword in low_keywords:
            if keyword in text_lower:
                return "low"

        return "unknown"

    async def monitor_competitor(
        self,
        competitor_name: str,
        track_aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Monitora atividades de um concorrente

        Args:
            competitor_name: Nome do concorrente
            track_aspects: Aspectos para monitorar

        Returns:
            Atualizações do concorrente
        """
        logger.info("competitor_monitor", competitor=competitor_name)

        if track_aspects is None:
            track_aspects = [
                "notícias",
                "lançamentos",
                "contratações",
                "parcerias",
                "financeiro"
            ]

        results = {}

        # Notícias recentes
        news = await self.tavily.get_company_news(competitor_name, days=7)
        results["news"] = news

        # Buscar aspectos específicos
        for aspect in track_aspects:
            if aspect == "notícias":
                continue  # Já coletado acima

            query = f'"{competitor_name}" {aspect}'
            search = await self.serper.search_news(query, num=5, tbs="qdr:w")
            results[aspect] = {
                "updates": search.get("news", []),
                "count": len(search.get("news", []))
            }

        # Detectar mudanças no site (se disponível)
        try:
            website = await self.serper.find_company_website(competitor_name)
            if website:
                site_data = await self.web_scraper.scrape_company_website(website)
                results["website_snapshot"] = {
                    "url": website,
                    "title": site_data.get("company_name"),
                    "description": site_data.get("description")
                }
        except Exception:
            pass

        return {
            "competitor": competitor_name,
            "monitoring_date": "now",
            "tracked_aspects": track_aspects,
            "updates": results,
            "alert_level": self._calculate_alert_level(results)
        }

    def _calculate_alert_level(self, results: Dict) -> str:
        """Calcula nível de alerta baseado nas atualizações"""
        news_count = len(results.get("news", {}).get("news", []))

        # Verificar notícias importantes
        for news_item in results.get("news", {}).get("news", []):
            sentiment = news_item.get("sentiment", "neutral")
            if sentiment == "negative":
                return "high"

        if news_count > 5:
            return "medium"

        return "low"

    async def get_market_share_estimate(
        self,
        industry: str,
        companies: List[str],
        location: str = "Brasil"
    ) -> Dict[str, Any]:
        """
        Estima market share de empresas em um setor

        Args:
            industry: Setor
            companies: Lista de empresas
            location: Localização

        Returns:
            Estimativa de market share
        """
        logger.info("competitor_market_share", industry=industry, companies=companies)

        # Pesquisar market share
        query = f"market share {industry} {location} {' '.join(companies)}"
        research = await self.perplexity.research(
            query,
            focus_areas=["market share", "participação de mercado", "liderança"]
        )

        # Buscar dados específicos
        market_data = await self.tavily.research(
            f"participação de mercado {industry} {location} 2024"
        )

        return {
            "industry": industry,
            "location": location,
            "companies": companies,
            "market_share_analysis": research.get("answer"),
            "market_data": market_data.get("answer"),
            "sources": research.get("citations", []) + market_data.get("results", []),
            "disclaimer": "Estimativas baseadas em dados públicos disponíveis"
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
