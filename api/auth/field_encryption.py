"""
Field-level encryption using AES-256 (Fernet).

Encrypts sensitive fields like CPF and phone before storing in database.

Moved from api/encryption.py to api/auth/field_encryption.py
"""

import re
from typing import Optional

import structlog
from cryptography.fernet import Fernet, InvalidToken

from config.settings import settings

logger = structlog.get_logger()


class FieldEncryption:
    """AES-256 field encryption using Fernet symmetric encryption."""

    def __init__(self, key: str) -> None:
        if not key:
            logger.warning("field_encryption_key_not_set", msg="Encryption disabled")
            self._fernet: Optional[Fernet] = None
            return
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error("field_encryption_init_error", error=str(e))
            self._fernet = None

    @property
    def is_configured(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if not self._fernet:
            raise RuntimeError("Encryption not configured. Set FIELD_ENCRYPTION_KEY.")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not self._fernet:
            raise RuntimeError("Encryption not configured. Set FIELD_ENCRYPTION_KEY.")
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            raise ValueError("Decryption failed: invalid key or corrupted data")

    def encrypt_cpf(self, cpf: str) -> str:
        cleaned = re.sub(r"\D", "", cpf)
        if len(cleaned) != 11:
            raise ValueError(f"CPF invalido: deve ter 11 digitos, recebeu {len(cleaned)}")
        return self.encrypt(cleaned)

    def encrypt_phone(self, phone: str) -> str:
        cleaned = re.sub(r"\D", "", phone)
        if len(cleaned) < 10 or len(cleaned) > 13:
            raise ValueError(f"Telefone invalido: {len(cleaned)} digitos")
        return self.encrypt(cleaned)


# Singleton instance
field_encryption = FieldEncryption(settings.field_encryption_key)
