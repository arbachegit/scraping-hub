# Skill: LLM Prompt Template Versioning and Safety

Auditor de prompts institucionais para avaliar prompt templates e orquestracao do LLM.

## Camada

**Camada 6** - LLM Runtime

## Quando Usar

- Prompt templates para LLM
- Orquestracao de chamadas LLM
- System prompts e user prompts

## Regras Inviolaveis

1. **Versionamento Obrigatorio**: Prompt template e versionado e rastreavel:
   ```python
   PROMPT_VERSION = "1.2.0"
   # Log inclui versao em cada execucao
   ```

2. **Minimizacao de PII**: Nao inserir PII desnecessario no prompt:
   - Apenas dados necessarios para a tarefa
   - Preferir IDs a nomes completos quando possivel

3. **Separacao Clara**: Instrucoes de sistema/politicas separadas de contexto RAG:
   ```
   [SYSTEM INSTRUCTIONS]
   ...
   [END SYSTEM]

   [CONTEXT START]
   {rag_context}
   [CONTEXT END]

   [USER QUERY]
   {user_query}
   ```

4. **Allowlist de Tools**: Ferramentas (tools) so podem ser chamadas via allowlist e com schema.

5. **Logging Seguro**: Logging do prompt deve ser redigido/mascarado conforme classificacao.

## Exemplo de Implementacao Correta

```python
from pydantic import BaseModel
from typing import List, Optional
import structlog
import hashlib

logger = structlog.get_logger()

# Versionamento de prompts
PROMPT_VERSION = "1.3.0"
PROMPT_HASH = None  # Calculado no startup

class PromptConfig(BaseModel):
    version: str
    hash: str
    max_tokens: int
    temperature: float
    allowed_tools: List[str]

class PromptTemplate:
    """Template de prompt versionado e seguro"""

    VERSION = "1.3.0"

    SYSTEM_TEMPLATE = """[SYSTEM INSTRUCTIONS - v{version}]
Voce e um assistente especializado em analise de empresas brasileiras.

REGRAS:
1. Responda apenas com base no contexto fornecido
2. Se nao souber, diga "Nao tenho essa informacao no contexto"
3. Nunca invente dados de CNPJ, faturamento ou socios
4. Cite a fonte quando possivel

FERRAMENTAS PERMITIDAS: {allowed_tools}
[END SYSTEM]"""

    CONTEXT_TEMPLATE = """[CONTEXT START]
{context}
[CONTEXT END]"""

    USER_TEMPLATE = """[USER QUERY]
{query}
[END QUERY]"""

    @classmethod
    def get_hash(cls) -> str:
        """Hash do template para rastreabilidade"""
        content = cls.SYSTEM_TEMPLATE + cls.CONTEXT_TEMPLATE + cls.USER_TEMPLATE
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    @classmethod
    def build(
        cls,
        query: str,
        context: str,
        allowed_tools: List[str],
        request_id: str
    ) -> dict:
        log = logger.bind(request_id=request_id)

        # Sanitizar query (remover tentativas de injection)
        safe_query = cls._sanitize_user_input(query)

        # Montar prompt com delimitadores claros
        system = cls.SYSTEM_TEMPLATE.format(
            version=cls.VERSION,
            allowed_tools=", ".join(allowed_tools) if allowed_tools else "Nenhuma"
        )

        context_block = cls.CONTEXT_TEMPLATE.format(context=context)
        user_block = cls.USER_TEMPLATE.format(query=safe_query)

        full_prompt = f"{system}\n\n{context_block}\n\n{user_block}"

        # Log seguro (sem conteudo completo)
        log.info("Prompt construido",
            prompt_version=cls.VERSION,
            prompt_hash=cls.get_hash(),
            context_length=len(context),
            query_length=len(safe_query),
            tools_count=len(allowed_tools)
            # NAO logar conteudo do prompt
        )

        return {
            "prompt": full_prompt,
            "metadata": {
                "prompt_version": cls.VERSION,
                "prompt_hash": cls.get_hash(),
                "allowed_tools": allowed_tools
            }
        }

    @staticmethod
    def _sanitize_user_input(text: str) -> str:
        """Remove tentativas de injection do input do usuario"""
        # Remove padroes perigosos
        dangerous = [
            r'\[SYSTEM',
            r'\[END SYSTEM',
            r'\[CONTEXT',
            r'ignore previous',
            r'disregard instructions',
        ]
        import re
        for pattern in dangerous:
            text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)
        return text


# Allowlist de tools
ALLOWED_TOOLS = {
    "search_company": {
        "description": "Busca empresas por nome",
        "schema": {...}
    },
    "get_cnpj_data": {
        "description": "Consulta dados de CNPJ",
        "schema": {...}
    }
}

async def call_llm(
    query: str,
    context: str,
    tools: List[str],
    request_id: str
):
    log = logger.bind(request_id=request_id)

    # Validar tools contra allowlist
    valid_tools = [t for t in tools if t in ALLOWED_TOOLS]
    if len(valid_tools) != len(tools):
        invalid = set(tools) - set(valid_tools)
        log.warning("Tools invalidos removidos", invalid_tools=list(invalid))

    # Construir prompt
    prompt_data = PromptTemplate.build(
        query=query,
        context=context,
        allowed_tools=valid_tools,
        request_id=request_id
    )

    # Chamar LLM
    response = await llm_client.chat(
        messages=[{"role": "user", "content": prompt_data["prompt"]}],
        tools=[ALLOWED_TOOLS[t] for t in valid_tools] if valid_tools else None,
        max_tokens=4096,
        temperature=0.2
    )

    # Log da resposta (sem conteudo sensivel)
    log.info("LLM respondeu",
        prompt_version=prompt_data["metadata"]["prompt_version"],
        response_tokens=response.usage.completion_tokens,
        tools_called=[t.name for t in response.tool_calls] if response.tool_calls else []
    )

    return response
```

## Checklist de Auditoria

- [ ] Prompt template tem `VERSION` explicita
- [ ] Hash do template calculado para rastreabilidade
- [ ] Log inclui `prompt_version` e `prompt_hash`
- [ ] PII minimizado no prompt
- [ ] Delimitadores claros entre SYSTEM, CONTEXT e USER
- [ ] Input do usuario sanitizado
- [ ] Tools validados contra allowlist
- [ ] Tools tem schema definido
- [ ] Logging nao expoe conteudo sensivel do prompt/resposta

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
