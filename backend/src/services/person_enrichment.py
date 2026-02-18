"""
Person Enrichment Service
Extrai e processa experiências de pessoas do Apollo e Perplexity

Fluxo:
1. Apollo (primário) - busca pessoa e extrai experiências
2. Perplexity (fallback) - pesquisa perfil profissional
3. Salva em fato_eventos_pessoa
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
import structlog

from supabase import Client

logger = structlog.get_logger()


class PersonEnrichmentService:
    """Serviço para enriquecimento de dados de pessoas."""

    def __init__(
        self,
        supabase: Client,
        apollo_api_key: str | None = None,
        perplexity_api_key: str | None = None,
    ):
        """
        Inicializa o serviço.

        Args:
            supabase: Cliente Supabase
            apollo_api_key: API key do Apollo
            perplexity_api_key: API key do Perplexity
        """
        self.supabase = supabase
        self.apollo_api_key = apollo_api_key
        self.perplexity_api_key = perplexity_api_key
        self.apollo_base_url = "https://api.apollo.io/v1"
        self.perplexity_base_url = "https://api.perplexity.ai"

    async def enrich_person(
        self,
        pessoa_id: str,
        nome: str,
        empresa_nome: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Enriquece dados de uma pessoa.

        Args:
            pessoa_id: ID da pessoa no banco
            nome: Nome completo
            empresa_nome: Nome da empresa (opcional)
            linkedin_url: URL do LinkedIn (opcional)

        Returns:
            Dados enriquecidos
        """
        result = {
            "pessoa_id": pessoa_id,
            "source": None,
            "experiences": [],
            "education": [],
            "success": False,
        }

        # 1. Tentar Apollo primeiro
        if self.apollo_api_key:
            apollo_data = await self._fetch_from_apollo(nome, empresa_nome)
            if apollo_data:
                result["source"] = "apollo"
                result["experiences"] = self._extract_apollo_experiences(apollo_data)
                result["education"] = self._extract_apollo_education(apollo_data)
                result["raw_data"] = apollo_data
                result["success"] = True

                # Salvar experiências
                await self._save_experiences(
                    pessoa_id, result["experiences"], "emprego"
                )
                await self._save_experiences(pessoa_id, result["education"], "educacao")

                return result

        # 2. Fallback para Perplexity
        if self.perplexity_api_key:
            perplexity_data = await self._fetch_from_perplexity(
                nome, empresa_nome, linkedin_url
            )
            if perplexity_data:
                result["source"] = "perplexity"
                result["experiences"] = perplexity_data.get("experiences", [])
                result["education"] = perplexity_data.get("education", [])
                result["raw_data"] = perplexity_data
                result["success"] = True

                # Salvar experiências
                await self._save_experiences(
                    pessoa_id, result["experiences"], "emprego"
                )
                await self._save_experiences(pessoa_id, result["education"], "educacao")

                return result

        logger.warning("person_enrichment_failed", nome=nome, empresa=empresa_nome)
        return result

    async def _fetch_from_apollo(
        self, nome: str, empresa_nome: str | None
    ) -> dict[str, Any] | None:
        """
        Busca pessoa no Apollo.

        Args:
            nome: Nome da pessoa
            empresa_nome: Nome da empresa

        Returns:
            Dados do Apollo ou None
        """
        name_parts = nome.strip().split()
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else name_parts[0]

        payload = {
            "first_name": first_name,
            "last_name": last_name,
        }

        if empresa_nome:
            payload["organization_name"] = empresa_nome

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.apollo_base_url}/people/match",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-Key": self.apollo_api_key,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("person")

        except Exception as e:
            logger.error("apollo_request_error", error=str(e))

        return None

    async def _fetch_from_perplexity(
        self,
        nome: str,
        empresa_nome: str | None,
        linkedin_url: str | None,
    ) -> dict[str, Any] | None:
        """
        Busca informações da pessoa via Perplexity.

        Args:
            nome: Nome da pessoa
            empresa_nome: Nome da empresa
            linkedin_url: URL do LinkedIn

        Returns:
            Dados estruturados ou None
        """
        query = f"Histórico profissional e acadêmico de {nome}"
        if empresa_nome:
            query += f" da empresa {empresa_nome}"
        if linkedin_url:
            query += f". LinkedIn: {linkedin_url}"

        query += ". Liste experiências profissionais (empresa, cargo, período) e formação acadêmica (instituição, curso, ano)."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.perplexity_base_url}/chat/completions",
                    json={
                        "model": "llama-3.1-sonar-small-128k-online",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Você é um assistente que pesquisa informações profissionais. "
                                "Retorne APENAS JSON com a estrutura: "
                                '{"experiences": [{"company": "", "title": "", "start_date": "", "end_date": "", "current": false}], '
                                '"education": [{"institution": "", "degree": "", "field": "", "year": ""}]}',
                            },
                            {"role": "user", "content": query},
                        ],
                    },
                    headers={
                        "Authorization": f"Bearer {self.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    # Tentar extrair JSON da resposta
                    return self._parse_perplexity_response(content)

        except Exception as e:
            logger.error("perplexity_request_error", error=str(e))

        return None

    def _extract_apollo_experiences(
        self, person_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extrai experiências profissionais do Apollo.

        Args:
            person_data: Dados da pessoa do Apollo

        Returns:
            Lista de experiências
        """
        experiences = []

        # Apollo retorna employment_history em alguns planos
        employment_history = person_data.get("employment_history", [])

        for emp in employment_history:
            experiences.append(
                {
                    "company": emp.get("organization_name"),
                    "title": emp.get("title"),
                    "start_date": emp.get("start_date"),
                    "end_date": emp.get("end_date"),
                    "current": emp.get("current", False),
                    "description": emp.get("description"),
                    "seniority": emp.get("seniority"),
                    "department": emp.get("department"),
                }
            )

        # Se não houver histórico, usar cargo atual
        if not experiences and person_data.get("title"):
            experiences.append(
                {
                    "company": person_data.get("organization_name"),
                    "title": person_data.get("title"),
                    "start_date": None,
                    "end_date": None,
                    "current": True,
                    "seniority": person_data.get("seniority"),
                    "department": (
                        person_data.get("departments", [None])[0]
                        if person_data.get("departments")
                        else None
                    ),
                }
            )

        return experiences

    def _extract_apollo_education(
        self, person_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extrai formação acadêmica do Apollo.

        Args:
            person_data: Dados da pessoa do Apollo

        Returns:
            Lista de formações
        """
        education = []

        # Apollo retorna education em alguns planos
        education_history = person_data.get("education", [])

        for edu in education_history:
            education.append(
                {
                    "institution": edu.get("school_name")
                    or edu.get("organization_name"),
                    "degree": edu.get("degree"),
                    "field": edu.get("field_of_study"),
                    "start_year": edu.get("start_date"),
                    "end_year": edu.get("end_date"),
                }
            )

        return education

    def _parse_perplexity_response(self, content: str) -> dict[str, Any] | None:
        """
        Parseia resposta do Perplexity extraindo JSON.

        Args:
            content: Texto da resposta

        Returns:
            Dados estruturados ou None
        """
        import json

        # Tentar encontrar JSON na resposta
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None

    async def _save_experiences(
        self,
        pessoa_id: str,
        experiences: list[dict[str, Any]],
        tipo_evento: str,
    ) -> None:
        """
        Salva experiências na tabela fato_eventos_pessoa.

        Args:
            pessoa_id: ID da pessoa
            experiences: Lista de experiências
            tipo_evento: Tipo (emprego, educacao)
        """
        for exp in experiences:
            try:
                data = {
                    "pessoa_id": pessoa_id,
                    "tipo_evento": tipo_evento,
                    "titulo": exp.get("title") or exp.get("degree"),
                    "instituicao": exp.get("company") or exp.get("institution"),
                    "atual": exp.get("current", False),
                    "senioridade": exp.get("seniority"),
                    "departamento": exp.get("department"),
                    "grau": exp.get("degree"),
                    "area_estudo": exp.get("field"),
                    "raw_data": exp,
                }

                # Tentar parsear datas
                if exp.get("start_date"):
                    data["data_inicio"] = self._parse_date(exp["start_date"])
                if exp.get("end_date"):
                    data["data_fim"] = self._parse_date(exp["end_date"])
                if exp.get("start_year"):
                    data["data_inicio"] = f"{exp['start_year']}-01-01"
                if exp.get("end_year"):
                    data["data_fim"] = f"{exp['end_year']}-12-31"

                # Calcular duração em meses
                if data.get("data_inicio") and data.get("data_fim"):
                    data["duracao_meses"] = self._calc_duration_months(
                        data["data_inicio"], data["data_fim"]
                    )

                # Upsert (evitar duplicatas)
                self.supabase.table("fato_eventos_pessoa").upsert(
                    data,
                    on_conflict="pessoa_id,tipo_evento,instituicao,titulo",
                ).execute()

            except Exception as e:
                logger.error(
                    "save_experience_error",
                    pessoa_id=pessoa_id,
                    tipo=tipo_evento,
                    error=str(e),
                )

    def _parse_date(self, date_str: str) -> str | None:
        """Parseia string de data para formato ISO."""
        if not date_str:
            return None

        # Tentar vários formatos
        formats = ["%Y-%m-%d", "%Y-%m", "%Y", "%d/%m/%Y", "%m/%Y"]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def _calc_duration_months(self, start: str, end: str) -> int:
        """Calcula duração em meses entre duas datas."""
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            return max(
                1, (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
            )
        except Exception:
            return 0


async def enrich_all_pending_persons(
    supabase: Client,
    apollo_api_key: str | None = None,
    perplexity_api_key: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Enriquece todas as pessoas pendentes no banco.

    Args:
        supabase: Cliente Supabase
        apollo_api_key: API key do Apollo
        perplexity_api_key: API key do Perplexity
        limit: Limite de pessoas a processar

    Returns:
        Estatísticas do processamento
    """
    service = PersonEnrichmentService(supabase, apollo_api_key, perplexity_api_key)

    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    # Buscar pessoas sem experiências cadastradas
    result = supabase.rpc(
        "get_persons_without_experiences",
        {"p_limit": limit},
    ).execute()

    # Fallback se RPC não existir
    if not result.data:
        result = (
            supabase.table("dim_pessoas")
            .select("id, nome_completo, empresa_atual_nome, linkedin_url")
            .is_("raw_apollo_data", "null")
            .limit(limit)
            .execute()
        )

    for pessoa in result.data:
        stats["processed"] += 1

        enrichment = await service.enrich_person(
            pessoa_id=pessoa["id"],
            nome=pessoa["nome_completo"],
            empresa_nome=pessoa.get("empresa_atual_nome"),
            linkedin_url=pessoa.get("linkedin_url"),
        )

        if enrichment["success"]:
            stats["success"] += 1
        else:
            stats["failed"] += 1

    return stats
