# Skill: Node Code Quality (ESLint + Prettier)

Auditor de qualidade para Node/TS focado em ESLint, Prettier e boas praticas.

## Camada

**Camada 8** - CI/CD e Supply Chain

## Quando Usar

- Codigo Node.js/TypeScript
- Revisao de qualidade de codigo
- Pre-merge checks

## Regras Inviolaveis

1. **ESLint Limpo**: ESLint configurado e sem warnings em codigo de producao:
   - Nenhum `// eslint-disable` sem justificativa
   - Regras de seguranca habilitadas

2. **Prettier Consistente**: Prettier aplicado e consistente:
   - Configuracao compartilhada (`.prettierrc`)
   - Pre-commit hook ou CI check

3. **TypeScript Strict**: Sem `any` implicito em camadas criticas (API/MCP/RAG):
   - `strict: true` no tsconfig
   - Tipos explicitos em interfaces publicas

4. **Tratamento de Erros**: Tratamento de erros obrigatorio:
   - `try/catch` em operacoes de IO
   - Promises com `await` (nao floating)
   - Erros logados com contexto

5. **Logs Seguros**: Sem logs sensiveis (PII/secrets):
   - Usar logger estruturado
   - Mascarar dados sensiveis

## Exemplo de Configuracao

```javascript
// .eslintrc.js
module.exports = {
  env: {
    node: true,
    es2022: true
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:security/recommended',
    'prettier'
  ],
  plugins: ['@typescript-eslint', 'security'],
  rules: {
    // Sem any implicito
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn',

    // Seguranca
    'security/detect-object-injection': 'warn',
    'security/detect-non-literal-regexp': 'warn',
    'security/detect-possible-timing-attacks': 'error',

    // Erros
    'no-unused-vars': 'error',
    'no-console': ['warn', { allow: ['warn', 'error'] }],

    // Promises
    'no-floating-promises': 'error',
    'require-await': 'warn'
  }
};

// .prettierrc
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}

// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

## Exemplo de Codigo Correto

```typescript
// services/company.ts
import logger from '../utils/logger';

interface SearchParams {
  nome: string;
  cidade?: string;
}

interface Company {
  id: string;
  razaoSocial: string;
  cnpj: string;
}

/**
 * Busca empresas por nome
 * @throws {ServiceError} Se falhar a busca
 */
async function searchCompanies(params: SearchParams): Promise<Company[]> {
  const { nome, cidade } = params;

  // Log seguro (sem dados sensiveis)
  logger.info('Buscando empresas', {
    termoLength: nome.length,
    cidade: cidade ?? 'todas'
  });

  try {
    const result = await db.query<Company>(
      'SELECT * FROM empresas WHERE nome ILIKE $1',
      [`%${nome}%`]
    );

    logger.info('Busca concluida', { count: result.length });

    return result;
  } catch (error) {
    // Log do erro com contexto
    logger.error('Erro na busca de empresas', {
      error: error instanceof Error ? error.message : 'Unknown error',
      params: { termoLength: nome.length, cidade }
    });

    throw new ServiceError('Falha ao buscar empresas', { cause: error });
  }
}

// NAO fazer:
// async function bad(params: any) {  // any implicito
//   console.log(params);  // console.log
//   const result = db.query(...);  // promise sem await
//   // sem try/catch
// }
```

## Checklist de Auditoria

- [ ] ESLint sem erros ou warnings ignorados
- [ ] Prettier aplicado consistentemente
- [ ] `strict: true` no tsconfig
- [ ] Sem `any` em interfaces publicas
- [ ] `try/catch` em operacoes de IO
- [ ] Promises com `await` (nao floating)
- [ ] Logger estruturado (nao console.log)
- [ ] Dados sensiveis mascarados nos logs
- [ ] Erros logados com contexto

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
