#!/usr/bin/env python3
"""
Script para popular a tabela raw_cnae com todos os CNAEs brasileiros.
Fonte: IBGE Servicodados API

Uso:
    python scripts/populate_cnae.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# IBGE API endpoints
IBGE_API_BASE = "https://servicodados.ibge.gov.br/api/v2/cnae"

# Seções CNAE (categorias principais)
SECOES = {
    "A": "Agricultura, pecuária, produção florestal, pesca e aquicultura",
    "B": "Indústrias extrativas",
    "C": "Indústrias de transformação",
    "D": "Eletricidade e gás",
    "E": "Água, esgoto, atividades de gestão de resíduos e descontaminação",
    "F": "Construção",
    "G": "Comércio; reparação de veículos automotores e motocicletas",
    "H": "Transporte, armazenagem e correio",
    "I": "Alojamento e alimentação",
    "J": "Informação e comunicação",
    "K": "Atividades financeiras, de seguros e serviços relacionados",
    "L": "Atividades imobiliárias",
    "M": "Atividades profissionais, científicas e técnicas",
    "N": "Atividades administrativas e serviços complementares",
    "O": "Administração pública, defesa e seguridade social",
    "P": "Educação",
    "Q": "Saúde humana e serviços sociais",
    "R": "Artes, cultura, esporte e recreação",
    "S": "Outras atividades de serviços",
    "T": "Serviços domésticos",
    "U": "Organismos internacionais e outras instituições extraterritoriais",
}


def format_cnae_code(code: str) -> str:
    """Formata código CNAE para padrão XXXX-X/XX."""
    code = code.replace("-", "").replace("/", "").replace(".", "")
    if len(code) == 7:
        return f"{code[:4]}-{code[4]}/{code[5:]}"
    elif len(code) == 5:
        return f"{code[:4]}-{code[4]}"
    return code


def extract_hierarchy(code: str) -> dict:
    """Extrai hierarquia do código CNAE."""
    code_num = code.replace("-", "").replace("/", "").replace(".", "")

    return {
        "divisao": code_num[:2] if len(code_num) >= 2 else None,
        "grupo": code_num[:3] if len(code_num) >= 3 else None,
        "classe": code_num[:5] if len(code_num) >= 5 else None,
        "subclasse": code_num[:7] if len(code_num) >= 7 else None,
    }


def fetch_cnae_subclasses():
    """Busca todas as subclasses CNAE da API do IBGE."""
    print("[1/4] Buscando subclasses CNAE da API IBGE...")

    all_cnaes = []

    with httpx.Client(timeout=60) as client:
        # Buscar todas as subclasses
        response = client.get(f"{IBGE_API_BASE}/subclasses")
        response.raise_for_status()
        subclasses = response.json()

        print(f"      Encontradas {len(subclasses)} subclasses")

        for sub in subclasses:
            code = sub.get("id", "")
            code_str = str(code).zfill(7)

            # Extrair hierarquia
            hierarchy = extract_hierarchy(code_str)

            # Determinar seção pela divisão
            divisao = hierarchy.get("divisao", "")
            secao = None

            # Mapear divisão para seção
            div_int = int(divisao) if divisao else 0
            if 1 <= div_int <= 3:
                secao = "A"
            elif 5 <= div_int <= 9:
                secao = "B"
            elif 10 <= div_int <= 33:
                secao = "C"
            elif div_int == 35:
                secao = "D"
            elif 36 <= div_int <= 39:
                secao = "E"
            elif 41 <= div_int <= 43:
                secao = "F"
            elif 45 <= div_int <= 47:
                secao = "G"
            elif 49 <= div_int <= 53:
                secao = "H"
            elif 55 <= div_int <= 56:
                secao = "I"
            elif 58 <= div_int <= 63:
                secao = "J"
            elif 64 <= div_int <= 66:
                secao = "K"
            elif div_int == 68:
                secao = "L"
            elif 69 <= div_int <= 75:
                secao = "M"
            elif 77 <= div_int <= 82:
                secao = "N"
            elif div_int == 84:
                secao = "O"
            elif div_int == 85:
                secao = "P"
            elif 86 <= div_int <= 88:
                secao = "Q"
            elif 90 <= div_int <= 93:
                secao = "R"
            elif 94 <= div_int <= 96:
                secao = "S"
            elif 97 <= div_int <= 97:
                secao = "T"
            elif div_int == 99:
                secao = "U"

            cnae_record = {
                "codigo": format_cnae_code(code_str),
                "codigo_numerico": code_str,
                "secao": secao,
                "divisao": hierarchy.get("divisao"),
                "grupo": hierarchy.get("grupo"),
                "classe": hierarchy.get("classe"),
                "subclasse": hierarchy.get("subclasse"),
                "descricao": sub.get("descricao", ""),
                "descricao_secao": SECOES.get(secao, "") if secao else None,
                "descricao_divisao": None,  # Será preenchido depois
                "descricao_grupo": None,
                "descricao_classe": None,
                "ativo": True,
            }

            all_cnaes.append(cnae_record)

    return all_cnaes


def fetch_hierarchy_descriptions(cnaes: list):
    """Busca descrições de divisões, grupos e classes."""
    print("[2/4] Buscando descrições de divisões, grupos e classes...")

    divisoes = {}
    grupos = {}
    classes = {}

    with httpx.Client(timeout=60) as client:
        # Buscar divisões
        print("      Buscando divisões...")
        response = client.get(f"{IBGE_API_BASE}/divisoes")
        response.raise_for_status()
        for div in response.json():
            divisoes[str(div.get("id", "")).zfill(2)] = div.get("descricao", "")

        # Buscar grupos
        print("      Buscando grupos...")
        response = client.get(f"{IBGE_API_BASE}/grupos")
        response.raise_for_status()
        for grp in response.json():
            grupos[str(grp.get("id", "")).zfill(3)] = grp.get("descricao", "")

        # Buscar classes
        print("      Buscando classes...")
        response = client.get(f"{IBGE_API_BASE}/classes")
        response.raise_for_status()
        for cls in response.json():
            classes[str(cls.get("id", "")).zfill(5)] = cls.get("descricao", "")

    print(f"      Divisões: {len(divisoes)}, Grupos: {len(grupos)}, Classes: {len(classes)}")

    # Atualizar CNAEs com descrições
    for cnae in cnaes:
        if cnae.get("divisao"):
            cnae["descricao_divisao"] = divisoes.get(cnae["divisao"], "")
        if cnae.get("grupo"):
            cnae["descricao_grupo"] = grupos.get(cnae["grupo"], "")
        if cnae.get("classe"):
            cnae["descricao_classe"] = classes.get(cnae["classe"], "")

    return cnaes


def insert_cnaes(supabase, cnaes: list):
    """Insere CNAEs no banco de dados."""
    print(f"[3/4] Inserindo {len(cnaes)} CNAEs no banco...")

    # Inserir em lotes de 500
    batch_size = 500
    inserted = 0
    errors = 0

    for i in range(0, len(cnaes), batch_size):
        batch = cnaes[i:i + batch_size]
        try:
            supabase.table("raw_cnae").upsert(
                batch,
                on_conflict="codigo"
            ).execute()
            inserted += len(batch)
            print(f"      Inseridos: {inserted}/{len(cnaes)}")
        except Exception as e:
            print(f"      Erro no lote {i//batch_size + 1}: {e}")
            errors += len(batch)

    return inserted, errors


def main():
    print("=" * 60)
    print("POPULAR TABELA RAW_CNAE")
    print("Fonte: IBGE Servicodados API")
    print("=" * 60)

    # Conectar ao Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("ERRO: SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Buscar CNAEs
    cnaes = fetch_cnae_subclasses()

    # Buscar descrições de hierarquia
    cnaes = fetch_hierarchy_descriptions(cnaes)

    # Inserir no banco
    inserted, errors = insert_cnaes(supabase, cnaes)

    # Resumo
    print("=" * 60)
    print("[4/4] RESUMO")
    print("=" * 60)
    print(f"  Total de CNAEs: {len(cnaes)}")
    print(f"  Inseridos:      {inserted}")
    print(f"  Erros:          {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
