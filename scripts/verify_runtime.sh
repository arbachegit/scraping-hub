#!/usr/bin/env bash
# =============================================================================
# verify_runtime.sh — Verifica se containers rodam a versao correta
# =============================================================================
# USO: ./verify_runtime.sh
#
# Le IMAGE_TAG do .env e compara com o que cada container esta rodando.
# Retorna exit 0 se tudo OK, exit 1 se mismatch.
# =============================================================================

set -euo pipefail

# ============================================
# CONFIGURACAO
# ============================================
PROJECT_DIR="${PROJECT_DIR:-/opt/iconsai-scraping}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"

# ============================================
# CORES
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ============================================
# LER SHA ESPERADO
# ============================================

cd "${PROJECT_DIR}"

EXPECTED_TAG=""
EXPECTED_SHA=""
if [[ -f "${ENV_FILE}" ]]; then
    EXPECTED_TAG=$(grep -E "^IMAGE_TAG=" "${ENV_FILE}" | cut -d'=' -f2 || echo "")
    EXPECTED_SHA=$(grep -E "^GIT_SHA=" "${ENV_FILE}" | cut -d'=' -f2 || echo "")
fi

if [[ -z "${EXPECTED_TAG}" ]]; then
    log_error "IMAGE_TAG nao definido em ${ENV_FILE}"
    exit 1
fi

log_info "============================================"
log_info "VERIFICACAO DE RUNTIME"
log_info "============================================"
log_info "IMAGE_TAG esperado: ${EXPECTED_TAG}"
log_info "GIT_SHA esperado:   ${EXPECTED_SHA}"
log_info "============================================"

HAS_ERROR=0
CONTAINERS=("iconsai-web" "iconsai-api" "iconsai-backend" "iconsai-scheduler")

for container in "${CONTAINERS[@]}"; do
    echo ""
    log_info "=== ${container} ==="

    # Status do container
    local_status=$(docker inspect --format='{{.State.Status}}' "${container}" 2>/dev/null || echo "not found")
    echo "  Status: ${local_status}"

    if [[ "${local_status}" == "not found" ]]; then
        log_error "Container nao encontrado"
        HAS_ERROR=1
        continue
    fi

    # Imagem em execucao
    running_image=$(docker inspect --format='{{.Config.Image}}' "${container}" 2>/dev/null || echo "N/A")
    echo "  Imagem: ${running_image}"

    # GIT_SHA do container
    container_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${container}" 2>/dev/null \
        | grep "^GIT_SHA=" | cut -d= -f2 || echo "unknown")
    echo "  GIT_SHA: ${container_sha}"

    # Health status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "N/A")
    echo "  Health: ${health_status}"

    # Verificar tag na imagem
    if [[ "${running_image}" == *"${EXPECTED_TAG}"* ]]; then
        log_ok "Tag correta na imagem"
    else
        log_error "TAG INCORRETA! Esperado contendo: ${EXPECTED_TAG}"
        HAS_ERROR=1
    fi

    # Verificar GIT_SHA
    if [[ -n "${EXPECTED_SHA}" && "${container_sha}" == "${EXPECTED_SHA}" ]]; then
        log_ok "GIT_SHA correto"
    elif [[ -n "${EXPECTED_SHA}" && "${container_sha}" != "${EXPECTED_SHA}" ]]; then
        log_error "GIT_SHA INCORRETO! Esperado=${EXPECTED_SHA} Atual=${container_sha}"
        HAS_ERROR=1
    fi
done

# ============================================
# VERIFICAR ENDPOINTS /version
# ============================================
echo ""
log_info "=== Endpoints /version ==="

declare -A ports
ports["api"]=8000
ports["backend"]=3001

for service in "${!ports[@]}"; do
    local_port="${ports[$service]}"
    response=$(curl -sf "http://localhost:${local_port}/version" 2>/dev/null || echo "")
    if [[ -n "${response}" ]]; then
        echo "  ${service} (${local_port}): ${response}"
    else
        echo "  ${service} (${local_port}): endpoint nao disponivel"
    fi
done

# ============================================
# VERIFICAR ENDPOINTS /health
# ============================================
echo ""
log_info "=== Endpoints /health ==="

declare -A health_ports
health_ports["api"]=8000
health_ports["backend"]=3001
health_ports["web"]=3000

for service in "${!health_ports[@]}"; do
    local_port="${health_ports[$service]}"
    response=$(curl -sf "http://localhost:${local_port}/health" 2>/dev/null || echo "")
    if [[ -n "${response}" ]]; then
        log_ok "${service} (${local_port}): ${response}"
    else
        log_warn "${service} (${local_port}): nao respondeu"
    fi
done

# ============================================
# ULTIMO BOM DEPLOY
# ============================================
echo ""
if [[ -f "${PROJECT_DIR}/.last_good_sha" ]]; then
    log_info "Ultimo bom deploy: $(cat "${PROJECT_DIR}/.last_good_sha")"
fi

# ============================================
# RESULTADO
# ============================================
echo ""
log_info "============================================"

if [[ ${HAS_ERROR} -eq 1 ]]; then
    log_error "MISMATCH DETECTADO!"
    log_error "Execute rollback: ./deploy_compose.sh <SHA_ANTERIOR>"
    exit 1
else
    log_ok "TODOS OS CONTAINERS COM VERSAO CORRETA"
    exit 0
fi
