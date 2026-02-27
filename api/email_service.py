"""
Backwards-compatibility shim.

All email functionality has moved to api.auth.email_service.
This file re-exports for existing imports.
"""

from api.auth.email_service import (
    send_password_reset_email,
    send_set_password_email,
    send_verification_code_email,
)

__all__ = [
    "send_password_reset_email",
    "send_set_password_email",
    "send_verification_code_email",
]
