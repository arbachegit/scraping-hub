"""
Field-level encryption using AES-256 (Fernet).

Encrypts sensitive fields like CPF and phone before storing in database.
Fernet guarantees that data encrypted using it cannot be manipulated
or read without the key.

Usage:
    from api.encryption import field_encryption
    encrypted = field_encryption.encrypt_cpf("123.456.789-00")
    decrypted = field_encryption.decrypt(encrypted)
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
        """
        Initialize with a Fernet key.

        Args:
            key: Base64-encoded 32-byte key. Generate with Fernet.generate_key().
        """
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
        """Check if encryption is properly configured."""
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded encrypted string.

        Raises:
            RuntimeError: If encryption is not configured.
        """
        if not self._fernet:
            raise RuntimeError("Encryption not configured. Set FIELD_ENCRYPTION_KEY.")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string.

        Returns:
            Decrypted plaintext string.

        Raises:
            RuntimeError: If encryption is not configured.
            ValueError: If decryption fails (invalid key or corrupted data).
        """
        if not self._fernet:
            raise RuntimeError("Encryption not configured. Set FIELD_ENCRYPTION_KEY.")
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            raise ValueError("Decryption failed: invalid key or corrupted data")

    def encrypt_cpf(self, cpf: str) -> str:
        """
        Encrypt a CPF after stripping formatting.

        Args:
            cpf: CPF string (with or without formatting).

        Returns:
            Encrypted CPF string.
        """
        cleaned = re.sub(r"\D", "", cpf)
        if len(cleaned) != 11:
            raise ValueError(f"CPF invalido: deve ter 11 digitos, recebeu {len(cleaned)}")
        return self.encrypt(cleaned)

    def encrypt_phone(self, phone: str) -> str:
        """
        Encrypt a phone number after stripping formatting.

        Args:
            phone: Phone string (with or without formatting).

        Returns:
            Encrypted phone string.
        """
        cleaned = re.sub(r"\D", "", phone)
        if len(cleaned) < 10 or len(cleaned) > 13:
            raise ValueError(f"Telefone invalido: {len(cleaned)} digitos")
        return self.encrypt(cleaned)


# Singleton instance
field_encryption = FieldEncryption(settings.field_encryption_key)
