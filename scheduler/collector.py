"""
Data Collector
Automação de coleta de dados empresariais das 27 capitais brasileiras

Execução diária às 2am via APScheduler.
Busca empresas usando MCPs e armazena no Supabase.
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings
from mcp_servers.apollo_mcp import ApolloMCPServer
from mcp_servers.brasil_data_hub_mcp import BrasilDataHubMCPServer
from mcp_servers.brasilapi_mcp import BrasilAPIMCPServer
from mcp_servers.cnpja_mcp import CNPJaMCPServer
from mcp_servers.serper_mcp import SerperMCPServer
from supabase import Client, create_client

logger = structlog.get_logger()


class DataCollector:
    """
    Coletor de dados empresariais.

    Fluxo de coleta:
    1. Buscar lista de capitais via Brasil Data Hub MCP
    2. Para cada capital:
       a. Buscar CNPJs via Serper MCP
       b. Enriquecer dados via BrasilAPI MCP
       c. Buscar executivos via Apollo MCP
       d. Consultar regime tributário via CNPJá MCP
       e. Salvar em dim_empresas, dim_pessoas, fato_*
    """

    def __init__(self):
        """Inicializa o coletor"""
        self.scheduler = AsyncIOScheduler()

        # Supabase principal
        self._supabase: Client | None = None
        if settings.has_supabase:
            self._supabase = create_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )

        # MCPs (lazy initialization)
        self._brasil_data_hub: BrasilDataHubMCPServer | None = None
        self._serper: SerperMCPServer | None = None
        self._brasilapi: BrasilAPIMCPServer | None = None
        self._apollo: ApolloMCPServer | None = None
        self._cnpja: CNPJaMCPServer | None = None

        # Estado
        self._running = False
        self._stats = {
            "last_run": None,
            "companies_collected": 0,
            "people_collected": 0,
            "errors": 0,
        }

    def _init_mcps(self) -> None:
        """Inicializa MCP servers"""
        self._brasil_data_hub = BrasilDataHubMCPServer()
        self._serper = SerperMCPServer()
        self._brasilapi = BrasilAPIMCPServer()
        self._apollo = ApolloMCPServer()
        self._cnpja = CNPJaMCPServer()

    async def get_capitais(self) -> list[dict[str, Any]]:
        """
        Busca lista das 27 capitais brasileiras via MCP.

        Returns:
            Lista de capitais com codigo_ibge, nome, uf
        """
        if not self._brasil_data_hub:
            self._init_mcps()

        result = await self._brasil_data_hub.handle_tool("get_capitais", {})

        # Extrair dados do TextContent
        import json

        text = result[0].text
        data = json.loads(text)

        if data.get("success"):
            return data.get("data", [])

        logger.error("get_capitais_failed", error=data.get("error"))
        return []

    async def collect_capital(
        self, capital: dict[str, Any], dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Coleta empresas de uma capital.

        Args:
            capital: Dados da capital (codigo_ibge, nome, uf)
            dry_run: Se True, não salva no banco

        Returns:
            Estatísticas da coleta
        """
        cidade = capital["nome"]
        uf = capital["uf"]
        codigo_ibge = capital.get("codigo_ibge")

        logger.info(
            "collect_capital_start",
            cidade=cidade,
            uf=uf,
            dry_run=dry_run,
        )

        stats = {
            "cidade": cidade,
            "uf": uf,
            "companies_found": 0,
            "companies_saved": 0,
            "people_saved": 0,
            "errors": [],
        }

        try:
            # 1. Buscar empresas via Serper (empresas destaque da cidade)
            search_queries = [
                f"empresas de tecnologia em {cidade}",
                f"startups {cidade}",
                f"indústrias em {cidade} {uf}",
                f"empresas de serviços {cidade}",
            ]

            companies_cnpjs = set()

            for query in search_queries:
                result = await self._serper.handle_tool(
                    "search_company",
                    {"company_name": query, "cidade": cidade},
                )

                # Extrair possíveis nomes de empresas dos resultados
                import json

                text = result[0].text
                data = json.loads(text)

                if data.get("success"):
                    search_results = data.get("data", {}).get("search_results", [])

                    for item in search_results[:5]:
                        # Tentar extrair nome de empresa do título
                        title = item.get("title", "")
                        # Ignorar se for site genérico
                        if any(
                            x in title.lower()
                            for x in ["lista", "ranking", "melhores", "top"]
                        ):
                            continue

                        # Buscar CNPJ desta empresa
                        cnpj_result = await self._serper.handle_tool(
                            "find_cnpj",
                            {"company_name": title[:50], "cidade": cidade},
                        )

                        cnpj_data = json.loads(cnpj_result[0].text)
                        if cnpj_data.get("success"):
                            cnpj = cnpj_data.get("data", {}).get("cnpj")
                            if cnpj:
                                companies_cnpjs.add(cnpj)
                                stats["companies_found"] += 1

                # Rate limiting
                await asyncio.sleep(1)

            logger.info(
                "collect_capital_cnpjs_found",
                cidade=cidade,
                count=len(companies_cnpjs),
            )

            # 2. Para cada CNPJ, enriquecer e salvar
            for cnpj in list(companies_cnpjs)[:20]:  # Limitar a 20 por capital
                try:
                    company_data = await self._enrich_and_save_company(
                        cnpj, codigo_ibge, dry_run
                    )

                    if company_data:
                        stats["companies_saved"] += 1
                        stats["people_saved"] += company_data.get("people_count", 0)

                except Exception as e:
                    logger.error("enrich_company_error", cnpj=cnpj, error=str(e))
                    stats["errors"].append({"cnpj": cnpj, "error": str(e)})

                # Rate limiting entre empresas
                await asyncio.sleep(2)

        except Exception as e:
            logger.error("collect_capital_error", cidade=cidade, error=str(e))
            stats["errors"].append({"stage": "collection", "error": str(e)})

        logger.info(
            "collect_capital_complete",
            cidade=cidade,
            stats=stats,
        )

        return stats

    async def _enrich_and_save_company(
        self, cnpj: str, codigo_ibge: str | None, dry_run: bool
    ) -> dict[str, Any] | None:
        """
        Enriquece dados de uma empresa e salva no banco.

        Args:
            cnpj: CNPJ da empresa
            codigo_ibge: Código IBGE do município
            dry_run: Se True, não salva no banco

        Returns:
            Dados da empresa ou None se falhou
        """
        import json

        # 1. Buscar dados da Receita Federal via BrasilAPI
        brasilapi_result = await self._brasilapi.handle_tool(
            "get_company", {"cnpj": cnpj}
        )
        brasilapi_data = json.loads(brasilapi_result[0].text)

        if not brasilapi_data.get("success"):
            logger.warning("brasilapi_not_found", cnpj=cnpj)
            return None

        company = brasilapi_data.get("data", {})

        # 2. Buscar LinkedIn da empresa via Serper
        razao_social = company.get("razao_social", "")
        linkedin_result = await self._serper.handle_tool(
            "find_linkedin",
            {"name": razao_social, "type": "company"},
        )
        linkedin_data = json.loads(linkedin_result[0].text)
        linkedin_url = linkedin_data.get("data", {}).get("linkedin_url", "inexistente")

        # 3. Buscar website via Serper
        website_result = await self._serper.handle_tool(
            "find_website", {"company_name": razao_social}
        )
        website_data = json.loads(website_result[0].text)
        website = website_data.get("data", {}).get("website")

        # 4. Consultar regime tributário via CNPJá (se configurado)
        regime_tributario = None
        if self._cnpja._api_key:
            try:
                regime_result = await self._cnpja.handle_tool(
                    "get_regime_tributario", {"cnpj": cnpj}
                )
                regime_data = json.loads(regime_result[0].text)
                if regime_data.get("success"):
                    regime_tributario = regime_data.get("data", {}).get(
                        "regime_tributario"
                    )
            except Exception as e:
                logger.warning("cnpja_regime_fetch_failed", cnpj=cnpj, error=str(e))

        # 5. Preparar dados para salvar
        empresa_data = {
            "cnpj": cnpj,
            "razao_social": razao_social,
            "nome_fantasia": company.get("nome_fantasia"),
            "linkedin": linkedin_url,
            "website": website,
            "endereco": self._format_endereco(company.get("endereco", {})),
            "cidade": company.get("endereco", {}).get("municipio"),
            "estado": company.get("endereco", {}).get("uf"),
            "codigo_ibge": codigo_ibge,
            "fonte": "scheduler",
            "data_coleta": datetime.utcnow().isoformat(),
        }

        # 6. Salvar empresa
        if not dry_run and self._supabase:
            try:
                # Upsert empresa
                result = (
                    self._supabase.table("dim_empresas")
                    .upsert(empresa_data, on_conflict="cnpj")
                    .execute()
                )

                empresa_id = result.data[0]["id"] if result.data else None

                # Salvar regime tributário
                if empresa_id and regime_tributario:
                    regime_data_to_save = {
                        "empresa_id": empresa_id,
                        "regime_tributario": regime_tributario,
                        "porte": company.get("porte"),
                        "natureza_juridica": company.get("natureza_juridica"),
                        "capital_social": company.get("capital_social"),
                        "cnae_principal": company.get("cnae_principal", {}).get(
                            "codigo"
                        ),
                        "cnae_descricao": company.get("cnae_principal", {}).get(
                            "descricao"
                        ),
                    }
                    self._supabase.table("fato_regime_tributario").insert(
                        regime_data_to_save
                    ).execute()

                # Salvar sócios
                people_count = 0
                for socio in company.get("socios", []):
                    pessoa_data = {
                        "nome": socio.get("nome"),
                        "empresa_id": empresa_id,
                        "linkedin_url": "inexistente",
                        "fonte": "brasilapi",
                    }
                    self._supabase.table("dim_pessoas").insert(pessoa_data).execute()
                    people_count += 1

                return {"empresa_id": empresa_id, "people_count": people_count}

            except Exception as e:
                logger.error("save_company_error", cnpj=cnpj, error=str(e))
                return None

        return {
            "cnpj": cnpj,
            "dry_run": True,
            "people_count": len(company.get("socios", [])),
        }

    def _format_endereco(self, endereco: dict[str, Any]) -> str:
        """Formata endereço como string"""
        parts = [
            endereco.get("logradouro"),
            endereco.get("numero"),
            endereco.get("complemento"),
            endereco.get("bairro"),
            endereco.get("municipio"),
            endereco.get("uf"),
            endereco.get("cep"),
        ]
        return ", ".join(filter(None, parts))

    async def run_daily_collection(self) -> dict[str, Any]:
        """
        Execução diária da coleta.

        Coleta empresas de todas as 27 capitais.

        Returns:
            Estatísticas consolidadas
        """
        if self._running:
            logger.warning("collection_already_running")
            return {"status": "already_running"}

        self._running = True
        self._stats["last_run"] = datetime.utcnow().isoformat()

        logger.info("daily_collection_start")

        try:
            self._init_mcps()

            capitais = await self.get_capitais()
            logger.info("capitais_loaded", count=len(capitais))

            all_stats = []

            for capital in capitais:
                try:
                    stats = await self.collect_capital(capital)
                    all_stats.append(stats)

                    self._stats["companies_collected"] += stats["companies_saved"]
                    self._stats["people_collected"] += stats["people_saved"]
                    self._stats["errors"] += len(stats["errors"])

                except Exception as e:
                    logger.error(
                        "capital_collection_error",
                        capital=capital.get("nome"),
                        error=str(e),
                    )

                # Pausa entre capitais (5 minutos)
                await asyncio.sleep(300)

            return {
                "status": "completed",
                "capitais_processed": len(all_stats),
                "companies_collected": self._stats["companies_collected"],
                "people_collected": self._stats["people_collected"],
                "errors": self._stats["errors"],
            }

        finally:
            self._running = False

    def start(self) -> None:
        """Inicia o scheduler"""
        if not settings.scheduler_enabled:
            logger.info("scheduler_disabled")
            return

        self.scheduler.add_job(
            self.run_daily_collection,
            CronTrigger(
                hour=settings.scheduler_hour,
                minute=settings.scheduler_minute,
            ),
            id="daily_collection",
            name="Coleta diária de empresas",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            "scheduler_started",
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute,
        )

    def stop(self) -> None:
        """Para o scheduler"""
        self.scheduler.shutdown()
        logger.info("scheduler_stopped")

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do coletor"""
        return {
            **self._stats,
            "running": self._running,
            "scheduler_enabled": settings.scheduler_enabled,
            "next_run": (
                str(self.scheduler.get_job("daily_collection").next_run_time)
                if self.scheduler.get_job("daily_collection")
                else None
            ),
        }


# CLI para execução manual
async def main():
    """Entry point CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="IconsAI Data Collector")
    parser.add_argument(
        "--capital",
        type=str,
        help="Coletar apenas uma capital (UF)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executar sem salvar no banco",
    )
    parser.add_argument(
        "--show-schedule",
        action="store_true",
        help="Mostrar configuração do scheduler",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Executar coleta completa agora",
    )

    args = parser.parse_args()

    collector = DataCollector()

    if args.show_schedule:
        print(f"Scheduler habilitado: {settings.scheduler_enabled}")
        print(f"Horário: {settings.scheduler_hour:02d}:{settings.scheduler_minute:02d}")
        return

    if args.capital:
        # Coletar apenas uma capital
        collector._init_mcps()
        capitais = await collector.get_capitais()
        capital = next(
            (c for c in capitais if c["uf"] == args.capital.upper()),
            None,
        )
        if capital:
            stats = await collector.collect_capital(capital, dry_run=args.dry_run)
            print(f"Coleta concluída: {stats}")
        else:
            print(f"Capital não encontrada: {args.capital}")
        return

    if args.run_now:
        # Executar coleta completa
        stats = await collector.run_daily_collection()
        print(f"Coleta concluída: {stats}")
        return

    # Iniciar scheduler
    collector.start()

    try:
        # Manter rodando
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        collector.stop()


if __name__ == "__main__":
    asyncio.run(main())
