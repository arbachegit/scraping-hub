"""
News API Routes
Endpoints para monitoramento de notícias
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import TokenData, get_current_user
from src.services import NewsMonitorService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v2/news", tags=["News"])


# ===========================================
# SCHEMAS
# ===========================================


class NewsSearchRequest(BaseModel):
    query: str
    days: int = 7
    max_results: int = 20
    sentiment_filter: Optional[str] = None  # positive, negative, neutral


class MonitorEntityRequest(BaseModel):
    entity_name: str
    entity_type: str = "company"  # company, person, sector
    alert_keywords: Optional[List[str]] = None


class DailyBriefingRequest(BaseModel):
    topics: List[str]
    country: str = "Brasil"


# ===========================================
# ENDPOINTS
# ===========================================


@router.post("/search")
async def search_news(
    request: NewsSearchRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Busca notícias por query

    Retorna:
    - Notícias de múltiplas fontes
    - Análise de sentimento
    - Resumo consolidado
    """
    logger.info("api_news_search", user=current_user.email, query=request.query)

    try:
        async with NewsMonitorService() as service:
            result = await service.search_news(
                query=request.query,
                days=request.days,
                max_results=request.max_results,
                sentiment_filter=request.sentiment_filter,
            )
            return result

    except Exception as e:
        logger.error("api_news_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_news_get(
    q: str = Query(..., description="Termo de busca"),
    days: int = Query(7, le=30, description="Dias para buscar"),
    limit: int = Query(20, le=50, description="Limite de resultados"),
    sentiment: Optional[str] = Query(None, description="Filtro de sentimento"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca notícias (GET)
    """
    return await search_news(
        NewsSearchRequest(query=q, days=days, max_results=limit, sentiment_filter=sentiment),
        current_user,
    )


# ===========================================
# COMPANY NEWS
# ===========================================


@router.get("/company/{company_name}")
async def get_company_news(
    company_name: str,
    days: int = Query(30, le=90, description="Dias para buscar"),
    include_analysis: bool = Query(True, description="Incluir análise AI"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca notícias sobre uma empresa
    """
    logger.info("api_news_company", user=current_user.email, company=company_name)

    try:
        async with NewsMonitorService() as service:
            result = await service.get_company_news(
                company_name=company_name, days=days, include_analysis=include_analysis
            )
            return result

    except Exception as e:
        logger.error("api_news_company_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# SECTOR NEWS
# ===========================================


@router.get("/sector/{sector}")
async def get_sector_news(
    sector: str,
    days: int = Query(7, le=30, description="Dias para buscar"),
    country: str = Query("Brasil", description="País"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca notícias de um setor
    """
    logger.info("api_news_sector", user=current_user.email, sector=sector)

    try:
        async with NewsMonitorService() as service:
            result = await service.get_sector_news(sector=sector, days=days, country=country)
            return result

    except Exception as e:
        logger.error("api_news_sector_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# ECONOMIC SCENARIO
# ===========================================


@router.get("/economic")
async def get_economic_scenario(
    sector: Optional[str] = Query(None, description="Setor específico"),
    country: str = Query("Brasil", description="País"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca cenário econômico atual

    Retorna análise de:
    - Inflação
    - Taxa de juros
    - PIB
    - Câmbio
    - Emprego
    """
    logger.info("api_news_economic", user=current_user.email, sector=sector)

    try:
        async with NewsMonitorService() as service:
            result = (
                await service.get_economic_scenario(aspects=None, sector=sector)
                if sector
                else await service.get_economic_scenario()
            )
            return result

    except Exception as e:
        logger.error("api_news_economic_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# TRENDS
# ===========================================


@router.get("/trends")
async def get_trending_topics(
    category: Optional[str] = Query(None, description="Categoria"),
    country: str = Query("Brasil", description="País"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca tópicos em alta
    """
    logger.info("api_news_trends", user=current_user.email, category=category)

    try:
        async with NewsMonitorService() as service:
            result = await service.get_trending_topics(category=category, country=country)
            return result

    except Exception as e:
        logger.error("api_news_trends_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# MONITORING
# ===========================================


@router.post("/monitor")
async def monitor_entity(
    request: MonitorEntityRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Monitora entidade para alertas

    Tipos de entidade:
    - company: empresa
    - person: pessoa
    - sector: setor

    Retorna alertas baseados em keywords
    """
    logger.info("api_news_monitor", user=current_user.email, entity=request.entity_name)

    try:
        async with NewsMonitorService() as service:
            result = await service.monitor_entity(
                entity_name=request.entity_name,
                entity_type=request.entity_type,
                alert_keywords=request.alert_keywords,
            )
            return result

    except Exception as e:
        logger.error("api_news_monitor_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# BRIEFING
# ===========================================


@router.post("/briefing")
async def get_daily_briefing(
    request: DailyBriefingRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Gera briefing diário de notícias

    Envie uma lista de tópicos de interesse para receber
    um resumo consolidado das principais notícias do dia.
    """
    logger.info("api_news_briefing", user=current_user.email, topics=request.topics)

    if len(request.topics) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 tópicos por briefing")

    try:
        async with NewsMonitorService() as service:
            result = await service.get_daily_briefing(
                topics=request.topics, country=request.country
            )
            return result

    except Exception as e:
        logger.error("api_news_briefing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing")
async def get_default_briefing(current_user: TokenData = Depends(get_current_user)):
    """
    Gera briefing diário com tópicos padrão

    Tópicos:
    - Economia
    - Tecnologia
    - Negócios
    - Política econômica
    - Mercado financeiro
    """
    return await get_daily_briefing(
        DailyBriefingRequest(
            topics=[
                "economia",
                "tecnologia",
                "negócios",
                "política econômica",
                "mercado financeiro",
            ]
        ),
        current_user,
    )
