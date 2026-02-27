#!/usr/bin/env python3
"""
Adiciona endpoint /version aos servicos API (Python) e Backend (Node.js).

USO: python3 scripts/add_version_endpoints.py

Este script modifica:
  1. api/main.py   — Adiciona GET /version (FastAPI)
  2. backend/src/index.js — Adiciona GET /version (Express)

Idempotente: se o endpoint ja existe, nao faz nada.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# 1. Python API — FastAPI /version endpoint
# =============================================================================

PYTHON_VERSION_CODE = '''
# --- Version endpoint (deploy deterministic) ---
@app.get("/version", tags=["System"])
async def version():
    """Retorna SHA do commit em execucao para validacao de deploy."""
    import os as _os
    from datetime import datetime as _dt
    sha = _os.getenv("GIT_SHA", "unknown")
    return {
        "sha": sha,
        "version": f"sha-{sha}" if not sha.startswith("sha-") else sha,
        "service": "api-python",
        "build_date": _os.getenv("BUILD_DATE", "unknown"),
        "timestamp": _dt.utcnow().isoformat() + "Z",
    }
'''

PYTHON_HEALTH_CODE = '''
# --- Health endpoint ---
@app.get("/health", tags=["System"])
async def health():
    """Health check para Docker e load balancer."""
    import os as _os
    return {
        "status": "healthy",
        "service": "api-python",
        "version": _os.getenv("GIT_SHA", "unknown"),
    }
'''


def patch_python_api():
    main_py = os.path.join(PROJECT_ROOT, "api", "main.py")
    if not os.path.exists(main_py):
        print(f"[SKIP] {main_py} nao encontrado")
        return False

    try:
        import signal

        def _timeout_handler(signum, frame):
            raise TimeoutError("File read timed out (iCloud?)")

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        with open(main_py, "r") as f:
            content = f.read()
        signal.alarm(0)
    except (TimeoutError, OSError) as e:
        print(f"[WARN] {main_py} nao acessivel ({e}). Re-execute quando iCloud sincronizar.")
        return False

    modified = False

    # Adiciona /version se nao existe
    if '"/version"' not in content and "'/version'" not in content:
        # Insere apos a ultima linha que contem app.include_router ou apos app = FastAPI
        # Tenta encontrar um bom ponto de insercao
        insert_after = None
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if "app.include_router" in line:
                insert_after = i
            elif '@app.get("/health")' in line or "@app.get('/health')" in line:
                insert_after = i - 1  # Insere antes do health

        if insert_after is None:
            # Fallback: insere no final
            content += PYTHON_VERSION_CODE
        else:
            lines.insert(insert_after + 1, PYTHON_VERSION_CODE)
            content = "\n".join(lines)

        modified = True
        print("[OK] /version endpoint adicionado a api/main.py")

    # Adiciona /health se nao existe
    if '"/health"' not in content and "'/health'" not in content:
        content += PYTHON_HEALTH_CODE
        modified = True
        print("[OK] /health endpoint adicionado a api/main.py")

    if modified:
        with open(main_py, "w") as f:
            f.write(content)
    else:
        print("[SKIP] api/main.py ja tem endpoints /version e /health")

    return modified


# =============================================================================
# 2. Node.js Backend — Express /version endpoint
# =============================================================================

NODE_VERSION_CODE = """
// --- Version endpoint (deploy deterministic) ---
app.get('/version', (req, res) => {
  const sha = process.env.GIT_SHA || 'unknown';
  res.json({
    sha,
    version: sha.startsWith('sha-') ? sha : `sha-${sha}`,
    service: 'api-node',
    build_date: process.env.BUILD_DATE || 'unknown',
    timestamp: new Date().toISOString(),
  });
});
"""

NODE_HEALTH_CODE = """
// --- Health endpoint ---
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'api-node',
    version: process.env.GIT_SHA || 'unknown',
  });
});
"""


def patch_node_backend():
    index_js = os.path.join(PROJECT_ROOT, "backend", "src", "index.js")
    if not os.path.exists(index_js):
        print(f"[SKIP] {index_js} nao encontrado")
        return False

    try:
        import signal

        def _timeout_handler(signum, frame):
            raise TimeoutError("File read timed out (iCloud?)")

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        with open(index_js, "r") as f:
            content = f.read()
        signal.alarm(0)
    except (TimeoutError, OSError) as e:
        print(f"[WARN] {index_js} nao acessivel ({e}). Re-execute quando iCloud sincronizar.")
        return False

    modified = False

    # Adiciona /version se nao existe
    if "'/version'" not in content and '"/version"' not in content:
        # Insere antes do app.listen
        if "app.listen" in content:
            content = content.replace(
                "app.listen",
                NODE_VERSION_CODE + "\napp.listen",
                1,
            )
        else:
            content += NODE_VERSION_CODE
        modified = True
        print("[OK] /version endpoint adicionado a backend/src/index.js")

    # Adiciona /health se nao existe
    if "'/health'" not in content and '"/health"' not in content:
        if "app.listen" in content:
            content = content.replace(
                "app.listen",
                NODE_HEALTH_CODE + "\napp.listen",
                1,
            )
        else:
            content += NODE_HEALTH_CODE
        modified = True
        print("[OK] /health endpoint adicionado a backend/src/index.js")

    if modified:
        with open(index_js, "w") as f:
            f.write(content)
    else:
        print("[SKIP] backend/src/index.js ja tem endpoints /version e /health")

    return modified


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Adicionando endpoints /version e /health")
    print("=" * 50)

    py_ok = patch_python_api()
    js_ok = patch_node_backend()

    if py_ok or js_ok:
        print("\n[DONE] Endpoints adicionados. Teste com:")
        print("  curl http://localhost:8000/version")
        print("  curl http://localhost:3001/version")
    else:
        print("\n[DONE] Nenhuma mudanca necessaria")

    sys.exit(0)
