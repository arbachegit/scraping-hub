"""
Politicians API Routes
Endpoints para análise de políticos (perfil pessoal)
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import TokenData, get_current_user
from src.database import get_supabase
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


class PoliticianImportRequest(BaseModel):
    """Schema para importar político de banco de dados externo"""
    name: str
    role: Optional[str] = None
    state: Optional[str] = None
    party: Optional[str] = None
    city: Optional[str] = None
    # Informações pessoais
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    education: Optional[str] = None
    profession: Optional[str] = None
    # Redes sociais
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    # Contato
    email: Optional[str] = None
    phone: Optional[str] = None
    # Dados adicionais (JSON livre)
    additional_data: Optional[Dict[str, Any]] = None


class PoliticianBulkImportRequest(BaseModel):
    """Schema para importar múltiplos políticos"""
    politicians: List[PoliticianImportRequest]


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


# ===========================================
# DATABASE OPERATIONS
# ===========================================

@router.post("/db/import")
async def import_politician(
    request: PoliticianImportRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Importa dados de político de banco de dados externo

    Use este endpoint para alimentar o sistema com dados de políticos
    que você já possui. Os dados serão usados para enriquecer análises.
    """
    logger.info(
        "api_politician_import",
        user=current_user.email,
        politician=request.name
    )

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        import json
        from datetime import datetime

        # Preparar registro
        record = {
            "full_name": request.name,
            "person_type": "politician",
            "political_role": request.role,
            "state": request.state,
            "city": request.city,
            "political_party": request.party,
            # Dados pessoais
            "birth_date": request.birth_date,
            "birth_place": request.birth_place,
            "education": request.education,
            "profession_before_politics": request.profession,
            # Redes sociais
            "instagram_url": request.instagram_url,
            "twitter_url": request.twitter_url,
            "facebook_url": request.facebook_url,
            "linkedin_url": request.linkedin_url,
            "website": request.website,
            # Contato
            "email": request.email,
            "phone": request.phone,
            # Raw data
            "raw_data": json.dumps({
                **request.model_dump(),
                "additional_data": request.additional_data or {}
            }, ensure_ascii=False, default=str),
            "imported_by": current_user.email,
            "imported_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Remover campos None
        record = {k: v for k, v in record.items() if v is not None}

        # Upsert no banco
        result = supabase.table("people").upsert(
            record,
            on_conflict="full_name,person_type"
        ).execute()

        if result.data:
            logger.info("politician_imported", name=request.name, id=result.data[0].get("id"))
            return {
                "status": "success",
                "message": f"Político '{request.name}' importado com sucesso",
                "id": result.data[0].get("id"),
                "data": result.data[0]
            }

        raise HTTPException(status_code=500, detail="Failed to import politician")

    except Exception as e:
        logger.error("api_politician_import_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/import-bulk")
async def import_politicians_bulk(
    request: PoliticianBulkImportRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Importa múltiplos políticos de uma vez

    Ideal para importar listas grandes de políticos.
    """
    logger.info(
        "api_politician_import_bulk",
        user=current_user.email,
        count=len(request.politicians)
    )

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        import json
        from datetime import datetime

        records = []
        for pol in request.politicians:
            record = {
                "full_name": pol.name,
                "person_type": "politician",
                "political_role": pol.role,
                "state": pol.state,
                "city": pol.city,
                "political_party": pol.party,
                "birth_date": pol.birth_date,
                "birth_place": pol.birth_place,
                "education": pol.education,
                "profession_before_politics": pol.profession,
                "instagram_url": pol.instagram_url,
                "twitter_url": pol.twitter_url,
                "facebook_url": pol.facebook_url,
                "linkedin_url": pol.linkedin_url,
                "website": pol.website,
                "email": pol.email,
                "phone": pol.phone,
                "raw_data": json.dumps({
                    **pol.model_dump(),
                    "additional_data": pol.additional_data or {}
                }, ensure_ascii=False, default=str),
                "imported_by": current_user.email,
                "imported_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            # Remover campos None
            record = {k: v for k, v in record.items() if v is not None}
            records.append(record)

        # Bulk upsert
        result = supabase.table("people").upsert(
            records,
            on_conflict="full_name,person_type"
        ).execute()

        imported_count = len(result.data) if result.data else 0
        logger.info("politicians_bulk_imported", count=imported_count)

        return {
            "status": "success",
            "message": f"{imported_count} políticos importados com sucesso",
            "imported_count": imported_count,
            "requested_count": len(request.politicians)
        }

    except Exception as e:
        logger.error("api_politician_bulk_import_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/list")
async def list_politicians_from_db(
    state: Optional[str] = Query(None, description="Filtrar por estado"),
    role: Optional[str] = Query(None, description="Filtrar por cargo"),
    party: Optional[str] = Query(None, description="Filtrar por partido"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Lista políticos do banco de dados

    Use para ver os políticos que foram importados.
    """
    logger.info(
        "api_politician_db_list",
        user=current_user.email
    )

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        query = supabase.table("people").select("*").eq("person_type", "politician")

        if state:
            query = query.eq("state", state)
        if role:
            query = query.ilike("political_role", f"%{role}%")
        if party:
            query = query.ilike("political_party", f"%{party}%")

        query = query.order("full_name").range(offset, offset + limit - 1)
        result = query.execute()

        return {
            "politicians": result.data or [],
            "count": len(result.data) if result.data else 0,
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error("api_politician_db_list_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/{politician_id}")
async def get_politician_from_db(
    politician_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Busca político específico do banco de dados pelo ID
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        result = supabase.table("people").select("*").eq("id", politician_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Politician not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_politician_db_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/{politician_id}/enrich")
async def enrich_politician_from_db(
    politician_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Enriquece político do banco com análise AI

    Pega os dados existentes do banco e executa a análise completa,
    combinando os dados que você importou com pesquisas em tempo real.
    """
    logger.info(
        "api_politician_enrich",
        user=current_user.email,
        id=politician_id
    )

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        # Buscar dados do banco
        db_result = supabase.table("people").select("*").eq("id", politician_id).execute()

        if not db_result.data:
            raise HTTPException(status_code=404, detail="Politician not found in database")

        db_data = db_result.data[0]

        # Executar análise completa
        async with PoliticianIntelService() as service:
            result = await service.analyze_politician(
                name=db_data.get("full_name"),
                role=db_data.get("political_role"),
                state=db_data.get("state"),
                focus="personal"
            )

        # Combinar dados do banco com análise
        result["db_data"] = db_data
        result["enrichment_source"] = "database + real-time analysis"

        # Atualizar banco com dados enriquecidos
        import json
        from datetime import datetime

        update_data = {
            "last_analysis": json.dumps(result.get("ai_analysis", {}), ensure_ascii=False, default=str),
            "last_enriched_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        supabase.table("people").update(update_data).eq("id", politician_id).execute()

        return {
            "status": "success",
            "politician": result,
            "message": f"Análise enriquecida para '{db_data.get('full_name')}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_politician_enrich_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/db/{politician_id}")
async def delete_politician_from_db(
    politician_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Remove político do banco de dados
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        result = supabase.table("people").delete().eq("id", politician_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Politician not found")

        return {
            "status": "success",
            "message": "Politician deleted",
            "id": politician_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_politician_delete_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
