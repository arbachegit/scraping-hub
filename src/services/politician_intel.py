"""
Politician Intelligence Service
Inteligência sobre políticos - perfil pessoal (não político)
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from src.scrapers import PerplexityClient, SerperClient, TavilyClient

from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class PoliticianIntelService:
    """
    Serviço de inteligência sobre políticos

    IMPORTANTE: Foco em perfil PESSOAL, não político
    - Histórico pessoal e familiar
    - Formação e carreira
    - Presença em redes sociais
    - Percepção pública

    NÃO analisamos:
    - Posições políticas
    - Votações ou projetos
    - Afiliação partidária
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

    async def analyze_politician(
        self,
        name: str,
        role: Optional[str] = None,
        state: Optional[str] = None,
        focus: str = "personal"
    ) -> Dict[str, Any]:
        """
        Análise de perfil pessoal de um político

        Args:
            name: Nome do político
            role: Cargo (prefeito, senador, deputado, etc)
            state: Estado
            focus: "personal", "career", "public_perception"

        Returns:
            Perfil pessoal do político
        """
        logger.info(
            "politician_intel_analyze",
            name=name,
            role=role,
            state=state,
            focus=focus
        )

        result = {
            "name": name,
            "role": role,
            "state": state,
            "focus": focus,
            "status": "processing"
        }

        try:
            # 1. Coletar dados em paralelo
            tasks = {
                "search_data": self.serper.find_politician_info(name, role, state),
                "research_data": self.perplexity.research_politician(name, role, state, focus),
                "tavily_data": self.tavily.research_politician(name, role, state)
            }

            results = await asyncio.gather(
                *tasks.values(),
                return_exceptions=True
            )

            # Mapear resultados
            task_keys = list(tasks.keys())
            for i, key in enumerate(task_keys):
                if isinstance(results[i], Exception):
                    logger.warning(f"politician_intel_{key}_error", error=str(results[i]))
                    result[key] = {}
                else:
                    result[key] = results[i]

            # 2. Consolidar perfil
            profile = self._consolidate_politician_data(result, name, role, state)
            result["profile"] = profile

            # 3. Buscar redes sociais
            social_media = await self._get_social_media(name, role)
            result["social_media"] = social_media

            # 4. Análise AI
            ai_analysis = await self.ai_analyzer.analyze_politician_profile(
                profile,
                news_data=result.get("search_data", {}).get("news", [])
            )
            result["ai_analysis"] = ai_analysis

            result["status"] = "completed"

        except Exception as e:
            logger.error("politician_intel_error", name=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _consolidate_politician_data(
        self,
        result: Dict,
        name: str,
        role: Optional[str],
        state: Optional[str]
    ) -> Dict[str, Any]:
        """Consolida dados de múltiplas fontes"""
        search_data = result.get("search_data", {})
        research_data = result.get("research_data", {})
        tavily_data = result.get("tavily_data", {})

        profile = {
            # Identificação
            "name": name,
            "role": role,
            "state": state,

            # Redes sociais (dos resultados de busca)
            "instagram": search_data.get("social_media", {}).get("instagram"),
            "twitter": search_data.get("social_media", {}).get("twitter"),
            "facebook": search_data.get("social_media", {}).get("facebook"),

            # Knowledge graph
            "knowledge_graph": search_data.get("knowledge_graph"),

            # Pesquisa
            "research_profile": research_data.get("profile"),
            "research_details": research_data.get("research", {}),

            # Notícias
            "recent_news": search_data.get("news", [])[:10],
            "news_summary": tavily_data.get("news_summary"),

            # Resultados governamentais
            "gov_sources": search_data.get("gov_results", []),

            # Fontes
            "sources": self._list_sources(result)
        }

        return profile

    def _list_sources(self, result: Dict) -> List[str]:
        """Lista fontes usadas"""
        sources = []
        if result.get("search_data"):
            sources.append("Google Search (Serper)")
        if result.get("research_data"):
            sources.append("Perplexity AI")
        if result.get("tavily_data"):
            sources.append("Tavily Search")
        return sources

    async def _get_social_media(self, name: str, role: Optional[str] = None) -> Dict[str, Any]:
        """Busca perfis em redes sociais"""
        social = {}

        platforms = [
            ("instagram", "site:instagram.com"),
            ("twitter", "site:twitter.com OR site:x.com"),
            ("facebook", "site:facebook.com"),
            ("youtube", "site:youtube.com")
        ]

        for platform, site_filter in platforms:
            try:
                query = f'"{name}"'
                if role:
                    query += f" {role}"
                query += f" {site_filter}"

                search = await self.serper.search(query, num=3)

                for item in search.get("organic", []):
                    url = item.get("link", "")
                    if platform in url or ("x.com" in url and platform == "twitter"):
                        social[platform] = {
                            "url": url,
                            "title": item.get("title"),
                            "snippet": item.get("snippet")
                        }
                        break

            except Exception as e:
                logger.warning(f"social_search_error_{platform}", error=str(e))

        return social

    async def get_public_perception(
        self,
        name: str,
        role: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analisa percepção pública

        Args:
            name: Nome do político
            role: Cargo
            days: Dias para análise

        Returns:
            Análise de percepção pública
        """
        logger.info("politician_intel_perception", name=name)

        # Buscar notícias
        news_query = f'"{name}"'
        if role:
            news_query += f" {role}"

        news = await self.tavily.search_news(news_query, max_results=20, days=days)

        # Analisar sentimento das notícias
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        news_items = news.get("results", [])

        for item in news_items:
            sentiment = self._analyze_sentiment(item.get("content", ""))
            sentiments[sentiment] += 1

        # Pesquisar percepção
        perception_research = await self.perplexity.chat(
            f"Qual é a percepção pública atual sobre {name} {'(' + role + ')' if role else ''}? "
            "Analise a imagem pública, pontos positivos e negativos na visão da população.",
            system_prompt="Analise de forma objetiva e imparcial, baseado em fatos públicos."
        )

        return {
            "name": name,
            "role": role,
            "analysis_period_days": days,
            "news_sentiment": sentiments,
            "total_news": len(news_items),
            "perception_analysis": perception_research.get("answer"),
            "sample_news": news_items[:5],
            "citations": perception_research.get("citations", [])
        }

    def _analyze_sentiment(self, text: str) -> str:
        """Análise de sentimento básica"""
        text_lower = text.lower()

        positive_words = [
            "sucesso", "aprovação", "conquista", "vitória", "elogio",
            "popular", "apoio", "reconhecimento", "destaque", "positivo"
        ]

        negative_words = [
            "crise", "crítica", "polêmica", "escândalo", "denúncia",
            "investigação", "rejeição", "protesto", "negativo", "problema"
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    async def get_personal_history(
        self,
        name: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca histórico pessoal (não político)

        Args:
            name: Nome do político
            role: Cargo (para contexto)

        Returns:
            Histórico pessoal
        """
        logger.info("politician_intel_history", name=name)

        # Pesquisar biografia
        bio_research = await self.perplexity.chat(
            f"Qual é a biografia pessoal de {name}? "
            "Inclua: nascimento, família, educação, carreira antes da política, "
            "interesses pessoais. Não inclua informações sobre posições políticas.",
            system_prompt="Forneça apenas fatos biográficos verificáveis. Evite viés político."
        )

        # Buscar informações educacionais
        education_search = await self.serper.search(
            f'"{name}" formação educação universidade',
            num=5
        )

        # Buscar carreira pré-política
        career_search = await self.serper.search(
            f'"{name}" carreira profissional antes política',
            num=5
        )

        return {
            "name": name,
            "role": role,
            "biography": bio_research.get("answer"),
            "education_sources": education_search.get("organic", []),
            "career_sources": career_search.get("organic", []),
            "citations": bio_research.get("citations", [])
        }

    async def get_media_presence(
        self,
        name: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analisa presença na mídia

        Args:
            name: Nome do político
            role: Cargo

        Returns:
            Análise de presença na mídia
        """
        logger.info("politician_intel_media", name=name)

        # Buscar redes sociais
        social_media = await self._get_social_media(name, role)

        # Buscar menções na mídia
        media_mentions = await self.serper.search_news(
            f'"{name}"',
            num=20,
            tbs="qdr:m"  # último mês
        )

        # Buscar entrevistas
        interviews = await self.serper.search(
            f'"{name}" entrevista OR podcast OR programa',
            num=10
        )

        # Buscar vídeos
        videos = await self.serper.search(
            f'"{name}" site:youtube.com',
            num=5
        )

        return {
            "name": name,
            "social_media": social_media,
            "media_mentions": {
                "count": len(media_mentions.get("news", [])),
                "recent": media_mentions.get("news", [])[:10]
            },
            "interviews": interviews.get("organic", []),
            "youtube_presence": videos.get("organic", [])
        }

    async def search_politicians(
        self,
        role: Optional[str] = None,
        state: Optional[str] = None,
        party: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Busca políticos por critérios

        Args:
            role: Cargo (prefeito, senador, etc)
            state: Estado
            party: Partido (apenas para filtro, não análise)
            limit: Limite de resultados

        Returns:
            Lista de políticos encontrados
        """
        logger.info("politician_intel_search", role=role, state=state)

        query_parts = []
        if role:
            query_parts.append(role)
        if state:
            query_parts.append(state)
        if party:
            query_parts.append(party)

        query_parts.append("Brasil político")
        query = " ".join(query_parts)

        search = await self.serper.search(query, num=limit * 2)

        # Extrair nomes dos resultados
        politicians = []
        seen_names = set()

        for item in search.get("organic", []):
            # Tentar extrair nome do título
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # Heurística simples para extrair nomes
            # Em produção, usar NER mais sofisticado
            import re
            name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            matches = re.findall(name_pattern, title + " " + snippet)

            for name in matches:
                if name not in seen_names and len(name) > 5:
                    seen_names.add(name)
                    politicians.append({
                        "name": name,
                        "source": item.get("link"),
                        "context": snippet[:200]
                    })

                    if len(politicians) >= limit:
                        break

            if len(politicians) >= limit:
                break

        return {
            "search_criteria": {
                "role": role,
                "state": state,
                "party": party
            },
            "politicians": politicians,
            "total": len(politicians)
        }

    async def quick_lookup(
        self,
        name: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca rápida de político

        Args:
            name: Nome do político
            role: Cargo

        Returns:
            Dados básicos
        """
        logger.info("politician_intel_quick", name=name)

        # Buscar informações básicas
        search = await self.serper.search(
            f'"{name}" {"" if not role else role} político Brasil',
            num=5
        )

        # Extrair knowledge graph se disponível
        kg = search.get("knowledge_graph", {})

        # Buscar redes sociais
        social = await self._get_social_media(name, role)

        return {
            "name": name,
            "role": role,
            "description": kg.get("description") or search.get("organic", [{}])[0].get("snippet"),
            "social_media": social,
            "search_results": search.get("organic", [])[:3]
        }

    async def monitor_politician(
        self,
        name: str,
        role: Optional[str] = None,
        alert_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Monitora político para alertas

        Args:
            name: Nome do político
            role: Cargo
            alert_keywords: Palavras-chave para alertas

        Returns:
            Status do monitoramento
        """
        logger.info("politician_intel_monitor", name=name)

        if alert_keywords is None:
            alert_keywords = [
                "polêmica", "escândalo", "denúncia", "investigação",
                "crítica", "protesto", "processo"
            ]

        # Buscar notícias recentes (24h)
        news = await self.serper.search_news(
            f'"{name}"',
            num=20,
            tbs="qdr:d"
        )

        # Verificar alertas
        alerts = []
        for item in news.get("news", []):
            text = (item.get("title", "") + " " + item.get("snippet", "")).lower()
            for keyword in alert_keywords:
                if keyword.lower() in text:
                    alerts.append({
                        "keyword": keyword,
                        "news": {
                            "title": item.get("title"),
                            "link": item.get("link"),
                            "source": item.get("source")
                        },
                        "severity": "high" if keyword in ["escândalo", "denúncia", "investigação"] else "medium"
                    })
                    break

        return {
            "name": name,
            "role": role,
            "monitoring_period": "24h",
            "news_count": len(news.get("news", [])),
            "alerts": alerts,
            "alert_count": len(alerts),
            "has_critical_alerts": any(a.get("severity") == "high" for a in alerts)
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
