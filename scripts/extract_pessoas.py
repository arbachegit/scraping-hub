#!/usr/bin/env python3
"""
Extrai pessoas (sócios e titulares MEI) das empresas e insere em dim_pessoas
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase


def extrair_nome_titular(razao_social: str) -> dict:
    """Extrai nome do titular de empresa individual"""
    nome = razao_social.strip()
    sufixos = [" ME", " MEI", " EIRELI", " EI", " EPP", " - ME", " - MEI", " - EIRELI", " - EI"]
    for suf in sufixos:
        if nome.upper().endswith(suf):
            nome = nome[:-len(suf)].strip()

    partes = nome.split()
    return {
        "nome_completo": nome,
        "primeiro_nome": partes[0] if partes else nome,
        "sobrenome": " ".join(partes[1:]) if len(partes) > 1 else "",
    }


def main():
    supabase = get_supabase()
    if not supabase:
        print("❌ Supabase não configurado")
        return

    print("📊 Extraindo pessoas das empresas...")

    # Buscar empresas em batches
    offset = 0
    batch_size = 500
    total_socios = 0
    total_titulares = 0

    while True:
        result = supabase.table("dim_empresas").select(
            "id, razao_social, raw_cnpj_data"
        ).range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        pessoas_batch = []

        for emp in result.data:
            empresa_id = emp["id"]
            razao_social = emp.get("razao_social", "")
            raw_data = emp.get("raw_cnpj_data") or {}
            fundadores = raw_data.get("fundadores", [])
            natureza = raw_data.get("natureza_juridica", "")

            # Sócios
            if fundadores:
                for f in fundadores:
                    nome = f.get("nome", "").strip()
                    if not nome:
                        continue
                    partes = nome.split()
                    pessoas_batch.append({
                        "nome_completo": nome,
                        "primeiro_nome": partes[0] if partes else nome,
                        "sobrenome": " ".join(partes[1:]) if len(partes) > 1 else "",
                        "fonte": "brasil_api",
                        "raw_enrichment_extended": {
                            "empresa_id": empresa_id,
                            "cargo": f.get("qualificacao"),
                            "data_entrada": f.get("data_entrada"),
                            "tipo": "socio",
                        },
                    })
                    total_socios += 1

            # Titulares MEI/Individual
            elif "Individual" in natureza or "EIRELI" in natureza:
                dados = extrair_nome_titular(razao_social)
                if dados["nome_completo"]:
                    pessoas_batch.append({
                        **dados,
                        "fonte": "brasil_api",
                        "raw_enrichment_extended": {
                            "empresa_id": empresa_id,
                            "cargo": "Titular",
                            "tipo": "titular_mei",
                        },
                    })
                    total_titulares += 1

        # Inserir batch
        if pessoas_batch:
            try:
                supabase.table("dim_pessoas").insert(pessoas_batch).execute()
                print(f"  ✅ +{len(pessoas_batch)} pessoas | Sócios: {total_socios} | Titulares: {total_titulares}")
            except Exception as e:
                print(f"  ⚠️ Erro batch: {e}")

        offset += batch_size

    print(f"\n📊 RESUMO:")
    print(f"   Sócios inseridos: {total_socios}")
    print(f"   Titulares MEI/EI: {total_titulares}")
    print(f"   Total: {total_socios + total_titulares}")


if __name__ == "__main__":
    main()
