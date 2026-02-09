"""
Database layer - Supabase integration
"""

from .client import get_supabase, supabase_client
from .dimensional_client import DimensionalClient, get_date_id, get_time_id
from .dimensional_repository import (
    AnalyticsQueryRepository,
    FactApiCallRepository,
    FactCompanyAnalysisRepository,
    FactIndicatorQueryRepository,
    FactNewsRepository,
    FactPersonAnalysisRepository,
    FactSearchRepository,
)
from .repository import (
    CompanyRepository,
    PeopleRepository,
    PoliticianRepository,
    SearchHistoryRepository,
    SearchRepository,
)
from .star_repository import (
    AnaliseEmpresaRepository,
    BuscaRepository,
    ConcorrenteRepository,
    EmpresaRepository,
    EventoPessoaRepository,
    PessoaRepository,
)
from .fontes_repository import (
    FontesDadosRepository,
    get_fontes_repository,
    registrar_fonte_api,
    registrar_fonte_scraping,
)

__all__ = [
    # Client
    "get_supabase",
    "supabase_client",
    # Dimensional
    "DimensionalClient",
    "get_date_id",
    "get_time_id",
    # Fact repositories
    "FactSearchRepository",
    "FactCompanyAnalysisRepository",
    "FactPersonAnalysisRepository",
    "FactNewsRepository",
    "FactIndicatorQueryRepository",
    "FactApiCallRepository",
    "AnalyticsQueryRepository",
    # Operational repositories
    "CompanyRepository",
    "PeopleRepository",
    "PoliticianRepository",
    "SearchHistoryRepository",
    "SearchRepository",
    # Star Schema repositories
    "EmpresaRepository",
    "PessoaRepository",
    "AnaliseEmpresaRepository",
    "EventoPessoaRepository",
    "ConcorrenteRepository",
    "BuscaRepository",
    # Fontes de dados (rastreabilidade)
    "FontesDadosRepository",
    "get_fontes_repository",
    "registrar_fonte_api",
    "registrar_fonte_scraping",
]
