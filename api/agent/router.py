"""
Agent Router - Endpoints for the conversational AI agent.
"""

from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import create_client

from api.agent.intent_parser import get_intent_parser
from api.agent.models import ChatRequest, ChatResponse, ParsedIntent
from api.agent.query_builder import create_query_builder
from api.agent.session_manager import session_manager
from api.auth import TokenData, get_current_user
from config.settings import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Process a natural language query and return structured results.

    The agent parses the user's message, extracts intent, builds a query,
    and returns matching data with a conversational response.

    Fallback chain: Perplexity -> Claude -> OpenAI
    """
    # Validate Supabase configuration
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not configured",
        )

    # Get or create session
    session = session_manager.get_or_create_session(
        session_id=request.session_id,
        user_id=current_user.user_id,
    )

    # Add user message to session
    session_manager.add_message(session.session_id, "user", request.message)

    # Get conversation context
    context = session_manager.get_conversation_context(
        session.session_id,
        max_messages=6,  # Last 6 messages for context
    )

    try:
        # Parse intent
        intent_parser = get_intent_parser()
        intent, provider_used = await intent_parser.parse(
            user_message=request.message,
            conversation_context=context,
        )

        logger.info(
            "intent_parsed",
            entity_type=intent.entity_type,
            action=intent.action,
            filters_count=len(intent.filters),
            confidence=intent.confidence,
            provider=provider_used,
        )

        # Create Supabase clients
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)

        # Create fiscal client if configured (for politicos)
        fiscal_client = None
        if settings.has_fiscal_supabase:
            fiscal_client = create_client(
                settings.fiscal_supabase_url,
                settings.fiscal_supabase_key,
            )

        # Execute query
        query_builder = create_query_builder(supabase, fiscal_client)
        data, total_count = await query_builder.execute(intent)

        # Generate response message
        response_message = _generate_response_message(intent, data, total_count)

        # Add assistant response to session
        session_manager.add_message(session.session_id, "assistant", response_message)

        return ChatResponse(
            session_id=session.session_id,
            message=response_message,
            data=data,
            total_count=total_count,
            intent=intent,
            ai_provider_used=provider_used,
        )

    except Exception as e:
        logger.error("chat_error", error=str(e), user=current_user.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar mensagem: {str(e)}",
        )


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get session information and conversation history.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada",
        )

    # Verify user owns the session
    if session.user_id and session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "message_count": len(session.messages),
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in session.messages
        ],
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Delete a conversation session.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada",
        )

    # Verify user owns the session
    if session.user_id and session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )

    session_manager.delete_session(session_id)
    return {"success": True, "message": "Sessão excluída"}


@router.get("/health")
async def agent_health():
    """
    Check the health of the agent subsystem.
    """
    from api.agent.ai_providers.chain import get_provider_chain

    chain = get_provider_chain()

    return {
        "status": "healthy" if chain.has_providers else "degraded",
        "providers_available": chain.available_providers,
        "active_sessions": session_manager.active_sessions_count,
    }


def _generate_response_message(
    intent: ParsedIntent,
    data: List[Dict[str, Any]],
    total_count: int,
) -> str:
    """
    Generate a conversational response message.

    Args:
        intent: The parsed intent
        data: Query results
        total_count: Total count of matching records

    Returns:
        A friendly response message in Portuguese
    """
    entity_names = {
        "empresas": ("empresa", "empresas"),
        "pessoas": ("pessoa", "pessoas"),
        "noticias": ("notícia", "notícias"),
        "politicos": ("político", "políticos"),
    }

    singular, plural = entity_names.get(intent.entity_type, ("item", "itens"))

    if total_count == 0:
        filters_desc = _describe_filters(intent)
        if filters_desc:
            return f"Não encontrei nenhum(a) {singular} {filters_desc}. Tente ajustar os filtros."
        return f"Não encontrei nenhum(a) {singular} com esses critérios."

    if total_count == 1:
        return f"Encontrei 1 {singular}."

    if len(data) < total_count:
        return f"Encontrei {total_count} {plural}. Mostrando os primeiros {len(data)}."

    return f"Encontrei {total_count} {plural}."


def _describe_filters(intent: ParsedIntent) -> str:
    """
    Generate a human-readable description of the applied filters.

    Args:
        intent: The parsed intent with filters

    Returns:
        A string describing the filters
    """
    if not intent.filters:
        return ""

    descriptions = []
    for f in intent.filters[:3]:  # Limit to 3 filters for brevity
        field = f.field
        value = f.value

        if field in ("estado", "uf", "cidade", "municipio_nome"):
            descriptions.append(f"em {value}")
        elif field == "porte":
            descriptions.append(f"de porte {value}")
        elif field == "regime_tributario":
            regime_names = {
                "SIMPLES_NACIONAL": "Simples Nacional",
                "LUCRO_PRESUMIDO": "Lucro Presumido",
                "LUCRO_REAL": "Lucro Real",
            }
            descriptions.append(f"com regime {regime_names.get(value, value)}")
        elif field == "cnae_principal":
            descriptions.append(f"do segmento {value}")
        elif field == "partido_sigla":
            descriptions.append(f"do partido {value}")
        elif field == "cargo_atual":
            descriptions.append(f"com cargo de {value}")
        else:
            descriptions.append(f"com {field}={value}")

    if descriptions:
        return " ".join(descriptions)

    return ""
