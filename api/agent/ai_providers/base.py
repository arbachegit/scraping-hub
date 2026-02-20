"""
Base class for AI providers.
"""

from abc import ABC, abstractmethod
from typing import Optional

import structlog

from api.agent.models import AIProviderResponse

logger = structlog.get_logger()


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "base"

    def __init__(self, api_key: str):
        """
        Initialize the provider.

        Args:
            api_key: The API key for authentication
        """
        self.api_key = api_key
        self._is_available = bool(api_key)

    @property
    def is_available(self) -> bool:
        """Check if the provider is available (has API key)."""
        return self._is_available

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> AIProviderResponse:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response

        Returns:
            AIProviderResponse with the completion result
        """
        pass

    def _log_request(self, prompt_preview: str):
        """Log the start of a request."""
        logger.info(
            "ai_provider_request",
            provider=self.name,
            prompt_length=len(prompt_preview),
        )

    def _log_response(self, success: bool, error: Optional[str] = None):
        """Log the response from the provider."""
        if success:
            logger.info("ai_provider_response", provider=self.name, success=True)
        else:
            logger.warning(
                "ai_provider_response",
                provider=self.name,
                success=False,
                error=error,
            )
