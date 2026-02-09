"""
Keyword Extractor Service
Extrai palavras-chave dos blocos de analise para busca de concorrentes
"""

import re
from typing import Any, Dict, List, Set

import structlog

from .ai_analyzer import AIAnalyzer

logger = structlog.get_logger()


class KeywordExtractor:
    """
    Extrator de palavras-chave para busca de concorrentes

    Funcionalidades:
    - Extrai keywords de cada bloco de analise
    - Identifica termos de setor/industria
    - Identifica competencias e capacidades
    - Gera queries para busca de concorrentes
    """

    # Stopwords em portugues para filtrar
    STOPWORDS = {
        "a",
        "o",
        "e",
        "de",
        "da",
        "do",
        "em",
        "para",
        "com",
        "por",
        "que",
        "um",
        "uma",
        "os",
        "as",
        "dos",
        "das",
        "no",
        "na",
        "nos",
        "nas",
        "ao",
        "aos",
        "pela",
        "pelo",
        "pelos",
        "pelas",
        "se",
        "ou",
        "mas",
        "como",
        "mais",
        "muito",
        "bem",
        "pode",
        "tem",
        "ser",
        "ter",
        "foi",
        "sua",
        "seu",
        "seus",
        "suas",
        "este",
        "esta",
        "esse",
        "essa",
        "isso",
        "isto",
        "aqui",
        "ali",
        "la",
        "ele",
        "ela",
        "eles",
        "elas",
        "voces",
        "empresa",
        "empresas",
        "cliente",
        "clientes",
        "servico",
        "servicos",
        "produto",
        "produtos",
        "mercado",
        "area",
        "trabalho",
        "equipe",
        "time",
        "anos",
        "ano",
        "brasil",
        "brasileiro",
        "forma",
        "tipo",
        "tipos",
        "parte",
        "partes",
        "exemplo",
        "cada",
    }

    def __init__(self):
        self.ai_analyzer = AIAnalyzer()
        logger.info("keyword_extractor_init")

    async def close(self):
        await self.ai_analyzer.close()

    async def extract_from_analysis(
        self, company_name: str, blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extrai palavras-chave de todos os blocos de analise

        Returns:
            {
                "keywords": ["tech", "saas", "b2b", ...],
                "keywords_by_block": {
                    "1_empresa": ["..."],
                    "4_ativo_humano": ["..."],
                    ...
                },
                "sector_keywords": ["tecnologia", "software"],
                "capability_keywords": ["automacao", "IA"],
                "search_queries": ["empresas tecnologia IA Brasil"]
            }
        """
        logger.info("keyword_extraction_start", company=company_name)

        result = {
            "keywords": [],
            "keywords_by_block": {},
            "sector_keywords": [],
            "capability_keywords": [],
            "search_queries": [],
        }

        # Blocos mais relevantes para concorrentes
        priority_blocks = [
            "1_empresa",  # Setor, mercado, atuacao
            "4_ativo_humano",  # Competencias
            "5_capacidade",  # O que entregam
            "6_comunicacao",  # Como se posicionam
        ]

        all_keywords: Set[str] = set()

        # Extrair de cada bloco
        for block_key in priority_blocks:
            block = blocks.get(block_key, {})
            content = block.get("content", "")

            if not content:
                continue

            # Extrai keywords do bloco
            block_keywords = await self._extract_keywords_from_text(content, company_name)
            result["keywords_by_block"][block_key] = block_keywords
            all_keywords.update(block_keywords)

        # Classificar keywords
        result["keywords"] = list(all_keywords)
        result["sector_keywords"] = self._classify_sector_keywords(all_keywords)
        result["capability_keywords"] = self._classify_capability_keywords(all_keywords)

        # Gerar queries de busca
        result["search_queries"] = self._generate_search_queries(
            company_name, result["sector_keywords"], result["capability_keywords"]
        )

        logger.info(
            "keyword_extraction_done",
            company=company_name,
            total_keywords=len(all_keywords),
            queries=len(result["search_queries"]),
        )

        return result

    async def _extract_keywords_from_text(self, text: str, company_name: str) -> List[str]:
        """
        Extrai palavras-chave de um texto usando Claude

        Combina:
        1. Extracao via AI (mais semantica)
        2. Extracao por frequencia (backup)
        """
        try:
            # Usar AI para extracao semantica
            keywords = await self._extract_with_ai(text, company_name)

            if keywords:
                return keywords

        except Exception as e:
            logger.warning("ai_extraction_failed", error=str(e))

        # Fallback: extracao por frequencia
        return self._extract_by_frequency(text)

    async def _extract_with_ai(self, text: str, company_name: str) -> List[str]:
        """Usa Claude para extrair keywords semanticamente"""

        prompt = f"""Analise o texto abaixo sobre a empresa {company_name} e extraia as PALAVRAS-CHAVE mais relevantes para encontrar empresas concorrentes ou similares.

TEXTO:
{text[:3000]}

REGRAS:
1. Extraia entre 5 e 15 palavras-chave
2. Foque em: setor, tecnologias, servicos, tipo de cliente, modelo de negocio
3. Ignore o nome da propria empresa
4. Use termos em portugues
5. Prefira substantivos e termos tecnicos
6. NAO inclua verbos ou adjetivos genericos

Retorne APENAS as palavras-chave separadas por virgula, sem explicacao.

Exemplo de saida: consultoria, tecnologia, SaaS, B2B, automacao, inteligencia artificial, startups"""

        response = await self.ai_analyzer._call_claude(prompt=prompt, max_tokens=200)

        if response:
            # Parse da resposta
            keywords = [
                kw.strip().lower()
                for kw in response.split(",")
                if kw.strip() and len(kw.strip()) > 2
            ]
            # Filtrar stopwords e nome da empresa
            keywords = [
                kw for kw in keywords if kw not in self.STOPWORDS and company_name.lower() not in kw
            ]
            return keywords[:15]

        return []

    def _extract_by_frequency(self, text: str) -> List[str]:
        """Extracao simples por frequencia de palavras"""

        # Limpar texto
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)

        # Tokenizar
        words = text.split()

        # Filtrar stopwords e palavras curtas
        words = [w for w in words if w not in self.STOPWORDS and len(w) > 3 and not w.isdigit()]

        # Contar frequencia
        freq: Dict[str, int] = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1

        # Ordenar por frequencia
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)

        # Retornar top 10
        return [word for word, _ in sorted_words[:10]]

    def _classify_sector_keywords(self, keywords: Set[str]) -> List[str]:
        """Identifica keywords relacionadas a setor/industria"""

        sector_indicators = {
            "tecnologia",
            "tech",
            "software",
            "saas",
            "fintech",
            "healthtech",
            "edtech",
            "agtech",
            "legaltech",
            "insurtech",
            "proptech",
            "varejo",
            "retail",
            "e-commerce",
            "ecommerce",
            "marketplace",
            "financeiro",
            "banco",
            "financa",
            "credito",
            "pagamento",
            "saude",
            "health",
            "medicina",
            "farmacia",
            "hospital",
            "educacao",
            "ensino",
            "treinamento",
            "capacitacao",
            "logistica",
            "transporte",
            "delivery",
            "frete",
            "industria",
            "manufatura",
            "fabricacao",
            "producao",
            "agro",
            "agronegocio",
            "agricultura",
            "rural",
            "energia",
            "sustentabilidade",
            "renovavel",
            "solar",
            "construcao",
            "imobiliario",
            "imoveis",
            "engenharia",
            "consultoria",
            "assessoria",
            "servicos",
            "terceirizacao",
            "marketing",
            "publicidade",
            "comunicacao",
            "midia",
            "telecomunicacoes",
            "telecom",
            "conectividade",
        }

        return [kw for kw in keywords if kw in sector_indicators]

    def _classify_capability_keywords(self, keywords: Set[str]) -> List[str]:
        """Identifica keywords relacionadas a capacidades/tecnologias"""

        capability_indicators = {
            "ia",
            "inteligencia artificial",
            "machine learning",
            "ml",
            "automacao",
            "robotica",
            "rpa",
            "bot",
            "dados",
            "data",
            "analytics",
            "bi",
            "big data",
            "cloud",
            "nuvem",
            "aws",
            "azure",
            "gcp",
            "api",
            "integracao",
            "plataforma",
            "sistema",
            "mobile",
            "app",
            "aplicativo",
            "ios",
            "android",
            "web",
            "frontend",
            "backend",
            "fullstack",
            "blockchain",
            "cripto",
            "defi",
            "web3",
            "iot",
            "sensores",
            "conectado",
            "smart",
            "seguranca",
            "ciberseguranca",
            "protecao",
            "compliance",
            "erp",
            "crm",
            "gestao",
            "administrativo",
            "design",
            "ux",
            "ui",
            "experiencia",
            "interface",
        }

        return [kw for kw in keywords if kw in capability_indicators]

    def _generate_search_queries(
        self, company_name: str, sector_keywords: List[str], capability_keywords: List[str]
    ) -> List[str]:
        """Gera queries para busca de concorrentes no Perplexity"""

        queries = []

        # Query principal: setor + capacidade
        if sector_keywords and capability_keywords:
            query = f"empresas brasileiras {' '.join(sector_keywords[:2])} {' '.join(capability_keywords[:2])} mesmo porte {company_name}"
            queries.append(query)

        # Query por setor apenas
        if sector_keywords:
            query = f"principais empresas {' '.join(sector_keywords[:3])} Brasil startups"
            queries.append(query)

        # Query por capacidade
        if capability_keywords:
            query = f"empresas especialistas {' '.join(capability_keywords[:3])} Brasil"
            queries.append(query)

        # Query generica
        if not queries:
            queries.append(f"empresas concorrentes {company_name} Brasil mesmo segmento")

        return queries[:3]  # Limitar a 3 queries

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
