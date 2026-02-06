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
        "fast": "claude-3-5-haiku-20241022",
        "balanced": "claude-sonnet-4-20250514",
        "powerful": "claude-sonnet-4-20250514"
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "balanced",
        timeout: float = 120.0
    ):
        self.api_key = api_key or settings.anthropic_api_key
        # Usar modelo do settings se configurado, senão usar o mapeamento
        if settings.anthropic_model:
            self.model = settings.anthropic_model
        else:
            self.model = self.MODELS.get(model, model)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        logger.info("ai_analyzer_init", model=self.model)

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

    async def analyze_company_complete(
        self,
        company_data: Dict[str, Any],
        website_content: str,
        employees_data: List[Dict[str, Any]],
        news_data: List[Dict[str, Any]],
        research_context: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """
        Análise COMPLETA de empresa com múltiplas perspectivas

        Gera análise densa e estruturada por temas, com visões de:
        - Leigo (pessoa comum)
        - Profissional (especialista do setor)
        - Fornecedor (potencial parceiro)
        - Concorrente (análise competitiva)
        - Cliente (potencial comprador)

        Args:
            company_data: Dados básicos da empresa
            website_content: Conteúdo completo do site
            employees_data: Funcionários encontrados via Apollo/LinkedIn
            news_data: Notícias sobre a empresa
            research_context: Pesquisa Perplexity + Tavily
            sources: Lista de fontes para citação

        Returns:
            Análise completa multi-perspectiva
        """
        logger.info("ai_analyze_company_complete", company=company_data.get("nome_fantasia", ""))

        # Preparar lista de fontes para citação
        sources_list = "\n".join([f"[{i+1}] {src}" for i, src in enumerate(sources[:20])])

        # Preparar dados de funcionários
        employees_text = ""
        if employees_data:
            employees_text = "## FUNCIONÁRIOS IDENTIFICADOS (LinkedIn/Apollo)\n"
            for emp in employees_data[:15]:
                employees_text += f"""
### {emp.get('name', 'N/A')}
- **Cargo:** {emp.get('title', 'N/A')}
- **Departamento:** {', '.join(emp.get('departments', [])) if emp.get('departments') else 'N/A'}
- **Senioridade:** {emp.get('seniority', 'N/A')}
- **LinkedIn:** {emp.get('linkedin_url', 'N/A')}
- **Tempo na empresa:** {emp.get('tenure', 'N/A')}
"""

        # Preparar notícias
        news_text = ""
        if news_data:
            news_text = "## NOTÍCIAS RECENTES\n"
            for i, news in enumerate(news_data[:10]):
                news_text += f"[{i+1}] **{news.get('title', 'N/A')}** - {news.get('source', 'N/A')}\n"
                news_text += f"   {news.get('content', news.get('snippet', ''))[:300]}\n\n"

        system = """Você é um ANALISTA DE INTELIGÊNCIA EMPRESARIAL SÊNIOR especializado no mercado brasileiro.

Sua tarefa é criar uma ANÁLISE COMPLETA E PROFUNDA de uma empresa, estruturada em MÚLTIPLAS PERSPECTIVAS.

REGRAS CRÍTICAS:
1. Escreva TEXTOS DENSOS - parágrafos substanciais, não bullet points superficiais
2. CITE AS FONTES no formato [1], [2] ao longo do texto
3. Seja ESPECÍFICO - mencione produtos, serviços, nomes, números
4. Analise de MÚLTIPLOS ÂNGULOS - cada perspectiva deve ter visão única
5. Use o conteúdo do WEBSITE como fonte primária
6. INCLUA os funcionários identificados na análise
7. Forneça INSIGHTS ACIONÁVEIS em cada perspectiva
8. Mínimo de 3-4 parágrafos por perspectiva

Responda SEMPRE em formato JSON válido com textos em Markdown."""

        prompt = f"""Analise COMPLETAMENTE esta empresa com múltiplas perspectivas.

# DADOS DA EMPRESA
- **Nome:** {company_data.get('nome_fantasia') or company_data.get('name')}
- **Razão Social:** {company_data.get('razao_social', 'N/A')}
- **CNPJ:** {company_data.get('cnpj', 'N/A')}
- **Setor:** {company_data.get('industry', 'N/A')}
- **Website:** {company_data.get('website', 'N/A')}

# CONTEÚDO DO WEBSITE (FONTE PRINCIPAL)
{website_content[:12000]}

# PESQUISA CONTEXTUAL
{research_context[:8000]}

{employees_text}

{news_text}

# FONTES DISPONÍVEIS PARA CITAÇÃO
{sources_list}

---

Gere uma análise COMPLETA em JSON com a seguinte estrutura:

{{
    "company_overview": {{
        "summary": "Resumo executivo da empresa em 2-3 parágrafos densos. O que a empresa faz, seu posicionamento, principais produtos/serviços. Cite fontes [1], [2], etc.",
        "key_facts": {{
            "founded": "Ano de fundação se disponível",
            "headquarters": "Localização",
            "size_estimate": "Estimativa de tamanho",
            "main_products": ["Produto/Serviço 1", "Produto/Serviço 2"],
            "target_market": "Mercado alvo principal"
        }}
    }},

    "perspectives": {{
        "layperson_view": {{
            "title": "Visão do Leigo",
            "analysis": "TEXTO DENSO (mínimo 3 parágrafos). Como uma pessoa comum, sem conhecimento técnico, entenderia esta empresa ao visitar o site? O que ela oferece de forma simples? A comunicação é clara? O site é acessível? Quais problemas ela resolve para pessoas comuns? Cite fontes."
        }},
        "professional_view": {{
            "title": "Visão do Profissional",
            "analysis": "TEXTO DENSO (mínimo 3 parágrafos). Como um profissional experiente do setor avaliaria esta empresa? Qual o nível de sofisticação técnica? Como se compara com padrões da indústria? Quais certificações ou metodologias utiliza? Qual a profundidade técnica demonstrada? Cite fontes."
        }},
        "supplier_view": {{
            "title": "Visão do Fornecedor",
            "analysis": "TEXTO DENSO (mínimo 3 parágrafos). Como um potencial fornecedor ou parceiro avaliaria esta empresa? Qual o potencial de parceria? Quais são as necessidades aparentes de fornecimento? A empresa parece ser boa pagadora/parceira? Qual o porte para negociações? Cite fontes."
        }},
        "competitor_view": {{
            "title": "Visão do Concorrente",
            "analysis": "TEXTO DENSO (mínimo 3 parágrafos). Como um concorrente direto analisaria esta empresa? Quais são os pontos fortes a temer? Quais as vulnerabilidades a explorar? Onde estão diferenciando? Qual estratégia de mercado aparente? Cite fontes."
        }},
        "customer_view": {{
            "title": "Visão do Cliente",
            "analysis": "TEXTO DENSO (mínimo 3 parágrafos). Como um potencial cliente avaliaria esta empresa? Os benefícios são claros? A proposta de valor é convincente? O que geraria confiança ou desconfiança? Por que escolher ou não escolher esta empresa? Cite fontes."
        }}
    }},

    "team_analysis": {{
        "overview": "Análise da equipe identificada via LinkedIn. Qual o perfil dos profissionais? Qual a experiência média? Há especialistas notáveis? Como a equipe se compara com concorrentes?",
        "key_people": [
            {{
                "name": "Nome do profissional",
                "role": "Cargo",
                "relevance": "Por que esta pessoa é relevante para entender a empresa"
            }}
        ],
        "team_insights": "Insights sobre a cultura e capacidade da equipe baseado nos perfis encontrados"
    }},

    "market_position": {{
        "positioning": "Análise do posicionamento de mercado em 2-3 parágrafos",
        "differentiation": "O que diferencia esta empresa dos concorrentes",
        "target_segments": ["Segmento 1", "Segmento 2"],
        "pricing_indication": "Indicação de posicionamento de preço (premium, competitivo, econômico)"
    }},

    "digital_presence": {{
        "website_quality": "Avaliação da qualidade do website",
        "content_strategy": "Análise da estratégia de conteúdo",
        "seo_observations": "Observações sobre SEO e presença digital",
        "social_media": "Análise da presença em redes sociais se disponível"
    }},

    "news_sentiment": {{
        "overall_sentiment": "positivo/negativo/neutro/misto",
        "key_themes": ["Tema 1 das notícias", "Tema 2"],
        "recent_highlights": "Destaques recentes da mídia em 1-2 parágrafos"
    }},

    "strategic_insights": [
        "Insight estratégico 1 - acionável e específico",
        "Insight estratégico 2 - acionável e específico",
        "Insight estratégico 3 - acionável e específico"
    ],

    "sources_used": ["Lista das fontes efetivamente citadas na análise"],

    "confidence_score": 0.0-1.0,
    "analysis_depth": "Nota sobre a profundidade da análise e limitações"
}}"""

        response = await self._call_claude(prompt, system=system, max_tokens=8000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    async def analyze_competitor_complete(
        self,
        competitor_data: Dict[str, Any],
        website_content: str,
        research_context: str,
        main_company_name: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """
        Análise COMPLETA de concorrente com mesma profundidade da empresa principal
        """
        logger.info("ai_analyze_competitor_complete", competitor=competitor_data.get("name", ""))

        sources_list = "\n".join([f"[{i+1}] {src}" for i, src in enumerate(sources[:15])])

        system = """Você é um ANALISTA DE INTELIGÊNCIA COMPETITIVA especializado no mercado brasileiro.

Analise este CONCORRENTE com a mesma profundidade que analisaria a empresa principal.
Escreva TEXTOS DENSOS com parágrafos substanciais. Cite fontes no formato [1], [2].

Responda SEMPRE em formato JSON válido."""

        prompt = f"""Analise este CONCORRENTE de "{main_company_name}":

# DADOS DO CONCORRENTE
- **Nome:** {competitor_data.get('name')}
- **Website:** {competitor_data.get('website', 'N/A')}
- **Setor:** {competitor_data.get('industry', 'N/A')}

# CONTEÚDO DO WEBSITE
{website_content[:8000]}

# PESQUISA CONTEXTUAL
{research_context[:5000]}

# FONTES
{sources_list}

---

Responda em JSON:
{{
    "competitor_name": "Nome do concorrente",
    "overview": "Resumo em 2-3 parágrafos densos sobre o concorrente. Cite fontes.",

    "comparison_to_main": {{
        "similarities": "O que há de similar com {main_company_name}",
        "differences": "Principais diferenças",
        "competitive_advantages": "Vantagens deste concorrente",
        "competitive_disadvantages": "Desvantagens deste concorrente"
    }},

    "market_position": "Posicionamento de mercado em 2 parágrafos",

    "threat_assessment": {{
        "threat_level": "alto/médio/baixo",
        "explanation": "Por que este nível de ameaça",
        "areas_of_competition": ["Área 1", "Área 2"]
    }},

    "key_insights": [
        "Insight 1 sobre este concorrente",
        "Insight 2 sobre este concorrente"
    ],

    "sources_used": ["Fontes citadas"]
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

    async def analyze_company_swot(
        self,
        company_data: Dict[str, Any],
        market_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera análise SWOT básica (método legado)
        Use analyze_swot_comprehensive para análise completa
        """
        # Redirecionar para método básico simplificado
        return await self._basic_swot(company_data, market_context)

    async def _basic_swot(
        self,
        company_data: Dict[str, Any],
        market_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """SWOT básico sem dados complementares"""
        logger.info("ai_analyze_swot_basic", company=company_data.get("nome_fantasia", ""))

        system = """Você é um analista de inteligência competitiva.
Gere uma análise SWOT básica. Responda em JSON válido."""

        website_content = company_data.get("website_content", "")

        prompt = f"""Análise SWOT para: {company_data.get("nome_fantasia")}

Website: {website_content[:4000] if website_content else "N/A"}
Setor: {company_data.get("industry", "N/A")}
{f"Contexto: {market_context[:2000]}" if market_context else ""}

JSON:
{{"strengths": [{{"point": "...", "impact": "alto/médio/baixo"}}],
"weaknesses": [{{"point": "...", "impact": "alto/médio/baixo"}}],
"opportunities": [{{"point": "...", "timeframe": "curto/médio/longo"}}],
"threats": [{{"point": "...", "probability": "alta/média/baixa"}}],
"summary": "..."}}"""

        response = await self._call_claude(prompt, system=system, max_tokens=2000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response}

    async def analyze_swot_comprehensive(
        self,
        company_data: Dict[str, Any],
        competitors_data: List[Dict[str, Any]],
        employees_data: List[Dict[str, Any]],
        news_data: List[Dict[str, Any]],
        regional_data: Dict[str, Any],
        research_context: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """
        Análise SWOT COMPLETA E ROBUSTA

        Integra TODAS as dimensões de análise:
        1. EMPRESA: Website, produtos, serviços, posicionamento
        2. CONCORRENTES: Análise competitiva detalhada
        3. PESSOAS: Perfil da equipe e talentos
        4. REGIÃO: Ambiente econômico local (PIB, IDHM, população)
        5. MERCADO: Notícias, tendências, cenário econômico
        6. PERCEPÇÕES: Múltiplas perspectivas de stakeholders

        Metodologia baseada em frameworks contemporâneos:
        - VRIO (Value, Rarity, Imitability, Organization)
        - PESTEL (Political, Economic, Social, Technological, Environmental, Legal)
        - Porter's Five Forces
        - Scoring quantitativo para priorização

        Args:
            company_data: Dados completos da empresa
            competitors_data: Lista de concorrentes analisados
            employees_data: Perfis de funcionários
            news_data: Notícias recentes sobre empresa/setor
            regional_data: Dados econômicos regionais (PIB, IDHM, etc)
            research_context: Contexto de pesquisa (Perplexity, Tavily)
            sources: Lista de fontes para citação

        Returns:
            SWOT completo com scoring, priorização e recomendações
        """
        logger.info("ai_analyze_swot_comprehensive", company=company_data.get("nome_fantasia", ""))

        # Preparar fontes para citação
        sources_list = "\n".join([f"[{i+1}] {src}" for i, src in enumerate(sources[:25])])

        # Preparar dados de concorrentes
        competitors_text = ""
        if competitors_data:
            competitors_text = "## ANÁLISE DE CONCORRENTES\n"
            for i, comp in enumerate(competitors_data[:5], 1):
                basic = comp.get("basic_info", {})
                analysis = comp.get("deep_analysis", {})
                competitors_text += f"""
### Concorrente {i}: {basic.get('name', 'N/A')}
- Website: {basic.get('website', 'N/A')}
- Setor: {basic.get('industry', 'N/A')}
- Análise: {analysis.get('overview', 'N/A')[:500] if analysis else 'N/A'}
- Nível de Ameaça: {analysis.get('threat_assessment', {}).get('threat_level', 'N/A') if analysis else 'N/A'}
"""

        # Preparar dados de funcionários
        employees_text = ""
        if employees_data:
            employees_text = "## PERFIL DA EQUIPE\n"
            for emp in employees_data[:10]:
                employees_text += f"- **{emp.get('name', 'N/A')}**: {emp.get('title', 'N/A')} ({emp.get('seniority', 'N/A')})\n"

        # Preparar dados regionais
        regional_text = ""
        if regional_data and regional_data.get("available"):
            pib = regional_data.get("raw_data", {}).get("pib", {}) or {}
            idhm = regional_data.get("raw_data", {}).get("idhm", {}) or {}
            pop = regional_data.get("raw_data", {}).get("populacao", {}) or {}
            profile = regional_data.get("raw_data", {}).get("economic_profile", {}) or {}

            regional_text = f"""## CONTEXTO REGIONAL: {regional_data.get('city', 'N/A')}/{regional_data.get('state', 'N/A')}

### Indicadores Econômicos
- **PIB Municipal:** R$ {pib.get('pib_total', 0)/1_000_000_000:.2f} bilhões
- **PIB per capita:** R$ {pib.get('pib_per_capita', 0):,.2f}
- **Ranking Nacional:** {pib.get('ranking_nacional', 'N/A')}º
- **Setor Dominante:** {profile.get('main_sector', 'N/A')}

### Desenvolvimento Humano
- **IDHM:** {idhm.get('idhm_2010', 'N/A')} ({idhm.get('classificacao_2010', 'N/A')})

### População
- **Total:** {pop.get('populacao', 0):,} habitantes

### Oportunidades Regionais
{chr(10).join('- ' + o for o in regional_data.get('opportunities', []))}

### Ameaças Regionais
{chr(10).join('- ' + t for t in regional_data.get('threats', []))}
"""

        # Preparar notícias
        news_text = ""
        if news_data:
            news_text = "## NOTÍCIAS E CENÁRIO DE MERCADO\n"
            for i, news in enumerate(news_data[:8], 1):
                news_text += f"[{i}] **{news.get('title', 'N/A')}**\n"
                news_text += f"   {news.get('content', news.get('snippet', ''))[:200]}\n\n"

        system = """Você é um CONSULTOR ESTRATÉGICO SÊNIOR especializado em análise SWOT e inteligência competitiva.

Sua tarefa é criar uma análise SWOT PROFUNDA, QUANTIFICADA e ACIONÁVEL.

METODOLOGIA OBRIGATÓRIA:

1. **SCORING QUANTITATIVO** (1-5):
   - Impacto: quanto afeta o negócio
   - Probabilidade/Certeza: quão provável ou certo
   - Urgência: quão rápido precisa ser tratado

2. **MÚLTIPLAS DIMENSÕES**:
   - Interna: recursos, capacidades, processos
   - Externa: mercado, concorrência, economia, regulação
   - Regional: contexto local, oportunidades geográficas
   - Humana: equipe, talentos, cultura

3. **FRAMEWORKS INTEGRADOS**:
   - VRIO para recursos (Valor, Raridade, Imitabilidade, Organização)
   - Porter para competição (5 Forças)
   - PESTEL para macro ambiente

4. **PRIORIZAÇÃO**:
   - Score total = Impacto × Probabilidade × Urgência
   - Ranqueie do mais crítico para menos

5. **RECOMENDAÇÕES ACIONÁVEIS**:
   - Cada ponto deve ter ação clara
   - Defina responsável sugerido
   - Indique horizonte temporal

REGRAS CRÍTICAS:
- Use TODOS os dados fornecidos
- CITE fontes no formato [1], [2]
- Seja ESPECÍFICO - nada genérico
- Textos DENSOS, não bullet points superficiais
- Mínimo 5 itens por quadrante SWOT
- Responda em JSON válido"""

        prompt = f"""Crie uma ANÁLISE SWOT COMPLETA E PROFUNDA para esta empresa.

# DADOS DA EMPRESA
- **Nome:** {company_data.get('nome_fantasia') or company_data.get('name')}
- **Razão Social:** {company_data.get('razao_social', 'N/A')}
- **CNPJ:** {company_data.get('cnpj', 'N/A')}
- **Setor:** {company_data.get('industry', 'N/A')}
- **Website:** {company_data.get('website', 'N/A')}

# CONTEÚDO DO WEBSITE
{company_data.get('website_content', 'N/A')[:8000]}

# PESQUISA CONTEXTUAL
{research_context[:6000]}

{competitors_text}

{employees_text}

{regional_text}

{news_text}

# FONTES PARA CITAÇÃO
{sources_list}

---

Responda em JSON com esta estrutura COMPLETA:

{{
    "executive_summary": "Resumo executivo em 2-3 parágrafos densos. Visão geral da posição estratégica, principais desafios e oportunidades. Cite fontes.",

    "strengths": [
        {{
            "id": "S1",
            "title": "Título do ponto forte",
            "description": "Descrição detalhada em 2-3 sentenças. Por que é força? Evidências? Cite [fontes].",
            "category": "recursos/capacidades/processos/mercado/equipe",
            "vrio_analysis": {{
                "valuable": true/false,
                "rare": true/false,
                "imitable": "fácil/difícil/muito_difícil",
                "organized": true/false
            }},
            "impact_score": 1-5,
            "certainty_score": 1-5,
            "total_score": "impact × certainty",
            "evidence": ["Evidência 1 [fonte]", "Evidência 2 [fonte]"],
            "leverage_action": "Como explorar esta força"
        }}
    ],

    "weaknesses": [
        {{
            "id": "W1",
            "title": "Título da fraqueza",
            "description": "Descrição detalhada. Por que é fraqueza? Impacto? Cite [fontes].",
            "category": "recursos/capacidades/processos/mercado/equipe",
            "impact_score": 1-5,
            "urgency_score": 1-5,
            "total_score": "impact × urgency",
            "root_cause": "Causa raiz identificada",
            "recommendation": "Recomendação de correção",
            "effort_level": "baixo/médio/alto",
            "responsible_area": "Área responsável sugerida"
        }}
    ],

    "opportunities": [
        {{
            "id": "O1",
            "title": "Título da oportunidade",
            "description": "Descrição detalhada. Por que é oportunidade? Potencial? Cite [fontes].",
            "category": "mercado/tecnologia/regulação/regional/tendências",
            "source": "De onde vem: concorrentes/região/mercado/notícias",
            "potential_score": 1-5,
            "probability_score": 1-5,
            "total_score": "potential × probability",
            "timeframe": "curto/médio/longo prazo",
            "required_resources": ["Recurso 1", "Recurso 2"],
            "action_plan": "Plano de ação sugerido",
            "quick_win": true/false
        }}
    ],

    "threats": [
        {{
            "id": "T1",
            "title": "Título da ameaça",
            "description": "Descrição detalhada. Por que é ameaça? Impacto potencial? Cite [fontes].",
            "category": "concorrência/mercado/economia/regulação/tecnologia/regional",
            "source": "De onde vem a ameaça",
            "impact_score": 1-5,
            "probability_score": 1-5,
            "total_score": "impact × probability",
            "timeframe": "iminente/curto/médio/longo prazo",
            "early_warning_signs": ["Sinal 1", "Sinal 2"],
            "mitigation_strategy": "Estratégia de mitigação",
            "contingency_plan": "Plano de contingência se ocorrer"
        }}
    ],

    "strategic_matrix": {{
        "so_strategies": [
            "Estratégia SO (Força + Oportunidade): Como usar S1 para capturar O1"
        ],
        "wo_strategies": [
            "Estratégia WO (Fraqueza + Oportunidade): Como superar W1 para capturar O1"
        ],
        "st_strategies": [
            "Estratégia ST (Força + Ameaça): Como usar S1 para neutralizar T1"
        ],
        "wt_strategies": [
            "Estratégia WT (Fraqueza + Ameaça): Como minimizar W1 para evitar T1"
        ]
    }},

    "competitive_position": {{
        "market_position": "líder/desafiante/seguidor/nicho",
        "competitive_advantage": "Vantagem competitiva sustentável identificada",
        "differentiation": "Como se diferencia dos concorrentes",
        "vulnerability": "Principal vulnerabilidade competitiva"
    }},

    "regional_fit": {{
        "alignment_score": 1-10,
        "regional_advantages": ["Vantagem regional 1", "Vantagem regional 2"],
        "regional_challenges": ["Desafio regional 1"],
        "expansion_potential": "Análise de potencial de expansão na região"
    }},

    "team_assessment": {{
        "strengths": ["Força da equipe 1"],
        "gaps": ["Lacuna identificada 1"],
        "recommendation": "Recomendação para equipe"
    }},

    "priority_actions": [
        {{
            "priority": 1,
            "action": "Ação prioritária 1",
            "rationale": "Por que é prioridade",
            "related_swot": ["S1", "O2"],
            "timeframe": "30/60/90 dias",
            "expected_outcome": "Resultado esperado"
        }}
    ],

    "risk_register": [
        {{
            "risk": "Risco identificado",
            "probability": "alta/média/baixa",
            "impact": "alto/médio/baixo",
            "mitigation": "Ação de mitigação",
            "owner": "Responsável sugerido"
        }}
    ],

    "sources_used": ["Lista de fontes efetivamente citadas"],

    "methodology_note": "Nota sobre a metodologia aplicada e limitações da análise",

    "confidence_score": 0.0-1.0,

    "next_steps": [
        "Próximo passo recomendado 1",
        "Próximo passo recomendado 2"
    ]
}}"""

        response = await self._call_claude(prompt, system=system, max_tokens=10000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
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
