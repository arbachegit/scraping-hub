# Skill: MCP Tool Contract and Guardrails

Auditor de MCP/tooling para avaliar contrato, seguranca e rastreabilidade de ferramentas MCP.

## Camada

**Camada 3** - MCPs (ferramentas/agents)

## Quando Usar

- Scripts de MCP servers
- Ferramentas para LLM agents
- Qualquer tool que sera chamado por IA

## Regras Inviolaveis

1. **Schema Formal**: Input do tool tem schema formal (Zod/JSON Schema/Pydantic) e versao:
   ```python
   inputSchema = {
       "type": "object",
       "properties": {...},
       "required": [...],
       "$version": "1.0.0"
   }
   ```

2. **Allowlist de Recursos**: O tool NAO pode acessar filesystem/rede fora de allowlist explicita:
   ```python
   ALLOWED_PATHS = ["/opt/app/data", "/tmp/cache"]
   ALLOWED_HOSTS = ["api.exemplo.com", "supabase.co"]
   ```

3. **Sem Segredos em Runtime**: Proibir qualquer leitura de segredos em runtime (env/arquivos) exceto via mecanismo aprovado:
   - Segredos via Secret Manager
   - Nunca logar segredos

4. **Timeouts e Retry**: Deve haver timeouts/retries/backoff em chamadas externas:
   ```python
   timeout = 30  # segundos
   max_retries = 3
   backoff_factor = 2
   ```

5. **Observabilidade**: Logs devem incluir `request_id`/`trace_id` e NAO conter PII/segredos.

6. **Validacao de Saida**: Saida do tool deve ser validada antes de retornar ao LLM.

## Exemplo de Implementacao Correta

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field
import httpx
import structlog

logger = structlog.get_logger()

# Allowlists explicitas
ALLOWED_HOSTS = ["api.brasilapi.com.br", "supabase.co"]
ALLOWED_PATHS = ["/opt/app/data"]

# Schema de input versionado
class SearchCompanyInput(BaseModel):
    """Schema v1.0.0 para busca de empresa"""
    nome: str = Field(..., min_length=2, max_length=200)
    cidade: str | None = Field(None, max_length=100)

    class Config:
        extra = "forbid"

# Schema de output
class SearchCompanyOutput(BaseModel):
    empresas: list[dict]
    total: int
    source: str

server = Server("company-search")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_company",
            description="Busca empresas por nome",
            inputSchema=SearchCompanyInput.model_json_schema()
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict, request_id: str = None):
    # Bind request_id para rastreabilidade
    log = logger.bind(request_id=request_id, tool=name)

    if name == "search_company":
        try:
            # Validar input
            input_data = SearchCompanyInput(**arguments)
            log.info("Tool chamado", nome=input_data.nome[:20])  # Trunca para log

            # Verificar host na allowlist
            host = "api.brasilapi.com.br"
            if host not in ALLOWED_HOSTS:
                raise ValueError(f"Host nao permitido: {host}")

            # Chamada com timeout e retry
            async with httpx.AsyncClient(timeout=30.0) as client:
                for attempt in range(3):
                    try:
                        response = await client.get(
                            f"https://{host}/api/cnpj/v1/search",
                            params={"nome": input_data.nome}
                        )
                        response.raise_for_status()
                        break
                    except httpx.TimeoutException:
                        if attempt == 2:
                            raise
                        await asyncio.sleep(2 ** attempt)  # Backoff

            data = response.json()

            # Validar output antes de retornar
            output = SearchCompanyOutput(
                empresas=data.get("empresas", []),
                total=len(data.get("empresas", [])),
                source="brasilapi"
            )

            log.info("Tool concluido", total=output.total)

            return [TextContent(
                type="text",
                text=output.model_dump_json()
            )]

        except Exception as e:
            log.error("Tool falhou", error=str(e))
            raise
```

## Checklist de Auditoria

- [ ] Input tem schema formal com versao
- [ ] Output tem schema de validacao
- [ ] Allowlist de hosts/paths definida
- [ ] Sem leitura de segredos fora de mecanismo aprovado
- [ ] Timeout configurado em chamadas externas
- [ ] Retry com backoff implementado
- [ ] Logs incluem request_id/trace_id
- [ ] Logs nao contem PII/segredos
- [ ] Saida validada antes de retornar

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
