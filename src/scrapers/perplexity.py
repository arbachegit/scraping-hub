"""
Perplexity Client
AI-powered research API
https://www.perplexity.ai/
"""

from typing import Any, Dict, List, Optional

import structlog

from config.settings import settings
from .base import BaseScraper

logger = structlog.get_logger()


class PerplexityClient(BaseScraper):
    """
    Cliente para Perplexity AI - Research API

    Funcionalidades:
    - Chat com pesquisa em tempo real
    - Respostas com citações
    - Múltiplos modelos disponíveis
    """

    MODELS = {
        "sonar": "llama-3.1-sonar-small-128k-online",
        "sonar-large": "llama-3.1-sonar-large-128k-online",
        "sonar-huge": "llama-3.1-sonar-huge-128k-online"
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "sonar",
        timeout: float = 60.0
    ):
        super().__init__(
            api_key=api_key or settings.perplexity_api_key,
            base_url="https://api.perplexity.ai",
            rate_limit=50,
            timeout=timeout
        )
        self.model = self.MODELS.get(model, model)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        return_citations: bool = True,
        search_domain_filter: Optional[List[str]] = None,
        search_recency_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat com pesquisa em tempo real

        Args:
            query: Pergunta ou tópico
            system_prompt: Instruções do sistema
            temperature: Criatividade (0-1)
            max_tokens: Máximo de tokens na resposta
            return_citations: Incluir citações
            search_domain_filter: Filtrar domínios
            search_recency_filter: Filtro de tempo ("month", "week", "day", "hour")

        Returns:
            Resposta com citações
        """
        logger.info("perplexity_chat", query=query[:50])

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": query
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "return_citations": return_citations
        }

        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter

        result = await self.post("/chat/completions", json=payload)

        # Extrair resposta
        choices = result.get("choices", [])
        if not choices:
            return {"answer": "", "citations": []}

        message = choices[0].get("message", {})

        return {
            "query": query,
            "answer": message.get("content", ""),
            "citations": result.get("citations", []),
            "model": result.get("model"),
            "usage": result.get("usage", {})
        }

    async def research(
        self,
        topic: str,
        depth: str = "detailed",
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Pesquisa em profundidade sobre um tópico

        Args:
            topic: Tópico para pesquisar
            depth: "brief", "detailed", ou "comprehensive"
            focus_areas: Áreas específicas para focar

        Returns:
            Pesquisa detalhada
        """
        depth_prompts = {
            "brief": "Forneça uma visão geral concisa",
            "detailed": "Forneça uma análise detalhada com exemplos",
            "comprehensive": "Forneça uma análise abrangente e aprofundada com múltiplas perspectivas"
        }

        system_prompt = f"""Você é um pesquisador especializado em inteligência de mercado brasileiro.
{depth_prompts.get(depth, depth_prompts['detailed'])}.
Sempre cite fontes confiáveis e foque em informações recentes e relevantes para o Brasil.
Responda em português brasileiro."""

        if focus_areas:
            system_prompt += f"\n\nÁreas de foco: {', '.join(focus_areas)}"

        return await self.chat(
            query=topic,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2048
        )

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA EMPRESAS
    # ===========================================

    async def analyze_company(
        self,
        company_name: str,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Análise completa de uma empresa

        Args:
            company_name: Nome da empresa
            analysis_type: "full", "swot", "competitors", "market"

        Returns:
            Análise da empresa
        """
        prompts = {
            "full": f"""Faça uma análise completa da empresa {company_name} no Brasil:
1. Visão geral do negócio
2. Principais produtos/serviços
3. Posicionamento de mercado
4. Principais concorrentes
5. Pontos fortes e fracos
6. Notícias recentes relevantes

Forneça informações atualizadas e cite fontes.""",

            "swot": f"""Faça uma análise SWOT detalhada da empresa {company_name} no Brasil:
- Forças (Strengths): vantagens competitivas
- Fraquezas (Weaknesses): pontos a melhorar
- Oportunidades (Opportunities): tendências favoráveis
- Ameaças (Threats): riscos e desafios

Baseie sua análise em dados e notícias recentes.""",

            "competitors": f"""Identifique e analise os principais concorrentes da empresa {company_name} no Brasil:
1. Liste os 3-5 principais concorrentes
2. Compare posicionamento e market share
3. Analise diferenciais de cada um
4. Identifique vantagens competitivas
5. Tendências de competição no setor""",

            "market": f"""Analise o mercado e setor de atuação da empresa {company_name} no Brasil:
1. Tamanho e crescimento do mercado
2. Principais tendências
3. Regulamentação relevante
4. Barreiras de entrada
5. Perspectivas para os próximos anos"""
        }

        system_prompt = """Você é um analista de inteligência competitiva especializado no mercado brasileiro.
Forneça análises objetivas, baseadas em fatos e dados recentes.
Sempre cite fontes quando disponíveis.
Responda em português brasileiro com formatação clara."""

        result = await self.chat(
            query=prompts.get(analysis_type, prompts["full"]),
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2048,
            search_recency_filter="month"
        )

        return {
            "company_name": company_name,
            "analysis_type": analysis_type,
            "analysis": result.get("answer"),
            "citations": result.get("citations", [])
        }

    async def find_competitors(
        self,
        company_name: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Encontra concorrentes de uma empresa

        Args:
            company_name: Nome da empresa
            industry: Setor (melhora precisão)

        Returns:
            Lista de concorrentes
        """
        query = f"Quais são os principais concorrentes da empresa {company_name}"
        if industry:
            query += f" no setor de {industry}"
        query += " no Brasil? Liste os nomes das empresas e uma breve descrição de cada."

        result = await self.chat(
            query=query,
            system_prompt="Liste concorrentes diretos e indiretos. Forneça nomes de empresas específicas.",
            temperature=0.2,
            max_tokens=1024
        )

        return {
            "company_name": company_name,
            "industry": industry,
            "competitors_analysis": result.get("answer"),
            "citations": result.get("citations", [])
        }

    async def suggest_okrs(
        self,
        company_name: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sugere OKRs para uma empresa

        Args:
            company_name: Nome da empresa
            context: Contexto adicional (setor, tamanho, desafios)

        Returns:
            OKRs sugeridos
        """
        query = f"""Com base no que você sabe sobre a empresa {company_name} no Brasil,
sugira 3-5 OKRs (Objectives and Key Results) estratégicos para os próximos 12 meses.
Para cada objetivo, inclua 2-3 resultados-chave mensuráveis."""

        if context:
            query += f"\n\nContexto adicional: {context}"

        result = await self.chat(
            query=query,
            system_prompt="""Você é um consultor estratégico especializado em OKRs.
Sugira objetivos ambiciosos mas alcançáveis, com KRs específicos e mensuráveis.
Considere o cenário econômico brasileiro atual.""",
            temperature=0.4,
            max_tokens=1500
        )

        return {
            "company_name": company_name,
            "okrs": result.get("answer"),
            "citations": result.get("citations", [])
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA PESSOAS
    # ===========================================

    async def research_person(
        self,
        name: str,
        context: Optional[str] = None,
        focus: str = "professional"
    ) -> Dict[str, Any]:
        """
        Pesquisa sobre uma pessoa

        Args:
            name: Nome da pessoa
            context: Contexto (empresa, cargo)
            focus: "professional", "academic", "public"

        Returns:
            Perfil da pessoa
        """
        focus_prompts = {
            "professional": "carreira profissional, experiências e realizações",
            "academic": "formação acadêmica, publicações e pesquisas",
            "public": "presença pública, aparições na mídia e redes sociais"
        }

        query = f"Quem é {name}"
        if context:
            query += f" ({context})"
        query += f"? Foque em: {focus_prompts.get(focus, focus_prompts['professional'])}"

        result = await self.chat(
            query=query,
            system_prompt="""Forneça informações biográficas e profissionais verificáveis.
Evite especulações e foque em fatos documentados.
Responda em português brasileiro.""",
            temperature=0.2,
            max_tokens=1024
        )

        return {
            "name": name,
            "context": context,
            "focus": focus,
            "profile": result.get("answer"),
            "citations": result.get("citations", [])
        }

    async def analyze_fit(
        self,
        person_name: str,
        company_name: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analisa fit de uma pessoa com uma empresa

        Args:
            person_name: Nome da pessoa
            company_name: Nome da empresa
            role: Cargo (opcional)

        Returns:
            Análise de fit
        """
        query = f"""Analise o potencial fit entre {person_name} e a empresa {company_name}"""
        if role:
            query += f" para a posição de {role}"

        query += """.
Considere:
1. Alinhamento de experiência e habilidades
2. Fit cultural (baseado em valores da empresa)
3. Trajetória de carreira
4. Potenciais sinergias
5. Possíveis gaps ou desafios

Forneça uma análise objetiva com pontuação de 1-10 para cada aspecto."""

        result = await self.chat(
            query=query,
            system_prompt="""Você é um especialista em recrutamento executivo.
Forneça uma análise equilibrada considerando múltiplas perspectivas.
Base sua análise em informações públicas disponíveis.""",
            temperature=0.3,
            max_tokens=1500
        )

        return {
            "person_name": person_name,
            "company_name": company_name,
            "role": role,
            "fit_analysis": result.get("answer"),
            "citations": result.get("citations", [])
        }

    # ===========================================
    # MÉTODOS ESPECÍFICOS PARA POLÍTICOS
    # ===========================================

    async def research_politician(
        self,
        name: str,
        role: Optional[str] = None,
        state: Optional[str] = None,
        focus: str = "personal"
    ) -> Dict[str, Any]:
        """
        Pesquisa sobre um político (foco em perfil pessoal)

        Args:
            name: Nome do político
            role: Cargo político
            state: Estado
            focus: "personal", "career", "public_perception"

        Returns:
            Perfil do político
        """
        focus_prompts = {
            "personal": "história pessoal, família, formação e trajetória de vida",
            "career": "carreira política, cargos ocupados e principais realizações",
            "public_perception": "percepção pública, presença nas redes sociais e imagem"
        }

        query = f"Forneça informações sobre {name}"
        if role:
            query += f", {role}"
        if state:
            query += f" do {state}"

        query += f". Foque em: {focus_prompts.get(focus, focus_prompts['personal'])}"

        result = await self.chat(
            query=query,
            system_prompt="""Você é um pesquisador especializado em perfis públicos.
Forneça informações factuais e verificáveis.
Evite viés político e foque em dados objetivos.
Responda em português brasileiro.""",
            temperature=0.2,
            max_tokens=1500,
            search_domain_filter=[
                "gov.br",
                "camara.leg.br",
                "senado.leg.br",
                "wikipedia.org",
                "politicos.org.br"
            ]
        )

        return {
            "name": name,
            "role": role,
            "state": state,
            "focus": focus,
            "profile": result.get("answer"),
            "citations": result.get("citations", [])
        }

    # ===========================================
    # MÉTODOS DE MERCADO
    # ===========================================

    async def analyze_market(
        self,
        industry: str,
        aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Análise de mercado/setor

        Args:
            industry: Setor para analisar
            aspects: Aspectos específicos

        Returns:
            Análise de mercado
        """
        if aspects is None:
            aspects = [
                "tamanho e crescimento",
                "principais players",
                "tendências",
                "desafios e oportunidades",
                "perspectivas"
            ]

        query = f"""Faça uma análise do mercado de {industry} no Brasil.
Cubra os seguintes aspectos: {', '.join(aspects)}.
Inclua dados e estatísticas quando disponíveis."""

        result = await self.chat(
            query=query,
            system_prompt="""Você é um analista de mercado especializado no Brasil.
Forneça análises baseadas em dados e tendências recentes.
Cite fontes e estatísticas quando disponíveis.""",
            temperature=0.3,
            max_tokens=2048,
            search_recency_filter="month"
        )

        return {
            "industry": industry,
            "aspects": aspects,
            "analysis": result.get("answer"),
            "citations": result.get("citations", [])
        }
