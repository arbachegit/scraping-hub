# Runbook de Producao — iconsai-scraping

## Arquitetura

```
scraping.iconsai.ai (Nginx + SSL)
    ├── /          → iconsai-web (Next.js, port 3000)
    ├── /api/auth/ → iconsai-api (FastAPI, port 8000)
    ├── /api/admin/→ iconsai-api (FastAPI, port 8000)
    ├── /api/atlas/→ iconsai-api (FastAPI, port 8000)
    ├── /api/stats/→ iconsai-api (FastAPI, port 8000)
    ├── /api/      → iconsai-backend (Express, port 3001)
    └── scheduler  → iconsai-scheduler (Python, sem porta)
```

**Server:** DigitalOcean Droplet
**Diretorio:** `/opt/iconsai-scraping`
**Registry:** `ghcr.io/arbachegit/iconsai-scraping-{web,api,backend,scheduler}`
**Tags:** `sha-<12chars>` (imutaveis, NUNCA usar `latest`)

---

## Comandos Rapidos

### Deploy de SHA Especifico

```bash
# Via GitHub Actions (recomendado)
gh workflow run deploy.yml -f sha_override=<SHA_COMPLETO>

# Manualmente no servidor
ssh root@<DROPLET_IP> "cd /opt/iconsai-scraping && ./deploy_compose.sh <SHA_12CHARS>"
```

### Rollback para SHA Anterior

```bash
ssh root@<DROPLET_IP>

# Ver SHA anterior (salvo automaticamente)
cat /opt/iconsai-scraping/.last_good_sha

# Executar rollback
cd /opt/iconsai-scraping
PREVIOUS_SHA=$(cat .last_good_sha | sed 's/sha-//')
./deploy_compose.sh ${PREVIOUS_SHA}
```

### Verificar Versao em Producao

```bash
# No servidor
ssh root@<DROPLET_IP> "cd /opt/iconsai-scraping && ./verify_runtime.sh"

# Externamente
curl -s https://scraping.iconsai.ai/version | jq .
curl -s https://scraping.iconsai.ai/health | jq .

# Verificar cada container
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-api | grep GIT_SHA
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-backend | grep GIT_SHA
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' iconsai-web | grep GIT_SHA

# Comparar com .env
cat /opt/iconsai-scraping/.env | grep IMAGE_TAG
```

---

## Logs

```bash
# Logs de um servico
docker logs iconsai-api --tail 100 -f
docker logs iconsai-backend --tail 100 -f
docker logs iconsai-web --tail 100 -f
docker logs iconsai-scheduler --tail 100 -f

# Todos os servicos
docker compose -f /opt/iconsai-scraping/docker-compose.prod.yml logs -f

# Filtrar erros
docker compose -f /opt/iconsai-scraping/docker-compose.prod.yml logs -f 2>&1 | grep -iE "error|traceback|exception"
```

---

## Restart de Servicos

```bash
# Reiniciar um servico
docker compose -f /opt/iconsai-scraping/docker-compose.prod.yml restart api

# Reiniciar todos
docker compose -f /opt/iconsai-scraping/docker-compose.prod.yml restart

# Force recreate (pull + recreate)
cd /opt/iconsai-scraping
docker compose -f docker-compose.prod.yml up -d --force-recreate --pull always
```

---

## Status

```bash
# Ver status de todos os containers
docker compose -f /opt/iconsai-scraping/docker-compose.prod.yml ps

# Health status
docker inspect --format='{{.Name}} {{.State.Health.Status}}' $(docker ps -q) 2>/dev/null

# Recursos (CPU/Memoria)
docker stats --no-stream

# Espaco em disco
df -h /
docker system df
```

---

## Limpeza

```bash
# Remover imagens antigas (>7 dias, nao em uso)
docker image prune -af --filter "until=168h"

# Remover volumes orfaos
docker volume prune -f

# Limpeza completa (CUIDADO)
docker system prune -a --volumes
```

---

## Troubleshooting

### Container nao sobe

1. Verificar logs: `docker logs iconsai-api --tail 50`
2. Verificar imagem: `docker images | grep iconsai`
3. Verificar .env: `cat /opt/iconsai-scraping/.env | grep IMAGE_TAG`
4. Verificar compose: `docker compose -f docker-compose.prod.yml config`
5. Verificar disco: `df -h /`

### Versao errada em producao

1. Verificar: `./verify_runtime.sh`
2. Comparar com GitHub: `gh run list --limit 5`
3. Forcar redeploy: `./deploy_compose.sh <SHA_CORRETO>`

### Health check falhando

1. Verificar endpoint: `curl -v http://localhost:8000/health`
2. Ver logs: `docker logs iconsai-api --tail 30`
3. Entrar no container: `docker exec -it iconsai-api bash`

### Portas em uso

```bash
ss -tulnp | grep -E ":(8000|3001|3000) "
# Se necessario forcar liberacao:
fuser -k 8000/tcp
fuser -k 3001/tcp
```

### Nginx nao funciona

```bash
sudo nginx -t           # Testar config
sudo systemctl status nginx
sudo tail -20 /var/log/nginx/error.log
sudo systemctl reload nginx
```

### Disco cheio

```bash
df -h /
docker system df
docker image prune -af --filter "until=48h"
docker system prune -a --volumes
journalctl --vacuum-size=100M  # Limpar logs do systemd
```

---

## Secrets (GitHub Actions)

| Secret | Descricao |
|--------|-----------|
| `DO_HOST` | IP do Droplet |
| `DO_USERNAME` | Usuario SSH |
| `DO_SSH_KEY` | Chave privada SSH |
| `GHCR_PAT` | Token GHCR (read:packages) |
| `SUPABASE_URL` | URL do Supabase |
| `SUPABASE_KEY` | Anon key |
| `SUPABASE_SERVICE_KEY` | Service role key |
| `SERPER_API_KEY` | Google Search API |
| `PERPLEXITY_API_KEY` | Perplexity AI |
| `APOLLO_API_KEY` | Apollo enrichment |
| `CNPJA_API_KEY` | CNPJa fiscal |
| `BRASIL_DATA_HUB_URL` | Brasil Data Hub URL |
| `BRASIL_DATA_HUB_KEY` | Brasil Data Hub key |
| `JWT_SECRET_KEY` | JWT signing key |
| `ANTHROPIC_API_KEY` | Claude API |
| `FIELD_ENCRYPTION_KEY` | AES-256 encryption |
| `SEED_ADMIN_EMAIL` | Admin seed email |
| `SEED_ADMIN_PASSWORD` | Admin seed password |
| `SMTP_HOST` | SMTP server |
| `SMTP_PORT` | SMTP port |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `EMAIL_FROM` | Sender email |

---

## Setup Inicial (novo servidor)

```bash
# 1. No GitHub - Configurar Secrets
gh secret set DO_HOST --body "<IP>"
gh secret set DO_USERNAME --body "root"
gh secret set DO_SSH_KEY < ~/.ssh/id_ed25519

# 2. No servidor - Preparar estrutura
ssh root@<IP> "mkdir -p /opt/iconsai-scraping"

# 3. No servidor - Docker (se necessario)
ssh root@<IP> "curl -fsSL https://get.docker.com | sh"

# 4. No servidor - Login GHCR
ssh root@<IP> "echo <GHCR_PAT> | docker login ghcr.io -u arbachegit --password-stdin"

# 5. Disparar primeiro deploy
gh workflow run deploy.yml
```
