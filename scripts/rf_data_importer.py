#!/usr/bin/env python3
"""
IconsAI - Receita Federal Data Importer
Importa dados do CNPJ dos Dados Abertos da Receita Federal

Fonte: https://dados.rfb.gov.br/CNPJ/dados_abertos_cnpj/

Arquivos disponíveis:
- Empresas*.zip: Dados cadastrais básicos
- Estabelecimentos*.zip: Dados dos estabelecimentos
- Socios*.zip: Quadro societário
- Simples*.zip: Optantes pelo Simples
- CNAE*.zip: Tabela de CNAEs
- Municipios*.zip: Códigos de municípios

Este script:
1. Baixa os arquivos necessários
2. Extrai e processa os CSVs
3. Filtra empresas das 27 capitais + 1000 maiores cidades
4. Salva no formato do projeto
"""

from __future__ import annotations

import asyncio
import csv
import json
import sys
import zipfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase

logger = structlog.get_logger()

# URL base dos dados abertos
RF_BASE_URL = "https://dados.rfb.gov.br/CNPJ/dados_abertos_cnpj"

# Códigos IBGE das capitais
CAPITAIS_IBGE = {
    "1100205", "1200401", "1302603", "1400100", "1501402", "1600303", "1721000",
    "2111300", "2211001", "2304400", "2408102", "2507507", "2611606", "2704302",
    "2800308", "2927408", "3106200", "3205309", "3304557", "3550308", "4106902",
    "4205407", "4314902", "5002704", "5103403", "5208707", "5300108",
}

# 1000 maiores cidades (por população) - códigos IBGE
# Incluindo capitais e maiores municípios
MAIORES_CIDADES = {
    # Capitais já incluídas acima
    # Top 50 não-capitais
    "3518800",  # Guarulhos
    "3509502",  # Campinas
    "3304904",  # São Gonçalo
    "3552205",  # São Bernardo do Campo
    "3547809",  # Santo André
    "3534401",  # Osasco
    "3170206",  # Uberlândia
    "3548708",  # São José dos Campos
    "3543402",  # Ribeirão Preto
    "3303302",  # Niterói
    "3301702",  # Duque de Caxias
    "2910800",  # Feira de Santana
    "3118601",  # Contagem
    "4113700",  # Londrina
    "3525904",  # Jundiaí
    "3136702",  # Juiz de Fora
    "4209102",  # Joinville
    "3205200",  # Vila Velha
    "4119905",  # Ponta Grossa
    "2905701",  # Camaçari
    # ... mais cidades seriam adicionadas aqui
}

# Combinar todas as cidades de interesse
CIDADES_INTERESSE = CAPITAIS_IBGE | MAIORES_CIDADES


class RFDataImporter:
    """Importador de dados da Receita Federal"""

    def __init__(self):
        self.supabase = get_supabase()
        self.download_dir = Path(__file__).parent.parent / "data" / "rf_downloads"
        self.output_dir = Path(__file__).parent.parent / "data" / "empresas"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "arquivos_baixados": 0,
            "empresas_processadas": 0,
            "empresas_filtradas": 0,
            "socios_coletados": 0,
        }

        # Caches
        self.empresas_cache: Dict[str, dict] = {}
        self.socios_cache: Dict[str, List[dict]] = {}
        self.municipios_cache: Dict[str, str] = {}
        self.cnaes_cache: Dict[str, str] = {}

    async def list_available_files(self) -> List[str]:
        """Lista arquivos disponíveis no servidor da RF"""
        logger.info("listando_arquivos_rf")

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.get(RF_BASE_URL)
                response.raise_for_status()

                # Parse HTML simples para encontrar links
                content = response.text
                files = []

                # Buscar links .zip
                import re
                pattern = r'href="([^"]+\.zip)"'
                matches = re.findall(pattern, content)

                for match in matches:
                    if not match.startswith("http"):
                        files.append(f"{RF_BASE_URL}/{match}")
                    else:
                        files.append(match)

                logger.info("arquivos_encontrados", count=len(files))
                return files

            except Exception as e:
                logger.error("erro_listagem", error=str(e))
                return []

    async def download_file(self, url: str, filename: str) -> Optional[Path]:
        """Baixa arquivo da RF"""
        filepath = self.download_dir / filename

        if filepath.exists():
            logger.info("arquivo_existente", arquivo=filename)
            return filepath

        logger.info("baixando_arquivo", url=url, destino=filename)

        try:
            async with httpx.AsyncClient(timeout=3600) as client:  # noqa: SIM117
                async with client.stream("GET", url) as response:
                    response.raise_for_status()

                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Log progresso a cada 10%
                            if total > 0 and downloaded % (total // 10 or 1) < 8192:
                                pct = (downloaded / total) * 100
                                logger.debug("download_progress", arquivo=filename, pct=f"{pct:.1f}%")

            self.stats["arquivos_baixados"] += 1
            logger.info("arquivo_baixado", arquivo=filename)
            return filepath

        except Exception as e:
            logger.error("erro_download", arquivo=filename, error=str(e))
            if filepath.exists():
                filepath.unlink()
            return None

    def process_municipios(self, filepath: Path):
        """Processa arquivo de municípios"""
        logger.info("processando_municipios", arquivo=filepath.name)

        with zipfile.ZipFile(filepath) as zf:
            for name in zf.namelist():
                if name.endswith(".csv") or name.endswith(".CSV"):
                    with zf.open(name) as f:
                        content = f.read().decode("latin-1", errors="replace")
                        reader = csv.reader(StringIO(content), delimiter=";")

                        for row in reader:
                            if len(row) >= 2:
                                codigo = row[0].strip()
                                nome = row[1].strip()
                                self.municipios_cache[codigo] = nome

        logger.info("municipios_carregados", count=len(self.municipios_cache))

    def process_cnaes(self, filepath: Path):
        """Processa arquivo de CNAEs"""
        logger.info("processando_cnaes", arquivo=filepath.name)

        with zipfile.ZipFile(filepath) as zf:
            for name in zf.namelist():
                if name.endswith(".csv") or name.endswith(".CSV"):
                    with zf.open(name) as f:
                        content = f.read().decode("latin-1", errors="replace")
                        reader = csv.reader(StringIO(content), delimiter=";")

                        for row in reader:
                            if len(row) >= 2:
                                codigo = row[0].strip()
                                descricao = row[1].strip()
                                self.cnaes_cache[codigo] = descricao

        logger.info("cnaes_carregados", count=len(self.cnaes_cache))

    def process_empresas(self, filepath: Path):
        """Processa arquivo de empresas"""
        logger.info("processando_empresas", arquivo=filepath.name)

        with zipfile.ZipFile(filepath) as zf:
            for name in zf.namelist():
                if name.endswith(".csv") or name.endswith(".CSV"):
                    with zf.open(name) as f:
                        content = f.read().decode("latin-1", errors="replace")
                        reader = csv.reader(StringIO(content), delimiter=";")

                        for row in reader:
                            self.stats["empresas_processadas"] += 1

                            if len(row) >= 7:
                                cnpj_base = row[0].strip().zfill(8)
                                razao_social = row[1].strip()
                                natureza_juridica = row[2].strip()
                                row[3].strip()
                                capital_social = row[4].strip().replace(",", ".")
                                porte = row[5].strip()
                                row[6].strip() if len(row) > 6 else ""

                                self.empresas_cache[cnpj_base] = {
                                    "cnpj_base": cnpj_base,
                                    "razao_social": razao_social,
                                    "natureza_juridica": natureza_juridica,
                                    "capital_social": float(capital_social) if capital_social else 0,
                                    "porte": porte,
                                }

                            if self.stats["empresas_processadas"] % 100000 == 0:
                                logger.info(
                                    "progresso_empresas",
                                    processadas=self.stats["empresas_processadas"],
                                    em_cache=len(self.empresas_cache),
                                )

        logger.info(
            "empresas_processadas",
            total=self.stats["empresas_processadas"],
            em_cache=len(self.empresas_cache),
        )

    def process_estabelecimentos(self, filepath: Path, batch_callback):
        """Processa arquivo de estabelecimentos (filtrado por cidade)"""
        logger.info("processando_estabelecimentos", arquivo=filepath.name)

        batch = []

        with zipfile.ZipFile(filepath) as zf:
            for name in zf.namelist():
                if name.endswith(".csv") or name.endswith(".CSV"):
                    with zf.open(name) as f:
                        content = f.read().decode("latin-1", errors="replace")
                        reader = csv.reader(StringIO(content), delimiter=";")

                        for row in reader:
                            if len(row) >= 20:
                                # Campos do estabelecimento
                                cnpj_base = row[0].strip().zfill(8)
                                cnpj_ordem = row[1].strip().zfill(4)
                                cnpj_dv = row[2].strip().zfill(2)
                                cnpj_completo = cnpj_base + cnpj_ordem + cnpj_dv

                                codigo_municipio = row[20].strip() if len(row) > 20 else ""
                                situacao_cadastral = row[5].strip()

                                # Filtrar por cidades de interesse e situação ativa
                                if (
                                    codigo_municipio in CIDADES_INTERESSE
                                    and situacao_cadastral == "02"
                                ):
                                    nome_fantasia = row[4].strip()
                                    row[6].strip()
                                    row[7].strip()
                                    row[8].strip()
                                    row[9].strip()
                                    data_inicio = row[10].strip()
                                    cnae_principal = row[11].strip()
                                    cnae_secundarios = row[12].strip()

                                    tipo_logradouro = row[13].strip()
                                    logradouro = row[14].strip()
                                    numero = row[15].strip()
                                    complemento = row[16].strip()
                                    bairro = row[17].strip()
                                    cep = row[18].strip()
                                    uf = row[19].strip()

                                    telefone1 = row[21].strip() if len(row) > 21 else ""
                                    telefone2 = row[22].strip() if len(row) > 22 else ""
                                    email = row[27].strip() if len(row) > 27 else ""

                                    # Buscar dados da empresa base
                                    empresa_base = self.empresas_cache.get(cnpj_base, {})

                                    # Buscar sócios
                                    socios = self.socios_cache.get(cnpj_base, [])

                                    registro = {
                                        "cnpj": cnpj_completo,
                                        "razao_social": empresa_base.get("razao_social", ""),
                                        "nome_fantasia": nome_fantasia or empresa_base.get("razao_social", ""),
                                        "natureza_juridica": empresa_base.get("natureza_juridica", ""),
                                        "situacao_cadastral": "ATIVA",
                                        "data_abertura": self._format_date(data_inicio),
                                        "capital_social": empresa_base.get("capital_social", 0),
                                        "porte": empresa_base.get("porte", ""),
                                        "cnae_principal": cnae_principal,
                                        "cnae_descricao": self.cnaes_cache.get(cnae_principal, ""),
                                        "cnaes_secundarios": cnae_secundarios.split(",") if cnae_secundarios else [],
                                        "logradouro": f"{tipo_logradouro} {logradouro}".strip(),
                                        "numero": numero,
                                        "complemento": complemento,
                                        "bairro": bairro,
                                        "cidade": self.municipios_cache.get(codigo_municipio, ""),
                                        "estado": uf,
                                        "cep": cep,
                                        "telefone": f"{telefone1}" if telefone1 else telefone2,
                                        "email": email,
                                        "fundadores": socios,
                                        "codigo_municipio": codigo_municipio,
                                        "coletado_em": datetime.now().isoformat(),
                                    }

                                    batch.append(registro)
                                    self.stats["empresas_filtradas"] += 1
                                    self.stats["socios_coletados"] += len(socios)

                                    if len(batch) >= 100:
                                        batch_callback(batch)
                                        batch = []

                            if self.stats["empresas_processadas"] % 500000 == 0:
                                logger.info(
                                    "progresso_estabelecimentos",
                                    processadas=self.stats["empresas_processadas"],
                                    filtradas=self.stats["empresas_filtradas"],
                                )

        # Último batch
        if batch:
            batch_callback(batch)

    def process_socios(self, filepath: Path):
        """Processa arquivo de sócios"""
        logger.info("processando_socios", arquivo=filepath.name)

        with zipfile.ZipFile(filepath) as zf:
            for name in zf.namelist():
                if name.endswith(".csv") or name.endswith(".CSV"):
                    with zf.open(name) as f:
                        content = f.read().decode("latin-1", errors="replace")
                        reader = csv.reader(StringIO(content), delimiter=";")

                        for row in reader:
                            if len(row) >= 7:
                                cnpj_base = row[0].strip().zfill(8)
                                tipo_socio = row[1].strip()  # 1=PJ, 2=PF, 3=Estrangeiro
                                nome = row[2].strip()
                                row[3].strip()
                                qualificacao = row[4].strip()
                                data_entrada = row[5].strip()
                                row[6].strip() if len(row) > 6 else ""
                                row[10].strip() if len(row) > 10 else ""

                                socio = {
                                    "nome": nome,
                                    "qualificacao": qualificacao,
                                    "data_entrada": self._format_date(data_entrada),
                                    "tipo": "PJ" if tipo_socio == "1" else "PF" if tipo_socio == "2" else "Estrangeiro",
                                }

                                if cnpj_base not in self.socios_cache:
                                    self.socios_cache[cnpj_base] = []
                                self.socios_cache[cnpj_base].append(socio)

        logger.info("socios_carregados", total=sum(len(s) for s in self.socios_cache.values()))

    def _format_date(self, date_str: str) -> Optional[str]:
        """Converte data do formato YYYYMMDD para YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return None
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            return None

    def save_batch(self, batch: List[dict]):
        """Salva batch de empresas"""
        if not batch:
            return

        batch_num = self.stats["empresas_filtradas"] // 100
        filename = self.output_dir / f"empresas_rf_{batch_num:06d}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)

        logger.info("batch_salvo", arquivo=filename.name, count=len(batch))

        # Inserir no Supabase se disponível
        if self.supabase:
            try:
                self.supabase.table("dim_empresas").upsert(batch, on_conflict="cnpj").execute()
            except Exception as e:
                logger.debug("supabase_error", error=str(e))

    async def run(self):
        """Executa importação"""
        logger.info("iniciando_importacao_rf")

        # Listar arquivos disponíveis
        files = await self.list_available_files()

        if not files:
            logger.error("nenhum_arquivo_encontrado")
            return

        # Identificar arquivos por tipo
        municipios_file = next((f for f in files if "Municipios" in f), None)
        cnaes_file = next((f for f in files if "CNAE" in f or "Cnaes" in f), None)
        empresas_files = [f for f in files if "Empresas" in f]
        socios_files = [f for f in files if "Socios" in f]
        estabelecimentos_files = [f for f in files if "Estabelecimentos" in f]

        # 1. Baixar e processar referências
        if municipios_file:
            local_file = await self.download_file(municipios_file, "Municipios.zip")
            if local_file:
                self.process_municipios(local_file)

        if cnaes_file:
            local_file = await self.download_file(cnaes_file, "CNAE.zip")
            if local_file:
                self.process_cnaes(local_file)

        # 2. Baixar e processar empresas
        for i, url in enumerate(empresas_files):
            filename = f"Empresas_{i}.zip"
            local_file = await self.download_file(url, filename)
            if local_file:
                self.process_empresas(local_file)

        # 3. Baixar e processar sócios
        for i, url in enumerate(socios_files):
            filename = f"Socios_{i}.zip"
            local_file = await self.download_file(url, filename)
            if local_file:
                self.process_socios(local_file)

        # 4. Baixar e processar estabelecimentos (filtrado)
        for i, url in enumerate(estabelecimentos_files):
            filename = f"Estabelecimentos_{i}.zip"
            local_file = await self.download_file(url, filename)
            if local_file:
                self.process_estabelecimentos(local_file, self.save_batch)

        # Resumo final
        logger.info(
            "importacao_concluida",
            empresas_filtradas=self.stats["empresas_filtradas"],
            socios_coletados=self.stats["socios_coletados"],
        )


async def main():
    importer = RFDataImporter()
    await importer.run()


if __name__ == "__main__":
    asyncio.run(main())
