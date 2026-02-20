"""
Intent Parser - Extracts structured intent from natural language queries.
"""

import json
import re
from typing import Optional

import structlog

from api.agent.ai_providers.chain import get_provider_chain
from api.agent.models import (
    ActionType,
    EntityType,
    FilterOperator,
    ParsedIntent,
    QueryFilter,
)
from api.agent.prompts import get_intent_prompt

logger = structlog.get_logger()


class IntentParser:
    """Parses natural language queries into structured intents."""

    def __init__(self):
        """Initialize the intent parser."""
        self._chain = get_provider_chain()

    async def parse(
        self,
        user_message: str,
        conversation_context: str = "",
    ) -> tuple[ParsedIntent, str]:
        """
        Parse a user message into a structured intent.

        Args:
            user_message: The user's natural language query
            conversation_context: Optional conversation history

        Returns:
            Tuple of (ParsedIntent, provider_used)
        """
        prompt = get_intent_prompt(user_message, conversation_context)

        response = await self._chain.complete(
            prompt=prompt,
            temperature=0.0,
            max_tokens=1000,
        )

        if not response.success:
            logger.error("intent_parse_failed", error=response.error)
            # Return default intent for listing empresas
            return self._default_intent(user_message), response.provider

        intent = self._extract_intent(response.content)
        return intent, response.provider

    def _extract_intent(self, content: str) -> ParsedIntent:
        """
        Extract intent from AI response content.

        Args:
            content: The AI response content (should be JSON)

        Returns:
            ParsedIntent object
        """
        try:
            # Try to extract JSON from the content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                logger.warning("intent_no_json_found", content_preview=content[:200])
                return self._default_intent("")

            json_str = json_match.group()
            data = json.loads(json_str)

            # Parse entity type
            entity_type_str = data.get("entity_type", "empresas").lower()
            try:
                entity_type = EntityType(entity_type_str)
            except ValueError:
                entity_type = EntityType.EMPRESAS

            # Parse action
            action_str = data.get("action", "list").lower()
            try:
                action = ActionType(action_str)
            except ValueError:
                action = ActionType.LIST

            # Parse filters
            filters = []
            for f in data.get("filters", []):
                try:
                    operator_str = f.get("operator", "eq").lower()
                    try:
                        operator = FilterOperator(operator_str)
                    except ValueError:
                        operator = FilterOperator.EQ

                    filters.append(QueryFilter(
                        field=f.get("field", ""),
                        operator=operator,
                        value=f.get("value"),
                    ))
                except Exception as e:
                    logger.warning("filter_parse_error", error=str(e), filter=f)
                    continue

            # Parse other fields
            order_by = data.get("order_by")
            order_desc = data.get("order_desc", False)
            limit = min(max(data.get("limit", 20), 1), 100)
            confidence = min(max(data.get("confidence", 0.5), 0.0), 1.0)

            return ParsedIntent(
                entity_type=entity_type,
                action=action,
                filters=filters,
                order_by=order_by,
                order_desc=order_desc,
                limit=limit,
                confidence=confidence,
            )

        except json.JSONDecodeError as e:
            logger.error("intent_json_decode_error", error=str(e))
            return self._default_intent("")
        except Exception as e:
            logger.error("intent_parse_error", error=str(e))
            return self._default_intent("")

    def _default_intent(self, user_message: str) -> ParsedIntent:
        """
        Create a default intent when parsing fails.

        Args:
            user_message: The original user message

        Returns:
            Default ParsedIntent for listing empresas
        """
        # Try to infer entity type from keywords
        message_lower = user_message.lower()

        if any(word in message_lower for word in ["pessoa", "pessoas", "sócio", "socios", "fundador", "fundadores"]):
            entity_type = EntityType.PESSOAS
        elif any(word in message_lower for word in ["notícia", "noticias", "news", "artigo", "artigos"]):
            entity_type = EntityType.NOTICIAS
        else:
            entity_type = EntityType.EMPRESAS

        return ParsedIntent(
            entity_type=entity_type,
            action=ActionType.LIST,
            filters=[],
            limit=20,
            confidence=0.3,
        )


# Global parser instance
_intent_parser: Optional[IntentParser] = None


def get_intent_parser() -> IntentParser:
    """
    Get the global intent parser instance.

    Returns:
        IntentParser instance
    """
    global _intent_parser
    if _intent_parser is None:
        _intent_parser = IntentParser()
    return _intent_parser
