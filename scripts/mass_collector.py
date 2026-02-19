#!/usr/bin/env python3
"""
IconsAI - Mass Company Collector
Coleta massiva de empresas para as 27 capitais + 1000 maiores cidades
Meta: ~1.465.000 empresas (1 por CNAE por cidade)

Fontes:
- Casa dos Dados: Busca empresas por município + CNAE
- BrasilAPI: Enriquecimento com dados de sócios
- IBGE: Lista de CNAEs

Author: IconsAI Scraping
"""

import asyncio
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.client import get_supabase
from src.scrapers.brasil_api import BrasilAPIClient

logger = structlog.get_logger()

# 27 Capitais brasileiras (código IBGE)
CAPITAIS = {
    "1100205": "Porto Velho",
    "1200401": "Rio Branco",
    "1302603": "Manaus",
    "1400100": "Boa Vista",
    "1501402": "Belém",
    "1600303": "Macapá",
    "1721000": "Palmas",
    "2111300": "São Luís",
    "2211001": "Teresina",
    "2304400": "Fortaleza",
    "2408102": "Natal",
    "2507507": "João Pessoa",
    "2611606": "Recife",
    "2704302": "Maceió",
    "2800308": "Aracaju",
    "2927408": "Salvador",
    "3106200": "Belo Horizonte",
    "3205309": "Vitória",
    "3304557": "Rio de Janeiro",
    "3550308": "São Paulo",
    "4106902": "Curitiba",
    "4205407": "Florianópolis",
    "4314902": "Porto Alegre",
    "5002704": "Campo Grande",
    "5103403": "Cuiabá",
    "5208707": "Goiânia",
    "5300108": "Brasília",
}


class CasaDadosClient:
    """Cliente para API Casa dos Dados (dados abertos CNPJ)"""

    BASE_URL = "https://api.casadosdados.com.br/v2/public/cnpj"

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(timeout=timeout)
        self.stats = {"requests": 0, "success": 0, "errors": 0}

    async def search(
        self,
        municipio: str,
        cnae: str,
        page: int = 1,
        limit: int = 1,
    ) -> list[dict]:
        """
        Busca empresas por município e CNAE

        Args:
            municipio: Nome do município
            cnae: Código CNAE (7 dígitos)
            page: Página de resultados
            limit: Número de resultados por página

        Returns:
            Lista de empresas encontradas
        """
        self.stats["requests"] += 1

        try:
            response = await self.client.post(
                f"{self.BASE_URL}/search",
                json={
                    "query": {
                        "termo": [],
                        "atividade_principal": [cnae],
                        "municipio": [municipio],
                        "situacao_cadastral": "ATIVA",
                    },
                    "extras": {"somente_mei": False, "excluir_mei": False},
                    "page": page,
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            self.stats["success"] += 1
            return data.get("data", {}).get("cnpj", [])[:limit]
        except httpx.HTTPStatusError as e:
            self.stats["errors"] += 1
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                await asyncio.sleep(5)
                return await self.search(municipio, cnae, page, limit)
            logger.warning("casadados_error", status=e.response.status_code)
            return []
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("casadados_exception", error=str(e))
            return []

    async def close(self):
        await self.client.aclose()


class MassCollector:
    """Coletor massivo de empresas"""

    def __init__(self):
        self.supabase = get_supabase()
        self.brasil_api = BrasilAPIClient()
        self.casadados = CasaDadosClient()
        self.cnaes: list[dict] = []
        self.cidades: list[dict] = []
        self.stats = {
            "total_inserted": 0,
            "total_errors": 0,
            "total_socios": 0,
            "start_time": None,
            "last_checkpoint": None,
        }
        self.checkpoint_file = Path(__file__).parent / ".mass_collector_checkpoint"

    async def load_cnaes(self) -> list[dict]:
        """Carrega CNAEs do IBGE"""
        logger.info("loading_cnaes")

        # Tentar carregar do banco primeiro
        if self.supabase:
            result = self.supabase.table("raw_cnae").select("*").execute()
            if result.data:
                self.cnaes = result.data
                logger.info("cnaes_loaded_from_db", count=len(self.cnaes))
                return self.cnaes

        # Fallback: buscar da API IBGE
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                "https://servicodados.ibge.gov.br/api/v2/cnae/subclasses"
            )
            response.raise_for_status()
            data = response.json()

            self.cnaes = [
                {"codigo": item["id"], "descricao": item.get("descricao", "")}
                for item in data
            ]
            logger.info("cnaes_loaded_from_ibge", count=len(self.cnaes))
            return self.cnaes

    async def load_cidades(self) -> list[dict]:
        """Carrega lista de cidades (27 capitais + 1000 maiores)"""
        logger.info("loading_cidades")

        # Primeiro: as 27 capitais
        self.cidades = [
            {"codigo_ibge": codigo, "nome": nome, "tipo": "capital"}
            for codigo, nome in CAPITAIS.items()
        ]

        # Tentar carregar mais cidades do brasil-data-hub ou IBGE
        if self.supabase:
            # Buscar 1000 maiores cidades por população
            result = (
                self.supabase.table("geo_municipios")
                .select("codigo_ibge, nome, populacao, uf")
                .order("populacao", desc=True)
                .limit(1027)  # 1000 + capitais para garantir cobertura
                .execute()
            )

            if result.data:
                # Filtrar para não duplicar capitais
                codigos_capitais = set(CAPITAIS.keys())
                for cidade in result.data:
                    codigo = str(cidade.get("codigo_ibge", ""))
                    if codigo not in codigos_capitais:
                        self.cidades.append(
                            {
                                "codigo_ibge": codigo,
                                "nome": cidade.get("nome"),
                                "uf": cidade.get("uf"),
                                "populacao": cidade.get("populacao"),
                                "tipo": "grande",
                            }
                        )
                        if len(self.cidades) >= 1027:
                            break

        # Se não conseguiu do banco, usar lista fixa das maiores
        if len(self.cidades) < 100:
            await self._load_cidades_ibge()

        logger.info("cidades_loaded", count=len(self.cidades))
        return self.cidades

    async def _load_cidades_ibge(self):
        """Fallback: carregar cidades da API IBGE"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
            )
            response.raise_for_status()
            data = response.json()

            # Ordenar por código IBGE (proxy para tamanho)
            # Em produção, seria melhor ter dados de população
            random.shuffle(data)  # Aleatorizar para distribuir geograficamente

            codigos_existentes = {c["codigo_ibge"] for c in self.cidades}
            for mun in data[:1000]:
                codigo = str(mun.get("id", ""))
                if codigo not in codigos_existentes:
                    self.cidades.append(
                        {
                            "codigo_ibge": codigo,
                            "nome": mun.get("nome"),
                            "uf": mun.get("microrregiao", {})
                            .get("mesorregiao", {})
                            .get("UF", {})
                            .get("sigla"),
                            "tipo": "municipio",
                        }
                    )

    def _save_checkpoint(self, cidade_idx: int, cnae_idx: int):
        """Salva checkpoint para retomar em caso de falha"""
        self.checkpoint_file.write_text(f"{cidade_idx},{cnae_idx}")
        self.stats["last_checkpoint"] = datetime.now().isoformat()

    def _load_checkpoint(self) -> tuple[int, int]:
        """Carrega último checkpoint"""
        if self.checkpoint_file.exists():
            content = self.checkpoint_file.read_text().strip()
            if content:
                parts = content.split(",")
                return int(parts[0]), int(parts[1])
        return 0, 0

    async def collect_company(
        self, cidade: dict, cnae: dict
    ) -> dict[str, Any] | None:
        """
        Coleta uma empresa para a combinação cidade+CNAE

        Args:
            cidade: Dicionário com dados da cidade
            cnae: Dicionário com código e descrição do CNAE

        Returns:
            Dados da empresa ou None se não encontrada
        """
        nome_cidade = cidade.get("nome", "")
        codigo_cnae = str(cnae.get("codigo", "")).replace("-", "").replace("/", "")

        # Buscar empresa na Casa dos Dados
        empresas = await self.casadados.search(
            municipio=nome_cidade, cnae=codigo_cnae, limit=1
        )

        if not empresas:
            return None

        empresa = empresas[0]
        cnpj = empresa.get("cnpj", "")

        if not cnpj:
            return None

        # Enriquecer com BrasilAPI para pegar sócios
        try:
            dados_completos = await self.brasil_api.get_cnpj(cnpj)
            if dados_completos:
                dados_completos["fonte_busca"] = "casadados"
                dados_completos["cidade_busca"] = nome_cidade
                dados_completos["cnae_busca"] = codigo_cnae
                return dados_completos
        except Exception as e:
            logger.warning("brasil_api_enrich_error", cnpj=cnpj[:8], error=str(e))

        # Retornar dados básicos se BrasilAPI falhar
        return {
            "cnpj": cnpj,
            "razao_social": empresa.get("razao_social"),
            "nome_fantasia": empresa.get("nome_fantasia"),
            "situacao_cadastral": empresa.get("situacao_cadastral"),
            "cnae_principal": {"codigo": codigo_cnae, "descricao": cnae.get("descricao")},
            "endereco": {
                "municipio": nome_cidade,
                "uf": cidade.get("uf"),
            },
            "socios": [],
            "fonte_busca": "casadados",
            "cidade_busca": nome_cidade,
            "cnae_busca": codigo_cnae,
        }

    async def insert_empresa(self, empresa: dict) -> bool:
        """Insere empresa no Supabase"""
        if not self.supabase:
            logger.error("supabase_not_configured")
            return False

        cnpj = empresa.get("cnpj", "")
        if not cnpj:
            return False

        try:
            # Verificar se já existe
            existing = (
                self.supabase.table("dim_empresas")
                .select("id")
                .eq("cnpj", cnpj)
                .execute()
            )

            if existing.data:
                logger.debug("empresa_exists", cnpj=cnpj[:8])
                return False

            # Preparar dados para inserção
            cnae_principal = empresa.get("cnae_principal", {})
            endereco = empresa.get("endereco", {})
            socios = empresa.get("socios", [])

            record = {
                "cnpj": cnpj,
                "razao_social": empresa.get("razao_social"),
                "nome_fantasia": empresa.get("nome_fantasia"),
                "situacao_cadastral": empresa.get("situacao_cadastral"),
                "data_abertura": empresa.get("data_abertura"),
                "capital_social": empresa.get("capital_social"),
                "porte": empresa.get("porte"),
                "natureza_juridica": empresa.get("natureza_juridica"),
                "cnae_principal": cnae_principal.get("codigo"),
                "cnae_descricao": cnae_principal.get("descricao"),
                "cnaes_secundarios": empresa.get("cnaes_secundarios"),
                "logradouro": endereco.get("logradouro"),
                "numero": endereco.get("numero"),
                "complemento": endereco.get("complemento"),
                "bairro": endereco.get("bairro"),
                "cidade": endereco.get("municipio"),
                "estado": endereco.get("uf"),
                "cep": endereco.get("cep"),
                "telefone": empresa.get("telefone"),
                "email": empresa.get("email"),
                # Armazenar fundadores/sócios no campo JSONB
                "fundadores": [
                    {
                        "nome": s.get("nome"),
                        "cargo": s.get("qualificacao"),
                        "data_entrada": s.get("data_entrada"),
                    }
                    for s in socios
                ],
                "raw_cnpj_data": empresa.get("raw_data"),
            }

            # Inserir empresa
            result = self.supabase.table("dim_empresas").insert(record).execute()

            if result.data:
                empresa_id = result.data[0].get("id")
                self.stats["total_inserted"] += 1
                self.stats["total_socios"] += len(socios)

                # Inserir sócios como pessoas
                await self._insert_socios(empresa_id, socios)

                return True

        except Exception as e:
            self.stats["total_errors"] += 1
            logger.warning("insert_error", cnpj=cnpj[:8], error=str(e))

        return False

    async def _insert_socios(self, empresa_id: int, socios: list[dict]):
        """Insere sócios como pessoas vinculadas à empresa"""
        if not socios or not self.supabase:
            return

        for socio in socios:
            nome = socio.get("nome", "").strip()
            if not nome or nome == "":
                continue

            try:
                # Separar nome
                partes = nome.split()
                primeiro_nome = partes[0] if partes else nome
                sobrenome = " ".join(partes[1:]) if len(partes) > 1 else ""

                # Verificar se pessoa já existe
                existing = (
                    self.supabase.table("dim_pessoas")
                    .select("id")
                    .eq("nome_completo", nome)
                    .execute()
                )

                if existing.data:
                    pessoa_id = existing.data[0]["id"]
                else:
                    # Inserir nova pessoa
                    pessoa_record = {
                        "nome_completo": nome,
                        "primeiro_nome": primeiro_nome,
                        "sobrenome": sobrenome,
                        "cargo_atual": socio.get("qualificacao"),
                        "empresa_atual_id": empresa_id,
                    }
                    result = (
                        self.supabase.table("dim_pessoas")
                        .insert(pessoa_record)
                        .execute()
                    )
                    if result.data:
                        pessoa_id = result.data[0]["id"]
                    else:
                        continue

                # Registrar evento de vínculo
                evento = {
                    "pessoa_id": pessoa_id,
                    "empresa_id": empresa_id,
                    "tipo_evento": "emprego",
                    "titulo": socio.get("qualificacao", "Sócio"),
                    "data_inicio": socio.get("data_entrada"),
                    "atual": True,
                }
                self.supabase.table("fato_eventos_pessoa").insert(evento).execute()

            except Exception as e:
                logger.debug("socio_insert_error", nome=nome[:20], error=str(e))

    async def run(self, resume: bool = True):
        """
        Executa a coleta massiva

        Args:
            resume: Se True, retoma do último checkpoint
        """
        self.stats["start_time"] = datetime.now().isoformat()

        logger.info("mass_collector_starting")

        # Carregar dados de referência
        await self.load_cnaes()
        await self.load_cidades()

        if not self.cnaes:
            logger.error("no_cnaes_loaded")
            return

        if not self.cidades:
            logger.error("no_cidades_loaded")
            return

        total_combinacoes = len(self.cidades) * len(self.cnaes)
        logger.info(
            "collection_plan",
            cidades=len(self.cidades),
            cnaes=len(self.cnaes),
            total_combinacoes=total_combinacoes,
        )

        # Retomar do checkpoint se solicitado
        start_cidade, start_cnae = (0, 0)
        if resume:
            start_cidade, start_cnae = self._load_checkpoint()
            if start_cidade > 0 or start_cnae > 0:
                logger.info(
                    "resuming_from_checkpoint",
                    cidade_idx=start_cidade,
                    cnae_idx=start_cnae,
                )

        # Loop principal
        for cidade_idx, cidade in enumerate(self.cidades[start_cidade:], start_cidade):
            cnae_start = start_cnae if cidade_idx == start_cidade else 0

            for cnae_idx, cnae in enumerate(self.cnaes[cnae_start:], cnae_start):
                try:
                    # Coletar empresa
                    empresa = await self.collect_company(cidade, cnae)

                    if empresa:
                        await self.insert_empresa(empresa)

                    # Rate limiting - delay entre requisições
                    await asyncio.sleep(0.1)  # 100ms entre requests

                    # Checkpoint a cada 100 combinações
                    if (cidade_idx * len(self.cnaes) + cnae_idx) % 100 == 0:
                        self._save_checkpoint(cidade_idx, cnae_idx)
                        self._log_progress(cidade_idx, cnae_idx, total_combinacoes)

                except KeyboardInterrupt:
                    logger.info("interrupted_by_user")
                    self._save_checkpoint(cidade_idx, cnae_idx)
                    return
                except Exception as e:
                    logger.warning(
                        "collection_error",
                        cidade=cidade.get("nome"),
                        cnae=cnae.get("codigo"),
                        error=str(e),
                    )
                    self.stats["total_errors"] += 1

        # Finalização
        self._log_final_stats()
        self.checkpoint_file.unlink(missing_ok=True)

    def _log_progress(self, cidade_idx: int, cnae_idx: int, total: int):
        """Loga progresso atual"""
        processed = cidade_idx * len(self.cnaes) + cnae_idx
        pct = (processed / total) * 100 if total > 0 else 0

        logger.info(
            "collection_progress",
            processed=processed,
            total=total,
            percent=f"{pct:.2f}%",
            inserted=self.stats["total_inserted"],
            errors=self.stats["total_errors"],
            socios=self.stats["total_socios"],
        )

    def _log_final_stats(self):
        """Loga estatísticas finais"""
        logger.info(
            "collection_complete",
            total_inserted=self.stats["total_inserted"],
            total_errors=self.stats["total_errors"],
            total_socios=self.stats["total_socios"],
            start_time=self.stats["start_time"],
            end_time=datetime.now().isoformat(),
            casadados_stats=self.casadados.stats,
        )

    async def close(self):
        """Fecha conexões"""
        await self.casadados.close()


async def main():
    """Ponto de entrada principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Mass Company Collector")
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Não retomar do checkpoint, começar do zero",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Modo teste: coleta apenas 10 empresas",
    )
    args = parser.parse_args()

    collector = MassCollector()

    try:
        if args.test:
            # Modo teste: limitar para 10 empresas
            await collector.load_cnaes()
            await collector.load_cidades()
            collector.cnaes = collector.cnaes[:10]
            collector.cidades = collector.cidades[:1]
            logger.info("test_mode", cidades=1, cnaes=10)

        await collector.run(resume=not args.no_resume)
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
