"""
IconsAI Scraping API - v3.0 (Clean Architecture)
"""

import os
import re
from datetime import timedelta
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from supabase import create_client

from api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    UserLogin,
    UserResponse,
    UserUpdate,
    authenticate_user,
    create_access_token,
    get_current_user,
    update_user,
)
from backend.src.services.person_enrichment import PersonEnrichmentService
from config.settings import settings

logger = structlog.get_logger()


# ===========================================
# QUERY PARAM SCHEMAS (Pydantic Validation)
# ===========================================


class CnaeListParams(BaseModel):
    """Schema para listagem de CNAEs."""

    model_config = ConfigDict(str_strip_whitespace=True)

    search: str = Field(default="", max_length=100)
    limit: int = Field(default=100, ge=1, le=2000)
    offset: int = Field(default=0, ge=0)

    @field_validator("search")
    @classmethod
    def sanitize_search(cls, v: str) -> str:
        """Remove caracteres especiais que podem causar SQL injection via ilike."""
        if not v:
            return ""
        # Remove %, _, \ que são metacaracteres do LIKE/ILIKE
        return re.sub(r"[%_\\]", "", v.strip())[:100]


class EnrichPeopleParams(BaseModel):
    """Schema para enriquecimento de pessoas."""

    model_config = ConfigDict(str_strip_whitespace=True)

    limit: int = Field(default=10, ge=1, le=100)


def get_version() -> str:
    """Read version from VERSION file"""
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "1.0.2026"


APP_VERSION = get_version()

# FastAPI app
app = FastAPI(
    title="IconsAI Scraping API",
    description="API de inteligencia de dados",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_path = Path(__file__).resolve().parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info("static_files_mounted", path=str(static_path))


# ===========================================
# PAGES
# ===========================================


@app.get("/", include_in_schema=False)
async def index():
    """Serve login page"""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return {"error": "index.html not found"}


@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    """Serve dashboard page"""
    dashboard_file = static_path / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    return {"error": "dashboard.html not found"}


@app.get("/admin", include_in_schema=False)
async def admin_page():
    """Serve admin page"""
    admin_file = static_path / "admin.html"
    if admin_file.exists():
        return FileResponse(str(admin_file), media_type="text/html")
    return {"error": "admin.html not found"}


# ===========================================
# AUTH ENDPOINTS
# ===========================================


@app.post("/auth/login", response_model=Token, tags=["Auth"])
async def login(user_data: UserLogin):
    """User login"""
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    access_token = create_access_token(
        data={
            "sub": user["email"],
            "user_id": user.get("id"),
            "role": user.get("role", "user"),
            "permissions": user.get("permissions", []),
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_me(current_user=Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.user_id or 0,
        "email": current_user.email,
        "name": None,
        "role": current_user.role or "user",
    }


@app.put("/auth/me", tags=["Auth"])
async def update_me(update_data: UserUpdate, current_user=Depends(get_current_user)):
    """Update current user"""
    result = await update_user(current_user.email, update_data)
    if not result:
        raise HTTPException(status_code=400, detail="Erro ao atualizar usuario")
    return {"message": "Usuario atualizado"}


# ===========================================
# HEALTH
# ===========================================


@app.get("/health", tags=["System"])
async def health():
    """Health check with API status"""
    apis = {
        "anthropic": bool(settings.anthropic_api_key),
        "serper": bool(settings.serper_api_key),
        "tavily": bool(settings.tavily_api_key),
        "perplexity": bool(settings.perplexity_api_key),
        "apollo": bool(settings.apollo_api_key),
        "supabase": bool(settings.supabase_url),
    }

    configured = sum(apis.values())
    total = len(apis)

    return {
        "status": "healthy",
        "version": APP_VERSION,
        "git_sha": os.getenv("GIT_SHA", "unknown"),
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "apis": apis,
        "apis_configured": f"{configured}/{total}",
        "ready": configured >= 3,
    }


@app.get("/version", tags=["System"])
async def version():
    """Version endpoint for deployment verification"""
    return {
        "version": APP_VERSION,
        "git_sha": os.getenv("GIT_SHA", "unknown"),
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "service": "iconsai-scraping-api",
    }


# ===========================================
# CNAE ENDPOINTS
# ===========================================


@app.get("/api/cnae", tags=["CNAE"])
async def list_cnae(
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=100, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
):
    """
    List CNAEs from raw_cnae table.
    Returns: subclasse, descricao, descricao_secao, descricao_divisao,
             descricao_grupo, descricao_classe
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    # Sanitize search input (remove SQL metacharacters)
    sanitized_search = re.sub(r"[%_\\]", "", search.strip())[:100] if search else ""

    try:
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)

        query = supabase.table("raw_cnae").select(
            "subclasse, codigo, descricao, descricao_secao, "
            "descricao_divisao, descricao_grupo, descricao_classe"
        )

        if sanitized_search:
            # Search in codigo or descricao (sanitized input)
            query = query.or_(
                f"codigo.ilike.%{sanitized_search}%,descricao.ilike.%{sanitized_search}%,"
                f"descricao_secao.ilike.%{sanitized_search}%,descricao_grupo.ilike.%{sanitized_search}%"
            )

        query = query.order("codigo").range(offset, offset + limit - 1)
        result = query.execute()

        return {
            "success": True,
            "data": result.data,
            "count": len(result.data),
            "offset": offset,
            "limit": limit,
        }

    except Exception as e:
        logger.error("list_cnae_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# ENRICHMENT ENDPOINTS
# ===========================================


@app.post("/api/enrich/people", tags=["Enrichment"])
async def enrich_people(
    limit: int = Query(default=10, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    """
    Enrich people data using Apollo/Perplexity.
    Requires authentication.
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    if not settings.apollo_api_key and not settings.perplexity_api_key:
        raise HTTPException(status_code=500, detail="Neither Apollo nor Perplexity API configured")

    try:
        # Create Supabase client
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)

        # Get people without enrichment
        result = (
            supabase.table("dim_pessoas")
            .select("id, nome_completo, linkedin_url")
            .is_("raw_apollo_data", "null")
            .limit(limit)
            .execute()
        )

        people = result.data
        if not people:
            return {
                "success": True,
                "message": "No people pending enrichment",
                "stats": {"processed": 0},
            }

        # Create enrichment service
        service = PersonEnrichmentService(
            supabase=supabase,
            apollo_api_key=settings.apollo_api_key,
            perplexity_api_key=settings.perplexity_api_key,
        )

        stats = {"processed": 0, "success": 0, "failed": 0, "linkedin_found": 0}

        for pessoa in people:
            nome = pessoa.get("nome_completo", "Unknown")

            try:
                enrichment = await service.enrich_person(
                    pessoa_id=pessoa["id"],
                    nome=nome,
                    linkedin_url=pessoa.get("linkedin_url"),
                )

                stats["processed"] += 1

                if enrichment["success"]:
                    stats["success"] += 1
                    raw_data = enrichment.get("raw_data", {})
                    linkedin = raw_data.get("linkedin_url") if raw_data else None

                    if linkedin:
                        stats["linkedin_found"] += 1
                        supabase.table("dim_pessoas").update(
                            {
                                "linkedin_url": linkedin,
                                "raw_apollo_data": raw_data,
                            }
                        ).eq("id", pessoa["id"]).execute()
                    else:
                        supabase.table("dim_pessoas").update(
                            {
                                "raw_apollo_data": raw_data,
                            }
                        ).eq("id", pessoa["id"]).execute()
                else:
                    stats["failed"] += 1

            except Exception as e:
                stats["failed"] += 1
                logger.error("enrichment_error", pessoa=nome, error=str(e))

        return {
            "success": True,
            "message": f"Enrichment completed for {stats['processed']} people",
            "stats": stats,
        }

    except Exception as e:
        logger.error("enrich_people_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# STARTUP
# ===========================================


@app.on_event("startup")
async def startup():
    logger.info("api_starting", version=APP_VERSION)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
