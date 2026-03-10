# Arquitetura Atual

Documento de referencia do runtime real do repositorio em 2026-03-10.

## Visao Geral

O sistema e um monorepo com quatro componentes principais:

1. `apps/web`: frontend Next.js 16 + React 19.
2. `api`: API Python/FastAPI para auth, admin e inteligencia.
3. `backend`: API Node.js/Express para busca, dados e modulos operacionais.
4. `services/pipeline-worker` e `scheduler`: processos de background.

O dado persistente principal fica no Supabase/Postgres. Redis e opcional para cache/fallback. O sistema integra APIs externas como Serper, Perplexity, Apollo, BrasilAPI, CNPJa, Anthropic e OpenAI.

## Topologia de Runtime

### Desenvolvimento

- Web: `http://localhost:3002`
- Backend Node: `http://localhost:3006`
- API Python: `http://localhost:8000`

Entrada principal:

- `npm run dev` no root sobe web + backend + api.
- `docker compose -f docker-compose.dev.yml up --build` sobe a mesma topologia em containers.
- `npm run server` usa PM2 para a mesma topologia local.

### Producao

`docker-compose.prod.yml` define:

- `web` em `3000`
- `api` em `8000`
- `backend` em `3001`
- `redis` em `6379`
- `pipeline-worker` em `8001`
- `scheduler` sem porta publica

Deploy usa tags SHA imutaveis via `IMAGE_PREFIX` + `IMAGE_TAG`.

## Roteamento HTTP

O browser fala sempre com o Next app.

O Next faz o roteamento interno de `/api/*`:

- `/api/auth/*` -> FastAPI `/auth/*`
- `/api/admin/*` -> FastAPI `/admin/*`
- `/api/atlas/*` -> FastAPI `/atlas/*`
- `/api/stats/*` -> route handlers do Next que fazem proxy para o backend Node
- restante de `/api/*` -> backend Node

Isso significa que o frontend nao conhece diretamente os hosts internos em producao; o Next server e a borda de aplicacao.

## Responsabilidades por Servico

### Web (`apps/web`)

Responsavel por:

- login e fluxo de senha
- dashboard
- Atlas chat
- modais de empresas, pessoas, noticias, CNAE e regime
- grafo e DB model UI
- proxies de stats

Auth do frontend:

- access token + refresh token em `localStorage`
- cookie `has_session` apenas para middleware de redirecionamento rapido
- validacao real feita via `fetchWithAuth`

### API Python (`api`)

Responsavel por:

- login, refresh, verify, recover/reset password
- `/auth/me` e profile completion
- rotas `/admin`
- inteligencia LLM (`/api/intelligence/*`)
- CNAE lookup
- enrichment de pessoas
- health/version
- seed de super admin no startup
- cron de snapshot de stats no startup

Esse servico e a autoridade de emissao de JWT.

### Backend Node (`backend`)

Responsavel por:

- companies
- people
- news
- politicians
- geo
- atlas
- people-agent
- graph
- emendas
- stats
- db-model

Esse servico valida o JWT emitido pelo FastAPI e aplica permissao por modulo.

Exemplo de fluxo importante:

1. busca empresa
2. analise cardinalidade/refinamento
3. busca interna no Supabase
4. fallback/federacao com Serper e Perplexity
5. enrichment com BrasilAPI
6. ranking e evidence logging

### Pipeline Worker (`services/pipeline-worker`)

Responsavel por jobs continuos:

- coleta de noticias
- update de empresas stale
- deteccao de relacionamentos
- geracao de embeddings
- escuta de eventos Postgres via `LISTEN/NOTIFY`
- upload opcional para DigitalOcean Spaces

### Scheduler Legacy (`scheduler`)

Mantem um fluxo mais antigo de coleta com MCP servers:

- busca capitais
- busca empresas via Serper MCP
- enrichment BrasilAPI/Apollo/CNPJa
- persistencia no Supabase

Hoje existem os dois modelos no repositorio.

## Banco e Schemas

As migrations e schemas estao divididos entre:

- `database/`
- `backend/database/migrations/`

As entidades mais centrais observadas no codigo:

- `dim_empresas`
- `dim_pessoas`
- `raw_cnae`
- `stats_historico`
- tabelas de graph/relationship
- tabelas de auth (`users`, `refresh_tokens`, `audit_logs`)

## Permissoes e Roles

Permissoes de modulo atuais:

- `empresas`
- `pessoas`
- `politicos`
- `mandatos`
- `emendas`
- `noticias`

Roles:

- `superadmin`
- `admin`
- `user`

O frontend usa essas permissoes para esconder modulos e o backend usa as mesmas para autorizar rotas.

## Observacoes Operacionais

- O repositorio tinha drift entre documentacao antiga e runtime real.
- `docker-compose.dev.yml`, `ecosystem.config.js`, `scripts/dev-server.sh` e `README.md` foram alinhados ao layout atual (`apps/web`, backend em `3006`, web em `3002`).
- Os testes Python nao devem depender de `fastapi.testclient.TestClient` neste stack atual; foi introduzido um client compativel baseado em `httpx.ASGITransport`.
