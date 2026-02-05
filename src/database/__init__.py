"""
Database layer - Supabase integration
"""

from .client import get_supabase, supabase_client
from .repository import CompanyRepository, SearchRepository

__all__ = [
    "get_supabase",
    "supabase_client",
    "CompanyRepository",
    "SearchRepository",
]
