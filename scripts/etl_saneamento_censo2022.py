#!/usr/bin/env python3
"""
ETL Saneamento Municipal - Censo 2022
Fonte: IBGE Cidades API - Pesquisa 10102 (Censo 2022)

Indicadores:
  122298 → domicilios_total
  122318 → agua sem rede (usado para calcular agua_rede_geral = total - sem_rede)
  122336 → esgoto_rede_geral (rede geral/pluvial/fossa ligada)
  122342 → esgoto_fossa_septica (fossa não ligada à rede)
  122344 → fossa rudimentar (esgoto_outro)
  122346 → vala (esgoto_outro)
  122348 → rio/lago (esgoto_outro)
  122350 → outra forma (esgoto_outro)
  122353 → lixo_coletado
  122360 → lixo queimado (lixo_outro)
  122362 → lixo enterrado (lixo_outro)
  122364 → lixo jogado (lixo_outro)
  122366 → lixo outro destino (lixo_outro)

Substitui projeções de 2022 por dados reais do Censo.
"""

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

IBGE_CIDADES = "https://servicodados.ibge.gov.br/api/v1"
IBGE_MUNIS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"

# Indicadores Censo 2022
INDICATOR_IDS = "122298|122318|122336|122342|122344|122346|122348|122350|122353|122360|122362|122364|122366"

UF_CODES = [
    11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53,
]


def fetch_json(url: str, timeout: int = 60) -> list | dict | None:
    """GET com retry."""
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            print(f"    HTTP {resp.status_code} (tentativa {attempt + 1})")
        except requests.exceptions.RequestException as e:
            print(f"    Erro: {e} (tentativa {attempt + 1})")
        time.sleep(2 * (attempt + 1))
    return None


def get_municipios_uf(uf: int) -> list[dict]:
    """Lista municípios de uma UF."""
    data = fetch_json(IBGE_MUNIS.format(uf=uf))
    if not data:
        return []
    return [{"code6": str(m["id"])[:6], "code7": int(str(m["id"]))} for m in data]


def fetch_saneamento_uf(uf: int) -> dict[int, dict]:
    """Busca saneamento Censo 2022 para todos os municípios de uma UF."""
    munis = get_municipios_uf(uf)
    if not munis:
        return {}

    code_map = {m["code6"]: m["code7"] for m in munis}
    muni_codes = "|".join(m["code6"] for m in munis)

    url = (
        f"{IBGE_CIDADES}/pesquisas/10102/periodos/2022"
        f"/indicadores/{INDICATOR_IDS}/resultados/{muni_codes}"
    )
    data = fetch_json(url)
    if not data or not isinstance(data, list):
        return {}

    # Parse results into dict per municipality
    raw: dict[int, dict] = {}
    for indicator in data:
        iid = indicator.get("id")
        for r in indicator.get("res", []):
            code6 = r.get("localidade", "")
            code7 = code_map.get(code6)
            if not code7:
                continue
            val_str = r.get("res", {}).get("2022")
            if not val_str or val_str in ("-", "...", "X", ""):
                continue
            if code7 not in raw:
                raw[code7] = {}
            try:
                raw[code7][iid] = int(float(val_str))
            except (ValueError, TypeError):
                pass

    # Transform into table columns
    municipios: dict[int, dict] = {}
    for code7, d in raw.items():
        total = d.get(122298, 0)
        if total <= 0:
            continue

        sem_rede = d.get(122318, 0)
        agua_rede = total - sem_rede

        esgoto_rede = d.get(122336, 0)
        esgoto_fossa = d.get(122342, 0)
        esgoto_rudimentar = d.get(122344, 0)
        esgoto_vala = d.get(122346, 0)
        esgoto_rio = d.get(122348, 0)
        esgoto_outra = d.get(122350, 0)
        esgoto_outro_total = esgoto_rudimentar + esgoto_vala + esgoto_rio + esgoto_outra
        esgoto_sem = total - esgoto_rede - esgoto_fossa - esgoto_outro_total
        if esgoto_sem < 0:
            esgoto_sem = 0

        lixo_coletado = d.get(122353, 0)
        lixo_outro = (d.get(122360, 0) + d.get(122362, 0) +
                       d.get(122364, 0) + d.get(122366, 0))

        esgoto_adequado = esgoto_rede + esgoto_fossa

        municipios[code7] = {
            "codigo_ibge": code7,
            "codigo_ibge_uf": int(str(code7)[:2]),
            "ano": 2022,
            "domicilios_total": total,
            "agua_rede_geral": agua_rede,
            "agua_poco_nascente": 0,  # Censo 2022 não separa poço/nascente
            "agua_outra": sem_rede,
            "pct_agua_rede_geral": round(agua_rede / total * 100, 2),
            "esgoto_rede_geral": esgoto_rede,
            "esgoto_fossa_septica": esgoto_fossa,
            "esgoto_outro": esgoto_outro_total,
            "esgoto_sem": esgoto_sem,
            "pct_esgoto_adequado": round(esgoto_adequado / total * 100, 2),
            "lixo_coletado": lixo_coletado,
            "lixo_outro": lixo_outro,
            "pct_lixo_coletado": round(lixo_coletado / total * 100, 2) if lixo_coletado else 0,
            "fonte": "IBGE/Censo 2022",
        }

    return municipios


def upsert_batch(records: list[dict]) -> int:
    """Upsert via PostgREST."""
    url = f"{SUPABASE_URL}/rest/v1/saneamento_municipios?on_conflict=codigo_ibge,ano"
    resp = requests.post(
        url,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=headers-only"},
        json=records,
    )
    if resp.status_code in (200, 201):
        return len(records)
    print(f"    Erro upsert: {resp.status_code} {resp.text[:300]}")
    return 0


def count_records(ano: int, fonte: str | None = None) -> int:
    """Conta registros."""
    url = f"{SUPABASE_URL}/rest/v1/saneamento_municipios?ano=eq.{ano}&select=id&limit=0"
    if fonte:
        url += f"&fonte=eq.{fonte}"
    resp = requests.get(url, headers={**HEADERS, "Prefer": "count=exact"})
    if resp.status_code in (200, 206):
        return int(resp.headers.get("content-range", "*/0").split("/")[-1])
    return 0


def main():
    print("=" * 50)
    print("  ETL SANEAMENTO MUNICIPAL - CENSO 2022")
    print("  Fonte: IBGE Cidades API (pesquisa 10102)")
    print("=" * 50)

    # Check existing data
    real = count_records(2022, "IBGE/Censo 2022")
    proj = count_records(2022, "Projeção econométrica")
    print(f"\n  2022 existente: {real} Censo + {proj} Projeções")

    if real > 0 and proj == 0:
        print("  Já tem dados reais do Censo 2022, pulando.")
        return

    # Fetch all municipalities
    print(f"\n  Buscando Censo 2022 via IBGE Cidades (27 UFs)...")
    all_munis: dict = {}
    for i, uf in enumerate(UF_CODES, 1):
        munis = fetch_saneamento_uf(uf)
        all_munis.update(munis)
        print(f"    UF {uf:02d}: {len(munis)} municípios ({i}/{len(UF_CODES)})")
        time.sleep(0.5)

    print(f"  Total: {len(all_munis)} municípios com dados")

    if not all_munis:
        print("  Nenhum dado encontrado")
        return

    # Build records
    records = list(all_munis.values())
    print(f"  Registros a inserir: {len(records)}")

    # Upsert
    batch_size = 500
    inserted = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        n = upsert_batch(batch)
        inserted += n
        if n > 0:
            print(f"    Batch {i // batch_size + 1}: {n} ok")
        time.sleep(0.3)

    print(f"  Inseridos: {inserted}")

    # Summary
    print(f"\n{'=' * 50}")
    print("  RESUMO - saneamento_municipios")
    print(f"{'=' * 50}")
    for ano in [2010, 2015, 2020, 2021, 2022, 2023, 2024, 2025]:
        total = count_records(ano)
        if total > 0:
            censo = count_records(ano, "IBGE/Censo 2010") + count_records(ano, "IBGE/Censo 2022")
            proj = count_records(ano, "Projeção econométrica")
            tag = "Censo" if proj == 0 else f"Censo:{censo} Proj:{proj}"
            print(f"  {ano}: {total:>6}  [{tag}]")
    print(f"{'=' * 50}")
    print("ETL concluído!")


if __name__ == "__main__":
    main()
