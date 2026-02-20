"""
Prompts module for the AI Agent.
"""

from api.agent.prompts.intent_prompts import (
    INTENT_EXTRACTION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    get_intent_prompt,
    get_response_prompt,
)

__all__ = [
    "INTENT_EXTRACTION_PROMPT",
    "RESPONSE_GENERATION_PROMPT",
    "get_intent_prompt",
    "get_response_prompt",
]
