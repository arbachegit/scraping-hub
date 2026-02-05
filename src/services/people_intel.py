"""
People Intelligence Service
Inteligência sobre pessoas - funcionários, executivos, candidatos
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from src.scrapers import (
    SerperClient,
    TavilyClient,
    PerplexityClient,
    ApolloClient
)
from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class PeopleIntelService:
    """
    Serviço de inteligência sobre pessoas

    Funcionalidades:
    - Análise de perfil profissional
    - Busca de contatos/executivos
    - Análise de fit cultural
    - Histórico de carreira
    """

    def __init__(self):
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.ai_analyzer = AIAnalyzer()

    async def close(self):
        """Fecha todos os clientes"""
        await asyncio.gather(
            self.serper.close(),
            self.tavily.close(),
            self.perplexity.close(),
            self.apollo.close(),
            self.ai_analyzer.close()
        )

    async def analyze_person(
        self,
        name: str,
        company: Optional[str] = None,
        role: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Análise completa de uma pessoa

        Args:
            name: Nome da pessoa
            company: Empresa atual
            role: Cargo atual
            linkedin_url: URL do LinkedIn
            analysis_type: "full", "quick", "fit"

        Returns:
            Perfil completo da pessoa
        """
        logger.info(
            "people_intel_analyze",
            name=name,
            company=company,
            type=analysis_type
        )

        result = {
            "name": name,
            "company": company,
            "role": role,
            "analysis_type": analysis_type,
            "status": "processing"
        }

        try:
            # 1. Buscar LinkedIn se não fornecido
            if not linkedin_url:
                linkedin_url = await self.serper.find_person_linkedin(name, company)

            result["linkedin_url"] = linkedin_url

            # 2. Coletar dados em paralelo
            tasks = {
                "search_data": self.serper.find_person_info(name, company),
                "research_data": self.perplexity.research_person(name, company),
                "news_data": self.tavily.research_person(name, company)
            }

            # Buscar via Apollo se tiver mais contexto
            if company or linkedin_url:
                tasks["apollo_data"] = self._get_apollo_data(name, company, linkedin_url)

            # Executar em paralelo
            results = await asyncio.gather(
                *tasks.values(),
                return_exceptions=True
            )

            # Mapear resultados
            task_keys = list(tasks.keys())
            for i, key in enumerate(task_keys):
                if isinstance(results[i], Exception):
                    logger.warning(f"people_intel_{key}_error", error=str(results[i]))
                    result[key] = {}
                else:
                    result[key] = results[i]

            # 3. Consolidar perfil
            profile = self._consolidate_person_data(result, name, company, role)
            result["profile"] = profile

            # 4. Análise AI
            if analysis_type != "quick":
                ai_analysis = await self.ai_analyzer.analyze_person_profile(
                    profile,
                    context=f"Contexto: {company}, {role}" if company else None
                )
                result["ai_analysis"] = ai_analysis

            result["status"] = "completed"

        except Exception as e:
            logger.error("people_intel_error", name=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _get_apollo_data(
        self,
        name: str,
        company: Optional[str],
        linkedin_url: Optional[str]
    ) -> Dict[str, Any]:
        """Busca dados via Apollo"""
        try:
            # Tentar enriquecer primeiro
            if linkedin_url:
                return await self.apollo.enrich_person(linkedin_url=linkedin_url)

            # Senão, buscar
            name_parts = name.split()
            first_name = name_parts[0] if name_parts else None
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

            result = await self.apollo.search_people(
                q_person_name=name,
                q_organization_name=company,
                per_page=5
            )

            people = result.get("people", [])
            if people:
                return people[0]

            return {}

        except Exception as e:
            logger.warning("apollo_error", error=str(e))
            return {}

    def _consolidate_person_data(
        self,
        result: Dict,
        name: str,
        company: Optional[str],
        role: Optional[str]
    ) -> Dict[str, Any]:
        """Consolida dados de múltiplas fontes"""
        search_data = result.get("search_data", {})
        research_data = result.get("research_data", {})
        apollo_data = result.get("apollo_data", {})

        profile = {
            # Identificação
            "name": name,
            "full_name": apollo_data.get("name") or name,

            # Profissional
            "current_title": (
                apollo_data.get("title") or
                role
            ),
            "current_company": (
                apollo_data.get("company", {}).get("name") or
                company
            ),
            "seniority": apollo_data.get("seniority"),
            "departments": apollo_data.get("departments", []),

            # Contato
            "email": apollo_data.get("email"),
            "phone": (apollo_data.get("phone_numbers") or [{}])[0] if apollo_data.get("phone_numbers") else None,

            # Social
            "linkedin_url": result.get("linkedin_url") or apollo_data.get("linkedin_url"),
            "twitter_url": apollo_data.get("twitter_url"),

            # Localização
            "city": apollo_data.get("city"),
            "state": apollo_data.get("state"),
            "country": apollo_data.get("country") or "Brasil",

            # Foto
            "photo_url": apollo_data.get("photo_url"),
            "headline": apollo_data.get("headline"),

            # Pesquisa
            "profile_summary": research_data.get("profile"),
            "news_mentions": result.get("news_data", {}).get("sources", []),

            # Knowledge graph do Google
            "knowledge_graph": search_data.get("knowledge_graph"),

            # Fontes
            "sources": self._list_person_sources(result)
        }

        return profile

    def _list_person_sources(self, result: Dict) -> List[str]:
        """Lista fontes usadas"""
        sources = []
        if result.get("apollo_data"):
            sources.append("Apollo.io")
        if result.get("search_data"):
            sources.append("Google Search (Serper)")
        if result.get("research_data"):
            sources.append("Perplexity AI")
        if result.get("news_data"):
            sources.append("Tavily Search")
        return sources

    async def analyze_fit(
        self,
        person_name: str,
        company_name: str,
        role: Optional[str] = None,
        person_data: Optional[Dict] = None,
        company_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analisa fit cultural entre pessoa e empresa

        Args:
            person_name: Nome da pessoa
            company_name: Nome da empresa
            role: Cargo em questão
            person_data: Dados da pessoa (opcional)
            company_data: Dados da empresa (opcional)

        Returns:
            Análise de fit
        """
        logger.info(
            "people_intel_fit",
            person=person_name,
            company=company_name,
            role=role
        )

        # Buscar dados se não fornecidos
        if not person_data:
            person_result = await self.analyze_person(
                person_name,
                company=None,
                role=role,
                analysis_type="quick"
            )
            person_data = person_result.get("profile", {})

        if not company_data:
            from .company_intel import CompanyIntelService
            company_service = CompanyIntelService()
            try:
                company_result = await company_service.quick_lookup(company_name)
                company_data = company_result
            finally:
                await company_service.close()

        # Pesquisar fit via Perplexity
        fit_research = await self.perplexity.analyze_fit(
            person_name,
            company_name,
            role
        )

        # Análise AI detalhada
        ai_fit = await self.ai_analyzer.analyze_cultural_fit(
            person_data,
            company_data,
            role
        )

        return {
            "person": {
                "name": person_name,
                "profile": person_data
            },
            "company": {
                "name": company_name,
                "profile": company_data
            },
            "role": role,
            "fit_research": fit_research.get("fit_analysis"),
            "ai_analysis": ai_fit,
            "scores": {
                "cultural_fit": ai_fit.get("cultural_fit_score"),
                "role_fit": ai_fit.get("role_fit_score"),
                "overall_fit": ai_fit.get("overall_fit_score")
            },
            "recommendation": ai_fit.get("recommendation")
        }

    async def search_employees(
        self,
        company_name: str,
        filters: Optional[Dict] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Busca funcionários de uma empresa

        Args:
            company_name: Nome da empresa
            filters: Filtros (seniority, title, department)
            limit: Limite de resultados

        Returns:
            Lista de funcionários
        """
        logger.info("people_intel_employees", company=company_name)

        filters = filters or {}

        try:
            result = await self.apollo.get_company_employees(
                organization_name=company_name,
                person_seniorities=filters.get("seniority"),
                person_titles=filters.get("titles"),
                per_page=min(limit, 100)
            )

            return {
                "company": company_name,
                "employees": result.get("employees", []),
                "total": result.get("total", 0),
                "filters_applied": filters
            }

        except Exception as e:
            logger.warning("apollo_employees_error", error=str(e))

            # Fallback: buscar via Google
            employees = []
            search_queries = [
                f'"{company_name}" "LinkedIn" site:linkedin.com/in CEO OR CFO OR Director',
                f'"{company_name}" executivos liderança'
            ]

            for query in search_queries:
                try:
                    search = await self.serper.search(query, num=10)
                    for item in search.get("organic", []):
                        if "linkedin.com/in/" in item.get("link", ""):
                            employees.append({
                                "name": item.get("title", "").split(" - ")[0],
                                "linkedin_url": item.get("link"),
                                "context": item.get("snippet")
                            })
                except Exception:
                    pass

            return {
                "company": company_name,
                "employees": employees[:limit],
                "total": len(employees),
                "source": "google_search",
                "note": "Dados limitados - Apollo não disponível"
            }

    async def search_decision_makers(
        self,
        company_name: str,
        departments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Busca tomadores de decisão

        Args:
            company_name: Nome da empresa
            departments: Departamentos específicos

        Returns:
            Lista de decision makers
        """
        logger.info("people_intel_decision_makers", company=company_name)

        try:
            result = await self.apollo.get_decision_makers(
                organization_name=company_name
            )

            decision_makers = result.get("employees", [])

            # Filtrar por departamento se especificado
            if departments:
                decision_makers = [
                    dm for dm in decision_makers
                    if any(
                        dept.lower() in (dm.get("departments") or [])
                        for dept in departments
                    )
                ]

            return {
                "company": company_name,
                "decision_makers": decision_makers,
                "total": len(decision_makers),
                "departments_filter": departments
            }

        except Exception as e:
            logger.warning("apollo_dm_error", error=str(e))
            return {
                "company": company_name,
                "decision_makers": [],
                "error": str(e)
            }

    async def compare_candidates(
        self,
        candidates: List[str],
        company_name: str,
        role: str
    ) -> Dict[str, Any]:
        """
        Compara candidatos para uma vaga

        Args:
            candidates: Lista de nomes de candidatos
            company_name: Empresa
            role: Cargo

        Returns:
            Comparação de candidatos
        """
        logger.info(
            "people_intel_compare",
            candidates=candidates,
            company=company_name,
            role=role
        )

        # Analisar cada candidato
        analyses = []
        for candidate in candidates:
            analysis = await self.analyze_fit(
                candidate,
                company_name,
                role
            )
            analyses.append({
                "name": candidate,
                "analysis": analysis
            })

        # Ordenar por fit score
        analyses.sort(
            key=lambda x: x.get("analysis", {}).get("scores", {}).get("overall_fit", 0),
            reverse=True
        )

        # Gerar comparação
        comparison = {
            "company": company_name,
            "role": role,
            "candidates": analyses,
            "ranking": [
                {
                    "rank": i + 1,
                    "name": a.get("name"),
                    "overall_fit": a.get("analysis", {}).get("scores", {}).get("overall_fit"),
                    "recommendation": a.get("analysis", {}).get("recommendation")
                }
                for i, a in enumerate(analyses)
            ]
        }

        return comparison

    async def quick_lookup(self, name: str, company: Optional[str] = None) -> Dict[str, Any]:
        """
        Busca rápida de pessoa

        Args:
            name: Nome da pessoa
            company: Empresa (opcional)

        Returns:
            Dados básicos
        """
        logger.info("people_intel_quick", name=name)

        # Buscar LinkedIn
        linkedin = await self.serper.find_person_linkedin(name, company)

        # Buscar via Apollo
        apollo_data = await self._get_apollo_data(name, company, linkedin)

        return {
            "name": name,
            "company": company or apollo_data.get("company", {}).get("name"),
            "title": apollo_data.get("title"),
            "linkedin_url": linkedin or apollo_data.get("linkedin_url"),
            "email": apollo_data.get("email"),
            "photo_url": apollo_data.get("photo_url"),
            "location": f"{apollo_data.get('city', '')}, {apollo_data.get('state', '')}"
        }

    async def get_career_history(self, name: str, linkedin_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Busca histórico de carreira

        Args:
            name: Nome da pessoa
            linkedin_url: URL do LinkedIn

        Returns:
            Histórico de carreira
        """
        logger.info("people_intel_career", name=name)

        # Pesquisar carreira
        research = await self.perplexity.research_person(
            name,
            focus="professional"
        )

        # Buscar notícias sobre mudanças de emprego
        news = await self.serper.search_news(
            f'"{name}" novo cargo OR nova posição OR contratação',
            num=10
        )

        return {
            "name": name,
            "career_summary": research.get("profile"),
            "career_news": news.get("news", []),
            "sources": research.get("citations", [])
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
