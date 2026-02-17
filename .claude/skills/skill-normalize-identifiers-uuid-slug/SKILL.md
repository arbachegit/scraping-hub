# Skill: Normalize Identifiers (UUID, Slug, Codes)

Auditor de normalizacao de identificadores (UUID, slug, codigos internos).

## Camada

**Camada 2** - Servicos de Dominio

## Quando Usar

- Geracao de IDs
- Criacao de slugs
- Codigos internos do sistema

## Regras Inviolaveis

1. **Formato Unico de ID**: IDs tem formato unico e consistente:
   - UUID v4 ou ULID (escolhido e documentado)
   - Mesmo formato em todo o sistema
   - Validacao na entrada

2. **Slugs Padronizados**: Slugs seguem padrao:
   - Lowercase
   - Hyphen como separador
   - Sem acentos/diacriticos
   - Tamanho maximo definido

3. **Codigos com Padding**: Regra de padding/zeros documentada:
   - IBGE: 7 digitos com zero a esquerda
   - CEP: 8 digitos
   - Codigos internos: documentados

4. **Normalizacao na Borda**: Normalizacao ocorre na borda (API/MCP) e e reaplicavel no dominio (defesa em profundidade).

5. **Persistencia Canonica**: Persistencia nao aceita formato alternativo (ou converte antes de salvar).

## Exemplo de Implementacao

```typescript
// utils/identifiers.ts
import { v4 as uuidv4, validate as uuidValidate } from 'uuid';
import slugify from 'slugify';

// Constantes
const SLUG_MAX_LENGTH = 100;
const IBGE_LENGTH = 7;
const CEP_LENGTH = 8;

/**
 * Gera UUID v4
 */
export function generateId(): string {
  return uuidv4();
}

/**
 * Valida UUID v4
 */
export function isValidId(id: string): boolean {
  return uuidValidate(id);
}

/**
 * Normaliza para UUID valido ou null
 */
export function normalizeId(id: string | null | undefined): string | null {
  if (!id) return null;
  const trimmed = id.trim().toLowerCase();
  return isValidId(trimmed) ? trimmed : null;
}

/**
 * Gera slug normalizado
 */
export function generateSlug(text: string): string {
  return slugify(text, {
    lower: true,
    strict: true,  // remove caracteres especiais
    locale: 'pt',
    trim: true
  }).substring(0, SLUG_MAX_LENGTH);
}

/**
 * Valida slug
 */
export function isValidSlug(slug: string): boolean {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) && slug.length <= SLUG_MAX_LENGTH;
}

/**
 * Normaliza codigo IBGE (7 digitos)
 */
export function normalizeCodigoIbge(codigo: string | number): string | null {
  const digits = String(codigo).replace(/\D/g, '');

  if (digits.length === 0 || digits.length > IBGE_LENGTH) {
    return null;
  }

  // Padding com zeros a esquerda
  return digits.padStart(IBGE_LENGTH, '0');
}

/**
 * Valida codigo IBGE
 */
export function isValidCodigoIbge(codigo: string): boolean {
  return /^\d{7}$/.test(codigo);
}

/**
 * Normaliza CEP (8 digitos)
 */
export function normalizeCep(cep: string): string | null {
  const digits = cep.replace(/\D/g, '');

  if (digits.length !== CEP_LENGTH) {
    return null;
  }

  return digits;
}

// Schemas Zod para validacao
import { z } from 'zod';

export const uuidSchema = z.string().uuid();

export const slugSchema = z.string()
  .min(1)
  .max(SLUG_MAX_LENGTH)
  .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/);

export const codigoIbgeSchema = z.string()
  .transform(normalizeCodigoIbge)
  .refine(val => val !== null, 'Codigo IBGE invalido')
  .transform(val => val as string);

export const cepSchema = z.string()
  .transform(normalizeCep)
  .refine(val => val !== null, 'CEP invalido')
  .transform(val => val as string);
```

```python
# utils/identifiers.py
import uuid
import re
from typing import Optional
import unicodedata

# Constantes
SLUG_MAX_LENGTH = 100
IBGE_LENGTH = 7
CEP_LENGTH = 8


def generate_id() -> str:
    """Gera UUID v4"""
    return str(uuid.uuid4())


def is_valid_id(id_str: str) -> bool:
    """Valida UUID v4"""
    try:
        uuid.UUID(id_str, version=4)
        return True
    except ValueError:
        return False


def normalize_id(id_str: Optional[str]) -> Optional[str]:
    """Normaliza para UUID valido ou None"""
    if not id_str:
        return None
    trimmed = id_str.strip().lower()
    return trimmed if is_valid_id(trimmed) else None


def generate_slug(text: str) -> str:
    """Gera slug normalizado"""
    # Remove acentos
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))

    # Lowercase e substitui espacos por hifen
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)  # Remove hifens duplicados
    text = text.strip('-')  # Remove hifens nas bordas

    return text[:SLUG_MAX_LENGTH]


def normalize_codigo_ibge(codigo: str | int) -> Optional[str]:
    """Normaliza codigo IBGE (7 digitos)"""
    digits = re.sub(r'\D', '', str(codigo))

    if not digits or len(digits) > IBGE_LENGTH:
        return None

    return digits.zfill(IBGE_LENGTH)


def normalize_cep(cep: str) -> Optional[str]:
    """Normaliza CEP (8 digitos)"""
    digits = re.sub(r'\D', '', cep)

    if len(digits) != CEP_LENGTH:
        return None

    return digits
```

## Checklist de Auditoria

- [ ] IDs usam formato unico (UUID v4 ou ULID)
- [ ] Validacao de ID na entrada
- [ ] Slugs em lowercase com hyphen
- [ ] Slugs sem acentos/diacriticos
- [ ] Slugs com tamanho maximo definido
- [ ] Codigos com padding documentado
- [ ] Normalizacao na borda (API/MCP)
- [ ] Defesa em profundidade (normalizacao no dominio tambem)
- [ ] Persistencia aceita apenas formato canonico

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
