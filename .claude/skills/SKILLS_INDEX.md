# Skills de Governanca ISO 27001/27701

Catalogo de skills para auditoria de codigo seguindo padroes institucionais de normalizacao e governanca.

## Mapa de Aplicacao: Qual Skill Usar

| Tipo de Arquivo | Skills Aplicaveis |
|-----------------|-------------------|
| Rotas/Controllers Node | `skill-api-request-normalization-node-zod`, `skill-sanitization-strings-validatorjs` |
| Gateway/Contratos | `skill-contract-validation-jsonschema-ajv` |
| NestJS DTOs | `skill-dto-validation-nest-classvalidator` |
| FastAPI/Flask endpoints | `skill-python-input-normalization-pydantic` |
| Flask com Marshmallow | `skill-python-serialization-marshmallow` |
| MCP scripts | `skill-mcp-tool-contract-guardrails` |
| Ingestion pipeline | `skill-rag-ingestion-data-lineage-pii` |
| Retrieval/busca | `skill-rag-retrieval-access-control` |
| Prompt orchestration | `skill-llm-prompt-template-versioning` |
| Codigo Node/TS | `skill-node-code-quality-eslint-prettier` |
| Codigo Python | `skill-python-code-quality-ruff-black` |
| Dependencias | `skill-dependency-governance-lockfiles-sbom` |
| IDs/Slugs/Codigos | `skill-normalize-identifiers-uuid-slug` |
| CPF/CNPJ/IBGE/CEP | `skill-normalize-brazilian-codes` |
| Docker/Compose | `skill-docker-compose-prod-immutability` |

## Skills por Camada

### Camada 1 - Entrada/API Gateway
1. **skill-api-request-normalization-node-zod** - Validacao Zod em Node
2. **skill-contract-validation-jsonschema-ajv** - Contratos JSON Schema + Ajv
3. **skill-sanitization-strings-validatorjs** - Sanitizacao com validator.js

### Camada 2 - Servicos de Dominio
4. **skill-dto-validation-nest-classvalidator** - DTOs NestJS
5. **skill-python-input-normalization-pydantic** - Pydantic em Python
6. **skill-python-serialization-marshmallow** - Marshmallow em Python

### Camada 3 - MCPs (ferramentas/agents)
7. **skill-mcp-tool-contract-guardrails** - Contratos e guardrails MCP

### Camada 4 - RAG Ingestion
8. **skill-rag-ingestion-data-lineage-pii** - Data lineage e PII handling

### Camada 5 - Retrieval & Prompt
9. **skill-rag-retrieval-access-control** - Controle de acesso no retrieval
10. **skill-llm-prompt-template-versioning** - Versionamento de prompts

### Camada 8 - CI/CD e Supply Chain
11. **skill-node-code-quality-eslint-prettier** - Qualidade Node/TS
12. **skill-python-code-quality-ruff-black** - Qualidade Python
13. **skill-dependency-governance-lockfiles-sbom** - Governanca de dependencias
14. **skill-docker-compose-prod-immutability** - Docker imutavel

### Normalizacao de Codigos
15. **skill-normalize-identifiers-uuid-slug** - UUID, Slug, Codigos
16. **skill-normalize-brazilian-codes** - CPF, CNPJ, IBGE, CEP

## Como Usar

### No Claude Code
```
/skill-api-request-normalization-node-zod
```

### Auditoria Manual
1. Identifique o tipo de arquivo
2. Consulte a tabela acima
3. Execute a skill correspondente
4. Verifique PASS/FAIL
5. Aplique correcoes se necessario

### Integracao com CI
```yaml
# .github/workflows/audit.yml
- name: Audit Node Routes
  run: |
    for file in backend/src/routes/*.js; do
      claude-code audit "$file" --skill skill-api-request-normalization-node-zod
    done
```

## Padrao de Saida

Todas as skills retornam:

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```

## Principios ISO 27001/27701

Todas as skills seguem:

1. **Controle de segredos**: Nunca hardcode
2. **Telemetria segura**: Logs sem PII
3. **Classificacao de dados**: Publico/Interno/Confidencial/Sensivel
4. **Minimizacao**: Coletar/reter/acessar o minimo
5. **Rastreabilidade**: Versao em tudo (git SHA, schema version)
