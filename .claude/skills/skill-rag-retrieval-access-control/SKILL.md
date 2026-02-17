# Skill: RAG Retrieval Access Control and Filtering

Auditor de retrieval para avaliar busca vetorial/SQL e montagem de contexto com controle de acesso.

## Camada

**Camada 5** - Retrieval & Prompt Orchestration

## Quando Usar

- Servicos de busca vetorial
- Montagem de contexto para LLM
- Queries SQL para RAG

## Regras Inviolaveis

1. **Filtros Obrigatorios**: Filtros por `classification`/`tenant` obrigatorios ANTES de retornar documentos:
   ```python
   # SEMPRE filtrar por tenant e classification
   filter = {
       "tenant": user.tenant,
       "classification": {"$in": user.allowed_classifications}
   }
   ```

2. **Normalizacao de Query**: Deve existir normalizacao da query consistente:
   - `trim()` e `lowercase()`
   - Remocao de diacriticos quando aplicavel
   - Stopwords controladas

3. **Limite de Contexto**: Deve existir limite de contexto e regras de truncamento seguras:
   - Max tokens definido
   - Truncamento que nao corta no meio de sentenca
   - Priorizacao por relevancia

4. **Protecao Prompt Injection**: Deve existir protecao contra prompt injection via conteudo recuperado:
   - Delimitadores claros (`---CONTEXT START---`)
   - Instrucoes ignoradas no contexto
   - Sanitizacao de caracteres especiais

5. **Metricas**: Deve haver metricas de observabilidade:
   - Recall/Precision
   - TopK configuravel
   - Latencia
   - Taxa de fallback

## Exemplo de Implementacao Correta

```python
import unicodedata
import re
from typing import List
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

# Configuracoes
MAX_CONTEXT_TOKENS = 4000
MAX_CHUNKS = 10
CONTEXT_DELIMITER = "---DOCUMENT---"

class RetrievalConfig(BaseModel):
    top_k: int = 10
    min_score: float = 0.7
    max_tokens: int = MAX_CONTEXT_TOKENS
    rerank: bool = True

class UserContext(BaseModel):
    tenant: str
    allowed_classifications: List[str]
    user_id: str

def normalize_query(query: str) -> str:
    """Normaliza query para busca consistente"""
    # Trim
    query = query.strip()

    # Lowercase
    query = query.lower()

    # Remove diacriticos
    query = unicodedata.normalize('NFKD', query)
    query = ''.join(c for c in query if not unicodedata.combining(c))

    # Remove caracteres especiais perigosos
    query = re.sub(r'[<>{}[\]\\]', '', query)

    # Remove multiplos espacos
    query = re.sub(r'\s+', ' ', query)

    return query

def sanitize_context(text: str) -> str:
    """Sanitiza conteudo recuperado para prevenir injection"""
    # Remove instrucoes que parecem prompts
    dangerous_patterns = [
        r'ignore previous instructions',
        r'disregard above',
        r'system:',
        r'assistant:',
        r'user:',
    ]
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '[REDACTED]', text, flags=re.IGNORECASE)

    # Escapa delimitadores
    text = text.replace(CONTEXT_DELIMITER, '[DELIMITER]')

    return text

async def retrieve_context(
    query: str,
    user: UserContext,
    config: RetrievalConfig,
    request_id: str
) -> dict:
    log = logger.bind(request_id=request_id, user_id=user.user_id)

    # 1. Normalizar query
    normalized_query = normalize_query(query)
    log.info("Query normalizada", original_len=len(query), normalized_len=len(normalized_query))

    # 2. Gerar embedding da query
    query_embedding = await generate_embedding(normalized_query)

    # 3. Buscar com FILTROS OBRIGATORIOS
    search_filter = {
        "tenant": {"$eq": user.tenant},
        "classification": {"$in": user.allowed_classifications}
    }

    results = await vector_store.search(
        embedding=query_embedding,
        filter=search_filter,
        top_k=config.top_k,
        min_score=config.min_score
    )

    log.info("Busca executada",
        results_count=len(results),
        filter_tenant=user.tenant,
        filter_classifications=user.allowed_classifications
    )

    # 4. Rerank se habilitado
    if config.rerank and results:
        results = await reranker.rerank(normalized_query, results)

    # 5. Montar contexto com limite de tokens
    context_parts = []
    total_tokens = 0

    for i, result in enumerate(results[:MAX_CHUNKS]):
        chunk_text = result['content']
        chunk_tokens = count_tokens(chunk_text)

        if total_tokens + chunk_tokens > config.max_tokens:
            # Truncar ultimo chunk se necessario
            remaining = config.max_tokens - total_tokens
            chunk_text = truncate_to_tokens(chunk_text, remaining)
            chunk_tokens = remaining

        # Sanitizar conteudo
        sanitized = sanitize_context(chunk_text)

        context_parts.append(f"{CONTEXT_DELIMITER}\nSource: {result['metadata']['source']}\n{sanitized}")
        total_tokens += chunk_tokens

        if total_tokens >= config.max_tokens:
            break

    context = "\n\n".join(context_parts)

    # 6. Metricas
    metrics = {
        "query_length": len(normalized_query),
        "results_found": len(results),
        "results_used": len(context_parts),
        "total_tokens": total_tokens,
        "latency_ms": timer.elapsed_ms()
    }

    log.info("Contexto montado", **metrics)

    return {
        "context": context,
        "sources": [r['metadata']['source'] for r in results[:len(context_parts)]],
        "metrics": metrics
    }
```

## Checklist de Auditoria

- [ ] Filtro por `tenant` aplicado ANTES da busca
- [ ] Filtro por `classification` aplicado ANTES da busca
- [ ] Query normalizada (trim, lowercase, diacriticos)
- [ ] Caracteres perigosos removidos da query
- [ ] Limite de tokens/chunks definido
- [ ] Truncamento seguro implementado
- [ ] Conteudo sanitizado contra prompt injection
- [ ] Delimitadores claros no contexto
- [ ] Metricas de observabilidade (latencia, recall, topK)

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
