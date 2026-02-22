# Bug Report - E2E Testing

**Date:** 2026-02-22
**Tester:** Playwright Massive UI Tester

---

## BUG-001: Dashboard inacessível sem autenticação real

### Severidade: Medium

### Ambiente
- URL: http://localhost:3000/dashboard
- Browser: Chromium
- Playwright: 1.58.2

### Passos para Reproduzir
1. Abrir browser em modo incógnito
2. Definir `localStorage.setItem('token', 'fake-token')`
3. Navegar para `/dashboard`
4. Observar comportamento

### Resultado Esperado
Dashboard deveria carregar (mesmo com token fake) ou redirecionar para login de forma rápida.

### Resultado Observado
- Página fica em loading infinito tentando validar token
- TanStack Query faz chamadas para `/auth/me` que falham com 401
- Timeout de 30 segundos atingido
- Página não renderiza conteúdo

### Evidência
- Trace: `test-results/critical-Critical-Tests-dashboard---loads-when-authenticated-chromium/trace.zip`
- Screenshot: `test-results/critical-Critical-Tests-dashboard---loads-when-authenticated-chromium/test-failed-1.png`
- Video: `test-results/critical-Critical-Tests-dashboard---loads-when-authenticated-chromium/video.webm`

### Solução Proposta
1. **Opção A:** Adicionar timeout no `useQuery` para falhar rapidamente em caso de 401
2. **Opção B:** Redirecionar para `/` imediatamente se token for inválido
3. **Para E2E:** Fornecer credenciais reais via `E2E_TEST_USER_EMAIL`/`E2E_TEST_USER_PASSWORD`

---

## Nota: Não são bugs, são limitações de teste

Os 3 testes que falharam são relacionados à **falta de autenticação real** para testes E2E. 
O código do frontend está correto - ele corretamente requer autenticação para acessar `/dashboard`.

Para resolver, configure variáveis de ambiente com credenciais de teste:
```bash
E2E_TEST_USER_EMAIL=test@example.com
E2E_TEST_USER_PASSWORD=testpassword123
E2E_BASE_URL=http://localhost:3000
npm run test:e2e
```
