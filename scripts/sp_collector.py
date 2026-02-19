#!/usr/bin/env python3
"""
Coletor focado em São Paulo - 1 empresa por CNAE por cidade
Processa cidades da maior para menor população
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

# Top 100 cidades de SP por população (IBGE 2024)
SP_CITIES_BY_POPULATION = [
    ("SAO PAULO", "3550308", 12_325_232),
    ("GUARULHOS", "3518800", 1_392_121),
    ("CAMPINAS", "3509502", 1_223_237),
    ("SAO BERNARDO DO CAMPO", "3548708", 844_483),
    ("SANTO ANDRE", "3547809", 721_368),
    ("OSASCO", "3534401", 699_944),
    ("SAO JOSE DOS CAMPOS", "3549904", 729_737),
    ("RIBEIRAO PRETO", "3543402", 711_825),
    ("SOROCABA", "3552205", 695_328),
    ("MAUA", "3529401", 477_552),
    ("SAO JOSE DO RIO PRETO", "3549805", 480_692),
    ("MOGI DAS CRUZES", "3530607", 450_785),
    ("SANTOS", "3548500", 433_656),
    ("DIADEMA", "3513801", 426_757),
    ("JUNDIAI", "3525904", 423_006),
    ("PIRACICABA", "3538709", 418_209),
    ("CARAPICUIBA", "3510609", 403_183),
    ("BAURU", "3506003", 381_706),
    ("ITAQUAQUECETUBA", "3523107", 378_189),
    ("SAO VICENTE", "3551009", 369_908),
    ("FRANCA", "3516200", 359_128),
    ("PRAIA GRANDE", "3541000", 343_227),
    ("GUARUJA", "3518701", 324_608),
    ("TAUBATE", "3554102", 323_807),
    ("LIMEIRA", "3526902", 313_226),
    ("SUZANO", "3552502", 306_129),
    ("TABOAO DA SERRA", "3553302", 293_652),
    ("SUMARE", "3552403", 290_797),
    ("BARUERI", "3505708", 284_896),
    ("EMBU DAS ARTES", "3515004", 278_986),
    ("SAO CARLOS", "3548906", 256_915),
    ("INDAIATUBA", "3520509", 257_718),
    ("COTIA", "3513009", 256_757),
    ("AMERICANA", "3501608", 242_018),
    ("MARILIA", "3529005", 242_249),
    ("ITAPECERICA DA SERRA", "3522208", 183_621),
    ("PRESIDENTE PRUDENTE", "3541406", 231_953),
    ("ITU", "3523909", 177_411),
    ("JACAREÍ", "3524402", 238_268),
    ("HORTOLANDIA", "3519071", 234_259),
    ("RIO CLARO", "3543907", 213_443),
    ("ARARAS", "3503208", 135_907),
    ("FERRAZ DE VASCONCELOS", "3515707", 200_990),
    ("SANTA BARBARA D'OESTE", "3545803", 196_657),
    ("FRANCISCO MORATO", "3516309", 184_533),
    ("ITAPEVI", "3522505", 241_513),
    ("BRAGANCA PAULISTA", "3507605", 173_378),
    ("PINDAMONHANGABA", "3538006", 171_215),
    ("ARARAQUARA", "3503208", 242_807),
    ("ATIBAIA", "3504107", 152_516),
]

# Prefixos CNPJ por região de SP
SP_CNPJ_PREFIXES = [
    "35",  # SP capital e região
    "33",  # Interior SP
    "32",  # Interior SP
    "34",  # Interior SP
]

BRASIL_API_URL = "https://brasilapi.com.br/api/cnpj/v1"
CHECKPOINT_FILE = Path(__file__).parent / "sp_checkpoint.json"
DATA_DIR = Path(__file__).parent.parent / "data" / "sp_empresas"


class SPCollector:
    """Coletor de empresas focado em São Paulo"""

    def __init__(self):
        self.supabase = get_supabase()
        self.session: aiohttp.ClientSession | None = None

        # Estado do coletor
        self.current_city_idx = 0
        self.cnae_set: set[str] = set()  # CNAEs disponíveis
        self.city_cnaes: dict[str, set[str]] = {}  # CNAEs já coletados por cidade

        # Estatísticas
        self.stats = {
            "total_requests": 0,
            "total_found": 0,
            "total_inserted": 0,
            "cities_completed": 0,
            "start_time": None,
        }

        # Batch buffer
        self.batch_buffer: list[dict] = []
        self.batch_size = 50

        # CNPJ generation
        self.current_base = 1
        self.max_base = 99_999_999

    async def setup(self):
        """Inicializa o coletor"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Carregar CNAEs do Supabase
        if self.supabase:
            result = self.supabase.table("raw_cnae").select("codigo").execute()
            self.cnae_set = {r["codigo"] for r in result.data}
            print(f"  Carregados {len(self.cnae_set)} CNAEs")
        else:
            print("  AVISO: Supabase não configurado")

        # Inicializar city_cnaes para todas as cidades
        for city_name, _, _ in SP_CITIES_BY_POPULATION:
            self.city_cnaes[city_name] = set()

        # Carregar checkpoint se existir
        self.load_checkpoint()

        # Carregar CNAEs já coletados do banco
        await self.load_existing_cnaes()

        # Criar sessão HTTP
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=5),
        )

        self.stats["start_time"] = datetime.now()

    async def load_existing_cnaes(self):
        """Carrega CNAEs já coletados por cidade do banco"""
        if not self.supabase:
            return

        print("  Carregando CNAEs já coletados...")

        # Buscar empresas de SP com cidade e CNAE
        offset = 0
        batch_size = 1000

        while True:
            result = self.supabase.table("dim_empresas").select(
                "cidade, raw_cnpj_data"
            ).eq("estado", "SP").range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break

            for emp in result.data:
                cidade = emp.get("cidade", "").upper()
                raw_data = emp.get("raw_cnpj_data") or {}
                cnae = raw_data.get("cnae_principal")

                if cidade and cnae:
                    # Normalizar nome da cidade
                    cidade_norm = self.normalize_city_name(cidade)
                    if cidade_norm in self.city_cnaes:
                        self.city_cnaes[cidade_norm].add(cnae)

            offset += batch_size
            print(f"    Processados {offset} registros...")

        # Mostrar resumo
        total_cnaes = sum(len(c) for c in self.city_cnaes.values())
        print(f"  Total CNAEs já coletados: {total_cnaes}")

        for city_name, _, _ in SP_CITIES_BY_POPULATION[:10]:
            count = len(self.city_cnaes.get(city_name, set()))
            print(f"    {city_name}: {count}/{len(self.cnae_set)} CNAEs")

    def normalize_city_name(self, name: str) -> str:
        """Normaliza nome de cidade para comparação"""
        name = name.upper().strip()
        # Remover acentos básicos
        replacements = {
            "Á": "A", "À": "A", "Ã": "A", "Â": "A",
            "É": "E", "È": "E", "Ê": "E",
            "Í": "I", "Ì": "I", "Î": "I",
            "Ó": "O", "Ò": "O", "Õ": "O", "Ô": "O",
            "Ú": "U", "Ù": "U", "Û": "U",
            "Ç": "C",
        }
        for old, new in replacements.items():
            name = name.replace(old, new)
        return name

    def load_checkpoint(self):
        """Carrega checkpoint anterior"""
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE) as f:
                data = json.load(f)

            self.current_city_idx = data.get("current_city_idx", 0)
            self.current_base = data.get("current_base", 1)
            self.stats = data.get("stats", self.stats)

            # Carregar city_cnaes
            for city, cnaes in data.get("city_cnaes", {}).items():
                self.city_cnaes[city] = set(cnaes)

            print(f"  Checkpoint carregado: cidade #{self.current_city_idx}, base {self.current_base}")

    def save_checkpoint(self):
        """Salva checkpoint"""
        data = {
            "current_city_idx": self.current_city_idx,
            "current_base": self.current_base,
            "stats": self.stats,
            "city_cnaes": {k: list(v) for k, v in self.city_cnaes.items()},
            "saved_at": datetime.now().isoformat(),
        }
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(data, f)

    def generate_cnpj(self, base: int) -> str:
        """Gera um CNPJ válido a partir de um número base"""
        # Usar prefixo aleatório de SP
        prefix = random.choice(SP_CNPJ_PREFIXES)

        # Base de 8 dígitos (sem filial e dígitos)
        base_str = f"{base:08d}"

        # Montar CNPJ parcial (8 dígitos base + 0001 filial)
        partial = prefix[:2] + base_str[2:] + "0001"

        # Calcular dígitos verificadores
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        sum1 = sum(int(d) * w for d, w in zip(partial, weights1))
        d1 = 11 - (sum1 % 11)
        d1 = 0 if d1 >= 10 else d1

        partial_with_d1 = partial + str(d1)
        sum2 = sum(int(d) * w for d, w in zip(partial_with_d1, weights2))
        d2 = 11 - (sum2 % 11)
        d2 = 0 if d2 >= 10 else d2

        return partial + str(d1) + str(d2)

    async def fetch_cnpj(self, cnpj: str) -> dict | None:
        """Busca dados de um CNPJ na BrasilAPI"""
        self.stats["total_requests"] += 1

        try:
            async with self.session.get(f"{BRASIL_API_URL}/{cnpj}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception:
            return None

    def is_target_city(self, cidade: str) -> str | None:
        """Verifica se a cidade é uma das que queremos"""
        cidade_norm = self.normalize_city_name(cidade)

        for city_name, _, _ in SP_CITIES_BY_POPULATION:
            if city_name == cidade_norm:
                return city_name
        return None

    def is_cnae_needed(self, city: str, cnae: str) -> bool:
        """Verifica se precisamos deste CNAE para esta cidade"""
        if city not in self.city_cnaes:
            return False

        # Já temos este CNAE para esta cidade?
        if cnae in self.city_cnaes[city]:
            return False

        return True

    def is_city_complete(self, city: str) -> bool:
        """Verifica se já coletamos todos os CNAEs para esta cidade"""
        if city not in self.city_cnaes:
            return False

        return len(self.city_cnaes[city]) >= len(self.cnae_set)

    async def process_empresa(self, data: dict) -> bool:
        """Processa uma empresa encontrada"""
        cidade = (data.get("municipio") or "").upper()
        estado = (data.get("uf") or "").upper()
        cnae = data.get("cnae_fiscal") or ""
        cnae = str(cnae).zfill(7)  # Garantir 7 dígitos

        # Verificar se é SP
        if estado != "SP":
            return False

        # Verificar se é uma cidade que queremos
        target_city = self.is_target_city(cidade)
        if not target_city:
            return False

        # Verificar se precisamos deste CNAE
        if not self.is_cnae_needed(target_city, cnae):
            return False

        # Marcar CNAE como coletado
        self.city_cnaes[target_city].add(cnae)
        self.stats["total_found"] += 1

        # Adicionar ao batch
        self.batch_buffer.append(self.transform_empresa(data))

        # Salvar batch se cheio
        if len(self.batch_buffer) >= self.batch_size:
            await self.save_batch()

        return True

    def transform_empresa(self, data: dict) -> dict:
        """Transforma dados da API para formato do banco"""
        fundadores = []
        for socio in data.get("qsa", []):
            fundadores.append({
                "nome": socio.get("nome_socio"),
                "qualificacao": socio.get("qualificacao_socio"),
                "data_entrada": socio.get("data_entrada_sociedade"),
            })

        raw_data = {
            "capital_social": data.get("capital_social"),
            "porte": data.get("porte"),
            "natureza_juridica": data.get("natureza_juridica"),
            "cnae_principal": str(data.get("cnae_fiscal", "")).zfill(7),
            "cnae_descricao": data.get("cnae_fiscal_descricao"),
            "cnaes_secundarios": data.get("cnaes_secundarios"),
            "fundadores": fundadores,
        }

        return {
            "cnpj": data.get("cnpj"),
            "razao_social": data.get("razao_social"),
            "nome_fantasia": data.get("nome_fantasia"),
            "situacao_cadastral": data.get("descricao_situacao_cadastral"),
            "data_abertura": data.get("data_inicio_atividade"),
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "complemento": data.get("complemento"),
            "bairro": data.get("bairro"),
            "cidade": data.get("municipio"),
            "estado": data.get("uf"),
            "cep": data.get("cep"),
            "telefone": data.get("ddd_telefone_1"),
            "email": data.get("email"),
            "raw_cnpj_data": raw_data,
            "fonte": "brasil_api",
            "data_coleta": datetime.now().isoformat(),
        }

    async def save_batch(self):
        """Salva batch no Supabase"""
        if not self.batch_buffer:
            return

        if self.supabase:
            try:
                # Inserir empresas
                emp_records = self.batch_buffer.copy()
                self.supabase.table("dim_empresas").upsert(
                    emp_records, on_conflict="cnpj"
                ).execute()

                # Extrair e inserir pessoas
                pessoas_records = []
                for emp in self.batch_buffer:
                    raw_data = emp.get("raw_cnpj_data", {})
                    fundadores = raw_data.get("fundadores", [])
                    natureza = raw_data.get("natureza_juridica", "")
                    razao = emp.get("razao_social", "")

                    # Sócios
                    for f in fundadores:
                        nome = (f.get("nome") or "").strip()
                        if nome:
                            partes = nome.split()
                            pessoas_records.append({
                                "nome_completo": nome,
                                "primeiro_nome": partes[0] if partes else nome,
                                "sobrenome": " ".join(partes[1:]) if len(partes) > 1 else "",
                                "fonte": "brasil_api",
                                "raw_enrichment_extended": {
                                    "cargo": f.get("qualificacao"),
                                    "data_entrada": f.get("data_entrada"),
                                    "tipo": "socio",
                                },
                            })

                    # Titular MEI
                    if not fundadores and ("Individual" in natureza or "EIRELI" in natureza):
                        nome = razao.strip()
                        for suf in [" ME", " MEI", " EIRELI", " EI", " EPP", " - ME", " - MEI"]:
                            if nome.upper().endswith(suf):
                                nome = nome[:-len(suf)].strip()
                        if nome:
                            partes = nome.split()
                            pessoas_records.append({
                                "nome_completo": nome,
                                "primeiro_nome": partes[0] if partes else nome,
                                "sobrenome": " ".join(partes[1:]) if len(partes) > 1 else "",
                                "fonte": "brasil_api",
                                "raw_enrichment_extended": {
                                    "cargo": "Titular",
                                    "tipo": "titular_mei",
                                },
                            })

                if pessoas_records:
                    self.supabase.table("dim_pessoas").insert(pessoas_records).execute()

                self.stats["total_inserted"] += len(self.batch_buffer)

            except Exception as e:
                print(f"  Erro ao salvar batch: {e}")

        self.batch_buffer.clear()

    def print_status(self):
        """Imprime status atual"""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        req_per_sec = self.stats["total_requests"] / elapsed if elapsed > 0 else 0
        hit_rate = (self.stats["total_found"] / self.stats["total_requests"] * 100) if self.stats["total_requests"] > 0 else 0

        # Cidade atual
        if self.current_city_idx < len(SP_CITIES_BY_POPULATION):
            city_name, _, pop = SP_CITIES_BY_POPULATION[self.current_city_idx]
            city_cnaes = len(self.city_cnaes.get(city_name, set()))
            city_progress = f"{city_cnaes}/{len(self.cnae_set)}"
        else:
            city_name = "N/A"
            city_progress = "N/A"

        print(f"\n{'='*60}")
        print(f"SP COLLECTOR - STATUS")
        print(f"{'='*60}")
        print(f"Tempo decorrido: {elapsed/60:.1f} min")
        print(f"Requisições: {self.stats['total_requests']:,} ({req_per_sec:.1f}/s)")
        print(f"Encontradas: {self.stats['total_found']:,} ({hit_rate:.1f}%)")
        print(f"Inseridas: {self.stats['total_inserted']:,}")
        print(f"Cidades completas: {self.stats['cities_completed']}/{len(SP_CITIES_BY_POPULATION)}")
        print(f"Cidade atual: {city_name} ({city_progress} CNAEs)")
        print(f"{'='*60}\n")

    async def run(self):
        """Executa o coletor"""
        print("\n" + "="*60)
        print("SP COLLECTOR - COLETA FOCADA EM SÃO PAULO")
        print("="*60)
        print(f"Cidades: {len(SP_CITIES_BY_POPULATION)}")
        print(f"CNAEs: {len(self.cnae_set)}")
        print(f"Meta por cidade: 1332 empresas (1 por CNAE)")
        print("="*60 + "\n")

        await self.setup()

        last_status = time.time()
        last_checkpoint = time.time()

        try:
            while self.current_city_idx < len(SP_CITIES_BY_POPULATION):
                city_name, _, _ = SP_CITIES_BY_POPULATION[self.current_city_idx]

                # Verificar se cidade está completa
                if self.is_city_complete(city_name):
                    print(f"  {city_name}: COMPLETO ({len(self.cnae_set)} CNAEs)")
                    self.stats["cities_completed"] += 1
                    self.current_city_idx += 1
                    continue

                # Gerar e buscar CNPJ
                cnpj = self.generate_cnpj(self.current_base)
                self.current_base += 1

                if self.current_base > self.max_base:
                    self.current_base = 1  # Reiniciar se chegar ao máximo

                # Buscar CNPJ
                data = await self.fetch_cnpj(cnpj)

                if data:
                    await self.process_empresa(data)

                # Rate limiting
                await asyncio.sleep(0.3)  # ~3 req/s

                # Status a cada 60s
                if time.time() - last_status > 60:
                    self.print_status()
                    last_status = time.time()

                # Checkpoint a cada 5 min
                if time.time() - last_checkpoint > 300:
                    await self.save_batch()
                    self.save_checkpoint()
                    last_checkpoint = time.time()

        except KeyboardInterrupt:
            print("\n\nInterrompido pelo usuário")

        finally:
            # Salvar estado final
            await self.save_batch()
            self.save_checkpoint()

            if self.session:
                await self.session.close()

            self.print_status()


async def main():
    collector = SPCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
