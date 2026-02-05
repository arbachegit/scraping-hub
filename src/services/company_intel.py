"""
Company Intelligence Service
Inteligência completa sobre empresas brasileiras
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.scrapers import (
    BrasilAPIClient,
    SerperClient,
    TavilyClient,
    PerplexityClient,
    ApolloClient,
    WebScraperClient
)
from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class CompanyIntelService:
    """
    Serviço de inteligência empresarial

    Fluxo:
    1. Buscar CNPJ (se não fornecido)
    2. Coletar dados cadastrais (BrasilAPI)
    3. Enriquecer com buscas (Serper, Tavily)
    4. Pesquisar contexto (Perplexity)
    5. Scrape do website
    6. Analisar com AI (Claude)
    """

    def __init__(self):
        self.brasil_api = BrasilAPIClient()
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.web_scraper = WebScraperClient()
        self.ai_analyzer = AIAnalyzer()

    async def close(self):
        """Fecha todos os clientes"""
        await asyncio.gather(
            self.brasil_api.close(),
            self.serper.close(),
            self.tavily.close(),
            self.perplexity.close(),
            self.apollo.close(),
            self.web_scraper.close(),
            self.ai_analyzer.close()
        )

    async def analyze_company(
        self,
        name: str,
        cnpj: Optional[str] = None,
        analysis_type: str = "client",
        include_competitors: bool = True,
        include_employees: bool = True
    ) -> Dict[str, Any]:
        """
        Análise completa de uma empresa

        Args:
            name: Nome da empresa
            cnpj: CNPJ (opcional, será buscado se não fornecido)
            analysis_type: "client", "competitor", "prospect"
            include_competitors: Incluir análise de concorrentes
            include_employees: Incluir funcionários principais

        Returns:
            Relatório completo da empresa
        """
        logger.info("company_intel_analyze", company=name, type=analysis_type)

        result = {
            "company_name": name,
            "analysis_type": analysis_type,
            "status": "processing"
        }

        try:
            # 1. Buscar CNPJ se não fornecido
            if not cnpj:
                logger.info("company_intel_finding_cnpj", company=name)
                cnpj = await self.serper.find_company_cnpj(name)

            # 2. Coletar dados em paralelo
            tasks = {
                "cnpj_data": self._get_cnpj_data(cnpj) if cnpj else asyncio.sleep(0),
                "search_data": self.serper.find_company_info(name),
                "research_data": self.perplexity.analyze_company(name, analysis_type="full"),
                "news_data": self.tavily.get_company_news(name, days=30)
            }

            # Executar tarefas em paralelo
            results = await asyncio.gather(
                *tasks.values(),
                return_exceptions=True
            )

            # Mapear resultados
            task_keys = list(tasks.keys())
            for i, key in enumerate(task_keys):
                if isinstance(results[i], Exception):
                    logger.warning(f"company_intel_{key}_error", error=str(results[i]))
                    result[key] = {}
                else:
                    result[key] = results[i]

            # 3. Scrape do website
            website_url = (
                result.get("cnpj_data", {}).get("website") or
                result.get("search_data", {}).get("website")
            )
            if website_url:
                try:
                    result["website_data"] = await self.web_scraper.scrape_company_website(website_url)
                except Exception as e:
                    logger.warning("company_intel_website_error", error=str(e))
                    result["website_data"] = {}

            # 4. Consolidar dados da empresa
            company_profile = self._consolidate_company_data(result, name, cnpj)
            result["company_profile"] = company_profile

            # 5. Análise AI
            logger.info("company_intel_ai_analysis", company=name)

            # Gerar SWOT
            swot = await self.ai_analyzer.analyze_company_swot(
                company_profile,
                market_context=result.get("research_data", {}).get("analysis")
            )
            result["swot_analysis"] = swot

            # Gerar OKRs
            okrs = await self.ai_analyzer.generate_okrs(
                company_profile,
                swot=swot
            )
            result["suggested_okrs"] = okrs

            # 6. Buscar concorrentes
            if include_competitors:
                result["competitors"] = await self._analyze_competitors(name, company_profile)

            # 7. Buscar funcionários principais
            if include_employees:
                result["key_people"] = await self._get_key_people(name, company_profile)

            result["status"] = "completed"
            result["confidence_score"] = self._calculate_confidence(result)

        except Exception as e:
            logger.error("company_intel_error", company=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _get_cnpj_data(self, cnpj: str) -> Dict[str, Any]:
        """Busca dados do CNPJ"""
        try:
            return await self.brasil_api.get_cnpj(cnpj)
        except Exception as e:
            logger.warning("brasil_api_error", error=str(e))
            return {}

    def _consolidate_company_data(
        self,
        result: Dict,
        name: str,
        cnpj: Optional[str]
    ) -> Dict[str, Any]:
        """Consolida dados de múltiplas fontes"""
        cnpj_data = result.get("cnpj_data", {})
        search_data = result.get("search_data", {})
        website_data = result.get("website_data", {})
        research_data = result.get("research_data", {})

        profile = {
            # Identificação
            "name": name,
            "nome_fantasia": cnpj_data.get("nome_fantasia") or name,
            "razao_social": cnpj_data.get("razao_social"),
            "cnpj": cnpj or cnpj_data.get("cnpj"),

            # Contato e localização
            "website": (
                website_data.get("url") or
                search_data.get("website") or
                cnpj_data.get("website")
            ),
            "endereco": cnpj_data.get("endereco", {}),
            "telefone": cnpj_data.get("telefone"),
            "email": cnpj_data.get("email"),

            # Negócio
            "industry": (
                search_data.get("industry") or
                cnpj_data.get("cnae_principal", {}).get("descricao")
            ),
            "description": (
                search_data.get("description") or
                website_data.get("description") or
                cnpj_data.get("cnae_principal", {}).get("descricao")
            ),
            "porte": cnpj_data.get("porte"),
            "capital_social": cnpj_data.get("capital_social"),
            "data_abertura": cnpj_data.get("data_abertura"),
            "situacao_cadastral": cnpj_data.get("situacao_cadastral"),

            # Social
            "linkedin_url": search_data.get("linkedin") or website_data.get("social_media", {}).get("linkedin"),
            "social_media": website_data.get("social_media", {}),

            # Sócios
            "socios": cnpj_data.get("socios", []),

            # Dados extras
            "knowledge_graph": search_data.get("knowledge_graph"),
            "research_summary": research_data.get("analysis"),

            # Fontes
            "sources": self._list_sources(result)
        }

        return profile

    def _list_sources(self, result: Dict) -> List[str]:
        """Lista fontes usadas"""
        sources = []
        if result.get("cnpj_data"):
            sources.append("BrasilAPI (CNPJ)")
        if result.get("search_data"):
            sources.append("Google Search (Serper)")
        if result.get("research_data"):
            sources.append("Perplexity AI")
        if result.get("news_data"):
            sources.append("Tavily News")
        if result.get("website_data"):
            sources.append("Website Scraping")
        return sources

    async def _analyze_competitors(
        self,
        company_name: str,
        company_profile: Dict
    ) -> Dict[str, Any]:
        """Analisa concorrentes"""
        logger.info("company_intel_competitors", company=company_name)

        # Buscar concorrentes via Perplexity
        competitors_search = await self.perplexity.find_competitors(
            company_name,
            industry=company_profile.get("industry")
        )

        competitors_data = []

        # Buscar dados básicos de cada concorrente (limite de 3)
        competitor_names = self._extract_competitor_names(
            competitors_search.get("competitors_analysis", "")
        )[:3]

        for comp_name in competitor_names:
            try:
                comp_info = await self.serper.find_company_info(comp_name)
                competitors_data.append({
                    "name": comp_name,
                    "website": comp_info.get("website"),
                    "description": comp_info.get("description"),
                    "industry": comp_info.get("industry")
                })
            except Exception as e:
                logger.warning("competitor_info_error", competitor=comp_name, error=str(e))

        # Análise competitiva com AI
        if competitors_data:
            competitive_analysis = await self.ai_analyzer.analyze_competitors(
                company_profile,
                competitors_data
            )
        else:
            competitive_analysis = {"note": "Não foi possível identificar concorrentes"}

        return {
            "search_analysis": competitors_search,
            "competitors": competitors_data,
            "competitive_analysis": competitive_analysis
        }

    def _extract_competitor_names(self, text: str) -> List[str]:
        """Extrai nomes de concorrentes do texto"""
        # Implementação simples - pode ser melhorada
        import re

        # Padrões comuns para listar empresas
        patterns = [
            r"(?:concorrentes?|competidores?):?\s*([^.]+)",
            r"(?:principais|maiores)\s+(?:concorrentes?|competidores?):\s*([^.]+)",
            r"\d+\.\s*([A-Z][^:,\n]+?)(?:\s*[-–:]|\s*\d|\n|$)"
        ]

        names = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Limpar e dividir por vírgulas
                parts = re.split(r'[,;]|(?:\s+e\s+)', match)
                for part in parts:
                    cleaned = part.strip().strip('.')
                    if cleaned and len(cleaned) > 2 and len(cleaned) < 100:
                        names.append(cleaned)

        return list(dict.fromkeys(names))  # Remove duplicatas mantendo ordem

    async def _get_key_people(
        self,
        company_name: str,
        company_profile: Dict
    ) -> Dict[str, Any]:
        """Busca pessoas-chave da empresa"""
        logger.info("company_intel_people", company=company_name)

        people = {
            "executives": [],
            "decision_makers": [],
            "socios": company_profile.get("socios", [])
        }

        # Buscar via Apollo se disponível
        try:
            executives = await self.apollo.get_executives(
                organization_name=company_name,
                domain=self._extract_domain(company_profile.get("website", ""))
            )
            people["executives"] = executives.get("employees", [])[:10]

            # Decision makers
            dm = await self.apollo.get_decision_makers(
                organization_name=company_name
            )
            people["decision_makers"] = dm.get("employees", [])[:10]

        except Exception as e:
            logger.warning("apollo_people_error", error=str(e))
            # Fallback: buscar via Serper
            try:
                for title in ["CEO", "CFO", "Diretor"]:
                    person_search = await self.serper.search(
                        f'"{company_name}" {title} LinkedIn',
                        num=3
                    )
                    for result in person_search.get("organic", []):
                        if "linkedin.com/in/" in result.get("link", ""):
                            people["executives"].append({
                                "name": result.get("title", "").split(" - ")[0],
                                "linkedin_url": result.get("link"),
                                "title": title
                            })
            except Exception:
                pass

        return people

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extrai domínio de uma URL"""
        if not url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc or url

    def _calculate_confidence(self, result: Dict) -> float:
        """Calcula score de confiança da análise"""
        score = 0.0
        weights = {
            "cnpj_data": 0.25,
            "search_data": 0.15,
            "research_data": 0.15,
            "website_data": 0.15,
            "news_data": 0.10,
            "swot_analysis": 0.10,
            "competitors": 0.10
        }

        for key, weight in weights.items():
            data = result.get(key, {})
            if data and not isinstance(data, Exception):
                if isinstance(data, dict):
                    if data.get("error"):
                        continue
                    score += weight
                elif data:
                    score += weight

        return round(min(score, 1.0), 2)

    # ===========================================
    # MÉTODOS SIMPLIFICADOS
    # ===========================================

    async def quick_lookup(self, name: str) -> Dict[str, Any]:
        """
        Busca rápida de empresa (apenas dados básicos)

        Args:
            name: Nome da empresa

        Returns:
            Dados básicos
        """
        logger.info("company_intel_quick_lookup", company=name)

        # Buscar CNPJ
        cnpj = await self.serper.find_company_cnpj(name)

        # Buscar dados em paralelo
        tasks = [
            self._get_cnpj_data(cnpj) if cnpj else asyncio.sleep(0),
            self.serper.find_company_info(name)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        cnpj_data = results[0] if not isinstance(results[0], Exception) else {}
        search_data = results[1] if not isinstance(results[1], Exception) else {}

        return {
            "name": name,
            "cnpj": cnpj,
            "razao_social": cnpj_data.get("razao_social") if isinstance(cnpj_data, dict) else None,
            "nome_fantasia": cnpj_data.get("nome_fantasia") if isinstance(cnpj_data, dict) else name,
            "website": search_data.get("website") if isinstance(search_data, dict) else None,
            "industry": search_data.get("industry") if isinstance(search_data, dict) else None,
            "description": search_data.get("description") if isinstance(search_data, dict) else None,
            "endereco": cnpj_data.get("endereco") if isinstance(cnpj_data, dict) else None,
            "situacao_cadastral": cnpj_data.get("situacao_cadastral") if isinstance(cnpj_data, dict) else None
        }

    async def get_swot(self, name: str) -> Dict[str, Any]:
        """
        Gera apenas SWOT para uma empresa

        Args:
            name: Nome da empresa

        Returns:
            Análise SWOT
        """
        # Buscar dados básicos
        company_data = await self.quick_lookup(name)

        # Adicionar contexto de mercado
        research = await self.perplexity.analyze_company(name, analysis_type="swot")
        company_data["market_context"] = research.get("analysis")

        # Gerar SWOT
        return await self.ai_analyzer.analyze_company_swot(company_data)

    async def get_okrs(
        self,
        name: str,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Gera OKRs sugeridos para uma empresa

        Args:
            name: Nome da empresa
            focus_areas: Áreas de foco

        Returns:
            OKRs sugeridos
        """
        # Buscar dados e SWOT
        company_data = await self.quick_lookup(name)
        swot = await self.get_swot(name)

        # Gerar OKRs
        return await self.ai_analyzer.generate_okrs(
            company_data,
            swot=swot,
            focus_areas=focus_areas
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
