---
name: favicon-guide
description: Guia completo para configuracao de favicon com fundo transparente no Next.js App Router
allowed-tools: Read, Glob, Bash
---

# Guia de Configuracao de Favicon

Esta skill documenta a configuracao correta de favicon com fundo transparente no Next.js App Router, garantindo que o icone apareca sem quadrado branco na aba do navegador.

---

## Requisitos

- **Fundo transparente obrigatorio**: O arquivo PNG deve ter canal alpha (transparencia)
- **Formato recomendado**: PNG-24 com transparencia
- **Tamanhos padrao**:
  - `icon.png`: 32x32px (favicon padrao)
  - `apple-icon.png`: 180x180px ou 192x192px (dispositivos Apple)

---

## Estrutura de Arquivos

```
src/app/
├── icon.png           # Favicon principal (32x32px)
├── apple-icon.png     # Apple Touch Icon (180-192px)
└── layout.tsx         # Metadata automatica pelo Next.js
```

---

## Configuracao no Next.js App Router

### 1. Arquivos de Icone Automaticos

O Next.js App Router detecta automaticamente arquivos de icone na pasta `app/`:

| Arquivo | Uso | Tamanho Recomendado |
|---------|-----|---------------------|
| `icon.png` ou `icon.ico` | Favicon padrao | 32x32px |
| `icon.svg` | Favicon vetorial | Qualquer |
| `apple-icon.png` | Apple Touch Icon | 180x180px |

### 2. Nao e Necessario Configurar Manualmente

O Next.js gera automaticamente as tags `<link>` no `<head>`:

```html
<link rel="icon" href="/icon.png" type="image/png" />
<link rel="apple-touch-icon" href="/apple-icon.png" />
```

---

## Garantindo Fundo Transparente

### Verificar Transparencia do PNG

```bash
# Usar sips no macOS para verificar
sips -g all icon.png | grep -i "alpha\|pixel"

# Ou usar ImageMagick
identify -verbose icon.png | grep -i "alpha\|type"
```

### Redimensionar Mantendo Transparencia

```bash
# macOS (sips)
sips -z 32 32 original.png --out icon.png
sips -z 192 192 original.png --out apple-icon.png

# ImageMagick (multiplataforma)
convert original.png -resize 32x32 icon.png
convert original.png -resize 192x192 apple-icon.png
```

### Remover Fundo Branco (se necessario)

```bash
# ImageMagick - remover fundo branco
convert input.png -fuzz 10% -transparent white output.png

# Ou especificar cor exata
convert input.png -transparent "#FFFFFF" output.png
```

---

## Problemas Comuns

### 1. Quadrado Branco na Aba

**Causa**: O PNG nao tem canal alpha (transparencia)

**Solucao**:
- Verificar se o arquivo original tem fundo transparente
- Re-exportar do software de design com transparencia habilitada
- Usar `convert` para remover fundo branco

### 2. Favicon Nao Atualiza

**Causa**: Cache do navegador

**Solucao**:
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) ou `Cmd+Shift+R` (Mac)
- Limpar cache do navegador
- Testar em aba anonima

### 3. Favicon Muito Grande

**Causa**: PNG em alta resolucao

**Solucao**:
- Redimensionar para 32x32px
- Tamanho ideal: < 10KB

---

## Checklist de Implementacao

- [ ] Arquivo PNG com fundo transparente
- [ ] `icon.png` em 32x32px na pasta `src/app/`
- [ ] `apple-icon.png` em 192x192px na pasta `src/app/`
- [ ] Remover `favicon.ico` antigo (se existir)
- [ ] Verificar em aba anonima apos deploy
- [ ] Testar em dispositivos moveis (Apple Touch Icon)

---

## Referencias

- [Next.js Metadata Files - Icons](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/app-icons)
- [PNG Transparency](https://www.w3.org/TR/PNG/)
