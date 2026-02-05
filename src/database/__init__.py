"""
Database layer - Supabase integration
"""

from .client import get_supabase, supabase_client
from .repository import (
    CompanyRepository,
    PeopleRepository,
    PoliticianRepository,
    SearchHistoryRepository,
    SearchRepository,
)

__all__ = [
    "get_supabase",
    "supabase_client",
    "CompanyRepository",
    "PeopleRepository",
    "PoliticianRepository",
    "SearchHistoryRepository",
    "SearchRepository",
]
