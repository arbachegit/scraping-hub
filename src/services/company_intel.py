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
            from src.database import CompanyRepository, SearchHistoryRepository
            self.repository = CompanyRepository()
            self.search_history = SearchHistoryRepository()
        except Exception:
            self.repository = None
            self.search_history = None

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
        Análise COMPLETA de uma empresa com múltiplas perspectivas

        FLUXO:
        1. Verificar cache/DB
        2. Coletar TODAS as fontes em paralelo
        3. Fazer scraping do site
        4. Buscar funcionários via Apollo
        5. Consolidar dados
        6. Análise MULTI-PERSPECTIVA com Claude (leigo, profissional, fornecedor, concorrente, cliente)
        7. Buscar concorrentes COM MESMA PROFUNDIDADE
        8. Salvar no DB

        Retorna análise densa com citações de fontes [1], [2], etc.
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

            # 3. Segunda rodada: coletar dados detalhados + funcionários
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

            # 5. BUSCAR FUNCIONÁRIOS VIA APOLLO
            logger.info("company_intel_fetching_employees", company=name)
            employees_data = []
            if include_employees:
                employees_data = await self._get_employees_apollo(name, search_data, website_data)
                result["employees"] = employees_data

            # 6. CONSOLIDAR TODOS OS DADOS
            company_profile = self._consolidate_all_data(result, name, cnpj)
            result["company_profile"] = company_profile

            # 7. PREPARAR FONTES PARA CITAÇÃO
            sources = self._build_sources_list(result)
            result["sources_list"] = sources

            # 8. ANÁLISE MULTI-PERSPECTIVA COM CLAUDE
            logger.info("company_intel_multiperspective_analysis", company=name)

            # Preparar contexto rico de pesquisa
            research_context = self._prepare_research_context(result)

            # Extrair conteúdo do website
            website_content = (
                website_data.get("full_content") or
                website_data.get("content_summary", "")
            )

            # Extrair notícias
            news_data = result.get("tavily_news", {}).get("results", [])

            # Análise COMPLETA multi-perspectiva com Claude
            complete_analysis = await self.ai_analyzer.analyze_company_complete(
                company_data=company_profile,
                website_content=website_content,
                employees_data=employees_data,
                news_data=news_data,
                research_context=research_context,
                sources=sources
            )
            result["complete_analysis"] = complete_analysis

            # 9. CONCORRENTES COM MESMA PROFUNDIDADE
            logger.info("company_intel_competitors_deep", company=name)
            result["competitors"] = await self._analyze_competitors_deep(
                name,
                company_profile,
                result.get("perplexity_competitors", {}),
                sources
            )

            result["status"] = "completed"
            result["confidence_score"] = self._calculate_confidence(result)
            result["sources_used"] = sources

            # 10. Salvar no cache e DB
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

            # Salvar no histórico de buscas
            if self.search_history:
                try:
                    await self.search_history.save_search(
                        search_type="company",
                        query={
                            "name": name,
                            "cnpj": cnpj,
                            "analysis_type": analysis_type,
                            "include_competitors": include_competitors,
                            "include_employees": include_employees
                        },
                        results_count=1 + len(result.get("competitors", {}).get("competitors_analyzed", [])),
                        credits_used=1
                    )
                except Exception as e:
                    logger.warning("search_history_error", error=str(e))

        except Exception as e:
            logger.error("company_intel_error", company=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _get_employees_apollo(
        self,
        company_name: str,
        search_data: Dict,
        website_data: Dict
    ) -> List[Dict[str, Any]]:
        """Busca funcionários via Apollo"""
        employees = []

        try:
            domain = self._extract_domain(
                website_data.get("url") or search_data.get("website") or ""
            )

            # Buscar funcionários gerais
            company_employees = await self.apollo.get_company_employees(
                organization_name=company_name,
                domain=domain,
                limit=20
            )
            if company_employees.get("employees"):
                employees.extend(company_employees["employees"])

            # Buscar executivos
            executives = await self.apollo.get_executives(
                organization_name=company_name,
                domain=domain
            )
            if executives.get("employees"):
                # Adicionar sem duplicar
                existing_ids = {e.get("id") for e in employees}
                for exec_data in executives.get("employees", []):
                    if exec_data.get("id") not in existing_ids:
                        employees.append(exec_data)

            # Buscar decision makers
            decision_makers = await self.apollo.get_decision_makers(
                organization_name=company_name
            )
            if decision_makers.get("employees"):
                existing_ids = {e.get("id") for e in employees}
                for dm in decision_makers.get("employees", []):
                    if dm.get("id") not in existing_ids:
                        employees.append(dm)

            logger.info("apollo_employees_found", company=company_name, count=len(employees))

        except Exception as e:
            logger.warning("apollo_employees_error", company=company_name, error=str(e))
            # Fallback: buscar via Serper
            employees = await self._fallback_search_people(company_name)

        return employees[:25]  # Limitar a 25 pessoas

    async def _fallback_search_people(self, company_name: str) -> List[Dict[str, Any]]:
        """Fallback: buscar pessoas via Serper quando Apollo falha"""
        people = []
        try:
            for title in ["CEO", "CFO", "CTO", "COO", "Diretor", "Fundador", "Head"]:
                search = await self.serper.search(
                    f'"{company_name}" {title} LinkedIn site:linkedin.com/in',
                    num=3
                )
                for item in search.get("organic", []):
                    if "linkedin.com/in/" in item.get("link", ""):
                        name_parts = item.get("title", "").split(" - ")
                        people.append({
                            "name": name_parts[0].strip() if name_parts else "N/A",
                            "linkedin_url": item.get("link"),
                            "title": title,
                            "snippet": item.get("snippet", "")
                        })
        except Exception as e:
            logger.warning("fallback_people_error", error=str(e))
        return people

    def _build_sources_list(self, result: Dict) -> List[str]:
        """Constrói lista de fontes para citação"""
        sources = []

        # Website
        website = result.get("website_data", {}).get("url")
        if website:
            sources.append(f"Website oficial: {website}")

        # Perplexity
        perplexity = result.get("perplexity_full", {})
        if perplexity.get("citations"):
            for citation in perplexity["citations"][:5]:
                sources.append(f"Perplexity: {citation}")

        # Tavily research
        tavily = result.get("tavily_research", {})
        if tavily.get("results"):
            for res in tavily["results"][:3]:
                sources.append(f"Tavily: {res.get('url', res.get('title', 'N/A'))}")

        # Tavily news
        news = result.get("tavily_news", {})
        if news.get("results"):
            for n in news["results"][:5]:
                sources.append(f"Notícia: {n.get('title', 'N/A')} ({n.get('source', 'N/A')})")

        # Google Search
        search = result.get("search_data", {})
        if search.get("knowledge_graph"):
            sources.append("Google Knowledge Graph")

        # BrasilAPI
        if result.get("cnpj_data"):
            sources.append("BrasilAPI (Dados Cadastrais CNPJ)")

        # Apollo
        if result.get("employees"):
            sources.append("Apollo.io (Perfis LinkedIn)")

        return sources

    def _prepare_research_context(self, result: Dict) -> str:
        """Prepara contexto de pesquisa para análise Claude"""
        parts = []

        # Perplexity full analysis
        perplexity = result.get("perplexity_full", {})
        if perplexity.get("analysis"):
            parts.append(f"## ANÁLISE PERPLEXITY\n{perplexity['analysis']}")

        # Tavily research
        tavily = result.get("tavily_research", {})
        if tavily.get("answer"):
            parts.append(f"## PESQUISA TAVILY\n{tavily['answer']}")

        # Competitors preview
        competitors = result.get("perplexity_competitors", {})
        if competitors.get("competitors_analysis"):
            parts.append(f"## CONCORRENTES IDENTIFICADOS\n{competitors['competitors_analysis']}")

        # CNPJ data summary
        cnpj_data = result.get("cnpj_data", {})
        if cnpj_data:
            cnpj_summary = f"""## DADOS CADASTRAIS (CNPJ)
- Razão Social: {cnpj_data.get('razao_social', 'N/A')}
- Nome Fantasia: {cnpj_data.get('nome_fantasia', 'N/A')}
- CNPJ: {cnpj_data.get('cnpj', 'N/A')}
- Situação: {cnpj_data.get('situacao_cadastral', 'N/A')}
- Porte: {cnpj_data.get('porte', 'N/A')}
- Capital Social: {cnpj_data.get('capital_social', 'N/A')}
- Data Abertura: {cnpj_data.get('data_abertura', 'N/A')}
- CNAE Principal: {cnpj_data.get('cnae_principal', {}).get('descricao', 'N/A')}"""
            parts.append(cnpj_summary)

        return "\n\n".join(parts)

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

    async def _analyze_competitors_deep(
        self,
        company_name: str,
        company_profile: Dict,
        perplexity_competitors: Dict,
        main_company_sources: List[str]
    ) -> Dict[str, Any]:
        """
        Análise PROFUNDA de concorrentes - mesma profundidade da empresa principal

        Para cada concorrente:
        1. Buscar informações básicas (Serper)
        2. Fazer scraping do website
        3. Buscar pesquisa contextual (Perplexity)
        4. Análise completa via Claude
        """
        logger.info("company_intel_analyzing_competitors_deep", company=company_name)

        competitors_deep = []

        # Extrair nomes dos concorrentes
        competitor_names = self._extract_competitor_names(
            perplexity_competitors.get("competitors_analysis", "")
        )[:5]  # Limitar a 5 concorrentes

        for comp_name in competitor_names:
            logger.info("analyzing_competitor", competitor=comp_name)

            try:
                # 1. Buscar informações básicas
                comp_info = await self.serper.find_company_info(comp_name)

                competitor_data = {
                    "name": comp_name,
                    "website": comp_info.get("website"),
                    "description": comp_info.get("description"),
                    "industry": comp_info.get("industry"),
                    "linkedin": comp_info.get("linkedin")
                }

                # 2. Scraping do website do concorrente
                website_content = ""
                competitor_sources = [f"Website: {comp_info.get('website', 'N/A')}"]

                if comp_info.get("website"):
                    try:
                        website_data = await self.web_scraper.scrape_company_website(
                            comp_info["website"]
                        )
                        website_content = (
                            website_data.get("full_content") or
                            website_data.get("content_summary", "")
                        )
                        competitor_data["website_data"] = website_data
                    except Exception as e:
                        logger.warning("competitor_website_error", competitor=comp_name, error=str(e))

                # 3. Pesquisa contextual do concorrente
                research_context = ""
                try:
                    perplexity_result = await self.perplexity.analyze_company(
                        comp_name,
                        analysis_type="brief"
                    )
                    research_context = perplexity_result.get("analysis", "")
                    if perplexity_result.get("citations"):
                        for c in perplexity_result["citations"][:3]:
                            competitor_sources.append(f"Perplexity: {c}")
                except Exception as e:
                    logger.warning("competitor_perplexity_error", competitor=comp_name, error=str(e))

                # 4. Análise COMPLETA via Claude
                competitor_analysis = await self.ai_analyzer.analyze_competitor_complete(
                    competitor_data=competitor_data,
                    website_content=website_content[:6000],
                    research_context=research_context[:4000],
                    main_company_name=company_name,
                    sources=competitor_sources
                )

                competitors_deep.append({
                    "basic_info": competitor_data,
                    "deep_analysis": competitor_analysis,
                    "sources": competitor_sources
                })

            except Exception as e:
                logger.warning("competitor_deep_analysis_error", competitor=comp_name, error=str(e))
                # Adicionar mesmo com erro, mas com análise básica
                competitors_deep.append({
                    "basic_info": {"name": comp_name, "error": str(e)},
                    "deep_analysis": None,
                    "sources": []
                })

        return {
            "perplexity_overview": perplexity_competitors.get("competitors_analysis"),
            "competitors_analyzed": competitors_deep,
            "total_competitors": len(competitors_deep)
        }

    async def _analyze_competitors_full(
        self,
        company_name: str,
        company_profile: Dict,
        perplexity_competitors: Dict
    ) -> Dict[str, Any]:
        """Análise de concorrentes (método legado - redireciona para deep)"""
        return await self._analyze_competitors_deep(
            company_name,
            company_profile,
            perplexity_competitors,
            []
        )

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
            "cnpj_data": 0.10,
            "search_data": 0.10,
            "perplexity_full": 0.15,
            "website_data": 0.20,
            "tavily_research": 0.10,
            "complete_analysis": 0.15,  # Análise multi-perspectiva
            "employees": 0.10,           # Funcionários Apollo
            "competitors": 0.10
        }

        for key, weight in weights.items():
            data = result.get(key)
            if data and not isinstance(data, Exception):
                if (isinstance(data, dict) and not data.get("error")) or (isinstance(data, list) and len(data) > 0):
                    score += weight

        return round(min(score, 1.0), 2)

    # ===========================================
    # MÉTODOS SIMPLIFICADOS
    # ===========================================

    async def quick_lookup(self, name: str) -> Dict[str, Any]:
        """
        Busca rápida com descrição mínima

        Retorna:
        - Dados básicos (CNPJ, website, LinkedIn)
        - Descrição breve da empresa
        - Setor de atuação
        - Análise resumida do Perplexity
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
            self.perplexity.analyze_company(name, analysis_type="brief"),  # Análise breve
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        cnpj = results[0] if not isinstance(results[0], Exception) else None
        search_data = results[1] if not isinstance(results[1], Exception) else {}
        perplexity_data = results[2] if not isinstance(results[2], Exception) else {}

        # Buscar CNPJ data se disponível
        cnpj_data = {}
        if cnpj:
            cnpj_data = await self._get_cnpj_data(cnpj) or {}

        # Construir descrição mínima
        description = self._build_quick_description(
            name, search_data, cnpj_data, perplexity_data
        )

        # Montar resultado
        result = {
            "name": name,
            "cnpj": cnpj,
            "razao_social": cnpj_data.get("razao_social"),
            "nome_fantasia": cnpj_data.get("nome_fantasia") or name,
            "website": search_data.get("website"),
            "linkedin": search_data.get("linkedin"),
            "industry": search_data.get("industry") or cnpj_data.get("cnae_principal", {}).get("descricao"),

            # DESCRIÇÃO - Sempre presente
            "description": description,

            # Análise Perplexity
            "analysis": perplexity_data.get("analysis"),
            "citations": perplexity_data.get("citations", []),

            # Dados complementares
            "endereco": cnpj_data.get("endereco"),
            "situacao_cadastral": cnpj_data.get("situacao_cadastral"),
            "porte": cnpj_data.get("porte"),
            "capital_social": cnpj_data.get("capital_social"),
            "data_abertura": cnpj_data.get("data_abertura"),
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

    def _build_quick_description(
        self,
        name: str,
        search_data: Dict,
        cnpj_data: Dict,
        perplexity_data: Dict
    ) -> str:
        """
        Constrói descrição mínima da empresa

        Prioridade:
        1. Perplexity (se disponível e curto)
        2. Google Knowledge Graph
        3. Descrição do Google
        4. CNAE + dados cadastrais
        """
        # Tentar extrair resumo do Perplexity (primeiros 500 chars)
        perplexity_text = perplexity_data.get("analysis", "")
        if perplexity_text:
            # Pegar primeiro parágrafo ou até 500 chars
            first_para = perplexity_text.split("\n\n")[0]
            if len(first_para) > 50:
                return first_para[:500] + ("..." if len(first_para) > 500 else "")

        # Tentar Knowledge Graph do Google
        kg = search_data.get("knowledge_graph", {})
        if kg:
            kg_desc = kg.get("description", "")
            if kg_desc:
                return kg_desc

        # Tentar descrição do Serper
        serper_desc = search_data.get("description", "")
        if serper_desc:
            return serper_desc

        # Fallback: construir a partir dos dados cadastrais
        parts = []

        nome = cnpj_data.get("nome_fantasia") or name
        parts.append(f"**{nome}**")

        cnae = cnpj_data.get("cnae_principal", {})
        if cnae.get("descricao"):
            parts.append(f"atua no setor de {cnae['descricao']}")

        porte = cnpj_data.get("porte")
        if porte:
            parts.append(f"({porte})")

        endereco = cnpj_data.get("endereco", {})
        cidade = endereco.get("municipio")
        uf = endereco.get("uf")
        if cidade and uf:
            parts.append(f"— {cidade}/{uf}")

        industry = search_data.get("industry")
        if industry and not cnae.get("descricao"):
            parts.append(f"Setor: {industry}")

        if parts:
            return " ".join(parts)

        return f"Empresa {name} - informações básicas disponíveis via CNPJ e busca"

    async def get_swot(self, name: str, use_full_analysis: bool = True) -> Dict[str, Any]:
        """
        Gera análise SWOT COMPLETA

        Se use_full_analysis=True (padrão), primeiro faz a análise completa
        da empresa para ter todos os dados necessários:
        - Concorrentes analisados
        - Funcionários via Apollo
        - Notícias
        - Dados regionais

        Args:
            name: Nome da empresa
            use_full_analysis: Se True, usa dados da análise completa

        Returns:
            SWOT completo com scoring, priorização e recomendações
        """
        logger.info("company_intel_swot", company=name, full=use_full_analysis)

        # Verificar se já temos análise completa no cache
        cached = self._get_from_cache(name) or {}

        if use_full_analysis and not cached.get("full_analysis"):
            # Fazer análise completa primeiro
            await self.analyze_company(
                name,
                include_competitors=True,
                include_employees=True
            )
            cached = self._get_from_cache(name) or {}

        full_analysis = cached.get("full_analysis", {})

        # Extrair dados necessários para SWOT completo
        company_profile = full_analysis.get("company_profile", {})
        competitors_data = full_analysis.get("competitors", {}).get("competitors_analyzed", [])
        employees_data = full_analysis.get("employees", [])
        news_data = full_analysis.get("tavily_news", {}).get("results", [])
        sources = full_analysis.get("sources_used", [])

        # Preparar contexto de pesquisa
        research_context = self._prepare_research_context(full_analysis)

        # Obter dados regionais
        regional_data = await self._get_regional_data(company_profile)

        # Gerar SWOT COMPLETO
        swot = await self.ai_analyzer.analyze_swot_comprehensive(
            company_data=company_profile,
            competitors_data=competitors_data,
            employees_data=employees_data,
            news_data=news_data,
            regional_data=regional_data,
            research_context=research_context,
            sources=sources
        )

        # Salvar SWOT no cache
        cached["swot_analysis"] = swot
        self._save_to_cache(name, cached)

        return swot

    async def _get_regional_data(self, company_profile: Dict) -> Dict[str, Any]:
        """
        Obtém dados regionais para contextualizar SWOT

        Usa endereço da empresa para buscar:
        - PIB municipal
        - IDHM
        - População
        - Indicadores fiscais
        """
        try:
            from .regional_intel import RegionalIntelService

            endereco = company_profile.get("endereco", {})
            if not endereco:
                return {"available": False, "reason": "Endereço não disponível"}

            async with RegionalIntelService() as regional:
                return await regional.get_region_for_swot(endereco)

        except Exception as e:
            logger.warning("regional_data_error", error=str(e))
            return {"available": False, "reason": str(e)}

    async def get_okrs(
        self,
        name: str,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Gera OKRs baseados no SWOT completo"""
        company_data = await self.quick_lookup(name)
        swot = await self.get_swot(name)
        return await self.ai_analyzer.generate_okrs(company_data, swot=swot, focus_areas=focus_areas)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
