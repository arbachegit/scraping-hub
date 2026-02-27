"""
Backwards-compatibility shim.

All audit functionality has moved to api.auth.audit_service.
This file re-exports for existing imports.
"""

from api.auth.audit_service import log_action

__all__ = ["log_action"]
