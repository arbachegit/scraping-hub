"""
Scraping Hub API
API REST para serviços de scraping
"""

from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.scrapers import CoresignalClient, FirecrawlClient

from .auth import (
    Token, UserLogin, UserResponse, TokenData,
    authenticate_user, create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = structlog.get_logger()

# Clients globais
coresignal: Optional[CoresignalClient] = None
firecrawl: Optional[FirecrawlClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    global coresignal, firecrawl

    logger.info("api_startup", message="Inicializando clientes...")

    coresignal = CoresignalClient()
    firecrawl = FirecrawlClient()

    yield

    logger.info("api_shutdown", message="Fechando clientes...")
    await coresignal.close()
    await firecrawl.close()


app = FastAPI(
    title="Scraping Hub API",
    description="API para enriquecimento de dados de empresas, LinkedIn e governo",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ===========================================
# SCHEMAS
# ===========================================

class ScrapeRequest(BaseModel):
    url: str
    formats: List[str] = ["markdown"]
    only_main_content: bool = True


# ===========================================
# ROOT & STATIC
# ===========================================

@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend"""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "service": "Scraping Hub API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ===========================================
# AUTH
# ===========================================

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login endpoint"""
    user = authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email ou senha incorretos"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["email"],
            "user_id": user["id"],
            "role": user["role"]
        },
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current user info"""
    from .auth import USERS_DB
    user = USERS_DB.get(current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"]
    )


# ===========================================
# EMPRESA (Coresignal)
# ===========================================

@app.get("/empresa/search")
async def search_empresas(
    name: Optional[str] = None,
    website: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = Query(default=10, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """Busca empresas por critérios"""
    try:
        logger.info("empresa_search", user=current_user.email, name=name)
        results = await coresignal.search_companies(
            name=name,
            website=website,
            industry=industry,
            country=country,
            limit=limit
        )
        return {"count": len(results), "data": results}
    except Exception as e:
        logger.error("empresa_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/empresa/{company_id}")
async def get_empresa(
    company_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Obtém detalhes de uma empresa pelo ID"""
    try:
        result = await coresignal.get_company(company_id)
        if not result:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("empresa_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/empresa/linkedin/search")
async def get_empresa_by_linkedin(
    url: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Busca empresa pelo URL do LinkedIn"""
    try:
        result = await coresignal.get_company_by_linkedin(url)
        if not result:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("empresa_linkedin_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/empresa/{company_id}/employees")
async def get_empresa_employees(
    company_id: str,
    limit: int = Query(default=50, le=200),
    current_user: TokenData = Depends(get_current_user)
):
    """Lista funcionários de uma empresa"""
    try:
        results = await coresignal.get_company_employees(company_id, limit=limit)
        return {"count": len(results), "data": results}
    except Exception as e:
        logger.error("empresa_employees_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# LINKEDIN (Requer Proxycurl)
# ===========================================

@app.get("/linkedin/search")
async def search_profissionais(current_user: TokenData = Depends(get_current_user)):
    """Busca profissionais - Requer Proxycurl API"""
    raise HTTPException(
        status_code=503,
        detail="LinkedIn search requer Proxycurl API. Configure PROXYCURL_API_KEY no .env"
    )


@app.get("/linkedin/profile/{member_id}")
async def get_profissional(
    member_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Perfil profissional - Requer Proxycurl API"""
    raise HTTPException(
        status_code=503,
        detail="LinkedIn profile requer Proxycurl API. Configure PROXYCURL_API_KEY no .env"
    )


@app.get("/linkedin/profile")
async def get_profissional_by_url(
    url: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Busca por URL - Requer Proxycurl API"""
    raise HTTPException(
        status_code=503,
        detail="LinkedIn profile requer Proxycurl API. Configure PROXYCURL_API_KEY no .env"
    )


# ===========================================
# SCRAPE (Firecrawl)
# ===========================================

@app.post("/scrape")
async def scrape_url_post(
    request: ScrapeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Faz scrape de uma URL"""
    try:
        logger.info("scrape", user=current_user.email, url=request.url)
        result = await firecrawl.scrape_url(
            url=request.url,
            formats=request.formats,
            only_main_content=request.only_main_content
        )
        return result
    except Exception as e:
        logger.error("scrape_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape")
async def scrape_url_get(
    url: str,
    format: str = "markdown",
    current_user: TokenData = Depends(get_current_user)
):
    """Faz scrape de uma URL (GET)"""
    try:
        logger.info("scrape", user=current_user.email, url=url)
        result = await firecrawl.scrape_url(
            url=url,
            formats=[format]
        )
        return result
    except Exception as e:
        logger.error("scrape_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/map")
async def map_site(
    url: str,
    limit: int = Query(default=100, le=5000),
    current_user: TokenData = Depends(get_current_user)
):
    """Mapeia URLs de um site"""
    try:
        logger.info("map", user=current_user.email, url=url)
        urls = await firecrawl.map_site(url=url, limit=limit)
        return {"count": len(urls), "urls": urls}
    except Exception as e:
        logger.error("map_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/crawl")
async def crawl_site(
    url: str,
    max_depth: int = Query(default=2, le=5),
    limit: int = Query(default=50, le=200),
    current_user: TokenData = Depends(get_current_user)
):
    """Inicia crawl de um site"""
    try:
        logger.info("crawl", user=current_user.email, url=url)
        result = await firecrawl.crawl_site(
            url=url,
            max_depth=max_depth,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error("crawl_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/crawl/{crawl_id}")
async def get_crawl_status(
    crawl_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Verifica status de um crawl"""
    try:
        return await firecrawl.get_crawl_status(crawl_id)
    except Exception as e:
        logger.error("crawl_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
