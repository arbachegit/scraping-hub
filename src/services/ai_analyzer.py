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
        "balanced": "claude-3-haiku-20240307",  # Fallback to haiku if no access to sonnet
        "powerful": "claude-3-haiku-20240307"   # Fallback to haiku if no access to opus
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
1. PRIORIZE o conteúdo extraído do website da empresa - é a fonte mais confiável
2. Analise os serviços, produtos, posicionamento e diferenciais mencionados no site
3. Seja específico e cite evidências dos dados fornecidos
4. Cada ponto deve ser claro e acionável
5. Considere o contexto do mercado brasileiro
6. Forneça 3-5 pontos em cada categoria
7. Responda SEMPRE em formato JSON válido"""

        # Extrair e preparar conteúdo do site para análise
        website_content = company_data.get("website_content", "")
        website_headings = company_data.get("website_headings", [])

        prompt = f"""Analise os dados desta empresa e gere uma análise SWOT completa.

IMPORTANTE: O conteúdo do website é a fonte PRINCIPAL de informação. Analise cuidadosamente:

## Conteúdo do Website da Empresa
{website_content[:8000] if website_content else "Não disponível"}

## Seções do Site
{json.dumps(website_headings, indent=2, ensure_ascii=False) if website_headings else "Não disponível"}

## Dados Cadastrais e Complementares
- Nome: {company_data.get("nome_fantasia")}
- Razão Social: {company_data.get("razao_social")}
- CNPJ: {company_data.get("cnpj")}
- Setor: {company_data.get("industry")}
- Website: {company_data.get("website")}
- Descrição: {company_data.get("description")}
- Redes Sociais: {json.dumps(company_data.get("social_media", {}), ensure_ascii=False)}

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
1. ANALISE o conteúdo do website para entender os serviços e posicionamento da empresa
2. Objetivos devem ser inspiradores e qualitativos
3. Key Results devem ser mensuráveis e específicos
4. Baseie-se nos serviços/produtos oferecidos pela empresa
5. Considere o cenário econômico brasileiro atual
6. Sugira 3-5 OKRs estratégicos
7. Responda SEMPRE em formato JSON válido"""

        # Extrair conteúdo do site
        website_content = company_data.get("website_content", "")

        prompt = f"""Com base nos dados desta empresa, sugira OKRs estratégicos para o período {timeframe}:

## Conteúdo do Website (FONTE PRINCIPAL)
{website_content[:6000] if website_content else "Não disponível"}

## Dados da Empresa
- Nome: {company_data.get("nome_fantasia")}
- Setor: {company_data.get("industry")}
- Descrição: {company_data.get("description")}
- Website: {company_data.get("website")}

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
        Analisa perfil de uma pessoa (método legado - use analyze_person_deep)
        """
        # Redirecionar para novo método
        return await self.analyze_person_deep(person_data, context or "", "quick")

    async def analyze_person_deep(
        self,
        person_data: Dict[str, Any],
        rich_context: str,
        analysis_depth: str = "full"
    ) -> Dict[str, Any]:
        """
        Análise PROFUNDA de perfil de pessoa

        IMPORTANTE: Este método recebe TODOS os dados coletados
        de TODAS as fontes e faz uma análise completa e detalhada.

        Args:
            person_data: Dados básicos consolidados
            rich_context: Contexto COMPLETO com dados de todas as fontes
            analysis_depth: "full" ou "quick"

        Returns:
            Análise profunda e estruturada
        """
        logger.info("ai_analyze_person_deep", name=person_data.get("name", ""), depth=analysis_depth)

        if analysis_depth == "quick":
            system = """Você é um headhunter e especialista em análise de talentos do mercado brasileiro.
Faça uma análise RÁPIDA mas SUBSTANCIAL do perfil profissional.
IMPORTANTE: Use TODAS as informações fornecidas para enriquecer sua análise.
Responda SEMPRE em formato JSON válido."""

            prompt = f"""Analise este profissional com base em TODOS os dados coletados:

## Dados Básicos
- Nome: {person_data.get('name')}
- Cargo: {person_data.get('title') or person_data.get('current_title', 'N/A')}
- Empresa: {person_data.get('company') or person_data.get('current_company', 'N/A')}

## DADOS COLETADOS DE MÚLTIPLAS FONTES
{rich_context}

Responda em JSON:
{{
    "professional_summary": "Resumo executivo do profissional em 2-3 parágrafos. Seja específico sobre cargo, empresa, área de atuação.",
    "key_insights": [
        "Insight 1 específico sobre o profissional",
        "Insight 2 específico sobre a carreira",
        "Insight 3 sobre área de atuação"
    ],
    "strengths": ["Ponto forte 1 com evidência", "Ponto forte 2 com evidência"],
    "quick_assessment": "Avaliação geral do perfil em 1 parágrafo"
}}"""
        else:
            system = """Você é um HEADHUNTER SÊNIOR e especialista em inteligência de talentos do mercado brasileiro.

Sua tarefa é fazer uma ANÁLISE PROFUNDA E COMPLETA do perfil profissional.

REGRAS IMPORTANTES:
1. USE TODAS as informações fornecidas - não ignore nenhuma fonte
2. Seja ESPECÍFICO - cite evidências e dados concretos
3. Analise a TRAJETÓRIA de carreira, não apenas o momento atual
4. Identifique PADRÕES na carreira
5. Avalie a PRESENÇA PÚBLICA e reputação
6. Forneça insights ACIONÁVEIS
7. Seja objetivo mas completo

Responda SEMPRE em formato JSON válido."""

            prompt = f"""Faça uma ANÁLISE PROFUNDA E COMPLETA deste profissional.

ATENÇÃO: Abaixo estão dados coletados de MÚLTIPLAS FONTES (Perplexity, Apollo, Google, Tavily, LinkedIn).
USE TODOS esses dados para construir uma análise rica e detalhada.

## DADOS BÁSICOS CONSOLIDADOS
- Nome: {person_data.get('name')}
- Cargo atual: {person_data.get('title') or person_data.get('current_title', 'Não identificado')}
- Empresa atual: {person_data.get('company') or person_data.get('current_company', 'Não identificada')}
- Senioridade: {person_data.get('seniority', 'Não identificada')}
- Localização: {person_data.get('city', '')}, {person_data.get('state', '')}, {person_data.get('country', 'Brasil')}
- LinkedIn: {person_data.get('linkedin_url', 'N/A')}

## DADOS COMPLETOS COLETADOS DE TODAS AS FONTES
{rich_context}

---

Com base em TODOS os dados acima, responda em JSON:
{{
    "professional_summary": "Resumo executivo COMPLETO do profissional em 3-5 parágrafos. Inclua: quem é, o que faz, trajetória, especializações, posicionamento no mercado. Seja ESPECÍFICO com nomes de empresas, cargos, áreas.",

    "career_analysis": {{
        "current_position": "Análise detalhada da posição atual",
        "career_trajectory": "Análise da evolução da carreira ao longo do tempo",
        "career_pattern": "Padrões identificados (generalista vs especialista, setores, etc)",
        "career_highlights": ["Marco 1 da carreira", "Marco 2 da carreira"],
        "estimated_experience_years": "número estimado de anos de experiência"
    }},

    "skills_assessment": [
        {{"skill": "Habilidade 1", "level": "expert/advanced/intermediate/basic", "evidence": "Evidência da competência"}},
        {{"skill": "Habilidade 2", "level": "expert/advanced/intermediate/basic", "evidence": "Evidência da competência"}},
        {{"skill": "Habilidade 3", "level": "expert/advanced/intermediate/basic", "evidence": "Evidência da competência"}}
    ],

    "strengths": [
        "Ponto forte 1 - com evidência específica dos dados",
        "Ponto forte 2 - com evidência específica dos dados",
        "Ponto forte 3 - com evidência específica dos dados"
    ],

    "development_areas": [
        "Área de desenvolvimento 1 - por que identificou",
        "Área de desenvolvimento 2 - por que identificou"
    ],

    "notable_achievements": [
        "Conquista/realização notável 1",
        "Conquista/realização notável 2"
    ],

    "public_presence": {{
        "linkedin_analysis": "Análise da presença no LinkedIn",
        "media_presence": "Presença em mídia/notícias",
        "social_media": "Presença em outras redes",
        "overall_visibility": "Baixa/Média/Alta",
        "reputation_indicators": ["Indicador 1", "Indicador 2"]
    }},

    "key_insights": [
        "Insight estratégico 1 sobre o profissional",
        "Insight estratégico 2 sobre a carreira",
        "Insight estratégico 3 sobre o potencial"
    ],

    "potential_roles": [
        {{"role": "Tipo de cargo adequado 1", "fit_reason": "Por que seria bom fit"}},
        {{"role": "Tipo de cargo adequado 2", "fit_reason": "Por que seria bom fit"}}
    ],

    "recommendations": [
        "Recomendação 1 para quem quer abordar/contratar este profissional",
        "Recomendação 2 para networking ou aproximação"
    ],

    "confidence_score": 0.0-1.0,
    "data_quality_note": "Nota sobre a qualidade e completude dos dados disponíveis"
}}"""

        response = await self._call_claude(prompt, system=system, max_tokens=6000)

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
        """Método legado - redireciona para analyze_politician_deep"""
        return await self.analyze_politician_deep(politician_data, "", "personal")

    async def analyze_politician_deep(
        self,
        politician_data: Dict[str, Any],
        rich_context: str,
        focus: str = "personal"
    ) -> Dict[str, Any]:
        """
        Análise PROFUNDA de perfil de político

        IMPORTANTE: Este método recebe TODOS os dados coletados
        de TODAS as fontes e faz uma análise completa.

        Args:
            politician_data: Dados básicos consolidados
            rich_context: Contexto COMPLETO com dados de todas as fontes
            focus: "personal", "career", "public_perception"

        Returns:
            Análise profunda e estruturada
        """
        logger.info("ai_analyze_politician_deep", name=politician_data.get("name", ""), focus=focus)

        system = """Você é um PESQUISADOR SÊNIOR especializado em perfis públicos brasileiros.

Sua tarefa é fazer uma ANÁLISE PROFUNDA E COMPLETA do perfil PESSOAL de um político.

REGRAS IMPORTANTES:
1. Foque no perfil PESSOAL - biografia, família, formação, carreira antes da política
2. USE TODAS as informações fornecidas - não ignore nenhuma fonte
3. Seja ESPECÍFICO - cite evidências e dados concretos
4. Seja OBJETIVO e IMPARCIAL - evite viés político
5. Identifique PADRÕES na trajetória pessoal
6. Avalie a PRESENÇA PÚBLICA e estilo de comunicação
7. Forneça insights ACIONÁVEIS

Responda SEMPRE em formato JSON válido."""

        prompt = f"""Faça uma ANÁLISE PROFUNDA E COMPLETA do perfil PESSOAL deste político.

ATENÇÃO: Abaixo estão dados coletados de MÚLTIPLAS FONTES (Perplexity, Google, Tavily).
USE TODOS esses dados para construir uma análise rica e detalhada.

## DADOS BÁSICOS
- Nome: {politician_data.get('name')}
- Cargo: {politician_data.get('role', 'Não informado')}
- Estado: {politician_data.get('state', 'Não informado')}
- Partido: {politician_data.get('party', 'Não informado')}

## DADOS COMPLETOS COLETADOS DE TODAS AS FONTES
{rich_context}

---

Com base em TODOS os dados acima, responda em JSON:
{{
    "personal_summary": "Resumo COMPLETO do perfil pessoal em 3-5 parágrafos. Inclua: quem é, origem, formação, carreira antes da política, família, características pessoais. Seja ESPECÍFICO.",

    "biography": {{
        "birth": "Data e local de nascimento",
        "family_origin": "Origem familiar, pais, contexto de criação",
        "childhood": "Infância e juventude",
        "education": [
            {{"institution": "Nome", "degree": "Curso/Grau", "year": "Período", "details": "Detalhes relevantes"}}
        ],
        "career_before_politics": [
            {{"role": "Cargo", "organization": "Empresa/Instituição", "period": "Período", "achievements": "Realizações"}}
        ],
        "family": {{
            "spouse": "Cônjuge (se público)",
            "children": "Filhos (se público)",
            "other": "Outras informações familiares públicas"
        }},
        "personal_interests": ["Hobbies", "Interesses conhecidos"],
        "curiosities": ["Curiosidades pessoais"]
    }},

    "public_perception": {{
        "overall_image": "Imagem pública geral",
        "positive_aspects": ["Aspecto positivo 1 com evidência", "Aspecto positivo 2"],
        "negative_aspects": ["Aspecto negativo 1 com evidência", "Aspecto negativo 2"],
        "controversies": [
            {{"topic": "Tema", "summary": "Resumo factual objetivo", "period": "Quando", "current_status": "Status atual"}}
        ],
        "reputation_trends": "Tendências na reputação pública"
    }},

    "communication_style": "Análise detalhada do estilo de comunicação - como se expressa, tom, linguagem, presença em público",

    "media_presence": {{
        "traditional_media": "Presença em mídia tradicional",
        "social_media": "Presença e estilo em redes sociais",
        "public_appearances": "Tipo de aparições públicas",
        "notable_interviews": ["Entrevistas ou aparições notáveis"]
    }},

    "key_characteristics": [
        "Característica marcante 1 - com evidência",
        "Característica marcante 2 - com evidência",
        "Característica marcante 3 - com evidência"
    ],

    "key_insights": [
        "Insight estratégico 1 sobre a pessoa",
        "Insight estratégico 2 sobre a trajetória",
        "Insight estratégico 3 sobre a imagem pública"
    ],

    "confidence_score": 0.0-1.0,
    "data_quality_note": "Nota sobre qualidade e completude dos dados"
}}"""

        response = await self._call_claude(prompt, system=system, max_tokens=6000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    async def analyze_politician_quick(
        self,
        name: str,
        role: Optional[str],
        context: str
    ) -> Dict[str, Any]:
        """Análise rápida de político"""
        logger.info("ai_analyze_politician_quick", name=name)

        system = """Você é um pesquisador especializado em perfis públicos brasileiros.
Faça uma análise RÁPIDA mas SUBSTANCIAL do perfil pessoal.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Analise este político com base nos dados coletados:

## Político
- Nome: {name}
- Cargo: {role or 'N/A'}

## DADOS COLETADOS
{context}

Responda em JSON:
{{
    "personal_summary": "Resumo do perfil pessoal em 2-3 parágrafos",
    "key_facts": [
        "Fato importante 1",
        "Fato importante 2",
        "Fato importante 3"
    ],
    "quick_bio": {{
        "education": "Formação principal",
        "career": "Carreira antes da política",
        "family": "Informações familiares públicas"
    }},
    "public_image": "Análise breve da imagem pública"
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

    async def analyze_perception_deep(
        self,
        name: str,
        role: Optional[str],
        context: str,
        sentiments: Dict[str, int]
    ) -> Dict[str, Any]:
        """Análise profunda de percepção pública"""
        logger.info("ai_analyze_perception", name=name)

        system = """Você é um analista de opinião pública especializado no Brasil.
Analise a percepção pública de forma objetiva e imparcial.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Analise a percepção pública de {name}{' (' + role + ')' if role else ''}:

## DADOS COLETADOS
{context}

## Análise de Sentimento das Notícias
- Positivas: {sentiments.get('positive', 0)}
- Negativas: {sentiments.get('negative', 0)}
- Neutras: {sentiments.get('neutral', 0)}

Responda em JSON:
{{
    "perception_summary": "Resumo da percepção pública em 2-3 parágrafos",
    "sentiment_analysis": {{
        "overall_sentiment": "positivo/negativo/neutro/misto",
        "explanation": "Explicação da análise de sentimento"
    }},
    "positive_factors": ["Fator positivo 1", "Fator positivo 2"],
    "negative_factors": ["Fator negativo 1", "Fator negativo 2"],
    "recent_trends": "Tendências recentes na percepção",
    "key_events_impact": ["Evento que impactou percepção"]
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

    async def analyze_biography_deep(
        self,
        name: str,
        role: Optional[str],
        context: str
    ) -> Dict[str, Any]:
        """Análise profunda de biografia"""
        logger.info("ai_analyze_biography", name=name)

        system = """Você é um biógrafo especializado em figuras públicas brasileiras.
Organize e estruture informações biográficas de forma clara.
Responda SEMPRE em formato JSON válido."""

        prompt = f"""Estruture a biografia de {name}{' (' + role + ')' if role else ''}:

## DADOS COLETADOS
{context}

Responda em JSON:
{{
    "structured_biography": {{
        "full_name": "Nome completo",
        "birth_date": "Data de nascimento",
        "birth_place": "Local de nascimento",
        "parents": "Informações sobre os pais",
        "childhood": "Infância e juventude",
        "education": [
            {{"level": "Nível", "institution": "Instituição", "course": "Curso", "year": "Ano"}}
        ],
        "career_timeline": [
            {{"period": "Período", "role": "Cargo", "organization": "Organização", "description": "Descrição"}}
        ],
        "family": {{
            "spouse": "Cônjuge",
            "children": "Filhos",
            "other_relatives": "Outros familiares relevantes"
        }},
        "personal_life": {{
            "hobbies": ["Hobbies"],
            "interests": ["Interesses"],
            "curiosities": ["Curiosidades"]
        }}
    }},
    "narrative_summary": "Resumo narrativo da biografia em 3-4 parágrafos"
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

    async def consolidate_news_insights(
        self,
        news_data: List[Dict[str, Any]],
        topic: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consolida e analisa notícias de forma inteligente

        Args:
            news_data: Lista de notícias de múltiplas fontes
            topic: Tópico principal (ex: "economia brasil")
            context: Contexto adicional

        Returns:
            Análise consolidada das notícias
        """
        logger.info("ai_consolidate_news", topic=topic, count=len(news_data))

        # Preparar conteúdo das notícias
        news_content = []
        for i, news in enumerate(news_data[:20], 1):
            title = news.get("title", "")
            content = news.get("content", "") or news.get("snippet", "") or news.get("description", "")
            source = news.get("source", "") or news.get("url", "")
            date = news.get("date", "") or news.get("published_at", "")

            news_content.append(f"""
### Notícia {i}
**Título:** {title}
**Fonte:** {source}
**Data:** {date}
**Conteúdo:** {content[:600]}
""")

        news_text = "\n".join(news_content)

        system = """Você é um ANALISTA DE INTELIGÊNCIA DE MERCADO especializado no Brasil.

Sua tarefa é CONSOLIDAR e ANALISAR notícias de múltiplas fontes, criando uma análise
coesa, estruturada e ACIONÁVEL.

REGRAS:
1. SINTETIZE as informações - não apenas liste
2. Identifique PADRÕES e TENDÊNCIAS
3. Destaque IMPACTOS PRÁTICOS
4. Forneça CONTEXTO e ANÁLISE
5. Organize de forma clara e estruturada
6. Responda em formato MARKDOWN estruturado"""

        prompt = f"""Analise e consolide as seguintes notícias sobre "{topic}":

## NOTÍCIAS COLETADAS DE MÚLTIPLAS FONTES
{news_text}

{f"## CONTEXTO ADICIONAL{chr(10)}{context}" if context else ""}

---

Forneça uma análise CONSOLIDADA em formato JSON:
{{
    "executive_summary": "Resumo executivo em 2-3 parágrafos. O que está acontecendo? Qual o cenário atual? Quais as principais tendências?",

    "key_developments": [
        {{
            "development": "Desenvolvimento principal 1",
            "impact": "Impacto prático",
            "sources": ["Fontes que mencionam"]
        }},
        {{
            "development": "Desenvolvimento principal 2",
            "impact": "Impacto prático",
            "sources": ["Fontes que mencionam"]
        }}
    ],

    "trend_analysis": {{
        "positive_trends": ["Tendência positiva 1", "Tendência positiva 2"],
        "negative_trends": ["Tendência negativa 1", "Tendência negativa 2"],
        "neutral_observations": ["Observação neutra 1"]
    }},

    "market_implications": {{
        "short_term": "Implicações de curto prazo",
        "medium_term": "Implicações de médio prazo",
        "sectors_affected": ["Setor 1", "Setor 2"]
    }},

    "key_players": ["Empresas/pessoas/instituições mencionadas frequentemente"],

    "actionable_insights": [
        "Insight acionável 1 - o que fazer com esta informação",
        "Insight acionável 2 - oportunidade ou risco identificado"
    ],

    "sentiment_overview": {{
        "overall": "positivo/negativo/neutro/misto",
        "explanation": "Explicação do sentimento geral das notícias"
    }},

    "recommended_actions": [
        "Ação recomendada 1",
        "Ação recomendada 2"
    ],

    "sources_quality_note": "Nota sobre qualidade e diversidade das fontes"
}}"""

        response = await self._call_claude(prompt, system=system, max_tokens=4000)

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
