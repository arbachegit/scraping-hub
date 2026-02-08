# IconsAI - Ecossistema de Sistemas Inteligentes

## 🚨 REGRAS CRÍTICAS (SEMPRE SEGUIR)

### 1. QUESTIONAR ANTES DE AGIR
- **NUNCA** assuma compreensão completa
- **SEMPRE** criar questionário de validação antes de implementar
- **SEMPRE** perguntar quando houver dúvidas, mesmo com bypass ativado
- **SEMPRE** explicar o que foi compreendido antes de começar

### 2. CÁLCULOS E PROCESSAMENTO
- ❌ **NEVER**: Cálculos matemáticos no frontend/JavaScript
- ✅ **ALWAYS**: Todos os cálculos em Python no backend
- ❌ **NEVER**: Dados hardcoded em código
- ✅ **ALWAYS**: Dados vindos de APIs/banco de dados

### 3. GESTÃO DE VOZ (TTS)
- ❌ **NEVER**: Usar voz do browser (window.speechSynthesis)
- ✅ **ALWAYS**: Usar OpenAI TTS (gpt-4o-mini-tts) ou ElevenLabs
- ✅ **ALWAYS**: Aplicar humanização conforme módulo (ver seção Voice)
- ✅ **ALWAYS**: Incluir instruções de voz personalizadas

### 4. RASTREABILIDADE DE DADOS
- ✅ **ALWAYS**: Toda informação precisa ter fonte registrada
- ✅ **ALWAYS**: Criar/atualizar tabela `fontes_dados` em TODOS os projetos
- ✅ **ALWAYS**: Incluir: fonte, URL, data coleta, periodicidade

### 5. MUDANÇAS NÃO SOLICITADAS
- ❌ **NEVER**: Alterar código que não foi pedido
- ❌ **NEVER**: "Melhorar" código sem autorização explícita
- ✅ **ONLY**: Fazer exatamente o que foi solicitado
- ✅ **IF**: Sugestões → perguntar antes de implementar

### 6. ENGENHARIA DE SOFTWARE
- ✅ **ALWAYS**: Seguir SOLID principles
- ✅ **ALWAYS**: Código testável e modular
- ✅ **ALWAYS**: TypeScript strict mode (frontend)
- ✅ **ALWAYS**: Type hints obrigatórios (Python)
- ✅ **ALWAYS**: Validação com Zod (TS) ou Pydantic (Python)

### 7. SEGURANÇA
- ❌ **NEVER**: Expor secrets em código
- ❌ **NEVER**: SQL direto sem prepared statements
- ✅ **ALWAYS**: Validar input do usuário
- ✅ **ALWAYS**: Sanitizar dados antes de armazenar
- ✅ **ALWAYS**: Usar variáveis de ambiente

---

## 📁 ESTRUTURA DOS PROJETOS

### Projetos Principais

```
iconsai-ecosystem/
├── iconsai-production/     → Sidebar/Admin (Vite + React + TS)
│   ├── src/
│   │   ├── components/     → UI components (shadcn/ui)
│   │   ├── modules/        → Feature modules
│   │   │   └── pwa-voice/  → Voice system (TTS/STT)
│   │   ├── config/         → voice-config.ts (presets)
│   │   ├── services/       → API integration
│   │   └── utils/          → Helpers
│   └── supabase/           → Edge Functions
│
├── orcamento-fiscal-municipios/ → Análise Fiscal (MAIS BEM ESTRUTURADO)
│   ├── backend/            → Python microservices
│   ├── src/                → React frontend
│   ├── scripts/            → ETL scripts (Python)
│   ├── mcp-servers/        → MCP integrations (SICONFI, etc)
│   ├── services/           → Microservices (Docker)
│   │   ├── tts-service/    → Voice synthesis
│   │   ├── auth-service/   → Authentication
│   │   ├── api-gateway/    → Gateway
│   │   └── geo-service/    → Geographic data
│   └── docs/               → Documentation (FONTES_DADOS.md)
│
└── scraping-hub/           → Web Scraping (MAIS PROBLEMÁTICO)
    ├── src/
    │   ├── scrapers/       → Scrapers individuais
    │   ├── services/       → Business logic
    │   └── database/       → DB models
    ├── api/                → FastAPI routes
    └── tests/              → pytest tests
```

### Status dos Projetos

| Projeto | Status | Stack | Principais Desafios |
|---------|--------|-------|---------------------|
| **orcamento-fiscal-municipios** | ✅ Melhor estruturado | React + Python + Supabase | Cálculos complexos, ETL massivo |
| **iconsai-production** | ⚠️ Adequado | React + TS + Supabase | Gestão de voz, múltiplos módulos |
| **scraping-hub** | ⚠️ Problemático | Python + FastAPI | Quebra frequente, manutenção alta |

---

## 🎯 STACK TECNOLÓGICA

### Frontend (iconsai-production, orcamento-fiscal)
```typescript
// Stack principal
- Vite + React 18
- TypeScript 5+ (strict mode)
- shadcn/ui + Radix UI
- TailwindCSS + Framer Motion
- Zustand (state management)
- React Query (@tanstack/react-query)
- Zod (validation)
```

### Backend (microservices)
```python
# Stack principal
- Python 3.11+
- FastAPI (async/await)
- Pydantic (validation)
- SQLAlchemy (ORM)
- Pytest (testing)
- Docker + Docker Compose
```

### Database & Infrastructure
```
- Supabase (PostgreSQL + Edge Functions)
- n8n (automação)
- DigitalOcean (hospedagem)
```

---

## 🎤 GESTÃO DE VOZ (CRÍTICO)

### Configuração OpenAI TTS (gpt-4o-mini-tts)

**Localização:** `src/config/voice-config.ts` (iconsai-production)

```typescript
// SEMPRE usar estes presets conforme módulo
export const VOICE_PRESETS = {
  friendly_assistant: {
    model: 'gpt-4o-mini-tts',
    voice: 'marin',
    speed: 1.0,
    instructions: `
      Voice Affect: Warm, friendly, naturally conversational.
      Tone: Approachable, like a knowledgeable friend.
      Language: Brazilian Portuguese with natural intonation.
      Avoid: Robotic monotone, rushed speech.
    `
  },
  calm_health: {
    voice: 'cedar',
    speed: 0.95,
    instructions: `
      Voice Affect: Calm, reassuring, empathetic.
      Tone: Professional yet warm healthcare provider.
      Language: Brazilian Portuguese.
    `
  },
  creative_ideas: {
    voice: 'nova',
    speed: 1.05,
    instructions: `
      Voice Affect: Energetic, inspiring, creative.
      Tone: Enthusiastic, sparking excitement.
    `
  }
};
```

### Parâmetros ElevenLabs (quando usado)

```json
{
  "stability": 0.45,
  "similarity_boost": 0.75,
  "style_exaggeration": 0.15,
  "speed": 1.0,
  "use_speaker_boost": true
}
```

### Vozes OpenAI Recomendadas

| Módulo | Voz | Características |
|--------|-----|-----------------|
| Home/Help | `marin` | Calorosa, natural |
| Saúde | `cedar` | Calma, reconfortante |
| Ideias | `nova` | Energética, engajada |
| Mundo/Info | `sage` | Sábia, educativa |

---

## 📊 RASTREAMENTO DE FONTES DE DADOS

### Estrutura da Tabela (OBRIGATÓRIA em todos os projetos)

```sql
CREATE TABLE fontes_dados (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Identificação
  nome TEXT NOT NULL,                  -- Ex: "SICONFI - RREO"
  categoria TEXT NOT NULL,             -- Ex: "fiscal", "geografico", "economico"
  
  -- Origem
  fonte_primaria TEXT NOT NULL,        -- Ex: "Tesouro Nacional"
  url TEXT NOT NULL,                   -- URL da API/fonte
  documentacao_url TEXT,               -- URL da documentação
  
  -- Rastreamento
  data_primeira_coleta TIMESTAMPTZ NOT NULL,
  data_ultima_atualizacao TIMESTAMPTZ,
  periodicidade TEXT,                  -- "mensal", "bimestral", "anual"
  
  -- Metadados
  formato TEXT,                        -- "JSON", "CSV", "XML"
  autenticacao_requerida BOOLEAN DEFAULT false,
  api_key_necessaria BOOLEAN DEFAULT false,
  
  -- Qualidade
  confiabilidade TEXT,                 -- "alta", "media", "baixa"
  cobertura_temporal TEXT,             -- Ex: "2015-presente"
  observacoes TEXT,
  
  -- Audit
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_fontes_categoria ON fontes_dados(categoria);
CREATE INDEX idx_fontes_periodicidade ON fontes_dados(periodicidade);
```

### Exemplo de Registro

```sql
INSERT INTO fontes_dados (
  nome,
  categoria,
  fonte_primaria,
  url,
  documentacao_url,
  data_primeira_coleta,
  periodicidade,
  formato,
  confiabilidade,
  cobertura_temporal
) VALUES (
  'SICONFI - Relatório Resumido Execução Orçamentária',
  'fiscal',
  'Tesouro Nacional',
  'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo',
  'https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra/finbra_list.jsf',
  '2026-01-15',
  'bimestral',
  'JSON',
  'alta',
  '2015-presente'
);
```

---

## 🔧 COMANDOS PRINCIPAIS

### iconsai-production
```bash
npm run dev              # Dev local
npm run build            # Build produção
npm run lint             # ESLint check
npm run preview          # Preview build
npm run validate         # lint + pre-deploy + build
```

### orcamento-fiscal-municipios
```bash
npm run dev              # Frontend dev
npm run build            # TypeScript compile + Vite build
npm run lint             # ESLint check

# Python scripts (backend)
python scripts/siconfi_rreo_import.py          # Importar RREO
python scripts/popular_indicadores_fiscais.py  # Calcular indicadores
python scripts/aplicar_migration_*.py          # Migrations
```

### scraping-hub
```bash
# Backend Python
uvicorn api.main:app --reload     # Dev local
pytest                            # Run tests
pytest --cov                      # Com coverage

# Frontend (se houver)
cd frontend && npm run dev
```

---

## 🏗️ PADRÕES DE CÓDIGO

### TypeScript (Frontend)

```typescript
// ✅ DO: Type safety completo
interface FiscalIndicator {
  codigo_ibge: string;
  rcl: number;
  despesa_pessoal: number;
  percentual_dp_rcl: number;
  status_lrf: 'regular' | 'alerta' | 'critico';
}

// ✅ DO: Validação com Zod
import { z } from 'zod';

const FiscalIndicatorSchema = z.object({
  codigo_ibge: z.string().regex(/^\d{7}$/),
  rcl: z.number().positive(),
  despesa_pessoal: z.number().nonnegative(),
  percentual_dp_rcl: z.number().min(0).max(100),
  status_lrf: z.enum(['regular', 'alerta', 'critico'])
});

// ✅ DO: Async/await para I/O
async function fetchIndicators(codigoIbge: string): Promise<FiscalIndicator> {
  const { data, error } = await supabase
    .from('indicadores_fiscais')
    .select('*')
    .eq('codigo_ibge', codigoIbge)
    .single();
  
  if (error) throw new AppError(error.message, 500);
  return FiscalIndicatorSchema.parse(data);
}

// ❌ DON'T: Cálculos complexos no frontend
const percentual = (despesa / rcl) * 100; // ❌ Fazer no backend Python

// ✅ DO: Chamar endpoint que calcula
const { percentual } = await api.calcularPercentualDpRcl(codigoIbge);
```

### Python (Backend)

```python
# ✅ DO: Type hints obrigatórios
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class FiscalIndicator(BaseModel):
    codigo_ibge: str = Field(..., regex=r'^\d{7}$')
    rcl: float = Field(..., gt=0)
    despesa_pessoal: float = Field(..., ge=0)
    percentual_dp_rcl: float = Field(..., ge=0, le=100)
    status_lrf: Literal['regular', 'alerta', 'critico']
    
    class Config:
        frozen = True  # Imutável

# ✅ DO: Async para I/O
async def fetch_indicators(codigo_ibge: str) -> FiscalIndicator:
    """
    Busca indicadores fiscais de um município.
    
    Args:
        codigo_ibge: Código IBGE de 7 dígitos
        
    Returns:
        FiscalIndicator com dados validados
        
    Raises:
        ValueError: Se código IBGE inválido
        HTTPException: Se município não encontrado
    """
    query = "SELECT * FROM indicadores_fiscais WHERE codigo_ibge = $1"
    row = await db.fetchrow(query, codigo_ibge)
    
    if not row:
        raise HTTPException(404, "Município não encontrado")
    
    return FiscalIndicator(**dict(row))

# ✅ DO: Cálculos complexos em Python
def calcular_percentual_dp_rcl(
    despesa_pessoal: float,
    rcl: float,
    aplicar_limite_prudencial: bool = False
) -> float:
    """
    Calcula percentual de Despesa com Pessoal sobre RCL.
    
    Conforme LRF (Lei Complementar 101/2000):
    - Limite total: 60% RCL (município)
    - Limite prudencial: 57% RCL (95% do limite)
    - Limite de alerta: 54% RCL (90% do limite)
    
    Args:
        despesa_pessoal: Total da despesa com pessoal
        rcl: Receita Corrente Líquida
        aplicar_limite_prudencial: Se deve usar limite prudencial
        
    Returns:
        Percentual calculado (0-100)
    """
    if rcl <= 0:
        raise ValueError("RCL deve ser positiva")
    
    percentual = (despesa_pessoal / rcl) * 100
    
    # Arredondar para 2 casas decimais
    return round(percentual, 2)

# ❌ DON'T: SQL direto
result = db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # SQL Injection!

# ✅ DO: Prepared statements
result = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
```

---

## 🧪 TESTES

### Frontend (Vitest)

```typescript
// src/__tests__/calculos.test.ts
import { describe, it, expect } from 'vitest';
import { calcularStatus } from '../utils/fiscais';

describe('Cálculos Fiscais', () => {
  it('deve classificar como regular quando < 90%', () => {
    const status = calcularStatus(45.5); // 45.5% de DP/RCL
    expect(status).toBe('regular');
  });
  
  it('deve classificar como alerta quando >= 90% e < 95%', () => {
    const status = calcularStatus(91.2);
    expect(status).toBe('alerta');
  });
  
  it('deve classificar como crítico quando >= 95%', () => {
    const status = calcularStatus(97.8);
    expect(status).toBe('critico');
  });
});
```

### Backend (pytest)

```python
# tests/test_fiscal_calculations.py
import pytest
from decimal import Decimal
from services.fiscal import calcular_percentual_dp_rcl

def test_calculo_percentual_dp_rcl_basico():
    """Testa cálculo básico do percentual DP/RCL"""
    percentual = calcular_percentual_dp_rcl(
        despesa_pessoal=100_000,
        rcl=200_000
    )
    assert percentual == 50.0

def test_calculo_com_rcl_zero_deve_falhar():
    """Testa que RCL zero levanta ValueError"""
    with pytest.raises(ValueError, match="RCL deve ser positiva"):
        calcular_percentual_dp_rcl(
            despesa_pessoal=100_000,
            rcl=0
        )

@pytest.mark.asyncio
async def test_fetch_indicators_municipio_inexistente():
    """Testa busca de município inexistente"""
    with pytest.raises(HTTPException) as exc_info:
        await fetch_indicators("9999999")
    
    assert exc_info.value.status_code == 404
```

---

## 📚 DOCUMENTAÇÃO ESSENCIAL

### Locais de Documentação por Projeto

#### orcamento-fiscal-municipios
- `docs/FONTES_DADOS.md` → Todas as fontes de dados usadas
- `docs/VOICE_HUMANIZATION_GUIDE.md` → Guia completo de TTS
- `docs/AUDITORIA_*.md` → Auditorias do sistema
- `docs/api-contracts/` → Contratos de API

#### iconsai-production
- `docs/PWA_SPECIFICATION.md` → Especificação do PWA
- `docs/PRE-DEPLOY-CHECKLIST.md` → Checklist antes de deploy

#### scraping-hub
- `README.md` → Setup e configuração
- `tests/` → Exemplos de uso

---

## 🚀 WORKFLOW DE DESENVOLVIMENTO

### 1. Entendimento do Requisito
```markdown
Antes de QUALQUER código:

1. ✅ Ler o requisito completamente
2. ✅ Criar questionário de validação:
   - O que foi compreendido?
   - Quais componentes serão afetados?
   - Existem cálculos envolvidos? (Backend!)
   - Precisa TTS? (Qual módulo?)
   - Fontes de dados? (Registrar!)
3. ✅ Aguardar confirmação do usuário
4. ✅ SÓ ENTÃO começar a implementar
```

### 2. Implementação
```markdown
Durante implementação:

1. ✅ Seguir EXATAMENTE o que foi pedido
2. ✅ NÃO mudar código não relacionado
3. ✅ Cálculos matemáticos → Python backend
4. ✅ Dados → vir de API/DB, NUNCA hardcode
5. ✅ TTS → usar presets, nunca browser voice
6. ✅ Registrar fontes de dados
```

### 3. Validação
```markdown
Antes de entregar:

1. ✅ Código compila/roda?
2. ✅ Testes passam?
3. ✅ Lint OK?
4. ✅ Fontes registradas?
5. ✅ TTS configurado (se aplicável)?
6. ✅ Documentação atualizada?
```

---

## 🔐 SEGURANÇA

### Variáveis de Ambiente

```bash
# NUNCA commitar secrets
# SEMPRE usar .env e .env.example

# .env (gitignored)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
OPENAI_API_KEY=sk-xxx
ELEVENLABS_API_KEY=xxx
DATABASE_URL=postgresql://xxx

# .env.example (versionado)
SUPABASE_URL=
SUPABASE_ANON_KEY=
OPENAI_API_KEY=
ELEVENLABS_API_KEY=
DATABASE_URL=
```

### Input Validation

```typescript
// ✅ SEMPRE validar input do usuário
import { z } from 'zod';

const UserInputSchema = z.object({
  codigoIbge: z.string().regex(/^\d{7}$/, 'Código IBGE inválido'),
  exercicio: z.number().int().min(2015).max(new Date().getFullYear())
});

async function handleUserInput(input: unknown) {
  try {
    const validated = UserInputSchema.parse(input);
    // Usar validated, não input diretamente
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ValidationError(error.errors);
    }
  }
}
```

---

## 📖 GLOSSÁRIO FISCAL (orcamento-fiscal)

- **RCL**: Receita Corrente Líquida
- **DP**: Despesa com Pessoal
- **LRF**: Lei de Responsabilidade Fiscal (LC 101/2000)
- **RREO**: Relatório Resumido da Execução Orçamentária
- **RGF**: Relatório de Gestão Fiscal
- **DCA**: Demonstrativo das Contas Anuais
- **SICONFI**: Sistema de Informações Contábeis e Fiscais
- **IBGE**: Instituto Brasileiro de Geografia e Estatística
- **Limite Prudencial**: 95% do limite total (57% para municípios)
- **Limite de Alerta**: 90% do limite total (54% para municípios)

---

## ⚠️ PROBLEMAS CONHECIDOS

### scraping-hub (PROBLEMÁTICO)
- Quebra frequente de scrapers (sites mudam)
- Falta de retry logic robusto
- Logs insuficientes para debug
- Necessita refactoring em services/

### iconsai-production
- Múltiplos módulos com lógica duplicada
- Necessita consolidação de componentes
- Performance de renderização em listas grandes

### orcamento-fiscal-municipios
- ETL massivo pode ser lento (5000+ municípios)
- Necessita cache em queries complexas
- Migrations manuais ainda necessárias

---

## 🎓 APRENDIZADO CONTÍNUO

### Após cada erro/correção:
```markdown
1. ✅ Documentar o que deu errado
2. ✅ Atualizar este CLAUDE.md com:
   - ❌ DON'T: [O que não fazer]
   - ✅ DO: [Como fazer certo]
3. ✅ Adicionar regra crítica se for caso grave
```

---

## 📞 QUANDO EM DÚVIDA

**REGRA DE OURO**: Na dúvida, PERGUNTE.

Nunca é melhor "tentar adivinhar" do que perguntar e fazer certo.

---

**Última atualização:** 08/02/2026
**Versão:** 1.0.0
**Mantenedor:** Fernando (fernando@iconsai.dev)
