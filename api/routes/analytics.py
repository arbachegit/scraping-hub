"""
Analytics API Routes
Endpoints para metricas e analytics do data warehouse
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import TokenData, get_current_user
from src.database.dimensional_repository import AnalyticsQueryRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v2/analytics", tags=["Analytics"])


# ===========================================
# SCHEMAS
# ===========================================

class DailyMetrics(BaseModel):
    period_days: int
    start_date: str
    end_date: str
    total_searches: int
    total_api_calls: int
    total_company_analyses: int
    total_person_analyses: int


class SearchByDate(BaseModel):
    full_date: str
    day_name: str
    search_type: str
    total_searches: int
    total_results: int
    avg_processing_time_ms: Optional[float]
    total_credits_used: int
    successful_searches: int
    failed_searches: int


class SourceQuality(BaseModel):
    source_name: str
    source_type: str
    total_calls: int
    success_rate: float
    avg_response_time_ms: float
    total_cost: float
    cache_hit_rate: float


class CompanyAnalysisSummary(BaseModel):
    full_date: str
    analysis_type: str
    total_analyses: int
    avg_completeness: Optional[float]
    avg_confidence: Optional[float]
    avg_processing_time_ms: Optional[float]
    total_tokens_used: int
    with_swot: int
    with_okrs: int


class UserUsage(BaseModel):
    user_email: str
    plan_type: str
    total_searches: int
    total_credits_used: int
    company_analyses: int
    person_analyses: int


class SearchTypeDistribution(BaseModel):
    search_type: str
    count: int


class HourlyActivity(BaseModel):
    hour: int
    count: int


class DashboardResponse(BaseModel):
    metrics: DailyMetrics
    search_distribution: List[SearchTypeDistribution]
    hourly_activity: List[HourlyActivity]
    source_quality: List[SourceQuality]


# ===========================================
# ENDPOINTS
# ===========================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Dashboard de analytics consolidado

    Retorna:
    - Metricas gerais do periodo
    - Distribuicao de tipos de pesquisa
    - Atividade por hora do dia
    - Qualidade das fontes de dados
    """
    logger.info("api_analytics_dashboard", user=current_user.email, days=days)

    try:
        repo = AnalyticsQueryRepository()

        # Get all dashboard data in parallel
        metrics = await repo.get_daily_metrics(days=days)
        search_distribution = await repo.get_search_type_distribution(days=days)
        hourly_activity = await repo.get_hourly_activity(days=min(days, 7))
        source_quality = await repo.get_source_quality()

        return {
            "metrics": metrics if metrics else {
                "period_days": days,
                "start_date": (datetime.utcnow().date() - timedelta(days=days)).isoformat(),
                "end_date": datetime.utcnow().date().isoformat(),
                "total_searches": 0,
                "total_api_calls": 0,
                "total_company_analyses": 0,
                "total_person_analyses": 0
            },
            "search_distribution": search_distribution,
            "hourly_activity": hourly_activity,
            "source_quality": source_quality
        }

    except Exception as e:
        logger.error("api_analytics_dashboard_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=DailyMetrics)
async def get_metrics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Metricas gerais do sistema

    Retorna contagens agregadas de pesquisas, analises e chamadas de API.
    """
    logger.info("api_analytics_metrics", user=current_user.email, days=days)

    try:
        repo = AnalyticsQueryRepository()
        metrics = await repo.get_daily_metrics(days=days)

        if not metrics:
            return {
                "period_days": days,
                "start_date": (datetime.utcnow().date() - timedelta(days=days)).isoformat(),
                "end_date": datetime.utcnow().date().isoformat(),
                "total_searches": 0,
                "total_api_calls": 0,
                "total_company_analyses": 0,
                "total_person_analyses": 0
            }

        return metrics

    except Exception as e:
        logger.error("api_analytics_metrics_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches", response_model=List[SearchByDate])
async def get_searches_by_date(
    start_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    search_type: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Pesquisas agregadas por dia

    Retorna estatisticas diarias de pesquisas com filtros opcionais.
    """
    logger.info(
        "api_analytics_searches",
        user=current_user.email,
        start_date=start_date,
        end_date=end_date
    )

    try:
        repo = AnalyticsQueryRepository()
        data = await repo.get_searches_by_date(
            start_date=start_date,
            end_date=end_date,
            search_type=search_type,
            limit=limit
        )
        return data

    except Exception as e:
        logger.error("api_analytics_searches_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[SourceQuality])
async def get_source_quality(
    limit: int = Query(default=20, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Qualidade das fontes de dados

    Retorna metricas de performance e confiabilidade por fonte de dados.
    """
    logger.info("api_analytics_sources", user=current_user.email)

    try:
        repo = AnalyticsQueryRepository()
        data = await repo.get_source_quality(limit=limit)
        return data

    except Exception as e:
        logger.error("api_analytics_sources_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies", response_model=List[CompanyAnalysisSummary])
async def get_company_analysis_summary(
    start_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Resumo de analises de empresas

    Retorna estatisticas diarias de analises de empresas.
    """
    logger.info(
        "api_analytics_companies",
        user=current_user.email,
        start_date=start_date,
        end_date=end_date
    )

    try:
        repo = AnalyticsQueryRepository()
        data = await repo.get_company_analysis_summary(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return data

    except Exception as e:
        logger.error("api_analytics_companies_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=List[UserUsage])
async def get_user_usage(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Uso por usuario

    Retorna estatisticas de uso agregadas por usuario.
    Requer role admin.
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem ver dados de todos os usuarios"
        )

    logger.info("api_analytics_users", user=current_user.email)

    try:
        repo = AnalyticsQueryRepository()
        data = await repo.get_user_usage(limit=limit)
        return data

    except Exception as e:
        logger.error("api_analytics_users_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-types", response_model=List[SearchTypeDistribution])
async def get_search_type_distribution(
    days: int = Query(default=30, ge=1, le=365),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Distribuicao de tipos de pesquisa

    Retorna a contagem de pesquisas por tipo.
    """
    logger.info("api_analytics_search_types", user=current_user.email, days=days)

    try:
        repo = AnalyticsQueryRepository()
        data = await repo.get_search_type_distribution(days=days)
        return data

    except Exception as e:
        logger.error("api_analytics_search_types_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/hourly", response_model=List[HourlyActivity])
async def get_hourly_activity(
    days: int = Query(default=7, ge=1, le=30),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Atividade por hora do dia

    Retorna a distribuicao de atividade por hora.
    """
    logger.info("api_analytics_hourly", user=current_user.email, days=days)

    try:
        repo = AnalyticsQueryRepository()
        data = await repo.get_hourly_activity(days=days)
        return data

    except Exception as e:
        logger.error("api_analytics_hourly_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
