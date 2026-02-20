#!/usr/bin/env bash
# verify_runtime.sh - Verifica se containers estão rodando a versão correta
#
# USO: ./verify_runtime.sh
#
# RETORNO:
#   0 - Tudo OK
#   1 - Mismatch detectado

set -euo pipefail

# ============================================
# CONFIGURAÇÃO
# ============================================
PROJECT_DIR="${PROJECT_DIR:-/opt/iconsai-scraping}"
ENV_FILE="${ENV_FILE:-.env}"

# ============================================
# CORES
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# VERIFICAÇÃO
# ============================================

cd "${PROJECT_DIR}"

# Lê SHA esperado do .env
EXPECTED_SHA=""
if [[ -f "${ENV_FILE}" ]]; then
    EXPECTED_SHA=$(grep -E "^GIT_SHA=" "${ENV_FILE}" | cut -d'=' -f2 || echo "")
fi

if [[ -z "${EXPECTED_SHA}" ]]; then
    log_error "GIT_SHA não definido em ${ENV_FILE}"
    exit 1
fi

log_info "============================================"
log_info "VERIFICAÇÃO DE RUNTIME"
log_info "============================================"
log_info "SHA esperado: ${EXPECTED_SHA}"
log_info "============================================"

HAS_ERROR=0

# Containers para verificar
declare -A containers
containers["iconsai-api"]="8000"
containers["iconsai-backend"]="3001"
containers["iconsai-scheduler"]=""

for container in "${!containers[@]}"; do
    echo ""
    log_info "=== ${container} ==="

    # Status do container
    container_status=$(docker inspect --format='{{.State.Status}}' "${container}" 2>/dev/null || echo "not found")
    echo "  Status: ${container_status}"

    if [[ "${container_status}" == "not found" ]]; then
        log_warn "Container não encontrado"
        continue
    fi

    # SHA em execução
    running_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${container}" 2>/dev/null | grep "^GIT_SHA=" | cut -d= -f2 || echo "N/A")
    echo "  GIT_SHA: ${running_sha}"

    # Imagem
    running_image=$(docker inspect --format='{{.Config.Image}}' "${container}" 2>/dev/null || echo "N/A")
    echo "  Image: ${running_image}"

    # Health status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "N/A")
    echo "  Health: ${health_status}"

    # Verifica SHA
    if [[ "${running_sha}" == "${EXPECTED_SHA}" ]]; then
        log_ok "SHA correto"
    elif [[ "${running_sha}" == "N/A" ]]; then
        log_warn "SHA não disponível"
    else
        log_error "SHA INCORRETO! Esperado: ${EXPECTED_SHA}"
        HAS_ERROR=1
    fi

    # Tenta /version se tiver porta
    port="${containers[$container]}"
    if [[ -n "${port}" ]]; then
        version_response=$(curl -sf "http://localhost:${port}/version" 2>/dev/null || echo "N/A")
        echo "  /version: ${version_response}"
    fi
done

echo ""
log_info "============================================"

if [[ ${HAS_ERROR} -eq 1 ]]; then
    log_error "MISMATCH DETECTADO!"
    exit 1
else
    log_ok "TODOS OS CONTAINERS COM VERSÃO CORRETA"
    exit 0
fi
