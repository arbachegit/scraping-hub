# Skill: API Request Normalization (Node/Zod)

Revisor institucional de backend Node/TS focado em normalizacao e validacao de entradas HTTP com Zod.

## Camada

**Camada 1** - Entrada/API Gateway (HTTP, Webhooks, clientes, jobs)

## Quando Usar

- Rotas/Controllers Node.js
- Endpoints Express/Fastify
- Qualquer arquivo que receba input HTTP

## Regras Inviolaveis

1. **Parsing Obrigatorio**: Todo input externo (body/query/params/headers relevantes) deve ser parseado por Zod usando `.parse()` ou `.safeParse()`.

2. **Normalizacao Explicita**: Deve haver normalizacao explicita:
   - `trim()` em strings
   - `toLowerCase()` onde aplicavel
   - Coercao de tipos (`z.coerce.*`) quando necessario

3. **Validacao Antes de Logica**: Nao pode existir logica de negocio antes da validacao.

4. **Erros Seguros**: Erros de validacao devem retornar 400 com mensagens seguras (sem vazar internals/PII).

5. **Campos Desconhecidos**: Campos desconhecidos devem ser tratados com `.strict()` (ou politica equivalente) em inputs criticos.

6. **Contrato de Saida**: Deve existir um contrato de saida (response schema) ou pelo menos shape consistente.

## Exemplo de Implementacao Correta

```typescript
import { z } from 'zod';

// Schema com normalizacao
const searchCompanySchema = z.object({
  nome: z.string()
    .min(2, 'Nome deve ter pelo menos 2 caracteres')
    .max(200)
    .transform(val => val.trim()),
  cidade: z.string()
    .optional()
    .transform(val => val?.trim().toLowerCase()),
  cnpj: z.string()
    .optional()
    .transform(val => val?.replace(/[^\d]/g, ''))
}).strict();

// Middleware de validacao
export function validateBody(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        success: false,
        error: 'Dados invalidos',
        details: result.error.issues.map(i => ({
          field: i.path.join('.'),
          message: i.message
        }))
      });
    }
    req.body = result.data;
    next();
  };
}

// Uso na rota
router.post('/search', validateBody(searchCompanySchema), async (req, res) => {
  // req.body ja esta validado e normalizado
  const { nome, cidade, cnpj } = req.body;
  // ... logica de negocio
});
```

## Checklist de Auditoria

- [ ] Todos os inputs externos usam Zod `.parse()` ou `.safeParse()`
- [ ] Strings sao normalizadas (trim, lowercase quando aplicavel)
- [ ] Tipos sao coercidos quando necessario
- [ ] Validacao ocorre ANTES de qualquer logica de negocio
- [ ] Erros retornam 400 sem expor internals
- [ ] `.strict()` usado em objetos criticos
- [ ] Response tem shape consistente

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```

## Arquivos Relacionados

- `backend/src/validation/schemas.js` - Schemas Zod centralizados
- `backend/src/routes/*.js` - Rotas que devem usar validacao
