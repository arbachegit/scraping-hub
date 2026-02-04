"""
Scraping Hub - Settings
Configuracoes centralizadas do sistema
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Configuracoes do Scraping Hub"""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Coresignal
    coresignal_api_key: str = Field(default="", env="CORESIGNAL_API_KEY")
    coresignal_base_url: str = Field(
        default="https://api.coresignal.com/cdapi/v1",
        env="CORESIGNAL_BASE_URL"
    )
    coresignal_rate_limit: int = Field(default=100, env="CORESIGNAL_RATE_LIMIT")

    # Proxycurl
    proxycurl_api_key: str = Field(default="", env="PROXYCURL_API_KEY")
    proxycurl_base_url: str = Field(
        default="https://nubela.co/proxycurl/api/v2",
        env="PROXYCURL_BASE_URL"
    )
    proxycurl_rate_limit: int = Field(default=50, env="PROXYCURL_RATE_LIMIT")

    # Firecrawl
    firecrawl_api_key: str = Field(default="", env="FIRECRAWL_API_KEY")
    firecrawl_base_url: str = Field(
        default="https://api.firecrawl.dev",
        env="FIRECRAWL_BASE_URL"
    )
    firecrawl_rate_limit: int = Field(default=200, env="FIRECRAWL_RATE_LIMIT")

    # Rate Limiting
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")

    # Supabase
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_service_key: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Cache
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Retorna singleton das configuracoes"""
    return Settings()


# Alias para uso direto
settings = get_settings()
