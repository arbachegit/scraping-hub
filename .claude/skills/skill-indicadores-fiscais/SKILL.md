# Skill: skill-indicadores-fiscais

Calcula indicadores de performance e metricas de scraping.

## Metadados

```yaml
nome: skill-indicadores-scraping
prioridade: ALTA
tabela_destino: scraping_metrics
periodicidade: Diario
tempo_estimado: 5 minutos
```

## Objetivo

Calcular e monitorar metricas de scraping para garantir qualidade e performance dos dados coletados.

## Indicadores Calculados

| Indicador | Campo | Calculo | Alertas |
|-----------|-------|---------|---------|
| Taxa de Sucesso | success_rate | (Sucesso / Total) x 100 | ALERTA <90%, CRITICO <80% |
| Latencia Media | avg_latency_ms | Media de tempo de resposta | ALERTA >2000ms, CRITICO >5000ms |
| Erros por Hora | errors_per_hour | Contagem de erros / hora | ALERTA >10, CRITICO >50 |
| Creditos Restantes | credits_remaining | API credits disponiveis | ALERTA <20%, CRITICO <10% |
| Dados Coletados | records_collected | Total de registros novos | INFO |

## Estrutura da Tabela Destino

```sql
scraping_metrics (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,  -- coresignal, proxycurl, firecrawl
    metric_date DATE NOT NULL,

    -- Performance
    total_requests INTEGER,
    successful_requests INTEGER,
    failed_requests INTEGER,
    success_rate NUMERIC(5,2),

    -- Latencia
    avg_latency_ms INTEGER,
    p95_latency_ms INTEGER,
    p99_latency_ms INTEGER,

    -- Erros
    error_count INTEGER,
    error_types JSONB,

    -- Custos
    credits_used INTEGER,
    credits_remaining INTEGER,

    -- Volume
    records_collected INTEGER,
    bytes_processed BIGINT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(provider, metric_date)
)
```

## Execucao

```bash
# Calcular metricas do dia
python scripts/skill_indicadores_scraping.py --date today

# Calcular metricas de um periodo
python scripts/skill_indicadores_scraping.py --start 2026-01-01 --end 2026-01-31

# Recalcular todas as metricas
python scripts/skill_indicadores_scraping.py --todos
```

## Alertas

### Configuracao de Alertas

```yaml
alertas:
  success_rate:
    warning: 90
    critical: 80

  avg_latency_ms:
    warning: 2000
    critical: 5000

  credits_remaining:
    warning_pct: 20
    critical_pct: 10

  errors_per_hour:
    warning: 10
    critical: 50
```

### Notificacoes

Alertas sao enviados via:
- Slack webhook
- Email
- Dashboard em tempo real

## Dashboard de Metricas

### Graficos Principais

1. **Taxa de Sucesso por Provider** - Linha temporal
2. **Latencia Media** - Gauge por provider
3. **Volume de Dados** - Barras empilhadas
4. **Creditos Restantes** - Indicadores coloridos

### Filtros

- Periodo (hoje, 7 dias, 30 dias, custom)
- Provider (todos, coresignal, proxycurl, firecrawl)
- Tipo de dado (empresa, linkedin, governo)

## Triggers

- Executar quando: final do dia (cron 23:59)
- Executar quando: usuario solicitar relatorio
- Executar quando: alerta de erro disparado
