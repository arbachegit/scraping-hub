"""
Regional Intelligence Service
Inteligência regional usando dados fiscais e socioeconômicos brasileiros
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx
import structlog

from config.settings import settings

logger = structlog.get_logger()


class RegionalIntelService:
    """
    Serviço de inteligência regional brasileira

    Conecta com:
    - Brasil Data Hub (MCP) - PIB, IDHM, População
    - Base fiscal de municípios
    - Dados de políticos da região

    Usado para contextualizar análises SWOT com ambiente econômico regional
    """

    # Estados brasileiros para normalização
    ESTADOS = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
        "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
        "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
        "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
        "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
        "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
        "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"
    }

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

        # Supabase fiscal database config
        self.fiscal_supabase_url = settings.fiscal_supabase_url if hasattr(settings, 'fiscal_supabase_url') else None
        self.fiscal_supabase_key = settings.fiscal_supabase_key if hasattr(settings, 'fiscal_supabase_key') else None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def extract_city_state(self, address: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extrai cidade e estado de um endereço"""
        city = address.get("municipio") or address.get("cidade") or address.get("city")
        state = address.get("uf") or address.get("estado") or address.get("state")

        # Normalizar estado para sigla
        if state and len(state) > 2:
            for sigla, nome in self.ESTADOS.items():
                if nome.lower() == state.lower():
                    state = sigla
                    break

        return city, state

    async def get_municipality_code(self, city: str, state: Optional[str] = None) -> Optional[int]:
        """
        Busca código IBGE do município

        Usa a API BrasilAPI como fallback
        """
        try:
            # Tentar via BrasilAPI
            url = f"https://brasilapi.com.br/api/ibge/municipios/v1/{state or ''}"
            response = await self.client.get(url)

            if response.status_code == 200:
                municipios = response.json()
                city_lower = city.lower().strip()

                for mun in municipios:
                    if mun.get("nome", "").lower() == city_lower:
                        return int(mun.get("codigo_ibge"))

        except Exception as e:
            logger.warning("municipality_code_error", city=city, error=str(e))

        return None

    async def get_regional_context(
        self,
        city: str,
        state: Optional[str] = None,
        codigo_ibge: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtém contexto regional completo para uma cidade

        Retorna:
        - PIB e composição econômica
        - IDHM e componentes
        - População e crescimento
        - Indicadores fiscais
        - Ranking regional e nacional
        """
        logger.info("regional_intel_context", city=city, state=state)

        context = {
            "city": city,
            "state": state,
            "codigo_ibge": codigo_ibge,
            "pib": None,
            "idhm": None,
            "populacao": None,
            "fiscal": None,
            "rankings": {},
            "economic_profile": None,
            "regional_analysis": None
        }

        # Buscar código IBGE se não fornecido
        if not codigo_ibge and city:
            codigo_ibge = await self.get_municipality_code(city, state)
            context["codigo_ibge"] = codigo_ibge

        if not codigo_ibge:
            logger.warning("regional_intel_no_ibge", city=city)
            return context

        # Buscar dados em paralelo (simulando chamadas MCP)
        # Na prática, as chamadas MCP serão feitas diretamente no serviço que usa este
        try:
            # Buscar via BrasilAPI como alternativa
            tasks = [
                self._get_pib_data(codigo_ibge),
                self._get_idhm_data(codigo_ibge),
                self._get_population_data(codigo_ibge),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            if not isinstance(results[0], Exception):
                context["pib"] = results[0]
            if not isinstance(results[1], Exception):
                context["idhm"] = results[1]
            if not isinstance(results[2], Exception):
                context["populacao"] = results[2]

            # Gerar análise do perfil econômico
            context["economic_profile"] = self._analyze_economic_profile(context)
            context["regional_analysis"] = self._generate_regional_analysis(context)

        except Exception as e:
            logger.error("regional_intel_error", error=str(e))

        return context

    async def _get_pib_data(self, codigo_ibge: int) -> Dict[str, Any]:
        """Busca dados de PIB via API"""
        # Esta função será substituída por chamadas MCP no uso real
        return {}

    async def _get_idhm_data(self, codigo_ibge: int) -> Dict[str, Any]:
        """Busca dados de IDHM"""
        return {}

    async def _get_population_data(self, codigo_ibge: int) -> Dict[str, Any]:
        """Busca dados populacionais"""
        return {}

    def _analyze_economic_profile(self, context: Dict) -> Dict[str, Any]:
        """Analisa perfil econômico da região"""
        profile = {
            "economic_size": "unknown",
            "main_sector": "unknown",
            "development_level": "unknown",
            "growth_trend": "unknown",
            "business_environment": "unknown"
        }

        pib = context.get("pib", {})
        idhm = context.get("idhm", {})
        pop = context.get("populacao", {})

        # Classificar tamanho econômico
        pib_total = pib.get("pib_total", 0) if pib else 0
        if pib_total > 100_000_000_000:  # > 100 bi
            profile["economic_size"] = "muito_grande"
        elif pib_total > 10_000_000_000:  # > 10 bi
            profile["economic_size"] = "grande"
        elif pib_total > 1_000_000_000:  # > 1 bi
            profile["economic_size"] = "medio"
        else:
            profile["economic_size"] = "pequeno"

        # Setor principal
        if pib:
            servicos = pib.get("pib_servicos", 0) or 0
            industria = pib.get("pib_industria", 0) or 0
            agro = pib.get("pib_agropecuaria", 0) or 0

            if servicos > industria and servicos > agro:
                profile["main_sector"] = "servicos"
            elif industria > servicos and industria > agro:
                profile["main_sector"] = "industria"
            else:
                profile["main_sector"] = "agropecuaria"

        # Nível de desenvolvimento (IDHM)
        idhm_value = idhm.get("idhm_2010", 0) if idhm else 0
        if idhm_value >= 0.8:
            profile["development_level"] = "muito_alto"
        elif idhm_value >= 0.7:
            profile["development_level"] = "alto"
        elif idhm_value >= 0.6:
            profile["development_level"] = "medio"
        elif idhm_value >= 0.5:
            profile["development_level"] = "baixo"
        else:
            profile["development_level"] = "muito_baixo"

        return profile

    def _generate_regional_analysis(self, context: Dict) -> str:
        """Gera análise textual da região"""
        city = context.get("city", "")
        state = context.get("state", "")
        profile = context.get("economic_profile", {})
        pib = context.get("pib", {})
        idhm = context.get("idhm", {})
        pop = context.get("populacao", {})

        parts = []

        # Introdução
        parts.append(f"## Contexto Regional: {city}/{state}")

        # PIB
        if pib:
            pib_total = pib.get("pib_total", 0)
            pib_per_capita = pib.get("pib_per_capita", 0)
            ranking = pib.get("ranking_nacional", "N/A")

            if pib_total:
                pib_formatted = f"R$ {pib_total/1_000_000_000:.2f} bilhões"
                parts.append(f"\n**PIB Municipal:** {pib_formatted}")
                parts.append(f"**PIB per capita:** R$ {pib_per_capita:,.2f}")
                parts.append(f"**Ranking Nacional:** {ranking}º lugar")

        # IDHM
        if idhm:
            idhm_value = idhm.get("idhm_2010", 0)
            classificacao = idhm.get("classificacao_2010", "N/A")
            parts.append(f"\n**IDHM (2010):** {idhm_value} - {classificacao}")

        # População
        if pop:
            populacao = pop.get("populacao", 0)
            parts.append(f"\n**População:** {populacao:,} habitantes")

        # Perfil econômico
        if profile:
            size_map = {
                "muito_grande": "economia de grande porte",
                "grande": "economia significativa",
                "medio": "economia de médio porte",
                "pequeno": "economia em desenvolvimento"
            }

            sector_map = {
                "servicos": "setor de serviços",
                "industria": "setor industrial",
                "agropecuaria": "setor agropecuário"
            }

            size_text = size_map.get(profile.get("economic_size", ""), "")
            sector_text = sector_map.get(profile.get("main_sector", ""), "")

            if size_text or sector_text:
                parts.append(f"\n**Perfil:** {city} possui {size_text}, com predominância do {sector_text}.")

        return "\n".join(parts)

    async def get_region_for_swot(
        self,
        company_address: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepara dados regionais formatados para análise SWOT

        Retorna dados estruturados para serem usados no SWOT:
        - Oportunidades regionais
        - Ameaças regionais
        - Contexto competitivo local
        """
        city, state = self.extract_city_state(company_address)

        if not city:
            return {"available": False, "reason": "Cidade não identificada"}

        context = await self.get_regional_context(city, state)

        swot_data = {
            "available": True,
            "city": city,
            "state": state,
            "context_text": context.get("regional_analysis", ""),

            # Para SWOT - Oportunidades
            "opportunities": self._extract_opportunities(context),

            # Para SWOT - Ameaças
            "threats": self._extract_threats(context),

            # Dados brutos para Claude analisar
            "raw_data": {
                "pib": context.get("pib"),
                "idhm": context.get("idhm"),
                "populacao": context.get("populacao"),
                "economic_profile": context.get("economic_profile")
            }
        }

        return swot_data

    def _extract_opportunities(self, context: Dict) -> List[str]:
        """Extrai oportunidades regionais"""
        opportunities = []
        profile = context.get("economic_profile", {})

        if profile.get("development_level") in ["muito_alto", "alto"]:
            opportunities.append("Região com alto IDH indica mercado consumidor qualificado")

        if profile.get("economic_size") in ["muito_grande", "grande"]:
            opportunities.append("Economia regional robusta oferece base de clientes potenciais")

        if profile.get("main_sector") == "servicos":
            opportunities.append("Economia baseada em serviços favorece parcerias B2B")

        return opportunities

    def _extract_threats(self, context: Dict) -> List[str]:
        """Extrai ameaças regionais"""
        threats = []
        profile = context.get("economic_profile", {})

        if profile.get("economic_size") in ["muito_grande", "grande"]:
            threats.append("Alta competitividade em mercados consolidados")

        if profile.get("development_level") in ["baixo", "muito_baixo"]:
            threats.append("Baixo desenvolvimento regional pode limitar crescimento")

        return threats

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
