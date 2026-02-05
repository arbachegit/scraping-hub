"""
People Intelligence Service
Inteligência sobre pessoas - funcionários, executivos, candidatos

VERSÃO 2.0 - Análise profunda com integração completa de todas as fontes
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from src.scrapers import ApolloClient, PerplexityClient, SerperClient, TavilyClient

from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class PeopleIntelService:
    """
    Serviço de inteligência sobre pessoas

    Funcionalidades:
    - Análise de perfil profissional COMPLETA
    - Busca de contatos/executivos
    - Análise de fit cultural
    - Histórico de carreira

    IMPORTANTE: Coleta TODOS os dados de TODAS as fontes e passa
    para análise profunda com Claude AI.
    """

    def __init__(self):
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.apollo = ApolloClient()
        self.ai_analyzer = AIAnalyzer()
        # Cache interno para compartilhar entre métodos
        self._cache: Dict[str, Any] = {}

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
        Análise COMPLETA e PROFUNDA de uma pessoa

        FLUXO:
        1. Coleta dados de TODAS as fontes em paralelo
        2. Pesquisa adicional focada (carreira, notícias, redes)
        3. Consolida TODOS os dados brutos em contexto rico
        4. Passa TUDO para Claude fazer análise profunda
        5. Retorna análise estruturada completa

        Args:
            name: Nome da pessoa
            company: Empresa atual
            role: Cargo atual
            linkedin_url: URL do LinkedIn
            analysis_type: "full", "quick", "fit"

        Returns:
            Perfil completo com análise profunda
        """
        logger.info(
            "people_intel_analyze_v2",
            name=name,
            company=company,
            type=analysis_type
        )

        result = {
            "name": name,
            "company": company,
            "role": role,
            "analysis_type": analysis_type,
            "status": "processing",
            "sources_used": []
        }

        try:
            # ============================================
            # FASE 1: COLETA MASSIVA DE DADOS EM PARALELO
            # ============================================

            # Primeiro, buscar LinkedIn se não fornecido
            if not linkedin_url:
                linkedin_url = await self.serper.find_person_linkedin(name, company)
            result["linkedin_url"] = linkedin_url

            # Construir query de busca enriquecida
            search_query = f"{name}"
            if company:
                search_query += f" {company}"
            if role:
                search_query += f" {role}"

            # Coletar TODAS as fontes em paralelo
            tasks = {
                # Buscas Google via Serper
                "serper_person": self.serper.find_person_info(name, company),
                "serper_career": self.serper.search(f'"{name}" carreira experiência profissional', num=10),
                "serper_news": self.serper.search_news(f'"{name}"', num=10),
                "serper_social": self.serper.search(f'"{name}" LinkedIn Instagram Twitter site:linkedin.com OR site:instagram.com OR site:twitter.com', num=10),

                # Pesquisa profunda Perplexity
                "perplexity_profile": self.perplexity.research_person(name, company, focus="complete"),
                "perplexity_career": self.perplexity.research(
                    f"Descreva em detalhes a carreira profissional de {name}" +
                    (f" da empresa {company}" if company else "") +
                    ". Inclua: formação, experiências anteriores, conquistas, projetos relevantes, especializações."
                ),

                # Pesquisa Tavily
                "tavily_research": self.tavily.research_person(name, company),
                "tavily_news": self.tavily.search(f'"{name}" notícias recentes', search_depth="advanced"),
            }

            # Apollo se tiver contexto
            if company or linkedin_url:
                tasks["apollo_data"] = self._get_apollo_data(name, company, linkedin_url)

            # Executar TUDO em paralelo
            task_names = list(tasks.keys())
            task_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            # Mapear resultados
            collected_data: Dict[str, Any] = {}
            for i, task_name in enumerate(task_names):
                if isinstance(task_results[i], Exception):
                    logger.warning(f"people_intel_{task_name}_error", error=str(task_results[i]))
                    collected_data[task_name] = {}
                else:
                    collected_data[task_name] = task_results[i]
                    if task_results[i]:
                        result["sources_used"].append(task_name)

            # Guardar dados brutos para referência
            result["raw_data"] = collected_data

            # ============================================
            # FASE 2: CONSOLIDAR DADOS BÁSICOS
            # ============================================

            profile = self._consolidate_basic_profile(
                collected_data, name, company, role, linkedin_url
            )
            result["profile"] = profile

            # ============================================
            # FASE 3: ANÁLISE PROFUNDA COM CLAUDE
            # ============================================

            if analysis_type == "quick":
                # Quick ainda faz uma análise, mas mais rápida
                quick_context = self._prepare_quick_context(collected_data, name, company)
                ai_analysis = await self.ai_analyzer.analyze_person_deep(
                    person_data=profile,
                    rich_context=quick_context,
                    analysis_depth="quick"
                )
            else:
                # ANÁLISE COMPLETA - passa TUDO para o Claude
                full_context = self._prepare_full_context(collected_data, name, company, role)
                ai_analysis = await self.ai_analyzer.analyze_person_deep(
                    person_data=profile,
                    rich_context=full_context,
                    analysis_depth="full"
                )

            result["ai_analysis"] = ai_analysis

            # ============================================
            # FASE 4: ESTRUTURAR RESULTADO FINAL
            # ============================================

            # Extrair análise estruturada
            if ai_analysis and not ai_analysis.get("error"):
                result["professional_summary"] = ai_analysis.get("professional_summary", "")
                result["career_analysis"] = ai_analysis.get("career_analysis", {})
                result["skills_assessment"] = ai_analysis.get("skills_assessment", [])
                result["strengths"] = ai_analysis.get("strengths", [])
                result["development_areas"] = ai_analysis.get("development_areas", [])
                result["notable_achievements"] = ai_analysis.get("notable_achievements", [])
                result["public_presence"] = ai_analysis.get("public_presence", {})
                result["insights"] = ai_analysis.get("key_insights", [])
                result["recommendations"] = ai_analysis.get("recommendations", [])

            result["status"] = "completed"

            # Cache para uso posterior
            cache_key = f"person:{name}:{company or ''}"
            self._cache[cache_key] = result

        except Exception as e:
            logger.error("people_intel_error", name=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _consolidate_basic_profile(
        self,
        data: Dict[str, Any],
        name: str,
        company: Optional[str],
        role: Optional[str],
        linkedin_url: Optional[str]
    ) -> Dict[str, Any]:
        """Consolida dados básicos do perfil de múltiplas fontes"""

        apollo = data.get("apollo_data", {})
        serper = data.get("serper_person", {})
        perplexity = data.get("perplexity_profile", {})

        # Knowledge graph do Google (se disponível)
        kg = serper.get("knowledge_graph", {})

        return {
            # Identificação
            "name": apollo.get("name") or name,
            "full_name": apollo.get("name") or kg.get("title", "").split(" - ")[0] or name,

            # Profissional - prioridade: Apollo > Perplexity > Serper
            "current_title": (
                apollo.get("title") or
                perplexity.get("title") or
                role or
                kg.get("occupation")
            ),
            "current_company": (
                apollo.get("company", {}).get("name") or
                perplexity.get("company") or
                company
            ),
            "headline": apollo.get("headline") or perplexity.get("headline"),
            "seniority": apollo.get("seniority"),
            "departments": apollo.get("departments", []),

            # Contato
            "email": apollo.get("email"),
            "phone": (apollo.get("phone_numbers") or [None])[0] if apollo.get("phone_numbers") else None,

            # Social
            "linkedin_url": linkedin_url or apollo.get("linkedin_url"),
            "twitter_url": apollo.get("twitter_url"),

            # Localização
            "city": apollo.get("city"),
            "state": apollo.get("state"),
            "country": apollo.get("country") or "Brasil",

            # Foto
            "photo_url": apollo.get("photo_url"),

            # Descrição do Knowledge Graph
            "description": kg.get("description"),
        }

    def _prepare_quick_context(
        self,
        data: Dict[str, Any],
        name: str,
        company: Optional[str]
    ) -> str:
        """Prepara contexto resumido para análise rápida"""

        context_parts = []

        # Perplexity profile summary
        perplexity = data.get("perplexity_profile", {})
        if perplexity.get("profile"):
            context_parts.append(f"## Perfil Profissional (Perplexity)\n{perplexity['profile']}")

        # Apollo data
        apollo = data.get("apollo_data", {})
        if apollo:
            apollo_info = f"""## Dados Apollo
- Nome: {apollo.get('name', 'N/A')}
- Cargo: {apollo.get('title', 'N/A')}
- Empresa: {apollo.get('company', {}).get('name', 'N/A')}
- Senioridade: {apollo.get('seniority', 'N/A')}
- Departamentos: {', '.join(apollo.get('departments', []))}
- Email: {apollo.get('email', 'N/A')}"""
            context_parts.append(apollo_info)

        # Knowledge graph
        kg = data.get("serper_person", {}).get("knowledge_graph", {})
        if kg:
            context_parts.append(f"## Knowledge Graph\n{kg.get('description', '')}")

        return "\n\n".join(context_parts)

    def _prepare_full_context(
        self,
        data: Dict[str, Any],
        name: str,
        company: Optional[str],
        role: Optional[str]
    ) -> str:
        """
        Prepara contexto COMPLETO e RICO para análise profunda

        Inclui TODOS os dados coletados de TODAS as fontes
        """

        context_parts = []

        context_parts.append(f"# ANÁLISE PROFUNDA: {name}")
        if company:
            context_parts.append(f"**Empresa referência:** {company}")
        if role:
            context_parts.append(f"**Cargo referência:** {role}")

        # ============================================
        # DADOS PERPLEXITY - Pesquisa profunda
        # ============================================

        perplexity_profile = data.get("perplexity_profile", {})
        perplexity_career = data.get("perplexity_career", {})

        if perplexity_profile.get("profile") or perplexity_career.get("answer"):
            context_parts.append("\n## PESQUISA PERPLEXITY (Fonte principal)")

            if perplexity_profile.get("profile"):
                context_parts.append(f"### Perfil Completo\n{perplexity_profile['profile']}")

            if perplexity_career.get("answer"):
                context_parts.append(f"### Análise de Carreira\n{perplexity_career['answer']}")

            # Citations
            citations = perplexity_profile.get("citations", []) + perplexity_career.get("citations", [])
            if citations:
                context_parts.append("### Fontes citadas\n" + "\n".join(f"- {c}" for c in citations[:10]))

        # ============================================
        # DADOS APOLLO - Dados profissionais estruturados
        # ============================================

        apollo = data.get("apollo_data", {})
        if apollo and any(apollo.values()):
            apollo_section = """
## DADOS APOLLO (Dados estruturados)
### Informações Profissionais
- **Nome completo:** {name}
- **Cargo atual:** {title}
- **Empresa:** {company}
- **Headline:** {headline}
- **Senioridade:** {seniority}
- **Departamentos:** {departments}

### Contato
- **Email:** {email}
- **Telefones:** {phones}

### Redes Sociais
- **LinkedIn:** {linkedin}
- **Twitter:** {twitter}

### Localização
- {city}, {state}, {country}
""".format(
                name=apollo.get("name", "N/A"),
                title=apollo.get("title", "N/A"),
                company=apollo.get("company", {}).get("name", "N/A") if isinstance(apollo.get("company"), dict) else apollo.get("company", "N/A"),
                headline=apollo.get("headline", "N/A"),
                seniority=apollo.get("seniority", "N/A"),
                departments=", ".join(apollo.get("departments", [])) or "N/A",
                email=apollo.get("email", "N/A"),
                phones=", ".join(apollo.get("phone_numbers", [])) if apollo.get("phone_numbers") else "N/A",
                linkedin=apollo.get("linkedin_url", "N/A"),
                twitter=apollo.get("twitter_url", "N/A"),
                city=apollo.get("city", ""),
                state=apollo.get("state", ""),
                country=apollo.get("country", "Brasil")
            )
            context_parts.append(apollo_section)

        # ============================================
        # DADOS SERPER - Google Search
        # ============================================

        # Knowledge Graph
        serper_person = data.get("serper_person", {})
        kg = serper_person.get("knowledge_graph", {})
        if kg:
            kg_section = f"""
## KNOWLEDGE GRAPH (Google)
- **Título:** {kg.get('title', 'N/A')}
- **Descrição:** {kg.get('description', 'N/A')}
- **Tipo:** {kg.get('type', 'N/A')}
"""
            if kg.get("attributes"):
                kg_section += "\n### Atributos:\n"
                for key, value in kg.get("attributes", {}).items():
                    kg_section += f"- **{key}:** {value}\n"
            context_parts.append(kg_section)

        # Resultados orgânicos de carreira
        serper_career = data.get("serper_career", {})
        organic_career = serper_career.get("organic", [])
        if organic_career:
            context_parts.append("\n## RESULTADOS GOOGLE - CARREIRA")
            for item in organic_career[:8]:
                context_parts.append(f"### {item.get('title', 'N/A')}")
                context_parts.append(f"- **Link:** {item.get('link', '')}")
                context_parts.append(f"- **Snippet:** {item.get('snippet', '')}")

        # Perfis sociais encontrados
        serper_social = data.get("serper_social", {})
        social_results = serper_social.get("organic", [])
        if social_results:
            context_parts.append("\n## PERFIS EM REDES SOCIAIS ENCONTRADOS")
            for item in social_results[:6]:
                context_parts.append(f"- **{item.get('title', '')}:** {item.get('link', '')}")
                if item.get('snippet'):
                    context_parts.append(f"  {item.get('snippet', '')}")

        # ============================================
        # DADOS TAVILY - Pesquisa avançada
        # ============================================

        tavily_research = data.get("tavily_research", {})
        if tavily_research.get("answer") or tavily_research.get("results"):
            context_parts.append("\n## PESQUISA TAVILY")

            if tavily_research.get("answer"):
                context_parts.append(f"### Síntese\n{tavily_research['answer']}")

            for res in tavily_research.get("results", [])[:5]:
                context_parts.append(f"### {res.get('title', 'N/A')}")
                context_parts.append(f"- **URL:** {res.get('url', '')}")
                context_parts.append(f"- **Conteúdo:** {res.get('content', '')[:500]}")

        # ============================================
        # NOTÍCIAS
        # ============================================

        serper_news = data.get("serper_news", {})
        news_items = serper_news.get("news", [])

        tavily_news = data.get("tavily_news", {})
        tavily_news_items = tavily_news.get("results", [])

        if news_items or tavily_news_items:
            context_parts.append("\n## NOTÍCIAS E MENÇÕES NA MÍDIA")

            for news in news_items[:5]:
                context_parts.append(f"### {news.get('title', 'N/A')}")
                context_parts.append(f"- **Fonte:** {news.get('source', 'N/A')}")
                context_parts.append(f"- **Data:** {news.get('date', 'N/A')}")
                context_parts.append(f"- **Snippet:** {news.get('snippet', '')}")

            for news in tavily_news_items[:3]:
                context_parts.append(f"### {news.get('title', 'N/A')}")
                context_parts.append(f"- **URL:** {news.get('url', '')}")
                context_parts.append(f"- **Conteúdo:** {news.get('content', '')[:400]}")

        full_context = "\n".join(context_parts)

        # Limitar tamanho mas manter o máximo possível
        return full_context[:25000]

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

            # Senão, buscar pelo nome completo
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
        Busca rápida de pessoa - mas AINDA com análise AI

        A quick lookup agora também passa por análise Claude,
        apenas com menos fontes e análise mais rápida.

        Args:
            name: Nome da pessoa
            company: Empresa (opcional)

        Returns:
            Perfil enriquecido com análise AI
        """
        logger.info("people_intel_quick_v2", name=name)

        # Buscar fontes essenciais em paralelo
        tasks = {
            "linkedin": self.serper.find_person_linkedin(name, company),
            "serper_info": self.serper.find_person_info(name, company),
            "perplexity": self.perplexity.research_person(name, company, focus="professional"),
            "tavily": self.tavily.research_person(name, company)
        }

        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Mapear resultados
        collected = {}
        for i, name_key in enumerate(task_names):
            if isinstance(results[i], Exception):
                collected[name_key] = {} if name_key != "linkedin" else None
            else:
                collected[name_key] = results[i]

        linkedin = collected.get("linkedin")
        search_info = collected.get("serper_info", {})
        research = collected.get("perplexity", {})
        tavily_data = collected.get("tavily", {})

        # Buscar via Apollo com LinkedIn encontrado
        apollo_data = await self._get_apollo_data(name, company, linkedin)

        # Construir perfil combinando fontes
        kg = search_info.get("knowledge_graph", {})

        profile = {
            "name": apollo_data.get("name") or name,
            "company": apollo_data.get("company", {}).get("name") if isinstance(apollo_data.get("company"), dict) else company,
            "title": apollo_data.get("title") or kg.get("occupation"),
            "headline": apollo_data.get("headline"),
            "linkedin_url": linkedin or apollo_data.get("linkedin_url"),
            "email": apollo_data.get("email"),
            "phone": apollo_data.get("phone_numbers", [None])[0] if apollo_data.get("phone_numbers") else None,
            "photo_url": apollo_data.get("photo_url"),
            "city": apollo_data.get("city"),
            "state": apollo_data.get("state"),
            "country": apollo_data.get("country") or "Brasil",
            "location": f"{apollo_data.get('city', '')}, {apollo_data.get('state', '')}".strip(", "),
            "seniority": apollo_data.get("seniority"),
            "departments": apollo_data.get("departments", []),
            "twitter_url": apollo_data.get("twitter_url"),
            "description": kg.get("description"),
            "sources": []
        }

        # Registrar fontes usadas
        sources_used = []
        if apollo_data and any(apollo_data.values()):
            sources_used.append("Apollo.io")
        if search_info:
            sources_used.append("Google Search")
        if research.get("profile"):
            sources_used.append("Perplexity AI")
        if tavily_data:
            sources_used.append("Tavily")
        profile["sources"] = sources_used

        # Preparar contexto para análise AI rápida
        context_parts = []

        if research.get("profile"):
            context_parts.append(f"## Perfil Perplexity\n{research['profile']}")

        if tavily_data.get("answer"):
            context_parts.append(f"## Pesquisa Tavily\n{tavily_data['answer']}")

        if kg:
            context_parts.append(f"## Knowledge Graph\n{kg.get('description', '')}")

        if apollo_data:
            context_parts.append(f"""## Dados Apollo
- Cargo: {apollo_data.get('title', 'N/A')}
- Empresa: {apollo_data.get('company', {}).get('name', 'N/A') if isinstance(apollo_data.get('company'), dict) else 'N/A'}
- Senioridade: {apollo_data.get('seniority', 'N/A')}
- Headline: {apollo_data.get('headline', 'N/A')}""")

        quick_context = "\n\n".join(context_parts)

        # Análise AI rápida
        if quick_context:
            ai_analysis = await self.ai_analyzer.analyze_person_deep(
                person_data=profile,
                rich_context=quick_context,
                analysis_depth="quick"
            )

            if ai_analysis and not ai_analysis.get("error"):
                profile["professional_summary"] = ai_analysis.get("professional_summary", "")
                profile["key_insights"] = ai_analysis.get("key_insights", [])
                profile["strengths"] = ai_analysis.get("strengths", [])

        return profile

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
