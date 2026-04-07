"""AES encryption for sensitive data fields.

Encrypts/decrypts values at the application layer before DB storage.
Used for: API keys, client contact info, financial details.
"""

import base64
import os
import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

logger = structlog.get_logger()


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet key from the app secret."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"logistics-presale-salt-v1",  # Fixed salt for deterministic derivation
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


class FieldEncryptor:
    """Encrypts and decrypts string values using Fernet (AES-128-CBC)."""

    def __init__(self, secret: str | None = None):
        settings = get_settings()
        key = _derive_key(secret or settings.app_secret_key)
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string, returns base64-encoded ciphertext."""
        if not plaintext:
            return ""
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext back to string."""
        if not ciphertext:
            return ""
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            return "[DECRYPTION_ERROR]"

    def is_encrypted(self, value: str) -> bool:
        """Check if a value looks like it's already encrypted."""
        if not value:
            return False
        try:
            self._fernet.decrypt(value.encode("utf-8"))
            return True
        except Exception:
            return False


# ── Singleton ──

_encryptor: FieldEncryptor | None = None


def get_encryptor() -> FieldEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = FieldEncryptor()
    return _encryptor


def encrypt_value(value: str) -> str:
    """Convenience function to encrypt a value."""
    return get_encryptor().encrypt(value)


def decrypt_value(value: str) -> str:
    """Convenience function to decrypt a value."""
    return get_encryptor().decrypt(value)
