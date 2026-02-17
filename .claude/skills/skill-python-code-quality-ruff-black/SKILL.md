# Skill: Python Code Quality (Ruff + Black)

Auditor de qualidade Python focado em Ruff, Black e boas praticas.

## Camada

**Camada 8** - CI/CD e Supply Chain

## Quando Usar

- Codigo Python
- Revisao de qualidade de codigo
- Pre-merge checks

## Regras Inviolaveis

1. **Black Format**: Black format aplicado:
   - Configuracao em `pyproject.toml`
   - Linha maxima de 100 caracteres
   - Pre-commit hook ou CI check

2. **Ruff Limpo**: Ruff sem issues criticas:
   - Todas as regras de seguranca habilitadas
   - Sem `# noqa` sem justificativa

3. **Tipagem Minima**: Tipagem (`typing`) em interfaces publicas:
   - Funcoes publicas com type hints
   - Classes com atributos tipados
   - Return types explicitos

4. **Tratamento de Erros**: Exceptions tratadas em IO:
   - `try/except` em operacoes de rede/arquivo
   - Timeouts obrigatorios em chamadas de rede
   - Logging de erros com contexto

5. **Logs Seguros**: Logs sem PII/segredos:
   - Usar `structlog` ou similar
   - Mascarar dados sensiveis

## Exemplo de Configuracao

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "S",    # flake8-bandit (security)
    "T20",  # flake8-print
    "SIM",  # flake8-simplify
    "ARG",  # flake8-unused-arguments
    "PTH",  # flake8-use-pathlib
]
ignore = [
    "E501",  # line too long (handled by black)
]

[tool.ruff.per-file-ignores]
"tests/*" = ["S101"]  # allow assert in tests

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
```

## Exemplo de Codigo Correto

```python
# services/company_service.py
from typing import Optional
import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

# Constantes
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3


class SearchParams(BaseModel):
    nome: str
    cidade: Optional[str] = None


class Company(BaseModel):
    id: str
    razao_social: str
    cnpj: str


async def search_companies(
    params: SearchParams,
    request_id: str
) -> list[Company]:
    """
    Busca empresas por nome.

    Args:
        params: Parametros de busca
        request_id: ID para rastreabilidade

    Returns:
        Lista de empresas encontradas

    Raises:
        ServiceError: Se falhar a busca
    """
    log = logger.bind(request_id=request_id)

    # Log seguro (sem dados sensiveis)
    log.info(
        "Buscando empresas",
        termo_length=len(params.nome),
        cidade=params.cidade or "todas"
    )

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(
                        "https://api.example.com/companies",
                        params={"nome": params.nome, "cidade": params.cidade}
                    )
                    response.raise_for_status()
                    break
                except httpx.TimeoutException:
                    if attempt == MAX_RETRIES - 1:
                        raise
                    log.warning("Timeout, tentando novamente", attempt=attempt + 1)
                    await asyncio.sleep(2 ** attempt)

        data = response.json()
        companies = [Company(**c) for c in data.get("companies", [])]

        log.info("Busca concluida", count=len(companies))

        return companies

    except httpx.HTTPStatusError as e:
        log.error(
            "Erro HTTP na busca",
            status_code=e.response.status_code,
            # NAO logar response.text (pode conter dados sensiveis)
        )
        raise ServiceError("Falha ao buscar empresas") from e

    except Exception as e:
        log.error(
            "Erro inesperado na busca",
            error_type=type(e).__name__,
            error_msg=str(e)
        )
        raise ServiceError("Falha ao buscar empresas") from e


# NAO fazer:
# def bad(params):  # sem tipos
#     print(params)  # print ao inves de logger
#     response = requests.get(url)  # sem timeout
#     return response.json()  # sem tratamento de erro
```

## Checklist de Auditoria

- [ ] Black format aplicado
- [ ] Ruff sem erros ou issues criticas
- [ ] Sem `# noqa` sem justificativa
- [ ] Type hints em funcoes publicas
- [ ] Return types explicitos
- [ ] `try/except` em operacoes de IO
- [ ] Timeout em chamadas de rede
- [ ] Retry com backoff em operacoes criticas
- [ ] Logger estruturado (nao print)
- [ ] Dados sensiveis mascarados nos logs

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
