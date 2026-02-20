# Runbook de Deploy - iconsai-scraping

## Comandos Rápidos

### Deploy de SHA Específico

```bash
# Via GitHub Actions (recomendado)
gh workflow run deploy.yml -f sha_override=<SHA_COMPLETO>

# Ou manualmente no servidor
ssh deploy@scraping.iconsai.ai "cd /opt/iconsai-scraping && ./scripts/deploy_compose.sh <SHA_COMPLETO>"
```

### Rollback para SHA Anterior

```bash
# No servidor
ssh deploy@scraping.iconsai.ai

# Ver SHA anterior
cat /opt/iconsai-scraping/.last_good_sha

# Executar rollback manual
cd /opt/iconsai-scraping
PREVIOUS_SHA=$(cat .last_good_sha)
./scripts/deploy_compose.sh ${PREVIOUS_SHA}
```

### Verificar Mismatch de Versão

```bash
# No servidor
./scripts/verify_runtime.sh

# Comparar com .env
cat /opt/iconsai-scraping/.env | grep GIT_SHA
```

### Ver Logs dos Serviços

```bash
# Logs de um serviço específico
docker logs iconsai-api --tail 100 -f
docker logs iconsai-backend --tail 100 -f

# Logs de todos os serviços
docker-compose -f docker-compose.prod.yml logs -f
```

### Status dos Serviços

```bash
docker-compose -f docker-compose.prod.yml ps
docker stats --no-stream
```

---

## Endpoints de Verificação

| Serviço | Health | Version |
|---------|--------|---------|
| API Python | http://localhost:8000/health | http://localhost:8000/version |
| Backend Node | http://localhost:3001/health | http://localhost:3001/version |

### Produção

- API: https://scraping.iconsai.ai/health
- Backend: https://scraping.iconsai.ai/api/health
