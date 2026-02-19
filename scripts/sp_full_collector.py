#!/usr/bin/env python3
"""
SP FULL COLLECTOR - Coleta TODAS as 645 cidades de São Paulo
1 empresa por CNAE por cidade = 645 × 1332 = 859.140 empresas

Execução autônoma e sistemática com checkpoint/resume.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from src.database.client import get_supabase
from sp_cities_data import SP_ALL_CITIES

# Prefixos CNPJ mais comuns em SP
SP_CNPJ_PREFIXES = ["35", "33", "32", "34", "31", "30", "29", "28"]

BRASIL_API_URL = "https://brasilapi.com.br/api/cnpj/v1"
CHECKPOINT_FILE = Path(__file__).parent / "sp_full_checkpoint.json"
DATA_DIR = Path(__file__).parent.parent / "data" / "sp_full"
LOG_FILE = Path(__file__).parent / "sp_full_collector.log"


def log(msg: str):
    """Log com timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def normalize_cnae(cnae: str) -> str:
    """Normaliza CNAE para apenas dígitos (7 dígitos)"""
    if not cnae:
        return ""
    # Remove tudo que não é dígito
    digits = re.sub(r"[^0-9]", "", str(cnae))
    # Preenche com zeros à esquerda se necessário
    return digits.zfill(7)


class SPFullCollector:
    """Coletor completo para todas as 645 cidades de SP"""

    def __init__(self):
        self.supabase = get_supabase()
        self.session: aiohttp.ClientSession | None = None
        self.running = True

        # CNAEs disponíveis (normalizados)
        self.cnae_set: set[str] = set()

        # Progresso por cidade: {cidade: set(cnaes_coletados)}
        self.city_progress: dict[str, set[str]] = {}

        # Estatísticas
        self.stats = {
            "total_requests": 0,
            "total_found": 0,
            "total_inserted": 0,
            "total_pessoas": 0,
            "cities_complete": 0,
            "start_time": None,
            "last_save": None,
        }

        # Batch buffer
        self.batch_buffer: list[dict] = []
        self.batch_size = 100

        # CNPJ base
        self.cnpj_base = 1

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        log("Sinal de parada recebido, salvando...")
        self.running = False

    async def setup(self):
        """Inicialização"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Carregar CNAEs e normalizar (com paginação)
        if self.supabase:
            offset = 0
            batch = 1000
            while True:
                result = self.supabase.table("raw_cnae").select("codigo").range(offset, offset + batch - 1).execute()
                if not result.data:
                    break
                for r in result.data:
                    cnae_norm = normalize_cnae(r["codigo"])
                    if cnae_norm:
                        self.cnae_set.add(cnae_norm)
                if len(result.data) < batch:
                    break
                offset += batch
            log(f"Carregados {len(self.cnae_set)} CNAEs (normalizados)")

        # Inicializar progresso para todas as cidades
        for city_name, _ in SP_ALL_CITIES:
            city_norm = self.normalize_city(city_name)
            self.city_progress[city_norm] = set()

        log(f"Cidades: {len(self.city_progress)}")

        # Carregar checkpoint
        self.load_checkpoint()

        # Carregar CNAEs já existentes no banco
        await self.load_existing_data()

        # Sessão HTTP
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=10),
        )

        self.stats["start_time"] = datetime.now()

    def load_checkpoint(self):
        """Carrega checkpoint"""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE) as f:
                    data = json.load(f)

                self.cnpj_base = data.get("cnpj_base", 1)
                self.stats = {**self.stats, **data.get("stats", {})}

                # Carregar progresso por cidade
                for city, cnaes in data.get("city_progress", {}).items():
                    city_norm = self.normalize_city(city)
                    if city_norm in self.city_progress:
                        self.city_progress[city_norm] = set(cnaes)

                log(f"Checkpoint carregado: base={self.cnpj_base}")
            except Exception as e:
                log(f"Erro ao carregar checkpoint: {e}")

    def save_checkpoint(self):
        """Salva checkpoint"""
        try:
            data = {
                "cnpj_base": self.cnpj_base,
                "stats": self.stats,
                "city_progress": {k: list(v) for k, v in self.city_progress.items()},
                "saved_at": datetime.now().isoformat(),
            }
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump(data, f, indent=2)
            self.stats["last_save"] = datetime.now().isoformat()
        except Exception as e:
            log(f"Erro ao salvar checkpoint: {e}")

    async def load_existing_data(self):
        """Carrega dados já existentes do banco"""
        if not self.supabase:
            return

        log("Carregando dados existentes...")
        offset = 0
        batch_size = 1000

        while True:
            result = self.supabase.table("dim_empresas").select(
                "cidade, raw_cnpj_data"
            ).eq("estado", "SP").range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break

            for emp in result.data:
                cidade = self.normalize_city(emp.get("cidade", ""))
                raw = emp.get("raw_cnpj_data") or {}
                cnae = normalize_cnae(raw.get("cnae_principal", ""))

                if cidade in self.city_progress and cnae:
                    self.city_progress[cidade].add(cnae)

            offset += batch_size

        # Calcular cidades completas
        complete = sum(1 for c, cnaes in self.city_progress.items()
                       if len(cnaes) >= len(self.cnae_set))
        self.stats["cities_complete"] = complete

        total_cnaes = sum(len(c) for c in self.city_progress.values())
        cities_with_data = len([c for c in self.city_progress.values() if c])
        log(f"Dados existentes: {total_cnaes} CNAEs em {cities_with_data} cidades")
        log(f"Cidades completas: {complete}/{len(SP_ALL_CITIES)}")

    def normalize_city(self, name: str) -> str:
        """Normaliza nome de cidade"""
        if not name:
            return ""
        name = name.upper().strip()
        # Remover acentos
        replacements = {
            "Á": "A", "À": "A", "Ã": "A", "Â": "A", "Ä": "A",
            "É": "E", "È": "E", "Ê": "E", "Ë": "E",
            "Í": "I", "Ì": "I", "Î": "I", "Ï": "I",
            "Ó": "O", "Ò": "O", "Õ": "O", "Ô": "O", "Ö": "O",
            "Ú": "U", "Ù": "U", "Û": "U", "Ü": "U",
            "Ç": "C", "Ñ": "N",
        }
        for old, new in replacements.items():
            name = name.replace(old, new)
        return name

    def generate_cnpj(self) -> str:
        """Gera próximo CNPJ válido"""
        prefix = random.choice(SP_CNPJ_PREFIXES)
        base_str = f"{self.cnpj_base:08d}"
        self.cnpj_base += 1

        if self.cnpj_base > 99_999_999:
            self.cnpj_base = 1

        partial = prefix[:2] + base_str[2:] + "0001"

        # Dígitos verificadores
        w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        s1 = sum(int(d) * w for d, w in zip(partial, w1))
        d1 = 11 - (s1 % 11)
        d1 = 0 if d1 >= 10 else d1

        s2 = sum(int(d) * w for d, w in zip(partial + str(d1), w2))
        d2 = 11 - (s2 % 11)
        d2 = 0 if d2 >= 10 else d2

        return partial + str(d1) + str(d2)

    async def fetch_cnpj(self, cnpj: str) -> dict | None:
        """Busca CNPJ na BrasilAPI"""
        self.stats["total_requests"] += 1
        try:
            async with self.session.get(f"{BRASIL_API_URL}/{cnpj}") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass
        return None

    def needs_cnae(self, city: str, cnae: str) -> bool:
        """Verifica se precisamos deste CNAE para esta cidade"""
        if city not in self.city_progress:
            return False
        return cnae not in self.city_progress[city]

    async def process_empresa(self, data: dict) -> bool:
        """Processa empresa encontrada"""
        estado = (data.get("uf") or "").upper()
        if estado != "SP":
            return False

        cidade = self.normalize_city(data.get("municipio", ""))
        if cidade not in self.city_progress:
            return False

        cnae = normalize_cnae(data.get("cnae_fiscal"))
        if not cnae or not self.needs_cnae(cidade, cnae):
            return False

        # Marcar como coletado
        self.city_progress[cidade].add(cnae)
        self.stats["total_found"] += 1

        # Verificar se cidade ficou completa
        if len(self.city_progress[cidade]) >= len(self.cnae_set):
            self.stats["cities_complete"] += 1
            log(f"CIDADE COMPLETA: {cidade} ({self.stats['cities_complete']}/{len(SP_ALL_CITIES)})")

        # Transformar e adicionar ao batch
        self.batch_buffer.append(self.transform_empresa(data))

        if len(self.batch_buffer) >= self.batch_size:
            await self.save_batch()

        return True

    def transform_empresa(self, data: dict) -> dict:
        """Transforma dados para formato do banco"""
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
            "cnae_principal": normalize_cnae(data.get("cnae_fiscal")),
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
        """Salva batch no banco"""
        if not self.batch_buffer or not self.supabase:
            self.batch_buffer.clear()
            return

        try:
            # Inserir empresas
            self.supabase.table("dim_empresas").upsert(
                self.batch_buffer, on_conflict="cnpj"
            ).execute()

            # Extrair pessoas
            pessoas = []
            for emp in self.batch_buffer:
                raw = emp.get("raw_cnpj_data", {})
                fundadores = raw.get("fundadores", [])
                natureza = raw.get("natureza_juridica", "")
                razao = emp.get("razao_social", "")

                # Sócios
                for f in fundadores:
                    nome = (f.get("nome") or "").strip()
                    if nome:
                        partes = nome.split()
                        pessoas.append({
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
                        pessoas.append({
                            "nome_completo": nome,
                            "primeiro_nome": partes[0] if partes else nome,
                            "sobrenome": " ".join(partes[1:]) if len(partes) > 1 else "",
                            "fonte": "brasil_api",
                            "raw_enrichment_extended": {"cargo": "Titular", "tipo": "titular_mei"},
                        })

            if pessoas:
                self.supabase.table("dim_pessoas").insert(pessoas).execute()
                self.stats["total_pessoas"] += len(pessoas)

            self.stats["total_inserted"] += len(self.batch_buffer)

        except Exception as e:
            log(f"Erro ao salvar batch: {e}")

        self.batch_buffer.clear()

    def print_status(self):
        """Mostra status atual"""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        req_rate = self.stats["total_requests"] / elapsed if elapsed > 0 else 0
        hit_rate = (self.stats["total_found"] / self.stats["total_requests"] * 100) if self.stats["total_requests"] > 0 else 0

        # Top 5 cidades com mais CNAEs
        top_cities = sorted(
            [(c, len(cnaes)) for c, cnaes in self.city_progress.items()],
            key=lambda x: x[1], reverse=True
        )[:5]

        # Progresso geral
        total_possible = len(SP_ALL_CITIES) * len(self.cnae_set)
        total_collected = sum(len(c) for c in self.city_progress.values())
        pct_complete = (total_collected / total_possible * 100) if total_possible > 0 else 0

        log("=" * 70)
        log("SP FULL COLLECTOR - STATUS")
        log("=" * 70)
        log(f"Tempo: {elapsed/3600:.1f}h | Requests: {self.stats['total_requests']:,} ({req_rate:.1f}/s)")
        log(f"Encontradas: {self.stats['total_found']:,} | Hit rate: {hit_rate:.2f}%")
        log(f"Inseridas: {self.stats['total_inserted']:,} empresas | {self.stats['total_pessoas']:,} pessoas")
        log(f"Cidades: {self.stats['cities_complete']}/{len(SP_ALL_CITIES)} completas")
        log(f"Progresso: {total_collected:,}/{total_possible:,} CNAEs ({pct_complete:.2f}%)")
        log(f"Top cidades: {', '.join(f'{c}({n})' for c, n in top_cities)}")
        log("=" * 70)

    async def run(self):
        """Executa o coletor"""
        log("=" * 70)
        log("SP FULL COLLECTOR - INICIANDO")
        log(f"Cidades: {len(SP_ALL_CITIES)} | CNAEs: {len(self.cnae_set)}")
        log(f"Meta: {len(SP_ALL_CITIES) * len(self.cnae_set):,} empresas")
        log("=" * 70)

        await self.setup()

        last_status = time.time()
        last_checkpoint = time.time()

        try:
            while self.running:
                # Verificar se completou tudo
                if self.stats["cities_complete"] >= len(SP_ALL_CITIES):
                    log("COLETA COMPLETA! Todas as 645 cidades preenchidas.")
                    break

                # Gerar e buscar CNPJ
                cnpj = self.generate_cnpj()
                data = await self.fetch_cnpj(cnpj)

                if data:
                    await self.process_empresa(data)

                # Rate limit
                await asyncio.sleep(0.2)

                # Status a cada 2 min
                if time.time() - last_status > 120:
                    self.print_status()
                    last_status = time.time()

                # Checkpoint a cada 5 min
                if time.time() - last_checkpoint > 300:
                    await self.save_batch()
                    self.save_checkpoint()
                    last_checkpoint = time.time()

        except Exception as e:
            log(f"Erro: {e}")

        finally:
            await self.save_batch()
            self.save_checkpoint()
            if self.session:
                await self.session.close()
            self.print_status()
            log("Coletor finalizado")


async def main():
    collector = SPFullCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
