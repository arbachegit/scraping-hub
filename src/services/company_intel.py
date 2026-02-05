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
    1. Buscar CNPJ (se não fornecido) - opcional para PMEs
    2. Coletar dados cadastrais (BrasilAPI) se CNPJ disponível
    3. Enriquecer com buscas (Serper, Tavily) - fonte principal para PMEs
    4. Pesquisar contexto (Perplexity)
    5. Scrape do website
    6. Analisar com AI (Claude)
    """

    # Cache em memória para compartilhar dados entre quick_lookup e analyze
    _cache: Dict[str, Dict] = {}

    def __init__(self):
        self.brasil_api = BrasilAPIClient()
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.web_scraper = WebScraperClient()
        self.ai_analyzer = AIAnalyzer()

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
            # Verificar cache de quick_lookup anterior
            cached = self._get_from_cache(name) or {}
            cached_cnpj_data = cached.get("cnpj_data", {})
            cached_search_data = cached.get("search_data", {})

            # 1. Usar CNPJ do cache ou buscar
            if not cnpj and cached.get("quick_lookup", {}).get("cnpj"):
                cnpj = cached["quick_lookup"]["cnpj"]
                logger.info("company_intel_cnpj_from_cache", company=name)
            elif not cnpj:
                logger.info("company_intel_finding_cnpj", company=name)
                cnpj = await self.serper.find_company_cnpj(name)

            # 2. Definir tarefas - usar cache se disponível
            tasks = {}

            # CNPJ data
            if cached_cnpj_data:
                result["cnpj_data"] = cached_cnpj_data
            elif cnpj:
                tasks["cnpj_data"] = self._get_cnpj_data(cnpj)

            # Search data
            if cached_search_data:
                result["search_data"] = cached_search_data
            else:
                tasks["search_data"] = self.serper.find_company_info(name)

            # Research data - sempre buscar análise completa para enriquecer
            tasks["research_data"] = self.perplexity.analyze_company(name, analysis_type="full")

            # News - sempre buscar fresco
            tasks["news_data"] = self.tavily.get_company_news(name, days=30)

            # Executar tarefas em paralelo
            if tasks:
                task_results = await asyncio.gather(
                    *tasks.values(),
                    return_exceptions=True
                )

                # Mapear resultados
                task_keys = list(tasks.keys())
                for i, key in enumerate(task_keys):
                    if isinstance(task_results[i], Exception):
                        logger.warning(f"company_intel_{key}_error", error=str(task_results[i]))
                        result[key] = result.get(key, {})
                    else:
                        result[key] = task_results[i]

            # 3. Scrape do website - PRIORIDADE MÁXIMA
            website_url = (
                result.get("search_data", {}).get("website") or
                result.get("cnpj_data", {}).get("website")
            )

            # Se não encontrou, buscar agressivamente
            if not website_url:
                logger.info("company_intel_searching_website", company=name)
                try:
                    website_search = await self.serper.search(f'"{name}" site oficial Brasil', num=5)
                    for item in website_search.get("organic", []):
                        link = item.get("link", "")
                        # Evitar redes sociais e sites de busca
                        if link and not any(x in link for x in ["linkedin", "facebook", "instagram", "twitter", "youtube", "google", "wikipedia"]):
                            website_url = link
                            break
                except Exception as e:
                    logger.warning("website_search_error", error=str(e))

            if website_url:
                logger.info("company_intel_scraping_website", url=website_url)
                try:
                    # Scrape da página principal
                    main_scrape = await self.web_scraper.scrape_company_website(website_url)
                    result["website_data"] = main_scrape

                    # Scrape de páginas importantes (about, services, etc)
                    important_pages = main_scrape.get("important_pages", {})
                    additional_content = []

                    for page_type, page_url in important_pages.items():
                        if page_url and page_type in ["about", "services", "products"]:
                            try:
                                page_data = await self.web_scraper.scrape(page_url)
                                page_text = page_data.get("content", {}).get("text", "")[:3000]
                                if page_text:
                                    additional_content.append(f"\n\n=== {page_type.upper()} ===\n{page_text}")
                            except Exception:
                                pass

                    # Adicionar conteúdo das páginas importantes
                    if additional_content:
                        current_content = result["website_data"].get("content_summary", "")
                        result["website_data"]["content_summary"] = current_content + "".join(additional_content)

                except Exception as e:
                    logger.warning("company_intel_website_error", url=website_url, error=str(e))
                    result["website_data"] = {}
            else:
                logger.warning("company_intel_no_website", company=name)
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
        """
        Consolida dados de múltiplas fontes
        PRIORIDADE: Website > Perplexity > Serper > CNPJ
        """
        cnpj_data = result.get("cnpj_data", {})
        search_data = result.get("search_data", {})
        website_data = result.get("website_data", {})
        research_data = result.get("research_data", {})

        # Extrair conteúdo do site (PRIORIDADE)
        website_content = website_data.get("content_summary", "")
        website_headings = website_data.get("headings", [])
        website_contact = website_data.get("contact_info", {})

        profile = {
            # Identificação
            "name": name,
            "nome_fantasia": cnpj_data.get("nome_fantasia") or website_data.get("company_name") or name,
            "razao_social": cnpj_data.get("razao_social"),
            "cnpj": cnpj or cnpj_data.get("cnpj") or website_contact.get("cnpj"),

            # Contato e localização (prioriza dados do site)
            "website": (
                website_data.get("url") or
                search_data.get("website") or
                cnpj_data.get("website")
            ),
            "endereco": cnpj_data.get("endereco", {}),
            "telefone": website_contact.get("phones", [None])[0] or cnpj_data.get("telefone"),
            "email": website_contact.get("emails", [None])[0] if website_contact.get("emails") else cnpj_data.get("email"),

            # Negócio - PRIORIZA CONTEÚDO DO SITE
            "industry": (
                search_data.get("industry") or
                cnpj_data.get("cnae_principal", {}).get("descricao")
            ),
            "description": (
                website_data.get("description") or  # Meta description do site
                search_data.get("description") or
                cnpj_data.get("cnae_principal", {}).get("descricao")
            ),

            # CONTEÚDO DO SITE - DADOS PRINCIPAIS PARA ANÁLISE
            "website_content": website_content,  # Texto completo do site
            "website_headings": website_headings,  # Títulos e seções
            "website_pages": website_data.get("important_pages", {}),  # Páginas importantes

            "porte": cnpj_data.get("porte"),
            "capital_social": cnpj_data.get("capital_social"),
            "data_abertura": cnpj_data.get("data_abertura"),
            "situacao_cadastral": cnpj_data.get("situacao_cadastral"),

            # Social (prioriza dados do site)
            "linkedin_url": website_data.get("social_media", {}).get("linkedin") or search_data.get("linkedin"),
            "social_media": website_data.get("social_media", {}),

            # Sócios
            "socios": cnpj_data.get("socios", []),

            # Dados extras
            "knowledge_graph": search_data.get("knowledge_graph"),
            "research_summary": research_data.get("analysis"),

            # Tecnologias detectadas no site
            "technologies": website_data.get("technologies", []),

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
        Dados são salvos no cache para uso posterior no analyze_company

        Args:
            name: Nome da empresa

        Returns:
            Dados básicos
        """
        logger.info("company_intel_quick_lookup", company=name)

        # Verificar cache primeiro
        cached = self._get_from_cache(name)
        if cached and cached.get("quick_lookup"):
            logger.info("company_intel_cache_hit", company=name)
            return cached.get("quick_lookup")

        # Buscar dados em paralelo (CNPJ, busca e pesquisa)
        tasks = [
            self.serper.find_company_cnpj(name),
            self.serper.find_company_info(name),
            self.perplexity.research(f"empresa {name} Brasil perfil negócio", depth="brief")
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        cnpj = results[0] if not isinstance(results[0], Exception) else None
        search_data = results[1] if not isinstance(results[1], Exception) else {}
        research_data = results[2] if not isinstance(results[2], Exception) else {}

        # Buscar dados CNPJ se disponível
        cnpj_data = {}
        if cnpj:
            try:
                cnpj_data = await self._get_cnpj_data(cnpj)
            except Exception as e:
                logger.warning("cnpj_lookup_failed", error=str(e))

        # Construir resultado combinando todas as fontes
        result = {
            "name": name,
            "cnpj": cnpj,
            "razao_social": cnpj_data.get("razao_social") if cnpj_data else None,
            "nome_fantasia": cnpj_data.get("nome_fantasia") if cnpj_data else name,
            "website": search_data.get("website") if isinstance(search_data, dict) else None,
            "industry": search_data.get("industry") if isinstance(search_data, dict) else None,
            "description": (
                search_data.get("description") or
                research_data.get("answer", "")[:500] if isinstance(research_data, dict) else None
            ),
            "endereco": cnpj_data.get("endereco") if cnpj_data else None,
            "situacao_cadastral": cnpj_data.get("situacao_cadastral") if cnpj_data else None,
            "linkedin_url": search_data.get("linkedin") if isinstance(search_data, dict) else None,
            "knowledge_graph": search_data.get("knowledge_graph") if isinstance(search_data, dict) else None,
            "research_summary": research_data.get("answer") if isinstance(research_data, dict) else None,
            "sources": ["Google Search", "Perplexity"] + (["BrasilAPI"] if cnpj_data else [])
        }

        # Salvar no cache para uso posterior
        cache_data = self._get_from_cache(name) or {}
        cache_data["quick_lookup"] = result
        cache_data["cnpj_data"] = cnpj_data
        cache_data["search_data"] = search_data
        cache_data["research_data"] = research_data
        self._save_to_cache(name, cache_data)

        return result

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
