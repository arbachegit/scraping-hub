"""
Companies API Routes
Endpoints para análise de empresas
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import TokenData, get_current_user
from src.services import (
    CNPJSearchService,
    CompanyAnalysisService,
    CompanyIntelService,
    CompetitorAnalysisService,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v2/company", tags=["Companies"])


# ===========================================
# SCHEMAS
# ===========================================


class CompanyAnalyzeRequest(BaseModel):
    name: str
    cnpj: Optional[str] = None
    analysis_type: str = "client"  # client, competitor, prospect
    include_competitors: bool = True
    include_employees: bool = True


class CompanyQuickRequest(BaseModel):
    name: str


class CompetitorCompareRequest(BaseModel):
    company1: str
    company2: str
    aspects: Optional[List[str]] = None


class OKRRequest(BaseModel):
    name: str
    focus_areas: Optional[List[str]] = None


class CompanyAnalyzeCompleteRequest(BaseModel):
    name: str
    cnpj: Optional[str] = None


class CNPJSearchRequest(BaseModel):
    company_name: str
    max_results: int = 5


# ===========================================
# ENDPOINTS - CNPJ SEARCH
# ===========================================


@router.post("/cnpj/search")
async def search_cnpj_by_name(
    request: CNPJSearchRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Busca CNPJ por nome da empresa.

    Fluxo:
    1. Busca no Google por CNPJs relacionados ao nome
    2. Valida cada CNPJ na Receita Federal (BrasilAPI)
    3. Retorna lista de empresas ordenadas por relevância

    Use para descobrir o CNPJ quando só tem o nome da empresa.
    """
    logger.info("api_cnpj_search", user=current_user.email, company_name=request.company_name)

    try:
        async with CNPJSearchService() as service:
            result = await service.search_by_name(
                company_name=request.company_name, max_results=request.max_results
            )
            return result

    except Exception as e:
        logger.error("api_cnpj_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cnpj/{cnpj}")
async def get_company_by_cnpj(cnpj: str, current_user: TokenData = Depends(get_current_user)):
    """
    Busca dados de empresa diretamente pelo CNPJ.

    Valida na Receita Federal e retorna dados completos.
    """
    logger.info(
        "api_cnpj_get",
        user=current_user.email,
        cnpj=cnpj[:8] + "...",  # Log parcial por segurança
    )

    try:
        async with CNPJSearchService() as service:
            result = await service.get_company_by_cnpj(cnpj)

            if result.get("error"):
                raise HTTPException(status_code=404, detail=result["message"])

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_cnpj_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# ENDPOINTS - COMPANY ANALYSIS
# ===========================================


@router.post("/analyze-complete")
async def analyze_company_complete(
    request: CompanyAnalyzeCompleteRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Análise COMPLETA de empresa com 11 blocos temáticos

    Retorna:
    - 11 blocos de análise (empresa, pessoas, formação, etc.)
    - Hipótese de objetivo vs OKR sugerido
    - Concorrentes com stamps (Forte/Médio/Fraco)
    - SWOT contemporâneo com scoring e TOWS
    """
    logger.info("api_company_analyze_complete", user=current_user.email, company=request.name)

    try:
        async with CompanyAnalysisService() as service:
            result = await service.analyze_complete(name=request.name, cnpj=request.cnpj)
            return result

    except Exception as e:
        logger.error("api_company_analyze_complete_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_company(
    request: CompanyAnalyzeRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Análise completa de empresa

    Retorna:
    - Dados cadastrais (CNPJ)
    - Análise SWOT
    - OKRs sugeridos
    - Concorrentes
    - Funcionários principais
    """
    logger.info("api_company_analyze", user=current_user.email, company=request.name)

    try:
        async with CompanyIntelService() as service:
            result = await service.analyze_company(
                name=request.name,
                cnpj=request.cnpj,
                analysis_type=request.analysis_type,
                include_competitors=request.include_competitors,
                include_employees=request.include_employees,
            )
            return result

    except Exception as e:
        logger.error("api_company_analyze_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_lookup(
    request: CompanyQuickRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Busca rápida de empresa (dados básicos)
    """
    logger.info("api_company_quick", user=current_user.email, company=request.name)

    try:
        async with CompanyIntelService() as service:
            result = await service.quick_lookup(request.name)
            return result

    except Exception as e:
        logger.error("api_company_quick_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_company(
    name: str = Query(..., description="Nome da empresa"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Busca empresa por nome
    """
    return await quick_lookup(CompanyQuickRequest(name=name), current_user)


@router.post("/swot")
async def get_swot(
    request: CompanyQuickRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Gera análise SWOT para empresa
    """
    logger.info("api_company_swot", user=current_user.email, company=request.name)

    try:
        async with CompanyIntelService() as service:
            result = await service.get_swot(request.name)
            return result

    except Exception as e:
        logger.error("api_company_swot_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/okrs")
async def get_okrs(request: OKRRequest, current_user: TokenData = Depends(get_current_user)):
    """
    Gera OKRs sugeridos para empresa
    """
    logger.info("api_company_okrs", user=current_user.email, company=request.name)

    try:
        async with CompanyIntelService() as service:
            result = await service.get_okrs(request.name, focus_areas=request.focus_areas)
            return result

    except Exception as e:
        logger.error("api_company_okrs_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# CONCORRENTES
# ===========================================


@router.get("/competitors")
async def find_competitors(
    name: str = Query(..., description="Nome da empresa"),
    industry: Optional[str] = Query(None, description="Setor"),
    max_competitors: int = Query(5, le=10, description="Máximo de concorrentes"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Identifica concorrentes de uma empresa
    """
    logger.info("api_company_competitors", user=current_user.email, company=name)

    try:
        async with CompetitorAnalysisService() as service:
            result = await service.identify_competitors(
                company_name=name, industry=industry, max_competitors=max_competitors
            )
            return result

    except Exception as e:
        logger.error("api_company_competitors_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitors/compare")
async def compare_companies(
    request: CompetitorCompareRequest, current_user: TokenData = Depends(get_current_user)
):
    """
    Compara duas empresas
    """
    logger.info(
        "api_company_compare",
        user=current_user.email,
        companies=[request.company1, request.company2],
    )

    try:
        async with CompetitorAnalysisService() as service:
            result = await service.compare_companies(
                company1=request.company1, company2=request.company2, aspects=request.aspects
            )
            return result

    except Exception as e:
        logger.error("api_company_compare_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/{industry}")
async def analyze_market(
    industry: str,
    location: str = Query("Brasil", description="Localização"),
    depth: str = Query("standard", description="Profundidade: quick, standard, deep"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Analisa cenário competitivo de um setor
    """
    logger.info("api_market_analysis", user=current_user.email, industry=industry)

    try:
        async with CompetitorAnalysisService() as service:
            result = await service.analyze_competitive_landscape(
                industry=industry, location=location, depth=depth
            )
            return result

    except Exception as e:
        logger.error("api_market_analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# FUNCIONÁRIOS
# ===========================================


@router.get("/{company_name}/employees")
async def get_employees(
    company_name: str,
    seniority: Optional[str] = Query(None, description="Filtro de senioridade"),
    limit: int = Query(50, le=100, description="Limite de resultados"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Lista funcionários de uma empresa
    """
    logger.info("api_company_employees", user=current_user.email, company=company_name)

    from src.services import PeopleIntelService

    try:
        async with PeopleIntelService() as service:
            filters = {}
            if seniority:
                filters["seniority"] = [seniority]

            result = await service.search_employees(
                company_name=company_name, filters=filters, limit=limit
            )
            return result

    except Exception as e:
        logger.error("api_company_employees_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_name}/decision-makers")
async def get_decision_makers(
    company_name: str, current_user: TokenData = Depends(get_current_user)
):
    """
    Lista tomadores de decisão de uma empresa
    """
    logger.info("api_company_dm", user=current_user.email, company=company_name)

    from src.services import PeopleIntelService

    try:
        async with PeopleIntelService() as service:
            result = await service.search_decision_makers(company_name)
            return result

    except Exception as e:
        logger.error("api_company_dm_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
