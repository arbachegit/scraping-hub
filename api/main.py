"""
IconsAI Scraping API v2.0
API REST para Business Intelligence Brasil
"""

from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings as app_settings

from .auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    TokenData,
    UserLogin,
    UserResponse,
    UserUpdate,
    authenticate_user,
    create_access_token,
    get_current_user,
    update_user,
)
from .routes import (
    analytics_router,
    companies_router,
    news_router,
    people_router,
    politicians_router,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    logger.info("api_startup", message="IconsAI Scraping v2.0 iniciando...")
    yield
    logger.info("api_shutdown", message="IconsAI Scraping v2.0 encerrando...")


app = FastAPI(
    title="IconsAI Scraping API",
    description="""
## Business Intelligence Brasil v2.0

API para análise de inteligência empresarial focada no mercado brasileiro.

### Funcionalidades

**Empresas**
- Análise completa com SWOT e OKRs
- Identificação de concorrentes
- Busca de funcionários e decisores

**Pessoas**
- Análise de perfil profissional
- Fit cultural com empresas
- Comparação de candidatos

**Políticos**
- Perfil pessoal (não político)
- Presença em redes sociais
- Percepção pública

**Notícias**
- Monitoramento de empresas/setores
- Cenário econômico
- Alertas e briefings

### APIs Utilizadas
- BrasilAPI (CNPJ)
- Serper.dev (Google Search)
- Tavily (AI Search)
- Perplexity (Research)
- Apollo.io (LinkedIn/Contatos)
- Claude (Análise AI)
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - Configuração segura via settings
# Determinar origens permitidas
_allowed_origins = app_settings.parsed_allowed_origins
if app_settings.is_development:
    # Em desenvolvimento, adicionar origens comuns de dev
    _allowed_origins = list(
        set(
            _allowed_origins
            + [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8000",
            ]
        )
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Static files - resolve absolute path
static_path = Path(__file__).resolve().parent.parent / "static"
logger.info("static_path", path=str(static_path), exists=static_path.exists())

if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ===========================================
# INCLUDE ROUTERS
# ===========================================

app.include_router(analytics_router)
app.include_router(companies_router)
app.include_router(people_router)
app.include_router(politicians_router)
app.include_router(news_router)


# ===========================================
# ROOT & HEALTH
# ===========================================


@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend login page"""
    index_file = static_path / "index.html"
    logger.debug("root_request", index_file=str(index_file), exists=index_file.exists())
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return {
        "service": "IconsAI Scraping API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/dashboard.html", include_in_schema=False)
async def dashboard():
    """Serve the dashboard page"""
    dashboard_file = static_path / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/health")
async def health():
    """Health check endpoint com status das APIs"""
    from config.settings import settings

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
        "status": "healthy" if configured >= 3 else "degraded",
        "version": "2.0.0",
        "apis": apis,
        "apis_configured": f"{configured}/{total}",
        "ready": configured >= 3,
    }


@app.get("/api/v2/status")
async def api_status(current_user: TokenData = Depends(get_current_user)):
    """Status da API (autenticado)"""
    return {
        "status": "operational",
        "version": "2.0.0",
        "user": current_user.email,
        "endpoints": {
            "companies": "/api/v2/company",
            "people": "/api/v2/person",
            "politicians": "/api/v2/politician",
            "news": "/api/v2/news",
        },
    }


# ===========================================
# AUTH
# ===========================================


@app.post("/auth/login", response_model=Token, tags=["Auth"])
async def login(user_data: UserLogin):
    """Login endpoint"""
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": user["id"], "role": user["role"]},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current user info"""
    from .auth import get_user_from_db

    user = await get_user_from_db(current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return UserResponse(
        id=user["id"], email=user["email"], name=user.get("name"), role=user["role"]
    )


@app.put("/auth/me", response_model=Token, tags=["Auth"])
async def update_me(update_data: UserUpdate, current_user: TokenData = Depends(get_current_user)):
    """
    Update current user profile

    - name: Update display name
    - email: Update email (must be unique)
    - current_password + new_password: Change password
    """
    updated_user = await update_user(current_user.email, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=400, detail="Falha na atualizacao. Verifique os dados e senha atual."
        )

    # Generate new token with updated info
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": updated_user["email"],
            "user_id": updated_user["id"],
            "role": updated_user["role"],
        },
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ===========================================
# LEGACY ENDPOINTS (v1 compatibility)
# ===========================================


@app.get("/empresa/search", tags=["Legacy"], deprecated=True)
async def legacy_empresa_search(
    name: str = None, current_user: TokenData = Depends(get_current_user)
):
    """
    [DEPRECATED] Use /api/v2/company/search

    Endpoint mantido para compatibilidade.
    """
    if not name:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")

    from src.services import CompanyIntelService

    async with CompanyIntelService() as service:
        result = await service.quick_lookup(name)
        return {"count": 1 if result else 0, "data": [result] if result else []}


@app.get("/scrape", tags=["Legacy"], deprecated=True)
async def legacy_scrape(url: str, current_user: TokenData = Depends(get_current_user)):
    """
    [DEPRECATED] Web scraping básico

    Use os novos endpoints de /api/v2/company para análise completa.
    """
    from src.scrapers import WebScraperClient

    async with WebScraperClient() as scraper:
        result = await scraper.scrape(url)
        return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
