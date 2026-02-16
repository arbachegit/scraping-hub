"""
Configurações compartilhadas para MCP Servers
"""

from dataclasses import dataclass

from config.settings import settings


@dataclass
class MCPConfig:
    """Configurações centralizadas para MCP Servers"""

    # Serper
    serper_api_key: str = settings.serper_api_key
    serper_base_url: str = settings.serper_base_url

    # BrasilAPI
    brasilapi_base_url: str = settings.brasil_api_url

    # Apollo
    apollo_api_key: str = settings.apollo_api_key
    apollo_base_url: str = settings.apollo_base_url

    # CNPJá
    cnpja_api_key: str = settings.cnpja_api_key
    cnpja_base_url: str = settings.cnpja_base_url

    # Perplexity
    perplexity_api_key: str = settings.perplexity_api_key
    perplexity_base_url: str = settings.perplexity_base_url

    # Brasil Data Hub (Supabase externo)
    brasil_data_hub_url: str = settings.brasil_data_hub_url
    brasil_data_hub_key: str = settings.brasil_data_hub_key

    # Supabase principal (IconsAI)
    supabase_url: str = settings.supabase_url
    supabase_key: str = settings.supabase_service_key

    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Cria configuração a partir das variáveis de ambiente"""
        return cls()

    def validate(self) -> dict[str, bool]:
        """Valida quais serviços estão configurados"""
        return {
            "serper": bool(self.serper_api_key),
            "brasilapi": True,  # Não requer autenticação
            "apollo": bool(self.apollo_api_key),
            "cnpja": bool(self.cnpja_api_key),
            "perplexity": bool(self.perplexity_api_key),
            "brasil_data_hub": bool(self.brasil_data_hub_url and self.brasil_data_hub_key),
            "supabase": bool(self.supabase_url and self.supabase_key),
        }
