# IconsAI Scraping Hub

Sistema de Business Intelligence Brasil com analise de empresas em 11 blocos tematicos, busca de pessoas e identificacao de concorrentes.

## Stack Tecnologico

| Componente | Tecnologia |
|------------|------------|
| **Backend Python** | FastAPI, Anthropic Claude, Pydantic |
| **Backend Node.js** | Express, Supabase |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind |
| **Banco de Dados** | Supabase (PostgreSQL) |
| **APIs Integradas** | Serper, Apollo, Perplexity, Tavily, BrasilAPI |

## Estrutura do Projeto

```
iconsai-scraping/
├── src/                          # Backend Python (analise avancada)
│   ├── scrapers/                 # Clientes de API
│   │   ├── apollo.py             # LinkedIn B2B
│   │   ├── brasil_api.py         # Dados CNPJ
│   │   ├── perplexity.py         # AI Research
│   │   ├── serper.py             # Google Search
│   │   └── tavily.py             # AI Search
│   ├── services/                 # Servicos de negocio
│   │   ├── company_analysis.py   # Analise 11 blocos
│   │   ├── ai_analyzer.py        # Claude AI
│   │   └── keyword_extractor.py  # Extracao de keywords
│   └── database/                 # Repositories
│       └── star_repository.py    # Star schema
├── backend/                      # Backend Node.js (API Gateway)
│   └── src/
│       ├── routes/               # Rotas Express
│       ├── services/             # Servicos
│       └── database/             # Supabase client
├── frontend/                     # Frontend Next.js
│   └── src/
│       ├── app/admin/            # Paginas admin
│       └── components/analysis/  # Componentes de analise
├── api/                          # FastAPI routes
├── config/                       # Configuracoes
├── database/                     # Migrations SQL
└── .env                          # Variaveis de ambiente
```

## Funcionalidades

### Analise de Empresas (11 Blocos)

1. **A Empresa** - Dados cadastrais, historia, mercado
2. **Pessoas da Empresa** - Colaboradores e executivos
3. **Formacao das Pessoas** - Background educacional
4. **Ativo Humano** - Competencias agregadas
5. **Capacidade do Ativo** - Capacidade de entrega
6. **Comunicacao vs Caracteristicas** - Alinhamento
7. **Fraquezas na Comunicacao** - Gaps identificados
8. **Visao do Leigo** - Perspectiva do publico geral
9. **Visao do Profissional** - Avaliacao tecnica
10. **Visao do Concorrente** - Analise competitiva
11. **Visao do Fornecedor** - Avaliacao como cliente

### Sintese Final

- **Hipotese de Objetivo** vs OKR sugerido
- **Concorrentes** com Stamps (Forte/Medio/Fraco)
- **SWOT Contemporaneo** com scoring e TOWS

## Instalacao

```bash
# Clonar repositorio
git clone https://github.com/iconsai/iconsai-scraping.git
cd iconsai-scraping

# Backend Python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Backend Node.js
cd backend && npm install

# Frontend
cd frontend && npm install

# Configurar variaveis
cp .env.example .env
# Editar .env com suas chaves
```

## Execucao Local

```bash
# Terminal 1 - Backend Python (porta 8000)
python -m uvicorn api.main:app --port 8000

# Terminal 2 - Backend Node.js (porta 3001)
cd backend && npm run dev

# Terminal 3 - Frontend (porta 3000)
cd frontend && npm run dev
```

## Variaveis de Ambiente

```bash
# APIs de Busca
SERPER_API_KEY=
PERPLEXITY_API_KEY=
TAVILY_API_KEY=

# APIs B2B
APOLLO_API_KEY=

# AI
ANTHROPIC_API_KEY=

# Banco de Dados
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Autenticacao
JWT_SECRET_KEY=
```

## Banco de Dados (Star Schema)

- `dim_empresas` - Dimensao de empresas
- `dim_pessoas` - Dimensao de pessoas
- `fato_analises_empresa` - Fato de analises
- `fato_concorrentes` - Fato de concorrentes
- `fato_eventos_pessoa` - Eventos de carreira

## API Endpoints

### Empresas
- `POST /api/v2/company/analyze-complete` - Analise completa
- `GET /api/v2/company/:id` - Buscar por ID
- `GET /api/v2/company/search?name=` - Buscar por nome

### Pessoas
- `POST /api/v2/people/search` - Buscar pessoas
- `GET /api/v2/people/empresa/:empresaId` - Listar por empresa

### Concorrentes
- `POST /api/v2/competitors/search` - Buscar concorrentes
- `GET /api/v2/competitors/empresa/:empresaId` - Listar por empresa

## Licenca

MIT License - IconsAI 2026
