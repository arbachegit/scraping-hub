# Scraping Intelligence Hub

Sistema de scraping inteligente utilizando Coresignal, Proxycurl e Firecrawl para coleta de dados de empresas, LinkedIn e governo.

## Servicos Integrados

| Servico | Uso | Documentacao |
|---------|-----|--------------|
| **Coresignal** | Dados de empresas e LinkedIn | https://coresignal.com/docs |
| **Proxycurl** | API LinkedIn (perfis, empresas) | https://nubela.co/proxycurl |
| **Firecrawl** | Web scraping estruturado | https://firecrawl.dev/docs |

## Estrutura do Projeto

```
scraping-hub/
├── .claude/skills/           # Skills Claude Code
│   ├── favicon-guide/
│   ├── logo-guide/
│   ├── skill-deploy/
│   ├── skill-design-audit/
│   └── skill-indicadores-fiscais/
├── src/
│   ├── scrapers/             # Scrapers especificos
│   │   ├── coresignal.py
│   │   ├── proxycurl.py
│   │   └── firecrawl.py
│   ├── services/             # Servicos de negocio
│   │   ├── empresa.py
│   │   ├── linkedin.py
│   │   └── governo.py
│   └── utils/                # Utilitarios
│       ├── cache.py
│       ├── rate_limiter.py
│       └── validators.py
├── config/                   # Configuracoes
│   ├── settings.py
│   └── providers.yaml
├── tests/                    # Testes
├── docs/                     # Documentacao
├── .env.example
├── requirements.txt
└── README.md
```

## Instalacao

```bash
# Clonar repositorio
git clone https://github.com/arbachegit/scraping-hub.git
cd scraping-hub

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com suas chaves de API
```

## Configuracao

### Variaveis de Ambiente

```bash
# API Keys
CORESIGNAL_API_KEY=your_coresignal_key
PROXYCURL_API_KEY=your_proxycurl_key
FIRECRAWL_API_KEY=your_firecrawl_key

# Supabase (armazenamento)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# Configuracoes
CACHE_TTL=3600
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

## Uso

### Coresignal - Dados de Empresas

```python
from src.scrapers.coresignal import CoresignalClient

client = CoresignalClient()

# Buscar empresa
empresa = client.search_company(
    name="Iconsai",
    country="Brazil"
)

# Buscar funcionarios
employees = client.get_company_employees(
    company_id=empresa['id'],
    limit=100
)
```

### Proxycurl - LinkedIn

```python
from src.scrapers.proxycurl import ProxycurlClient

client = ProxycurlClient()

# Buscar perfil LinkedIn
profile = client.get_person_profile(
    linkedin_url="https://linkedin.com/in/username"
)

# Buscar empresa LinkedIn
company = client.get_company_profile(
    linkedin_url="https://linkedin.com/company/iconsai"
)
```

### Firecrawl - Web Scraping

```python
from src.scrapers.firecrawl import FirecrawlClient

client = FirecrawlClient()

# Scrape de pagina
content = client.scrape_url(
    url="https://gov.br/dados",
    formats=["markdown", "html"]
)

# Crawl de site
pages = client.crawl_site(
    url="https://transparencia.gov.br",
    max_pages=100
)
```

## Casos de Uso

### 1. Enriquecimento de Empresas

```python
from src.services.empresa import EmpresaService

service = EmpresaService()

# Enriquecer dados de empresa
dados = service.enrich_company(
    cnpj="12.345.678/0001-90",
    sources=["coresignal", "proxycurl"]
)
```

### 2. Inteligencia de LinkedIn

```python
from src.services.linkedin import LinkedInService

service = LinkedInService()

# Analise de perfil
insights = service.analyze_profile(
    linkedin_url="https://linkedin.com/in/ceo-empresa"
)

# Mapeamento de organograma
org = service.map_company_org(
    company_linkedin="https://linkedin.com/company/empresa"
)
```

### 3. Dados de Governo

```python
from src.services.governo import GovernoService

service = GovernoService()

# Scrape de transparencia
dados = service.scrape_transparency_portal(
    uf="SP",
    tipo="licitacoes"
)
```

## Rate Limiting

O sistema possui controle automatico de rate limiting:

| Servico | Limite | Periodo |
|---------|--------|---------|
| Coresignal | 100 req | 60s |
| Proxycurl | 50 req | 60s |
| Firecrawl | 200 req | 60s |

## Cache

Estrategia de cache em 3 niveis:

1. **Memoria (LRU)**: Dados recentes em memoria
2. **Redis**: Cache distribuido (opcional)
3. **Supabase**: Persistencia permanente

## Deploy

Ver documentacao em `.claude/skills/skill-deploy/skill.md`

## Licenca

MIT License - Iconsai 2026
