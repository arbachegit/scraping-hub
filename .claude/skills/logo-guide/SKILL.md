---
name: logo-guide
description: Guia completo de uso do logo Iconsai com especificacoes tecnicas, cores, aplicacoes e boas praticas
allowed-tools: Read, Glob, Bash
---

# Guia de Uso do Logo Iconsai

Esta skill documenta todas as especificacoes e regras de uso do logo Iconsai nos projetos da organizacao.

---

## Descricao do Logo

O logo Iconsai e composto por:

### Elementos Visuais

| Elemento | Descricao | Cor |
|----------|-----------|-----|
| **"i"** (letra) | Letra minuscula com haste vertical | Cinza claro (#D1D5DB) |
| **Triangulo Play** | Icone de play sobre a letra "i" | Cinza claro (#D1D5DB) |
| **"cons"** | Letras em fonte sans-serif bold | Cinza claro (#D1D5DB) |
| **Triangulo Play interno** | Dentro da letra "o" | Vermelho/Laranja (#EF4444) |
| **"."** (ponto) | Separador antes de "ai" | Vermelho/Laranja (#EF4444) |
| **"ai"** | Letras finais representando Inteligencia Artificial | Vermelho/Laranja (#EF4444) |

### Tipografia

- **Fonte**: Sans-serif bold (similar a Poppins Bold ou Inter Bold)
- **Peso**: 700-800 (Bold/ExtraBold)
- **Estilo**: Moderno, limpo, tecnologico

### Paleta de Cores

```css
/* Cores principais do logo */
--logo-gray: #D1D5DB;      /* Cinza claro - "icons" */
--logo-red: #EF4444;       /* Vermelho - ".ai" */
--logo-orange: #F97316;    /* Laranja alternativo */

/* Em HSL */
--logo-gray-hsl: 220 13% 84%;
--logo-red-hsl: 0 84% 60%;
--logo-orange-hsl: 25 95% 53%;
```

---

## Especificacoes Tecnicas

### Formato

| Propriedade | Valor |
|-------------|-------|
| Formato | PNG-24 |
| Transparencia | Sim (canal alpha) |
| Resolucao original | Alta (>2000px largura) |
| Tamanho arquivo | ~2.2MB |

### Dimensoes Recomendadas

| Uso | Largura | Altura | Classe CSS |
|-----|---------|--------|------------|
| Header/Login | 280px | auto | `h-16 w-auto` |
| Sidebar | 160px | auto | `h-10 w-auto` |
| Footer | 120px | auto | `h-8 w-auto` |
| Mobile | 200px | auto | `h-12 w-auto` |

---

## Fundo Transparente - OBRIGATORIO

### Regra Principal

> **O logo DEVE sempre ser exibido com fundo transparente.**
> **NAO adicionar bordas, sombras ou contornos ao redor do logo.**

### Implementacao Correta

```tsx
// CORRETO - Sem fundo, sem contorno
<Image
  src="/images/iconsai-logo.png"
  alt="Iconsai"
  width={280}
  height={80}
  className="h-16 w-auto"
/>

// CORRETO - Sem classes de background
<div className="flex justify-center">
  <Image src="/images/iconsai-logo.png" ... />
</div>
```

### Implementacao INCORRETA

```tsx
// ERRADO - Fundo branco
<div className="bg-white p-4">
  <Image src="/images/iconsai-logo.png" ... />
</div>

// ERRADO - Borda ao redor
<Image
  src="/images/iconsai-logo.png"
  className="border border-gray-200 rounded-lg"
  ...
/>

// ERRADO - Sombra que cria "caixa"
<Image
  src="/images/iconsai-logo.png"
  className="shadow-lg"
  ...
/>
```

---

## Contraste e Legibilidade

### Fundos Escuros (Recomendado)

O logo foi projetado para fundos escuros:

```css
/* Fundos ideais */
background: #0a0e1a;  /* Azul escuro */
background: #0f1629;  /* Azul muito escuro */
background: #1a1a2e;  /* Roxo escuro */
```

---

## Otimizacao de Performance

### Next.js Image Component

Sempre usar o componente `Image` do Next.js:

```tsx
import Image from 'next/image'

<Image
  src="/images/iconsai-logo.png"
  alt="Iconsai"
  width={280}      // Largura intrinseca
  height={80}      // Altura intrinseca
  priority         // Para logos above-the-fold
  className="..."  // Dimensoes via CSS
/>
```

### Propriedades Importantes

| Prop | Uso | Quando |
|------|-----|--------|
| `priority` | Pre-carrega a imagem | Logos no header/login |
| `loading="lazy"` | Carrega sob demanda | Logos no footer |
| `placeholder="blur"` | Mostra blur durante carga | Imagens grandes |

---

## Checklist de Implementacao

- [ ] Usar arquivo PNG com fundo transparente
- [ ] Implementar com `next/image` para otimizacao
- [ ] Adicionar `alt="Iconsai"` para acessibilidade
- [ ] Usar `priority` para logos above-the-fold
- [ ] Definir dimensoes via `className` (h-XX w-auto)
- [ ] Verificar contraste com fundo
- [ ] Testar em mobile
- [ ] Verificar que nao ha borda/contorno visivel

---

## Arquivos Relacionados

| Arquivo | Uso |
|---------|-----|
| `public/images/iconsai-logo.png` | Logo principal |
| `src/app/icon.png` | Favicon (cropped "i.ai") |
| `src/app/apple-icon.png` | Apple Touch Icon |

---

## Referencias

- Skill relacionada: `favicon-guide` (para icone da aba)
