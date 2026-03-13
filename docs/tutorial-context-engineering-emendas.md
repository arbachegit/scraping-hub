# Tutorial: Context Engineering — Emendas Parlamentares

**Data:** 2026-03-12
**Versao:** 1.0.0
**Autor:** Fernando + Claude

---

## O que foi construido

Um sistema de **inteligencia contextual** que transforma dados brutos de emendas parlamentares em respostas a perguntas reais. Em vez de apenas listar registros, o sistema responde:

- "Qual o panorama geral?" (RPC 1)
- "Pra quem vai o dinheiro?" (RPC 2)
- "Onde mais se investe?" (RPC 3)
- "Quem mais direciona?" (RPC 4)
- "Pra onde vai?" (RPC 5)
- "Qual o perfil?" (RPC 6)
- "Como o dinheiro flui?" (RPC 7)
- "Como evolui o orcamento?" (RPC 8)
- "Como evolui por tema?" (RPC 9)
- "Como evolui por autor?" (RPC 10)
- "Como evolui por territorio?" (RPC 11)
- "O orcamento esta concentrado?" (RPC 12)

---

## Arquitetura Geral

```
                    ┌─────────────────────┐
                    │   Frontend (Next.js) │
                    │  apps/web/app/emendas│
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │   API Layer (api.ts) │
                    │  listEmendas()       │
                    │  getEmendasTimeSeries│
                    │  getEmendaContext()  │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │  Backend (Express)   │
                    │  routes/emendas.js   │
                    └──┬──────────────┬───┘
                       │              │
          ┌────────────▼──┐    ┌──────▼────────────┐
          │ Brasil Data Hub│    │  iconsai-scraping  │
          │ (mnfjkegt...)  │    │  (redivrme...)     │
          │                │    │                    │
          │ fato_emendas_  │    │ dim_taxonomia_     │
          │  parlamentares │    │  tematica          │
          │ fato_emendas_  │    │ map_funcao_        │
          │  favorecidos   │    │  taxonomia         │
          │ fato_emendas_  │    │ fato_associacoes_  │
          │  convenios     │    │  contextuais       │
          │ fato_emendas_  │    │ dim_noticias       │
          │  apoiamento    │    │ dim_sinais_        │
          └────────────────┘    │  contextuais       │
                                └────────────────────┘
```

**Dois bancos, uma camada semantica.** O Brasil Data Hub armazena os dados brutos de emendas (75k parlamentares + 733k favorecidos). O iconsai-scraping armazena noticias, taxonomia e associacoes. A ponte entre eles e a **taxonomia tematica unificada**.

---

## 1. Taxonomia Tematica Unificada

### O problema

Emendas usam `funcao` com ~46 variantes: "10-Saude", "Saude", "Educacao", "12-Educacao", etc.
Noticias usam `tema_principal` com 11 valores: "saude", "educacao", "economia", etc.

Nao ha como cruzar diretamente.

### A solucao: 3 tabelas

```
dim_taxonomia_tematica (15 slugs canonicos)
  ↑                         ↑
  │                         │
map_funcao_taxonomia     map_tema_taxonomia
  ↑                         ↑
  │                         │
emendas.funcao           noticias.tema_principal
```

#### Tabela 1: `dim_taxonomia_tematica` — Vocabulario comum

| slug | nome | cor | icone | dominio |
|------|------|-----|-------|---------|
| saude | Saude | #10b981 | heart-pulse | ambos |
| educacao | Educacao | #3b82f6 | graduation-cap | ambos |
| economia | Economia | #f59e0b | trending-up | ambos |
| mercado | Mercado | #8b5cf6 | building-2 | ambos |
| politica | Politica | #ef4444 | landmark | noticias |
| agricultura | Agricultura | #84cc16 | wheat | ambos |
| seguranca_publica | Seguranca Publica | #f97316 | shield | ambos |
| tecnologia | Tecnologia | #06b6d4 | cpu | ambos |
| infraestrutura | Infraestrutura | #64748b | hard-hat | ambos |
| energia | Energia | #eab308 | zap | ambos |
| assistencia_social | Assistencia Social | #ec4899 | hand-heart | emendas |
| cultura_lazer | Cultura e Lazer | #a855f7 | palette | emendas |
| defesa | Defesa | #475569 | shield-alert | emendas |
| meio_ambiente | Meio Ambiente | #22c55e | leaf | ambos |
| geral | Geral | #94a3b8 | layers | ambos |

O campo `dominio` indica se o tema aparece em emendas, noticias ou ambos. "politica" so aparece em noticias (emendas nao tem funcao "Politica"). "assistencia_social", "cultura_lazer" e "defesa" so existem em emendas.

#### Tabela 2: `map_funcao_taxonomia` — Normaliza funcao

Exemplos:

```sql
'Saude'              → 'saude'
'10-Saude'           → 'saude'
'Educacao'           → 'educacao'
'12-Educacao'        → 'educacao'
'Encargos especiais' → 'economia'
'Urbanismo'          → 'infraestrutura'
'15-Urbanismo'       → 'infraestrutura'
'Comercio e servicos'→ 'mercado'
```

~46 variantes mapeadas para 15 slugs.

#### Tabela 3: `map_tema_taxonomia` — Mapeia noticias

```sql
'saude'    → 'saude'
'economia' → 'economia'
'mercado'  → 'mercado'
-- (mapeamento direto, mas explicito para consistencia)
```

### Como usar: Buscar taxonomia de uma emenda

```javascript
// 1. Pegar o funcao da emenda
const emenda = { funcao: '10-Saude', autor: 'Fulano', ... };

// 2. Mapear funcao → slug
const { data } = await scrapingDb
  .from('map_funcao_taxonomia')
  .select('taxonomia_slug')
  .eq('funcao', emenda.funcao)
  .single();
// → { taxonomia_slug: 'saude' }

// 3. Buscar detalhes do tema
const { data: tema } = await scrapingDb
  .from('dim_taxonomia_tematica')
  .select('slug, nome, cor, icone')
  .eq('slug', data.taxonomia_slug)
  .single();
// → { slug: 'saude', nome: 'Saude', cor: '#10b981', icone: 'heart-pulse' }
```

### Como usar: Encontrar emendas por tema de noticia

```javascript
// 1. Noticia tem tema_principal = 'saude'
const slug = 'saude';

// 2. Reverse lookup: quais funcoes mapeiam para 'saude'?
const { data } = await scrapingDb
  .from('map_funcao_taxonomia')
  .select('funcao')
  .eq('taxonomia_slug', slug);
// → [{ funcao: 'Saude' }, { funcao: '10-Saude' }]

// 3. Buscar emendas com essas funcoes
const funcoes = data.map(d => d.funcao);
const { data: emendas } = await brasilDataHub
  .from('fato_emendas_parlamentares')
  .select('id, autor, funcao, ano, valor_empenhado')
  .in('funcao', funcoes)
  .limit(10);
```

---

## 2. Associacoes Contextuais (O Grafo)

### Tabela: `fato_associacoes_contextuais`

Esta e a tabela de **arestas** do grafo. Conecta entidades de tipos diferentes:

```
┌──────────┐    tema_comum     ┌──────────┐
│ noticia  │ ───────────────── │  emenda  │
│ (id:abc) │  conf: 0.65      │ (id:123) │
└──────────┘  slug: saude      └──────────┘
```

**Campos:**

| Campo | Tipo | Descricao |
|-------|------|-----------|
| origem_tipo | TEXT | 'noticia', 'emenda', 'pessoa', 'empresa' |
| origem_id | TEXT | ID na tabela de origem |
| destino_tipo | TEXT | 'noticia', 'emenda', 'pessoa', 'empresa' |
| destino_id | TEXT | ID na tabela de destino |
| tipo_associacao | TEXT | 'tema_comum', 'territorio_comum', 'mencao', 'autor_citado' |
| taxonomia_slug | TEXT | slug do tema compartilhado (FK → dim_taxonomia_tematica) |
| confianca | FLOAT | 0.0 a 1.0 — quanto confiamos nesta aresta |
| metodo | TEXT | 'manual', 'ia', 'regra', 'grafo' |
| evidencia | TEXT | Explicacao textual da associacao |

### Como as associacoes sao criadas

O servico `association-populator.js` roda o pipeline:

```
                    runAssociationPipeline()
                            │
                ┌───────────▼───────────┐
                │ 1. Carrega taxonomia  │
                │    temaToSlug (Map)   │
                │    funcaoToSlug (Map) │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │ 2. Busca noticias     │
                │    recentes com       │
                │    tema_principal     │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │ 3. Para cada noticia: │
                │    tema → slug        │
                │    slug → funcoes[]   │
                │    funcoes → emendas  │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │ 4. Calcula confianca: │
                │    base: 0.50         │
                │    +estado: 0.05      │
                │    +mesmo ano: 0.15   │
                │    +ano ±1: 0.05      │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │ 5. Insere arestas em  │
                │    fato_associacoes_  │
                │    contextuais        │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │ 6. Detecta sinais     │
                │    (regex em titulo   │
                │     + resumo)         │
                └───────────────────────┘
```

### Calculo de confianca

```javascript
function computeConfianca(noticia, emenda) {
  let confianca = 0.5;  // base: mesmo tema

  // Sobreposicao territorial
  if (emenda.localidade && noticia.fonte_nome) {
    confianca += 0.05;
  }

  // Proximidade temporal
  const pubYear = new Date(noticia.data_publicacao).getFullYear();
  if (emenda.ano === pubYear) confianca += 0.15;      // mesmo ano
  else if (Math.abs(emenda.ano - pubYear) <= 1) confianca += 0.05;  // ±1 ano

  return Math.min(confianca, 1.0);  // max: 1.0
}
```

Resultado: confianca varia de 0.50 (so tema) a 0.70 (tema + estado + ano).

### Como as associacoes sao consumidas

**Endpoint `GET /api/emendas/:id/context`** — consulta bidirecional:

```javascript
// Dado uma emenda, encontrar noticias associadas:
const { data: associations } = await scrapingDb
  .from('fato_associacoes_contextuais')
  .select('origem_id, tipo_associacao, confianca, evidencia')
  .eq('destino_tipo', 'emenda')
  .eq('destino_id', String(emendaId))
  .eq('origem_tipo', 'noticia')
  .order('confianca', { ascending: false })
  .limit(10);

// Depois buscar as noticias reais:
const noticiaIds = associations.map(a => a.origem_id);
const { data: noticias } = await scrapingDb
  .from('dim_noticias')
  .select('id, titulo, resumo, fonte_nome, data_publicacao, tema_principal, url')
  .in('id', noticiaIds);
```

**Fallback** — se nao existem associacoes pre-computadas:

```javascript
// Buscar noticias com mesmo tema via taxonomia
const { data: temaMapping } = await scrapingDb
  .from('map_tema_taxonomia')
  .select('tema_principal')
  .eq('taxonomia_slug', taxonomiaSlug);

const temas = temaMapping.map(t => t.tema_principal);
const { data: noticias } = await scrapingDb
  .from('dim_noticias')
  .select('...')
  .in('tema_principal', temas)
  .limit(5);
```

---

## 3. RPCs — Funcoes de Contexto

### Onde vivem

- **RPCs 1-7** (Agregacao): `backend/database/migrations/060_emendas_context_rpcs.sql`
  - Deployadas no **Brasil Data Hub** (`mnfjkegtynjtgesfphge`)
- **RPCs 8-12** (Serie temporal): `backend/database/migrations/063_emendas_time_series_rpcs.sql`
  - Deployadas no **Brasil Data Hub** (`mnfjkegtynjtgesfphge`)

### Tabela de RPCs

| # | RPC | Pergunta | Parametros | Retorno |
|---|-----|----------|------------|---------|
| 1 | `get_emendas_context_totals` | Qual o panorama? | nenhum | total_emendas, empenhado, pago, taxa_execucao, autores_unicos |
| 2 | `get_emendas_beneficiary_focus` | Pra quem vai? | nenhum | tipo_favorecido, count, valor_total, percentual |
| 3 | `get_emendas_top_funcoes` | Onde investe? | p_limit | funcao, count, empenhado, pago, taxa_execucao |
| 4 | `get_emendas_context_top_autores` | Quem direciona? | p_limit | autor, count, empenhado, pago, funcoes_distintas |
| 5 | `get_emendas_top_destinos` | Pra onde vai? | p_limit | uf, count, valor_total, municipios |
| 6 | `get_emendas_by_tipo_emenda` | Qual o perfil? | nenhum | tipo_emenda, count, empenhado, pago |
| 7 | `get_emendas_mecanismos` | Como flui? | nenhum | convenios, pix, apoiamento (contagens + valores) |
| 8 | `get_emendas_time_series` | Como evolui? | p_funcao, p_uf, p_autor, p_tipo_emenda | ano, total, empenhado, liquidado, pago, taxa |
| 9 | `get_emendas_funcao_time_series` | Tema evolui? | p_limit | ano, funcao, total, empenhado, pago, taxa |
| 10 | `get_emendas_autor_time_series` | Autor evolui? | p_autor | ano, total, empenhado, liquidado, pago, funcoes |
| 11 | `get_emendas_destino_time_series` | Territorio evolui? | p_limit | ano, uf, total_repasses, valor_total |
| 12 | `get_emendas_concentration` | Concentrado? | nenhum | autor(top10/50_share), territorio(top5), tema(top3) |

### Exemplos de chamada

```sql
-- Panorama geral
SELECT get_emendas_context_totals();

-- Serie temporal com filtro por Saude
SELECT get_emendas_time_series('Saude', NULL, NULL, NULL);

-- Serie temporal de um autor especifico
SELECT get_emendas_autor_time_series('FULANO DE TAL');

-- Concentracao (usa materialized view internamente)
SELECT get_emendas_concentration();
```

---

## 4. Endpoints da API

### `GET /api/emendas/list`

Lista emendas com paginacao e filtros.

```bash
curl "http://localhost:3106/api/emendas/list?limit=20&offset=0&autor=Fulano&uf=SP&ano=2024"
```

**Parametros** (todos validados por Zod):

| Param | Tipo | Default | Descricao |
|-------|------|---------|-----------|
| limit | int | 50 | 1-200 |
| offset | int | 0 | paginacao |
| autor | string | - | ilike com escapeLike |
| uf | string(2) | - | eq exato |
| ano | int | - | 2000-2030 |
| tipo | string | - | ilike com escapeLike |

### `GET /api/emendas/search`

Busca hibrida com fallback em 3 niveis.

```bash
curl "http://localhost:3106/api/emendas/search?q=saude%20sao%20paulo&limit=20"
```

**Chain de busca:**
1. `buscar_emendas` (RPC v2) — exact + prefix + FTS + trigram
2. `search_emendas_ranked_v1` (RPC v1) — fallback
3. `ilike` direto — ultimo recurso

### `GET /api/emendas/aggregation`

Dashboard de contexto — 7 RPCs em paralelo via `Promise.all`.

```bash
curl "http://localhost:3106/api/emendas/aggregation"
```

**Resposta:**
```json
{
  "success": true,
  "rpc_available": true,
  "totals": {
    "total_emendas": 75712,
    "valor_empenhado": 244000000000,
    "valor_pago": 144200000000,
    "taxa_execucao": 59.1,
    "autores_unicos": 893
  },
  "beneficiaries": [...],
  "top_funcoes": [...],
  "top_autores": [...],
  "top_destinos": [...],
  "by_tipo": [...],
  "mecanismos": {...}
}
```

### `GET /api/emendas/time-series`

Serie temporal + concentracao — 3 RPCs em paralelo.

```bash
# Geral
curl "http://localhost:3106/api/emendas/time-series"

# Filtrado por funcao e UF
curl "http://localhost:3106/api/emendas/time-series?funcao=Saude&uf=SP"
```

**Parametros** (validados por Zod `timeSeriesEmendasSchema`):

| Param | Tipo | Descricao |
|-------|------|-----------|
| funcao | string | Filtra por funcao (trimmed, max 200) |
| uf | string(2) | Filtra por UF (uppercase) |
| autor | string | Filtra por autor (trimmed, max 200) |
| tipo_emenda | string | Filtra por tipo (trimmed, max 200) |

**Resposta:**
```json
{
  "success": true,
  "rpc_available": true,
  "series": [
    { "ano": 2019, "total_emendas": 8234, "valor_empenhado": 32000000000, "valor_pago": 18000000000, "taxa_execucao": 56.3 },
    { "ano": 2020, "total_emendas": 9102, "valor_empenhado": 38000000000, "valor_pago": 22000000000, "taxa_execucao": 57.9 }
  ],
  "by_funcao": [
    { "ano": 2019, "funcao": "Saude", "total_emendas": 2100, "valor_empenhado": 8000000000, "valor_pago": 5000000000, "taxa_execucao": 62.5 }
  ],
  "concentration": {
    "autor": { "total_autores": 893, "top10_share": 15.2, "top50_share": 42.8 },
    "territorio": { "total_ufs": 27, "top5_share": 58.3 },
    "tema": { "total_funcoes": 28, "top3_share": 45.7 }
  }
}
```

### `GET /api/emendas/:id/context`

Inteligencia contextual completa para uma emenda — conecta os dois bancos.

```bash
curl "http://localhost:3106/api/emendas/12345/context"
```

**Fluxo interno (5 queries paralelas + 2 sequenciais):**

```
1. Buscar emenda no Brasil Data Hub
          │
2. Promise.all([
     map_funcao_taxonomia → slug,     ← iconsai-scraping
     fato_emendas_favorecidos top 10, ← Brasil Data Hub
     get_emendas_autor_time_series(), ← Brasil Data Hub (RPC)
   ])
          │
3. dim_taxonomia_tematica → cor, icone ← iconsai-scraping
          │
4. fato_associacoes_contextuais → edges ← iconsai-scraping
          │
5. dim_noticias (pelos IDs das edges)  ← iconsai-scraping
   OU fallback: noticias por tema
```

**Resposta:**
```json
{
  "success": true,
  "emenda_id": 12345,
  "resumo": {
    "autor": "FULANO DE TAL",
    "partido": null,
    "funcao": "Saude",
    "subfuncao": "Atencao Basica",
    "tipo_emenda": "Individual",
    "localidade": "Sao Paulo - SP",
    "ano": 2023,
    "is_pix": false,
    "codigo_ibge": 3550308
  },
  "execucao": {
    "empenhado": 500000,
    "liquidado": 450000,
    "pago": 420000,
    "resto_a_pagar": 30000,
    "taxa_execucao": 84.0
  },
  "taxonomia": {
    "slug": "saude",
    "nome": "Saude",
    "cor": "#10b981",
    "icone": "heart-pulse"
  },
  "favorecidos": [
    { "tipo": "PJ", "nome": "Hospital Municipal XYZ", "uf": "SP", "municipio": "Sao Paulo", "valor": 300000 },
    { "tipo": "PJ", "nome": "UBS Centro", "uf": "SP", "municipio": "Sao Paulo", "valor": 120000 }
  ],
  "autor_historico": [
    { "ano": 2020, "total_emendas": 15, "valor_empenhado": 3000000, "valor_pago": 2100000, "taxa_execucao": 70.0, "funcoes_distintas": 4 },
    { "ano": 2021, "total_emendas": 18, "valor_empenhado": 4500000, "valor_pago": 3800000, "taxa_execucao": 84.4, "funcoes_distintas": 5 },
    { "ano": 2022, "total_emendas": 22, "valor_empenhado": 6000000, "valor_pago": 5200000, "taxa_execucao": 86.7, "funcoes_distintas": 6 }
  ],
  "associations_count": 3,
  "noticias": [
    {
      "id": "uuid-abc",
      "titulo": "Governo anuncia R$ 2 bi para saude basica",
      "resumo": "Ministerio da Saude destina...",
      "fonte_nome": "Folha de Sao Paulo",
      "data_publicacao": "2023-06-15",
      "tema_principal": "saude",
      "url": "https://..."
    }
  ]
}
```

---

## 5. Como tudo se encaixa no Grafo

### Modelo de Grafo Atual

```
                        ┌───────────────────────────────────┐
                        │      dim_taxonomia_tematica       │
                        │  (15 slugs = categorias semanticas)│
                        └──┬──────────────────────┬─────────┘
                           │                      │
              map_funcao_taxonomia      map_tema_taxonomia
                           │                      │
                    ┌──────▼──────┐        ┌──────▼──────┐
                    │   EMENDA    │        │   NOTICIA   │
                    │  (75.712)   │        │  (29.000+)  │
                    └──────┬──────┘        └──────┬──────┘
                           │                      │
                           │  fato_associacoes_    │
                           │  contextuais          │
                           │  (tema_comum,         │
                           │   territorio_comum,   │
                           │   mencao,             │
                           │   autor_citado)        │
                           │                      │
                           └──────────┬───────────┘
                                      │
                              ┌───────▼────────┐
                              │   ARESTA       │
                              │ confianca: 0-1 │
                              │ metodo: regra  │
                              │ evidencia: ... │
                              └────────────────┘
```

### Tipos de nos (vertices)

| Tipo | Tabela | Banco | Volume |
|------|--------|-------|--------|
| emenda | fato_emendas_parlamentares | Brasil Data Hub | 75.712 |
| noticia | dim_noticias | iconsai-scraping | ~29.000 |
| pessoa | dim_pessoas | iconsai-scraping | variavel |
| empresa | dim_empresas | iconsai-scraping | variavel |
| politico | dim_politicos | Brasil Data Hub | ~160.000 |

### Tipos de arestas

| tipo_associacao | Origem → Destino | Descricao |
|-----------------|------------------|-----------|
| `tema_comum` | noticia → emenda | Compartilham taxonomia (saude, educacao...) |
| `territorio_comum` | noticia → emenda | Mesmo estado ou municipio |
| `mencao` | noticia → pessoa/empresa | Entidade mencionada no texto da noticia |
| `autor_citado` | noticia → emenda | Autor da emenda citado na noticia |

### Como o grafo cresce

```
Hoje (1.865 arestas):
  500 noticias classificadas × ~3.7 emendas cada

Proximo passo (estimativa ~10.000+ arestas):
  29.000 noticias classificadas × 5 emendas cada
  + mencoes de entidades
  + territorio_comum
```

### Consulta bidirecional

**Emenda → Noticias** (endpoint `/:id/context`):
```sql
SELECT * FROM fato_associacoes_contextuais
WHERE destino_tipo = 'emenda' AND destino_id = '12345'
  AND origem_tipo = 'noticia'
ORDER BY confianca DESC LIMIT 10;
```

**Noticia → Emendas** (servico `getNoticiaContext`):
```sql
SELECT * FROM fato_associacoes_contextuais
WHERE origem_tipo = 'noticia' AND origem_id = 'uuid-abc'
  AND destino_tipo = 'emenda'
ORDER BY confianca DESC LIMIT 10;
```

### Integracao com o Graph Route existente

O arquivo `backend/src/routes/graph.js` ja suporta nos do tipo `politico`. As emendas entram no grafo como arestas conectando:

```
politico ──(autor)──> emenda ──(tema_comum)──> noticia
                                                  │
                                        ──(mencao)──> empresa
                                        ──(mencao)──> pessoa
```

Isto habilita queries de travessia como:
- "Quais empresas sao mencionadas em noticias sobre emendas do politico X?"
- "Quais emendas de saude tem noticias recentes sobre irregularidades?"

---

## 6. Frontend — Pagina de Emendas

### Localizacao: `apps/web/app/emendas/page.tsx`

### Layout (de cima para baixo)

```
┌─────────────────────────────────────────────────────────┐
│ Row 1: 4 Summary Cards                                  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │Total     │ │Empenhado │ │Pago      │ │Taxa Exec │    │
│ │75.712    │ │R$ 244 bi │ │R$ 144 bi │ │59.1%     │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────┤
│ Row 2: 4 Summary Cards                                  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │Autores   │ │Liquidado │ │PIX       │ │Convenios │    │
│ │893       │ │R$ 167 bi │ │12.340    │ │71.039    │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────┤
│ Row 3: Context Facet Cards                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│ │Beneficiarios │ │Onde Investe  │ │Destinos (UFs)│     │
│ │PJ: 45%       │ │Saude: 22%   │ │SP: 18%       │     │
│ │PF: 30%       │ │Educacao: 15%│ │MG: 12%       │     │
│ │UG: 25%       │ │Economia: 12%│ │RJ: 10%       │     │
│ └──────────────┘ └──────────────┘ └──────────────┘     │
├─────────────────────────────────────────────────────────┤
│ Row 4: Time Series + Concentration                      │
│ ┌──────────────────────────┐ ┌──────┐ ┌──────┐ ┌──────┐│
│ │ ████ Empenhado           │ │Autor │ │Terr. │ │Tema  ││
│ │ ████ ████                │ │Top10 │ │Top5  │ │Top3  ││
│ │ ████ ████ ████           │ │15.2% │ │58.3% │ │45.7% ││
│ │ 2019  2020  2021  2022   │ │Baixa │ │Alta  │ │Media ││
│ └──────────────────────────┘ └──────┘ └──────┘ └──────┘│
├─────────────────────────────────────────────────────────┤
│ Search + Filters                                        │
│ [🔍 Buscar...                  ] [Filtros ▼ (2)]       │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │Funcao ▼  │ │Ano ▼     │ │Tipo ▼    │ │Local. ▼  │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────┤
│ Data Table                                              │
│ ┌────────┬────────┬────────┬────────┬────────┬────┐     │
│ │ Autor ▲│ Funcao │ Local  │ Tipo   │Empenh. │ Ano│     │
│ ├────────┼────────┼────────┼────────┼────────┼────┤     │
│ │ FULANO │ Saude  │ SP     │ Indiv. │ R$500k │2023│     │
│ │ CICRANO│ Educ.  │ MG     │ Banc.  │ R$1.2M │2023│     │
│ │ ...    │ ...    │ ...    │ ...    │ ...    │ .. │     │
│ └────────┴────────┴────────┴────────┴────────┴────┘     │
├─────────────────────────────────────────────────────────┤
│ Expanded Row (ao clicar):                               │
│ ┌──────────────────┬──────────────────┬────────────────┐│
│ │ Col 1: Resumo    │ Col 2: Favorec.  │ Col 3: Noticias││
│ │                  │                  │                ││
│ │ 🟢 Saude         │ Hospital XYZ     │ "Governo anuncia│
│ │ Autor: Fulano   │ R$ 300k (PJ)     │  R$ 2 bi..."   ││
│ │ Individual      │ UBS Centro       │                ││
│ │ Sao Paulo - SP  │ R$ 120k (PJ)     │ Folha, 15/06   ││
│ │ 2023            │                  │                ││
│ │                  │ ── Historico ──  │                ││
│ │ ████████████ 84% │ 2020: ██ R$2.1M │                ││
│ │ Empenhado: 500k │ 2021: ███ R$3.8M│                ││
│ │ Pago:      420k │ 2022: ████ R$5.2M│                ││
│ └──────────────────┴──────────────────┴────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### Expanded Row — Detalhes

Ao expandir uma linha, o frontend faz `GET /api/emendas/:id/context` e exibe:

**Coluna 1 — Resumo + Execucao:**
- Badge da taxonomia (cor + icone do tema)
- Autor, partido, tipo, ano, localidade, subfuncao
- Badge PIX (se aplicavel)
- Barra de progresso da execucao (verde >= 80%, amber >= 50%, vermelho < 50%)
- Valores: empenhado, liquidado, pago, resto a pagar

**Coluna 2 — Favorecidos + Historico do Autor:**
- Top 10 beneficiarios (nome, tipo, UF/municipio, valor)
- Mini-grafico de barras: evolucao do autor por ano (empenhado vs pago)

**Coluna 3 — Noticias Relacionadas:**
- Noticias vindas das associacoes contextuais (ou fallback por tema)
- Titulo, resumo, fonte, data, link

---

## 7. Deteccao de Sinais

### Tabela: `dim_sinais_contextuais`

Define padroes regex para detectar sinais em noticias:

| Campo | Descricao |
|-------|-----------|
| slug | Identificador: 'risco_fiscal', 'alta_inflacao', etc. |
| nome | Nome legivel |
| categoria | economia, politica, saude, etc. |
| tipo | sinal, alerta, positivo |
| keywords_regex | Regex para match: `inflacao\|ipca\|selic` |
| prioridade | 0-100 |

### Como funciona

```javascript
// Para cada noticia:
const text = `${noticia.titulo} ${noticia.resumo}`.toLowerCase();

for (const signal of signals) {
  const regex = new RegExp(signal.keywords_regex, 'i');
  if (regex.test(text)) {
    // Match! Inserir em fato_noticias_sinais
    // confianca: 0.70 (regex match)
    // metodo: 'regex'
  }
}
```

### Tabela de juncao: `fato_noticias_sinais`

```sql
noticia_id → dim_noticias.id
sinal_id   → dim_sinais_contextuais.id
confidence → 0.70 (regex)
detection_method → 'regex'
```

### RPCs de consulta

```sql
-- Quais sinais tem essa noticia?
SELECT get_noticias_sinais('uuid-da-noticia');

-- Quais noticias tem esse sinal?
SELECT get_noticias_by_sinal('risco_fiscal', 20);
```

---

## 8. Validacao e Sanitizacao

### Schemas Zod aplicados

| Endpoint | Schema | Campos validados |
|----------|--------|------------------|
| GET /list | `listEmendasSchema` | limit, offset, autor, uf, ano, tipo |
| GET /search | `searchEmendasSchema` | q (min 2), limit |
| GET /time-series | `timeSeriesEmendasSchema` | funcao, uf, autor, tipo_emenda |
| GET /subnacionais | `listEmendasSubnacionaisSchema` | limit, offset, autor, uf, ano, tipo, esfera |
| GET /:id | `integerIdParamSchema` | id (int positivo) |
| GET /:id/context | `integerIdParamSchema` | id (int positivo) |

### Sanitizacao aplicada

- `safeStringSchema`: max 200 chars + trim + rejeita `%`, `_`, `\`
- `escapeLike()`: escapa caracteres especiais para queries ILIKE
- Log injection: `q.replace(/[\r\n]/g, ' ')` antes de logar
- UF: uppercase + regex `^[A-Z]{2}$`
- esfera: enum `['estadual', 'municipal']`

---

## 9. Materialized Views

Para queries que excedem o timeout do Supabase REST API (~3-8s):

| View | Fonte | Motivo |
|------|-------|--------|
| `mv_emendas_concentration` | CTE com 75k + 733k rows | get_emendas_concentration() le da view |

A view precisa ser refreshed periodicamente:

```sql
REFRESH MATERIALIZED VIEW mv_emendas_concentration;
```

---

## 10. Proximos Passos

### Pendente (Fase 2)

| Item | Descricao | Status |
|------|-----------|--------|
| Preencher `partido` | Coluna existe mas esta NULL em todas as emendas | Pendente |
| Mais associacoes | Rodar pipeline nas 29k noticias classificadas (hoje: 500) | Pendente |
| territorio_comum | Arestas por sobreposicao geografica (UF da emenda vs UF da noticia) | Pendente |
| autor_citado | Detectar nome de autor de emenda no texto da noticia | Pendente |
| HHI real | Indice de Herfindahl-Hirschman (soma dos quadrados dos market shares) | Pendente |
| Comparison endpoints | Comparar dois autores, dois temas, duas UFs | Pendente |
| Refresh cron | Atualizar mv_emendas_concentration periodicamente | Pendente |

### Pendente (Fase 3)

| Item | Descricao |
|------|-----------|
| Graph materialization | Criar tabela de arestas materializada para travessia rapida |
| Anomaly detection | Detectar emendas com taxa_execucao outlier |
| Entity resolution | Ligar emenda.autor ↔ dim_politicos.nome_urna |
| Multi-hop queries | "Empresas beneficiadas por emendas de politicos mencionados em noticias sobre fraude" |

---

## Arquivos-chave

```
backend/database/migrations/
  060_emendas_context_rpcs.sql          ← RPCs 1-7 (agregacao)
  061_emendas_favorecidos_indexes.sql   ← indices de performance
  062_context_taxonomy_and_associations.sql ← taxonomia + associacoes
  063_emendas_time_series_rpcs.sql      ← RPCs 8-12 (temporal)
  063_sinais_contextuais_tables.sql     ← sinais contextuais

backend/src/routes/emendas.js           ← 7 endpoints REST
backend/src/services/association-populator.js ← pipeline de associacoes
backend/src/validation/schemas.js       ← Zod schemas

apps/web/app/emendas/page.tsx           ← pagina frontend
apps/web/lib/api.ts                     ← tipos TS + funcoes API
```
