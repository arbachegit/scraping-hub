"""
Supabase Client
"""

from typing import Optional

import structlog
from supabase import Client, create_client

from config.settings import settings

logger = structlog.get_logger()

_supabase_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """
    Get Supabase client singleton
    Returns None if not configured
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.has_supabase:
        logger.warning("supabase_not_configured")
        return None

    try:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        logger.info("supabase_connected")
        return _supabase_client
    except Exception as e:
        logger.error("supabase_connection_error", error=str(e))
        return None


# Alias
supabase_client = get_supabase
