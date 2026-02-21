"""
Query Builder - Constructs Supabase queries from parsed intents.
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog
from supabase import Client

from api.agent.models import (
    EntityType,
    FilterOperator,
    ParsedIntent,
    QueryFilter,
)

logger = structlog.get_logger()


# Table mappings for each entity type
TABLE_MAPPINGS = {
    EntityType.EMPRESAS: "dim_empresas",
    EntityType.PESSOAS: "dim_pessoas",
    EntityType.NOTICIAS: "dim_noticias",
    EntityType.POLITICOS: "dim_politicos",  # Tabela no brasil-data-hub
}

# Entity types that use external database (fiscal)
EXTERNAL_ENTITIES = {EntityType.POLITICOS}

# Default columns to select for each entity type
SELECT_COLUMNS = {
    EntityType.EMPRESAS: (
        "id, cnpj, razao_social, nome_fantasia, cidade, estado, "
        "cnae_principal, descricao_cnae, porte, regime_tributario, "
        "capital_social, data_abertura, situacao_cadastral, qtd_funcionarios"
    ),
    EntityType.PESSOAS: (
        "id, nome_completo, email, cargo, empresa_id, linkedin_url, telefone"
    ),
    EntityType.NOTICIAS: (
        "id, titulo, resumo, fonte, data_publicacao, segmento, url"
    ),
    # dim_politicos (brasil-data-hub) - Schema real
    EntityType.POLITICOS: (
        "id, cpf, nome_completo, nome_urna, data_nascimento, "
        "sexo, grau_instrucao, ocupacao"
    ),
}

# Valid fields for each entity type (for security)
VALID_FIELDS = {
    EntityType.EMPRESAS: {
        "id", "cnpj", "razao_social", "nome_fantasia", "cidade", "estado",
        "cnae_principal", "descricao_cnae", "porte", "regime_tributario",
        "capital_social", "data_abertura", "situacao_cadastral", "qtd_funcionarios",
        "nome"  # alias for razao_social/nome_fantasia
    },
    EntityType.PESSOAS: {
        "id", "nome_completo", "email", "cargo", "empresa_id", "linkedin_url",
        "telefone", "nome"  # alias for nome_completo
    },
    EntityType.NOTICIAS: {
        "id", "titulo", "resumo", "fonte", "data_publicacao", "segmento", "url",
        "keywords"  # virtual field for searching titulo + resumo
    },
    # dim_politicos (brasil-data-hub) - Schema real
    EntityType.POLITICOS: {
        "id", "cpf", "nome_completo", "nome_urna", "data_nascimento",
        "sexo", "grau_instrucao", "ocupacao",
        "nome",  # alias para nome_completo
        # Campos de mandatos (fato_politicos_mandatos) - buscados via join
        "cargo", "partido_sigla", "partido_nome", "municipio", "codigo_ibge",
        "ano_eleicao", "eleito", "coligacao", "situacao_turno",
    },
}

# Campos que pertencem a fato_politicos_mandatos (não dim_politicos)
MANDATO_FIELDS = {
    "cargo", "partido_sigla", "partido_nome", "municipio", "codigo_ibge",
    "ano_eleicao", "eleito", "coligacao", "situacao_turno", "turno",
    "numero_candidato", "data_inicio_mandato", "data_fim_mandato",
}

# Field aliases (map common names to actual column names)
FIELD_ALIASES = {
    EntityType.EMPRESAS: {
        "nome": "razao_social",
        "name": "razao_social",
        "fantasia": "nome_fantasia",
        "uf": "estado",
        "state": "estado",
        "cnae": "cnae_principal",
        "funcionarios": "qtd_funcionarios",
        "employees": "qtd_funcionarios",
    },
    EntityType.PESSOAS: {
        "nome": "nome_completo",
        "name": "nome_completo",
        "empresa": "empresa_id",
        "linkedin": "linkedin_url",
        "phone": "telefone",
    },
    EntityType.NOTICIAS: {
        "data": "data_publicacao",
        "date": "data_publicacao",
        "source": "fonte",
        "title": "titulo",
        "summary": "resumo",
    },
    # dim_politicos (brasil-data-hub) - Aliases simplificados
    EntityType.POLITICOS: {
        "nome": "nome_completo",
        "name": "nome_completo",
        "nascimento": "data_nascimento",
        "instrucao": "grau_instrucao",
        "escolaridade": "grau_instrucao",
        "partido": "partido_sigla",
        "cidade": "municipio",
    },
}


class QueryBuilder:
    """Builds and executes Supabase queries from parsed intents."""

    def __init__(
        self,
        supabase_client: Client,
        brasil_data_hub_client: Optional[Client] = None,
    ):
        """
        Initialize the query builder.

        Args:
            supabase_client: Supabase client instance (main database)
            brasil_data_hub_client: Optional Supabase client for brasil-data-hub (politicos)
        """
        self.client = supabase_client
        self.brasil_data_hub_client = brasil_data_hub_client

    async def execute(
        self,
        intent: ParsedIntent,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Execute a query based on the parsed intent.

        Args:
            intent: The parsed intent

        Returns:
            Tuple of (results list, total count)
        """
        table_name = TABLE_MAPPINGS.get(intent.entity_type)
        if not table_name:
            logger.error("unknown_entity_type", entity_type=intent.entity_type)
            return [], 0

        select_columns = SELECT_COLUMNS.get(intent.entity_type, "*")

        # Determine which client to use
        if intent.entity_type in EXTERNAL_ENTITIES:
            if not self.brasil_data_hub_client:
                logger.warning("brasil_data_hub_client_not_configured")
                return [], 0
            client = self.brasil_data_hub_client
        else:
            client = self.client

        try:
            # Start building the query
            query = client.table(table_name).select(select_columns, count="exact")

            # Apply filters
            query = self._apply_filters(query, intent)

            # Apply ordering
            if intent.order_by:
                resolved_field = self._resolve_field(intent.entity_type, intent.order_by)
                if resolved_field:
                    query = query.order(resolved_field, desc=intent.order_desc)

            # Apply limit
            query = query.limit(intent.limit)

            # Execute query
            result = query.execute()

            data = result.data or []
            total_count = result.count or len(data)

            logger.info(
                "query_executed",
                entity_type=intent.entity_type,
                filters_count=len(intent.filters),
                results_count=len(data),
                total_count=total_count,
            )

            return data, total_count

        except Exception as e:
            logger.error("query_execution_error", error=str(e))
            return [], 0

    async def fetch_mandatos(
        self,
        politico_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch mandatos history for a specific politician.

        Args:
            politico_id: The UUID of the politician

        Returns:
            List of mandatos records
        """
        if not self.brasil_data_hub_client:
            logger.warning("brasil_data_hub_client_not_configured")
            return []

        try:
            result = self.brasil_data_hub_client.table("fato_politicos_mandatos").select(
                "id, politico_id, codigo_ibge, municipio, cargo, ano_eleicao, "
                "turno, numero_candidato, partido_sigla, partido_nome, coligacao, "
                "situacao_turno, eleito, data_inicio_mandato, data_fim_mandato"
            ).eq("politico_id", politico_id).order("ano_eleicao", desc=True).execute()

            data = result.data or []

            logger.info(
                "mandatos_fetched",
                politico_id=politico_id,
                mandatos_count=len(data),
            )

            return data

        except Exception as e:
            logger.error("mandatos_fetch_error", error=str(e), politico_id=politico_id)
            return []

    async def search_politicos_with_mandatos(
        self,
        intent: ParsedIntent,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search politicians and enrich with their current/latest mandato info.

        This handles two scenarios:
        1. If filters include mandato fields (cargo, partido, municipio), search
           fato_politicos_mandatos first and join with dim_politicos
        2. Otherwise, search dim_politicos first and enrich with mandato info

        Args:
            intent: The parsed intent

        Returns:
            Tuple of (results list with mandato info, total count)
        """
        if not self.brasil_data_hub_client:
            logger.warning("brasil_data_hub_client_not_configured")
            return [], 0

        # Separate filters: politico fields vs mandato fields
        politico_filters = []
        mandato_filters = []

        for f in intent.filters:
            resolved_field = self._resolve_field(intent.entity_type, f.field)
            if resolved_field and resolved_field in MANDATO_FIELDS:
                mandato_filters.append((resolved_field, f))
            else:
                politico_filters.append(f)

        # If we have mandato filters, search mandatos first
        if mandato_filters:
            return await self._search_via_mandatos(
                mandato_filters, politico_filters, intent.limit
            )

        # Otherwise, search politicos first and enrich
        data, total_count = await self.execute(intent)

        if not data:
            return data, total_count

        # Enrich each politician with their latest mandato
        enriched_data = []
        for politico in data:
            politico_id = politico.get("id")
            if politico_id:
                mandatos = await self.fetch_mandatos(politico_id)
                if mandatos:
                    # Get the most recent mandato (already ordered by ano_eleicao desc)
                    latest = mandatos[0]
                    politico["partido_sigla"] = latest.get("partido_sigla")
                    politico["cargo_atual"] = latest.get("cargo")
                    politico["municipio"] = latest.get("municipio")
                    politico["eleito"] = latest.get("eleito")
                    politico["mandatos_count"] = len(mandatos)
            enriched_data.append(politico)

        return enriched_data, total_count

    async def _search_via_mandatos(
        self,
        mandato_filters: List[Tuple[str, QueryFilter]],
        politico_filters: List[QueryFilter],
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search politicians by first querying fato_politicos_mandatos.

        Args:
            mandato_filters: Filters for mandato fields (already resolved)
            politico_filters: Filters for politico fields
            limit: Maximum results to return

        Returns:
            Tuple of (results list with mandato info, total count)
        """
        try:
            # Build query on fato_politicos_mandatos with join to dim_politicos
            query = self.brasil_data_hub_client.table("fato_politicos_mandatos").select(
                "id, cargo, partido_sigla, partido_nome, municipio, codigo_ibge, "
                "ano_eleicao, turno, numero_candidato, eleito, coligacao, situacao_turno, "
                "politico:politico_id (id, cpf, nome_completo, nome_urna, "
                "data_nascimento, sexo, grau_instrucao, ocupacao)",
                count="exact",
            )

            # Apply mandato filters
            for resolved_field, f in mandato_filters:
                query = self._apply_single_filter(query, resolved_field, f)

            # Apply politico filters via nested filter
            for f in politico_filters:
                resolved_field = self._resolve_field(EntityType.POLITICOS, f.field)
                if resolved_field and resolved_field not in MANDATO_FIELDS:
                    # For nested politico fields, use the nested filter syntax
                    nested_field = f"politico.{resolved_field}"
                    if f.operator in (FilterOperator.LIKE, FilterOperator.ILIKE):
                        query = query.ilike(nested_field, f"%{f.value}%")
                    elif f.operator == FilterOperator.EQ:
                        query = query.eq(nested_field, f.value)

            # Order by most recent election
            query = query.order("ano_eleicao", desc=True).limit(limit)

            result = query.execute()
            data = result.data or []
            total_count = result.count or len(data)

            # Flatten the data structure
            flattened = []
            seen_politicos = set()

            for mandato in data:
                politico_data = mandato.pop("politico", {}) or {}
                politico_id = politico_data.get("id")

                # Avoid duplicates (same politico with multiple mandatos)
                if politico_id and politico_id in seen_politicos:
                    continue
                seen_politicos.add(politico_id)

                flattened.append({
                    **politico_data,
                    "partido_sigla": mandato.get("partido_sigla"),
                    "cargo_atual": mandato.get("cargo"),
                    "municipio": mandato.get("municipio"),
                    "codigo_ibge": mandato.get("codigo_ibge"),
                    "ano_eleicao": mandato.get("ano_eleicao"),
                    "eleito": mandato.get("eleito"),
                    "coligacao": mandato.get("coligacao"),
                    "situacao_turno": mandato.get("situacao_turno"),
                })

            logger.info(
                "search_via_mandatos_executed",
                mandato_filters_count=len(mandato_filters),
                politico_filters_count=len(politico_filters),
                results_count=len(flattened),
                total_count=total_count,
            )

            return flattened, len(flattened)

        except Exception as e:
            logger.error("search_via_mandatos_error", error=str(e))
            return [], 0

    def _apply_filters(self, query, intent: ParsedIntent):
        """
        Apply filters to the query.

        Args:
            query: The Supabase query builder
            intent: The parsed intent with filters

        Returns:
            The query with filters applied
        """
        for f in intent.filters:
            resolved_field = self._resolve_field(intent.entity_type, f.field)
            if not resolved_field:
                logger.warning("invalid_filter_field", field=f.field)
                continue

            query = self._apply_single_filter(query, resolved_field, f)

        return query

    def _resolve_field(self, entity_type: EntityType, field: str) -> Optional[str]:
        """
        Resolve a field name, handling aliases.

        Args:
            entity_type: The entity type
            field: The field name (possibly an alias)

        Returns:
            The resolved field name or None if invalid
        """
        field_lower = field.lower()

        # Check aliases first
        aliases = FIELD_ALIASES.get(entity_type, {})
        if field_lower in aliases:
            field_lower = aliases[field_lower]

        # Validate field
        valid_fields = VALID_FIELDS.get(entity_type, set())
        if field_lower not in valid_fields:
            return None

        return field_lower

    def _apply_single_filter(self, query, field: str, filter_obj: QueryFilter):
        """
        Apply a single filter to the query.

        Args:
            query: The Supabase query builder
            field: The resolved field name
            filter_obj: The filter object

        Returns:
            The query with the filter applied
        """
        value = filter_obj.value
        operator = filter_obj.operator

        # Handle special virtual fields
        if field == "keywords" and operator in (FilterOperator.LIKE, FilterOperator.ILIKE):
            # Search in titulo and resumo for noticias
            query = query.or_(f"titulo.ilike.%{value}%,resumo.ilike.%{value}%")
            return query

        # Standard operators
        if operator == FilterOperator.EQ:
            query = query.eq(field, value)
        elif operator == FilterOperator.NEQ:
            query = query.neq(field, value)
        elif operator == FilterOperator.GT:
            query = query.gt(field, value)
        elif operator == FilterOperator.GTE:
            query = query.gte(field, value)
        elif operator == FilterOperator.LT:
            query = query.lt(field, value)
        elif operator == FilterOperator.LTE:
            query = query.lte(field, value)
        elif operator in (FilterOperator.LIKE, FilterOperator.ILIKE):
            query = query.ilike(field, f"%{value}%")
        elif operator == FilterOperator.IN:
            if isinstance(value, list):
                query = query.in_(field, value)
        elif operator == FilterOperator.IS_NULL:
            query = query.is_(field, "null")
        elif operator == FilterOperator.NOT_NULL:
            query = query.not_.is_(field, "null")

        return query


# Global query builder (requires supabase client)
def create_query_builder(
    supabase_client: Client,
    brasil_data_hub_client: Optional[Client] = None,
) -> QueryBuilder:
    """
    Create a query builder instance.

    Args:
        supabase_client: Supabase client instance (main database)
        brasil_data_hub_client: Optional Supabase client for brasil-data-hub (politicos)

    Returns:
        QueryBuilder instance
    """
    return QueryBuilder(supabase_client, brasil_data_hub_client)
