"""
Politicians API Routes
Endpoints para análise de políticos (perfil pessoal)
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import TokenData, get_current_user
from src.services import PoliticianIntelService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v2/politician", tags=["Politicians"])


# ===========================================
# SCHEMAS
# ===========================================

class PoliticianAnalyzeRequest(BaseModel):
    name: str
    role: Optional[str] = None  # prefeito, senador, deputado, etc
    state: Optional[str] = None
    focus: str = "personal"  # personal, career, public_perception


class QuickLookupRequest(BaseModel):
    name: str
    role: Optional[str] = None


class MonitorRequest(BaseModel):
    name: str
    role: Optional[str] = None
    alert_keywords: Optional[List[str]] = None


# ===========================================
# ENDPOINTS
# ===========================================

@router.post("/analyze")
async def analyze_politician(
    request: PoliticianAnalyzeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Análise de perfil pessoal de político

    NOTA: Foco em perfil PESSOAL, não político
    - Histórico pessoal e familiar
    - Formação e carreira
    - Presença em redes sociais
    - Percepção pública

    Não analisamos posições políticas ou votações.
    """
    logger.info(
        "api_politician_analyze",
        user=current_user.email,
        politician=request.name
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.analyze_politician(
                name=request.name,
                role=request.role,
                state=request.state,
                focus=request.focus
            )
            return result

    except Exception as e:
        logger.error("api_politician_analyze_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_lookup(
    request: QuickLookupRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Busca rápida de político (dados básicos)
    """
    logger.info(
        "api_politician_quick",
        user=current_user.email,
        politician=request.name
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.quick_lookup(
                name=request.name,
                role=request.role
            )
            return result

    except Exception as e:
        logger.error("api_politician_quick_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_politician(
    name: str = Query(..., description="Nome do político"),
    role: Optional[str] = Query(None, description="Cargo"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Busca político por nome
    """
    return await quick_lookup(
        QuickLookupRequest(name=name, role=role),
        current_user
    )


# ===========================================
# PROFILE SECTIONS
# ===========================================

@router.get("/{name}/perception")
async def get_public_perception(
    name: str,
    role: Optional[str] = Query(None, description="Cargo"),
    days: int = Query(30, le=90, description="Dias para análise"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Analisa percepção pública de um político
    """
    logger.info(
        "api_politician_perception",
        user=current_user.email,
        politician=name
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.get_public_perception(
                name=name,
                role=role,
                days=days
            )
            return result

    except Exception as e:
        logger.error("api_politician_perception_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/history")
async def get_personal_history(
    name: str,
    role: Optional[str] = Query(None, description="Cargo"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Busca histórico pessoal (não político)
    """
    logger.info(
        "api_politician_history",
        user=current_user.email,
        politician=name
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.get_personal_history(
                name=name,
                role=role
            )
            return result

    except Exception as e:
        logger.error("api_politician_history_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/media")
async def get_media_presence(
    name: str,
    role: Optional[str] = Query(None, description="Cargo"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Analisa presença na mídia
    """
    logger.info(
        "api_politician_media",
        user=current_user.email,
        politician=name
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.get_media_presence(
                name=name,
                role=role
            )
            return result

    except Exception as e:
        logger.error("api_politician_media_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# SEARCH & MONITOR
# ===========================================

@router.get("/list")
async def search_politicians(
    role: Optional[str] = Query(None, description="Cargo"),
    state: Optional[str] = Query(None, description="Estado (UF)"),
    party: Optional[str] = Query(None, description="Partido"),
    limit: int = Query(10, le=30),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Busca políticos por critérios
    """
    logger.info(
        "api_politicians_search",
        user=current_user.email,
        role=role,
        state=state
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.search_politicians(
                role=role,
                state=state,
                party=party,
                limit=limit
            )
            return result

    except Exception as e:
        logger.error("api_politicians_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor")
async def monitor_politician(
    request: MonitorRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Monitora político para alertas de notícias

    Retorna alertas baseados em palavras-chave como:
    - polêmica, escândalo, denúncia
    - investigação, crítica, protesto
    """
    logger.info(
        "api_politician_monitor",
        user=current_user.email,
        politician=request.name
    )

    try:
        async with PoliticianIntelService() as service:
            result = await service.monitor_politician(
                name=request.name,
                role=request.role,
                alert_keywords=request.alert_keywords
            )
            return result

    except Exception as e:
        logger.error("api_politician_monitor_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
