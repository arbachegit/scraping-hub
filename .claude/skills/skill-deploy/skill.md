# Skill: Deploy do Scraping Hub

Skill para realizar deploy da aplicacao e documentar o processo de CI/CD.

## Arquitetura de Deploy

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐
│   GitHub Repo   │────▶│   GitHub Actions │────▶│   Digital Ocean Droplet     │
│   (main branch) │     │   (CI/CD)        │     │   (VPS + Services)          │
└─────────────────┘     └──────────────────┘     └─────────────────────────────┘
```

## Como Fazer Deploy

### Deploy Automatico (Recomendado)

O deploy e disparado **automaticamente** quando um commit e feito na branch `main`:

```bash
# 1. Fazer as alteracoes necessarias
# 2. Adicionar arquivos ao stage
git add <arquivos>

# 3. Criar commit
git commit -m "feat: descricao da alteracao"

# 4. Push para main (dispara deploy automatico)
git push origin main
```

### Verificar Status do Deploy

```bash
# Ver ultimos workflows executados
gh run list --limit 5

# Ver detalhes de um workflow especifico
gh run view <run-id>

# Ver logs de um workflow
gh run view <run-id> --log

# Monitorar deploy em tempo real
gh run watch
```

## Configuracao do GitHub Actions

### Workflow: `.github/workflows/deploy.yml`

### Secrets Necessarios no GitHub

Configurar em: **Settings > Secrets and variables > Actions**

| Secret | Descricao | Exemplo |
|--------|-----------|---------|
| `DO_HOST` | IP ou hostname do Droplet | `143.198.xxx.xxx` |
| `DO_USERNAME` | Usuario SSH | `root` ou `deploy` |
| `DO_SSH_KEY` | Chave privada SSH | `-----BEGIN OPENSSH...` |
| `CORESIGNAL_API_KEY` | API Key Coresignal | `cs_...` |
| `PROXYCURL_API_KEY` | API Key Proxycurl | `px_...` |
| `FIRECRAWL_API_KEY` | API Key Firecrawl | `fc_...` |
| `SUPABASE_URL` | URL do Supabase | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Chave de servico Supabase | `eyJhbG...` |

## Configuracao do Servidor (Digital Ocean)

### Estrutura de Diretorios

```
/opt/scraping-hub/
├── src/
│   ├── scrapers/
│   ├── services/
│   └── utils/
├── config/
├── venv/
├── .env
└── scraping-hub.service
```

### Systemd Service

```ini
[Unit]
Description=Scraping Hub Service
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/scraping-hub
Environment=PATH=/opt/scraping-hub/venv/bin
ExecStart=/opt/scraping-hub/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Comandos Systemd

```bash
# Status do service
sudo systemctl status scraping-hub

# Reiniciar service
sudo systemctl restart scraping-hub

# Ver logs
sudo journalctl -u scraping-hub -f
```

## SSL/HTTPS (Let's Encrypt)

```bash
# Renovar certificado
sudo certbot renew

# Verificar certificado
sudo certbot certificates
```

## Troubleshooting

### Deploy Falhou no GitHub Actions

```bash
# Ver logs do ultimo deploy
gh run view --log-failed

# Verificar testes locais
pytest
```

### Service Nao Responde

```bash
# SSH no servidor
ssh user@server

# Verificar status
sudo systemctl status scraping-hub

# Ver logs
sudo journalctl -u scraping-hub -n 50

# Reiniciar
sudo systemctl restart scraping-hub
```

## Checklist Pre-Deploy

- [ ] Todas as alteracoes commitadas
- [ ] Testes passando (`pytest`)
- [ ] Linting OK (`ruff check .`)
- [ ] Type checking OK (`mypy .`)
- [ ] Branch main atualizada
- [ ] Secrets do GitHub configurados
- [ ] Servidor Digital Ocean acessivel

## URLs do Projeto

| Ambiente | URL |
|----------|-----|
| **GitHub Actions** | https://github.com/arbachegit/scraping-hub/actions |
| **Digital Ocean** | https://cloud.digitalocean.com |
