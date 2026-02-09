# ERROS E PROBLEMAS DO PROJETO

**Data:** 09/02/2026
**Status:** CRÍTICO - SISTEMA NÃO FUNCIONAL

---

## 1. VIOLAÇÕES DAS REGRAS DO CLAUDE.MD

### 1.1 VIOLAÇÃO DA REGRA 0 - Mudanças Não Solicitadas
- Tela de login criada/modificada sem autorização
- `static/dashboard.html` criado/modificado sem autorização
- `static/admin.html` criado sem autorização
- HTML embutido em `api/main.py` (LOGIN_HTML, DASHBOARD_HTML) sem autorização
- Credenciais possivelmente alteradas sem autorização

### 1.2 VIOLAÇÃO DA REGRA 1 - Execução Literal
- Modificações feitas sem confirmação prévia
- Arquivos alterados sem listar quais seriam modificados
- Nenhum pedido de "Prosseguir? (sim/não)"

### 1.3 VIOLAÇÃO DA REGRA 2 - Automação Obrigatória
- Deploy requer intervenção manual
- Pedido para usuário executar comandos no terminal
- Soluções manuais sugeridas ao invés de automação

### 1.4 VIOLAÇÃO DA REGRA 7 - Testes Obrigatórios
- Nenhum teste criado para as modificações
- Código modificado sem testes automáticos

---

## 2. ERRO CRÍTICO - DASHBOARD CARDS

**Arquivo:** `static/dashboard.html`
**Linhas:** 299-374

**Problema:** Todos os cards são links `<a>` que redirecionam para documentação Swagger ao invés de páginas funcionais.

| Card | Link Atual (ERRADO) | Comportamento |
|------|---------------------|---------------|
| Empresas | `/docs#/Companies` | Redireciona para Swagger |
| Pessoas | `/docs#/People` | Redireciona para Swagger |
| Políticos | `/docs#/Politicians` | Redireciona para Swagger |
| Notícias | `/docs#/News` | Redireciona para Swagger |
| Analytics | `/docs#/Analytics` | Redireciona para Swagger |
| Documentação | `/docs` | Redireciona para Swagger |

**Resultado:** Sistema não tem interface de uso - apenas links para documentação API.

---

## 3. ERRO - DEPLOY CI/CD (CORRIGIDO)

**Arquivo:** `.github/workflows/ci.yml`
**Linhas:** 85-91

**Problemas identificados e corrigidos:**
1. ~~Caminho `/opt/scraping-hub`~~ → **CORRIGIDO para `/opt/iconsai-scraping`**
2. ~~Serviço systemd `scraping-hub`~~ → **CORRIGIDO para `scraping`**

**Informações corretas do servidor:**
- IP: 161.35.128.174
- Caminho: `/opt/iconsai-scraping`
- Serviço: `scraping`
- Banco: Supabase (redivrmeajmktenwshmn)
- Repo: github.com/arbachegit/scraping-hub

---

## 4. ERRO - HTML EMBUTIDO EM PYTHON

**Arquivo:** `api/main.py`
**Linhas:** 158-226 (LOGIN_HTML) e 252-332 (DASHBOARD_HTML)

**Problema:** Strings HTML de 100+ linhas embutidas em código Python.

**Consequências:**
- Difícil manutenção
- Código ilegível
- Duplicação com arquivos em `static/`
- Confusão sobre qual versão é usada

---

## 5. ERRO - ARQUIVOS DESINCRONIZADOS

**Arquivos conflitantes:**
- `static/dashboard.html` (430 linhas - versão com cards)
- `DASHBOARD_HTML` em `api/main.py` (80 linhas - versão simples)

**Problema:** Duas versões diferentes do dashboard existem no código.

---

## 6. ERRO - FALTA DE PÁGINAS FUNCIONAIS

**Situação atual:** O sistema só tem:
- Página de login (`/`)
- Dashboard (`/dashboard.html`) - apenas links para docs
- Admin (`/admin.html`)

**O que falta:**
- Página de busca de empresas (funcional)
- Página de busca de pessoas (funcional)
- Página de busca de políticos (funcional)
- Página de notícias (funcional)
- Página de analytics (funcional)

---

## 7. ERRO - SERVIÇO NÃO REINICIANDO

**Logs do CI mostram:**
```
Unit scraping-hub.service could not be found.
Failed to restart scraping-hub.service
```

**Causa:** Nome do serviço systemd incorreto ou serviço não existe.

---

## 8. ERRO - STATIC FILES NÃO SERVIDOS

**Arquivo:** `api/main.py` linha 121-125

**Problema:** Arquivos estáticos não estão sendo servidos corretamente no servidor de produção.

```python
static_path = Path(__file__).resolve().parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
```

**Resultado:** Sistema retorna JSON ao invés de HTML no endpoint `/`.

---

## RESUMO DE AÇÕES NECESSÁRIAS

1. **REVERTER** todas as mudanças não autorizadas
2. **IDENTIFICAR** o caminho correto do projeto no servidor
3. **IDENTIFICAR** o nome correto do serviço systemd
4. **CORRIGIR** o CI/CD com os caminhos corretos
5. **DECIDIR** se cards devem ser links para docs ou páginas funcionais
6. **REMOVER** HTML embutido em Python (usar apenas arquivos static/)
7. **SINCRONIZAR** versões do dashboard
8. **TESTAR** deploy automático

---

## INFORMAÇÕES DO SERVIDOR (CONFIRMADAS)

| Item | Valor |
|------|-------|
| IP | 161.35.128.174 |
| Caminho | `/opt/iconsai-scraping` |
| Serviço systemd | `scraping` |
| Banco de dados | Supabase (redivrmeajmktenwshmn) |
| Repositório | github.com/arbachegit/scraping-hub |

---

## PENDÊNCIAS

1. **Cards do dashboard** - Ainda redirecionam para /docs (aguardando decisão)
2. **HTML embutido em Python** - LOGIN_HTML e DASHBOARD_HTML em api/main.py
3. **Arquivos desincronizados** - static/dashboard.html vs DASHBOARD_HTML

---

**ESTE DOCUMENTO LISTA APENAS ERROS - NÃO CONTÉM SOLUÇÕES NÃO AUTORIZADAS**
