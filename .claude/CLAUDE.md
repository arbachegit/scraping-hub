# scraping-hub - Sistema de Web Scraping

**VERSÃO: 2.0.0 - ULTRA-STRICT**  
**DATA: 08/02/2026**  
**STATUS: PROJETO TRAVADO - AUTOMAÇÃO OBRIGATÓRIA**

---

## 🚨 REGRAS IMUTÁVEIS (NUNCA VIOLAR)

### REGRA 0: PROIBIÇÃO ABSOLUTA DE MUDANÇAS NÃO SOLICITADAS

```
❌ NUNCA MUDAR CÓDIGO QUE NÃO FOI EXPLICITAMENTE PEDIDO
❌ NUNCA "MELHORAR" CÓDIGO SEM AUTORIZAÇÃO
❌ NUNCA "REFATORAR" SEM ORDEM DIRETA
❌ NUNCA "OTIMIZAR" SEM PERMISSÃO
❌ NUNCA ADICIONAR FEATURES NÃO PEDIDAS
❌ NUNCA SUGERIR MUDANÇAS - APENAS EXECUTAR ORDENS
```

**PENALIDADE:** Se Claude modificar QUALQUER arquivo não solicitado, o trabalho é REJEITADO e deve ser revertido completamente.

---

### REGRA 1: EXECUÇÃO LITERAL DE COMANDOS

**Claude deve:**
- ✅ Executar EXATAMENTE o que foi pedido
- ✅ Não interpretar, não inferir, não assumir
- ✅ Se houver QUALQUER ambiguidade → PARAR e perguntar
- ✅ Confirmar entendimento ANTES de executar

**Formato obrigatório de resposta:**
```
Entendi que você quer:
1. [ação específica 1]
2. [ação específica 2]
3. [ação específica 3]

Arquivos que serão modificados:
- arquivo1.py (linha X-Y)
- arquivo2.py (adicionar função Z)

CONFIRMAÇÃO NECESSÁRIA: Prosseguir? (sim/não)
```

---

### REGRA 2: AUTOMAÇÃO OBRIGATÓRIA - ZERO INTERVENÇÃO MANUAL

**TUDO deve ser automatizado:**

```python
# ❌ NUNCA fazer manualmente
# ❌ NUNCA pedir para usuário fazer algo
# ❌ NUNCA deixar tarefas para depois

# ✅ SEMPRE criar scripts de automação
# ✅ SEMPRE usar DigitalOcean API
# ✅ SEMPRE criar CRON jobs
# ✅ SEMPRE criar webhooks
# ✅ SEMPRE criar monitoramento automático
```

**Exemplos proibidos:**
- ❌ "Você pode executar esse comando manualmente"
- ❌ "Depois você configura o CRON"
- ❌ "Faça login no servidor e..."
- ❌ "Manualmente, ajuste o arquivo X"

**Exemplos obrigatórios:**
- ✅ "Criando script de deploy automático"
- ✅ "Configurando CRON via DigitalOcean API"
- ✅ "Implementando webhook de monitoramento"
- ✅ "Deploy automático via GitHub Actions"

---

### REGRA 3: ACESSO OBRIGATÓRIO AO DIGITALOCEAN

**Claude DEVE ter acesso à infraestrutura:**

```bash
# Servidor DigitalOcean
IP: 161.35.128.174
Port: 5678 (n8n)
SSH: Acesso obrigatório via API
```

**Automações obrigatórias via DigitalOcean:**
1. ✅ Deploy automático via API
2. ✅ CRON configuration via API
3. ✅ Monitoring setup via API
4. ✅ Log collection automático
5. ✅ Health checks automáticos
6. ✅ Restart automático em falhas
7. ✅ Backup automático

**Se Claude não conseguir acessar DigitalOcean:**
```
PARAR IMEDIATAMENTE
REPORTAR: "Acesso DigitalOcean necessário para automação"
SOLICITAR: Credenciais API / SSH keys
NÃO PROSSEGUIR com soluções manuais
```

---

### REGRA 4: DOCUMENTAÇÃO PROIBIDA (APENAS CÓDIGO)

```
❌ NUNCA escrever documentação longa
❌ NUNCA criar READMEs extensos
❌ NUNCA explicar "como funciona"

✅ APENAS código auto-documentado
✅ APENAS docstrings curtas
✅ APENAS comentários essenciais
```

**Formato permitido de comentário:**
```python
# O QUÊ (não POR QUÊ)
def scrape_siconfi(codigo_ibge: str):
    """Scrape SICONFI para município."""  # ← Máximo permitido
    pass
```

**Formato PROIBIDO:**
```python
# ❌ NUNCA fazer isso:
def scrape_siconfi(codigo_ibge: str):
    """
    Esta função realiza o scraping do portal SICONFI.
    
    O SICONFI é o Sistema de Informações Contábeis...
    Utilizamos BeautifulSoup porque...
    O retry é necessário pois...
    
    Args:
        codigo_ibge: Código IBGE de 7 dígitos que representa...
    
    Returns:
        Um dicionário contendo os dados fiscais...
    
    Examples:
        >>> scrape_siconfi('3550308')
        {'rcl': 1000000, ...}
    
    Notes:
        - Lembre-se de configurar...
        - É importante que...
    """
    pass
```

---

### REGRA 5: IMUTABILIDADE DO BASE.PY

**O arquivo `src/scrapers/base.py` é SAGRADO:**

```
🔒 NUNCA modificar base.py sem ordem EXPLÍCITA
🔒 NUNCA "melhorar" base.py
🔒 NUNCA "otimizar" base.py
🔒 NUNCA adicionar features a base.py

✅ APENAS criar NOVOS scrapers que HERDAM de BaseScraper
✅ APENAS modificar base.py se comando for:
   "Modifique o arquivo base.py adicionando [X]"
```

**Conteúdo atual do base.py (IMUTÁVEL):**
- Retry automático (tenacity)
- Logging estruturado (structlog)
- Métricas de uso
- Async HTTP client (httpx)
- Context manager

**Se precisar de nova funcionalidade:**
```python
# ✅ CERTO - Criar em NOVO arquivo
# src/scrapers/advanced_base.py
from .base import BaseScraper

class AdvancedBaseScraper(BaseScraper):
    # Nova funcionalidade aqui
    pass
```

```python
# ❌ ERRADO - Modificar base.py
# src/scrapers/base.py
class BaseScraper:
    # Adicionar nova funcionalidade ← PROIBIDO
    pass
```

---

### REGRA 6: SCRAPERS SÃO WRITE-ONLY

**Scrapers existentes NÃO podem ser modificados:**

```
🔒 apollo.py         - IMUTÁVEL
🔒 brasil_api.py     - IMUTÁVEL
🔒 perplexity.py     - IMUTÁVEL
🔒 serper.py         - IMUTÁVEL
🔒 tavily.py         - IMUTÁVEL
🔒 web_scraper.py    - IMUTÁVEL
```

**Único caso permitido para modificação:**
```
"Corrija o BUG na linha X do arquivo Y"
"Adicione o parâmetro Z à função W do arquivo V"
```

**Para novas features:**
```python
# ✅ Criar NOVO scraper
# src/scrapers/siconfi_v2.py
from .base import BaseScraper

class SiconfiV2Scraper(BaseScraper):
    # Nova implementação
    pass
```

---

### REGRA 7: TESTES SÃO OBRIGATÓRIOS E AUTOMÁTICOS

**TODA mudança de código DEVE ter teste automático:**

```python
# ❌ NUNCA aceitar código sem testes
# ❌ NUNCA deixar "adicionar testes depois"
# ❌ NUNCA testes manuais

# ✅ SEMPRE criar testes junto com código
# ✅ SEMPRE rodar testes antes de commitar
# ✅ SEMPRE CI/CD com testes automáticos
```

**Estrutura obrigatória:**
```
CRIAR código → CRIAR teste → RODAR teste → COMMITAR
```

**Formato de teste obrigatório:**
```python
# tests/scrapers/test_novo_scraper.py
import pytest
from src.scrapers.novo_scraper import NovoScraper

@pytest.mark.asyncio
async def test_scraper_success():
    scraper = NovoScraper()
    result = await scraper.scrape()
    assert result is not None
    assert len(result) > 0

@pytest.mark.asyncio
async def test_scraper_validation():
    scraper = NovoScraper()
    data = {"field": "value"}
    validated = scraper.validate(data)
    assert validated["field"] == "value"

# MÍNIMO: 2 testes por scraper
# IDEAL: 5+ testes (happy path + edge cases)
```

---

### REGRA 8: REGISTRO DE FONTES OBRIGATÓRIO

**TODO scraping DEVE registrar fonte:**

```python
async def register_data_source(self, **kwargs):
    """
    OBRIGATÓRIO para compliance ISO 27001/27701.
    
    Deve ser chamado SEMPRE após scraping.
    """
    from database import get_db_client
    
    db = get_db_client()
    
    await db.execute("""
        INSERT INTO fontes_dados (
            nome, categoria, fonte_primaria, url, 
            data_primeira_coleta, periodicidade, 
            formato, confiabilidade
        )
        VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7)
        ON CONFLICT (nome) DO UPDATE
        SET data_ultima_atualizacao = NOW()
    """,
        'Nome da Fonte',      # OBRIGATÓRIO
        'categoria',          # OBRIGATÓRIO
        'Fonte Primária',     # OBRIGATÓRIO
        'https://url.com',    # OBRIGATÓRIO
        'periodicidade',      # OBRIGATÓRIO
        'formato',            # OBRIGATÓRIO
        'confiabilidade'      # OBRIGATÓRIO
    )
```

**Penalidade:** Scraper sem registro de fonte = REJEITADO

---

## 🤖 AUTOMAÇÃO OBRIGATÓRIA

### DigitalOcean API - Acesso Necessário

**Servidor:**
```
IP: 161.35.128.174
Porta n8n: 5678
SSH: Via API Token
DigitalOcean API: Obrigatório
```

**Automações obrigatórias:**

#### 1. Deploy Automático

```python
# scripts/deploy_to_digitalocean.py
"""
Deploy automático via DigitalOcean API.

NUNCA fazer deploy manual.
NUNCA pedir para usuário fazer SSH.
SEMPRE usar este script.
"""

import digitalocean
import subprocess

def deploy_scraper(scraper_name: str):
    """
    Deploy automático de scraper.
    
    Passos:
    1. Build Docker image
    2. Push to registry
    3. Deploy via API
    4. Configure CRON via API
    5. Setup monitoring via API
    """
    # 1. Build
    subprocess.run([
        "docker", "build", 
        "-t", f"scraping-hub/{scraper_name}:latest",
        "."
    ])
    
    # 2. Push
    subprocess.run([
        "docker", "push",
        f"scraping-hub/{scraper_name}:latest"
    ])
    
    # 3. Deploy via DigitalOcean API
    manager = digitalocean.Manager(token=DIGITALOCEAN_TOKEN)
    droplet = manager.get_droplet(DROPLET_ID)
    
    # Execute deployment commands via API
    droplet.run_command([
        "docker", "pull", f"scraping-hub/{scraper_name}:latest",
        "&&",
        "docker", "run", "-d", f"scraping-hub/{scraper_name}:latest"
    ])
    
    # 4. Configure CRON via API (not manual!)
    configure_cron_via_api(scraper_name)
    
    # 5. Setup monitoring
    setup_monitoring_via_api(scraper_name)

def configure_cron_via_api(scraper_name: str):
    """Configure CRON job via DigitalOcean API."""
    # IMPLEMENTAR: API call to configure CRON
    pass

def setup_monitoring_via_api(scraper_name: str):
    """Setup monitoring via DigitalOcean API."""
    # IMPLEMENTAR: API call to setup monitoring
    pass

if __name__ == "__main__":
    # NUNCA rodar manualmente
    # SEMPRE via CI/CD
    pass
```

#### 2. CRON Automático

```python
# scripts/setup_cron_jobs.py
"""
Configuração automática de CRON jobs via API.

NUNCA editar crontab manualmente.
NUNCA SSH no servidor para configurar.
SEMPRE usar este script.
"""

from digitalocean import Manager

CRON_JOBS = {
    "siconfi_daily": {
        "schedule": "0 2 * * *",  # 2h da manhã
        "command": "python src/scrapers/siconfi.py",
        "description": "Import diário SICONFI"
    },
    "cleanup_old_data": {
        "schedule": "0 1 1 * *",  # 1º dia do mês, 1h
        "command": "python scripts/cleanup.py",
        "description": "Limpeza de dados > 90 dias"
    }
}

def setup_all_crons():
    """Setup TODOS os CRON jobs via API."""
    manager = Manager(token=DIGITALOCEAN_TOKEN)
    droplet = manager.get_droplet(DROPLET_ID)
    
    for job_name, config in CRON_JOBS.items():
        # Remove existing
        droplet.run_command(f"crontab -l | grep -v '{job_name}' | crontab -")
        
        # Add new
        cron_line = f"{config['schedule']} {config['command']} # {job_name}"
        droplet.run_command(f"(crontab -l; echo '{cron_line}') | crontab -")

if __name__ == "__main__":
    setup_all_crons()
```

#### 3. Monitoramento Automático

```python
# scripts/setup_monitoring.py
"""
Monitoramento automático via n8n webhooks.

NUNCA verificar manualmente.
NUNCA logs manuais.
SEMPRE monitoramento automático.
"""

import requests

N8N_WEBHOOK = "http://161.35.128.174:5678/webhook/scraping-monitor"

def send_alert(scraper: str, status: str, error: str = None):
    """Envia alerta para n8n."""
    payload = {
        "scraper": scraper,
        "status": status,
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    requests.post(N8N_WEBHOOK, json=payload)

def setup_health_checks():
    """Configura health checks automáticos."""
    # Verificar cada 5 minutos
    # Enviar alerta se falhar
    # Auto-restart se necessário
    pass

if __name__ == "__main__":
    setup_health_checks()
```

---

## 📁 ESTRUTURA IMUTÁVEL DO PROJETO

```
scraping-hub/
├── .claude/
│   └── CLAUDE.md                    🔒 IMUTÁVEL (este arquivo)
├── src/
│   ├── scrapers/
│   │   ├── base.py                  🔒 IMUTÁVEL (salvo ordem explícita)
│   │   ├── apollo.py                🔒 IMUTÁVEL
│   │   ├── brasil_api.py            🔒 IMUTÁVEL
│   │   ├── perplexity.py            🔒 IMUTÁVEL
│   │   ├── serper.py                🔒 IMUTÁVEL
│   │   ├── tavily.py                🔒 IMUTÁVEL
│   │   └── web_scraper.py           🔒 IMUTÁVEL
│   ├── database/                    ✅ Modificável (com ordem)
│   ├── models/                      ✅ Modificável (com ordem)
│   └── services/                    ✅ Modificável (com ordem)
├── scripts/                         ✅ CRIAR automações aqui
│   ├── deploy_to_digitalocean.py    
│   ├── setup_cron_jobs.py
│   └── setup_monitoring.py
├── tests/                           ✅ SEMPRE criar testes
└── .github/workflows/               ✅ CI/CD automático
    └── deploy.yml
```

---

## 🚫 ANTI-PADRÕES PROIBIDOS

### 1. "Melhorias" Não Solicitadas

```python
# ❌ NUNCA fazer:
# "Vou aproveitar e melhorar o logging aqui"
# "Vou refatorar esta função para ficar mais limpa"
# "Vou adicionar type hints para melhorar"

# ✅ SEMPRE:
# Executar APENAS o solicitado
# Se vir oportunidade de melhoria → IGNORAR
# Se código estiver ruim → IGNORAR (a não ser que seja pedido para corrigir)
```

### 2. Soluções Manuais

```
❌ "Execute este comando no servidor"
❌ "Configure manualmente o CRON"
❌ "Faça SSH e edite o arquivo X"
❌ "Depois você adiciona..."

✅ "Criando script de automação..."
✅ "Configurando via DigitalOcean API..."
✅ "Deploy automático configurado"
✅ "Monitoramento automático ativo"
```

### 3. Documentação Excessiva

```
❌ README de 500 linhas
❌ Explicações de "como funciona"
❌ Tutoriais passo-a-passo
❌ Diagramas de arquitetura

✅ Código auto-documentado
✅ Docstrings de 1 linha
✅ Scripts de automação
✅ Testes automáticos
```

### 4. Perguntas Desnecessárias

```
❌ "Você quer que eu adicione testes?"  (SIM, sempre)
❌ "Devo criar documentação?"           (NÃO, nunca)
❌ "Prefere fazer X ou Y?"              (Decida e execute)
❌ "Como você quer que eu faça?"        (Automação total)

✅ Apenas executar com automação máxima
✅ Perguntar APENAS se houver ambiguidade REAL
```

---

## ✅ WORKFLOW OBRIGATÓRIO

### Para QUALQUER mudança de código:

```
1. CONFIRMAÇÃO
   ├─ Entendi: [listar ações]
   ├─ Arquivos: [listar modificações]
   └─ Prosseguir? (aguardar SIM)

2. EXECUÇÃO (somente após SIM)
   ├─ Modificar APENAS arquivos listados
   ├─ Modificar APENAS linhas mencionadas
   └─ NÃO tocar em nada mais

3. TESTES AUTOMÁTICOS
   ├─ Criar testes (se código novo)
   ├─ Rodar todos os testes
   └─ FALHOU? → Reverter tudo

4. AUTOMAÇÃO
   ├─ Criar scripts de deploy
   ├─ Configurar CRON via API
   └─ Setup monitoramento via API

5. COMMIT
   ├─ Git add (APENAS arquivos modificados)
   ├─ Git commit (mensagem descritiva)
   └─ Git push (CI/CD automático)
```

---

## 🔐 CREDENCIAIS NECESSÁRIAS

**Claude PRECISA ter acesso a:**

```bash
# DigitalOcean
DIGITALOCEAN_TOKEN=dop_v1_xxxxx
DROPLET_ID=xxxxx

# n8n
N8N_URL=http://161.35.128.174:5678
N8N_WEBHOOK_URL=http://161.35.128.174:5678/webhook/scraping-monitor

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx

# GitHub (CI/CD)
GITHUB_TOKEN=ghp_xxxxx
```

**Se NÃO tiver acesso:**
```
PARAR
SOLICITAR credenciais
NÃO prosseguir com soluções manuais
```

---

## 📊 MÉTRICAS DE SUCESSO

**Este projeto é considerado BOM se:**

- ✅ 0% de mudanças não solicitadas
- ✅ 100% de automação (zero manual)
- ✅ 100% de testes (todo código testado)
- ✅ 0% de documentação desnecessária
- ✅ Deploy automático funcionando
- ✅ CRON via API configurado
- ✅ Monitoramento automático ativo

**Este projeto FALHA se:**

- ❌ Código modificado sem ordem
- ❌ Tarefa manual sugerida
- ❌ Teste não criado
- ❌ README extenso criado
- ❌ "Melhorias" não pedidas
- ❌ Deploy manual necessário

---

## 🎯 PRINCÍPIOS IMUTÁVEIS

```
1. LITERAL     - Executar exatamente o pedido
2. ZERO MANUAL - Tudo deve ser automatizado
3. IMUTÁVEL    - base.py e scrapers existentes são sagrados
4. TESTADO     - Todo código tem teste automático
5. SUCINTO     - Sem documentação excessiva
6. API-FIRST   - DigitalOcean API obrigatória
7. CI/CD       - Deploy automático sempre
```

---

## 🚀 COMANDOS RÁPIDOS

```bash
# Deploy automático
python scripts/deploy_to_digitalocean.py

# Configurar CRON via API
python scripts/setup_cron_jobs.py

# Setup monitoramento
python scripts/setup_monitoring.py

# Rodar testes
pytest tests/ -v

# ❌ NUNCA fazer manualmente:
ssh user@161.35.128.174
crontab -e
nano arquivo.py
```

---

## 📝 CHANGELOG

**v2.0.0 (08/02/2026) - ULTRA-STRICT**
- ✅ Proibição absoluta de mudanças não solicitadas
- ✅ Automação obrigatória via DigitalOcean API
- ✅ Imutabilidade de base.py e scrapers existentes
- ✅ Testes automáticos obrigatórios
- ✅ Documentação mínima
- ✅ CI/CD automático obrigatório

---

**ESTE DOCUMENTO É IMUTÁVEL**  
**VIOLAÇÕES SERÃO REJEITADAS**  
**AUTOMAÇÃO É LEI**
