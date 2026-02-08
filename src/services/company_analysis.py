"""
Company Analysis Service - 11 Blocos
Análise completa de empresas com 11 blocos temáticos
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.database import (
    AnaliseEmpresaRepository,
    BuscaRepository,
    ConcorrenteRepository,
    EmpresaRepository,
    EventoPessoaRepository,
    PessoaRepository,
)
from src.scrapers import (
    ApolloClient,
    BrasilAPIClient,
    PerplexityClient,
    SerperClient,
    TavilyClient,
    WebScraperClient,
)

from .ai_analyzer import AIAnalyzer
from .keyword_extractor import KeywordExtractor

logger = structlog.get_logger()


class CompanyAnalysisService:
    """
    Serviço de Análise de Empresas com 11 Blocos Temáticos

    Blocos:
    1. A Empresa - Dados cadastrais, história, mercado
    2. Pessoas da Empresa - Colaboradores, executivos
    3. Formação das Pessoas - Background educacional
    4. Ativo Humano - Competências agregadas
    5. Capacidade do Ativo - O que conseguem entregar
    6. Comunicação vs Características - Alinhamento mensagem/realidade
    7. Fraquezas na Comunicação - Gaps identificados
    8. Visão do Leigo - Como público geral entende
    9. Visão do Profissional - Como especialista avalia
    10. Visão do Concorrente - Como rival enxerga
    11. Visão do Fornecedor - Como parceiro avalia

    Síntese Final:
    - Hipótese de Objetivo vs OKR sugerido
    - Concorrentes com Stamps (Forte/Médio/Fraco)
    - SWOT Contemporâneo com scoring e TOWS
    """

    def __init__(self):
        # Scrapers
        self.brasil_api = BrasilAPIClient()
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.web_scraper = WebScraperClient()

        # AI Services
        self.ai_analyzer = AIAnalyzer()
        self.keyword_extractor = KeywordExtractor()

        # Repositories
        self.empresa_repo = EmpresaRepository()
        self.pessoa_repo = PessoaRepository()
        self.analise_repo = AnaliseEmpresaRepository()
        self.evento_repo = EventoPessoaRepository()
        self.concorrente_repo = ConcorrenteRepository()
        self.busca_repo = BuscaRepository()

        logger.info("company_analysis_service_init")

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

    async def analyze_complete(
        self,
        name: str,
        cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Análise COMPLETA com 11 blocos temáticos

        Fluxo de Execução:
        FASE 1: Coleta Paralela de Dados
        FASE 2: Geração dos Blocos 1-3 (dados primários)
        FASE 3: Geração dos Blocos 4-5 (derivados de pessoas)
        FASE 4: Geração dos Blocos 6-7 (análise de comunicação)
        FASE 5: Geração dos Blocos 8-11 (perspectivas em paralelo)
        FASE 6: Síntese Final (hipótese, concorrentes, SWOT)
        """
        logger.info("company_analysis_complete_start", company=name)
        start_time = datetime.utcnow()

        result = {
            "metadata": {
                "company_name": name,
                "cnpj": cnpj,
                "analysis_date": start_time.isoformat(),
                "data_quality_score": 0.0,
                "sources_used": []
            },
            "blocks": {},
            "synthesis": {},
            "status": "processing"
        }

        try:
            # ===== FASE 1: COLETA PARALELA DE DADOS =====
            logger.info("phase_1_data_collection", company=name)
            raw_data = await self._collect_all_data(name, cnpj)
            result["metadata"]["sources_used"] = raw_data.get("sources", [])

            # ===== FASE 2: BLOCOS 1-3 (DADOS PRIMÁRIOS) =====
            logger.info("phase_2_primary_blocks", company=name)
            blocks_1_3 = await self._generate_primary_blocks(name, raw_data)
            result["blocks"].update(blocks_1_3)

            # ===== FASE 3: BLOCOS 4-5 (DERIVADOS DE PESSOAS) =====
            logger.info("phase_3_people_derived_blocks", company=name)
            blocks_4_5 = await self._generate_people_derived_blocks(
                name, raw_data, blocks_1_3
            )
            result["blocks"].update(blocks_4_5)

            # ===== FASE 4: BLOCOS 6-7 (COMUNICAÇÃO) =====
            logger.info("phase_4_communication_blocks", company=name)
            blocks_6_7 = await self._generate_communication_blocks(
                name, raw_data, result["blocks"]
            )
            result["blocks"].update(blocks_6_7)

            # ===== FASE 5: BLOCOS 8-11 (PERSPECTIVAS EM PARALELO) =====
            logger.info("phase_5_perspective_blocks", company=name)
            blocks_8_11 = await self._generate_perspective_blocks(
                name, raw_data, result["blocks"]
            )
            result["blocks"].update(blocks_8_11)

            # ===== FASE 6: SÍNTESE FINAL =====
            logger.info("phase_6_synthesis", company=name)
            synthesis = await self._generate_synthesis(
                name, raw_data, result["blocks"]
            )
            result["synthesis"] = synthesis

            # Calcular qualidade dos dados
            result["metadata"]["data_quality_score"] = self._calculate_quality_score(
                raw_data, result["blocks"]
            )

            # ===== FASE 7: PERSISTÊNCIA =====
            logger.info("phase_7_persistence", company=name)
            persistence_result = await self._persist_analysis(
                name, cnpj, raw_data, result
            )
            result["metadata"]["empresa_id"] = persistence_result.get("empresa_id")
            result["metadata"]["analise_id"] = persistence_result.get("analise_id")
            result["palavras_chave"] = persistence_result.get("palavras_chave", [])
            result["palavras_chave_por_bloco"] = persistence_result.get("palavras_chave_por_bloco", {})

            # ===== FASE 8: BUSCA DE CONCORRENTES =====
            if persistence_result.get("empresa_id"):
                logger.info("phase_8_competitors", company=name)
                await self._find_and_analyze_competitors(
                    empresa_id=persistence_result["empresa_id"],
                    company_name=name,
                    keywords=persistence_result.get("palavras_chave", []),
                    search_queries=persistence_result.get("search_queries", [])
                )

            result["status"] = "completed"
            result["metadata"]["processing_time_seconds"] = (
                datetime.utcnow() - start_time
            ).total_seconds()

            logger.info(
                "company_analysis_complete_done",
                company=name,
                duration=result["metadata"]["processing_time_seconds"]
            )

        except Exception as e:
            logger.error("company_analysis_error", company=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    # =========================================
    # FASE 1: COLETA DE DADOS
    # =========================================

    async def _collect_all_data(
        self,
        name: str,
        cnpj: Optional[str]
    ) -> Dict[str, Any]:
        """
        Coleta TODOS os dados necessários em paralelo

        Fontes:
        - BrasilAPI (CNPJ)
        - Serper (Google Search)
        - WebScraper (Website)
        - Apollo (Funcionários)
        - Perplexity (Pesquisa contextual)
        - Tavily (Notícias)
        """
        data = {
            "sources": [],
            "cnpj_data": {},
            "search_data": {},
            "website_data": {},
            "employees": [],
            "perplexity_research": {},
            "tavily_news": [],
            "tavily_research": {}
        }

        # Primeira rodada: buscar CNPJ e website
        initial_tasks = {
            "cnpj_search": self.serper.find_company_cnpj(name),
            "company_search": self.serper.find_company_info(name),
        }

        initial_results = await asyncio.gather(
            *initial_tasks.values(),
            return_exceptions=True
        )

        # Extrair CNPJ
        if not cnpj and not isinstance(initial_results[0], Exception):
            cnpj = initial_results[0]

        # Extrair dados de busca
        if not isinstance(initial_results[1], Exception):
            data["search_data"] = initial_results[1]
            data["sources"].append("Google Search (Serper)")

        website_url = data["search_data"].get("website")

        # Segunda rodada: coleta paralela completa
        detail_tasks = []
        task_names = []

        # CNPJ Data
        if cnpj:
            detail_tasks.append(self.brasil_api.get_cnpj(cnpj))
            task_names.append("cnpj_data")

        # Website Scraping
        if website_url:
            detail_tasks.append(self.web_scraper.scrape_company_website(website_url))
            task_names.append("website_data")

        # Apollo - Funcionários
        domain = self._extract_domain(website_url) if website_url else None
        detail_tasks.append(
            self.apollo.get_company_employees(
                organization_name=name,
                domain=domain,
                per_page=50
            )
        )
        task_names.append("employees")

        # Perplexity - Pesquisa contextual
        detail_tasks.append(self.perplexity.analyze_company(name, analysis_type="full"))
        task_names.append("perplexity_research")

        # Tavily - Notícias
        detail_tasks.append(self.tavily.get_company_news(name, days=60))
        task_names.append("tavily_news")

        # Tavily - Pesquisa geral
        detail_tasks.append(
            self.tavily.research(f"empresa {name} Brasil história produtos serviços mercado")
        )
        task_names.append("tavily_research")

        # Executar em paralelo
        detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)

        # Processar resultados
        for i, task_name in enumerate(task_names):
            if not isinstance(detail_results[i], Exception):
                if task_name == "employees":
                    data["employees"] = detail_results[i].get("employees", [])
                    if data["employees"]:
                        data["sources"].append("Apollo (LinkedIn)")
                elif task_name == "cnpj_data":
                    data["cnpj_data"] = detail_results[i]
                    data["sources"].append("BrasilAPI (CNPJ)")
                elif task_name == "website_data":
                    data["website_data"] = detail_results[i]
                    data["sources"].append("Website Oficial")
                elif task_name == "perplexity_research":
                    data["perplexity_research"] = detail_results[i]
                    data["sources"].append("Perplexity AI")
                elif task_name == "tavily_news":
                    data["tavily_news"] = detail_results[i].get("results", [])
                    if data["tavily_news"]:
                        data["sources"].append("Tavily (Notícias)")
                elif task_name == "tavily_research":
                    data["tavily_research"] = detail_results[i]
                    data["sources"].append("Tavily (Pesquisa)")
            else:
                logger.warning(f"data_collection_{task_name}_error", error=str(detail_results[i]))

        # ========================================
        # FALLBACK PARA BUSCA DE PESSOAS
        # Prioridade: Apollo → Perplexity → Google
        # ========================================
        data["employees_source"] = None

        # 1. Tentar Apollo primeiro (já foi tentado acima)
        if data["employees"]:
            data["employees_source"] = "Apollo"
            logger.info("employees_found", source="Apollo", count=len(data["employees"]))
        else:
            # 2. Fallback: buscar executivos no Apollo
            try:
                executives = await self.apollo.get_executives(
                    organization_name=name,
                    domain=domain
                )
                if executives.get("employees"):
                    data["employees"] = executives["employees"]
                    data["employees_source"] = "Apollo (Executives)"
                    data["sources"].append("Apollo (LinkedIn)")
                    logger.info("employees_found", source="Apollo Executives", count=len(data["employees"]))
            except Exception as e:
                logger.warning("apollo_executives_error", error=str(e))

        # 3. Fallback: Perplexity se Apollo falhou
        if not data["employees"]:
            try:
                logger.info("employees_fallback_perplexity", company=name)
                people_result = await self.perplexity.search(
                    f"Quem são os principais executivos, fundadores e líderes da empresa {name} Brasil? "
                    f"Liste nomes, cargos e LinkedIn se disponível."
                )
                if people_result and people_result.get("answer"):
                    extracted = self._extract_people_from_text(people_result["answer"], name)
                    if extracted:
                        data["employees"] = extracted
                        data["employees_source"] = "Perplexity"
                        logger.info("employees_found", source="Perplexity", count=len(extracted))
            except Exception as e:
                logger.warning("perplexity_people_error", error=str(e))

        # 4. Fallback: Google/Serper se Perplexity falhou
        if not data["employees"]:
            try:
                logger.info("employees_fallback_google", company=name)
                google_result = await self.serper.search(
                    f"{name} empresa executivos fundadores CEO diretores LinkedIn"
                )
                if google_result and google_result.get("organic"):
                    extracted = self._extract_people_from_search(google_result["organic"], name)
                    if extracted:
                        data["employees"] = extracted
                        data["employees_source"] = "Google"
                        logger.info("employees_found", source="Google", count=len(extracted))
            except Exception as e:
                logger.warning("google_people_error", error=str(e))

        if data["employees_source"]:
            data["sources"].append(f"Pessoas ({data['employees_source']})")

        data["cnpj"] = cnpj
        data["name"] = name
        data["website_url"] = website_url

        return data

    def _extract_people_from_text(self, text: str, company_name: str) -> List[Dict[str, Any]]:
        """Extrai pessoas de texto do Perplexity"""
        import re

        people = []
        # Padrões para encontrar pessoas
        patterns = [
            r"([A-Z][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-Z][a-záàâãéèêíìîóòôõúùûç]+)+)\s*[-–:,]\s*(CEO|CTO|CFO|COO|Fundador|Founder|Diretor|Director|Presidente|VP|Head|Sócio|Partner|Gerente|Manager)",
            r"(CEO|CTO|CFO|COO|Fundador|Founder|Diretor|Director|Presidente):\s*([A-Z][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-Z][a-záàâãéèêíìîóòôõúùûç]+)+)",
        ]

        seen_names = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    name = match[0].strip() if match[0][0].isupper() else match[1].strip()
                    title = match[1].strip() if match[0][0].isupper() else match[0].strip()

                    if name and name not in seen_names and len(name) > 5:
                        seen_names.add(name)
                        people.append({
                            "name": name,
                            "title": title,
                            "organization_name": company_name,
                            "fonte": "perplexity"
                        })

        return people[:20]

    def _extract_people_from_search(self, results: List[Dict], company_name: str) -> List[Dict[str, Any]]:
        """Extrai pessoas dos resultados de busca Google"""
        import re

        people = []
        seen_names = set()

        for result in results[:10]:
            title = result.get("title", "")
            link = result.get("link", "")

            # Se é um perfil LinkedIn
            if "linkedin.com/in/" in link:
                # Extrair nome do título
                name_match = re.match(r"^([A-Z][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-Z][a-záàâãéèêíìîóòôõúùûç]+)+)", title)
                if name_match:
                    name = name_match.group(1)
                    if name not in seen_names:
                        seen_names.add(name)
                        # Tentar extrair cargo
                        cargo = ""
                        cargo_match = re.search(r"[-–|]\s*([^|]+?)(?:\s*[-–|]|$)", title)
                        if cargo_match:
                            cargo = cargo_match.group(1).strip()

                        people.append({
                            "name": name,
                            "title": cargo,
                            "linkedin_url": link,
                            "organization_name": company_name,
                            "fonte": "google"
                        })

        return people[:15]

    # =========================================
    # FASE 2: BLOCOS 1-3 (PRIMÁRIOS)
    # =========================================

    async def _generate_primary_blocks(
        self,
        name: str,
        raw_data: Dict
    ) -> Dict[str, Any]:
        """Gera blocos 1, 2 e 3 (dados primários)"""

        blocks = {}

        # Preparar contexto comum
        website_content = (
            raw_data.get("website_data", {}).get("full_content") or
            raw_data.get("website_data", {}).get("content_summary", "")
        )
        perplexity_text = raw_data.get("perplexity_research", {}).get("analysis", "")
        cnpj_data = raw_data.get("cnpj_data", {})
        employees = raw_data.get("employees", [])

        # BLOCO 1: A Empresa
        block_1 = await self.ai_analyzer.generate_block_empresa(
            company_name=name,
            cnpj_data=cnpj_data,
            website_content=website_content,
            perplexity_context=perplexity_text,
            tavily_research=raw_data.get("tavily_research", {}).get("answer", "")
        )
        blocks["1_empresa"] = block_1

        # BLOCO 2: Pessoas da Empresa
        block_2 = await self.ai_analyzer.generate_block_pessoas(
            company_name=name,
            employees=employees,
            website_content=website_content
        )
        blocks["2_pessoas"] = block_2

        # BLOCO 3: Formação das Pessoas
        block_3 = await self.ai_analyzer.generate_block_formacao(
            company_name=name,
            employees=employees,
            perplexity_context=perplexity_text
        )
        blocks["3_formacao"] = block_3

        return blocks

    # =========================================
    # FASE 3: BLOCOS 4-5 (DERIVADOS DE PESSOAS)
    # =========================================

    async def _generate_people_derived_blocks(
        self,
        name: str,
        raw_data: Dict,
        previous_blocks: Dict
    ) -> Dict[str, Any]:
        """Gera blocos 4 e 5 (derivados das pessoas)"""

        blocks = {}

        pessoas_block = previous_blocks.get("2_pessoas", {})
        formacao_block = previous_blocks.get("3_formacao", {})

        # BLOCO 4: Ativo Humano
        block_4 = await self.ai_analyzer.generate_block_ativo_humano(
            company_name=name,
            pessoas_content=pessoas_block.get("content", ""),
            formacao_content=formacao_block.get("content", "")
        )
        blocks["4_ativo_humano"] = block_4

        # BLOCO 5: Capacidade do Ativo
        block_5 = await self.ai_analyzer.generate_block_capacidade(
            company_name=name,
            ativo_humano_content=block_4.get("content", ""),
            empresa_content=previous_blocks.get("1_empresa", {}).get("content", "")
        )
        blocks["5_capacidade"] = block_5

        return blocks

    # =========================================
    # FASE 4: BLOCOS 6-7 (COMUNICAÇÃO)
    # =========================================

    async def _generate_communication_blocks(
        self,
        name: str,
        raw_data: Dict,
        previous_blocks: Dict
    ) -> Dict[str, Any]:
        """Gera blocos 6 e 7 (análise de comunicação)"""

        blocks = {}

        website_content = (
            raw_data.get("website_data", {}).get("full_content") or
            raw_data.get("website_data", {}).get("content_summary", "")
        )
        perplexity_text = raw_data.get("perplexity_research", {}).get("analysis", "")

        # BLOCO 6: Comunicação vs Características
        block_6 = await self.ai_analyzer.generate_block_comunicacao(
            company_name=name,
            website_content=website_content,
            perplexity_context=perplexity_text,
            empresa_content=previous_blocks.get("1_empresa", {}).get("content", ""),
            capacidade_content=previous_blocks.get("5_capacidade", {}).get("content", "")
        )
        blocks["6_comunicacao"] = block_6

        # BLOCO 7: Fraquezas na Comunicação
        block_7 = await self.ai_analyzer.generate_block_fraquezas_comunicacao(
            company_name=name,
            comunicacao_content=block_6.get("content", "")
        )
        blocks["7_fraquezas"] = block_7

        return blocks

    # =========================================
    # FASE 5: BLOCOS 8-11 (PERSPECTIVAS)
    # =========================================

    async def _generate_perspective_blocks(
        self,
        name: str,
        raw_data: Dict,
        previous_blocks: Dict
    ) -> Dict[str, Any]:
        """Gera blocos 8-11 (perspectivas em paralelo)"""

        # Preparar contexto consolidado
        all_blocks_content = "\n\n".join([
            f"## {key.upper()}\n{block.get('content', '')}"
            for key, block in previous_blocks.items()
        ])

        perplexity_text = raw_data.get("perplexity_research", {}).get("analysis", "")
        news_data = raw_data.get("tavily_news", [])

        # Executar 4 perspectivas em paralelo
        perspective_tasks = [
            self.ai_analyzer.generate_block_visao_leigo(
                company_name=name,
                all_blocks_content=all_blocks_content
            ),
            self.ai_analyzer.generate_block_visao_profissional(
                company_name=name,
                all_blocks_content=all_blocks_content,
                perplexity_context=perplexity_text
            ),
            self.ai_analyzer.generate_block_visao_concorrente(
                company_name=name,
                all_blocks_content=all_blocks_content,
                perplexity_context=perplexity_text,
                news_data=news_data
            ),
            self.ai_analyzer.generate_block_visao_fornecedor(
                company_name=name,
                all_blocks_content=all_blocks_content,
                cnpj_data=raw_data.get("cnpj_data", {}),
                perplexity_context=perplexity_text
            )
        ]

        results = await asyncio.gather(*perspective_tasks, return_exceptions=True)

        blocks = {}

        # BLOCO 8: Visão do Leigo
        if not isinstance(results[0], Exception):
            blocks["8_visao_leigo"] = results[0]
        else:
            blocks["8_visao_leigo"] = {"title": "Visão do Leigo", "content": "Erro na geração", "error": str(results[0])}

        # BLOCO 9: Visão do Profissional
        if not isinstance(results[1], Exception):
            blocks["9_visao_profissional"] = results[1]
        else:
            blocks["9_visao_profissional"] = {"title": "Visão do Profissional", "content": "Erro na geração", "error": str(results[1])}

        # BLOCO 10: Visão do Concorrente
        if not isinstance(results[2], Exception):
            blocks["10_visao_concorrente"] = results[2]
        else:
            blocks["10_visao_concorrente"] = {"title": "Visão do Concorrente", "content": "Erro na geração", "error": str(results[2])}

        # BLOCO 11: Visão do Fornecedor
        if not isinstance(results[3], Exception):
            blocks["11_visao_fornecedor"] = results[3]
        else:
            blocks["11_visao_fornecedor"] = {"title": "Visão do Fornecedor", "content": "Erro na geração", "error": str(results[3])}

        return blocks

    # =========================================
    # FASE 6: SÍNTESE FINAL
    # =========================================

    async def _generate_synthesis(
        self,
        name: str,
        raw_data: Dict,
        all_blocks: Dict
    ) -> Dict[str, Any]:
        """
        Gera síntese final:
        - Hipótese de Objetivo vs OKR sugerido
        - Concorrentes com Stamps
        - SWOT Contemporâneo
        """

        synthesis = {}

        # Preparar contexto consolidado
        all_blocks_content = "\n\n".join([
            f"## {key.upper()}\n{block.get('content', '')}"
            for key, block in all_blocks.items()
        ])

        # Tarefas de síntese em paralelo
        synthesis_tasks = [
            # Hipótese de Objetivo e OKRs
            self.ai_analyzer.generate_hypothesis_and_okrs(
                company_name=name,
                all_blocks_content=all_blocks_content
            ),
            # Análise de Concorrentes com Stamps
            self._analyze_competitors_with_stamps(
                name, raw_data, all_blocks_content
            ),
            # SWOT Contemporâneo
            self.ai_analyzer.generate_swot_contemporaneo(
                company_name=name,
                all_blocks_content=all_blocks_content,
                raw_data=raw_data
            )
        ]

        results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)

        # Hipótese e OKRs
        if not isinstance(results[0], Exception):
            synthesis["hypothesis_objective"] = results[0].get("hypothesis", {})
            synthesis["suggested_okr"] = results[0].get("okrs", {})
        else:
            synthesis["hypothesis_objective"] = {"error": str(results[0])}
            synthesis["suggested_okr"] = {"error": str(results[0])}

        # Concorrentes
        if not isinstance(results[1], Exception):
            synthesis["competitors"] = results[1]
        else:
            synthesis["competitors"] = []

        # SWOT
        if not isinstance(results[2], Exception):
            synthesis["swot"] = results[2]
        else:
            synthesis["swot"] = {"error": str(results[2])}

        return synthesis

    async def _analyze_competitors_with_stamps(
        self,
        company_name: str,
        raw_data: Dict,
        all_blocks_content: str
    ) -> List[Dict[str, Any]]:
        """
        Analisa concorrentes e atribui Stamps (Forte/Médio/Fraco)
        """
        # Buscar concorrentes via Perplexity
        try:
            competitors_info = await self.perplexity.find_competitors(
                company_name,
                raw_data.get("search_data", {}).get("industry")
            )
        except Exception:
            competitors_info = {}

        # Extrair nomes de concorrentes
        competitor_names = self._extract_competitor_names(
            competitors_info.get("competitors_analysis", "")
        )[:5]

        if not competitor_names:
            return []

        # Analisar cada concorrente
        competitors = []
        for comp_name in competitor_names:
            try:
                # Buscar info básica
                comp_info = await self.serper.find_company_info(comp_name)

                # Gerar análise com stamp via AI
                comp_analysis = await self.ai_analyzer.analyze_competitor_with_stamp(
                    main_company=company_name,
                    competitor_name=comp_name,
                    competitor_info=comp_info,
                    main_company_context=all_blocks_content[:4000]
                )

                competitors.append(comp_analysis)

            except Exception as e:
                logger.warning("competitor_stamp_error", competitor=comp_name, error=str(e))
                competitors.append({
                    "name": comp_name,
                    "description": "Informações não disponíveis",
                    "stamp": "Medio",
                    "stamp_color": "yellow",
                    "justification": "Dados insuficientes para avaliação completa"
                })

        return competitors

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

    def _calculate_quality_score(
        self,
        raw_data: Dict,
        blocks: Dict
    ) -> float:
        """Calcula score de qualidade dos dados"""
        score = 0.0
        max_score = 0.0

        # Fontes de dados (40%)
        source_weights = {
            "cnpj_data": 0.08,
            "website_data": 0.12,
            "employees": 0.08,
            "perplexity_research": 0.08,
            "tavily_news": 0.04
        }

        for source, weight in source_weights.items():
            max_score += weight
            data = raw_data.get(source)
            if data and (isinstance(data, dict) and data) or (isinstance(data, list) and len(data) > 0):
                score += weight

        # Blocos gerados (60%)
        block_weight = 0.06
        for block_key in blocks:
            max_score += block_weight
            block = blocks.get(block_key, {})
            if block.get("content") and not block.get("error"):
                score += block_weight

        return round(score / max_score if max_score > 0 else 0, 2)

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extrai domínio de uma URL"""
        if not url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc or url

    # =========================================
    # FASE 7: PERSISTÊNCIA
    # =========================================

    async def _persist_analysis(
        self,
        name: str,
        cnpj: Optional[str],
        raw_data: Dict,
        result: Dict
    ) -> Dict[str, Any]:
        """
        Persiste empresa, pessoas e análise no banco de dados

        Returns:
            {
                "empresa_id": "...",
                "analise_id": "...",
                "pessoas_salvas": 10,
                "palavras_chave": [...],
                "search_queries": [...]
            }
        """
        persistence_result: Dict[str, Any] = {
            "empresa_id": None,
            "analise_id": None,
            "pessoas_salvas": 0,
            "palavras_chave": [],
            "palavras_chave_por_bloco": {},
            "search_queries": []
        }

        try:
            # 1. Extrair fundadores dos dados
            fundadores = self._extract_founders(raw_data)

            # 2. Salvar empresa em dim_empresas
            cnpj_data = raw_data.get("cnpj_data", {})
            empresa_data = {
                "cnpj": cnpj or cnpj_data.get("cnpj"),
                "razao_social": cnpj_data.get("razao_social"),
                "nome_fantasia": cnpj_data.get("nome_fantasia") or name,
                "cnae_principal": cnpj_data.get("cnae_fiscal"),
                "cnae_descricao": cnpj_data.get("cnae_fiscal_descricao"),
                "logradouro": cnpj_data.get("logradouro"),
                "numero": cnpj_data.get("numero"),
                "complemento": cnpj_data.get("complemento"),
                "bairro": cnpj_data.get("bairro"),
                "cidade": cnpj_data.get("municipio"),
                "estado": cnpj_data.get("uf"),
                "cep": cnpj_data.get("cep"),
                "fundadores": fundadores,
                "website": raw_data.get("website_url"),
                "telefone": cnpj_data.get("ddd_telefone_1"),
                "email": cnpj_data.get("email"),
                "porte": cnpj_data.get("porte"),
                "natureza_juridica": cnpj_data.get("natureza_juridica"),
                "situacao_cadastral": cnpj_data.get("descricao_situacao_cadastral"),
                "data_abertura": cnpj_data.get("data_inicio_atividade"),
                "capital_social": cnpj_data.get("capital_social"),
                "setor": raw_data.get("search_data", {}).get("industry"),
                "raw_cnpj_data": cnpj_data,
                "raw_search_data": raw_data.get("search_data", {})
            }

            empresa_id = await self.empresa_repo.upsert(empresa_data)
            persistence_result["empresa_id"] = empresa_id

            if not empresa_id:
                logger.warning("empresa_not_saved", name=name)
                return persistence_result

            # 3. Salvar pessoas em dim_pessoas
            employees = raw_data.get("employees", [])
            pessoas_salvas = await self._persist_employees(empresa_id, employees)
            persistence_result["pessoas_salvas"] = pessoas_salvas

            # 4. Extrair palavras-chave
            keywords_result = await self.keyword_extractor.extract_from_analysis(
                company_name=name,
                blocks=result.get("blocks", {})
            )
            persistence_result["palavras_chave"] = keywords_result.get("keywords", [])
            persistence_result["palavras_chave_por_bloco"] = keywords_result.get("keywords_by_block", {})
            persistence_result["search_queries"] = keywords_result.get("search_queries", [])

            # 4.1 Atualizar palavras-chave na dimensão empresa
            await self.empresa_repo.update_keywords(
                empresa_id,
                keywords_result.get("keywords", [])
            )

            # 5. Salvar análise em fato_analises_empresa
            analise_data = {
                **result,
                "palavras_chave": keywords_result.get("keywords", []),
                "palavras_chave_por_bloco": keywords_result.get("keywords_by_block", {}),
                "raw_data": {
                    "perplexity_research": raw_data.get("perplexity_research", {}),
                    "tavily_research": raw_data.get("tavily_research", {})
                }
            }

            analise_id = await self.analise_repo.save(empresa_id, analise_data)
            persistence_result["analise_id"] = analise_id

            logger.info(
                "persistence_complete",
                empresa_id=empresa_id,
                analise_id=analise_id,
                pessoas=pessoas_salvas,
                keywords=len(persistence_result["palavras_chave"])
            )

        except Exception as e:
            logger.error("persistence_error", error=str(e), company=name)

        return persistence_result

    async def _persist_employees(
        self,
        empresa_id: str,
        employees: List[Dict]
    ) -> int:
        """
        Persiste funcionários em dim_pessoas e fato_eventos_pessoa

        Returns:
            Número de pessoas salvas
        """
        saved_count = 0

        for emp in employees:
            try:
                # Salvar pessoa
                emp["empresa_atual_id"] = empresa_id
                pessoa_id = await self.pessoa_repo.upsert(emp)

                if not pessoa_id:
                    continue

                saved_count += 1

                # Salvar emprego atual como evento
                await self.evento_repo.save_emprego(
                    pessoa_id=pessoa_id,
                    emprego={
                        "title": emp.get("title"),
                        "organization_name": emp.get("organization_name"),
                        "is_current": True,
                        "start_date": emp.get("employment_start_date")
                    },
                    empresa_id=empresa_id
                )

                # Salvar histórico de empregos se disponível
                for exp in emp.get("employment_history", []):
                    await self.evento_repo.save_emprego(
                        pessoa_id=pessoa_id,
                        emprego=exp
                    )

                # Salvar educação se disponível
                for edu in emp.get("education", []):
                    await self.evento_repo.save_educacao(
                        pessoa_id=pessoa_id,
                        educacao=edu
                    )

            except Exception as e:
                logger.warning("employee_save_error", error=str(e), name=emp.get("name"))

        return saved_count

    def _extract_founders(self, raw_data: Dict) -> List[Dict]:
        """Extrai fundadores dos dados coletados"""
        founders = []

        # Buscar em QSA (Quadro Societário)
        cnpj_data = raw_data.get("cnpj_data", {})
        qsa = cnpj_data.get("qsa", [])

        for socio in qsa:
            qual = socio.get("qualificacao_socio", "").lower()
            # Identificar fundadores/sócios principais
            if any(term in qual for term in ["administrador", "socio", "diretor", "presidente"]):
                founders.append({
                    "nome": socio.get("nome_socio"),
                    "cargo": socio.get("qualificacao_socio"),
                    "data_entrada": socio.get("data_entrada_sociedade")
                })

        # Buscar em funcionários (C-level)
        employees = raw_data.get("employees", [])
        for emp in employees:
            title = (emp.get("title") or "").lower()
            if any(term in title for term in ["founder", "fundador", "ceo", "cto", "coo", "cfo", "owner"]):
                # Evitar duplicatas
                nome = emp.get("name")
                if nome and not any(f.get("nome") == nome for f in founders):
                    founders.append({
                        "nome": nome,
                        "cargo": emp.get("title"),
                        "linkedin_url": emp.get("linkedin_url")
                    })

        return founders[:10]  # Limitar a 10 fundadores

    # =========================================
    # FASE 8: BUSCA DE CONCORRENTES
    # =========================================

    async def _find_and_analyze_competitors(
        self,
        empresa_id: str,
        company_name: str,
        keywords: List[str],
        search_queries: List[str]
    ) -> List[Dict]:
        """
        Busca e analisa concorrentes baseado em palavras-chave

        Fluxo:
        1. Usa queries geradas para buscar no Perplexity
        2. Extrai nomes de empresas da resposta
        3. Para cada concorrente:
           - Busca dados básicos (sem análise completa para evitar loop)
           - Salva em dim_empresas
           - Salva relação em fato_concorrentes
        """
        competitors = []

        if not search_queries:
            logger.warning("no_search_queries", company=company_name)
            return competitors

        try:
            # Usar primeira query para buscar concorrentes
            query = search_queries[0]
            logger.info("searching_competitors", query=query)

            # Buscar no Perplexity
            perplexity_result = await self.perplexity.search(
                f"Liste 5 empresas brasileiras concorrentes ou similares a {company_name}. {query}. Retorne apenas os nomes das empresas."
            )

            if not perplexity_result:
                return competitors

            # Extrair nomes de concorrentes
            competitor_names = self._extract_competitor_names(
                perplexity_result.get("answer", "")
            )[:5]

            logger.info("competitors_found", count=len(competitor_names), names=competitor_names)

            # Analisar cada concorrente (versão simplificada)
            for comp_name in competitor_names:
                if comp_name.lower() == company_name.lower():
                    continue  # Pular a própria empresa

                try:
                    comp_data = await self._analyze_competitor_simple(
                        comp_name, keywords
                    )

                    if comp_data and comp_data.get("id"):
                        # Salvar relação de concorrência
                        await self.concorrente_repo.save(
                            empresa_id=empresa_id,
                            concorrente_id=comp_data["id"],
                            palavras_chave_match=comp_data.get("keywords_match", []),
                            score_similaridade=comp_data.get("similarity_score", 0.5),
                            stamp=comp_data.get("stamp", "Medio"),
                            stamp_justificativa=comp_data.get("stamp_justification", ""),
                            fonte_descoberta="perplexity",
                            query_utilizada=query
                        )

                        competitors.append(comp_data)

                except Exception as e:
                    logger.warning("competitor_analysis_error", competitor=comp_name, error=str(e))

        except Exception as e:
            logger.error("competitors_search_error", error=str(e))

        return competitors

    async def _analyze_competitor_simple(
        self,
        name: str,
        source_keywords: List[str]
    ) -> Optional[Dict]:
        """
        Análise simplificada de concorrente (sem recursão)

        Coleta apenas:
        - Dados básicos via Serper
        - CNPJ via BrasilAPI (se encontrar)
        - Avaliação de stamp via AI
        """
        try:
            # Buscar dados básicos
            search_result = await self.serper.find_company_info(name)

            if not search_result:
                return None

            # Tentar buscar CNPJ
            cnpj = await self.serper.find_company_cnpj(name)
            cnpj_data = {}

            if cnpj:
                import contextlib
                with contextlib.suppress(Exception):
                    cnpj_data = await self.brasil_api.get_cnpj(cnpj)

            # Preparar dados da empresa
            empresa_data = {
                "cnpj": cnpj,
                "nome_fantasia": name,
                "razao_social": cnpj_data.get("razao_social"),
                "website": search_result.get("website"),
                "setor": search_result.get("industry"),
                "cidade": cnpj_data.get("municipio"),
                "estado": cnpj_data.get("uf"),
                "raw_cnpj_data": cnpj_data,
                "raw_search_data": search_result
            }

            # Salvar concorrente
            concorrente_id = await self.empresa_repo.upsert(empresa_data)

            if not concorrente_id:
                return None

            # Calcular keywords match
            comp_description = (
                search_result.get("description", "") +
                " " +
                (search_result.get("industry") or "")
            ).lower()

            keywords_match = [
                kw for kw in source_keywords
                if kw.lower() in comp_description
            ]

            # Gerar stamp via AI
            stamp_result = await self.ai_analyzer.analyze_competitor_with_stamp(
                main_company=name,
                competitor_name=name,
                competitor_info=search_result,
                main_company_context=""
            )

            return {
                "id": concorrente_id,
                "name": name,
                "website": search_result.get("website"),
                "industry": search_result.get("industry"),
                "keywords_match": keywords_match,
                "similarity_score": len(keywords_match) / max(len(source_keywords), 1),
                "stamp": stamp_result.get("stamp", "Medio"),
                "stamp_justification": stamp_result.get("justification", "")
            }

        except Exception as e:
            logger.error("competitor_simple_analysis_error", name=name, error=str(e))
            return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
