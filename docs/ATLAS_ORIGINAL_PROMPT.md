Implement the following plan:

# Atlas Agent Implementation Plan

## Overview
Implement "Atlas: Agente Inteligente de Consulta" - a conversational AI agent for querying Brazilian political and fiscal data.

## Architecture

```
POST /api/atlas/chat
        │
        ▼
┌─────────────────┐
│  Orchestrator   │ ← Entry point, coordinates all components
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│ Intent │ │   Context    │
│ Parser │ │   Manager    │
└────┬───┘ └──────┬───────┘
     │            │
     └─────┬──────┘
           ▼
    ┌─────────────┐
    │   Query     │
    │   Builder   │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Supabase   │ ← dim_politicos, fato_politicos_mandatos
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Response   │
    │  Formatter  │ ← LLM-powered natural language
    └─────────────┘
```

## Files to Create

### 1. `backend/src/atlas/orchestrator.js`
Main coordinator that:
- Receives chat messages
- Manages session context
- Coordinates intent → query → response flow
- Returns structured response

### 2. `backend/src/atlas/intent-parser.js`
Parses user messages to extract:
- Intent type: `search_politician`, `details`, `by_party`, `by_municipality`, `statistics`
- Entities: politician names, party acronyms, IBGE codes, years
- Uses pattern matching first, LLM fallback for complex queries

### 3. `backend/src/atlas/query-builder.js`
Builds Supabase queries based on parsed intent:
- Maps intents to database operations
- Handles joins between dim_politicos and fato_politicos_mandatos
- Applies filters (partido, cargo, ano_eleicao, municipio)

### 4. `backend/src/atlas/context-manager.js`
Manages conversational context:
- Session storage (in-memory with TTL)
- Entity resolution ("ele", "esse político" → previous result)
- Conversation history for follow-up questions

### 5. `backend/src/atlas/response-formatter.js`
Formats data as natural language:
- Uses LLM to generate conversational responses
- Includes relevant data points
- Handles error cases gracefully

### 6. `backend/src/atlas/llm-service.js`
LLM integration:
- Primary: Claude API (Anthropic)
- Fallback: OpenAI GPT-4
- Configurable via environment variables

### 7. `backend/src/atlas/prompts/system.js`
System prompts for Atlas personality:
- Brazilian Portuguese
- Expert in political data
- Concise but informative responses

### 8. `backend/src/routes/atlas.js`
Express router with endpoints:
- `POST /api/atlas/chat` - Main conversation endpoint
- `POST /api/atlas/session/clear` - Clear session context

### 9. `backend/src/validation/schemas.js` (update)
Add Zod schemas:
- `atlasChatSchema` - Chat request validation
- `atlasClearSessionSchema` - Session clear validation

## Implementation Details

### Intent Types
```javascript
const INTENTS = {
  SEARCH_POLITICIAN: 'search_politician',    // "Quem é Lula?"
  POLITICIAN_DETAILS: 'politician_details',  // "Detalhes do político X"
  BY_PARTY: 'by_party',                      // "Políticos do PT"
  BY_MUNICIPALITY: 'by_municipality',        // "Vereadores de São Paulo"
  STATISTICS: 'statistics',                  // "Quantos políticos do PSDB?"
  PARTY_LIST: 'party_list',                  // "Quais partidos existem?"
  GENERAL: 'general'                         // Fallback
};
```

### Entity Extraction Patterns
```javascript
// Examples
"políticos do PT" → { party: 'PT' }
"vereadores de São Paulo" → { cargo: 'VEREADOR', municipio: 'São Paulo' }
"eleitos em 2024" → { ano_eleicao: 2024, eleito: true }
"quem é Jair Bolsonaro" → { nome: 'Jair Bolsonaro' }
```

### Session Context Structure
```javascript
{
  sessionId: "uuid",
  lastQuery: { intent, entities, results },
  conversationHistory: [
    { role: "user", content: "..." },
    { role: "assistant", content: "..." }
  ],
  resolvedEntities: {
    currentPolitician: { id, nome, ... }
  },
  createdAt: Date,
  lastActivity: Date
}
```

### API Response Format
```javascript
{
  success: true,
  sessionId: "uuid",
  response: {
    text: "Natural language response",
    data: { /* structured data */ },
    suggestions: ["Pergunta sugerida 1", "Pergunta sugerida 2"]
  },
  metadata: {
    intent: "search_politician",
    entities: { nome: "Lula" },
    processingTime: 245
  }
}
```

## Environment Variables
```bash
# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...     # Primary (Claude)
OPENAI_API_KEY=sk-...            # Fallback (GPT-4)
ATLAS_LLM_PROVIDER=anthropic     # 'anthropic' or 'openai'
ATLAS_SESSION_TTL=1800           # Session timeout in seconds (30 min)
```

## Integration Points

### Existing Services to Reuse
- `backend/src/database/supabase.js` - Database client (brasilDataHub)
- `backend/src/utils/logger.js` - Structured logging
- `backend/src/validation/schemas.js` - Zod validation patterns

### Database Tables Used
- `dim_politicos` - Politician dimension (id, nome_completo, nome_urna, sexo, ocupacao)
- `fato_politicos_mandatos` - Mandates fact (politico_id, cargo, partido_sigla, municipio, ano_eleicao)

## Verification Steps

1. **Unit test intent parser:**
   ```bash
   node -e "
   const { parseIntent } = require('./backend/src/atlas/intent-parser.js');
   console.log(parseIntent('Quem é Lula?'));
   // Expected: { intent: 'search_politician', entities: { nome: 'Lula' } }
   "
   ```

2. **Test API endpoint:**
   ```bash
   curl -X POST http://localhost:3001/api/atlas/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Quem é Lula?", "sessionId": null}'
   ```

3. **Test conversation context:**
   ```bash
   # First request
   curl -X POST http://localhost:3001/api/atlas/chat \
     -d '{"message": "Políticos do PT"}'

   # Follow-up using session
   curl -X POST http://localhost:3001/api/atlas/chat \
     -d '{"message": "Quantos foram eleitos em 2024?", "sessionId": "..."}'
   ```

4. **Verify in production:**
   ```bash
   curl -X POST https://scraping.iconsai.ai/api/atlas/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Liste os partidos com mais políticos"}'
   ```

## Implementation Order

1. Create `backend/src/atlas/` directory
2. Implement `intent-parser.js` (pattern matching, no LLM yet)
3. Implement `query-builder.js` (Supabase queries)
4. Implement `context-manager.js` (session storage)
5. Implement `llm-service.js` (Claude/OpenAI integration)
6. Implement `response-formatter.js` (LLM response generation)
7. Implement `orchestrator.js` (coordination)
8. Add validation schemas to `schemas.js`
9. Create `routes/atlas.js` and register in `index.js`
10. Test locally
11. Deploy and verify
