# Skill: Deterministic Docker Deploy

CI/CD deterministic para deploy em DigitalOcean Droplet usando Docker/Compose com tags SHA imutaveis.

## Problema Resolvido

Garantir que SEMPRE rode a imagem do commit novo, nunca uma imagem antiga cacheada.

## Principios

1. **Tags SHA Imutaveis**: Cada build gera tag `ghcr.io/user/repo:abc1234`
2. **pull_policy: always**: docker-compose.prod.yml forca pull a cada deploy
3. **Verificacao Pos-Deploy**: Script verifica que SHA no container == SHA do deploy
4. **Rollback Automatico**: Se verificacao falhar, rollback para versao anterior

## Arquivos do Sistema

### 1. Dockerfiles

- `Dockerfile` - Python API (FastAPI)
- `backend/Dockerfile` - Node.js Backend (Express)
- `scheduler/Dockerfile` - Scheduler (Python)

Todos recebem build args:
```dockerfile
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_DATE=${BUILD_DATE}
```

### 2. docker-compose.prod.yml

```yaml
services:
  api:
    image: ghcr.io/arbachegit/iconsai-scraping-api:${GIT_SHA:-latest}
    pull_policy: always
    environment:
      - GIT_SHA=${GIT_SHA}
      - BUILD_DATE=${BUILD_DATE}
```

### 3. Workflow (.github/workflows/deploy.yml)

Jobs:
1. **test**: Roda pytest, ruff
2. **build**: Build e push para GHCR com tag SHA
3. **deploy**: SSH no servidor, docker-compose pull/up

### 4. Scripts

- `scripts/deploy_compose.sh deploy` - Deploy com verificacao
- `scripts/deploy_compose.sh verify [sha]` - Verifica SHA nos containers

## Endpoints de Verificacao

Todos os servicos expoe:

### /health
```json
{
  "status": "healthy",
  "git_sha": "abc1234",
  "build_date": "2026-02-17T10:00:00Z"
}
```

### /version
```json
{
  "version": "1.81.2026",
  "git_sha": "abc1234",
  "build_date": "2026-02-17T10:00:00Z",
  "service": "iconsai-scraping-api"
}
```

## Workflow de Deploy

```
1. Push para main
   |
2. GitHub Actions: test -> build -> deploy
   |
3. Build images com tag SHA (ghcr.io/user/repo:abc1234)
   |
4. Push para GHCR
   |
5. SSH no servidor
   |
6. docker-compose pull (forca download da tag SHA)
   |
7. docker-compose up -d
   |
8. Verifica SHA nos containers == SHA do deploy
   |
9. Health check nos endpoints
   |
10. Se falhar -> rollback
```

## Verificacao Manual

```bash
# No servidor
./scripts/deploy_compose.sh verify abc1234

# Ou manualmente
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-api | grep GIT_SHA

# Via API
curl -s https://scraping.iconsai.ai/version | jq .git_sha
curl -s https://scraping.iconsai.ai/api/version | jq .git_sha
```

## Secrets Necessarios (GitHub)

- `DO_HOST` - IP do servidor
- `DO_USERNAME` - Usuario SSH
- `DO_SSH_KEY` - Chave SSH privada
- `GITHUB_TOKEN` - Auto (para GHCR)
- `APOLLO_API_KEY`
- `CNPJA_API_KEY`
- `PERPLEXITY_API_KEY`
- `SERPER_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`
- `BRASIL_DATA_HUB_URL`
- `BRASIL_DATA_HUB_KEY`

## Migracao de systemd para Docker

O workflow automaticamente:
1. Para servicos systemd (scraping, scraping-backend)
2. Desabilita servicos systemd
3. Inicia containers Docker

Apos primeiro deploy bem-sucedido, projeto roda 100% em Docker.
