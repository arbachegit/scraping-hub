"""
Extended Person Enrichment Service
Integra múltiplas fontes para enriquecimento completo de pessoas.

Fontes:
1. Apollo (LinkedIn, histórico profissional) - JÁ EXISTENTE
2. Perplexity (fallback AI) - JÁ EXISTENTE
3. GitHub (perfil técnico)
4. Google Scholar (publicações acadêmicas)
5. Google News (análise reputacional)
6. Reclame Aqui (reclamações)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog
from supabase import Client

logger = structlog.get_logger()


class ExtendedPersonEnrichmentService:
    """Serviço estendido para enriquecimento de dados de pessoas."""

    def __init__(
        self,
        supabase: Client,
        serper_api_key: str | None = None,
        github_token: str | None = None,
        apollo_api_key: str | None = None,
        perplexity_api_key: str | None = None,
    ):
        """
        Inicializa o serviço.

        Args:
            supabase: Cliente Supabase
            serper_api_key: API key do Serper (para Scholar, News, Reclame Aqui)
            github_token: Token do GitHub (opcional, aumenta rate limit)
            apollo_api_key: API key do Apollo
            perplexity_api_key: API key do Perplexity
        """
        self.supabase = supabase
        self.serper_api_key = serper_api_key
        self.github_token = github_token
        self.apollo_api_key = apollo_api_key
        self.perplexity_api_key = perplexity_api_key
        self.serper_base_url = "https://google.serper.dev"
        self.github_base_url = "https://api.github.com"

    async def enrich_person_full(
        self,
        pessoa_id: str,
        nome: str,
        empresa_nome: str | None = None,
        linkedin_url: str | None = None,
        enrich_github: bool = True,
        enrich_scholar: bool = True,
        enrich_news: bool = True,
        enrich_reclameaqui: bool = True,
    ) -> dict[str, Any]:
        """
        Enriquecimento completo de uma pessoa.

        Args:
            pessoa_id: ID da pessoa no banco
            nome: Nome completo
            empresa_nome: Nome da empresa (opcional)
            linkedin_url: URL do LinkedIn (opcional)
            enrich_github: Buscar perfil GitHub
            enrich_scholar: Buscar publicações acadêmicas
            enrich_news: Buscar notícias
            enrich_reclameaqui: Buscar reclamações

        Returns:
            Dados enriquecidos de todas as fontes
        """
        result = {
            "pessoa_id": pessoa_id,
            "nome": nome,
            "sources_checked": [],
            "github": None,
            "scholar": None,
            "news": None,
            "reclameaqui": None,
            "competencies": {},
            "risk_analysis": {},
            "enriched_at": datetime.utcnow().isoformat(),
        }

        tasks = []

        if enrich_github:
            tasks.append(("github", self._enrich_github(nome, empresa_nome)))
            result["sources_checked"].append("github")

        if enrich_scholar and self.serper_api_key:
            tasks.append(("scholar", self._enrich_scholar(nome, empresa_nome)))
            result["sources_checked"].append("google_scholar")

        if enrich_news and self.serper_api_key:
            tasks.append(("news", self._enrich_news(nome, empresa_nome)))
            result["sources_checked"].append("google_news")

        if enrich_reclameaqui and self.serper_api_key:
            tasks.append(("reclameaqui", self._enrich_reclameaqui(nome, empresa_nome)))
            result["sources_checked"].append("reclame_aqui")

        # Execute all enrichments in parallel
        if tasks:
            task_results = await asyncio.gather(
                *[task[1] for task in tasks], return_exceptions=True
            )

            for i, (source_name, _) in enumerate(tasks):
                task_result = task_results[i]
                if isinstance(task_result, Exception):
                    logger.error(
                        "enrichment_source_error",
                        source=source_name,
                        error=str(task_result),
                    )
                    result[source_name] = {"error": str(task_result)}
                else:
                    result[source_name] = task_result

        # Consolidate competencies
        result["competencies"] = self._consolidate_competencies(result)

        # Consolidate risk analysis
        result["risk_analysis"] = self._consolidate_risk(result)

        # Save to database
        await self._save_enrichment(pessoa_id, result)

        return result

    async def _enrich_github(
        self, nome: str, empresa_nome: str | None
    ) -> dict[str, Any]:
        """Busca perfil GitHub."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "iconsai-scraping",
        }

        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        # Search for user
        query = nome.replace(" ", "+")
        if empresa_nome:
            query += "+location:Brazil"

        try:
            async with httpx.AsyncClient() as client:
                # Search users
                response = await client.get(
                    f"{self.github_base_url}/search/users",
                    params={"q": query, "per_page": 3},
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return {"found": False, "error": f"Status {response.status_code}"}

                data = response.json()
                users = data.get("items", [])

                if not users:
                    return {"found": False, "profiles": []}

                # Get profile details for first user
                profiles = []
                for user in users[:3]:
                    profile_resp = await client.get(
                        f"{self.github_base_url}/users/{user['login']}",
                        headers=headers,
                        timeout=30.0,
                    )

                    if profile_resp.status_code == 200:
                        profile = profile_resp.json()

                        # Get repos for language stats
                        repos_resp = await client.get(
                            f"{self.github_base_url}/users/{user['login']}/repos",
                            params={"sort": "updated", "per_page": 100},
                            headers=headers,
                            timeout=30.0,
                        )

                        languages = {}
                        total_stars = 0

                        if repos_resp.status_code == 200:
                            repos = repos_resp.json()
                            for repo in repos:
                                if repo.get("language"):
                                    lang = repo["language"]
                                    languages[lang] = languages.get(lang, 0) + 1
                                total_stars += repo.get("stargazers_count", 0)

                        profiles.append(
                            {
                                "username": profile.get("login"),
                                "name": profile.get("name"),
                                "bio": profile.get("bio"),
                                "company": profile.get("company"),
                                "location": profile.get("location"),
                                "email": profile.get("email"),
                                "html_url": profile.get("html_url"),
                                "public_repos": profile.get("public_repos"),
                                "followers": profile.get("followers"),
                                "total_stars": total_stars,
                                "top_languages": sorted(
                                    languages.items(), key=lambda x: x[1], reverse=True
                                )[:5],
                                "created_at": profile.get("created_at"),
                            }
                        )

                # Try to find best match
                best_match = None
                if empresa_nome:
                    empresa_lower = empresa_nome.lower()
                    for p in profiles:
                        if p.get("company") and empresa_lower in p["company"].lower():
                            best_match = p
                            break

                if not best_match and profiles:
                    best_match = profiles[0]

                return {
                    "found": True,
                    "profiles": profiles,
                    "best_match": best_match,
                    "competencies": self._analyze_github_competencies(best_match),
                }

        except Exception as e:
            logger.error("github_enrichment_error", error=str(e))
            return {"found": False, "error": str(e)}

    async def _enrich_scholar(
        self, nome: str, instituicao: str | None
    ) -> dict[str, Any]:
        """Busca publicações acadêmicas no Google Scholar via Serper."""
        query = f'author:"{nome}"'
        if instituicao:
            query += f' "{instituicao}"'

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.serper_base_url}/scholar",
                    json={"q": query, "num": 20},
                    headers={
                        "X-API-KEY": self.serper_api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return {"found": False, "error": f"Status {response.status_code}"}

                data = response.json()
                publications = []

                for item in data.get("organic", []):
                    publications.append(
                        {
                            "title": item.get("title"),
                            "link": item.get("link"),
                            "snippet": item.get("snippet"),
                            "publication_info": item.get("publicationInfo"),
                            "cited_by": self._extract_citations(item),
                        }
                    )

                metrics = self._calculate_academic_metrics(publications)

                return {
                    "found": len(publications) > 0,
                    "publications": publications,
                    "metrics": metrics,
                    "competencies": self._analyze_academic_competencies(metrics),
                }

        except Exception as e:
            logger.error("scholar_enrichment_error", error=str(e))
            return {"found": False, "error": str(e)}

    async def _enrich_news(self, nome: str, empresa_nome: str | None) -> dict[str, Any]:
        """Busca notícias para análise reputacional via Serper News."""
        query = f'"{nome}"'
        if empresa_nome:
            query += f' "{empresa_nome}"'

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.serper_base_url}/news",
                    json={"q": query, "num": 30, "gl": "br", "hl": "pt-br"},
                    headers={
                        "X-API-KEY": self.serper_api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return {"found": False, "error": f"Status {response.status_code}"}

                data = response.json()
                articles = []

                for item in data.get("news", []):
                    sentiment = self._analyze_sentiment(
                        item.get("title", ""), item.get("snippet", "")
                    )
                    articles.append(
                        {
                            "title": item.get("title"),
                            "link": item.get("link"),
                            "snippet": item.get("snippet"),
                            "source": item.get("source"),
                            "date": item.get("date"),
                            "sentiment": sentiment,
                        }
                    )

                metrics = self._calculate_reputation_metrics(articles)
                negative_alerts = [a for a in articles if a["sentiment"] == "negative"]

                return {
                    "found": len(articles) > 0,
                    "articles": articles[:20],  # Limit stored articles
                    "metrics": metrics,
                    "negative_alerts": negative_alerts[:5],
                }

        except Exception as e:
            logger.error("news_enrichment_error", error=str(e))
            return {"found": False, "error": str(e)}

    async def _enrich_reclameaqui(
        self, nome: str, empresa_nome: str | None
    ) -> dict[str, Any]:
        """Busca reclamações no Reclame Aqui via Serper."""
        query = f'"{nome}" site:reclameaqui.com.br'
        if empresa_nome:
            query += f' "{empresa_nome}"'

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.serper_base_url}/search",
                    json={"q": query, "num": 20, "gl": "br", "hl": "pt-br"},
                    headers={
                        "X-API-KEY": self.serper_api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return {"found": False, "error": f"Status {response.status_code}"}

                data = response.json()
                mentions = []

                nome_lower = nome.lower().split()[0]  # First name for matching

                for item in data.get("organic", []):
                    text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
                    if nome_lower in text:
                        mentions.append(
                            {
                                "url": item.get("link"),
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                            }
                        )

                risk_level = "nenhum"
                if len(mentions) > 2:
                    risk_level = "medio"
                elif len(mentions) > 0:
                    risk_level = "baixo"

                return {
                    "found": len(mentions) > 0,
                    "mentions": mentions,
                    "total_found": len(mentions),
                    "risk_level": risk_level,
                }

        except Exception as e:
            logger.error("reclameaqui_enrichment_error", error=str(e))
            return {"found": False, "error": str(e)}

    def _extract_citations(self, item: dict) -> int:
        """Extrai contagem de citações de item do Scholar."""
        cited_by = item.get("citedBy")
        if cited_by:
            import re

            match = re.search(r"\d+", str(cited_by))
            return int(match.group()) if match else 0
        return 0

    def _calculate_academic_metrics(self, publications: list[dict]) -> dict[str, Any]:
        """Calcula métricas acadêmicas."""
        if not publications:
            return {
                "total_publications": 0,
                "total_citations": 0,
                "h_index": 0,
            }

        citations = [p.get("cited_by", 0) for p in publications]
        citations_sorted = sorted(citations, reverse=True)

        # Calculate h-index
        h_index = 0
        for i, c in enumerate(citations_sorted):
            if c >= i + 1:
                h_index = i + 1
            else:
                break

        return {
            "total_publications": len(publications),
            "total_citations": sum(citations),
            "h_index": h_index,
        }

    def _analyze_sentiment(self, title: str, snippet: str) -> str:
        """Analisa sentimento de texto de notícia."""
        text = f"{title} {snippet}".lower()

        negative_words = [
            "fraude",
            "escândalo",
            "prisão",
            "preso",
            "denúncia",
            "corrupção",
            "acusado",
            "investigado",
            "condenado",
            "processo",
            "crime",
            "demitido",
            "afastado",
            "multa",
            "lavagem",
            "delação",
        ]

        positive_words = [
            "premiado",
            "sucesso",
            "inovação",
            "crescimento",
            "expansão",
            "liderança",
            "reconhecimento",
            "conquista",
            "investimento",
            "parceria",
            "destaque",
            "eleito",
            "nomeado",
            "promovido",
        ]

        neg_count = sum(1 for w in negative_words if w in text)
        pos_count = sum(1 for w in positive_words if w in text)

        if neg_count > pos_count and neg_count > 0:
            return "negative"
        elif pos_count > neg_count and pos_count > 0:
            return "positive"
        return "neutral"

    def _calculate_reputation_metrics(self, articles: list[dict]) -> dict[str, Any]:
        """Calcula métricas reputacionais."""
        if not articles:
            return {
                "total_mentions": 0,
                "sentiment_score": 0,
                "risk_level": "desconhecido",
            }

        positive = sum(1 for a in articles if a["sentiment"] == "positive")
        negative = sum(1 for a in articles if a["sentiment"] == "negative")
        total = len(articles)

        sentiment_score = round(((positive - negative) / total) * 100)

        risk_level = "baixo"
        if negative >= 3:
            risk_level = "alto"
        elif negative >= 1:
            risk_level = "medio"

        return {
            "total_mentions": total,
            "positive_count": positive,
            "negative_count": negative,
            "sentiment_score": sentiment_score,
            "risk_level": risk_level,
        }

    def _analyze_github_competencies(self, profile: dict | None) -> dict[str, Any]:
        """Analisa competências técnicas do perfil GitHub."""
        if not profile:
            return {}

        competencies = {
            "nivel_tecnico": "junior",
            "linguagens": [lang for lang, _ in profile.get("top_languages", [])],
            "score_atividade": 0,
        }

        # Calculate activity score
        repos = profile.get("public_repos", 0)
        stars = profile.get("total_stars", 0)
        followers = profile.get("followers", 0)

        score = min(repos * 2, 40) + min(stars * 0.5, 30) + min(followers * 0.2, 30)
        competencies["score_atividade"] = round(score)

        if score >= 80:
            competencies["nivel_tecnico"] = "senior"
        elif score >= 50:
            competencies["nivel_tecnico"] = "pleno"

        return competencies

    def _analyze_academic_competencies(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Analisa competências acadêmicas."""
        if not metrics.get("total_publications"):
            return {}

        nivel = "iniciante"
        h_index = metrics.get("h_index", 0)
        total_pubs = metrics.get("total_publications", 0)

        if h_index >= 20 and total_pubs >= 30:
            nivel = "autoridade"
        elif h_index >= 10 and total_pubs >= 15:
            nivel = "senior"
        elif h_index >= 5 or total_pubs >= 5:
            nivel = "pesquisador"

        return {
            "nivel_academico": nivel,
            "score_impacto": min(h_index * 5, 100),
        }

    def _consolidate_competencies(self, result: dict) -> dict[str, Any]:
        """Consolida competências de todas as fontes."""
        competencies = {
            "tecnicas": {},
            "academicas": {},
            "areas_atuacao": [],
        }

        # GitHub competencies
        github = result.get("github")
        if github and github.get("competencies"):
            competencies["tecnicas"] = github["competencies"]

        # Scholar competencies
        scholar = result.get("scholar")
        if scholar and scholar.get("competencies"):
            competencies["academicas"] = scholar["competencies"]

        # Collect areas
        if github and github.get("best_match", {}).get("top_languages"):
            for lang, _ in github["best_match"]["top_languages"]:
                competencies["areas_atuacao"].append(f"Programação: {lang}")

        if scholar and scholar.get("found"):
            competencies["areas_atuacao"].append("Pesquisa Acadêmica")

        return competencies

    def _consolidate_risk(self, result: dict) -> dict[str, Any]:
        """Consolida análise de risco de todas as fontes."""
        risk = {
            "nivel_geral": "baixo",
            "fatores": [],
            "alertas": [],
        }

        # News risk
        news = result.get("news")
        if news and news.get("metrics", {}).get("risk_level") in ["medio", "alto"]:
            risk["nivel_geral"] = news["metrics"]["risk_level"]
            risk["fatores"].append("Menções negativas na mídia")
            for alert in news.get("negative_alerts", [])[:3]:
                risk["alertas"].append(
                    {
                        "fonte": "Google News",
                        "titulo": alert.get("title"),
                        "data": alert.get("date"),
                    }
                )

        # Reclame Aqui risk
        reclameaqui = result.get("reclameaqui")
        if reclameaqui and reclameaqui.get("risk_level") in ["medio", "alto"]:
            if risk["nivel_geral"] == "baixo":
                risk["nivel_geral"] = reclameaqui["risk_level"]
            elif reclameaqui["risk_level"] == "alto":
                risk["nivel_geral"] = "alto"
            risk["fatores"].append("Mencionado em reclamações (Reclame Aqui)")

        return risk

    async def _save_enrichment(self, pessoa_id: str, result: dict) -> None:
        """Salva resultado do enriquecimento no banco."""
        try:
            enrichment_data = {
                "github_profile": result.get("github", {}).get("best_match"),
                "scholar_metrics": result.get("scholar", {}).get("metrics"),
                "reputation_metrics": result.get("news", {}).get("metrics"),
                "reclameaqui_risk": result.get("reclameaqui", {}).get("risk_level"),
                "competencies": result.get("competencies"),
                "risk_analysis": result.get("risk_analysis"),
                "enriched_at": result.get("enriched_at"),
                "sources_checked": result.get("sources_checked"),
            }

            # Update dim_pessoas with enrichment data
            self.supabase.table("dim_pessoas").update(
                {
                    "raw_enrichment_extended": enrichment_data,
                }
            ).eq("id", pessoa_id).execute()

            logger.info(
                "person_enrichment_extended_saved",
                pessoa_id=pessoa_id,
                sources=result.get("sources_checked"),
            )

        except Exception as e:
            logger.error(
                "save_enrichment_error",
                pessoa_id=pessoa_id,
                error=str(e),
            )


async def enrich_persons_extended(
    supabase: Client,
    serper_api_key: str | None = None,
    github_token: str | None = None,
    apollo_api_key: str | None = None,
    perplexity_api_key: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Enriquece pessoas com fontes estendidas.

    Args:
        supabase: Cliente Supabase
        serper_api_key: API key do Serper
        github_token: Token do GitHub (opcional)
        apollo_api_key: API key do Apollo
        perplexity_api_key: API key do Perplexity
        limit: Limite de pessoas a processar

    Returns:
        Estatísticas do processamento
    """
    service = ExtendedPersonEnrichmentService(
        supabase=supabase,
        serper_api_key=serper_api_key,
        github_token=github_token,
        apollo_api_key=apollo_api_key,
        perplexity_api_key=perplexity_api_key,
    )

    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "github_found": 0,
        "scholar_found": 0,
        "news_found": 0,
        "reclameaqui_found": 0,
    }

    # Get people without extended enrichment
    result = (
        supabase.table("dim_pessoas")
        .select("id, nome_completo")
        .is_("raw_enrichment_extended", "null")
        .limit(limit)
        .execute()
    )

    for pessoa in result.data:
        stats["processed"] += 1

        try:
            enrichment = await service.enrich_person_full(
                pessoa_id=pessoa["id"],
                nome=pessoa["nome_completo"],
                empresa_nome=None,  # Company enrichment done separately
            )

            stats["success"] += 1

            if enrichment.get("github", {}).get("found"):
                stats["github_found"] += 1
            if enrichment.get("scholar", {}).get("found"):
                stats["scholar_found"] += 1
            if enrichment.get("news", {}).get("found"):
                stats["news_found"] += 1
            if enrichment.get("reclameaqui", {}).get("found"):
                stats["reclameaqui_found"] += 1

        except Exception as e:
            stats["failed"] += 1
            logger.error(
                "enrich_person_extended_error",
                pessoa_id=pessoa["id"],
                error=str(e),
            )

        # Rate limiting
        await asyncio.sleep(2)

    return stats
