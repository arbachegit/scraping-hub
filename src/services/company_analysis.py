"""
Company Analysis Service - 11 Blocos
Análise completa de empresas com 11 blocos temáticos
"""

import asyncio
from datetime import datetime
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
        self.brasil_api = BrasilAPIClient()
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.web_scraper = WebScraperClient()
        self.ai_analyzer = AIAnalyzer()

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

        # Buscar executivos separadamente se necessário
        if len(data["employees"]) < 5:
            try:
                executives = await self.apollo.get_executives(
                    organization_name=name,
                    domain=domain
                )
                existing_ids = {e.get("id") for e in data["employees"]}
                for exec_data in executives.get("employees", []):
                    if exec_data.get("id") not in existing_ids:
                        data["employees"].append(exec_data)
            except Exception as e:
                logger.warning("executives_fetch_error", error=str(e))

        data["cnpj"] = cnpj
        data["name"] = name
        data["website_url"] = website_url

        return data

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

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
