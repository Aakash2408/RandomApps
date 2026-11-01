"""Secrets at rest: shop access tokens are encrypted, phone numbers are hashed.

A leaked database should not hand out working Admin API tokens for every
installed store, and should not be a list of customer phone numbers. Phones are
only needed for "has this number caused an RTO before?", which a keyed hash
answers without storing the number itself.
"""
from __future__ import annotations

import hashlib
import hmac

from cryptography.fernet import Fernet

from . import config


def _fernet() -> Fernet:
    return Fernet(config.require(config.settings.token_key, "CODGUARD_TOKEN_KEY").encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def phone_hash(shop: str, normalized_phone: str) -> str:
    """Per-shop keyed hash, so the same customer is not linkable across stores."""
    if not normalized_phone:
        return ""
    key = config.require(config.settings.phone_pepper, "CODGUARD_PHONE_PEPPER").encode()
    return hmac.new(key, f"{shop}:{normalized_phone}".encode(), hashlib.sha256).hexdigest()
