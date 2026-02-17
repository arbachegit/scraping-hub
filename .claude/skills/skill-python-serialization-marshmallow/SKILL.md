# Skill: Python Serialization (Marshmallow)

Revisor Python focado em Marshmallow para verificar se schemas sao completos e consistentes quando Pydantic nao for usado.

## Camada

**Camada 2** - Servicos de Dominio (Python)

## Quando Usar

- Projetos Python que usam Marshmallow
- Serializacao/deserializacao de dados
- Validacao quando Pydantic nao esta disponivel

## Regras Inviolaveis

1. **Schema Completo**: Schemas Marshmallow definem:
   - `required=True` para campos obrigatorios
   - `validate` para constraints
   - `unknown=EXCLUDE` ou `unknown=RAISE` conforme politica

2. **Normalizacao Explicita**: Normalizacao explicita em:
   - `@pre_load` para input
   - `@post_load` para transformacao final
   - `@post_dump` para output

3. **Erros Padronizados**: Erros seguros e padronizados, sem expor internals.

4. **Centralizacao**: Nao misturar validacao espalhada no codigo (centralizar nos schemas).

## Exemplo de Implementacao Correta

```python
from marshmallow import Schema, fields, validate, pre_load, post_load, EXCLUDE, RAISE
import re

class SearchCompanySchema(Schema):
    """Schema para busca de empresas"""

    class Meta:
        unknown = RAISE  # Rejeita campos extras

    nome = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=200),
        metadata={"description": "Nome da empresa"}
    )
    cidade = fields.Str(
        load_default=None,
        validate=validate.Length(max=100)
    )
    cnpj = fields.Str(
        load_default=None,
        validate=validate.Regexp(r'^\d{14}$', error="CNPJ deve ter 14 digitos")
    )
    regime = fields.Str(
        load_default=None,
        validate=validate.OneOf([
            "MEI", "SIMPLES_NACIONAL", "LUCRO_PRESUMIDO", "LUCRO_REAL"
        ])
    )

    @pre_load
    def normalize_input(self, data, **kwargs):
        """Normaliza dados antes da validacao"""
        if 'nome' in data and data['nome']:
            data['nome'] = data['nome'].strip()

        if 'cidade' in data and data['cidade']:
            data['cidade'] = data['cidade'].strip().lower()

        if 'cnpj' in data and data['cnpj']:
            # Remove formatacao
            data['cnpj'] = re.sub(r'[^\d]', '', data['cnpj'])

        return data

    @post_load
    def create_object(self, data, **kwargs):
        """Transforma em objeto de dominio"""
        return SearchCompanyRequest(**data)


# Uso em Flask
from flask import Flask, request, jsonify
from marshmallow import ValidationError

app = Flask(__name__)
search_schema = SearchCompanySchema()

@app.route('/companies/search', methods=['POST'])
def search_companies():
    try:
        # Valida e normaliza
        data = search_schema.load(request.json)
        result = service.search(data)
        return jsonify({"success": True, "data": result})

    except ValidationError as err:
        return jsonify({
            "success": False,
            "error": "Dados invalidos",
            "details": err.messages
        }), 400


# Response Schema
class CompanyResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.UUID(required=True)
    razao_social = fields.Str(required=True)
    cnpj = fields.Str(required=True)
    cidade = fields.Str()

    @post_dump
    def mask_sensitive(self, data, **kwargs):
        """Mascara dados sensiveis na saida"""
        if 'cnpj' in data:
            data['cnpj_masked'] = f"***{data['cnpj'][-4:]}"
        return data
```

## Checklist de Auditoria

- [ ] Todos os campos tem tipo definido
- [ ] `required=True` em campos obrigatorios
- [ ] `validate` com constraints apropriados
- [ ] `unknown=RAISE` ou `EXCLUDE` configurado
- [ ] `@pre_load` para normalizacao de input
- [ ] `@post_load` para criacao de objetos
- [ ] `@post_dump` para formatacao de output
- [ ] Erros tratados sem expor internals
- [ ] Validacao centralizada nos schemas

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
