"""
Audit logging service.

Records user actions for security auditing and compliance.

Moved from api/audit.py to api/auth/audit_service.py
"""

from typing import Any, Dict, Optional

import structlog
from fastapi import Request

from src.database.client import get_supabase

logger = structlog.get_logger()


async def log_action(
    user_id: Optional[int],
    action: str,
    resource: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """Log an auditable action."""
    ip_address = None
    user_agent = None

    if request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    client = get_supabase()
    if not client:
        logger.warning(
            "audit_log_no_db",
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
        )
        return

    try:
        entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        client.table("audit_logs").insert(entry).execute()
        logger.info("audit_logged", action=action, user_id=user_id)
    except Exception as e:
        logger.error(
            "audit_log_failed",
            action=action,
            user_id=user_id,
            error=str(e),
        )
