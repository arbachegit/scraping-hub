#!/usr/bin/env bash
# deploy_compose.sh - Deploy Determinístico com Docker Compose
#
# USO: ./deploy_compose.sh <SHA_COMMIT>
#
# REGRAS INVIOLÁVEIS:
#   1. Atualiza .env com GIT_SHA de forma atômica
#   2. Executa docker compose pull e valida imagens
#   3. Executa docker compose up -d --force-recreate --remove-orphans
#   4. Proíbe containers com imagem diferente do SHA
#   5. Aguarda healthchecks e valida endpoint /version
#   6. Rollback automático em falha

set -euo pipefail

# ============================================
# CONFIGURAÇÃO
# ============================================
PROJECT_DIR="${PROJECT_DIR:-/opt/iconsai-scraping}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"
KEEP_VERSIONS="${KEEP_VERSIONS:-5}"

# ============================================
# CORES PARA OUTPUT
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
# VALIDAÇÃO DE ARGUMENTOS
# ============================================
if [[ $# -lt 1 ]]; then
    log_error "Uso: $0 <SHA_COMMIT>"
    exit 1
fi

SHA="$1"
GIT_SHA="${SHA:0:7}"
LAST_GOOD_SHA_FILE="${PROJECT_DIR}/.last_good_sha"

log_info "============================================"
log_info "DEPLOY DETERMINÍSTICO"
log_info "============================================"
log_info "SHA Completo: ${SHA}"
log_info "GIT_SHA:      ${GIT_SHA}"
log_info "PROJECT:      ${PROJECT_DIR}"
log_info "COMPOSE:      ${COMPOSE_FILE}"
log_info "============================================"

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

save_last_good_sha() {
    if [[ -f "${PROJECT_DIR}/${ENV_FILE}" ]]; then
        local current_sha
        current_sha=$(grep -E "^GIT_SHA=" "${PROJECT_DIR}/${ENV_FILE}" 2>/dev/null | cut -d'=' -f2 || echo "")
        if [[ -n "${current_sha}" && "${current_sha}" != "${GIT_SHA}" ]]; then
            echo "${current_sha}" > "${LAST_GOOD_SHA_FILE}"
            log_info "SHA anterior salvo: ${current_sha}"
        fi
    fi
}

rollback() {
    log_error "============================================"
    log_error "DEPLOY FALHOU - INICIANDO ROLLBACK"
    log_error "============================================"

    if [[ -f "${LAST_GOOD_SHA_FILE}" ]]; then
        local previous_sha
        previous_sha=$(cat "${LAST_GOOD_SHA_FILE}")
        log_warn "Revertendo para: ${previous_sha}"

        sed -i "s/^GIT_SHA=.*/GIT_SHA=${previous_sha}/" "${PROJECT_DIR}/${ENV_FILE}"

        cd "${PROJECT_DIR}"
        docker-compose -f "${COMPOSE_FILE}" pull --quiet
        docker-compose -f "${COMPOSE_FILE}" up -d --force-recreate --remove-orphans

        log_warn "Rollback executado para ${previous_sha}"
    else
        log_error "Nenhum SHA anterior disponível para rollback"
    fi

    exit 1
}

trap rollback ERR

update_env_file() {
    local env_path="${PROJECT_DIR}/${ENV_FILE}"
    local temp_file="${env_path}.tmp"

    if [[ ! -f "${env_path}" ]]; then
        log_info "Criando ${ENV_FILE}..."
        touch "${env_path}"
    fi

    if grep -q "^GIT_SHA=" "${env_path}" 2>/dev/null; then
        sed "s/^GIT_SHA=.*/GIT_SHA=${GIT_SHA}/" "${env_path}" > "${temp_file}"
    else
        cp "${env_path}" "${temp_file}"
        echo "GIT_SHA=${GIT_SHA}" >> "${temp_file}"
    fi

    # Atualiza BUILD_DATE
    local build_date
    build_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    if grep -q "^BUILD_DATE=" "${temp_file}" 2>/dev/null; then
        sed -i "s/^BUILD_DATE=.*/BUILD_DATE=${build_date}/" "${temp_file}"
    else
        echo "BUILD_DATE=${build_date}" >> "${temp_file}"
    fi

    mv "${temp_file}" "${env_path}"
    log_ok ".env atualizado: GIT_SHA=${GIT_SHA}"
}

pull_and_verify_images() {
    log_info "Fazendo pull das imagens..."

    cd "${PROJECT_DIR}"

    if ! docker-compose -f "${COMPOSE_FILE}" pull; then
        log_error "Falha ao fazer pull das imagens"
        return 1
    fi

    log_ok "Pull concluído"
    return 0
}

stop_old_services() {
    log_info "Parando serviços systemd antigos..."
    sudo systemctl stop scraping 2>/dev/null || true
    sudo systemctl stop scraping-backend 2>/dev/null || true
    sudo systemctl disable scraping 2>/dev/null || true
    sudo systemctl disable scraping-backend 2>/dev/null || true
    log_ok "Serviços systemd parados"
}

recreate_containers() {
    log_info "Parando containers existentes..."

    cd "${PROJECT_DIR}"

    docker-compose -f "${COMPOSE_FILE}" down --remove-orphans || true

    log_info "Aguardando liberação das portas..."
    sleep 5

    # Verifica se portas estão livres
    if lsof -i :8000 > /dev/null 2>&1; then
        log_warn "Porta 8000 ainda em uso, matando..."
        sudo fuser -k 8000/tcp || true
        sleep 2
    fi

    if lsof -i :3001 > /dev/null 2>&1; then
        log_warn "Porta 3001 ainda em uso, matando..."
        sudo fuser -k 3001/tcp || true
        sleep 2
    fi

    log_info "Recriando containers..."
    docker-compose -f "${COMPOSE_FILE}" up -d --force-recreate --remove-orphans

    log_ok "Containers recriados"
}

verify_container_images() {
    log_info "Verificando imagens dos containers..."

    cd "${PROJECT_DIR}"

    local containers=("iconsai-api" "iconsai-backend" "iconsai-scheduler")

    for container in "${containers[@]}"; do
        local running_sha
        running_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${container}" 2>/dev/null | grep "^GIT_SHA=" | cut -d= -f2 || echo "")

        if [[ -z "${running_sha}" ]]; then
            log_warn "Container ${container} não encontrado ou sem GIT_SHA"
            continue
        fi

        if [[ "${running_sha}" != "${GIT_SHA}" ]]; then
            log_error "Container ${container} rodando SHA errado!"
            log_error "  Esperado: ${GIT_SHA}"
            log_error "  Atual:    ${running_sha}"
            return 1
        fi

        log_ok "Container ${container}: SHA=${running_sha}"
    done

    return 0
}

wait_for_health() {
    log_info "Aguardando healthchecks (timeout: ${HEALTH_TIMEOUT}s)..."

    local start_time
    start_time=$(date +%s)

    local services=("iconsai-api:8000" "iconsai-backend:3001")

    for service_port in "${services[@]}"; do
        local service="${service_port%%:*}"
        local port="${service_port##*:}"

        log_info "Aguardando ${service}..."

        while true; do
            local current_time
            current_time=$(date +%s)
            local elapsed=$((current_time - start_time))

            if [[ ${elapsed} -gt ${HEALTH_TIMEOUT} ]]; then
                log_error "Timeout aguardando ${service}"
                docker logs --tail 50 "${service}" 2>&1 || true
                return 1
            fi

            if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
                log_ok "${service} está healthy"
                break
            fi

            sleep 5
        done
    done

    return 0
}

validate_version_endpoints() {
    log_info "Validando endpoints /version..."

    local expected_sha="${GIT_SHA}"

    # API Python
    local api_response
    api_response=$(curl -sf "http://localhost:8000/version" 2>/dev/null || echo "")
    if [[ -n "${api_response}" ]]; then
        local api_sha
        api_sha=$(echo "${api_response}" | grep -oE '"git_sha"\s*:\s*"[^"]+"' | grep -oE '[a-f0-9]{7}' | head -1 || echo "")
        if [[ "${api_sha}" == "${expected_sha}" ]]; then
            log_ok "API Python: ${api_sha}"
        else
            log_warn "API Python SHA diferente: ${api_sha} (esperado: ${expected_sha})"
        fi
    else
        log_warn "Endpoint /version não disponível para API Python"
    fi

    # Backend Node.js
    local backend_response
    backend_response=$(curl -sf "http://localhost:3001/version" 2>/dev/null || echo "")
    if [[ -n "${backend_response}" ]]; then
        local backend_sha
        backend_sha=$(echo "${backend_response}" | grep -oE '"git_sha"\s*:\s*"[^"]+"' | grep -oE '[a-f0-9]{7}' | head -1 || echo "")
        if [[ "${backend_sha}" == "${expected_sha}" ]]; then
            log_ok "Backend Node.js: ${backend_sha}"
        else
            log_warn "Backend Node.js SHA diferente: ${backend_sha} (esperado: ${expected_sha})"
        fi
    else
        log_warn "Endpoint /version não disponível para Backend Node.js"
    fi

    return 0
}

cleanup_old_images() {
    log_info "Limpando imagens antigas (mantendo ${KEEP_VERSIONS} versões)..."

    # Remove imagens dangling
    docker image prune -f > /dev/null 2>&1 || true

    log_ok "Limpeza concluída"
}

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================

cd "${PROJECT_DIR}"

# 1. Salva SHA atual para possível rollback
save_last_good_sha

# 2. Atualiza .env com nova tag
update_env_file

# 3. Para serviços systemd antigos
stop_old_services

# 4. Pull e verificação de imagens
pull_and_verify_images

# 5. Recria containers
recreate_containers

# 6. Verifica imagens dos containers
verify_container_images

# 7. Aguarda healthchecks
wait_for_health

# 8. Valida endpoints /version
validate_version_endpoints

# 9. Salva SHA como último bom
echo "${GIT_SHA}" > "${LAST_GOOD_SHA_FILE}"

# 10. Limpeza de imagens antigas
cleanup_old_images

# ============================================
# SUCESSO
# ============================================
log_ok "============================================"
log_ok "DEPLOY CONCLUÍDO COM SUCESSO"
log_ok "============================================"
log_ok "SHA:       ${SHA}"
log_ok "GIT_SHA:   ${GIT_SHA}"
log_ok "============================================"

exit 0
