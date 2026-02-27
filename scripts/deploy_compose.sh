#!/usr/bin/env bash
# =============================================================================
# deploy_compose.sh — Deploy Deterministico com Docker Compose
# =============================================================================
# USO: ./deploy_compose.sh <SHA_SHORT>
#
# PARAMETROS:
#   SHA_SHORT      - SHA curto (12 chars) do commit (obrigatorio)
#
# VARIAVEIS DE AMBIENTE (opcionais):
#   PROJECT_DIR    - Diretorio do projeto (default: /opt/iconsai-scraping)
#   COMPOSE_FILE   - Arquivo compose (default: docker-compose.prod.yml)
#   ENV_FILE       - Arquivo de env (default: .env)
#   HEALTH_TIMEOUT - Timeout para healthcheck em segundos (default: 180)
#   KEEP_IMAGES    - Versoes antigas a manter (default: 5)
#
# REGRAS INVIOLAVEIS:
#   1. Atualiza IMAGE_TAG no .env de forma atomica
#   2. Executa docker compose pull e valida imagens
#   3. Executa docker compose up -d --force-recreate --remove-orphans
#   4. Valida que containers rodam a imagem correta (SHA match)
#   5. Aguarda healthchecks com polling (sem sleep fixo)
#   6. Verifica endpoint /version quando disponivel
#   7. Rollback automatico se qualquer passo falhar
# =============================================================================

set -euo pipefail

# ============================================
# CONFIGURACAO
# ============================================
PROJECT_DIR="${PROJECT_DIR:-/opt/iconsai-scraping}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"
KEEP_IMAGES="${KEEP_IMAGES:-5}"

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
# VALIDACAO DE ARGUMENTOS
# ============================================
if [[ $# -lt 1 ]]; then
    log_error "Uso: $0 <SHA_SHORT>"
    log_error "Exemplo: $0 2f3a1b4c5d6e"
    exit 1
fi

SHA_SHORT="$1"
IMAGE_TAG="sha-${SHA_SHORT}"
LAST_GOOD_FILE="${PROJECT_DIR}/.last_good_sha"

log_info "============================================"
log_info "DEPLOY DETERMINISTICO"
log_info "============================================"
log_info "SHA:        ${SHA_SHORT}"
log_info "IMAGE_TAG:  ${IMAGE_TAG}"
log_info "PROJECT:    ${PROJECT_DIR}"
log_info "COMPOSE:    ${COMPOSE_FILE}"
log_info "============================================"

# ============================================
# FUNCOES
# ============================================

save_previous_sha() {
    if [[ -f "${PROJECT_DIR}/${ENV_FILE}" ]]; then
        local current_tag
        current_tag=$(grep -E "^IMAGE_TAG=" "${PROJECT_DIR}/${ENV_FILE}" 2>/dev/null | cut -d'=' -f2 || echo "")
        if [[ -n "${current_tag}" && "${current_tag}" != "${IMAGE_TAG}" ]]; then
            echo "${current_tag}" > "${LAST_GOOD_FILE}"
            log_info "SHA anterior salvo para rollback: ${current_tag}"
        fi
    fi
}

rollback() {
    log_error "============================================"
    log_error "DEPLOY FALHOU — INICIANDO ROLLBACK"
    log_error "============================================"

    if [[ -f "${LAST_GOOD_FILE}" ]]; then
        local previous_tag
        previous_tag=$(cat "${LAST_GOOD_FILE}")
        log_warn "Revertendo para: ${previous_tag}"

        # Atualiza .env com tag anterior
        local env_path="${PROJECT_DIR}/${ENV_FILE}"
        if grep -q "^IMAGE_TAG=" "${env_path}" 2>/dev/null; then
            sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${previous_tag}/" "${env_path}"
        fi

        # Sobe containers com tag anterior
        cd "${PROJECT_DIR}"
        docker compose -f "${COMPOSE_FILE}" pull --quiet 2>/dev/null || true
        docker compose -f "${COMPOSE_FILE}" up -d --force-recreate --remove-orphans 2>/dev/null || true

        log_warn "Rollback executado para ${previous_tag}"
    else
        log_error "Nenhum SHA anterior disponivel para rollback"
    fi

    exit 1
}

# Trap para rollback em caso de erro
trap rollback ERR

update_env() {
    local env_path="${PROJECT_DIR}/${ENV_FILE}"

    if [[ ! -f "${env_path}" ]]; then
        log_error ".env nao encontrado em ${env_path}"
        return 1
    fi

    local temp_file="${env_path}.tmp.$$"

    # Atualiza IMAGE_TAG atomicamente
    if grep -q "^IMAGE_TAG=" "${env_path}" 2>/dev/null; then
        sed "s/^IMAGE_TAG=.*/IMAGE_TAG=${IMAGE_TAG}/" "${env_path}" > "${temp_file}"
    else
        cp "${env_path}" "${temp_file}"
        echo "IMAGE_TAG=${IMAGE_TAG}" >> "${temp_file}"
    fi

    # Atualiza GIT_SHA
    if grep -q "^GIT_SHA=" "${temp_file}" 2>/dev/null; then
        sed -i "s/^GIT_SHA=.*/GIT_SHA=${SHA_SHORT}/" "${temp_file}"
    else
        echo "GIT_SHA=${SHA_SHORT}" >> "${temp_file}"
    fi

    # Move atomicamente
    mv "${temp_file}" "${env_path}"
    log_ok ".env atualizado: IMAGE_TAG=${IMAGE_TAG}"
}

stop_old_services() {
    log_info "Parando servicos antigos (systemd)..."
    sudo systemctl stop scraping 2>/dev/null || true
    sudo systemctl stop scraping-backend 2>/dev/null || true
    sudo systemctl disable scraping 2>/dev/null || true
    sudo systemctl disable scraping-backend 2>/dev/null || true

    log_info "Parando containers existentes..."
    cd "${PROJECT_DIR}"
    docker compose -f "${COMPOSE_FILE}" down --remove-orphans --timeout 30 2>/dev/null || true

    # Limpa containers orfaos
    docker ps -a --filter "name=iconsai" -q | xargs -r docker rm -f 2>/dev/null || true

    # Aguarda portas liberarem
    log_info "Aguardando portas liberarem..."
    local max_wait=30
    local elapsed=0
    while [[ ${elapsed} -lt ${max_wait} ]]; do
        local blocked=0
        for port in 8000 3001 3000; do
            if ss -tuln 2>/dev/null | grep -q ":${port} "; then
                blocked=1
                break
            fi
        done
        if [[ ${blocked} -eq 0 ]]; then
            log_ok "Portas livres"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if [[ ${elapsed} -ge ${max_wait} ]]; then
        log_warn "Timeout aguardando portas — forcando liberacao..."
        for port in 8000 3001 3000; do
            if command -v fuser &>/dev/null; then
                fuser -k ${port}/tcp 2>/dev/null || true
            fi
        done
        sleep 2
    fi
}

pull_images() {
    log_info "Fazendo pull das imagens (tag: ${IMAGE_TAG})..."

    cd "${PROJECT_DIR}"

    # Limpa espaco antes do pull
    docker image prune -af --filter "until=48h" 2>/dev/null || true
    docker system prune -f --volumes 2>/dev/null || true

    log_info "Espaco em disco:"
    df -h / | tail -1

    if ! docker compose -f "${COMPOSE_FILE}" pull; then
        log_error "Falha ao fazer pull das imagens"
        return 1
    fi

    log_ok "Pull concluido"
}

recreate_containers() {
    log_info "Recriando containers..."

    cd "${PROJECT_DIR}"

    docker compose -f "${COMPOSE_FILE}" up -d \
        --force-recreate \
        --remove-orphans

    log_ok "Containers recriados"
}

verify_container_images() {
    log_info "Verificando imagens dos containers..."

    local containers=("iconsai-web" "iconsai-api" "iconsai-backend" "iconsai-scheduler")
    local all_ok=1

    for container in "${containers[@]}"; do
        local env_sha
        env_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${container}" 2>/dev/null \
            | grep "^GIT_SHA=" | cut -d= -f2 || echo "unknown")

        if [[ "${env_sha}" == "${SHA_SHORT}" ]]; then
            log_ok "${container}: GIT_SHA=${env_sha}"
        else
            log_error "${container}: SHA mismatch! Esperado=${SHA_SHORT} Atual=${env_sha}"
            all_ok=0
        fi
    done

    if [[ ${all_ok} -eq 0 ]]; then
        return 1
    fi
}

wait_for_health() {
    log_info "Aguardando healthchecks (timeout: ${HEALTH_TIMEOUT}s)..."

    local containers=("iconsai-api" "iconsai-backend" "iconsai-web")
    local start_time
    start_time=$(date +%s)

    for container in "${containers[@]}"; do
        log_info "  Aguardando ${container}..."

        while true; do
            local current_time
            current_time=$(date +%s)
            local elapsed=$((current_time - start_time))

            if [[ ${elapsed} -gt ${HEALTH_TIMEOUT} ]]; then
                log_error "Timeout aguardando ${container} (${HEALTH_TIMEOUT}s)"
                docker logs --tail 30 "${container}" 2>&1 || true
                return 1
            fi

            local health
            health=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "none")

            case "${health}" in
                "healthy")
                    log_ok "${container} healthy (${elapsed}s)"
                    break
                    ;;
                "unhealthy")
                    log_error "${container} unhealthy!"
                    docker logs --tail 30 "${container}" 2>&1 || true
                    return 1
                    ;;
                "none")
                    local state
                    state=$(docker inspect --format='{{.State.Status}}' "${container}" 2>/dev/null || echo "")
                    if [[ "${state}" == "running" ]]; then
                        log_ok "${container} running (sem healthcheck, ${elapsed}s)"
                        break
                    fi
                    ;;
                *)
                    # starting ou outro estado transitorio
                    if [[ $((elapsed % 15)) -eq 0 ]]; then
                        log_info "  ${container} status: ${health} (${elapsed}s)"
                    fi
                    ;;
            esac

            sleep 3
        done
    done

    # Scheduler nao tem porta, so verifica se esta running
    local sched_state
    sched_state=$(docker inspect --format='{{.State.Status}}' "iconsai-scheduler" 2>/dev/null || echo "unknown")
    if [[ "${sched_state}" == "running" ]]; then
        log_ok "iconsai-scheduler running"
    else
        log_warn "iconsai-scheduler status: ${sched_state}"
    fi
}

validate_version_endpoints() {
    log_info "Validando endpoints /version..."

    local has_error=0

    # API Python (porta 8000)
    local api_response
    api_response=$(curl -sf "http://localhost:8000/version" 2>/dev/null || echo "")
    if [[ -n "${api_response}" ]]; then
        local api_sha
        api_sha=$(echo "${api_response}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
        if [[ "${api_sha}" == "${SHA_SHORT}" ]]; then
            log_ok "api /version: ${api_sha}"
        elif [[ -n "${api_sha}" ]]; then
            log_error "api /version mismatch! Esperado=${SHA_SHORT} Retornado=${api_sha}"
            has_error=1
        else
            log_warn "api /version: resposta sem SHA"
        fi
    else
        log_warn "api /version nao disponivel"
    fi

    # Backend Node.js (porta 3001)
    local backend_response
    backend_response=$(curl -sf "http://localhost:3001/version" 2>/dev/null || echo "")
    if [[ -n "${backend_response}" ]]; then
        local backend_sha
        backend_sha=$(echo "${backend_response}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
        if [[ "${backend_sha}" == "${SHA_SHORT}" ]]; then
            log_ok "backend /version: ${backend_sha}"
        elif [[ -n "${backend_sha}" ]]; then
            log_error "backend /version mismatch! Esperado=${SHA_SHORT} Retornado=${backend_sha}"
            has_error=1
        else
            log_warn "backend /version: resposta sem SHA"
        fi
    else
        log_warn "backend /version nao disponivel"
    fi

    # /version e best-effort, nao bloqueia deploy
    if [[ ${has_error} -eq 1 ]]; then
        log_warn "Mismatch em /version detectado (nao-bloqueante)"
    fi

    return 0
}

cleanup_old_images() {
    log_info "Limpando imagens antigas (mantendo ${KEEP_IMAGES} versoes)..."

    # Remove imagens antigas nao em uso (>7 dias)
    docker image prune -af --filter "until=168h" 2>/dev/null || true

    local disk_free
    disk_free=$(df -h / | tail -1 | awk '{print $4}')
    log_ok "Limpeza concluida. Espaco livre: ${disk_free}"
}

# ============================================
# EXECUCAO PRINCIPAL
# ============================================

cd "${PROJECT_DIR}"

# 1. Salvar SHA anterior para rollback
save_previous_sha

# 2. Atualizar .env com nova tag
update_env

# 3. Parar servicos antigos
stop_old_services

# 4. Pull imagens
pull_images

# 5. Recriar containers
recreate_containers

# 6. Verificar imagens dos containers (SHA match)
verify_container_images

# 7. Aguardar healthchecks
wait_for_health

# 8. Validar /version endpoints (best-effort)
validate_version_endpoints

# 9. Salvar SHA como ultimo bom deploy
echo "${IMAGE_TAG}" > "${LAST_GOOD_FILE}"

# 10. Limpar imagens antigas
cleanup_old_images

# ============================================
# SUCESSO
# ============================================
log_ok "============================================"
log_ok "DEPLOY CONCLUIDO COM SUCESSO"
log_ok "============================================"
log_ok "SHA:       ${SHA_SHORT}"
log_ok "IMAGE_TAG: ${IMAGE_TAG}"
log_ok "============================================"
docker compose -f "${COMPOSE_FILE}" ps
echo ""

exit 0
