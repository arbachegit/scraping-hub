# Configuracao de Favicon e Logo - Iconsai

## Arquivos Necessarios

Voce precisa adicionar os seguintes arquivos PNG com fundo transparente:

### 1. Favicon (obrigatorio)
- **Arquivo**: `src/app/icon.png`
- **Tamanho**: 32x32px
- **Formato**: PNG-24 com transparencia

### 2. Apple Touch Icon (obrigatorio)
- **Arquivo**: `src/app/apple-icon.png`
- **Tamanho**: 180x180px ou 192x192px
- **Formato**: PNG-24 com transparencia

### 3. Logo Principal (obrigatorio)
- **Arquivo**: `public/images/iconsai-logo.png`
- **Tamanho**: Original em alta resolucao
- **Formato**: PNG-24 com transparencia

## Como Criar os Favicons

### Usando ImageMagick (recomendado)

```bash
# A partir do logo original
convert iconsai-logo.png -resize 32x32 src/app/icon.png
convert iconsai-logo.png -resize 192x192 src/app/apple-icon.png
```

### Usando sips (macOS)

```bash
sips -z 32 32 iconsai-logo.png --out src/app/icon.png
sips -z 192 192 iconsai-logo.png --out src/app/apple-icon.png
```

## Verificar Transparencia

```bash
# macOS
sips -g all icon.png | grep -i alpha

# ImageMagick
identify -verbose icon.png | grep -i alpha
```

## Checklist

- [ ] `src/app/icon.png` - 32x32px com fundo transparente
- [ ] `src/app/apple-icon.png` - 192x192px com fundo transparente
- [ ] `public/images/iconsai-logo.png` - Logo principal
- [ ] Remover `src/app/icon.svg` (placeholder temporario)

## Referencias

Consulte as skills para mais detalhes:
- `.claude/skills/favicon-guide/`
- `.claude/skills/logo-guide/`
