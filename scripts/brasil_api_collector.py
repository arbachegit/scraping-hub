#!/usr/bin/env python3
"""
IconsAI - Brasil API Collector
Coleta massiva de empresas usando BrasilAPI

Estratégia:
- Gera CNPJs válidos por região (baseado em prefixos por UF)
- Busca dados na BrasilAPI (gratuita e sem autenticação)
- Filtra por CNAEs de interesse
- Salva em arquivos JSON ou Supabase

Meta: ~1.465.000 empresas
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

logger = structlog.get_logger()

# Configurações
NUM_WORKERS = 20  # BrasilAPI é bem tolerante
BATCH_SIZE = 100
CHECKPOINT_INTERVAL = 1000

# Mapeamento de prefixos CNPJ por UF (aproximação histórica)
# Os primeiros 2 dígitos do CNPJ costumam ter distribuição regional
UF_PREFIXES = {
    "SP": list(range(1, 25)),      # São Paulo - maior concentração
    "RJ": list(range(25, 35)),     # Rio de Janeiro
    "MG": list(range(35, 45)),     # Minas Gerais
    "RS": list(range(45, 52)),     # Rio Grande do Sul
    "PR": list(range(52, 58)),     # Paraná
    "SC": list(range(58, 63)),     # Santa Catarina
    "BA": list(range(63, 68)),     # Bahia
    "PE": list(range(68, 72)),     # Pernambuco
    "CE": list(range(72, 76)),     # Ceará
    "GO": list(range(76, 79)),     # Goiás
    "DF": list(range(79, 82)),     # Distrito Federal
    "ES": list(range(82, 84)),     # Espírito Santo
    "PA": list(range(84, 86)),     # Pará
    "MA": list(range(86, 88)),     # Maranhão
    "MT": list(range(88, 90)),     # Mato Grosso
    "MS": list(range(90, 92)),     # Mato Grosso do Sul
    "PB": list(range(92, 93)),     # Paraíba
    "RN": list(range(93, 94)),     # Rio Grande do Norte
    "AL": list(range(94, 95)),     # Alagoas
    "PI": list(range(95, 96)),     # Piauí
    "SE": list(range(96, 97)),     # Sergipe
    "AM": list(range(97, 98)),     # Amazonas
    "RO": [98],                     # Rondônia
    "AC": [98],                     # Acre
    "AP": [99],                     # Amapá
    "RR": [99],                     # Roraima
    "TO": [99],                     # Tocantins
}

# CNAEs principais por setor (para filtrar resultados relevantes)
CNAES_INTERESSE = {
    "tecnologia": ["62", "63"],  # TI e Comunicação
    "comercio": ["47", "46"],    # Comércio varejista e atacadista
    "servicos": ["69", "70", "73"],  # Advocacia, consultoria, publicidade
    "industria": ["10", "11", "13", "14", "20", "22", "25", "28"],  # Diversas indústrias
    "construcao": ["41", "42", "43"],  # Construção civil
    "saude": ["86", "87"],       # Saúde
    "educacao": ["85"],          # Educação
    "financeiro": ["64", "65", "66"],  # Financeiro
    "transporte": ["49", "50", "51", "52"],  # Transporte
    "alimentacao": ["56"],       # Restaurantes
}


@dataclass
class CollectionStats:
    """Estatísticas de coleta"""
    started_at: str = ""
    cnpjs_tentados: int = 0
    empresas_encontradas: int = 0
    empresas_ativas: int = 0
    empresas_salvas: int = 0
    socios_coletados: int = 0
    erros: int = 0
    rate_limited: int = 0


def calcular_digitos_verificadores(cnpj_base: str) -> str:
    """Calcula os dígitos verificadores do CNPJ"""
    def calc_digito(cnpj_parte: str, pesos: List[int]) -> int:
        total = sum(int(d) * p for d, p in zip(cnpj_parte, pesos, strict=False))
        resto = total % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = calc_digito(cnpj_base, pesos1)
    d2 = calc_digito(cnpj_base + str(d1), pesos2)

    return cnpj_base + str(d1) + str(d2)


def gerar_cnpjs_regiao(uf: str, quantidade: int = 1000) -> List[str]:
    """Gera CNPJs válidos para uma região"""
    prefixes = UF_PREFIXES.get(uf, list(range(1, 100)))
    cnpjs = []

    for _ in range(quantidade):
        prefix = random.choice(prefixes)
        # Formato: PP.XXX.XXX/0001-YY (matriz)
        # PP = prefixo regional (2 dígitos)
        # XXX.XXX = número sequencial (6 dígitos)
        # 0001 = filial (0001 = matriz)
        # YY = dígitos verificadores

        numero = random.randint(0, 999999)
        base = f"{prefix:02d}{numero:06d}0001"
        cnpj = calcular_digitos_verificadores(base)
        cnpjs.append(cnpj)

    return cnpjs


class BrasilAPICollector:
    """Coletor usando BrasilAPI"""

    BASE_URL = "https://brasilapi.com.br/api"

    def __init__(self):
        self.supabase = get_supabase()
        self.stats = CollectionStats()
        self.output_dir = Path(__file__).parent.parent / "data" / "empresas"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = Path(__file__).parent / ".brasil_api_checkpoint.json"
        self.cnpjs_processados: set = set()
        self.batch_buffer: List[dict] = []
        self.batch_count = 0
        self.semaphore = asyncio.Semaphore(NUM_WORKERS)

    async def fetch_cnpj(self, client: httpx.AsyncClient, cnpj: str) -> Optional[dict]:
        """Busca dados de um CNPJ na BrasilAPI"""
        async with self.semaphore:
            try:
                self.stats.cnpjs_tentados += 1
                response = await client.get(
                    f"{self.BASE_URL}/cnpj/v1/{cnpj}",
                    headers={"Accept": "application/json"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    self.stats.empresas_encontradas += 1

                    # Verificar se está ativa
                    situacao = data.get("descricao_situacao_cadastral", "").upper()
                    if "ATIVA" in situacao:
                        self.stats.empresas_ativas += 1
                        return self._normalizar(data)

                elif response.status_code == 429:
                    self.stats.rate_limited += 1
                    await asyncio.sleep(2)  # Rate limit - esperar

                elif response.status_code != 404:
                    self.stats.erros += 1

            except httpx.TimeoutException:
                self.stats.erros += 1
            except Exception as e:
                self.stats.erros += 1
                logger.debug("fetch_error", cnpj=cnpj[:8], error=str(e))

            # Pequeno delay para não sobrecarregar
            await asyncio.sleep(0.05)
            return None

    def _normalizar(self, data: dict) -> dict:
        """Normaliza dados da empresa"""
        socios = []
        for s in data.get("qsa", []):
            socios.append({
                "nome": s.get("nome_socio"),
                "qualificacao": s.get("qualificacao_socio"),
                "data_entrada": s.get("data_entrada_sociedade"),
                "faixa_etaria": s.get("faixa_etaria"),
                "pais_origem": s.get("pais"),
            })

        self.stats.socios_coletados += len(socios)

        porte_map = {
            "MICRO EMPRESA": "micro",
            "EMPRESA DE PEQUENO PORTE": "pequena",
            "DEMAIS": "media_grande",
        }

        return {
            "cnpj": data.get("cnpj"),
            "razao_social": data.get("razao_social"),
            "nome_fantasia": data.get("nome_fantasia") or data.get("razao_social"),
            "natureza_juridica": data.get("natureza_juridica"),
            "situacao_cadastral": data.get("descricao_situacao_cadastral"),
            "data_abertura": data.get("data_inicio_atividade"),
            "capital_social": data.get("capital_social"),
            "porte": porte_map.get(data.get("porte", ""), data.get("porte")),
            "cnae_principal": data.get("cnae_fiscal"),
            "cnae_descricao": data.get("cnae_fiscal_descricao"),
            "cnaes_secundarios": [
                {"codigo": c.get("codigo"), "descricao": c.get("descricao")}
                for c in data.get("cnaes_secundarios", [])
            ],
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "complemento": data.get("complemento"),
            "bairro": data.get("bairro"),
            "cidade": data.get("municipio"),
            "estado": data.get("uf"),
            "cep": data.get("cep"),
            "telefone": data.get("ddd_telefone_1"),
            "email": data.get("email"),
            "fundadores": socios,
            "raw_data": data,
            "coletado_em": datetime.now().isoformat(),
        }

    async def salvar_batch(self):
        """Salva lote de empresas"""
        if not self.batch_buffer:
            return

        self.batch_count += 1

        # Salvar em arquivo JSON
        filename = self.output_dir / f"empresas_batch_{self.batch_count:06d}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.batch_buffer, f, ensure_ascii=False, indent=2)

        self.stats.empresas_salvas += len(self.batch_buffer)
        logger.info(
            "batch_salvo",
            arquivo=filename.name,
            empresas=len(self.batch_buffer),
            total=self.stats.empresas_salvas,
        )

        # Se tiver Supabase, inserir também no banco
        if self.supabase:
            try:
                records = []
                for empresa in self.batch_buffer:
                    record = {k: v for k, v in empresa.items() if k != "raw_data"}
                    record["raw_cnpj_data"] = empresa.get("raw_data")
                    records.append(record)

                self.supabase.table("dim_empresas").upsert(
                    records, on_conflict="cnpj"
                ).execute()

            except Exception as e:
                logger.warning("supabase_insert_error", error=str(e))

        self.batch_buffer = []

    def salvar_checkpoint(self):
        """Salva checkpoint para retomar"""
        checkpoint = {
            "cnpjs_processados": list(self.cnpjs_processados)[-10000:],  # Últimos 10k
            "stats": {
                "started_at": self.stats.started_at,
                "cnpjs_tentados": self.stats.cnpjs_tentados,
                "empresas_encontradas": self.stats.empresas_encontradas,
                "empresas_ativas": self.stats.empresas_ativas,
                "empresas_salvas": self.stats.empresas_salvas,
                "socios_coletados": self.stats.socios_coletados,
                "erros": self.stats.erros,
            },
            "batch_count": self.batch_count,
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.checkpoint_path, "w") as f:
            json.dump(checkpoint, f)

    def carregar_checkpoint(self) -> bool:
        """Carrega checkpoint anterior"""
        if not self.checkpoint_path.exists():
            return False

        try:
            with open(self.checkpoint_path) as f:
                checkpoint = json.load(f)

            self.cnpjs_processados = set(checkpoint.get("cnpjs_processados", []))
            self.batch_count = checkpoint.get("batch_count", 0)

            stats = checkpoint.get("stats", {})
            self.stats.started_at = stats.get("started_at", "")
            self.stats.cnpjs_tentados = stats.get("cnpjs_tentados", 0)
            self.stats.empresas_encontradas = stats.get("empresas_encontradas", 0)
            self.stats.empresas_ativas = stats.get("empresas_ativas", 0)
            self.stats.empresas_salvas = stats.get("empresas_salvas", 0)
            self.stats.socios_coletados = stats.get("socios_coletados", 0)

            logger.info(
                "checkpoint_carregado",
                empresas_salvas=self.stats.empresas_salvas,
                batch_count=self.batch_count,
            )
            return True

        except Exception as e:
            logger.warning("checkpoint_load_error", error=str(e))
            return False

    def log_progresso(self):
        """Loga progresso atual"""
        elapsed = datetime.now() - datetime.fromisoformat(self.stats.started_at)
        rate = self.stats.empresas_salvas / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0

        # Estimativa de conclusão
        meta = 1_465_000
        restante = meta - self.stats.empresas_salvas
        tempo_restante = restante / rate if rate > 0 else 0
        horas_restantes = tempo_restante / 3600

        logger.info(
            "progresso",
            tentados=self.stats.cnpjs_tentados,
            encontrados=self.stats.empresas_encontradas,
            ativos=self.stats.empresas_ativas,
            salvos=self.stats.empresas_salvas,
            socios=self.stats.socios_coletados,
            erros=self.stats.erros,
            rate=f"{rate:.1f}/s",
            elapsed=str(elapsed).split(".")[0],
            meta=f"{self.stats.empresas_salvas:,}/{meta:,}",
            eta=f"{horas_restantes:.1f}h" if horas_restantes > 0 else "N/A",
        )

    async def coletar_regiao(
        self, client: httpx.AsyncClient, uf: str, quantidade: int
    ):
        """Coleta empresas de uma região"""
        logger.info("coletando_regiao", uf=uf, quantidade=quantidade)

        cnpjs = gerar_cnpjs_regiao(uf, quantidade)

        tasks = []
        for cnpj in cnpjs:
            if cnpj not in self.cnpjs_processados:
                tasks.append(self.fetch_cnpj(client, cnpj))
                self.cnpjs_processados.add(cnpj)

        results = await asyncio.gather(*tasks)

        for empresa in results:
            if empresa:
                self.batch_buffer.append(empresa)

                if len(self.batch_buffer) >= BATCH_SIZE:
                    await self.salvar_batch()

    async def run(self, resume: bool = True):
        """Executa a coleta"""
        if resume:
            self.carregar_checkpoint()

        if not self.stats.started_at:
            self.stats.started_at = datetime.now().isoformat()

        logger.info(
            "coleta_iniciada",
            workers=NUM_WORKERS,
            batch_size=BATCH_SIZE,
            meta="1.465.000 empresas",
        )

        # Ordem das UFs por importância econômica
        ufs_ordem = [
            "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "GO",
            "DF", "ES", "PA", "MA", "MT", "MS", "PB", "RN", "AL", "PI",
            "SE", "AM", "RO", "AC", "AP", "RR", "TO"
        ]

        # CNPJs por UF (proporcional à economia)
        cnpjs_por_uf = {
            "SP": 500000, "RJ": 200000, "MG": 150000, "RS": 100000,
            "PR": 80000, "SC": 60000, "BA": 60000, "PE": 40000,
            "CE": 40000, "GO": 40000, "DF": 40000, "ES": 30000,
            "PA": 25000, "MA": 20000, "MT": 20000, "MS": 15000,
            "PB": 15000, "RN": 15000, "AL": 10000, "PI": 10000,
            "SE": 10000, "AM": 15000, "RO": 5000, "AC": 5000,
            "AP": 5000, "RR": 5000, "TO": 5000,
        }

        async with httpx.AsyncClient() as client:
            try:
                for uf in ufs_ordem:
                    quantidade = cnpjs_por_uf.get(uf, 10000)

                    # Coletar em lotes
                    lote_size = 5000
                    for i in range(0, quantidade, lote_size):
                        lote_atual = min(lote_size, quantidade - i)
                        await self.coletar_regiao(client, uf, lote_atual)

                        # Checkpoint e progresso
                        if self.stats.empresas_salvas % CHECKPOINT_INTERVAL == 0:
                            self.salvar_checkpoint()
                            self.log_progresso()

                        # Verificar se atingiu a meta
                        if self.stats.empresas_salvas >= 1_465_000:
                            logger.info("meta_atingida")
                            break

                    if self.stats.empresas_salvas >= 1_465_000:
                        break

            except KeyboardInterrupt:
                logger.info("interrompido_pelo_usuario")
            finally:
                # Salvar último batch
                await self.salvar_batch()
                self.salvar_checkpoint()
                self.log_progresso()

        logger.info("coleta_finalizada", empresas_salvas=self.stats.empresas_salvas)


async def main():
    global NUM_WORKERS

    import argparse

    parser = argparse.ArgumentParser(description="Brasil API Collector")
    parser.add_argument(
        "--no-resume", action="store_true",
        help="Não retomar do checkpoint"
    )
    parser.add_argument(
        "--workers", type=int, default=20,
        help="Número de workers paralelos (default: 20)"
    )
    args = parser.parse_args()

    NUM_WORKERS = args.workers

    collector = BrasilAPICollector()
    await collector.run(resume=not args.no_resume)


if __name__ == "__main__":
    asyncio.run(main())
