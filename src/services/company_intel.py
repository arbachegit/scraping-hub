"""
Company Intelligence Service
Inteligência completa sobre empresas brasileiras
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from src.scrapers import (
    ApolloClient,
    BrasilAPIClient,
    PerplexityClient,
    SerperClient,
    TavilyClient,
    WebScraperClient,
)

from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class CompanyIntelService:
    """
    Serviço de inteligência empresarial

    Fluxo:
    1. Verificar cache/banco de dados
    2. Coletar dados de TODAS as fontes em paralelo
    3. Consolidar e enriquecer
    4. Fazer scraping do website
    5. Analisar com AI (Claude)
    6. Buscar concorrentes (OBRIGATÓRIO)
    7. Salvar no banco
    """

    # Cache em memória (persiste durante a sessão)
    _cache: Dict[str, Dict] = {}

    def __init__(self):
        self.brasil_api = BrasilAPIClient()
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.web_scraper = WebScraperClient()
        self.ai_analyzer = AIAnalyzer()

        # Repository para persistência
        try:
            from src.database import CompanyRepository
            self.repository = CompanyRepository()
        except Exception:
            self.repository = None

    def _cache_key(self, name: str) -> str:
        """Gera chave de cache normalizada"""
        return name.lower().strip()

    def _get_from_cache(self, name: str) -> Optional[Dict]:
        """Busca dados do cache"""
        key = self._cache_key(name)
        return CompanyIntelService._cache.get(key)

    def _save_to_cache(self, name: str, data: Dict):
        """Salva dados no cache"""
        key = self._cache_key(name)
        CompanyIntelService._cache[key] = data

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

        FLUXO:
        1. Verificar cache/DB
        2. Coletar TODAS as fontes em paralelo
        3. Fazer scraping do site
        4. Consolidar dados
        5. Gerar SWOT com dados completos
        6. Buscar concorrentes (SEMPRE)
        7. Salvar no DB
        """
        logger.info("company_intel_analyze", company=name, type=analysis_type)

        result = {
            "company_name": name,
            "analysis_type": analysis_type,
            "status": "processing"
        }

        try:
            # 1. Verificar se já temos dados recentes no cache
            cached = self._get_from_cache(name)
            if cached and cached.get("full_analysis"):
                logger.info("company_intel_cache_hit", company=name)
                return cached["full_analysis"]

            # 2. COLETAR TUDO EM PARALELO
            logger.info("company_intel_collecting_all_data", company=name)

            # Primeira rodada: buscar CNPJ e website
            initial_tasks = {
                "cnpj_search": self.serper.find_company_cnpj(name),
                "company_search": self.serper.find_company_info(name),
            }

            initial_results = await asyncio.gather(
                *initial_tasks.values(),
                return_exceptions=True
            )

            # Extrair CNPJ e website
            if not cnpj and not isinstance(initial_results[0], Exception):
                cnpj = initial_results[0]

            search_data = initial_results[1] if not isinstance(initial_results[1], Exception) else {}
            website_url = search_data.get("website")

            # 3. Segunda rodada: coletar dados detalhados
            detail_tasks = {
                "perplexity_full": self.perplexity.analyze_company(name, analysis_type="full"),
                "perplexity_competitors": self.perplexity.find_competitors(name, search_data.get("industry")),
                "tavily_news": self.tavily.get_company_news(name, days=30),
                "tavily_research": self.tavily.research(f"empresa {name} Brasil produtos serviços"),
            }

            # Adicionar CNPJ se disponível
            if cnpj:
                detail_tasks["cnpj_data"] = self._get_cnpj_data(cnpj)

            detail_results = await asyncio.gather(
                *detail_tasks.values(),
                return_exceptions=True
            )

            # Mapear resultados
            task_keys = list(detail_tasks.keys())
            for i, key in enumerate(task_keys):
                if isinstance(detail_results[i], Exception):
                    logger.warning(f"company_intel_{key}_error", error=str(detail_results[i]))
                    result[key] = {}
                else:
                    result[key] = detail_results[i]

            result["search_data"] = search_data
            result["cnpj"] = cnpj

            # 4. SCRAPING DO WEBSITE - ESSENCIAL
            website_data = await self._scrape_website_fully(name, website_url, search_data)
            result["website_data"] = website_data

            # 5. CONSOLIDAR TODOS OS DADOS
            company_profile = self._consolidate_all_data(result, name, cnpj)
            result["company_profile"] = company_profile

            # 6. ANÁLISE AI COM TODOS OS DADOS
            logger.info("company_intel_ai_analysis", company=name)

            # Preparar contexto rico para AI
            ai_context = self._prepare_ai_context(result)

            # Gerar SWOT com contexto completo
            swot = await self.ai_analyzer.analyze_company_swot(
                company_profile,
                market_context=ai_context
            )
            result["swot_analysis"] = swot

            # Gerar OKRs
            okrs = await self.ai_analyzer.generate_okrs(
                company_profile,
                swot=swot
            )
            result["suggested_okrs"] = okrs

            # 7. CONCORRENTES - SEMPRE BUSCAR
            logger.info("company_intel_competitors", company=name)
            result["competitors"] = await self._analyze_competitors_full(
                name,
                company_profile,
                result.get("perplexity_competitors", {})
            )

            # 8. Funcionários se solicitado
            if include_employees:
                result["key_people"] = await self._get_key_people(name, company_profile)

            result["status"] = "completed"
            result["confidence_score"] = self._calculate_confidence(result)
            result["sources_used"] = self._list_all_sources(result)

            # 9. Salvar no cache e DB
            cache_data = self._get_from_cache(name) or {}
            cache_data["full_analysis"] = result
            self._save_to_cache(name, cache_data)

            if self.repository:
                try:
                    company_id = await self.repository.save_company(company_profile)
                    if company_id:
                        await self.repository.save_analysis(company_id, analysis_type, result)
                except Exception as e:
                    logger.warning("db_save_error", error=str(e))

        except Exception as e:
            logger.error("company_intel_error", company=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _scrape_website_fully(
        self,
        name: str,
        website_url: Optional[str],
        search_data: Dict
    ) -> Dict[str, Any]:
        """Faz scraping completo do website"""

        # Se não temos URL, buscar agressivamente
        if not website_url:
            logger.info("company_intel_searching_website", company=name)
            try:
                website_search = await self.serper.search(f'"{name}" site oficial Brasil', num=5)
                for item in website_search.get("organic", []):
                    link = item.get("link", "")
                    if link and not any(x in link for x in [
                        "linkedin", "facebook", "instagram", "twitter",
                        "youtube", "google", "wikipedia", "reclameaqui"
                    ]):
                        website_url = link
                        break
            except Exception as e:
                logger.warning("website_search_error", error=str(e))

        if not website_url:
            logger.warning("company_intel_no_website", company=name)
            return {}

        logger.info("company_intel_scraping_website", url=website_url)

        try:
            # Scrape da página principal
            main_scrape = await self.web_scraper.scrape_company_website(website_url)

            # Scrape de páginas importantes
            important_pages = main_scrape.get("important_pages", {})
            all_content = [main_scrape.get("content_summary", "")]

            for page_type, page_url in important_pages.items():
                if page_url and page_type in ["about", "services", "products", "team"]:
                    try:
                        page_data = await self.web_scraper.scrape(page_url)
                        page_text = page_data.get("content", {}).get("text", "")[:5000]
                        if page_text:
                            all_content.append(f"\n\n=== {page_type.upper()} ===\n{page_text}")
                    except Exception:
                        pass

            main_scrape["full_content"] = "\n".join(all_content)
            return main_scrape

        except Exception as e:
            logger.warning("company_intel_website_error", url=website_url, error=str(e))
            return {}

    def _consolidate_all_data(
        self,
        result: Dict,
        name: str,
        cnpj: Optional[str]
    ) -> Dict[str, Any]:
        """
        Consolida TODOS os dados coletados
        Prioridade: Website > Perplexity > Serper > CNPJ
        """
        cnpj_data = result.get("cnpj_data", {}) or {}
        search_data = result.get("search_data", {}) or {}
        website_data = result.get("website_data", {}) or {}
        perplexity_full = result.get("perplexity_full", {}) or {}
        tavily_research = result.get("tavily_research", {}) or {}

        # Extrair conteúdo do site
        website_content = website_data.get("full_content") or website_data.get("content_summary", "")
        website_headings = website_data.get("headings", [])
        website_contact = website_data.get("contact_info", {}) or {}

        # Descrição combinada (Perplexity > Website > Serper)
        description = (
            perplexity_full.get("analysis") or
            tavily_research.get("answer") or
            website_data.get("description") or
            search_data.get("description") or
            cnpj_data.get("cnae_principal", {}).get("descricao", "")
        )

        profile = {
            # Identificação
            "name": name,
            "nome_fantasia": cnpj_data.get("nome_fantasia") or website_data.get("company_name") or name,
            "razao_social": cnpj_data.get("razao_social"),
            "cnpj": cnpj or cnpj_data.get("cnpj") or website_contact.get("cnpj"),

            # Contato (prioriza website)
            "website": website_data.get("url") or search_data.get("website") or cnpj_data.get("website"),
            "endereco": cnpj_data.get("endereco", {}),
            "telefone": (website_contact.get("phones") or [None])[0] or cnpj_data.get("telefone"),
            "email": (website_contact.get("emails") or [None])[0] or cnpj_data.get("email"),

            # Negócio - CONTEÚDO RICO
            "industry": search_data.get("industry") or cnpj_data.get("cnae_principal", {}).get("descricao"),
            "description": description,

            # CONTEÚDO DO SITE - ESSENCIAL PARA ANÁLISE
            "website_content": website_content[:15000],  # Aumentado para mais contexto
            "website_headings": website_headings,
            "website_pages": website_data.get("important_pages", {}),

            # Dados adicionais
            "porte": cnpj_data.get("porte"),
            "capital_social": cnpj_data.get("capital_social"),
            "data_abertura": cnpj_data.get("data_abertura"),
            "situacao_cadastral": cnpj_data.get("situacao_cadastral"),

            # Social
            "linkedin_url": (
                website_data.get("social_media", {}).get("linkedin") or
                search_data.get("linkedin")
            ),
            "social_media": website_data.get("social_media", {}),

            # Sócios
            "socios": cnpj_data.get("socios", []),

            # Pesquisa AI
            "perplexity_analysis": perplexity_full.get("analysis"),
            "tavily_insights": tavily_research.get("answer"),
            "knowledge_graph": search_data.get("knowledge_graph"),

            # Tecnologias
            "technologies": website_data.get("technologies", []),

            # Notícias
            "recent_news": result.get("tavily_news", {}).get("results", [])[:5],

            # Fontes
            "sources": self._list_all_sources(result)
        }

        return profile

    def _prepare_ai_context(self, result: Dict) -> str:
        """Prepara contexto rico para análise AI"""
        parts = []

        # Perplexity analysis
        perplexity = result.get("perplexity_full", {})
        if perplexity.get("analysis"):
            parts.append(f"ANÁLISE PERPLEXITY:\n{perplexity['analysis']}")

        # Tavily research
        tavily = result.get("tavily_research", {})
        if tavily.get("answer"):
            parts.append(f"\nPESQUISA TAVILY:\n{tavily['answer']}")

        # Competitors preview
        competitors = result.get("perplexity_competitors", {})
        if competitors.get("competitors_analysis"):
            parts.append(f"\nCONCORRENTES IDENTIFICADOS:\n{competitors['competitors_analysis']}")

        # News summary
        news = result.get("tavily_news", {})
        if news.get("results"):
            news_titles = [n.get("title", "") for n in news["results"][:5]]
            parts.append("\nNOTÍCIAS RECENTES:\n" + "\n".join(f"- {t}" for t in news_titles))

        return "\n\n".join(parts)

    async def _analyze_competitors_full(
        self,
        company_name: str,
        company_profile: Dict,
        perplexity_competitors: Dict
    ) -> Dict[str, Any]:
        """Análise completa de concorrentes"""
        logger.info("company_intel_analyzing_competitors", company=company_name)

        competitors_data = []

        # Extrair nomes dos concorrentes
        competitor_names = self._extract_competitor_names(
            perplexity_competitors.get("competitors_analysis", "")
        )[:5]

        # Buscar dados de cada concorrente
        for comp_name in competitor_names:
            try:
                comp_info = await self.serper.find_company_info(comp_name)
                competitors_data.append({
                    "name": comp_name,
                    "website": comp_info.get("website"),
                    "description": comp_info.get("description"),
                    "industry": comp_info.get("industry"),
                    "linkedin": comp_info.get("linkedin")
                })
            except Exception as e:
                logger.warning("competitor_info_error", competitor=comp_name, error=str(e))

        # Análise comparativa AI
        competitive_analysis = {}
        if competitors_data:
            try:
                competitive_analysis = await self.ai_analyzer.analyze_competitors(
                    company_profile,
                    competitors_data
                )
            except Exception as e:
                logger.warning("competitor_analysis_error", error=str(e))

        return {
            "perplexity_analysis": perplexity_competitors.get("competitors_analysis"),
            "competitors_found": competitors_data,
            "competitive_analysis": competitive_analysis,
            "total_competitors": len(competitors_data)
        }

    def _extract_competitor_names(self, text: str) -> List[str]:
        """Extrai nomes de concorrentes do texto"""
        import re

        patterns = [
            r"(?:concorrentes?|competidores?):?\s*([^.]+)",
            r"(?:principais|maiores)\s+(?:concorrentes?|competidores?):\s*([^.]+)",
            r"\d+\.\s*\*?\*?([A-Z][^:,\n*]+?)\*?\*?(?:\s*[-–:]|\s*\d|\n|$)"
        ]

        names = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                parts = re.split(r'[,;]|(?:\s+e\s+)', match)
                for part in parts:
                    cleaned = part.strip().strip('.').strip('*')
                    if cleaned and 3 < len(cleaned) < 80:
                        names.append(cleaned)

        return list(dict.fromkeys(names))

    async def _get_key_people(
        self,
        company_name: str,
        company_profile: Dict
    ) -> Dict[str, Any]:
        """Busca pessoas-chave"""
        logger.info("company_intel_people", company=company_name)

        people = {
            "executives": [],
            "decision_makers": [],
            "socios": company_profile.get("socios", [])
        }

        try:
            domain = self._extract_domain(company_profile.get("website", ""))

            executives = await self.apollo.get_executives(
                organization_name=company_name,
                domain=domain
            )
            people["executives"] = executives.get("employees", [])[:10]

            dm = await self.apollo.get_decision_makers(organization_name=company_name)
            people["decision_makers"] = dm.get("employees", [])[:10]

        except Exception as e:
            logger.warning("apollo_people_error", error=str(e))
            # Fallback via Serper
            try:
                for title in ["CEO", "CFO", "Diretor", "Fundador"]:
                    search = await self.serper.search(f'"{company_name}" {title} LinkedIn', num=3)
                    for item in search.get("organic", []):
                        if "linkedin.com/in/" in item.get("link", ""):
                            people["executives"].append({
                                "name": item.get("title", "").split(" - ")[0],
                                "linkedin_url": item.get("link"),
                                "title": title
                            })
            except Exception:
                pass

        return people

    async def _get_cnpj_data(self, cnpj: str) -> Dict[str, Any]:
        """Busca dados do CNPJ"""
        try:
            return await self.brasil_api.get_cnpj(cnpj)
        except Exception as e:
            logger.warning("brasil_api_error", error=str(e))
            return {}

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extrai domínio de uma URL"""
        if not url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc or url

    def _list_all_sources(self, result: Dict) -> List[str]:
        """Lista todas as fontes usadas"""
        sources = []
        if result.get("cnpj_data"):
            sources.append("BrasilAPI (CNPJ)")
        if result.get("search_data"):
            sources.append("Google Search (Serper)")
        if result.get("perplexity_full"):
            sources.append("Perplexity AI")
        if result.get("tavily_news") or result.get("tavily_research"):
            sources.append("Tavily Search")
        if result.get("website_data"):
            sources.append("Website Scraping")
        return sources

    def _calculate_confidence(self, result: Dict) -> float:
        """Calcula score de confiança"""
        score = 0.0
        weights = {
            "cnpj_data": 0.15,
            "search_data": 0.10,
            "perplexity_full": 0.20,
            "website_data": 0.25,
            "tavily_research": 0.10,
            "swot_analysis": 0.10,
            "competitors": 0.10
        }

        for key, weight in weights.items():
            data = result.get(key, {})
            if data and not isinstance(data, Exception):
                if isinstance(data, dict) and not data.get("error") or data:
                    score += weight

        return round(min(score, 1.0), 2)

    # ===========================================
    # MÉTODOS SIMPLIFICADOS
    # ===========================================

    async def quick_lookup(self, name: str) -> Dict[str, Any]:
        """
        Busca rápida - usa Perplexity como fonte principal
        Dados são armazenados para uso no analyze_company
        """
        logger.info("company_intel_quick_lookup", company=name)

        # Verificar cache
        cached = self._get_from_cache(name)
        if cached and cached.get("quick_lookup"):
            logger.info("company_intel_cache_hit", company=name)
            return cached.get("quick_lookup")

        # Buscar tudo em paralelo
        tasks = [
            self.serper.find_company_cnpj(name),
            self.serper.find_company_info(name),
            self.perplexity.analyze_company(name, analysis_type="full"),  # Análise completa
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        cnpj = results[0] if not isinstance(results[0], Exception) else None
        search_data = results[1] if not isinstance(results[1], Exception) else {}
        perplexity_data = results[2] if not isinstance(results[2], Exception) else {}

        # Buscar CNPJ data se disponível
        cnpj_data = {}
        if cnpj:
            cnpj_data = await self._get_cnpj_data(cnpj) or {}

        # Montar resultado com formato markdown do Perplexity
        result = {
            "name": name,
            "cnpj": cnpj,
            "razao_social": cnpj_data.get("razao_social"),
            "nome_fantasia": cnpj_data.get("nome_fantasia") or name,
            "website": search_data.get("website"),
            "linkedin": search_data.get("linkedin"),
            "industry": search_data.get("industry"),

            # PERPLEXITY - Fonte principal (já vem em markdown)
            "analysis": perplexity_data.get("analysis"),
            "citations": perplexity_data.get("citations", []),

            # Dados complementares
            "endereco": cnpj_data.get("endereco"),
            "situacao_cadastral": cnpj_data.get("situacao_cadastral"),
            "knowledge_graph": search_data.get("knowledge_graph"),

            "sources": ["Perplexity AI", "Google Search"] + (["BrasilAPI"] if cnpj_data else [])
        }

        # Salvar no cache para uso posterior
        cache_data = self._get_from_cache(name) or {}
        cache_data["quick_lookup"] = result
        cache_data["cnpj_data"] = cnpj_data
        cache_data["search_data"] = search_data
        cache_data["perplexity_full"] = perplexity_data
        self._save_to_cache(name, cache_data)

        return result

    async def get_swot(self, name: str) -> Dict[str, Any]:
        """Gera SWOT usando dados completos"""
        # Primeiro faz quick_lookup para coletar dados
        await self.quick_lookup(name)

        # Depois usa os dados do cache
        cached = self._get_from_cache(name) or {}

        company_data = {
            "name": name,
            "perplexity_analysis": cached.get("perplexity_full", {}).get("analysis"),
            "industry": cached.get("search_data", {}).get("industry"),
            "website_content": "",  # Será preenchido pelo scraping
        }

        # Fazer scraping se tiver website
        website_url = cached.get("search_data", {}).get("website")
        if website_url:
            try:
                website_data = await self.web_scraper.scrape_company_website(website_url)
                company_data["website_content"] = website_data.get("content_summary", "")
            except Exception:
                pass

        return await self.ai_analyzer.analyze_company_swot(
            company_data,
            market_context=cached.get("perplexity_full", {}).get("analysis")
        )

    async def get_okrs(
        self,
        name: str,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Gera OKRs"""
        company_data = await self.quick_lookup(name)
        swot = await self.get_swot(name)
        return await self.ai_analyzer.generate_okrs(company_data, swot=swot, focus_areas=focus_areas)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
