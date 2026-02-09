"""
Politician Intelligence Service
Inteligência sobre políticos - perfil pessoal (não político)

VERSÃO 2.0 - Análise profunda com integração completa de todas as fontes
"""

import asyncio
import contextlib
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

    VERSÃO 2.0: Coleta TODOS os dados de TODAS as fontes
    e passa para análise profunda com Claude AI.

    PERSISTÊNCIA: Todas as análises são salvas no banco de dados.
    """

    def __init__(self):
        self.serper = SerperClient()
        self.tavily = TavilyClient()
        self.perplexity = PerplexityClient()
        self.ai_analyzer = AIAnalyzer()
        # Cache interno
        self._cache: Dict[str, Any] = {}

        # Repository para persistência
        try:
            from src.database import PoliticianRepository, SearchHistoryRepository

            self.repository = PoliticianRepository()
            self.search_history = SearchHistoryRepository()
        except Exception:
            self.repository = None
            self.search_history = None

    async def close(self):
        """Fecha todos os clientes"""
        await asyncio.gather(
            self.serper.close(),
            self.tavily.close(),
            self.perplexity.close(),
            self.ai_analyzer.close(),
        )

    async def analyze_politician(
        self,
        name: str,
        role: Optional[str] = None,
        state: Optional[str] = None,
        focus: str = "personal",
    ) -> Dict[str, Any]:
        """
        Análise COMPLETA e PROFUNDA de perfil pessoal de um político

        FLUXO:
        1. Coleta dados de TODAS as fontes em paralelo
        2. Pesquisa adicional focada (biografia, carreira, percepção)
        3. Consolida TODOS os dados brutos em contexto rico
        4. Passa TUDO para Claude fazer análise profunda
        5. Retorna análise estruturada completa

        Args:
            name: Nome do político
            role: Cargo (prefeito, senador, deputado, etc)
            state: Estado
            focus: "personal", "career", "public_perception"

        Returns:
            Perfil completo com análise profunda
        """
        logger.info("politician_intel_analyze_v2", name=name, role=role, state=state, focus=focus)

        result = {
            "name": name,
            "role": role,
            "state": state,
            "focus": focus,
            "status": "processing",
            "sources_used": [],
        }

        try:
            # ============================================
            # FASE 1: COLETA MASSIVA DE DADOS EM PARALELO
            # ============================================

            # Construir queries de busca
            base_query = f'"{name}"'
            if role:
                base_query += f" {role}"
            if state:
                base_query += f" {state}"

            # Coletar TODAS as fontes em paralelo
            tasks = {
                # Buscas Google via Serper
                "serper_info": self.serper.find_politician_info(name, role, state),
                "serper_bio": self.serper.search(
                    f"{base_query} biografia história pessoal família", num=10
                ),
                "serper_career": self.serper.search(
                    f"{base_query} carreira formação profissão antes política", num=10
                ),
                "serper_news": self.serper.search_news(f"{base_query}", num=15),
                "serper_social": self.serper.search(
                    f"{base_query} Instagram Twitter Facebook site:instagram.com OR site:twitter.com OR site:facebook.com",
                    num=10,
                ),
                "serper_interviews": self.serper.search(
                    f"{base_query} entrevista podcast programa", num=8
                ),
                # Pesquisa profunda Perplexity
                "perplexity_profile": self.perplexity.research_politician(name, role, state, focus),
                "perplexity_bio": self.perplexity.research(
                    f"Descreva a biografia completa de {name}"
                    + (f" ({role})" if role else "")
                    + (f" de {state}" if state else "")
                    + ". Inclua: nascimento, família, infância, formação acadêmica, carreira profissional ANTES da política, vida pessoal, hobbies e interesses."
                ),
                "perplexity_perception": self.perplexity.research(
                    f"Qual é a percepção pública atual sobre {name}"
                    + (f" ({role})" if role else "")
                    + "? Analise: imagem pública, pontos positivos e negativos na visão da população, controvérsias conhecidas, estilo de comunicação."
                ),
                # Pesquisa Tavily
                "tavily_research": self.tavily.research_politician(name, role, state),
                "tavily_news": self.tavily.search(
                    f"{base_query} notícias recentes", search_depth="advanced"
                ),
            }

            # Executar TUDO em paralelo
            task_names = list(tasks.keys())
            task_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            # Mapear resultados
            collected_data: Dict[str, Any] = {}
            for i, task_name in enumerate(task_names):
                if isinstance(task_results[i], Exception):
                    logger.warning(
                        f"politician_intel_{task_name}_error", error=str(task_results[i])
                    )
                    collected_data[task_name] = {}
                else:
                    collected_data[task_name] = task_results[i]
                    if task_results[i]:
                        result["sources_used"].append(task_name)

            # Guardar dados brutos
            result["raw_data"] = collected_data

            # ============================================
            # FASE 2: BUSCAR REDES SOCIAIS ESPECIFICAMENTE
            # ============================================

            social_media = await self._extract_social_media(collected_data, name, role)
            result["social_media"] = social_media

            # ============================================
            # FASE 3: CONSOLIDAR DADOS BÁSICOS
            # ============================================

            profile = self._consolidate_basic_profile(collected_data, name, role, state)
            profile["social_media"] = social_media
            result["profile"] = profile

            # ============================================
            # FASE 4: ANÁLISE PROFUNDA COM CLAUDE
            # ============================================

            # Preparar contexto COMPLETO com TODOS os dados
            full_context = self._prepare_full_context(collected_data, name, role, state)

            # Análise profunda
            ai_analysis = await self.ai_analyzer.analyze_politician_deep(
                politician_data=profile, rich_context=full_context, focus=focus
            )

            result["ai_analysis"] = ai_analysis

            # ============================================
            # FASE 5: ESTRUTURAR RESULTADO FINAL
            # ============================================

            if ai_analysis and not ai_analysis.get("error"):
                result["personal_summary"] = ai_analysis.get("personal_summary", "")
                result["biography"] = ai_analysis.get("biography", {})
                result["public_perception"] = ai_analysis.get("public_perception", {})
                result["communication_style"] = ai_analysis.get("communication_style", "")
                result["key_characteristics"] = ai_analysis.get("key_characteristics", [])
                result["controversies"] = ai_analysis.get("controversies", [])
                result["media_presence"] = ai_analysis.get("media_presence", {})
                result["insights"] = ai_analysis.get("key_insights", [])

            result["status"] = "completed"

            # Cache
            cache_key = f"politician:{name}:{role or ''}:{state or ''}"
            self._cache[cache_key] = result

            # ============================================
            # FASE 6: SALVAR NO BANCO DE DADOS
            # ============================================
            if self.repository:
                try:
                    # Preparar dados para salvar
                    save_data = {
                        "name": name,
                        "role": role,
                        "state": state,
                        "personal_summary": result.get("personal_summary"),
                        **profile,
                        **social_media,
                    }

                    # Salvar político
                    politician_id = await self.repository.save_politician(save_data)
                    result["politician_id"] = politician_id

                    # Salvar análise
                    if politician_id and ai_analysis:
                        await self.repository.save_analysis(politician_id, result)

                    logger.info("politician_saved_to_db", name=name, id=politician_id)
                except Exception as db_error:
                    logger.warning("politician_db_save_error", error=str(db_error))

            # Salvar histórico de busca
            if self.search_history:
                with contextlib.suppress(Exception):
                    await self.search_history.save_search(
                        search_type="politician_analysis",
                        query={"name": name, "role": role, "state": state, "focus": focus},
                        results_count=1,
                        result_ids=[result.get("politician_id")],
                    )

        except Exception as e:
            logger.error("politician_intel_error", name=name, error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _consolidate_basic_profile(
        self, data: Dict[str, Any], name: str, role: Optional[str], state: Optional[str]
    ) -> Dict[str, Any]:
        """Consolida dados básicos do perfil"""

        serper_info = data.get("serper_info", {})

        # Knowledge graph do Google
        kg = serper_info.get("knowledge_graph", {})

        return {
            "name": name,
            "role": role,
            "state": state,
            "title": kg.get("title") or kg.get("occupation"),
            "description": kg.get("description"),
            "image": kg.get("image"),
            "born": kg.get("born"),
            "party": kg.get("party") or kg.get("political_party"),
            "education": kg.get("education"),
            "office": kg.get("office"),
        }

    async def _extract_social_media(
        self, data: Dict[str, Any], name: str, role: Optional[str]
    ) -> Dict[str, Any]:
        """Extrai perfis de redes sociais dos resultados"""

        social = {}
        serper_social = data.get("serper_social", {})

        platforms = {
            "instagram": ["instagram.com"],
            "twitter": ["twitter.com", "x.com"],
            "facebook": ["facebook.com"],
            "youtube": ["youtube.com"],
            "tiktok": ["tiktok.com"],
        }

        for item in serper_social.get("organic", []):
            url = item.get("link", "").lower()
            for platform, domains in platforms.items():
                if platform not in social:
                    for domain in domains:
                        if domain in url:
                            social[platform] = {
                                "url": item.get("link"),
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                            }
                            break

        return social

    def _prepare_full_context(
        self, data: Dict[str, Any], name: str, role: Optional[str], state: Optional[str]
    ) -> str:
        """
        Prepara contexto COMPLETO e RICO para análise profunda

        Inclui TODOS os dados coletados de TODAS as fontes
        """

        context_parts = []

        context_parts.append(f"# ANÁLISE PROFUNDA: {name}")
        if role:
            context_parts.append(f"**Cargo:** {role}")
        if state:
            context_parts.append(f"**Estado:** {state}")

        # ============================================
        # DADOS PERPLEXITY - Pesquisa profunda
        # ============================================

        perplexity_profile = data.get("perplexity_profile", {})
        perplexity_bio = data.get("perplexity_bio", {})
        perplexity_perception = data.get("perplexity_perception", {})

        if any(
            [
                perplexity_profile.get("profile"),
                perplexity_bio.get("answer"),
                perplexity_perception.get("answer"),
            ]
        ):
            context_parts.append("\n## PESQUISA PERPLEXITY (Fonte principal)")

            if perplexity_profile.get("profile"):
                context_parts.append(f"### Perfil Geral\n{perplexity_profile['profile']}")

            if perplexity_bio.get("answer"):
                context_parts.append(f"### Biografia Pessoal\n{perplexity_bio['answer']}")

            if perplexity_perception.get("answer"):
                context_parts.append(f"### Percepção Pública\n{perplexity_perception['answer']}")

            # Citations
            all_citations = (
                perplexity_profile.get("citations", [])
                + perplexity_bio.get("citations", [])
                + perplexity_perception.get("citations", [])
            )
            if all_citations:
                unique_citations = list(set(all_citations))[:15]
                context_parts.append(
                    "### Fontes citadas\n" + "\n".join(f"- {c}" for c in unique_citations)
                )

        # ============================================
        # DADOS SERPER - Knowledge Graph
        # ============================================

        serper_info = data.get("serper_info", {})
        kg = serper_info.get("knowledge_graph", {})

        if kg:
            kg_section = f"""
## KNOWLEDGE GRAPH (Google)
- **Nome:** {kg.get("title", "N/A")}
- **Descrição:** {kg.get("description", "N/A")}
- **Nascimento:** {kg.get("born", "N/A")}
- **Partido:** {kg.get("party", "N/A")}
- **Cargo:** {kg.get("office", "N/A")}
- **Educação:** {kg.get("education", "N/A")}
"""
            if kg.get("attributes"):
                kg_section += "\n### Atributos adicionais:\n"
                for key, value in kg.get("attributes", {}).items():
                    kg_section += f"- **{key}:** {value}\n"
            context_parts.append(kg_section)

        # ============================================
        # DADOS SERPER - Resultados de busca
        # ============================================

        # Biografia
        serper_bio = data.get("serper_bio", {})
        bio_results = serper_bio.get("organic", [])
        if bio_results:
            context_parts.append("\n## RESULTADOS GOOGLE - BIOGRAFIA")
            for item in bio_results[:6]:
                context_parts.append(f"### {item.get('title', 'N/A')}")
                context_parts.append(f"- **Link:** {item.get('link', '')}")
                context_parts.append(f"- **Snippet:** {item.get('snippet', '')}")

        # Carreira
        serper_career = data.get("serper_career", {})
        career_results = serper_career.get("organic", [])
        if career_results:
            context_parts.append("\n## RESULTADOS GOOGLE - CARREIRA")
            for item in career_results[:6]:
                context_parts.append(f"### {item.get('title', 'N/A')}")
                context_parts.append(f"- **Link:** {item.get('link', '')}")
                context_parts.append(f"- **Snippet:** {item.get('snippet', '')}")

        # Entrevistas
        serper_interviews = data.get("serper_interviews", {})
        interview_results = serper_interviews.get("organic", [])
        if interview_results:
            context_parts.append("\n## ENTREVISTAS E APARIÇÕES")
            for item in interview_results[:5]:
                context_parts.append(f"- **{item.get('title', '')}:** {item.get('link', '')}")
                if item.get("snippet"):
                    context_parts.append(f"  {item.get('snippet', '')}")

        # Redes sociais encontradas
        serper_social = data.get("serper_social", {})
        social_results = serper_social.get("organic", [])
        if social_results:
            context_parts.append("\n## PERFIS EM REDES SOCIAIS")
            for item in social_results[:8]:
                context_parts.append(f"- **{item.get('title', '')}:** {item.get('link', '')}")

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

            for news in news_items[:8]:
                context_parts.append(f"### {news.get('title', 'N/A')}")
                context_parts.append(f"- **Fonte:** {news.get('source', 'N/A')}")
                context_parts.append(f"- **Data:** {news.get('date', 'N/A')}")
                context_parts.append(f"- **Snippet:** {news.get('snippet', '')}")

            for news in tavily_news_items[:4]:
                context_parts.append(f"### {news.get('title', 'N/A')}")
                context_parts.append(f"- **URL:** {news.get('url', '')}")
                context_parts.append(f"- **Conteúdo:** {news.get('content', '')[:400]}")

        full_context = "\n".join(context_parts)

        # Limitar tamanho mas manter o máximo possível
        return full_context[:25000]

    async def get_public_perception(
        self, name: str, role: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Analisa percepção pública com análise AI

        Args:
            name: Nome do político
            role: Cargo
            days: Dias para análise

        Returns:
            Análise de percepção pública
        """
        logger.info("politician_intel_perception_v2", name=name)

        # Buscar notícias e percepção em paralelo
        tasks = {
            "tavily_news": self.tavily.search_news(
                f'"{name}"' + (f" {role}" if role else ""), max_results=20, days=days
            ),
            "perplexity_perception": self.perplexity.research(
                f"Qual é a percepção pública atual sobre {name} {'(' + role + ')' if role else ''}? "
                "Analise: imagem pública positiva e negativa, controvérsias recentes, tendências de opinião."
            ),
            "serper_news": self.serper.search_news(f'"{name}"', num=15),
        }

        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        collected = {}
        for i, name_key in enumerate(task_names):
            collected[name_key] = results[i] if not isinstance(results[i], Exception) else {}

        # Análise de sentimento das notícias
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        all_news = collected.get("tavily_news", {}).get("results", []) + collected.get(
            "serper_news", {}
        ).get("news", [])

        for item in all_news:
            content = item.get("content", "") or item.get("snippet", "")
            sentiment = self._analyze_sentiment(content)
            sentiments[sentiment] += 1

        # Preparar contexto para análise AI
        context = f"""## Percepção Pública - {name}

### Pesquisa Perplexity
{collected.get("perplexity_perception", {}).get("answer", "N/A")}

### Notícias ({len(all_news)} encontradas)
Sentimentos: {sentiments}

Amostra de notícias:
"""
        for news in all_news[:10]:
            title = news.get("title", "")
            content = news.get("content", "") or news.get("snippet", "")
            context += f"\n- {title}: {content[:200]}"

        # Análise AI
        ai_analysis = await self.ai_analyzer.analyze_perception_deep(
            name=name, role=role, context=context, sentiments=sentiments
        )

        return {
            "name": name,
            "role": role,
            "analysis_period_days": days,
            "news_sentiment": sentiments,
            "total_news": len(all_news),
            "perception_analysis": collected.get("perplexity_perception", {}).get("answer"),
            "ai_analysis": ai_analysis,
            "sample_news": all_news[:8],
            "citations": collected.get("perplexity_perception", {}).get("citations", []),
        }

    def _analyze_sentiment(self, text: str) -> str:
        """Análise de sentimento básica"""
        text_lower = text.lower()

        positive_words = [
            "sucesso",
            "aprovação",
            "conquista",
            "vitória",
            "elogio",
            "popular",
            "apoio",
            "reconhecimento",
            "destaque",
            "positivo",
            "avanço",
            "melhoria",
            "crescimento",
        ]

        negative_words = [
            "crise",
            "crítica",
            "polêmica",
            "escândalo",
            "denúncia",
            "investigação",
            "rejeição",
            "protesto",
            "negativo",
            "problema",
            "falha",
            "erro",
            "corrupção",
            "acusação",
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    async def quick_lookup(self, name: str, role: Optional[str] = None) -> Dict[str, Any]:
        """
        Busca rápida de político - AINDA com análise AI

        Args:
            name: Nome do político
            role: Cargo

        Returns:
            Perfil enriquecido com análise AI
        """
        logger.info("politician_intel_quick_v2", name=name)

        # Buscar fontes essenciais em paralelo
        search_query = f'"{name}" {role or ""} político Brasil'

        tasks = {
            "serper": self.serper.search(search_query, num=10),
            "perplexity": self.perplexity.research(
                f"Quem é {name}{' (' + role + ')' if role else ''}? "
                "Forneça informações pessoais: cargo atual, estado, formação acadêmica, "
                "carreira antes da política, família, idade, cidade natal."
            ),
            "tavily": self.tavily.search(search_query, search_depth="basic"),
            "news": self.serper.search_news(f'"{name}"', num=5),
        }

        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        collected = {}
        for i, name_key in enumerate(task_names):
            collected[name_key] = results[i] if not isinstance(results[i], Exception) else {}

        # Extrair redes sociais
        social_media = {}
        for item in collected.get("serper", {}).get("organic", []):
            url = item.get("link", "").lower()
            if "instagram.com" in url and "instagram" not in social_media:
                social_media["instagram"] = {"url": item.get("link"), "title": item.get("title")}
            elif ("twitter.com" in url or "x.com" in url) and "twitter" not in social_media:
                social_media["twitter"] = {"url": item.get("link"), "title": item.get("title")}
            elif "facebook.com" in url and "facebook" not in social_media:
                social_media["facebook"] = {"url": item.get("link"), "title": item.get("title")}

        # Knowledge graph
        kg = collected.get("serper", {}).get("knowledge_graph", {}) or {}

        # Preparar contexto para análise AI rápida
        context_parts = []

        perplexity_answer = collected.get("perplexity", {}).get("answer", "")
        if perplexity_answer:
            context_parts.append(f"## Pesquisa Perplexity\n{perplexity_answer}")

        if kg:
            context_parts.append(f"""## Knowledge Graph
- Descrição: {kg.get("description", "N/A")}
- Nascimento: {kg.get("born", "N/A")}
- Partido: {kg.get("party", "N/A")}
- Educação: {kg.get("education", "N/A")}""")

        tavily_answer = collected.get("tavily", {}).get("answer", "")
        if tavily_answer:
            context_parts.append(f"## Pesquisa Tavily\n{tavily_answer}")

        quick_context = "\n\n".join(context_parts)

        # Análise AI rápida
        ai_analysis = {}
        if quick_context:
            ai_analysis = await self.ai_analyzer.analyze_politician_quick(
                name=name, role=role, context=quick_context
            )

        return {
            "name": name,
            "role": role,
            "description": kg.get("description") or perplexity_answer[:500]
            if perplexity_answer
            else None,
            "social_media": social_media,
            "knowledge_graph": kg,
            "research_summary": perplexity_answer,
            "ai_analysis": ai_analysis,
            "personal_summary": ai_analysis.get("personal_summary", ""),
            "key_facts": ai_analysis.get("key_facts", []),
            "recent_news": collected.get("news", {}).get("news", [])[:5],
            "citations": collected.get("perplexity", {}).get("citations", []),
            "sources": ["Serper", "Perplexity", "Tavily"],
        }

    async def get_personal_history(self, name: str, role: Optional[str] = None) -> Dict[str, Any]:
        """
        Busca histórico pessoal (não político) com análise profunda
        """
        logger.info("politician_intel_history_v2", name=name)

        # Pesquisar biografia em paralelo
        tasks = {
            "perplexity_bio": self.perplexity.research(
                f"Qual é a biografia PESSOAL completa de {name}? "
                "Inclua: data e local de nascimento, família (pais, cônjuge, filhos), "
                "infância, educação (escolas, universidades, cursos), "
                "carreira profissional ANTES da política, "
                "hobbies e interesses, curiosidades pessoais. "
                "NÃO inclua informações sobre posições políticas ou mandatos."
            ),
            "serper_bio": self.serper.search(
                f'"{name}" biografia nascimento família formação', num=10
            ),
            "serper_education": self.serper.search(
                f'"{name}" formação educação universidade escola', num=5
            ),
            "serper_career": self.serper.search(
                f'"{name}" carreira profissional antes política trabalhou empresa', num=5
            ),
        }

        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        collected = {}
        for i, name_key in enumerate(task_names):
            collected[name_key] = results[i] if not isinstance(results[i], Exception) else {}

        # Contexto para análise
        context = f"""## Biografia Perplexity
{collected.get("perplexity_bio", {}).get("answer", "N/A")}

## Resultados de Busca - Biografia
"""
        for item in collected.get("serper_bio", {}).get("organic", [])[:5]:
            context += f"\n- {item.get('title')}: {item.get('snippet')}"

        context += "\n\n## Resultados de Busca - Educação\n"
        for item in collected.get("serper_education", {}).get("organic", [])[:3]:
            context += f"\n- {item.get('title')}: {item.get('snippet')}"

        context += "\n\n## Resultados de Busca - Carreira\n"
        for item in collected.get("serper_career", {}).get("organic", [])[:3]:
            context += f"\n- {item.get('title')}: {item.get('snippet')}"

        # Análise AI
        ai_analysis = await self.ai_analyzer.analyze_biography_deep(
            name=name, role=role, context=context
        )

        return {
            "name": name,
            "role": role,
            "biography": collected.get("perplexity_bio", {}).get("answer"),
            "ai_analysis": ai_analysis,
            "structured_bio": ai_analysis.get("structured_biography", {}),
            "education_sources": collected.get("serper_education", {}).get("organic", []),
            "career_sources": collected.get("serper_career", {}).get("organic", []),
            "citations": collected.get("perplexity_bio", {}).get("citations", []),
        }

    async def get_media_presence(self, name: str, role: Optional[str] = None) -> Dict[str, Any]:
        """Analisa presença na mídia com análise AI"""
        logger.info("politician_intel_media_v2", name=name)

        # Buscar em paralelo
        tasks = {
            "social_search": self.serper.search(
                f'"{name}" Instagram Twitter Facebook site:instagram.com OR site:twitter.com OR site:facebook.com',
                num=15,
            ),
            "news": self.serper.search_news(f'"{name}"', num=20),
            "interviews": self.serper.search(
                f'"{name}" entrevista podcast programa televisão', num=10
            ),
            "youtube": self.serper.search(f'"{name}" site:youtube.com', num=8),
        }

        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        collected = {}
        for i, name_key in enumerate(task_names):
            collected[name_key] = results[i] if not isinstance(results[i], Exception) else {}

        # Extrair redes sociais
        social_media = {}
        platforms = {
            "instagram": ["instagram.com"],
            "twitter": ["twitter.com", "x.com"],
            "facebook": ["facebook.com"],
            "youtube": ["youtube.com"],
            "tiktok": ["tiktok.com"],
        }

        for item in collected.get("social_search", {}).get("organic", []):
            url = item.get("link", "").lower()
            for platform, domains in platforms.items():
                if platform not in social_media:
                    for domain in domains:
                        if domain in url:
                            social_media[platform] = {
                                "url": item.get("link"),
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                            }
                            break

        return {
            "name": name,
            "social_media": social_media,
            "social_platforms_found": list(social_media.keys()),
            "media_mentions": {
                "count": len(collected.get("news", {}).get("news", [])),
                "recent": collected.get("news", {}).get("news", [])[:10],
            },
            "interviews": collected.get("interviews", {}).get("organic", []),
            "youtube_presence": collected.get("youtube", {}).get("organic", []),
        }

    async def search_politicians(
        self,
        role: Optional[str] = None,
        state: Optional[str] = None,
        party: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Busca políticos por critérios"""
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
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            import re

            name_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
            matches = re.findall(name_pattern, title + " " + snippet)

            for found_name in matches:
                if found_name not in seen_names and len(found_name) > 5:
                    seen_names.add(found_name)
                    politicians.append(
                        {"name": found_name, "source": item.get("link"), "context": snippet[:200]}
                    )
                    if len(politicians) >= limit:
                        break
            if len(politicians) >= limit:
                break

        return {
            "search_criteria": {"role": role, "state": state, "party": party},
            "politicians": politicians,
            "total": len(politicians),
        }

    async def monitor_politician(
        self, name: str, role: Optional[str] = None, alert_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Monitora político para alertas"""
        logger.info("politician_intel_monitor", name=name)

        if alert_keywords is None:
            alert_keywords = [
                "polêmica",
                "escândalo",
                "denúncia",
                "investigação",
                "crítica",
                "protesto",
                "processo",
                "corrupção",
            ]

        news = await self.serper.search_news(f'"{name}"', num=20, tbs="qdr:d")

        alerts = []
        for item in news.get("news", []):
            text = (item.get("title", "") + " " + item.get("snippet", "")).lower()
            for keyword in alert_keywords:
                if keyword.lower() in text:
                    alerts.append(
                        {
                            "keyword": keyword,
                            "news": {
                                "title": item.get("title"),
                                "link": item.get("link"),
                                "source": item.get("source"),
                            },
                            "severity": "high"
                            if keyword in ["escândalo", "denúncia", "investigação", "corrupção"]
                            else "medium",
                        }
                    )
                    break

        return {
            "name": name,
            "role": role,
            "monitoring_period": "24h",
            "news_count": len(news.get("news", [])),
            "alerts": alerts,
            "alert_count": len(alerts),
            "has_critical_alerts": any(a.get("severity") == "high" for a in alerts),
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
