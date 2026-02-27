"""
Backwards-compatibility shim.

All encryption functionality has moved to api.auth.field_encryption.
This file re-exports for existing imports.
"""

from api.auth.field_encryption import FieldEncryption, field_encryption

__all__ = ["FieldEncryption", "field_encryption"]
