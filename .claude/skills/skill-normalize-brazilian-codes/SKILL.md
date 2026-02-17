# Skill: Normalize Brazilian Codes (CPF, CNPJ, IBGE, CEP)

Auditor para codigos brasileiros (CPF, CNPJ, IBGE, CEP) com validacao e normalizacao.

## Camada

**Camada 2** - Servicos de Dominio

## Quando Usar

- Qualquer codigo que manipule CPF, CNPJ, IBGE ou CEP
- Validacao de documentos brasileiros
- Persistencia de dados cadastrais

## Regras Inviolaveis

1. **CPF/CNPJ com Digito Verificador**: CPF/CNPJ devem ser validados por digito verificador:
   - CPF: 11 digitos + validacao DV
   - CNPJ: 14 digitos + validacao DV

2. **CEP Normalizado**: CEP deve ser normalizado para 8 digitos (sem hifen) e validado.

3. **IBGE Normalizado**: IBGE deve ser normalizado para 7 digitos (zero padding quando aplicavel).

4. **Formato Canonico**: Armazenamento em formato canonico unico:
   - CPF: 11 digitos sem formatacao
   - CNPJ: 14 digitos sem formatacao
   - CEP: 8 digitos sem formatacao
   - IBGE: 7 digitos com zero padding

5. **Logs Mascarados**: Logs NUNCA devem registrar CPF/CNPJ completo (mascarar).

## Exemplo de Implementacao

```typescript
// utils/brazilian-codes.ts

/**
 * Valida CPF pelo digito verificador
 */
export function isValidCpf(cpf: string): boolean {
  const digits = cpf.replace(/\D/g, '');

  if (digits.length !== 11) return false;

  // Rejeita CPFs conhecidos como invalidos
  if (/^(\d)\1+$/.test(digits)) return false;

  // Calcula primeiro digito verificador
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(digits[i]) * (10 - i);
  }
  let dv1 = (sum * 10) % 11;
  if (dv1 === 10) dv1 = 0;

  if (dv1 !== parseInt(digits[9])) return false;

  // Calcula segundo digito verificador
  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(digits[i]) * (11 - i);
  }
  let dv2 = (sum * 10) % 11;
  if (dv2 === 10) dv2 = 0;

  return dv2 === parseInt(digits[10]);
}

/**
 * Valida CNPJ pelo digito verificador
 */
export function isValidCnpj(cnpj: string): boolean {
  const digits = cnpj.replace(/\D/g, '');

  if (digits.length !== 14) return false;

  // Rejeita CNPJs conhecidos como invalidos
  if (/^(\d)\1+$/.test(digits)) return false;

  // Pesos para calculo
  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  // Primeiro digito verificador
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(digits[i]) * weights1[i];
  }
  let dv1 = sum % 11;
  dv1 = dv1 < 2 ? 0 : 11 - dv1;

  if (dv1 !== parseInt(digits[12])) return false;

  // Segundo digito verificador
  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(digits[i]) * weights2[i];
  }
  let dv2 = sum % 11;
  dv2 = dv2 < 2 ? 0 : 11 - dv2;

  return dv2 === parseInt(digits[13]);
}

/**
 * Normaliza CPF para formato canonico (11 digitos)
 */
export function normalizeCpf(cpf: string): string | null {
  const digits = cpf.replace(/\D/g, '');

  if (digits.length !== 11 || !isValidCpf(digits)) {
    return null;
  }

  return digits;
}

/**
 * Normaliza CNPJ para formato canonico (14 digitos)
 */
export function normalizeCnpj(cnpj: string): string | null {
  const digits = cnpj.replace(/\D/g, '');

  if (digits.length !== 14 || !isValidCnpj(digits)) {
    return null;
  }

  return digits;
}

/**
 * Normaliza CEP para formato canonico (8 digitos)
 */
export function normalizeCep(cep: string): string | null {
  const digits = cep.replace(/\D/g, '');

  if (digits.length !== 8) {
    return null;
  }

  // Validacao basica de range
  const num = parseInt(digits);
  if (num < 1000000 || num > 99999999) {
    return null;
  }

  return digits;
}

/**
 * Normaliza codigo IBGE para formato canonico (7 digitos)
 */
export function normalizeCodigoIbge(codigo: string | number): string | null {
  const digits = String(codigo).replace(/\D/g, '');

  if (!digits || digits.length > 7) {
    return null;
  }

  return digits.padStart(7, '0');
}

/**
 * Mascara CPF para log seguro
 * 123.456.789-00 -> ***.***.789-**
 */
export function maskCpf(cpf: string): string {
  const digits = cpf.replace(/\D/g, '');
  if (digits.length !== 11) return '***';
  return `***.***${digits.slice(6, 9)}-**`;
}

/**
 * Mascara CNPJ para log seguro
 * 12.345.678/0001-90 -> **.***.***/**01-**
 */
export function maskCnpj(cnpj: string): string {
  const digits = cnpj.replace(/\D/g, '');
  if (digits.length !== 14) return '***';
  return `**.***.***/**${digits.slice(10, 12)}-**`;
}

// Schemas Zod
import { z } from 'zod';

export const cpfSchema = z.string()
  .transform(val => val.replace(/\D/g, ''))
  .refine(isValidCpf, 'CPF invalido')
  .transform(normalizeCpf)
  .refine(val => val !== null)
  .transform(val => val as string);

export const cnpjSchema = z.string()
  .transform(val => val.replace(/\D/g, ''))
  .refine(isValidCnpj, 'CNPJ invalido')
  .transform(normalizeCnpj)
  .refine(val => val !== null)
  .transform(val => val as string);

export const cepSchema = z.string()
  .transform(normalizeCep)
  .refine(val => val !== null, 'CEP invalido')
  .transform(val => val as string);

export const codigoIbgeSchema = z.union([z.string(), z.number()])
  .transform(normalizeCodigoIbge)
  .refine(val => val !== null, 'Codigo IBGE invalido')
  .transform(val => val as string);
```

## Uso Correto em Logs

```typescript
import logger from '../utils/logger';
import { maskCpf, maskCnpj } from '../utils/brazilian-codes';

// CORRETO: mascara dados sensiveis
logger.info('Empresa encontrada', {
  cnpj_masked: maskCnpj(empresa.cnpj),
  razao_social: empresa.razao_social
});

// ERRADO: expoe CNPJ completo
// logger.info('Empresa encontrada', { cnpj: empresa.cnpj });
```

## Checklist de Auditoria

- [ ] CPF validado por digito verificador
- [ ] CNPJ validado por digito verificador
- [ ] CEP normalizado para 8 digitos
- [ ] IBGE normalizado para 7 digitos com padding
- [ ] Armazenamento em formato canonico (sem formatacao)
- [ ] CPF nunca logado completo
- [ ] CNPJ nunca logado completo
- [ ] Funcoes de mascara usadas em logs
- [ ] Schemas Zod/Pydantic para validacao

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
