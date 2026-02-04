"""
Scraping Hub - Settings
Configuracoes centralizadas do sistema
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes do Scraping Hub"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    environment: str = "development"
    debug: bool = False

    # Coresignal
    coresignal_api_key: str = ""
    coresignal_base_url: str = "https://api.coresignal.com/cdapi/v1"
    coresignal_rate_limit: int = 100

    # Proxycurl
    proxycurl_api_key: str = ""
    proxycurl_base_url: str = "https://nubela.co/proxycurl/api/v2"
    proxycurl_rate_limit: int = 50

    # Firecrawl
    firecrawl_api_key: str = ""
    firecrawl_base_url: str = "https://api.firecrawl.dev"
    firecrawl_rate_limit: int = 200

    # Rate Limiting
    rate_limit_period: int = 60

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Cache
    cache_ttl: int = 3600
    cache_max_size: int = 1000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache()
def get_settings() -> Settings:
    """Retorna singleton das configuracoes"""
    return Settings()


# Alias para uso direto
settings = get_settings()
