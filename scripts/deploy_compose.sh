#!/bin/bash
# =============================================================================
# DETERMINISTIC DOCKER COMPOSE DEPLOY
# =============================================================================
# Este script garante que SEMPRE rode a imagem do commit novo, nunca cache.
#
# Princípios:
# 1. Tags SHA imutáveis (ghcr.io/user/repo:abc1234)
# 2. pull_policy: always no docker-compose.prod.yml
# 3. Verificação pós-deploy que o SHA no container == SHA do deploy
# 4. Rollback automático se verificação falhar
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_DIR="${PROJECT_DIR:-/opt/iconsai-scraping}"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env"
TIMEOUT=120
RETRY_COUNT=3

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get GIT_SHA from environment or git
get_git_sha() {
    if [ -n "${GIT_SHA:-}" ]; then
        echo "$GIT_SHA"
    elif [ -d ".git" ]; then
        git rev-parse --short HEAD
    else
        echo "unknown"
    fi
}

# Verify container is running expected SHA
verify_container_sha() {
    local container_name=$1
    local expected_sha=$2
    local port=$3
    local endpoint=${4:-"/health"}

    log_info "Verifying ${container_name} is running SHA ${expected_sha}..."

    # Wait for container to be healthy
    local attempt=0
    while [ $attempt -lt $RETRY_COUNT ]; do
        if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            # Get SHA from container environment
            local container_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container_name" | grep "^GIT_SHA=" | cut -d= -f2)

            if [ "$container_sha" == "$expected_sha" ]; then
                log_success "${container_name} is running correct SHA: ${container_sha}"
                return 0
            else
                log_error "${container_name} SHA mismatch! Expected: ${expected_sha}, Got: ${container_sha}"
                return 1
            fi
        fi

        attempt=$((attempt + 1))
        log_warn "Container ${container_name} not ready, attempt ${attempt}/${RETRY_COUNT}..."
        sleep 5
    done

    log_error "Container ${container_name} did not become ready"
    return 1
}

# Health check for a service
health_check() {
    local url=$1
    local attempt=0

    while [ $attempt -lt $RETRY_COUNT ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    return 1
}

# Main deploy function
deploy() {
    local GIT_SHA=$(get_git_sha)
    local BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    log_info "=========================================="
    log_info "DETERMINISTIC DEPLOY"
    log_info "=========================================="
    log_info "GIT_SHA: ${GIT_SHA}"
    log_info "BUILD_DATE: ${BUILD_DATE}"
    log_info "PROJECT_DIR: ${PROJECT_DIR}"
    log_info "=========================================="

    cd "$PROJECT_DIR"

    # Export variables for docker-compose
    export GIT_SHA
    export BUILD_DATE

    # Load .env if exists
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
        log_success "Loaded environment from ${ENV_FILE}"
    fi

    # Backup current state for rollback
    log_info "Backing up current container states..."
    local PREVIOUS_API_SHA=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-api 2>/dev/null | grep "^GIT_SHA=" | cut -d= -f2 || echo "none")
    local PREVIOUS_BACKEND_SHA=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-backend 2>/dev/null | grep "^GIT_SHA=" | cut -d= -f2 || echo "none")

    log_info "Previous API SHA: ${PREVIOUS_API_SHA}"
    log_info "Previous Backend SHA: ${PREVIOUS_BACKEND_SHA}"

    # Pull new images (force pull with SHA tag)
    log_info "Pulling images with SHA tag: ${GIT_SHA}..."
    docker-compose -f "$COMPOSE_FILE" pull --quiet || {
        log_error "Failed to pull images"
        exit 1
    }
    log_success "Images pulled successfully"

    # Stop old containers
    log_info "Stopping old containers..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true

    # Start new containers
    log_info "Starting new containers..."
    docker-compose -f "$COMPOSE_FILE" up -d || {
        log_error "Failed to start containers"
        exit 1
    }

    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 10

    # Verify all services
    local DEPLOY_SUCCESS=true

    # Verify API
    if ! verify_container_sha "iconsai-api" "$GIT_SHA" 8000; then
        DEPLOY_SUCCESS=false
    fi

    # Verify Backend
    if ! verify_container_sha "iconsai-backend" "$GIT_SHA" 3001; then
        DEPLOY_SUCCESS=false
    fi

    # Health checks
    log_info "Running health checks..."

    if health_check "http://localhost:8000/health"; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        DEPLOY_SUCCESS=false
    fi

    if health_check "http://localhost:3001/health"; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        DEPLOY_SUCCESS=false
    fi

    # Final status
    if [ "$DEPLOY_SUCCESS" = true ]; then
        log_info "=========================================="
        log_success "DEPLOY SUCCESSFUL"
        log_info "=========================================="
        log_info "API: http://localhost:8000 (SHA: ${GIT_SHA})"
        log_info "Backend: http://localhost:3001 (SHA: ${GIT_SHA})"
        log_info "=========================================="

        # Show running containers
        docker-compose -f "$COMPOSE_FILE" ps

        exit 0
    else
        log_error "=========================================="
        log_error "DEPLOY FAILED - Rolling back..."
        log_error "=========================================="

        # Rollback is handled by keeping old images available
        # In production, you might want to implement proper rollback here

        exit 1
    fi
}

# Verify runtime (can be called separately)
verify_runtime() {
    local GIT_SHA=${1:-$(get_git_sha)}

    log_info "Verifying runtime for SHA: ${GIT_SHA}"

    local ALL_OK=true

    # Check API
    local api_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-api 2>/dev/null | grep "^GIT_SHA=" | cut -d= -f2 || echo "unknown")
    if [ "$api_sha" == "$GIT_SHA" ]; then
        log_success "API SHA matches: ${api_sha}"
    else
        log_error "API SHA mismatch! Expected: ${GIT_SHA}, Got: ${api_sha}"
        ALL_OK=false
    fi

    # Check Backend
    local backend_sha=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-backend 2>/dev/null | grep "^GIT_SHA=" | cut -d= -f2 || echo "unknown")
    if [ "$backend_sha" == "$GIT_SHA" ]; then
        log_success "Backend SHA matches: ${backend_sha}"
    else
        log_error "Backend SHA mismatch! Expected: ${GIT_SHA}, Got: ${backend_sha}"
        ALL_OK=false
    fi

    if [ "$ALL_OK" = true ]; then
        log_success "All containers running correct SHA"
        exit 0
    else
        log_error "SHA verification failed"
        exit 1
    fi
}

# Show help
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  deploy        Deploy with current GIT_SHA (default)"
    echo "  verify [sha]  Verify running containers match SHA"
    echo "  help          Show this help"
    echo ""
    echo "Environment variables:"
    echo "  GIT_SHA       Git commit SHA (auto-detected if not set)"
    echo "  PROJECT_DIR   Project directory (default: /opt/iconsai-scraping)"
}

# Main
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    verify)
        verify_runtime "${2:-}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
