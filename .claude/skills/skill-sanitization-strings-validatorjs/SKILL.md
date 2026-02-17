# Skill: Sanitization Strings (validator.js)

Revisor de sanitizacao para garantir que strings externas sejam sanitizadas com validator.js (ou equivalente) antes de persistir/logar.

## Camada

**Camada 1 e 2** - Gateway e Servicos de Dominio

## Quando Usar

- Qualquer codigo que receba strings de usuarios
- Antes de persistir dados no banco
- Antes de logar informacoes

## Regras Inviolaveis

1. **Validacao de Formatos**: Emails/URLs/UUIDs/whitelist patterns devem ser validados com `validator.js`:
   - `isEmail()`, `isURL()`, `isUUID()`
   - `matches()` para patterns customizados

2. **Normalizacao Unicode**: Deve haver trim e normalizacao de Unicode/diacriticos quando definido:
   - `normalizeEmail()`
   - `trim()`, `escape()`

3. **Protecao Injection**: Deve haver protecao contra:
   - Header injection (escapar `\r\n`)
   - Log injection (escapar quebras de linha)
   - HTML injection (`escape()`)

4. **Logs Sem PII**: Jamais logar string nao sanitizada que possa conter PII.

5. **Normalizacao Consistente**: Persistencia exige normalizacao consistente (mesmas funcoes em todos os servicos).

## Exemplo de Implementacao Correta

```javascript
import validator from 'validator';

// Sanitizacao de email
function sanitizeEmail(email) {
  if (!email) return null;

  const trimmed = validator.trim(email);

  if (!validator.isEmail(trimmed)) {
    return null;
  }

  return validator.normalizeEmail(trimmed, {
    gmail_remove_dots: false,
    all_lowercase: true
  });
}

// Sanitizacao de URL
function sanitizeUrl(url) {
  if (!url) return null;

  const trimmed = validator.trim(url);

  if (!validator.isURL(trimmed, {
    protocols: ['http', 'https'],
    require_protocol: true
  })) {
    return null;
  }

  return trimmed;
}

// Sanitizacao para logs (remove injection)
function sanitizeForLog(str) {
  if (!str) return '';

  return validator.escape(
    validator.stripLow(str, true)
  ).substring(0, 500); // Limita tamanho
}

// Sanitizacao de CNPJ
function sanitizeCnpj(cnpj) {
  if (!cnpj) return null;

  const digits = cnpj.replace(/[^\d]/g, '');

  if (digits.length !== 14) {
    return null;
  }

  return digits;
}

// Uso
const email = sanitizeEmail(req.body.email);
const url = sanitizeUrl(req.body.website);

// Log seguro
logger.info('Busca empresa', {
  termo: sanitizeForLog(req.body.nome),
  // NUNCA logar CNPJ completo
  cnpj_masked: cnpj ? `***${cnpj.slice(-4)}` : null
});
```

## Checklist de Auditoria

- [ ] Emails validados com `isEmail()` e normalizados
- [ ] URLs validadas com `isURL()` e protocols restritos
- [ ] UUIDs validados com `isUUID()`
- [ ] Strings escapadas antes de logar
- [ ] Quebras de linha removidas para prevenir injection
- [ ] PII nunca logada sem mascara
- [ ] Normalizacao consistente em todos os servicos

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
