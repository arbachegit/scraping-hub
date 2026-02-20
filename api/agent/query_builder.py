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
}

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
}


class QueryBuilder:
    """Builds and executes Supabase queries from parsed intents."""

    def __init__(self, supabase_client: Client):
        """
        Initialize the query builder.

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client

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

        try:
            # Start building the query
            query = self.client.table(table_name).select(select_columns, count="exact")

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
def create_query_builder(supabase_client: Client) -> QueryBuilder:
    """
    Create a query builder instance.

    Args:
        supabase_client: Supabase client instance

    Returns:
        QueryBuilder instance
    """
    return QueryBuilder(supabase_client)
