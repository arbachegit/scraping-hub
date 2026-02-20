"""
Tests for the AI Agent module.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.agent.models import (
    AIProviderResponse,
    ActionType,
    ChatRequest,
    EntityType,
    FilterOperator,
    ParsedIntent,
    QueryFilter,
)
from api.agent.prompts import get_intent_prompt, get_response_prompt
from api.agent.session_manager import SessionManager


class TestModels:
    """Tests for Pydantic models."""

    def test_chat_request_valid(self):
        """Test valid ChatRequest creation."""
        request = ChatRequest(message="Liste empresas de tecnologia")
        assert request.message == "Liste empresas de tecnologia"
        assert request.session_id is None

    def test_chat_request_with_session(self):
        """Test ChatRequest with session_id."""
        request = ChatRequest(
            message="Mostre detalhes",
            session_id="abc-123",
        )
        assert request.session_id == "abc-123"

    def test_chat_request_strips_whitespace(self):
        """Test that message whitespace is stripped."""
        request = ChatRequest(message="  teste  ")
        assert request.message == "teste"

    def test_parsed_intent_default_values(self):
        """Test ParsedIntent default values."""
        intent = ParsedIntent(entity_type=EntityType.EMPRESAS)
        assert intent.action == ActionType.LIST
        assert intent.filters == []
        assert intent.limit == 20
        assert intent.order_by is None
        assert intent.order_desc is False

    def test_parsed_intent_with_filters(self):
        """Test ParsedIntent with filters."""
        filters = [
            QueryFilter(field="estado", operator=FilterOperator.EQ, value="SP"),
            QueryFilter(field="cnae_principal", operator=FilterOperator.LIKE, value="62"),
        ]
        intent = ParsedIntent(
            entity_type=EntityType.EMPRESAS,
            action=ActionType.LIST,
            filters=filters,
            confidence=0.95,
        )
        assert len(intent.filters) == 2
        assert intent.confidence == 0.95

    def test_query_filter_operators(self):
        """Test all filter operators."""
        operators = [
            FilterOperator.EQ,
            FilterOperator.NEQ,
            FilterOperator.GT,
            FilterOperator.GTE,
            FilterOperator.LT,
            FilterOperator.LTE,
            FilterOperator.LIKE,
            FilterOperator.ILIKE,
            FilterOperator.IN,
            FilterOperator.IS_NULL,
            FilterOperator.NOT_NULL,
        ]
        for op in operators:
            f = QueryFilter(field="test", operator=op, value="test")
            assert f.operator == op

    def test_ai_provider_response_success(self):
        """Test successful AIProviderResponse."""
        response = AIProviderResponse(
            success=True,
            content='{"entity_type": "empresas"}',
            provider="perplexity",
        )
        assert response.success
        assert response.error is None

    def test_ai_provider_response_failure(self):
        """Test failed AIProviderResponse."""
        response = AIProviderResponse(
            success=False,
            content="",
            provider="perplexity",
            error="API timeout",
        )
        assert not response.success
        assert response.error == "API timeout"


class TestSessionManager:
    """Tests for SessionManager."""

    def test_create_session(self):
        """Test session creation."""
        manager = SessionManager()
        session = manager.get_or_create_session()

        assert session.session_id is not None
        assert len(session.messages) == 0

    def test_get_existing_session(self):
        """Test retrieving existing session."""
        manager = SessionManager()
        session1 = manager.get_or_create_session()
        session2 = manager.get_or_create_session(session_id=session1.session_id)

        assert session1.session_id == session2.session_id

    def test_add_message(self):
        """Test adding messages to session."""
        manager = SessionManager()
        session = manager.get_or_create_session()

        result = manager.add_message(session.session_id, "user", "Hello")
        assert result is True

        session = manager.get_session(session.session_id)
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"

    def test_add_message_nonexistent_session(self):
        """Test adding message to non-existent session."""
        manager = SessionManager()
        result = manager.add_message("nonexistent", "user", "Hello")
        assert result is False

    def test_conversation_context(self):
        """Test getting conversation context."""
        manager = SessionManager()
        session = manager.get_or_create_session()

        manager.add_message(session.session_id, "user", "Olá")
        manager.add_message(session.session_id, "assistant", "Como posso ajudar?")

        context = manager.get_conversation_context(session.session_id)
        assert "Usuário: Olá" in context
        assert "Assistente: Como posso ajudar?" in context

    def test_delete_session(self):
        """Test session deletion."""
        manager = SessionManager()
        session = manager.get_or_create_session()

        result = manager.delete_session(session.session_id)
        assert result is True

        assert manager.get_session(session.session_id) is None

    def test_message_limit(self):
        """Test that messages are limited to 20."""
        manager = SessionManager()
        session = manager.get_or_create_session()

        # Add 25 messages
        for i in range(25):
            manager.add_message(session.session_id, "user", f"Message {i}")

        session = manager.get_session(session.session_id)
        assert len(session.messages) == 20

    def test_active_sessions_count(self):
        """Test active sessions counter."""
        manager = SessionManager()

        assert manager.active_sessions_count == 0

        manager.get_or_create_session()
        manager.get_or_create_session()

        assert manager.active_sessions_count == 2


class TestPrompts:
    """Tests for prompt generation."""

    def test_intent_prompt_basic(self):
        """Test basic intent prompt generation."""
        prompt = get_intent_prompt("Liste empresas de SP")

        assert "Liste empresas de SP" in prompt
        assert "entity_type" in prompt
        assert "empresas" in prompt
        assert "pessoas" in prompt
        assert "noticias" in prompt

    def test_intent_prompt_with_context(self):
        """Test intent prompt with conversation context."""
        context = "Usuário: Olá\nAssistente: Como posso ajudar?"
        prompt = get_intent_prompt("Mostre empresas", context)

        assert "Olá" in prompt
        assert "Mostre empresas" in prompt

    def test_response_prompt(self):
        """Test response prompt generation."""
        prompt = get_response_prompt(
            entity_type="empresas",
            action="list",
            filters=[{"field": "estado", "operator": "eq", "value": "SP"}],
            total_count=45,
            data_sample='[{"nome": "Empresa X"}]',
        )

        assert "empresas" in prompt
        assert "list" in prompt
        assert "45" in prompt


class TestEntityTypes:
    """Tests for entity type enums."""

    def test_entity_types(self):
        """Test all entity types exist."""
        assert EntityType.EMPRESAS.value == "empresas"
        assert EntityType.PESSOAS.value == "pessoas"
        assert EntityType.NOTICIAS.value == "noticias"

    def test_action_types(self):
        """Test all action types exist."""
        assert ActionType.LIST.value == "list"
        assert ActionType.COUNT.value == "count"
        assert ActionType.DETAIL.value == "detail"
        assert ActionType.AGGREGATE.value == "aggregate"


class TestIntentParser:
    """Tests for intent parsing."""

    @pytest.mark.asyncio
    async def test_parse_intent_empresas_sp(self):
        """Test parsing intent for empresas in SP."""
        from api.agent.intent_parser import IntentParser
        from api.agent.models import AIProviderResponse

        mock_response = AIProviderResponse(
            success=True,
            content=json.dumps({
                "entity_type": "empresas",
                "action": "list",
                "filters": [
                    {"field": "estado", "operator": "eq", "value": "SP"}
                ],
                "confidence": 0.95
            }),
            provider="test",
        )

        with patch.object(IntentParser, '__init__', lambda x: None):
            parser = IntentParser()
            parser._chain = MagicMock()
            parser._chain.complete = AsyncMock(return_value=mock_response)

            intent, provider = await parser.parse("Liste empresas de SP")

            assert intent.entity_type == EntityType.EMPRESAS
            assert len(intent.filters) == 1
            assert intent.filters[0].field == "estado"
            assert intent.filters[0].value == "SP"

    @pytest.mark.asyncio
    async def test_parse_intent_fallback(self):
        """Test fallback when AI fails."""
        from api.agent.intent_parser import IntentParser
        from api.agent.models import AIProviderResponse

        mock_response = AIProviderResponse(
            success=False,
            content="",
            provider="test",
            error="API error",
        )

        with patch.object(IntentParser, '__init__', lambda x: None):
            parser = IntentParser()
            parser._chain = MagicMock()
            parser._chain.complete = AsyncMock(return_value=mock_response)

            intent, provider = await parser.parse("Liste empresas")

            # Should return default intent
            assert intent.entity_type == EntityType.EMPRESAS
            assert intent.action == ActionType.LIST
            assert intent.confidence == 0.3  # Low confidence for fallback
