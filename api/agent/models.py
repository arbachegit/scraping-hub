"""
Pydantic models for the AI Agent module.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    """Types of entities the agent can query."""

    EMPRESAS = "empresas"
    PESSOAS = "pessoas"
    NOTICIAS = "noticias"


class ActionType(str, Enum):
    """Types of actions the agent can perform."""

    LIST = "list"
    COUNT = "count"
    DETAIL = "detail"
    AGGREGATE = "aggregate"


class FilterOperator(str, Enum):
    """Supported filter operators for queries."""

    EQ = "eq"  # equals
    NEQ = "neq"  # not equals
    GT = "gt"  # greater than
    GTE = "gte"  # greater than or equal
    LT = "lt"  # less than
    LTE = "lte"  # less than or equal
    LIKE = "like"  # contains (case insensitive)
    ILIKE = "ilike"  # contains (case insensitive)
    IN = "in"  # in list
    IS_NULL = "is_null"  # is null
    NOT_NULL = "not_null"  # is not null


class QueryFilter(BaseModel):
    """A single filter condition for a query."""

    model_config = ConfigDict(use_enum_values=True)

    field: str = Field(..., description="The field to filter on")
    operator: FilterOperator = Field(..., description="The comparison operator")
    value: Any = Field(..., description="The value to compare against")


class ParsedIntent(BaseModel):
    """The parsed intent from a user's natural language query."""

    model_config = ConfigDict(use_enum_values=True)

    entity_type: EntityType = Field(..., description="The type of entity to query")
    action: ActionType = Field(default=ActionType.LIST, description="The action to perform")
    filters: List[QueryFilter] = Field(default_factory=list, description="Filter conditions")
    order_by: Optional[str] = Field(default=None, description="Field to order by")
    order_desc: bool = Field(default=False, description="Order descending")
    limit: int = Field(default=20, ge=1, le=100, description="Max results to return")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(default=None, description="Optional session ID")


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""

    session_id: str = Field(..., description="Session ID for conversation continuity")
    message: str = Field(..., description="AI-generated response message")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    total_count: int = Field(default=0, description="Total count of matching records")
    intent: Optional[ParsedIntent] = Field(default=None, description="Parsed intent")
    ai_provider_used: str = Field(default="unknown", description="AI provider that processed the request")


class SessionMessage(BaseModel):
    """A single message in a conversation session."""

    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationSession(BaseModel):
    """A conversation session with history."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[int] = Field(default=None)
    messages: List[SessionMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIProviderResponse(BaseModel):
    """Response from an AI provider."""

    success: bool = Field(..., description="Whether the request was successful")
    content: str = Field(default="", description="The response content")
    provider: str = Field(..., description="The provider name")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, description="Raw provider response")
