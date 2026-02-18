"""
Supabase client for database operations
"""

from typing import Optional

import structlog

from config.settings import settings
from supabase import Client, create_client

logger = structlog.get_logger()

_supabase_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client singleton"""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.supabase_url or not settings.supabase_service_key:
        logger.warning("supabase_not_configured")
        return None

    try:
        _supabase_client = create_client(
            settings.supabase_url, settings.supabase_service_key
        )
        logger.info("supabase_connected")
        return _supabase_client
    except Exception as e:
        logger.error("supabase_connection_error", error=str(e))
        return None
