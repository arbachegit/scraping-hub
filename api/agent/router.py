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

        # Create brasil-data-hub client if configured (for politicos)
        brasil_data_hub_client = None
        if settings.has_brasil_data_hub:
            brasil_data_hub_client = create_client(
                settings.brasil_data_hub_url,
                settings.brasil_data_hub_key,
            )

        # Execute query
        query_builder = create_query_builder(supabase, brasil_data_hub_client)

        # For politicos, use enriched search with mandatos
        if intent.entity_type == "politicos":
            data, total_count = await query_builder.search_politicos_with_mandatos(intent)
        else:
            data, total_count = await query_builder.execute(intent)

        # If no data found and we have Perplexity, search externally
        external_info = None
        if total_count == 0 and settings.has_perplexity:
            external_info = await _search_external_with_perplexity(
                request.message,
                intent.entity_type,
            )

        # Generate response message
        response_message = _generate_response_message(
            intent, data, total_count, external_info
        )

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


@router.get("/politico/{politico_id}/mandatos")
async def get_politico_mandatos(
    politico_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get the mandatos history for a specific politician.
    """
    if not settings.has_brasil_data_hub:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Brasil Data Hub não configurado",
        )

    try:
        brasil_data_hub_client = create_client(
            settings.brasil_data_hub_url,
            settings.brasil_data_hub_key,
        )

        query_builder = create_query_builder(None, brasil_data_hub_client)
        mandatos = await query_builder.fetch_mandatos(politico_id)

        return {
            "politico_id": politico_id,
            "mandatos": mandatos,
            "total": len(mandatos),
        }

    except Exception as e:
        logger.error("mandatos_error", error=str(e), politico_id=politico_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar mandatos: {str(e)}",
        )


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


async def _search_external_with_perplexity(
    user_message: str,
    entity_type: str,
) -> str:
    """
    Search externally using Perplexity AI when data is not found in the database.

    Args:
        user_message: The original user message
        entity_type: The type of entity being searched

    Returns:
        External information from Perplexity or None
    """
    try:
        from api.agent.ai_providers.chain import get_provider_chain

        chain = get_provider_chain()

        # Build a search prompt
        search_prompt = f"""Busque informações sobre: {user_message}

Contexto: O usuário está buscando informações sobre {entity_type} no Brasil.
Forneça uma resposta concisa e informativa em português brasileiro.
Se não encontrar informações específicas, indique isso claramente."""

        response = await chain.complete(search_prompt)

        if response.success and response.content:
            return response.content

        return None

    except Exception as e:
        logger.warning("perplexity_search_error", error=str(e))
        return None


def _generate_response_message(
    intent: ParsedIntent,
    data: List[Dict[str, Any]],
    total_count: int,
    external_info: str = None,
) -> str:
    """
    Generate a conversational response message.

    Args:
        intent: The parsed intent
        data: Query results
        total_count: Total count of matching records
        external_info: External information from Perplexity (if any)

    Returns:
        A friendly response message in Portuguese
    """
    entity_names = {
        "empresas": ("empresa", "empresas"),
        "pessoas": ("pessoa", "pessoas"),
        "noticias": ("notícia", "notícias"),
        "politicos": ("político", "políticos"),  # dim_politicos + fato_politicos_mandatos
    }

    singular, plural = entity_names.get(intent.entity_type, ("item", "itens"))

    if total_count == 0:
        filters_desc = _describe_filters(intent)
        base_msg = ""
        if filters_desc:
            base_msg = f"Não encontrei nenhum(a) {singular} {filters_desc} na base de dados."
        else:
            base_msg = f"Não encontrei nenhum(a) {singular} com esses critérios na base de dados."

        # Append external info if available
        if external_info:
            return f"{base_msg}\n\nPorém, encontrei informações externas:\n{external_info}"

        return f"{base_msg} Tente ajustar os filtros."

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
        elif field == "sexo":
            sexo_nome = "masculino" if value == "M" else "feminino"
            descriptions.append(f"do sexo {sexo_nome}")
        elif field == "grau_instrucao":
            descriptions.append(f"com {value}")
        elif field == "ocupacao":
            descriptions.append(f"com ocupação {value}")
        else:
            descriptions.append(f"com {field}={value}")

    if descriptions:
        return " ".join(descriptions)

    return ""
