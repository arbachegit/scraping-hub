"""
Scraping Hub v2.0 - Settings
Configuracoes centralizadas do sistema
Business Intelligence Brasil
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes do Scraping Hub v2.0"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ===========================================
    # Environment
    # ===========================================
    environment: str = "development"
    debug: bool = False

    # ===========================================
    # APIs de Dados Brasileiros
    # ===========================================

    # BrasilAPI - Dados públicos (CNPJ, CEP, etc)
    brasil_api_url: str = "https://brasilapi.com.br/api"

    # ===========================================
    # APIs de Busca
    # ===========================================

    # Serper.dev - Google Search
    serper_api_key: str = ""
    serper_base_url: str = "https://google.serper.dev"
    serper_rate_limit: int = 100

    # Tavily - AI Search & News
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com"
    tavily_rate_limit: int = 50

    # ===========================================
    # APIs de AI/Research
    # ===========================================

    # Perplexity - AI Research
    perplexity_api_key: str = ""
    perplexity_base_url: str = "https://api.perplexity.ai"
    perplexity_rate_limit: int = 50

    # Anthropic Claude - AI Analysis
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # ===========================================
    # APIs de Dados B2B
    # ===========================================

    # Apollo.io - LinkedIn & Contatos
    apollo_api_key: str = ""
    apollo_base_url: str = "https://api.apollo.io/v1"
    apollo_rate_limit: int = 100

    # ===========================================
    # Banco de Dados
    # ===========================================

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""

    # Redis (opcional)
    redis_url: str = "redis://localhost:6379/0"

    # ===========================================
    # Rate Limiting & Cache
    # ===========================================

    rate_limit_period: int = 60
    cache_ttl: int = 3600
    cache_max_size: int = 1000

    # ===========================================
    # Logging
    # ===========================================

    log_level: str = "INFO"
    log_format: str = "json"

    # ===========================================
    # Autenticação API
    # ===========================================

    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # ===========================================
    # Web Scraping
    # ===========================================

    playwright_headless: bool = True
    playwright_timeout: int = 30000
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # ===========================================
    # Propriedades Computadas
    # ===========================================

    @property
    def is_production(self) -> bool:
        """Verifica se está em produção"""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Verifica se está em desenvolvimento"""
        return self.environment == "development"

    @property
    def has_serper(self) -> bool:
        """Verifica se Serper está configurado"""
        return bool(self.serper_api_key)

    @property
    def has_tavily(self) -> bool:
        """Verifica se Tavily está configurado"""
        return bool(self.tavily_api_key)

    @property
    def has_perplexity(self) -> bool:
        """Verifica se Perplexity está configurado"""
        return bool(self.perplexity_api_key)

    @property
    def has_apollo(self) -> bool:
        """Verifica se Apollo está configurado"""
        return bool(self.apollo_api_key)

    @property
    def has_anthropic(self) -> bool:
        """Verifica se Anthropic está configurado"""
        return bool(self.anthropic_api_key)

    @property
    def has_supabase(self) -> bool:
        """Verifica se Supabase está configurado"""
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache()
def get_settings() -> Settings:
    """Retorna singleton das configuracoes"""
    return Settings()


# Alias para uso direto
settings = get_settings()
