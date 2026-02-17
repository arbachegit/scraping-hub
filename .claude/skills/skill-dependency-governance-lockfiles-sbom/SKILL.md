# Skill: Dependency Governance (Lockfiles + SBOM)

Auditor de supply chain focado em lockfiles, versoes e SBOM.

## Camada

**Camada 8** - CI/CD e Supply Chain

## Quando Usar

- Revisao de dependencias
- Auditoria de seguranca
- Pre-merge de mudancas em package.json/requirements.txt

## Regras Inviolaveis

1. **Lockfiles Obrigatorios**: Lockfiles devem existir e estar commitados:
   - `package-lock.json` ou `yarn.lock` (Node)
   - `poetry.lock` ou `requirements.lock` (Python)
   - Lockfile sincronizado com manifest

2. **Versoes Fixas em Producao**: Dependencias com versoes fixas:
   - Sem `^` ou `~` em dependencias criticas
   - Versao exata ou range muito restrito

3. **Verificacao de Vulnerabilidades**: Scan de vulnerabilidades deve existir:
   - `npm audit` / `pip-audit` / `safety`
   - Bloqueante para severidade alta/critica
   - Politica de excecoes documentada

4. **SBOM Recomendado**: Software Bill of Materials:
   - Formato CycloneDX ou SPDX
   - Gerado em cada release
   - Armazenado como artefato

## Exemplo de Configuracao

```json
// package.json - versoes fixas
{
  "dependencies": {
    "@supabase/supabase-js": "2.39.0",
    "express": "4.18.2",
    "zod": "3.22.4"
  }
}

// Nao usar:
// "@supabase/supabase-js": "^2.39.0"  // range muito amplo
// "express": "*"  // qualquer versao
// "zod": "latest"  // imprevisivel
```

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Node audit
      - name: npm audit
        run: npm audit --audit-level=high
        continue-on-error: false

      # Python audit
      - name: pip-audit
        run: |
          pip install pip-audit
          pip-audit --strict --vulnerability-service osv

      # SBOM Generation
      - name: Generate SBOM
        run: |
          npm install -g @cyclonedx/cyclonedx-npm
          cyclonedx-npm --output sbom.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json
```

```toml
# pyproject.toml
[tool.poetry]
name = "my-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.109.0"  # versao fixa
pydantic = "2.5.3"   # versao fixa
httpx = "0.26.0"     # versao fixa

[tool.pip-audit]
vulnerability-service = "osv"
strict = true
```

## Checklist de Auditoria

- [ ] Lockfile existe e esta commitado
- [ ] Lockfile sincronizado com manifest (package.json/requirements.txt)
- [ ] Versoes fixas em dependencias de producao
- [ ] Sem `^`, `~`, `*` ou `latest` em deps criticas
- [ ] `npm audit` / `pip-audit` configurado no CI
- [ ] Severidade alta/critica bloqueia merge
- [ ] Politica de excecoes documentada
- [ ] SBOM gerado em releases (recomendado)
- [ ] Dependabot ou Renovate configurado

## Politica de Severidade

| Severidade | Acao | Prazo |
|------------|------|-------|
| Critical | Bloqueia merge | Imediato |
| High | Bloqueia merge | 24h |
| Medium | Warning | 7 dias |
| Low | Info | 30 dias |

## Saida da Auditoria

```
RESULTADO: PASS | FAIL

VIOLACOES:
- [Regra X]: Descricao do problema

CORRECOES:
- Arquivo:linha - O que mudar
```
