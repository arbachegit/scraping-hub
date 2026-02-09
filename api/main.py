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
    from fastapi.responses import HTMLResponse

    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")

    # Fallback: embedded login page
    return HTMLResponse(content=LOGIN_HTML, status_code=200)


LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IconsAI Scraping - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-container { background: rgba(255,255,255,0.95); padding: 40px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 100%; max-width: 400px; }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #1a1a2e; font-size: 28px; }
        .logo p { color: #666; font-size: 14px; margin-top: 5px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; color: #333; font-weight: 500; margin-bottom: 8px; }
        .form-group input { width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px; }
        .form-group input:focus { outline: none; border-color: #0f3460; }
        .btn-login { width: 100%; padding: 14px; background: linear-gradient(135deg, #0f3460, #1a1a2e); color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(15,52,96,0.4); }
        .error-message { background: #fee; color: #c00; padding: 12px; border-radius: 8px; margin-bottom: 20px; display: none; }
        .error-message.show { display: block; }
        .links { text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; }
        .links a { color: #0f3460; text-decoration: none; margin: 0 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo"><h1>IconsAI Scraping</h1><p>Business Intelligence Brasil</p></div>
        <div class="error-message" id="errorMessage"></div>
        <form id="loginForm">
            <div class="form-group"><label>Email</label><input type="email" id="email" required placeholder="seu@email.com"></div>
            <div class="form-group"><label>Senha</label><input type="password" id="password" required placeholder="Sua senha"></div>
            <button type="submit" class="btn-login" id="btnLogin">Entrar</button>
        </form>
        <div class="links"><a href="/docs">API Docs</a><a href="/redoc">ReDoc</a></div>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnLogin');
            const err = document.getElementById('errorMessage');
            btn.disabled = true; btn.textContent = 'Entrando...'; err.classList.remove('show');
            try {
                const r = await fetch('/auth/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ email: document.getElementById('email').value, password: document.getElementById('password').value }) });
                const data = await r.json();
                if (r.ok) { localStorage.setItem('token', data.access_token); window.location.href = '/dashboard.html'; }
                else { err.textContent = data.detail || 'Email ou senha incorretos'; err.classList.add('show'); }
            } catch (e) { err.textContent = 'Erro de conexão'; err.classList.add('show'); }
            finally { btn.disabled = false; btn.textContent = 'Entrar'; }
        });
    </script>
</body>
</html>"""


@app.get("/dashboard.html", include_in_schema=False)
async def dashboard():
    """Serve the dashboard page"""
    from fastapi.responses import HTMLResponse

    dashboard_file = static_path / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file), media_type="text/html")
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IconsAI Scraping - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); color: white; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; }
        .btn-logout { background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h3 { color: #1a1a2e; margin-bottom: 16px; }
        .card p { color: #666; font-size: 14px; margin-bottom: 16px; }
        .card a { display: inline-block; background: #0f3460; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; }
        .search-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .search-form { display: flex; gap: 10px; margin-bottom: 20px; }
        .search-form input { flex: 1; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; }
        .search-form button { padding: 12px 24px; background: #0f3460; color: white; border: none; border-radius: 8px; cursor: pointer; }
        .results { margin-top: 20px; }
        .result-item { padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px; }
        .result-item h4 { color: #1a1a2e; }
        .result-item p { color: #666; font-size: 14px; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="header"><h1>IconsAI Scraping</h1><div><span id="userEmail">-</span> <button class="btn-logout" onclick="logout()">Sair</button></div></div>
    <div class="container">
        <div class="cards">
            <div class="card"><h3>API Status</h3><p id="apiStatus">Verificando...</p></div>
            <div class="card"><h3>Documentacao</h3><p>Explore os endpoints</p><a href="/docs">Swagger UI</a></div>
            <div class="card"><h3>Endpoints</h3><p>Empresas, Pessoas, Politicos</p><a href="/redoc">ReDoc</a></div>
        </div>
        <div class="search-section">
            <h3>Buscar Empresa por Nome (CNPJ)</h3>
            <div class="search-form"><input type="text" id="companyName" placeholder="Ex: Natura, Magazine Luiza"><button onclick="searchCNPJ()">Buscar</button></div>
            <div class="results" id="results"></div>
        </div>
    </div>
    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/';
        async function fetchAuth(url, opt={}) { return fetch(url, {...opt, headers: {...opt.headers, 'Authorization': 'Bearer '+token}}); }
        async function loadUser() { try { const r = await fetchAuth('/auth/me'); if (r.ok) { const u = await r.json(); document.getElementById('userEmail').textContent = u.email; } else if (r.status === 401) logout(); } catch(e){} }
        async function loadStatus() { try { const r = await fetch('/health'); const d = await r.json(); document.getElementById('apiStatus').textContent = d.apis_configured + ' APIs - ' + d.status; } catch(e){} }
        async function searchCNPJ() {
            const name = document.getElementById('companyName').value; if (!name) return;
            document.getElementById('results').innerHTML = '<p>Buscando...</p>';
            try {
                const r = await fetchAuth('/api/v2/company/cnpj/search', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ company_name: name, max_results: 5 }) });
                const d = await r.json();
                if (d.companies && d.companies.length > 0) { document.getElementById('results').innerHTML = d.companies.map(c => '<div class="result-item"><h4>'+(c.razao_social||c.nome_fantasia||'N/A')+'</h4><p><strong>CNPJ:</strong> '+c.cnpj+'</p></div>').join(''); }
                else { document.getElementById('results').innerHTML = '<p>Nenhuma empresa encontrada</p>'; }
            } catch(e) { document.getElementById('results').innerHTML = '<p>Erro na busca</p>'; }
        }
        function logout() { localStorage.removeItem('token'); window.location.href = '/'; }
        loadUser(); loadStatus();
    </script>
</body>
</html>"""


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
