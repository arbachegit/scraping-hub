# IconsAI MCP Servers

Model Context Protocol (MCP) servers para acesso padronizado a fontes de dados.

## Visão Geral

Os MCP servers permitem que agentes de IA acessem fontes de dados externas de forma padronizada. Cada server expõe "tools" que podem ser invocadas pelos agentes.

## Servers Disponíveis

| Server | Fonte | Tools | Autenticação |
|--------|-------|-------|--------------|
| **brasil-data-hub-mcp** | Supabase externo | get_capitais, get_municipio, get_municipios_por_uf | Service key |
| **serper-mcp** | Google Search | search_company, find_cnpj, find_linkedin, find_website, search_news | API key |
| **brasilapi-mcp** | Receita Federal | get_company, get_cep, list_banks | Não requer |
| **apollo-mcp** | Apollo.io | search_company, enrich_person, get_executives, search_brazil_companies | API key |
| **cnpja-mcp** | CNPJá | get_regime_tributario, get_company_details | API key |
| **perplexity-mcp** | Perplexity AI | research_company, analyze_market, find_competitors, search_ai | API key |

## Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com as API keys necessárias
```

## Configuração

### Brasil Data Hub (geo_municipios)

```env
BRASIL_DATA_HUB_URL=https://mnfjkegtynjtgesfphge.supabase.co
BRASIL_DATA_HUB_KEY=your_service_role_key
```

### Outras APIs

```env
SERPER_API_KEY=your_serper_key
APOLLO_API_KEY=your_apollo_key
CNPJA_API_KEY=your_cnpja_key
PERPLEXITY_API_KEY=your_perplexity_key
```

## Uso

### Via stdio (padrão MCP)

```bash
# Iniciar server
python -m mcp_servers.serper_mcp.server
```

### Via código Python

```python
from mcp_servers.serper_mcp import SerperMCPServer

server = SerperMCPServer()

# Listar tools
tools = server.get_tools()

# Chamar tool
result = await server.handle_tool("search_company", {
    "company_name": "Nubank",
    "cidade": "São Paulo"
})
```

### Exemplo: Buscar capitais brasileiras

```python
from mcp_servers.brasil_data_hub_mcp import BrasilDataHubMCPServer

server = BrasilDataHubMCPServer()

# Buscar todas as capitais
result = await server.handle_tool("get_capitais", {})

# Buscar capitais do Nordeste
result = await server.handle_tool("get_capitais", {"regiao": "Nordeste"})
```

### Exemplo: Enriquecer dados de empresa

```python
from mcp_servers.brasilapi_mcp import BrasilAPIMCPServer
from mcp_servers.apollo_mcp import ApolloMCPServer

brasilapi = BrasilAPIMCPServer()
apollo = ApolloMCPServer()

# 1. Buscar dados da Receita Federal
company = await brasilapi.handle_tool("get_company", {"cnpj": "00000000000191"})

# 2. Buscar executivos via Apollo
executives = await apollo.handle_tool("get_executives", {
    "company_name": "Banco do Brasil"
})
```

## Estrutura de Resposta

Todas as tools retornam resposta padronizada:

```json
{
    "success": true,
    "message": "Descrição do resultado",
    "data": {
        // dados específicos da tool
    }
}
```

Em caso de erro:

```json
{
    "success": false,
    "error": "Descrição do erro"
}
```

## Testes

```bash
# Testar todos os MCPs
python -m pytest tests/test_mcp_servers.py

# Testar MCP específico
python -m mcp_servers.serper_mcp.server --test
```

## Rastreabilidade (Compliance)

Todos os MCPs registram uso das fontes de dados na tabela `fontes_dados` conforme requisitos de compliance (ISO 27001/27701).

## Arquitetura

```
mcp_servers/
├── __init__.py
├── config.py           # Configurações compartilhadas
├── base_mcp.py         # Classe base para MCPs
│
├── brasil_data_hub_mcp/
│   ├── __init__.py
│   └── server.py       # Dados geográficos
│
├── serper_mcp/
│   ├── __init__.py
│   └── server.py       # Google Search
│
├── brasilapi_mcp/
│   ├── __init__.py
│   └── server.py       # Receita Federal
│
├── apollo_mcp/
│   ├── __init__.py
│   └── server.py       # B2B Intelligence
│
├── cnpja_mcp/
│   ├── __init__.py
│   └── server.py       # Regime tributário
│
└── perplexity_mcp/
    ├── __init__.py
    └── server.py       # AI Research
```

## Referências

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
