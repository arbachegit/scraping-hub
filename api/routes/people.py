"""
People API Routes
Endpoints para análise de pessoas
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import TokenData, get_current_user
from src.services import PeopleIntelService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v2/person", tags=["People"])


# ===========================================
# SCHEMAS
# ===========================================


class PersonAnalyzeRequest(BaseModel):
    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    linkedin_url: Optional[str] = None
    analysis_type: str = "full"  # full, quick, fit


class FitAnalysisRequest(BaseModel):
    person_name: str
    company_name: str
    role: Optional[str] = None


class CompareCandidatesRequest(BaseModel):
    candidates: List[str]
    company_name: str
    role: str


class QuickLookupRequest(BaseModel):
    name: str
    company: Optional[str] = None


# ===========================================
# ENDPOINTS
# ===========================================


@router.post("/analyze")
async def analyze_person(
    request: PersonAnalyzeRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Análise completa de pessoa

    Retorna:
    - Perfil profissional
    - Histórico de carreira
    - Habilidades identificadas
    - Análise AI
    """
    logger.info("api_person_analyze", user=current_user.email, person=request.name)

    try:
        async with PeopleIntelService() as service:
            result = await service.analyze_person(
                name=request.name,
                company=request.company,
                role=request.role,
                linkedin_url=request.linkedin_url,
                analysis_type=request.analysis_type,
            )
            return result

    except Exception as e:
        logger.error("api_person_analyze_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_lookup(
    request: QuickLookupRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Busca rápida de pessoa (dados básicos)
    """
    logger.info("api_person_quick", user=current_user.email, person=request.name)

    try:
        async with PeopleIntelService() as service:
            result = await service.quick_lookup(name=request.name, company=request.company)
            return result

    except Exception as e:
        logger.error("api_person_quick_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_person(
    name: str = Query(..., description="Nome da pessoa"),
    company: Optional[str] = Query(None, description="Empresa"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca pessoa por nome
    """
    return await quick_lookup(QuickLookupRequest(name=name, company=company), current_user)


# ===========================================
# FIT ANALYSIS
# ===========================================


@router.post("/fit-analysis")
async def analyze_fit(
    request: FitAnalysisRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Analisa fit cultural entre pessoa e empresa
    """
    logger.info(
        "api_person_fit",
        user=current_user.email,
        person=request.person_name,
        company=request.company_name,
    )

    try:
        async with PeopleIntelService() as service:
            result = await service.analyze_fit(
                person_name=request.person_name,
                company_name=request.company_name,
                role=request.role,
            )
            return result

    except Exception as e:
        logger.error("api_person_fit_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-candidates")
async def compare_candidates(
    request: CompareCandidatesRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Compara múltiplos candidatos para uma vaga
    """
    logger.info(
        "api_person_compare",
        user=current_user.email,
        candidates=request.candidates,
        company=request.company_name,
    )

    if len(request.candidates) < 2:
        raise HTTPException(status_code=400, detail="Mínimo de 2 candidatos para comparação")

    if len(request.candidates) > 5:
        raise HTTPException(status_code=400, detail="Máximo de 5 candidatos por comparação")

    try:
        async with PeopleIntelService() as service:
            result = await service.compare_candidates(
                candidates=request.candidates, company_name=request.company_name, role=request.role
            )
            return result

    except Exception as e:
        logger.error("api_person_compare_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# CAREER
# ===========================================


@router.get("/career/{name}")
async def get_career_history(
    name: str,
    linkedin_url: Optional[str] = Query(None, description="URL do LinkedIn"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca histórico de carreira
    """
    logger.info("api_person_career", user=current_user.email, person=name)

    try:
        async with PeopleIntelService() as service:
            result = await service.get_career_history(name=name, linkedin_url=linkedin_url)
            return result

    except Exception as e:
        logger.error("api_person_career_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# EMPLOYEES SEARCH
# ===========================================


@router.get("/employees")
async def search_employees(
    company: str = Query(..., description="Nome da empresa"),
    seniority: Optional[str] = Query(None, description="c_suite, director, manager, senior"),
    title: Optional[str] = Query(None, description="Cargo específico"),
    limit: int = Query(25, le=100),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca funcionários de uma empresa
    """
    logger.info("api_employees_search", user=current_user.email, company=company)

    try:
        filters = {}
        if seniority:
            filters["seniority"] = [seniority]
        if title:
            filters["titles"] = [title]

        async with PeopleIntelService() as service:
            result = await service.search_employees(
                company_name=company, filters=filters, limit=limit
            )
            return result

    except Exception as e:
        logger.error("api_employees_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decision-makers")
async def get_decision_makers(
    company: str = Query(..., description="Nome da empresa"),
    departments: Optional[str] = Query(None, description="Departamentos (separados por vírgula)"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca tomadores de decisão de uma empresa
    """
    logger.info("api_dm_search", user=current_user.email, company=company)

    try:
        dept_list = departments.split(",") if departments else None

        async with PeopleIntelService() as service:
            result = await service.search_decision_makers(
                company_name=company, departments=dept_list
            )
            return result

    except Exception as e:
        logger.error("api_dm_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
