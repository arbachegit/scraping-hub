#!/usr/bin/env python3
"""
Importa arquivos JSON de empresas para o Supabase
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

def main():
    supabase = get_supabase()
    if not supabase:
        print("❌ Supabase não configurado")
        return

    data_dir = Path(__file__).parent.parent / "data" / "empresas"
    files = sorted(data_dir.glob("empresas_*.json"))

    print(f"📁 Encontrados {len(files)} arquivos para importar")

    total_inserted = 0
    total_errors = 0

    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                empresas = json.load(f)

            # Preparar registros (usando colunas que existem na tabela)
            records = []
            for emp in empresas:
                # Montar raw_cnpj_data com todos os dados extras
                raw_data = {
                    "capital_social": emp.get("capital_social"),
                    "porte": emp.get("porte"),
                    "natureza_juridica": emp.get("natureza_juridica"),
                    "cnae_principal": emp.get("cnae_principal"),
                    "cnae_descricao": emp.get("cnae_descricao"),
                    "cnaes_secundarios": emp.get("cnaes_secundarios"),
                    "fundadores": emp.get("fundadores"),
                }

                record = {
                    "cnpj": emp.get("cnpj"),
                    "razao_social": emp.get("razao_social"),
                    "nome_fantasia": emp.get("nome_fantasia"),
                    "situacao_cadastral": emp.get("situacao_cadastral"),
                    "data_abertura": emp.get("data_abertura"),
                    "logradouro": emp.get("logradouro"),
                    "numero": emp.get("numero"),
                    "complemento": emp.get("complemento"),
                    "bairro": emp.get("bairro"),
                    "cidade": emp.get("cidade"),
                    "estado": emp.get("estado"),
                    "cep": emp.get("cep"),
                    "telefone": emp.get("telefone"),
                    "email": emp.get("email"),
                    "raw_cnpj_data": raw_data,
                    "fonte": "brasil_api",
                    "data_coleta": emp.get("coletado_em"),
                }
                records.append(record)

            # Inserir no Supabase (upsert para evitar duplicatas)
            result = supabase.table("dim_empresas").upsert(
                records, on_conflict="cnpj"
            ).execute()

            inserted = len(result.data) if result.data else 0
            total_inserted += inserted
            print(f"✅ {filepath.name}: {inserted} empresas inseridas (total: {total_inserted})")

        except Exception as e:
            total_errors += 1
            print(f"❌ {filepath.name}: {e}")

    print(f"\n📊 RESUMO:")
    print(f"   Total inseridas: {total_inserted}")
    print(f"   Erros: {total_errors}")


if __name__ == "__main__":
    main()
