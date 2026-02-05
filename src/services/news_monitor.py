"""
News Monitor Service
Monitoramento de notícias e cenário econômico
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.scrapers import PerplexityClient, SerperClient, TavilyClient

from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class NewsMonitorService:
    """
    Serviço de monitoramento de notícias

    Funcionalidades:
    - Busca de notícias por empresa/pessoa
    - Monitoramento de setores
    - Cenário econômico
    - Alertas de tendências
    """

    def __init__(self):
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.ai_analyzer = AIAnalyzer()

    async def close(self):
        """Fecha todos os clientes"""
        await asyncio.gather(
            self.serper.close(),
            self.tavily.close(),
            self.perplexity.close(),
            self.ai_analyzer.close()
        )

    async def search_news(
        self,
        query: str,
        days: int = 7,
        max_results: int = 20,
        sources: Optional[List[str]] = None,
        sentiment_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca notícias por query

        Args:
            query: Termo de busca
            days: Dias para buscar
            max_results: Máximo de resultados
            sources: Fontes específicas
            sentiment_filter: "positive", "negative", "neutral"

        Returns:
            Notícias encontradas
        """
        logger.info("news_search", query=query, days=days)

        # Buscar via múltiplas fontes
        tasks = [
            self.serper.search_news(query, num=max_results, tbs=self._days_to_tbs(days)),
            self.tavily.search_news(query, max_results=max_results, days=days)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Consolidar notícias
        all_news = []

        # Do Serper
        if not isinstance(results[0], Exception):
            for item in results[0].get("news", []):
                all_news.append(self._normalize_news_item(item, "serper"))

        # Do Tavily
        if not isinstance(results[1], Exception):
            for item in results[1].get("results", []):
                all_news.append(self._normalize_news_item(item, "tavily"))

        # Remover duplicatas por URL
        seen_urls = set()
        unique_news = []
        for news in all_news:
            url = news.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)

        # Analisar sentimento
        for news in unique_news:
            news["sentiment"] = self._analyze_sentiment(
                news.get("title", "") + " " + news.get("content", "")
            )

        # Filtrar por sentimento se especificado
        if sentiment_filter:
            unique_news = [n for n in unique_news if n.get("sentiment") == sentiment_filter]

        # Ordenar por data
        unique_news.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True
        )

        return {
            "query": query,
            "news": unique_news[:max_results],
            "total": len(unique_news),
            "summary": results[1].get("answer") if not isinstance(results[1], Exception) else None,
            "sentiment_distribution": self._calculate_sentiment_distribution(unique_news)
        }

    def _days_to_tbs(self, days: int) -> str:
        """Converte dias para formato tbs do Google"""
        if days <= 1:
            return "qdr:d"
        elif days <= 7:
            return "qdr:w"
        elif days <= 30:
            return "qdr:m"
        else:
            return "qdr:y"

    def _normalize_news_item(self, item: Dict, source: str) -> Dict[str, Any]:
        """Normaliza item de notícia de diferentes fontes"""
        if source == "serper":
            return {
                "title": item.get("title"),
                "url": item.get("link"),
                "source": item.get("source"),
                "content": item.get("snippet"),
                "published_at": item.get("date"),
                "image_url": item.get("imageUrl"),
                "data_source": "serper"
            }
        elif source == "tavily":
            return {
                "title": item.get("title"),
                "url": item.get("url"),
                "source": self._extract_domain(item.get("url", "")),
                "content": item.get("content"),
                "published_at": item.get("published_date"),
                "relevance_score": item.get("score"),
                "data_source": "tavily"
            }
        return item

    def _extract_domain(self, url: str) -> str:
        """Extrai domínio de URL"""
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return url

    def _analyze_sentiment(self, text: str) -> str:
        """Análise de sentimento básica"""
        text_lower = text.lower()

        positive_words = [
            "crescimento", "sucesso", "lucro", "expansão", "inovação",
            "investimento", "alta", "aumento", "ganho", "melhora",
            "positivo", "otimismo", "recorde", "conquista"
        ]

        negative_words = [
            "crise", "queda", "prejuízo", "demissão", "problema",
            "escândalo", "processo", "falência", "perda", "redução",
            "negativo", "pessimismo", "risco", "preocupação"
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    def _calculate_sentiment_distribution(self, news: List[Dict]) -> Dict[str, int]:
        """Calcula distribuição de sentimentos"""
        distribution = {"positive": 0, "negative": 0, "neutral": 0}
        for item in news:
            sentiment = item.get("sentiment", "neutral")
            distribution[sentiment] = distribution.get(sentiment, 0) + 1
        return distribution

    async def get_company_news(
        self,
        company_name: str,
        days: int = 30,
        include_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Busca notícias sobre uma empresa

        Args:
            company_name: Nome da empresa
            days: Dias para buscar
            include_analysis: Incluir análise AI

        Returns:
            Notícias da empresa
        """
        logger.info("news_company", company=company_name, days=days)

        # Buscar notícias
        news = await self.search_news(f'"{company_name}"', days=days, max_results=30)

        result = {
            "company": company_name,
            "news": news.get("news", []),
            "total": news.get("total", 0),
            "sentiment_distribution": news.get("sentiment_distribution"),
            "summary": news.get("summary")
        }

        # Análise AI se solicitado
        if include_analysis and news.get("news"):
            analysis = await self._analyze_news_batch(company_name, news.get("news", []))
            result["analysis"] = analysis

        return result

    async def _analyze_news_batch(
        self,
        entity_name: str,
        news_items: List[Dict]
    ) -> Dict[str, Any]:
        """Analisa um conjunto de notícias"""
        # Preparar resumo das notícias
        news_summary = [
            {
                "title": n.get("title"),
                "sentiment": n.get("sentiment"),
                "source": n.get("source")
            }
            for n in news_items[:10]
        ]

        prompt = f"""Analise estas notícias recentes sobre "{entity_name}" e forneça:
1. Principais temas cobertos
2. Tendência geral (positiva/negativa/neutra)
3. Impactos potenciais para a empresa/pessoa
4. Recomendações baseadas nas notícias

Notícias:
{news_summary}"""

        try:
            analysis = await self.ai_analyzer._call_claude(
                prompt,
                system="Você é um analista de mídia. Responda de forma concisa e objetiva."
            )
            return {"ai_analysis": analysis}
        except Exception as e:
            logger.warning("news_analysis_error", error=str(e))
            return {"ai_analysis": None}

    async def get_sector_news(
        self,
        sector: str,
        days: int = 7,
        country: str = "Brasil"
    ) -> Dict[str, Any]:
        """
        Busca notícias de um setor

        Args:
            sector: Setor/indústria
            days: Dias para buscar
            country: País

        Returns:
            Notícias do setor
        """
        logger.info("news_sector", sector=sector, country=country)

        query = f"{sector} {country}"
        news = await self.search_news(query, days=days, max_results=30)

        # Pesquisa contextual
        context = await self.perplexity.analyze_market(sector)

        return {
            "sector": sector,
            "country": country,
            "news": news.get("news", []),
            "total": news.get("total", 0),
            "market_context": context.get("analysis"),
            "sentiment_distribution": news.get("sentiment_distribution")
        }

    async def get_economic_scenario(
        self,
        aspects: Optional[List[str]] = None,
        country: str = "Brasil"
    ) -> Dict[str, Any]:
        """
        Busca cenário econômico atual

        Args:
            aspects: Aspectos específicos
            country: País

        Returns:
            Análise do cenário econômico
        """
        logger.info("news_economic_scenario", country=country)

        if aspects is None:
            aspects = [
                "inflação",
                "taxa de juros",
                "PIB",
                "câmbio",
                "emprego"
            ]

        results = {}

        # Buscar cada aspecto
        for aspect in aspects:
            query = f"{aspect} {country} economia"
            search = await self.tavily.search(
                query,
                search_depth="basic",
                include_answer=True,
                max_results=3
            )
            results[aspect] = {
                "summary": search.get("answer"),
                "sources": [r.get("url") for r in search.get("results", [])]
            }

        # Visão geral
        overview = await self.perplexity.research(
            f"cenário econômico {country} atual perspectivas",
            depth="detailed"
        )

        # Notícias econômicas
        news = await self.search_news(
            f"economia {country}",
            days=7,
            max_results=15
        )

        return {
            "country": country,
            "overview": overview.get("answer"),
            "aspects": results,
            "recent_news": news.get("news", []),
            "sentiment": news.get("sentiment_distribution"),
            "sources": overview.get("citations", [])
        }

    async def get_trending_topics(
        self,
        category: Optional[str] = None,
        country: str = "Brasil"
    ) -> Dict[str, Any]:
        """
        Busca tópicos em alta

        Args:
            category: Categoria (negócios, tecnologia, etc)
            country: País

        Returns:
            Tópicos em trending
        """
        logger.info("news_trending", category=category, country=country)

        query = f"tendências {category or 'negócios'} {country} 2024"

        # Buscar tendências
        trends = await self.tavily.get_market_trends(
            category or "negócios",
            country
        )

        # Buscar notícias relacionadas
        news = await self.serper.search_news(query, num=10, tbs="qdr:d")

        # Extrair tópicos das notícias
        topics = self._extract_trending_topics(news.get("news", []))

        return {
            "category": category,
            "country": country,
            "trends": trends.get("trends"),
            "trending_topics": topics,
            "recent_news": news.get("news", []),
            "sources": trends.get("sources", [])
        }

    def _extract_trending_topics(self, news_items: List[Dict]) -> List[str]:
        """Extrai tópicos em alta das notícias"""
        import re
        from collections import Counter

        # Palavras para ignorar
        stopwords = {
            "de", "da", "do", "em", "para", "com", "que", "uma", "um",
            "os", "as", "por", "no", "na", "se", "não", "mais", "seu",
            "sua", "como", "sobre", "após", "entre", "ser", "está"
        }

        words = []
        for item in news_items:
            title = item.get("title", "")
            # Extrair palavras significativas
            title_words = re.findall(r'\b[A-Za-zÀ-ú]{4,}\b', title)
            words.extend([w.lower() for w in title_words if w.lower() not in stopwords])

        # Contar frequência
        counter = Counter(words)
        return [word for word, count in counter.most_common(10)]

    async def monitor_entity(
        self,
        entity_name: str,
        entity_type: str = "company",
        alert_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Monitora uma entidade para alertas

        Args:
            entity_name: Nome da entidade
            entity_type: "company", "person", "sector"
            alert_keywords: Palavras-chave para alertas

        Returns:
            Status do monitoramento
        """
        logger.info("news_monitor", entity=entity_name, type=entity_type)

        if alert_keywords is None:
            if entity_type == "company":
                alert_keywords = ["crise", "processo", "escândalo", "demissão", "fraude"]
            else:
                alert_keywords = ["polêmica", "denúncia", "investigação", "crítica"]

        # Buscar notícias recentes
        news = await self.search_news(f'"{entity_name}"', days=1, max_results=20)

        # Verificar alertas
        alerts = []
        for item in news.get("news", []):
            text = (item.get("title", "") + " " + item.get("content", "")).lower()
            for keyword in alert_keywords:
                if keyword.lower() in text:
                    alerts.append({
                        "keyword": keyword,
                        "news_item": item,
                        "severity": "high" if item.get("sentiment") == "negative" else "medium"
                    })
                    break

        return {
            "entity": entity_name,
            "entity_type": entity_type,
            "monitoring_time": datetime.utcnow().isoformat(),
            "news_count": news.get("total", 0),
            "alerts": alerts,
            "alert_count": len(alerts),
            "has_critical_alerts": any(a.get("severity") == "high" for a in alerts),
            "sentiment_distribution": news.get("sentiment_distribution")
        }

    async def get_daily_briefing(
        self,
        topics: List[str],
        country: str = "Brasil"
    ) -> Dict[str, Any]:
        """
        Gera briefing diário de notícias

        Args:
            topics: Tópicos de interesse
            country: País

        Returns:
            Briefing consolidado
        """
        logger.info("news_briefing", topics=topics)

        briefing = {
            "date": datetime.utcnow().date().isoformat(),
            "country": country,
            "topics": {}
        }

        # Buscar notícias para cada tópico
        for topic in topics:
            news = await self.search_news(f"{topic} {country}", days=1, max_results=5)
            briefing["topics"][topic] = {
                "top_news": news.get("news", [])[:5],
                "summary": news.get("summary"),
                "sentiment": news.get("sentiment_distribution")
            }

        # Visão geral do dia
        overview_query = f"principais notícias {country} hoje"
        overview = await self.tavily.search(
            overview_query,
            search_depth="basic",
            include_answer=True,
            max_results=5
        )

        briefing["day_overview"] = overview.get("answer")
        briefing["headline_news"] = overview.get("results", [])[:5]

        return briefing

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
