#!/usr/bin/env python3
"""
IconsAI - Smart Company Collector
Coleta inteligente de empresas usando CNPJs em intervalos conhecidos

Estratégia:
1. CNPJs seguem padrão regional (primeiros 2 dígitos = região)
2. Empresas mais recentes têm números maiores
3. Filiais usam número sequencial (0001, 0002, etc.)
4. Usar BrasilAPI que é gratuita e estável

Esta versão usa CNPJs sequenciais começando de valores conhecidos
onde há alta concentração de empresas ativas.

Meta: ~1.465.000 empresas
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

logger = structlog.get_logger()

# Configurações
NUM_WORKERS = 30
BATCH_SIZE = 100
REQUEST_DELAY = 0.02  # 20ms entre requests = 50 req/s por worker


@dataclass
class Stats:
    started_at: str = ""
    cnpjs_tentados: int = 0
    empresas_encontradas: int = 0
    empresas_ativas: int = 0
    empresas_salvas: int = 0
    socios_coletados: int = 0
    erros_404: int = 0
    erros_outros: int = 0


def calcular_dv(cnpj_base: str) -> str:
    """Calcula dígitos verificadores"""
    def calc(s: str, pesos: List[int]) -> int:
        total = sum(int(d) * p for d, p in zip(s, pesos))
        r = total % 11
        return 0 if r < 2 else 11 - r

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = calc(cnpj_base, p1)
    d2 = calc(cnpj_base + str(d1), p2)
    return cnpj_base + str(d1) + str(d2)


class SmartCollector:
    """Coletor inteligente de empresas"""

    BASE_URL = "https://brasilapi.com.br/api"

    def __init__(self):
        self.supabase = get_supabase()
        self.stats = Stats()
        self.output_dir = Path(__file__).parent.parent / "data" / "empresas"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = Path(__file__).parent / ".smart_collector_checkpoint.json"
        self.batch_buffer: List[dict] = []
        self.batch_count = 0
        self.semaphore = asyncio.Semaphore(NUM_WORKERS)
        self.current_prefix = 0
        self.current_number = 0

    async def fetch(self, client: httpx.AsyncClient, cnpj: str) -> Optional[dict]:
        """Busca CNPJ na BrasilAPI"""
        async with self.semaphore:
            self.stats.cnpjs_tentados += 1

            try:
                r = await client.get(
                    f"{self.BASE_URL}/cnpj/v1/{cnpj}",
                    timeout=15.0,
                )

                if r.status_code == 200:
                    data = r.json()
                    self.stats.empresas_encontradas += 1

                    situacao = data.get("descricao_situacao_cadastral", "").upper()
                    if "ATIVA" in situacao:
                        self.stats.empresas_ativas += 1
                        await asyncio.sleep(REQUEST_DELAY)
                        return self._normalize(data)

                elif r.status_code == 404:
                    self.stats.erros_404 += 1
                else:
                    self.stats.erros_outros += 1

            except Exception:
                self.stats.erros_outros += 1

            await asyncio.sleep(REQUEST_DELAY)
            return None

    def _normalize(self, data: dict) -> dict:
        """Normaliza dados"""
        socios = []
        for s in data.get("qsa", []):
            socios.append({
                "nome": s.get("nome_socio"),
                "qualificacao": s.get("qualificacao_socio"),
                "data_entrada": s.get("data_entrada_sociedade"),
            })
        self.stats.socios_coletados += len(socios)

        return {
            "cnpj": data.get("cnpj"),
            "razao_social": data.get("razao_social"),
            "nome_fantasia": data.get("nome_fantasia") or data.get("razao_social"),
            "situacao_cadastral": data.get("descricao_situacao_cadastral"),
            "data_abertura": data.get("data_inicio_atividade"),
            "capital_social": data.get("capital_social"),
            "porte": data.get("porte"),
            "natureza_juridica": data.get("natureza_juridica"),
            "cnae_principal": data.get("cnae_fiscal"),
            "cnae_descricao": data.get("cnae_fiscal_descricao"),
            "cnaes_secundarios": data.get("cnaes_secundarios", []),
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "bairro": data.get("bairro"),
            "cidade": data.get("municipio"),
            "estado": data.get("uf"),
            "cep": data.get("cep"),
            "telefone": data.get("ddd_telefone_1"),
            "email": data.get("email"),
            "fundadores": socios,
            "coletado_em": datetime.now().isoformat(),
        }

    async def save_batch(self):
        """Salva batch em arquivo"""
        if not self.batch_buffer:
            return

        self.batch_count += 1
        filename = self.output_dir / f"empresas_{self.batch_count:06d}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.batch_buffer, f, ensure_ascii=False, indent=2)

        self.stats.empresas_salvas += len(self.batch_buffer)

        logger.info(
            "batch_salvo",
            arquivo=filename.name,
            count=len(self.batch_buffer),
            total=self.stats.empresas_salvas,
        )

        # Inserir no Supabase se disponível
        if self.supabase:
            try:
                # Preparar registros de empresas
                emp_records = []
                pessoas_records = []

                for e in self.batch_buffer:
                    fundadores = e.get("fundadores", [])
                    natureza = e.get("natureza_juridica", "")
                    razao = e.get("razao_social", "")

                    # Registro da empresa
                    raw_data = {
                        "capital_social": e.get("capital_social"),
                        "porte": e.get("porte"),
                        "natureza_juridica": natureza,
                        "cnae_principal": e.get("cnae_principal"),
                        "cnae_descricao": e.get("cnae_descricao"),
                        "cnaes_secundarios": e.get("cnaes_secundarios"),
                        "fundadores": fundadores,
                    }
                    emp_records.append({
                        "cnpj": e.get("cnpj"),
                        "razao_social": razao,
                        "nome_fantasia": e.get("nome_fantasia"),
                        "situacao_cadastral": e.get("situacao_cadastral"),
                        "data_abertura": e.get("data_abertura"),
                        "logradouro": e.get("logradouro"),
                        "numero": e.get("numero"),
                        "bairro": e.get("bairro"),
                        "cidade": e.get("cidade"),
                        "estado": e.get("estado"),
                        "cep": e.get("cep"),
                        "telefone": e.get("telefone"),
                        "email": e.get("email"),
                        "raw_cnpj_data": raw_data,
                        "fonte": "brasil_api",
                        "data_coleta": e.get("coletado_em"),
                    })

                    # Extrair pessoas (sócios)
                    for f in fundadores:
                        nome = f.get("nome", "").strip()
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

                    # Se MEI/Individual, extrair titular
                    if not fundadores and ("Individual" in natureza or "EIRELI" in natureza):
                        nome = razao.strip()
                        for suf in [" ME", " MEI", " EIRELI", " EI", " EPP"]:
                            if nome.upper().endswith(suf):
                                nome = nome[:-len(suf)].strip()
                        if nome:
                            partes = nome.split()
                            pessoas_records.append({
                                "nome_completo": nome,
                                "primeiro_nome": partes[0] if partes else nome,
                                "sobrenome": " ".join(partes[1:]) if len(partes) > 1 else "",
                                "fonte": "brasil_api",
                                "raw_enrichment_extended": {"cargo": "Titular", "tipo": "titular_mei"},
                            })

                # Inserir empresas
                self.supabase.table("dim_empresas").upsert(emp_records, on_conflict="cnpj").execute()

                # Inserir pessoas
                if pessoas_records:
                    self.supabase.table("dim_pessoas").insert(pessoas_records).execute()

            except Exception as e:
                logger.debug("supabase_error", error=str(e))

        self.batch_buffer = []

    def save_checkpoint(self):
        """Salva checkpoint"""
        data = {
            "prefix": self.current_prefix,
            "number": self.current_number,
            "batch_count": self.batch_count,
            "stats": {
                "started_at": self.stats.started_at,
                "cnpjs_tentados": self.stats.cnpjs_tentados,
                "empresas_encontradas": self.stats.empresas_encontradas,
                "empresas_ativas": self.stats.empresas_ativas,
                "empresas_salvas": self.stats.empresas_salvas,
                "socios_coletados": self.stats.socios_coletados,
            },
            "timestamp": datetime.now().isoformat(),
        }
        with open(self.checkpoint_path, "w") as f:
            json.dump(data, f)

    def load_checkpoint(self) -> bool:
        """Carrega checkpoint"""
        if not self.checkpoint_path.exists():
            return False

        try:
            with open(self.checkpoint_path) as f:
                data = json.load(f)

            self.current_prefix = data.get("prefix", 0)
            self.current_number = data.get("number", 0)
            self.batch_count = data.get("batch_count", 0)

            s = data.get("stats", {})
            self.stats.started_at = s.get("started_at", "")
            self.stats.cnpjs_tentados = s.get("cnpjs_tentados", 0)
            self.stats.empresas_encontradas = s.get("empresas_encontradas", 0)
            self.stats.empresas_ativas = s.get("empresas_ativas", 0)
            self.stats.empresas_salvas = s.get("empresas_salvas", 0)
            self.stats.socios_coletados = s.get("socios_coletados", 0)

            logger.info(
                "checkpoint_carregado",
                prefix=self.current_prefix,
                number=self.current_number,
                empresas_salvas=self.stats.empresas_salvas,
            )
            return True
        except Exception:
            return False

    def log_progress(self):
        """Log de progresso"""
        if not self.stats.started_at:
            return

        elapsed = datetime.now() - datetime.fromisoformat(self.stats.started_at)
        secs = elapsed.total_seconds()
        rate = self.stats.empresas_salvas / secs if secs > 0 else 0

        # Taxa de sucesso
        hit_rate = (
            (self.stats.empresas_ativas / self.stats.cnpjs_tentados * 100)
            if self.stats.cnpjs_tentados > 0 else 0
        )

        # ETA
        meta = 1_465_000
        restante = meta - self.stats.empresas_salvas
        eta_secs = restante / rate if rate > 0 else 0
        eta_hours = eta_secs / 3600

        logger.info(
            "progresso",
            tentados=f"{self.stats.cnpjs_tentados:,}",
            encontrados=f"{self.stats.empresas_encontradas:,}",
            salvos=f"{self.stats.empresas_salvas:,}",
            socios=f"{self.stats.socios_coletados:,}",
            hit_rate=f"{hit_rate:.2f}%",
            rate=f"{rate:.1f}/s",
            elapsed=str(elapsed).split(".")[0],
            prefix=self.current_prefix,
            eta=f"{eta_hours:.1f}h",
        )

    async def collect_range(self, client: httpx.AsyncClient, prefix: int, start: int, count: int):
        """Coleta intervalo de CNPJs"""
        tasks = []
        for i in range(count):
            num = start + i
            if num > 999999:
                break

            # Formato: PP + XXXXXX + 0001 (matriz)
            base = f"{prefix:02d}{num:06d}0001"
            cnpj = calcular_dv(base)
            tasks.append(self.fetch(client, cnpj))

        results = await asyncio.gather(*tasks)

        for empresa in results:
            if empresa:
                self.batch_buffer.append(empresa)
                if len(self.batch_buffer) >= BATCH_SIZE:
                    await self.save_batch()

        return count

    async def run(self, resume: bool = True):
        """Executa coleta"""
        if resume:
            self.load_checkpoint()

        if not self.stats.started_at:
            self.stats.started_at = datetime.now().isoformat()

        logger.info(
            "coleta_iniciada",
            workers=NUM_WORKERS,
            meta="1.465.000 empresas",
            resume=resume,
        )

        # Prefixos com maior concentração de empresas (regiões mais ativas)
        prefixes = [
            # São Paulo (maioria das empresas)
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
            # Rio de Janeiro
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
            # Minas Gerais
            31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
            # Sul
            41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
            # Outros estados
            61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
            81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99,
        ]

        # Começar do checkpoint
        start_prefix_idx = prefixes.index(self.current_prefix) if self.current_prefix in prefixes else 0
        start_number = self.current_number

        batch_size = 1000  # CNPJs por lote

        async with httpx.AsyncClient() as client:
            try:
                for prefix in prefixes[start_prefix_idx:]:
                    self.current_prefix = prefix

                    # Cada prefixo tem até 1.000.000 de números possíveis
                    number = start_number
                    start_number = 0  # Resetar para próximos prefixos

                    while number < 1000000:
                        self.current_number = number
                        await self.collect_range(client, prefix, number, batch_size)
                        number += batch_size

                        # Checkpoint e log a cada 10.000 tentativas
                        if self.stats.cnpjs_tentados % 10000 == 0:
                            self.save_checkpoint()
                            self.log_progress()

                        # Verificar meta
                        if self.stats.empresas_salvas >= 1_465_000:
                            logger.info("meta_atingida")
                            break

                    if self.stats.empresas_salvas >= 1_465_000:
                        break

            except KeyboardInterrupt:
                logger.info("interrompido")
            finally:
                await self.save_batch()
                self.save_checkpoint()
                self.log_progress()

        logger.info(
            "coleta_finalizada",
            total_salvas=self.stats.empresas_salvas,
            total_socios=self.stats.socios_coletados,
        )


async def main():
    global NUM_WORKERS

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--workers", type=int, default=30)
    args = parser.parse_args()

    NUM_WORKERS = args.workers

    collector = SmartCollector()
    await collector.run(resume=not args.no_resume)


if __name__ == "__main__":
    asyncio.run(main())
