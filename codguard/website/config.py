"""Website configuration, read from the environment once at import."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _plan_variants(raw: str) -> dict[str, str]:
    """'123:starter,456:growth' -> {'123': 'starter', '456': 'growth'}"""
    out = {}
    for part in raw.split(","):
        if ":" in part:
            variant, plan = (p.strip() for p in part.split(":", 1))
            if variant and plan:
                out[variant] = plan
    return out


@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    usd: int
    checks: int  # per calendar month


PLANS = {p.key: p for p in (
    Plan("starter", "Starter", 9, 1_000),
    Plan("growth", "Growth", 29, 5_000),
    Plan("pro", "Pro", 79, 25_000),
)}


@dataclass(frozen=True)
class Settings:
    host: str = _env("HOST", "127.0.0.1")
    port: int = int(_env("PORT", "8000"))
    site_url: str = _env("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
    db_path: str = _env("CODGUARD_DB", "codguard-web.sqlite3")
    # Lemon Squeezy: the store whose license keys we accept, and which variant is which plan.
    ls_store_id: str = _env("LEMONSQUEEZY_STORE_ID")
    plan_variants: dict = field(default_factory=lambda: _plan_variants(_env("LEMONSQUEEZY_PLAN_VARIANTS")))
    # Hosted checkout links, one per plan (Lemon Squeezy -> product -> Share).
    checkout_urls: dict = field(default_factory=lambda: {
        k: _env(f"CHECKOUT_URL_{k.upper()}") for k in PLANS})
    contact_email: str = _env("CONTACT_EMAIL")
    free_checks_per_day: int = int(_env("FREE_CHECKS_PER_DAY", "20"))


settings = Settings()


def check_deployable(s: Settings) -> None:
    """Refuse to serve publicly with paid features unable to verify customers."""
    if s.host in ("127.0.0.1", "localhost", "::1"):
        return
    if not s.site_url.startswith("https://"):
        raise RuntimeError("SITE_URL must be https:// on a public host")
    if not s.ls_store_id or not s.plan_variants:
        raise RuntimeError("LEMONSQUEEZY_STORE_ID and LEMONSQUEEZY_PLAN_VARIANTS must be set on a public host")
