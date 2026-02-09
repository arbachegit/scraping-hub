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
    <title>Iconsai Scraping - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e1a; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; position: relative; overflow: hidden; }
        .bg-effects { position: absolute; inset: 0; pointer-events: none; background-image: radial-gradient(circle at 30% 20%, rgba(0,255,255,0.08) 0%, transparent 40%), radial-gradient(circle at 70% 80%, rgba(59,130,246,0.08) 0%, transparent 40%); }
        .login-card { position: relative; width: 100%; max-width: 28rem; background: rgba(15,22,41,0.9); backdrop-filter: blur(12px); border-radius: 1rem; border: 1px solid rgba(6,182,212,0.2); box-shadow: 0 0 50px rgba(0,255,255,0.1); overflow: hidden; }
        .card-header { background: linear-gradient(to right, rgba(6,182,212,0.1), rgba(59,130,246,0.1), rgba(168,85,247,0.1)); padding: 2rem; border-bottom: 1px solid rgba(6,182,212,0.1); text-align: center; }
        .logo { height: 4rem; width: auto; margin-bottom: 1rem; }
        .title { font-size: 1.75rem; font-weight: 700; background: linear-gradient(to right, #22d3ee, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: rgba(6,182,212,0.6); margin-top: 0.5rem; font-size: 0.875rem; }
        .card-content { padding: 2rem; }
        .form-group { margin-bottom: 1.25rem; }
        .form-label { display: block; font-size: 0.875rem; font-weight: 500; color: #cbd5e1; margin-bottom: 0.5rem; }
        .form-input { width: 100%; height: 3rem; padding: 0 1rem; border-radius: 0.75rem; background: #1a2332; border: 1px solid rgba(6,182,212,0.3); color: #fff; font-size: 1rem; }
        .form-input::placeholder { color: #64748b; }
        .form-input:focus { outline: none; border-color: #22d3ee; box-shadow: 0 0 0 3px rgba(6,182,212,0.2); }
        .error-message { display: none; margin-bottom: 1rem; padding: 0.75rem; border-radius: 0.5rem; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #f87171; font-size: 0.875rem; }
        .error-message.show { display: block; }
        .btn-primary { width: 100%; height: 3rem; border-radius: 0.75rem; background: linear-gradient(to right, #06b6d4, #3b82f6); color: #fff; font-weight: 600; font-size: 1rem; border: none; cursor: pointer; transition: all 0.2s; }
        .btn-primary:hover { box-shadow: 0 0 30px rgba(0,255,255,0.4); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
        .links { display: flex; justify-content: center; padding-top: 1rem; gap: 1rem; }
        .link { color: #22d3ee; text-decoration: none; font-size: 0.875rem; }
        .link:hover { color: #67e8f9; }
        .card-footer { padding: 0 2rem 1.5rem; text-align: center; }
        .footer-text { font-size: 0.75rem; color: #64748b; }
    </style>
</head>
<body>
    <div class="bg-effects"></div>
    <div class="login-card">
        <div class="card-header">
            <img src="/static/images/iconsai-logo.png" alt="Iconsai" class="logo" onerror="this.style.display='none'">
            <h1 class="title">Scraping Hub</h1>
            <p class="subtitle">Business Intelligence Brasil</p>
        </div>
        <div class="card-content">
            <div class="error-message" id="errorMessage"></div>
            <form id="loginForm">
                <div class="form-group"><label class="form-label">Email</label><input type="email" id="email" class="form-input" required placeholder="seu@email.com"></div>
                <div class="form-group"><label class="form-label">Senha</label><input type="password" id="password" class="form-input" required placeholder="********"></div>
                <button type="submit" class="btn-primary" id="btnLogin">Entrar</button>
            </form>
            <div class="links"><a href="/docs" class="link">API Docs</a><a href="/redoc" class="link">ReDoc</a></div>
        </div>
        <div class="card-footer"><p class="footer-text">Iconsai - Todos os direitos reservados</p></div>
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
            } catch (e) { err.textContent = 'Erro de conexao'; err.classList.add('show'); }
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
    <title>Iconsai Scraping - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e1a; min-height: 100vh; color: #fff; }
        .header { background: rgba(15,22,41,0.8); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(6,182,212,0.1); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .header-left { display: flex; align-items: center; gap: 1rem; }
        .header-logo { height: 2.5rem; width: auto; }
        .header h1 { font-size: 1.25rem; font-weight: 700; background: linear-gradient(to right, #22d3ee, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-right { display: flex; align-items: center; gap: 1rem; }
        .user-email { color: #94a3b8; font-size: 0.875rem; }
        .btn-logout { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #f87171; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.875rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card { background: rgba(15,22,41,0.8); border: 1px solid rgba(6,182,212,0.2); border-radius: 1rem; padding: 1.5rem; }
        .card h3 { color: #fff; font-size: 1.125rem; margin-bottom: 0.75rem; }
        .card p { color: #94a3b8; font-size: 0.875rem; margin-bottom: 1rem; }
        .card-link { display: inline-block; background: linear-gradient(to right, #06b6d4, #3b82f6); color: #fff; padding: 0.625rem 1.25rem; border-radius: 0.5rem; text-decoration: none; font-weight: 500; font-size: 0.875rem; }
        .status-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
        .status-healthy { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); color: #4ade80; }
        .search-section { background: rgba(15,22,41,0.8); border: 1px solid rgba(6,182,212,0.2); border-radius: 1rem; padding: 1.5rem; }
        .search-section h3 { color: #fff; font-size: 1.125rem; margin-bottom: 1rem; }
        .search-form { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
        .search-input { flex: 1; padding: 0.75rem 1rem; background: #1a2332; border: 1px solid rgba(6,182,212,0.3); border-radius: 0.5rem; color: #fff; font-size: 1rem; }
        .search-input:focus { outline: none; border-color: #22d3ee; }
        .search-btn { padding: 0.75rem 1.5rem; background: linear-gradient(to right, #06b6d4, #3b82f6); color: #fff; border: none; border-radius: 0.5rem; font-weight: 600; cursor: pointer; }
        .result-item { padding: 1rem; background: rgba(26,35,50,0.5); border: 1px solid rgba(6,182,212,0.1); border-radius: 0.5rem; margin-bottom: 0.75rem; }
        .result-item h4 { color: #fff; font-size: 1rem; margin-bottom: 0.5rem; }
        .result-item p { color: #94a3b8; font-size: 0.875rem; margin: 0.25rem 0; }
        .result-item strong { color: #22d3ee; }
        .api-count { font-size: 2rem; font-weight: 700; background: linear-gradient(to right, #22d3ee, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <img src="/static/images/iconsai-logo.png" alt="Iconsai" class="header-logo" onerror="this.style.display='none'">
            <h1>Scraping Hub</h1>
        </div>
        <div class="header-right">
            <span class="user-email" id="userEmail">-</span>
            <button class="btn-logout" onclick="logout()">Sair</button>
        </div>
    </div>
    <div class="container">
        <div class="cards">
            <div class="card"><h3>API Status</h3><span class="api-count" id="apiCount">-</span><p id="apiStatus">Verificando...</p></div>
            <div class="card"><h3>Documentacao</h3><p>Explore todos os endpoints</p><a href="/docs" class="card-link">Swagger UI</a></div>
            <div class="card"><h3>Endpoints</h3><p>Empresas, Pessoas, Politicos</p><a href="/redoc" class="card-link">ReDoc</a></div>
        </div>
        <div class="search-section">
            <h3>Buscar Empresa por Nome (CNPJ)</h3>
            <div class="search-form"><input type="text" id="companyName" class="search-input" placeholder="Ex: Natura, Magazine Luiza"><button onclick="searchCNPJ()" class="search-btn">Buscar</button></div>
            <div id="results"></div>
        </div>
    </div>
    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/';
        async function fetchAuth(url, opt={}) { return fetch(url, {...opt, headers: {...opt.headers, 'Authorization': 'Bearer '+token}}); }
        async function loadUser() { try { const r = await fetchAuth('/auth/me'); if (r.ok) { const u = await r.json(); document.getElementById('userEmail').textContent = u.email; } else if (r.status === 401) logout(); } catch(e){} }
        async function loadStatus() { try { const r = await fetch('/health'); const d = await r.json(); document.getElementById('apiCount').textContent = d.apis_configured; document.getElementById('apiStatus').textContent = d.ready ? 'Sistema operacional' : 'Sistema degradado'; } catch(e){} }
        async function searchCNPJ() {
            const name = document.getElementById('companyName').value; if (!name) return;
            document.getElementById('results').innerHTML = '<p style="color:#94a3b8">Buscando...</p>';
            try {
                const r = await fetchAuth('/api/v2/company/cnpj/search', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ company_name: name, max_results: 5 }) });
                const d = await r.json();
                if (d.companies && d.companies.length > 0) { document.getElementById('results').innerHTML = d.companies.map(c => '<div class="result-item"><h4>'+(c.razao_social||c.nome_fantasia||'N/A')+'</h4><p><strong>CNPJ:</strong> '+c.cnpj+'</p></div>').join(''); }
                else { document.getElementById('results').innerHTML = '<div class="result-item"><p>Nenhuma empresa encontrada</p></div>'; }
            } catch(e) { document.getElementById('results').innerHTML = '<div class="result-item"><p>Erro na busca</p></div>'; }
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
