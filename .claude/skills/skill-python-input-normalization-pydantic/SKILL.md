# Skill: Python Input Normalization (Pydantic)

Revisor Python para avaliar normalizacao e validacao com Pydantic para inputs externos.

## Camada

**Camada 2** - Servicos de Dominio (Python)

## Quando Usar

- Endpoints FastAPI/Flask
- Qualquer codigo Python que receba input externo
- Models de dados

## Regras Inviolaveis

1. **Model Obrigatorio**: Todo input externo vira um model Pydantic.

2. **Validacao Completa**: Deve existir validacao de:
   - Tipos (str, int, float, bool, etc.)
   - Constraints (`min_length`, `max_length`, `ge`, `le`)
   - Patterns (regex via `pattern`)
   - Enums para valores restritos

3. **Normalizacao via Validators**: Normalizacao deve ser feita via:
   - `@field_validator` (mode='before' ou 'after')
   - `@model_validator`
   - Field serializers

4. **Erros Seguros**: Erros devem ser tratados sem vazar dados sensiveis.

5. **Versionamento**: Model versioning deve existir se contrato mudar de forma breaking.

## Exemplo de Implementacao Correta

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from enum import Enum
import re

class RegimeTributario(str, Enum):
    MEI = "MEI"
    SIMPLES_NACIONAL = "SIMPLES_NACIONAL"
    LUCRO_PRESUMIDO = "LUCRO_PRESUMIDO"
    LUCRO_REAL = "LUCRO_REAL"

class SearchCompanyRequest(BaseModel):
    """Schema v1 para busca de empresas"""

    nome: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Nome da empresa para busca"
    )
    cidade: Optional[str] = Field(
        None,
        max_length=100,
        description="Cidade para filtrar"
    )
    cnpj: Optional[str] = Field(
        None,
        pattern=r"^\d{14}$",
        description="CNPJ sem formatacao"
    )
    regime: Optional[RegimeTributario] = None

    model_config = {
        "str_strip_whitespace": True,  # Trim automatico
        "extra": "forbid",  # Rejeita campos extras
        "json_schema_extra": {
            "examples": [
                {"nome": "Empresa Exemplo", "cidade": "Sao Paulo"}
            ]
        }
    }

    @field_validator('nome', 'cidade', mode='before')
    @classmethod
    def normalize_string(cls, v: str) -> str:
        if v is None:
            return v
        return v.strip()

    @field_validator('cnpj', mode='before')
    @classmethod
    def normalize_cnpj(cls, v: str) -> str:
        if v is None:
            return v
        # Remove formatacao
        return re.sub(r'[^\d]', '', v)

    @field_validator('cidade', mode='after')
    @classmethod
    def lowercase_cidade(cls, v: str) -> str:
        if v is None:
            return v
        return v.lower()

# Uso no FastAPI
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

app = FastAPI()

@app.post("/companies/search")
async def search_companies(request: SearchCompanyRequest):
    # request ja validado e normalizado pelo Pydantic
    return await service.search(request)

# Handler de erros customizado
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "Dados invalidos",
            "details": [
                {"field": e["loc"], "message": e["msg"]}
                for e in exc.errors()
            ]
        }
    )
```

## Checklist de Auditoria

- [ ] Todo input externo usa model Pydantic
- [ ] Tipos definidos para todos os campos
- [ ] Constraints (min/max/pattern) aplicados
- [ ] Normalizacao via `@field_validator`
- [ ] `str_strip_whitespace: True` no config
- [ ] `extra: "forbid"` em models criticos
- [ ] Erros 400 sem expor internals
- [ ] Versao do schema documentada

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
