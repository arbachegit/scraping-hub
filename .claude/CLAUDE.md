# scraping-hub - Sistema de Web Scraping

**VERSÃO: 3.0.0 - COMPLIANCE + VALIDATION**
**DATA: 11/02/2026**
**STATUS: PROJETO AUDITADO - COMPLIANCE ISO 27001/27701**

---

## 🚨 REGRAS IMUTÁVEIS (NUNCA VIOLAR)

### REGRA 0: PROIBIÇÃO ABSOLUTA DE MUDANÇAS NÃO SOLICITADAS

```
❌ NUNCA MUDAR CÓDIGO QUE NÃO FOI EXPLICITAMENTE PEDIDO
❌ NUNCA "MELHORAR" CÓDIGO SEM AUTORIZAÇÃO
❌ NUNCA "REFATORAR" SEM ORDEM DIRETA
❌ NUNCA "OTIMIZAR" SEM PERMISSÃO
❌ NUNCA ADICIONAR FEATURES NÃO PEDIDAS
❌ NUNCA SUGERIR MUDANÇAS - APENAS EXECUTAR ORDENS
```

**PENALIDADE:** Se Claude modificar QUALQUER arquivo não solicitado, o trabalho é REJEITADO e deve ser revertido completamente.

---

### REGRA 1: EXECUÇÃO LITERAL DE COMANDOS

**Claude deve:**
- ✅ Executar EXATAMENTE o que foi pedido
- ✅ Não interpretar, não inferir, não assumir
- ✅ Se houver QUALQUER ambiguidade → PARAR e perguntar
- ✅ Confirmar entendimento ANTES de executar

**Formato obrigatório de resposta:**
```
Entendi que você quer:
1. [ação específica 1]
2. [ação específica 2]
3. [ação específica 3]

Arquivos que serão modificados:
- arquivo1.py (linha X-Y)
- arquivo2.py (adicionar função Z)

CONFIRMAÇÃO NECESSÁRIA: Prosseguir? (sim/não)
```

---

### REGRA 2: VALIDAÇÃO OBRIGATÓRIA (ZOD + PYDANTIC)

**Todo endpoint DEVE ter validação:**

```javascript
// ✅ Node.js - SEMPRE usar Zod
import { z } from 'zod';
import { validateBody } from '../validation/schemas.js';

const schema = z.object({
  nome: z.string().min(2).max(200),
  cnpj: z.string().transform(val => val.replace(/[^\d]/g, ''))
});

router.post('/endpoint', validateBody(schema), async (req, res) => {
  // req.body já validado
});
```

```python
# ✅ Python - SEMPRE usar Pydantic
from pydantic import BaseModel

class RequestBody(BaseModel):
    nome: str
    cnpj: str

@app.post("/endpoint")
async def endpoint(body: RequestBody):
    # body já validado
```

**Schemas existentes:** `backend/src/validation/schemas.js`
- `searchCompanySchema` - Busca de empresa
- `detailsCompanySchema` - Detalhes por CNPJ
- `sociosSchema` - Enriquecimento de sócios
- `approveCompanySchema` - Aprovação de empresa
- `recalculateSchema` - Recálculo VAR

---

### REGRA 3: CONSTANTES OBRIGATÓRIAS (SEM MAGIC STRINGS)

**NUNCA usar strings literais repetidas:**

```javascript
// ❌ PROIBIDO
linkedin = 'NAO_POSSUI';
regime = 'SIMPLES_NACIONAL';

// ✅ OBRIGATÓRIO - usar constants.js
import { LINKEDIN_STATUS, REGIME_TRIBUTARIO } from '../constants.js';

linkedin = LINKEDIN_STATUS.NAO_POSSUI;
regime = REGIME_TRIBUTARIO.SIMPLES_NACIONAL;
```

**Constantes disponíveis:** `backend/src/constants.js`
- `LINKEDIN_STATUS` - NAO_POSSUI, PENDENTE
- `REGIME_TRIBUTARIO` - MEI, SIMPLES_NACIONAL, LUCRO_PRESUMIDO, LUCRO_REAL
- `LIMITES_REGIME` - Limites de faturamento por regime
- `DATA_SOURCES` - Fontes de dados para compliance

---

### REGRA 4: LOGGING ESTRUTURADO OBRIGATÓRIO

**NUNCA usar console.log para logs de produção:**

```javascript
// ❌ PROIBIDO
console.log('Buscando empresa:', nome);
console.error('Erro:', error);

// ✅ OBRIGATÓRIO - usar logger estruturado
import logger from '../utils/logger.js';

logger.info('Buscando empresa', { nome, cidade });
logger.error('Erro na busca', { error: error.message, stack: error.stack });
```

**Logger:** `backend/src/utils/logger.js`
- Formato JSON estruturado
- Níveis: debug, info, warn, error
- Request ID para rastreamento
- Consistente com Python structlog

---

### REGRA 5: RATE LIMITER OBRIGATÓRIO

**Todo endpoint público DEVE ter rate limit:**

```javascript
// Configurado em backend/src/index.js
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 60 * 1000,  // 1 minuto
  max: 100,             // 100 requisições por IP
  message: { error: 'Muitas requisições. Tente novamente em 1 minuto.' }
});

app.use('/companies', limiter);
```

**Limites atuais:**
- `/companies/*` - 100 req/min por IP

---

### REGRA 6: REGISTRO DE FONTES OBRIGATÓRIO (COMPLIANCE)

**TODO scraping DEVE registrar fonte na tabela `fontes_dados`:**

```javascript
// Registro automático no startup do backend
import { registerDataSource } from '../database/supabase.js';
import { DATA_SOURCES } from '../constants.js';

// Auto-registro de todas as fontes
for (const [key, source] of Object.entries(DATA_SOURCES)) {
  await registerDataSource(source);
}
```

**Tabela `fontes_dados` (Supabase):**
| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| nome | TEXT UNIQUE | ✅ |
| categoria | TEXT | ✅ |
| fonte_primaria | TEXT | ✅ |
| url | TEXT | ✅ |
| confiabilidade | TEXT | ✅ |
| api_key_necessaria | BOOLEAN | ✅ |

**Fontes registradas:**
1. Serper - Google Search API (busca)
2. Perplexity AI (ia)
3. BrasilAPI - Receita Federal (governamental)
4. Apollo.io (enrichment)
5. CNPJá - Regime Tributário (fiscal)

**Penalidade:** Scraper sem registro de fonte = REJEITADO

---

### REGRA 7: IMUTABILIDADE DO BASE.PY

**O arquivo `src/scrapers/base.py` é SAGRADO:**

```
🔒 NUNCA modificar base.py sem ordem EXPLÍCITA
🔒 NUNCA "melhorar" base.py
🔒 NUNCA "otimizar" base.py
🔒 NUNCA adicionar features a base.py

✅ APENAS criar NOVOS scrapers que HERDAM de BaseScraper
```

---

### REGRA 8: SCRAPERS SÃO WRITE-ONLY

**Scrapers existentes NÃO podem ser modificados:**

```
🔒 src/scrapers/*.py     - IMUTÁVEL
🔒 backend/src/services/*.js - IMUTÁVEL (exceto bug fixes)
```

**Único caso permitido para modificação:**
```
"Corrija o BUG na linha X do arquivo Y"
"Adicione o parâmetro Z à função W do arquivo V"
```

---

### REGRA 9: DEPLOY VIA CI/CD (GITHUB ACTIONS)

**NUNCA fazer deploy manual:**

```
❌ NUNCA SSH no servidor para deploy
❌ NUNCA editar arquivos diretamente no servidor
❌ NUNCA rodar comandos manuais no servidor

✅ SEMPRE commit + push → CI/CD automático
✅ SEMPRE usar GitHub Actions
✅ SEMPRE secrets via GitHub Secrets
```

**Secrets configurados:**
- `DO_HOST` - IP do servidor
- `DO_USERNAME` - Usuário SSH
- `DO_SSH_KEY` - Chave SSH
- `APOLLO_API_KEY` - Apollo API
- `CNPJA_API_KEY` - CNPJá API
- `PERPLEXITY_API_KEY` - Perplexity API

---

### REGRA 10: AUTONOMIA: QUANDO EXECUTAR vs QUANDO PERGUNTAR

**EXECUTAR SEM PERGUNTAR (Correções Operacionais):**
- ✅ Adicionar porta ao CORS
- ✅ Criar/corrigir `.env` com credenciais já conhecidas
- ✅ Adicionar campo opcional em config (ex: nova env var)
- ✅ Corrigir imports quebrados
- ✅ Reiniciar serviços
- ✅ Corrigir erros de TypeScript/lint
- ✅ Adicionar índices em banco (sem alterar schema)
- ✅ Instalar dependências já listadas no package.json/requirements.txt
- ✅ Formatar código (prettier, black)
- ✅ Atualizar tipos/interfaces para match com API existente
- ✅ **Comandos Git**: status, add, commit, pull, push, branch, checkout, log, diff, stash

**PERGUNTAR ANTES (Mudanças de Impacto):**
- ❓ Alterar estrutura de tabelas (migrations)
- ❓ Mudar contratos de API (novos campos obrigatórios, remover campos)
- ❓ Alterar lógica de negócio/cálculos
- ❓ Criar novos endpoints
- ❓ Mudar arquitetura de componentes
- ❓ Adicionar dependências NOVAS ao projeto
- ❓ Alterar fluxo de autenticação
- ❓ Deletar código/arquivos
- ❓ Refatorar estrutura de pastas
- ❓ Mudar configurações de build/deploy

**Regra de Ouro:** Se a mudança pode quebrar algo que estava funcionando ou afeta outros desenvolvedores, PERGUNTE. Se é apenas fazer funcionar o que deveria funcionar, EXECUTE.

### BI DENSITY DESIGN SYSTEM (REGRA DE OURO - UI/UX)

**Princípio Fundamental:** Elementos de UI devem se adaptar ao container sem quebrar linha ou transbordar.

#### Regras Obrigatórias para Componentes Responsivos:

```css
/* 1. NUNCA permitir quebra de linha em labels/valores */
white-space: nowrap;

/* 2. SEMPRE permitir encolhimento em flex children */
min-width: 0;  /* CRÍTICO - sem isso flex não encolhe! */

/* 3. Truncar quando não couber */
text-overflow: ellipsis;
overflow: hidden;

/* 4. Fontes e espaçamentos fluidos com clamp() */
font-size: clamp(10px, 0.8vw, 14px);
padding: clamp(4px, 0.5vw, 8px);
gap: clamp(2px, 0.3vw, 6px);

/* 5. Números sempre alinhados */
font-variant-numeric: tabular-nums;
```

#### Padrão para Pares Label + Valor:

```css
.bi-kpi {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: var(--bi-gap-sm);
  align-items: baseline;
}

.bi-kpi-label { white-space: nowrap; opacity: 0.7; }

.bi-kpi-value {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
```

#### Padrão para Linhas Flex:

```css
.bi-row { display: flex; flex-wrap: nowrap; align-items: center; gap: var(--bi-gap-sm); }
.bi-cell { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bi-cell-fixed { flex-shrink: 0; white-space: nowrap; }
```

**Regra de Ouro UI:** Se um elemento pode ter texto longo, SEMPRE aplicar: `min-width: 0 + white-space: nowrap + text-overflow: ellipsis`.

---

## 📁 ESTRUTURA DO PROJETO

```
scraping-hub/
├── .claude/
│   └── CLAUDE.md                    📋 Este arquivo
├── backend/
│   ├── src/
│   │   ├── index.js                 🚀 Entry point (rate limiter, logger)
│   │   ├── constants.js             📌 Constantes (LINKEDIN_STATUS, etc)
│   │   ├── routes/
│   │   │   └── companies.js         🛣️ Rotas (com Zod validation)
│   │   ├── services/
│   │   │   ├── serper.js            🔍 Google Search
│   │   │   ├── perplexity.js        🤖 AI Search (fallback)
│   │   │   ├── apollo.js            👤 LinkedIn enrichment
│   │   │   ├── brasilapi.js         🏛️ Receita Federal
│   │   │   ├── cnpja.js             📊 Regime tributário
│   │   │   └── var_inference.js     📈 Modelo VAR
│   │   ├── database/
│   │   │   └── supabase.js          🗄️ DB + registerDataSource
│   │   ├── validation/
│   │   │   └── schemas.js           ✅ Zod schemas
│   │   └── utils/
│   │       └── logger.js            📝 Structured logging
│   └── database/
│       └── migrations/              🔄 SQL migrations
├── src/
│   └── scrapers/
│       └── base.py                  🔒 IMUTÁVEL
├── api/
│   ├── main.py                      🐍 FastAPI
│   └── auth.py                      🔐 JWT + Pydantic
├── static/
│   └── dashboard.html               🖥️ Frontend
├── scripts/
│   └── apply_migration_*.py         🔧 Migration scripts
├── tests/                           🧪 Pytest
└── .github/workflows/
    └── ci.yml                       🚀 CI/CD
```

---

## 🔄 FLUXO DE BUSCA (FALLBACK)

```
1. Serper (Google)
   ↓ não encontrou?
2. Perplexity AI
   ↓ não encontrou?
3. Serper (nome exato)
   ↓ não encontrou?
4. Retorna vazio + sources_tried
```

---

## 🗄️ BANCO DE DADOS (SUPABASE)

**Tabelas principais:**
- `dim_empresas` - Dados cadastrais
- `dim_pessoas` - Sócios/fundadores
- `fato_regime_tributario` - Histórico de regimes
- `fato_transacao_empresas` - Relação pessoa-empresa
- `fato_inferencia_limites` - Análise VAR
- `fontes_dados` - Compliance (ISO 27001/27701)

---

## 🚀 COMANDOS

```bash
# Deploy (via CI/CD)
git add . && git commit -m "feat: ..." && git push

# Rodar testes
pytest tests/ -v

# Rodar backend local
cd backend && npm run dev

# Rodar Python API local
uvicorn api.main:app --reload
```

---

## 📝 CHANGELOG

**v3.0.0 (11/02/2026) - COMPLIANCE + VALIDATION**
- ✅ Validação Zod em todos os endpoints Node.js
- ✅ Rate limiter (100 req/min)
- ✅ Logging estruturado (JSON)
- ✅ Constantes (sem magic strings)
- ✅ Tabela fontes_dados (compliance ISO 27001/27701)
- ✅ Auto-registro de fontes no startup
- ✅ Removida dependência de DigitalOcean API direta

**v2.0.0 (08/02/2026) - ULTRA-STRICT**
- ✅ Proibição absoluta de mudanças não solicitadas
- ✅ Imutabilidade de base.py e scrapers existentes
- ✅ Testes automáticos obrigatórios
- ✅ CI/CD automático obrigatório

---

**ESTE DOCUMENTO É A FONTE DA VERDADE**
**VIOLAÇÕES SERÃO REJEITADAS**
