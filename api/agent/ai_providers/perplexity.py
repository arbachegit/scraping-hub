"""
Perplexity AI provider implementation.
"""

from typing import Optional

import httpx
import structlog

from api.agent.ai_providers.base import BaseAIProvider
from api.agent.models import AIProviderResponse

logger = structlog.get_logger()


class PerplexityProvider(BaseAIProvider):
    """Perplexity AI provider for natural language understanding."""

    name = "perplexity"
    base_url = "https://api.perplexity.ai"

    def __init__(self, api_key: str):
        """
        Initialize the Perplexity provider.

        Args:
            api_key: Perplexity API key
        """
        super().__init__(api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> AIProviderResponse:
        """
        Generate a completion using Perplexity API.

        Uses sonar-pro model for best accuracy.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            AIProviderResponse with the completion result
        """
        if not self.is_available:
            return AIProviderResponse(
                success=False,
                content="",
                provider=self.name,
                error="API key not configured",
            )

        self._log_request(prompt[:100])

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "sonar-pro",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code != 200:
                    error_msg = f"API error: {response.status_code} - {response.text}"
                    self._log_response(False, error_msg)
                    return AIProviderResponse(
                        success=False,
                        content="",
                        provider=self.name,
                        error=error_msg,
                    )

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                self._log_response(True)
                return AIProviderResponse(
                    success=True,
                    content=content,
                    provider=self.name,
                    raw_response=data,
                )

        except httpx.TimeoutException:
            error_msg = "Request timeout"
            self._log_response(False, error_msg)
            return AIProviderResponse(
                success=False,
                content="",
                provider=self.name,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            self._log_response(False, error_msg)
            return AIProviderResponse(
                success=False,
                content="",
                provider=self.name,
                error=error_msg,
            )
