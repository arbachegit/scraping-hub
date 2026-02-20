"""
OpenAI provider implementation.
"""

from typing import Optional

import httpx
import structlog

from api.agent.ai_providers.base import BaseAIProvider
from api.agent.models import AIProviderResponse

logger = structlog.get_logger()


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider for GPT models."""

    name = "openai"
    base_url = "https://api.openai.com/v1"

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
        """
        super().__init__(api_key)
        self.model = model

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> AIProviderResponse:
        """
        Generate a completion using OpenAI API.

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
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
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
