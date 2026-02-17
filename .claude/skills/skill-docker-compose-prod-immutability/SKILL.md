# Skill: Docker Compose Prod Immutability (SHA Tags)

Auditor de producao Docker/Compose focado em imutabilidade e rastreabilidade.

## Camada

**Camada 8** - CI/CD e Supply Chain

## Quando Usar

- Deploy em producao com Docker
- Revisao de docker-compose
- Auditoria de CI/CD

## Regras Inviolaveis

1. **Sem Tags Mutaveis**: Proibido usar `:latest` ou tags mutaveis em producao:
   ```yaml
   # ERRADO
   image: myapp:latest
   image: myapp:dev

   # CORRETO
   image: ghcr.io/user/myapp:sha-abc1234
   ```

2. **Tag SHA Obrigatoria**: Imagens devem ser tagueadas com `sha-<GIT_SHA>`:
   ```yaml
   image: ghcr.io/org/app:sha-${GIT_SHA}
   ```

3. **Force Recreate**: Deploy deve forcar pull e recriar containers:
   ```bash
   docker-compose pull
   docker-compose up -d --force-recreate
   ```

4. **Healthcheck Obrigatorio**: Healthcheck obrigatorio em cada servico:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

5. **Labels de Rastreabilidade**: Labels devem carregar `git_sha` e `schema_version`:
   ```yaml
   labels:
     - "git_sha=${GIT_SHA}"
     - "schema_version=1.0.0"
     - "build_date=${BUILD_DATE}"
   ```

6. **Verificacao Pos-Deploy**: Deve existir verificacao que confirme o SHA via endpoint `/version`.

## Exemplo de Implementacao Correta

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  api:
    image: ghcr.io/org/myapp-api:sha-${GIT_SHA:?GIT_SHA is required}
    pull_policy: always
    restart: unless-stopped
    environment:
      - GIT_SHA=${GIT_SHA}
      - BUILD_DATE=${BUILD_DATE}
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    labels:
      - "git_sha=${GIT_SHA}"
      - "schema_version=1.0.0"
      - "build_date=${BUILD_DATE}"
      - "service=api"
    ports:
      - "8000:8000"

  backend:
    image: ghcr.io/org/myapp-backend:sha-${GIT_SHA:?GIT_SHA is required}
    pull_policy: always
    restart: unless-stopped
    environment:
      - GIT_SHA=${GIT_SHA}
      - BUILD_DATE=${BUILD_DATE}
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    labels:
      - "git_sha=${GIT_SHA}"
      - "schema_version=1.0.0"
    depends_on:
      api:
        condition: service_healthy
```

```dockerfile
# Dockerfile
FROM node:20-slim

ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

ENV GIT_SHA=${GIT_SHA}
ENV BUILD_DATE=${BUILD_DATE}

LABEL git_sha=${GIT_SHA}
LABEL build_date=${BUILD_DATE}
LABEL maintainer="team@example.com"

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["node", "src/index.js"]
```

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  GIT_SHA: ${{ github.sha }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and push
        run: |
          docker build \
            --build-arg GIT_SHA=${{ github.sha }} \
            --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
            -t ${{ env.REGISTRY }}/org/myapp:sha-${{ github.sha }} \
            .
          docker push ${{ env.REGISTRY }}/org/myapp:sha-${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        run: |
          ssh user@server << 'EOF'
            cd /opt/app
            export GIT_SHA=${{ github.sha }}
            export BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d --force-recreate

            # Aguarda healthcheck
            sleep 30

            # Verifica SHA
            DEPLOYED_SHA=$(curl -s http://localhost:8000/version | jq -r .git_sha)
            if [ "$DEPLOYED_SHA" != "${{ github.sha }}" ]; then
              echo "SHA mismatch! Expected ${{ github.sha }}, got $DEPLOYED_SHA"
              exit 1
            fi

            echo "Deploy verificado: $DEPLOYED_SHA"
          EOF
```

```typescript
// Endpoint /version
app.get('/version', (req, res) => {
  res.json({
    version: process.env.npm_package_version || '1.0.0',
    git_sha: process.env.GIT_SHA || 'unknown',
    build_date: process.env.BUILD_DATE || 'unknown',
    service: 'myapp-api'
  });
});

// Endpoint /health
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    git_sha: process.env.GIT_SHA || 'unknown',
    uptime: process.uptime()
  });
});
```

## Checklist de Auditoria

- [ ] Nenhuma imagem usa `:latest` ou tag mutavel
- [ ] Todas as imagens usam tag `sha-<GIT_SHA>`
- [ ] `pull_policy: always` configurado
- [ ] `--force-recreate` no deploy
- [ ] Healthcheck em todos os servicos
- [ ] Labels com `git_sha` e `schema_version`
- [ ] Endpoint `/version` expoe SHA
- [ ] Endpoint `/health` para healthcheck
- [ ] Verificacao pos-deploy do SHA
- [ ] Rollback automatico se verificacao falhar

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
