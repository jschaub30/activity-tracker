"""Encrypt Garmin session tokens at rest."""

from cryptography.fernet import Fernet, InvalidToken

from garmin_tracker.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.token_encryption_key
    if not key:
        # Dev fallback: derive from secret_key (not ideal; set TOKEN_ENCRYPTION_KEY in .env)
        import base64
        import hashlib

        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt Garmin token; check TOKEN_ENCRYPTION_KEY") from exc
