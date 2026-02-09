"""
IconsAI Scraping API - v3.0 (Clean Architecture)
"""

from datetime import timedelta
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
from config.settings import settings

logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="IconsAI Scraping API",
    description="API de inteligencia de dados",
    version="3.0.0",
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


@app.get("/dashboard.html", include_in_schema=False)
async def dashboard():
    """Serve dashboard page"""
    dashboard_file = static_path / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    return {"error": "dashboard.html not found"}


@app.get("/admin.html", include_in_schema=False)
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
        "version": "3.0.0",
        "apis": apis,
        "apis_configured": f"{configured}/{total}",
        "ready": configured >= 3,
    }


# ===========================================
# STARTUP
# ===========================================

@app.on_event("startup")
async def startup():
    logger.info("api_starting", version="3.0.0")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
