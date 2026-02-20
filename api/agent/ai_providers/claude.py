"""
Claude (Anthropic) AI provider implementation.
"""

from typing import Optional

import structlog
from anthropic import AsyncAnthropic

from api.agent.ai_providers.base import BaseAIProvider
from api.agent.models import AIProviderResponse

logger = structlog.get_logger()


class ClaudeProvider(BaseAIProvider):
    """Claude AI provider using the Anthropic SDK."""

    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the Claude provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-sonnet-4-20250514)
        """
        super().__init__(api_key)
        self.model = model
        self._client: Optional[AsyncAnthropic] = None
        if self.is_available:
            self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> AIProviderResponse:
        """
        Generate a completion using Claude API.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            AIProviderResponse with the completion result
        """
        if not self.is_available or not self._client:
            return AIProviderResponse(
                success=False,
                content="",
                provider=self.name,
                error="API key not configured",
            )

        self._log_request(prompt[:100])

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if temperature > 0:
                kwargs["temperature"] = temperature

            response = await self._client.messages.create(**kwargs)

            content = ""
            if response.content:
                content = response.content[0].text

            self._log_response(True)
            return AIProviderResponse(
                success=True,
                content=content,
                provider=self.name,
                raw_response={
                    "id": response.id,
                    "model": response.model,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                },
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
