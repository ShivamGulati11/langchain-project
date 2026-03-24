"""Encryption helpers for PII at rest."""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the application secret key."""
    raw = settings.app_secret_key.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64url-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string produced by encrypt()."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def hash_pii(value: str) -> str:
    """One-way SHA-256 hash for PII fields used in deduplication lookups."""
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()
