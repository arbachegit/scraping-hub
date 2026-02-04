---
name: design-audit
description: >
  Skill para auditoria de design e UI/UX do sistema. Use para verificar consistencia visual,
  validar componentes contra as regras de design, identificar desvios de padrao, e garantir que
  novas paginas sigam o Design System.
---

# Design Audit

Skill para auditoria e validacao de design do sistema.

## Objetivo Principal

Garantir consistencia visual em todo o sistema atraves de:
1. Auditoria de paginas contra o Design System
2. Validacao de novos componentes
3. Identificacao de desvios de padrao
4. Geracao de relatorios de conformidade
5. Sugestoes de correcao

## Design System de Referencia

O documento de regras esta em: `.claude/design-rules.md`

## Workflow de Auditoria

### 1. Auditoria Rapida de Pagina

```bash
# Verificar uma pagina especifica
claude "auditar design de src/pages/NovaPagina.tsx"
```

### 2. Auditoria Completa do Sistema

```bash
# Auditar todas as paginas
claude "fazer auditoria completa de design"
```

### 3. Validacao de Novo Componente

```bash
# Validar componente novo antes de commit
claude "validar design de src/components/novo/MeuComponente.tsx"
```

## Checklist de Auditoria

### Header
- [ ] Background: `bg-[#0f1629]/80 backdrop-blur-sm`
- [ ] Borda: `border-b border-cyan-500/10`
- [ ] Titulo: gradiente `from-cyan-400 via-green-400 to-yellow-400`
- [ ] Subtitulo: `text-sm text-slate-400`

### Sidebar
- [ ] Background: `bg-slate-900`
- [ ] Borda: `border-r border-slate-700`
- [ ] Item ativo: `bg-slate-800 text-cyan-400`
- [ ] Item hover: `hover:bg-slate-800 hover:text-white`

### Cards
- [ ] Background: `bg-[#0f1629]` ou `bg-[#0f1629]/80`
- [ ] Bordas: `rounded-xl` ou `rounded-2xl`
- [ ] Borda cor: `border-cyan-500/20`
- [ ] Shadow glow: `shadow-[0_0_30px_rgba(0,255,255,0.05)]`

### Tabelas
- [ ] Header: `bg-[#1a2332]/80`
- [ ] Linha hover: `hover:bg-cyan-500/5`
- [ ] Bordas: `border-cyan-500/10`
- [ ] Textos: branco para principais, `text-slate-400` para secundarios

### Inputs
- [ ] Background: `bg-[#1a2332]`
- [ ] Borda: `border-cyan-500/20`
- [ ] Focus: `focus:ring-cyan-500/30 focus:border-cyan-500/50`
- [ ] Placeholder: `placeholder-slate-500`

### Botoes

#### Tipos de Botao

| Tipo | Classes | Uso |
|------|---------|-----|
| **Primario** | `bg-gradient-to-r from-cyan-500 to-purple-500 hover:shadow-[0_0_20px_rgba(0,255,255,0.4)] text-white font-medium rounded-xl` | Acoes principais |
| **Secundario** | `bg-slate-800/90 border-cyan-500/30 rounded-xl` | Acoes secundarias |
| **Ghost** | `hover:bg-slate-800 text-slate-300 hover:text-cyan-400` | Links e acoes sutis |
| **Destrutivo** | `border-red-500/20 text-red-400` | Excluir, Remover |

### Estados
- [ ] Loading: `Loader2` com `animate-spin text-cyan-400`
- [ ] Empty: icone + texto + CTA opcional
- [ ] Error: cores vermelhas

### Cores Semanticas
- [ ] Sucesso/OK: green-400/500
- [ ] Alerta/Atencao: yellow-400/500
- [ ] Erro/Critico: red-400/500
- [ ] Info/Neutro: cyan-400/500 ou slate-400

### Icones
- [ ] Biblioteca: Lucide React
- [ ] Tamanhos: `h-4 w-4` (sm), `h-5 w-5` (md), `h-6 w-6` (lg)

## Formato do Relatorio de Auditoria

```markdown
# Auditoria de Design - [Nome do Arquivo]

## Resumo
- **Conformidade**: X%
- **Desvios Criticos**: N
- **Desvios Menores**: N
- **Sugestoes**: N

## Conformidades
- [x] Header segue padrao
- [x] Cores semanticas corretas
...

## Desvios Encontrados

### Criticos
1. **[Linha X]** Background incorreto
   - Encontrado: `bg-gray-800`
   - Esperado: `bg-[#0f1629]`

### Menores
1. **[Linha Y]** Tamanho de icone inconsistente
   - Encontrado: `h-6 w-6`
   - Esperado: `h-5 w-5`

## Correcoes Sugeridas
...
```

## Metricas de Qualidade

| Metrica | Meta | Aceitavel |
|---------|------|-----------|
| Conformidade Geral | >95% | >85% |
| Desvios Criticos | 0 | 0 |
| Desvios Menores | <5 por pagina | <10 |
| Componentes Reutilizados | >80% | >60% |
