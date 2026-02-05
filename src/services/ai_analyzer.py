"""
AI Analyzer Service
Análise inteligente usando Claude/Anthropic
"""

import json
from typing import Any, Dict, List, Optional

import httpx
import structlog

from config.settings import settings

logger = structlog.get_logger()


class AIAnalyzer:
    """
    Serviço de análise usando Claude API

    Funcionalidades:
    - Análise SWOT
    - Geração de OKRs
    - Análise de fit cultural
    - Sumarização de dados
    - Extração de insights
    """

    MODELS = {
        "fast": "claude-3-haiku-20240307",
        "balanced": "claude-3-5-sonnet-20241022",
        "powerful": "claude-3-opus-20240229"
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "balanced",
        timeout: float = 120.0
    ):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = self.MODELS.get(model, model)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        # Estatísticas
        self.stats = {
            "requests": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "errors": 0
        }

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy client initialization"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.anthropic.com",
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
            )
        return self._client

    async def close(self):
        """Fecha o cliente HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _call_claude(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3
    ) -> str:
        """
        Chama a API do Claude

        Args:
            prompt: Mensagem do usuário
            system: System prompt
            max_tokens: Máximo de tokens na resposta
            temperature: Criatividade (0-1)

        Returns:
            Resposta do modelo
        """
        self.stats["requests"] += 1

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        if system:
            payload["system"] = system

        try:
            response = await self.client.post("/v1/messages", json=payload)
            response.raise_for_status()
            data = response.json()

            # Atualizar estatísticas
            usage = data.get("usage", {})
            self.stats["tokens_input"] += usage.get("input_tokens", 0)
            self.stats["tokens_output"] += usage.get("output_tokens", 0)

            # Extrair texto da resposta
            content = data.get("content", [])
            if content and content[0].get("type") == "text":
                return content[0].get("text", "")

            return ""

        except Exception as e:
            self.stats["errors"] += 1
            logger.error("claude_api_error", error=str(e))
            raise

    # ===========================================
    # ANÁLISE DE EMPRESAS
    # ===========================================

    async def analyze_company_swot(
        self,
        company_data: Dict[str, Any],
        market_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera análise SWOT para uma empresa

        Args:
            company_data: Dados coletados da empresa
            market_context: Contexto de mercado adicional

        Returns:
            Análise SWOT estruturada
        """
        logger.info("ai_analyze_swot", company=company_data.get("nome_fantasia", ""))

        system = """Você é um analista de inteligência competitiva especializado no mercado brasileiro.
Sua tarefa é criar uma análise SWOT detalhada e acionável para empresas.

Regras:
1. Seja específico e baseie-se nos dados fornecidos
2. Cada ponto deve ser claro e acionável
3. Considere o contexto do mercado brasileiro
4. Forneça 3-5 pontos em cada categoria
5. Responda SEMPRE em formato JSON válido"""

        prompt = f"""Analise os dados desta empresa e gere uma análise SWOT completa:

## Dados da Empresa
{json.dumps(company_data, indent=2, ensure_ascii=False, default=str)}

{f"## Contexto de Mercado{chr(10)}{market_context}" if market_context else ""}

Responda em JSON com a seguinte estrutura:
{{
    "strengths": [
        {{"point": "descrição do ponto forte", "impact": "alto/médio/baixo", "evidence": "evidência dos dados"}}
    ],
    "weaknesses": [
        {{"point": "descrição do ponto fraco", "impact": "alto/médio/baixo", "recommendation": "recomendação"}}
    ],
    "opportunities": [
        {{"point": "descrição da oportunidade", "timeframe": "curto/médio/longo prazo", "action": "ação sugerida"}}
    ],
    "threats": [
        {{"point": "descrição da ameaça", "probability": "alta/média/baixa", "mitigation": "mitigação sugerida"}}
    ],
    "summary": "resumo executivo da análise",
    "confidence_score": 0.0-1.0
}}"""

        response = await self._call_claude(prompt, system=system)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Tentar extrair JSON do texto
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    async def generate_okrs(
        self,
        company_data: Dict[str, Any],
        swot: Optional[Dict] = None,
        focus_areas: Optional[List[str]] = None,
        timeframe: str = "quarterly"
    ) -> Dict[str, Any]:
        """
        Gera OKRs sugeridos para uma empresa

        Args:
            company_data: Dados da empresa
            swot: Análise SWOT (se disponível)
            focus_areas: Áreas de foco específicas
            timeframe: "quarterly", "annual"

        Returns:
            OKRs estruturados
        """
        logger.info("ai_generate_okrs", company=company_data.get("nome_fantasia", ""))

        system = """Você é um consultor estratégico especializado em OKRs (Objectives and Key Results).
Sua tarefa é criar OKRs ambiciosos mas alcançáveis para empresas brasileiras.

Regras:
1. Objetivos devem ser inspiradores e qualitativos
2. Key Results devem ser mensuráveis e específicos
3. Considere o cenário econômico brasileiro atual
4. Sugira 3-5 OKRs estratégicos
5. Responda SEMPRE em formato JSON válido"""

        prompt = f"""Com base nos dados desta empresa, sugira OKRs estratégicos para o período {timeframe}:

## Dados da Empresa
{json.dumps(company_data, indent=2, ensure_ascii=False, default=str)}

{f"## Análise SWOT{chr(10)}{json.dumps(swot, indent=2, ensure_ascii=False)}" if swot else ""}

{f"## Áreas de Foco Prioritárias{chr(10)}{chr(10).join(f'- {area}' for area in focus_areas)}" if focus_areas else ""}

Responda em JSON:
{{
    "okrs": [
        {{
            "objective": "Objetivo inspirador",
            "rationale": "Por que este objetivo é importante",
            "key_results": [
                {{"kr": "Key Result mensurável", "target": "meta específica", "baseline": "valor atual se conhecido"}},
                {{"kr": "Key Result mensurável", "target": "meta específica", "baseline": "valor atual se conhecido"}},
                {{"kr": "Key Result mensurável", "target": "meta específica", "baseline": "valor atual se conhecido"}}
            ],
            "initiatives": ["iniciativa sugerida 1", "iniciativa sugerida 2"]
        }}
    ],
    "alignment_notes": "Como os OKRs se alinham com a estratégia da empresa",
    "risks": ["risco potencial na execução"],
    "dependencies": ["dependência externa ou interna"]
}}"""

        response = await self._call_claude(prompt, system=system)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    async def analyze_competitors(
        self,
        company_data: Dict[str, Any],
        competitors_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analisa posicionamento competitivo

        Args:
            company_data: Dados da empresa principal
            competitors_data: Dados dos concorrentes

        Returns:
            Análise competitiva
        """
        logger.info(
            "ai_analyze_competitors",
            company=company_data.get("nome_fantasia", ""),
            num_competitors=len(competitors_data)
        )

        system = """Você é um analista de inteligência competitiva.
Sua tarefa é comparar empresas e identificar diferenciais competitivos.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Compare a empresa principal com seus concorrentes:

## Empresa Principal
{json.dumps(company_data, indent=2, ensure_ascii=False, default=str)}

## Concorrentes
{json.dumps(competitors_data, indent=2, ensure_ascii=False, default=str)}

Responda em JSON:
{{
    "market_position": "posição no mercado (líder, desafiante, seguidor, nicho)",
    "competitive_advantages": [
        {{"advantage": "vantagem", "sustainability": "alta/média/baixa"}}
    ],
    "competitive_disadvantages": [
        {{"disadvantage": "desvantagem", "impact": "alto/médio/baixo"}}
    ],
    "competitor_comparison": [
        {{
            "competitor": "nome do concorrente",
            "similarity_score": 0.0-1.0,
            "strengths_vs_us": ["pontos fortes em relação a nós"],
            "weaknesses_vs_us": ["pontos fracos em relação a nós"],
            "threat_level": "alto/médio/baixo"
        }}
    ],
    "opportunities_vs_competitors": ["oportunidades identificadas"],
    "recommended_strategy": "estratégia competitiva recomendada",
    "key_battlegrounds": ["áreas de competição mais intensa"]
}}"""

        response = await self._call_claude(prompt, system=system)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    # ===========================================
    # ANÁLISE DE PESSOAS
    # ===========================================

    async def analyze_person_profile(
        self,
        person_data: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analisa perfil de uma pessoa

        Args:
            person_data: Dados da pessoa
            context: Contexto adicional

        Returns:
            Análise do perfil
        """
        logger.info("ai_analyze_person", name=person_data.get("name", ""))

        system = """Você é um especialista em análise de perfis profissionais.
Analise os dados e forneça insights sobre a pessoa.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Analise o perfil desta pessoa:

## Dados da Pessoa
{json.dumps(person_data, indent=2, ensure_ascii=False, default=str)}

{f"## Contexto{chr(10)}{context}" if context else ""}

Responda em JSON:
{{
    "profile_summary": "resumo do perfil profissional",
    "strengths": ["pontos fortes identificados"],
    "skills": [
        {{"skill": "habilidade", "level": "expert/advanced/intermediate", "evidence": "evidência"}}
    ],
    "experience_highlights": ["destaques da experiência"],
    "career_trajectory": "análise da trajetória de carreira",
    "leadership_indicators": ["indicadores de liderança"],
    "potential_roles": ["funções adequadas ao perfil"],
    "development_areas": ["áreas de desenvolvimento"],
    "notable_achievements": ["conquistas notáveis"],
    "professional_network": "análise da rede de contatos (se disponível)"
}}"""

        response = await self._call_claude(prompt, system=system)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    async def analyze_cultural_fit(
        self,
        person_data: Dict[str, Any],
        company_data: Dict[str, Any],
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analisa fit cultural entre pessoa e empresa

        Args:
            person_data: Dados da pessoa
            company_data: Dados da empresa
            role: Cargo em questão

        Returns:
            Análise de fit
        """
        logger.info(
            "ai_analyze_fit",
            person=person_data.get("name", ""),
            company=company_data.get("nome_fantasia", "")
        )

        system = """Você é um especialista em recrutamento e cultura organizacional.
Analise o fit entre candidato e empresa de forma objetiva.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Analise o fit entre esta pessoa e empresa:

## Dados da Pessoa
{json.dumps(person_data, indent=2, ensure_ascii=False, default=str)}

## Dados da Empresa
{json.dumps(company_data, indent=2, ensure_ascii=False, default=str)}

{f"## Cargo em Questão: {role}" if role else ""}

Responda em JSON:
{{
    "cultural_fit_score": 0.0-1.0,
    "role_fit_score": 0.0-1.0,
    "overall_fit_score": 0.0-1.0,
    "cultural_alignment": [
        {{"aspect": "aspecto cultural", "alignment": "alto/médio/baixo", "explanation": "explicação"}}
    ],
    "skill_match": [
        {{"skill": "habilidade requerida", "match": "total/parcial/gap", "notes": "observações"}}
    ],
    "experience_relevance": "análise da relevância da experiência",
    "growth_potential": "potencial de crescimento na empresa",
    "onboarding_considerations": ["considerações para onboarding"],
    "potential_challenges": ["desafios potenciais"],
    "interview_focus_areas": ["áreas para explorar em entrevista"],
    "recommendation": "recomendação final",
    "confidence_score": 0.0-1.0
}}"""

        response = await self._call_claude(prompt, system=system)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    # ===========================================
    # ANÁLISE DE POLÍTICOS
    # ===========================================

    async def analyze_politician_profile(
        self,
        politician_data: Dict[str, Any],
        news_data: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analisa perfil de um político (foco pessoal, não político)

        Args:
            politician_data: Dados do político
            news_data: Notícias relacionadas

        Returns:
            Análise do perfil pessoal
        """
        logger.info("ai_analyze_politician", name=politician_data.get("name", ""))

        system = """Você é um pesquisador especializado em perfis públicos.
Analise o perfil pessoal (não político) de forma objetiva e factual.
Evite viés político e foque em dados verificáveis.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Analise o perfil pessoal deste político:

## Dados do Político
{json.dumps(politician_data, indent=2, ensure_ascii=False, default=str)}

{f"## Notícias Recentes{chr(10)}{json.dumps(news_data, indent=2, ensure_ascii=False)}" if news_data else ""}

Responda em JSON:
{{
    "personal_profile": {{
        "background": "histórico pessoal",
        "education": ["formação acadêmica"],
        "career_before_politics": "carreira antes da política",
        "family": "informações familiares públicas",
        "interests": ["interesses conhecidos"]
    }},
    "public_perception": {{
        "positive_aspects": ["aspectos positivos na percepção pública"],
        "negative_aspects": ["aspectos negativos na percepção pública"],
        "media_presence": "presença na mídia",
        "social_media_presence": "presença em redes sociais"
    }},
    "communication_style": "estilo de comunicação",
    "key_characteristics": ["características marcantes"],
    "public_actions": ["ações públicas relevantes"],
    "controversies": [
        {{"topic": "tema", "summary": "resumo factual", "date": "período"}}
    ],
    "notable_quotes": ["citações notáveis"],
    "data_quality_note": "nota sobre qualidade/completude dos dados"
}}"""

        response = await self._call_claude(prompt, system=system)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    # ===========================================
    # UTILITÁRIOS
    # ===========================================

    async def summarize_data(
        self,
        data: Dict[str, Any],
        context: str,
        max_length: int = 500
    ) -> str:
        """
        Sumariza dados em texto

        Args:
            data: Dados para sumarizar
            context: Contexto da sumarização
            max_length: Tamanho máximo do resumo

        Returns:
            Resumo em texto
        """
        prompt = f"""Resuma os seguintes dados em até {max_length} caracteres.
Contexto: {context}

Dados:
{json.dumps(data, indent=2, ensure_ascii=False, default=str)}

Forneça um resumo claro e objetivo em português brasileiro."""

        return await self._call_claude(prompt)

    async def extract_insights(
        self,
        data: Dict[str, Any],
        focus: str
    ) -> List[Dict[str, str]]:
        """
        Extrai insights de dados

        Args:
            data: Dados para análise
            focus: Foco da análise

        Returns:
            Lista de insights
        """
        prompt = f"""Extraia os principais insights dos dados abaixo.
Foco: {focus}

Dados:
{json.dumps(data, indent=2, ensure_ascii=False, default=str)}

Responda em JSON:
{{
    "insights": [
        {{"insight": "descrição do insight", "importance": "alta/média/baixa", "actionable": true/false}}
    ]
}}"""

        response = await self._call_claude(prompt)

        try:
            result = json.loads(response)
            return result.get("insights", [])
        except json.JSONDecodeError:
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso"""
        return {
            **self.stats,
            "model": self.model,
            "estimated_cost": self._estimate_cost()
        }

    def _estimate_cost(self) -> float:
        """Estima custo baseado nos tokens"""
        # Preços aproximados (verificar pricing atual)
        input_cost_per_1k = 0.003  # $3 per 1M tokens
        output_cost_per_1k = 0.015  # $15 per 1M tokens

        input_cost = (self.stats["tokens_input"] / 1000) * input_cost_per_1k
        output_cost = (self.stats["tokens_output"] / 1000) * output_cost_per_1k

        return round(input_cost + output_cost, 4)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
