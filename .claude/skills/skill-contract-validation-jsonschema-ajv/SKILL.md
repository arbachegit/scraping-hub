# Skill: Contract Validation (JSON Schema + Ajv)

Auditor de contratos API para verificar validacao e publicacao de contratos formais via JSON Schema/OpenAPI com Ajv no gateway/borda.

## Camada

**Camada 1** - Entrada/API Gateway

## Quando Usar

- Gateway/contratos de API
- Servicos que expoe APIs publicas
- Integracao entre microservicos

## Regras Inviolaveis

1. **Schema Versionado**: Existe JSON Schema versionado para requests e responses (ex.: `/schemas/v1/...`).

2. **Validacao Ajv**: Ajv valida request/response (ou ao menos request) antes de executar logica.

3. **Definicoes Completas**: Schema deve definir:
   - `required` para campos obrigatorios
   - `type` para todos os campos
   - `format` para strings especiais (email, uri, date-time)
   - `minimum/maximum` para numeros
   - `minLength/maxLength` para strings
   - `enum` para valores restritos

4. **Sem additionalProperties**: Nao aceitar `additionalProperties: true` em objetos criticos (ou justificar explicitamente).

5. **Documentacao**: O schema deve incluir `examples` e `description` para governanca.

6. **Versionamento Breaking**: Mudanca de schema exige bump de versao (v1->v2) se breaking.

## Exemplo de Implementacao Correta

```javascript
// schemas/v1/company-search.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "schemas/v1/company-search-request",
  "type": "object",
  "required": ["nome"],
  "additionalProperties": false,
  "properties": {
    "nome": {
      "type": "string",
      "minLength": 2,
      "maxLength": 200,
      "description": "Nome da empresa para busca"
    },
    "cidade": {
      "type": "string",
      "maxLength": 100,
      "description": "Cidade para filtrar resultados"
    },
    "cnpj": {
      "type": "string",
      "pattern": "^[0-9]{14}$",
      "description": "CNPJ sem formatacao (14 digitos)"
    }
  },
  "examples": [
    { "nome": "Empresa Exemplo", "cidade": "Sao Paulo" }
  ]
}

// Validacao com Ajv
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);

const validateRequest = ajv.compile(schema);

function validateMiddleware(req, res, next) {
  const valid = validateRequest(req.body);
  if (!valid) {
    return res.status(400).json({
      success: false,
      error: 'Contrato invalido',
      details: validateRequest.errors
    });
  }
  next();
}
```

## Checklist de Auditoria

- [ ] JSON Schema existe e esta versionado
- [ ] Ajv valida requests antes da logica
- [ ] Todos os campos tem `type` definido
- [ ] Campos obrigatorios marcados com `required`
- [ ] `additionalProperties: false` em objetos criticos
- [ ] `format` usado para emails, URLs, datas
- [ ] `examples` e `description` presentes
- [ ] Mudancas breaking incrementam versao

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
