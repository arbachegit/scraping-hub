"""
AI Provider Chain with fallback support.

Order: Perplexity -> Claude -> OpenAI
"""

from typing import List, Optional

import structlog

from api.agent.ai_providers.base import BaseAIProvider
from api.agent.ai_providers.claude import ClaudeProvider
from api.agent.ai_providers.openai import OpenAIProvider
from api.agent.ai_providers.perplexity import PerplexityProvider
from api.agent.models import AIProviderResponse
from config.settings import settings

logger = structlog.get_logger()


class AIProviderChain:
    """
    Manages multiple AI providers with automatic fallback.

    Fallback order: Perplexity -> Claude -> OpenAI
    """

    def __init__(
        self,
        perplexity_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize the provider chain.

        Args:
            perplexity_api_key: Perplexity API key
            anthropic_api_key: Anthropic API key
            openai_api_key: OpenAI API key
        """
        self.providers: List[BaseAIProvider] = []

        # Add providers in priority order
        if perplexity_api_key:
            self.providers.append(PerplexityProvider(perplexity_api_key))

        if anthropic_api_key:
            self.providers.append(ClaudeProvider(anthropic_api_key))

        if openai_api_key:
            self.providers.append(OpenAIProvider(openai_api_key))

        logger.info(
            "ai_provider_chain_initialized",
            available_providers=[p.name for p in self.providers if p.is_available],
        )

    @classmethod
    def from_settings(cls) -> "AIProviderChain":
        """
        Create a provider chain from application settings.

        Returns:
            AIProviderChain configured with available API keys
        """
        return cls(
            perplexity_api_key=settings.perplexity_api_key,
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=settings.openai_api_key,
        )

    @property
    def has_providers(self) -> bool:
        """Check if any provider is available."""
        return any(p.is_available for p in self.providers)

    @property
    def available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [p.name for p in self.providers if p.is_available]

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> AIProviderResponse:
        """
        Generate a completion using the provider chain.

        Tries each provider in order until one succeeds.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            AIProviderResponse from the first successful provider
        """
        if not self.has_providers:
            return AIProviderResponse(
                success=False,
                content="",
                provider="none",
                error="No AI providers configured",
            )

        errors = []

        for provider in self.providers:
            if not provider.is_available:
                continue

            logger.info("ai_chain_trying_provider", provider=provider.name)

            response = await provider.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if response.success:
                logger.info(
                    "ai_chain_success",
                    provider=provider.name,
                    content_length=len(response.content),
                )
                return response

            errors.append(f"{provider.name}: {response.error}")
            logger.warning(
                "ai_chain_provider_failed",
                provider=provider.name,
                error=response.error,
            )

        # All providers failed
        combined_error = "; ".join(errors)
        logger.error("ai_chain_all_failed", errors=combined_error)

        return AIProviderResponse(
            success=False,
            content="",
            provider="chain",
            error=f"All providers failed: {combined_error}",
        )


# Global provider chain instance (lazy initialization)
_provider_chain: Optional[AIProviderChain] = None


def get_provider_chain() -> AIProviderChain:
    """
    Get the global provider chain instance.

    Creates the chain on first access using application settings.

    Returns:
        AIProviderChain instance
    """
    global _provider_chain
    if _provider_chain is None:
        _provider_chain = AIProviderChain.from_settings()
    return _provider_chain
