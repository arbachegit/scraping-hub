#!/usr/bin/env python3
"""
ETL PIB Municipal - Atualiza pib_municipios com dados reais SIDRA.

Fonte: IBGE/SIDRA - Tabela 5938 (PIB dos Municípios)
  - 2020-2021: PIB total + setores (todos disponíveis)
  - 2022-2023: Apenas PIB total (setores sob sigilo)

Variáveis SIDRA:
  V37   → pib_total
  V543  → impostos
  V513  → pib_agropecuaria
  V517  → pib_industria
  V6575 → pib_servicos
  V525  → pib_administracao

Nota: Valores SIDRA em R$ 1.000 → banco armazena × 1000 (R$).
"""

import contextlib
import os
import sys
import time

import requests
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "brasil-data-hub-etl", ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: SUPABASE_URL e SUPABASE_KEY não definidos")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"
UFS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
       31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]

# Mapeamento SIDRA → colunas do banco
VAR_MAP = {
    "37": "pib_total",
    "543": "impostos",
    "513": "pib_agropecuaria",
    "517": "pib_industria",
    "6575": "pib_servicos",
    "525": "pib_administracao",
}

# Variáveis: completas (2020-2021) vs só total (2022-2023)
VARS_FULL = "37,543,513,517,6575,525"
VARS_TOTAL = "37"

# Estimativa de população para calcular PIB per capita (IBGE Cidades API)
POP_INDICATOR = 143491  # Não é população, preciso de outra fonte
# Usaremos a estimativa de população da tabela 6579 do SIDRA


def fetch_sidra(url: str) -> list:
    """Fetch SIDRA com retry."""
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                return [r for r in data[1:] if r.get("V") and r["V"] not in ("...", "-", "")]
            print(f"    HTTP {resp.status_code} (tentativa {attempt + 1})")
        except requests.exceptions.RequestException as e:
            print(f"    Erro: {e} (tentativa {attempt + 1})")
        time.sleep(3 * (attempt + 1))
    return []


def fetch_populacao(ano: int) -> dict[int, int]:
    """Busca estimativa populacional por município via SIDRA tabela 6579."""
    pop = {}
    for uf in UFS:
        url = f"{SIDRA_BASE}/t/6579/n6/in%20n3%20{uf}/v/9324/p/{ano}"
        registros = fetch_sidra(url)
        for r in registros:
            try:
                cod = int(r["D1C"])
                pop[cod] = int(r["V"])
            except (ValueError, TypeError):
                pass
        time.sleep(0.3)
    return pop


def fetch_pib_ano(ano: int, full_sectors: bool = True) -> dict[int, dict]:
    """Busca dados PIB de um ano, UF por UF."""
    vars_str = VARS_FULL if full_sectors else VARS_TOTAL
    municipios: dict[int, dict] = {}

    for i, uf in enumerate(UFS, 1):
        url = f"{SIDRA_BASE}/t/5938/n6/in%20n3%20{uf}/v/{vars_str}/p/{ano}"
        registros = fetch_sidra(url)

        for r in registros:
            cod = int(r["D1C"])
            var_code = r["D2C"]
            campo = VAR_MAP.get(var_code)
            if not campo:
                continue

            if cod not in municipios:
                municipios[cod] = {"codigo_ibge": cod}

            with contextlib.suppress(ValueError, TypeError):
                # SIDRA retorna em R$ 1.000 → multiplicar por 1000
                municipios[cod][campo] = float(r["V"]) * 1000

        if i % 5 == 0:
            print(f"    {i}/{len(UFS)} UFs processadas...")
        time.sleep(0.5)

    return municipios


def count_by_fonte(ano: int, fonte: str) -> int:
    """Conta registros por ano e fonte."""
    url = (
        f"{SUPABASE_URL}/rest/v1/pib_municipios"
        f"?ano=eq.{ano}&fonte=eq.{fonte}&select=id&limit=0"
    )
    resp = requests.get(url, headers={**HEADERS, "Prefer": "count=exact"})
    if resp.status_code in (200, 206):
        cr = resp.headers.get("content-range", "*/0")
        return int(cr.split("/")[-1])
    return 0


def upsert_batch(records: list[dict]) -> int:
    """Upsert via PostgREST."""
    url = f"{SUPABASE_URL}/rest/v1/pib_municipios?on_conflict=codigo_ibge,ano"
    resp = requests.post(
        url,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=headers-only"},
        json=records,
    )
    if resp.status_code in (200, 201):
        return len(records)
    print(f"    Erro upsert: {resp.status_code} {resp.text[:300]}")
    return 0


def process_year(ano: int, full_sectors: bool = True) -> int:
    """Processa um ano de dados PIB."""
    print(f"\n{'=' * 50}")
    print(f"  PIB {ano} {'(completo)' if full_sectors else '(apenas total)'}")
    print(f"{'=' * 50}")

    real = count_by_fonte(ano, "IBGE/SIDRA Tabela 5938")
    estimated = count_by_fonte(ano, "IBGE/Estimado")
    print(f"  Existentes: {real} SIDRA + {estimated} Estimados")

    if estimated == 0:
        print("  Nenhum registro estimado para atualizar, pulando.")
        return 0

    # Buscar PIB
    print(f"  Buscando SIDRA t/5938 para {ano}...")
    municipios = fetch_pib_ano(ano, full_sectors)
    print(f"  -> {len(municipios)} municípios com dados")

    if not municipios:
        print("  Nenhum dado encontrado")
        return 0

    # Buscar população para calcular per capita
    print(f"  Buscando população estimada {ano}...")
    pop = fetch_populacao(ano)
    print(f"  -> {len(pop)} municípios com população")

    # Montar registros
    records = []
    for cod, dados in municipios.items():
        pib_total = dados.get("pib_total")
        if not pib_total:
            continue

        pop_mun = pop.get(cod)
        pib_per_capita = round(pib_total / pop_mun, 2) if pop_mun and pop_mun > 0 else None

        record = {
            "codigo_ibge": cod,
            "ano": ano,
            "pib_total": pib_total,
            "pib_per_capita": pib_per_capita,
            "fonte": "IBGE/SIDRA Tabela 5938",
        }

        if full_sectors:
            record.update({
                "pib_agropecuaria": dados.get("pib_agropecuaria"),
                "pib_industria": dados.get("pib_industria"),
                "pib_servicos": dados.get("pib_servicos"),
                "pib_administracao": dados.get("pib_administracao"),
                "impostos": dados.get("impostos"),
            })

        records.append(record)

    print(f"  Registros a inserir: {len(records)}")

    # Upsert em batches
    batch_size = 500
    inserted = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        n = upsert_batch(batch)
        inserted += n
        time.sleep(0.3)

    print(f"  Upserted: {inserted}")

    # Verificar resultado
    new_real = count_by_fonte(ano, "IBGE/SIDRA Tabela 5938")
    new_est = count_by_fonte(ano, "IBGE/Estimado")
    print(f"  Resultado: {new_real} SIDRA + {new_est} Estimados")

    return inserted


def main():
    print("=" * 50)
    print("  ETL PIB MUNICIPAL")
    print("  Fonte: IBGE/SIDRA Tabela 5938")
    print("=" * 50)

    total = 0

    # 2020-2021: dados completos (PIB + setores)
    for ano in [2020, 2021]:
        total += process_year(ano, full_sectors=True)

    # 2022-2023: apenas PIB total
    for ano in [2022, 2023]:
        total += process_year(ano, full_sectors=False)

    # Resumo
    print(f"\n{'=' * 50}")
    print("  RESUMO FINAL - pib_municipios")
    print(f"{'=' * 50}")
    for ano in range(2010, 2026):
        real = count_by_fonte(ano, "IBGE/SIDRA Tabela 5938")
        est = count_by_fonte(ano, "IBGE/Estimado")
        t = real + est
        if t > 0:
            tag = "SIDRA" if est == 0 else f"SIDRA:{real} Est:{est}"
            print(f"  {ano}: {t:>6}  [{tag}]")
    print(f"{'=' * 50}")
    print(f"  Total atualizado: {total}")
    print("ETL concluído!")


if __name__ == "__main__":
    main()
