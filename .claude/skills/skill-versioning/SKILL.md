# Skill: Versionamento Automatico

## Descricao
Gerencia versionamento do projeto iconsai-scraping. Incrementa automaticamente o contador de deploys em cada deploy.

## Formato de Versao
`MAJOR.DEPLOY_COUNT.YEAR`
- **MAJOR:** Versao principal (incrementa em breaking changes)
- **DEPLOY_COUNT:** Numero sequencial de deploys (incrementado em cada deploy)
- **YEAR:** Ano atual

Exemplo: `V1.70.2026` = Major 1, Deploy #70, Ano 2026

## Uso

### Incrementar versao para deploy (OBRIGATORIO)
```bash
python .claude/skills/skill-versioning/script.py --deploy
```

### Incrementar MAJOR (breaking changes)
```bash
python .claude/skills/skill-versioning/script.py --major
```

### Ver versao atual
```bash
python .claude/skills/skill-versioning/script.py --show
```

### Definir versao especifica
```bash
python .claude/skills/skill-versioning/script.py --set 2.1.2026
```

## Arquivos Gerenciados
- `VERSION` - Arquivo principal de versao
- `CHANGELOG.md` - Registra historico de deploys

## Integracao com Deploy
Este skill e executado automaticamente pelo GitHub Actions antes de cada deploy.
O workflow chama `--deploy` que incrementa o contador automaticamente.

## Exibicao no Frontend
A versao e exibida no dashboard via endpoint `/health` que le o arquivo VERSION.

## Triggers
- deploy, versao, version, versionamento, release
