# IconsAI Scraping Hub

Plataforma de business intelligence para empresas, pessoas, noticias, politicos, grafo de relacionamentos e agentes de consulta.

## Estado Atual

O layout ativo do repositorio hoje e:

```text
iconsai-scraping/
├── apps/web/                    # Next.js 16 + React 19
├── api/                         # FastAPI (auth, admin, inteligencia)
├── backend/                     # Express (dados, busca, modulos)
├── services/pipeline-worker/    # jobs continuos + LISTEN/NOTIFY
├── scheduler/                   # coletor legacy com MCPs
├── config/                      # settings centralizados
├── database/                    # schema e migrations SQL
├── tests/                       # testes Python
└── docs/ARCHITECTURE_CURRENT.md # mapa atual do sistema
```

Arquitetura detalhada: `docs/ARCHITECTURE_CURRENT.md`

## Stack

| Componente | Tecnologia |
|------------|------------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind |
| API Python | FastAPI, Pydantic, Anthropic/OpenAI |
| Backend Node | Express 5, Supabase, Redis fallback |
| Background | APScheduler, asyncpg, Postgres LISTEN/NOTIFY |
| Banco | Supabase / PostgreSQL |

## Portas

### Desenvolvimento

- Web: `http://localhost:3002`
- Backend Node: `http://localhost:3006`
- API Python: `http://localhost:8000`

### Producao

- Web: `3000`
- Backend Node: `3001`
- API Python: `8000`
- Pipeline Worker: `8001`

## Fluxo de Roteamento

O browser acessa o Next app. O Next faz rewrites de `/api/*`:

- `/api/auth/*` -> FastAPI
- `/api/admin/*` -> FastAPI
- `/api/atlas/*` -> FastAPI
- `/api/stats/*` -> route handlers do Next que fazem proxy para o backend Node
- restante de `/api/*` -> backend Node

## Instalacao

```bash
cp .env.example .env

python3 -m pip install -r requirements.txt
npm install
npm --workspace=iconsai-scraping-backend install
npm --workspace=iconsai-scraping-web install
```

## Execucao Local

### Sem Docker

```bash
npm run dev
```

Ou via PM2:

```bash
npm run server
```

### Com Docker Compose

```bash
docker compose -f docker-compose.dev.yml up --build
```

## Variaveis Criticas

```bash
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
JWT_SECRET_KEY=
SERPER_API_KEY=
ANTHROPIC_API_KEY=
```

As demais integracoes estao descritas em `.env.example`.

## Verificacao Rapida

```bash
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:3006/health | jq .
curl -I http://localhost:3002
```

## Testes

```bash
python3 -m pytest tests/test_health.py -q
npm run verify:backend
npm --workspace=iconsai-scraping-web run lint
npm --workspace=iconsai-scraping-web run test:e2e
```

## Licenca

MIT
