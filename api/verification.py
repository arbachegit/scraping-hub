"""
Backwards-compatibility shim.

All verification functionality has moved to api.auth.verification_service.
This file re-exports for existing imports.
"""

from api.auth.verification_service import create_verification_code, verify_code

__all__ = ["create_verification_code", "verify_code"]
