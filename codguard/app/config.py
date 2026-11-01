"""Runtime configuration, read from the environment once at import.

Every value has a safe default for local development. Secrets have NO default:
code that needs one calls `require()` and fails loudly instead of running with
an empty key (an empty HMAC key would make every signature check pass for
anyone who also uses an empty key).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    api_key: str = _env("SHOPIFY_API_KEY")
    api_secret: str = _env("SHOPIFY_API_SECRET")
    # Public HTTPS base URL Shopify calls back on, e.g. https://codguard.example.com
    app_url: str = _env("APP_URL", "http://127.0.0.1:8000").rstrip("/")
    scopes: str = _env("SHOPIFY_SCOPES", "read_orders,write_orders")
    # Verify this against Shopify's supported-versions list before launch.
    api_version: str = _env("SHOPIFY_API_VERSION", "2026-10")
    db_path: str = _env("CODGUARD_DB", "codguard.sqlite3")
    # Fernet key used to encrypt shop access tokens at rest.
    token_key: str = _env("CODGUARD_TOKEN_KEY")
    # HMAC key used to hash customer phone numbers (history without storing phones).
    phone_pepper: str = _env("CODGUARD_PHONE_PEPPER")
    # Shopify test charges (no real money). Must be "0" in production.
    billing_test: bool = _env("CODGUARD_BILLING_TEST", "1") == "1"
    # Loopback by default. A deploy that must be reachable sets HOST explicitly.
    host: str = _env("HOST", "127.0.0.1")
    port: int = int(_env("PORT", "8000"))
    # WhatsApp Cloud API. Sending is disabled unless all three are set.
    wa_token: str = _env("WHATSAPP_TOKEN")
    wa_phone_number_id: str = _env("WHATSAPP_PHONE_NUMBER_ID")
    wa_template: str = _env("WHATSAPP_TEMPLATE")
    wa_template_lang: str = _env("WHATSAPP_TEMPLATE_LANG", "en")
    # Languages the template is approved in, e.g. "en,ar,es,pt".
    wa_template_langs: str = _env("WHATSAPP_TEMPLATE_LANGS")
    # Days a customer confirmation link stays valid.
    confirm_ttl_days: int = int(_env("CODGUARD_CONFIRM_TTL_DAYS", "7"))


settings = Settings()


def require(value: str, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is not set; refusing to run without it")
    return value


def check_deployable(s: Settings) -> None:
    """Refuse to start a non-loopback server that is missing a secret.

    Locally, missing secrets surface on first use. On a public host that would
    mean serving traffic and failing every request, so fail before listening.
    """
    if s.host in ("127.0.0.1", "localhost", "::1"):
        return
    for value, name in ((s.api_key, "SHOPIFY_API_KEY"), (s.api_secret, "SHOPIFY_API_SECRET"),
                        (s.token_key, "CODGUARD_TOKEN_KEY"), (s.phone_pepper, "CODGUARD_PHONE_PEPPER")):
        require(value, name)
    if not s.app_url.startswith("https://"):
        raise RuntimeError("APP_URL must be https:// on a deployed host (Shopify requires it)")
