"""Paid access = a Lemon Squeezy subscription license key.

Lemon Squeezy issues a license key to every subscriber and keeps it active
exactly as long as the subscription is active (it expires when a cancelled
subscription reaches the end of its cycle, or when payment can no longer be
retried). So the key is the whole account: no passwords, no sessions.

A key is accepted only if Lemon Squeezy's License API says it is valid AND
active AND it belongs to OUR store AND its variant maps to one of our plans.
Any other Lemon Squeezy seller's keys are rejected by the store check.
Fail closed: unconfigured store, network error, or odd response -> rejected.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

import httpx

from . import config

VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
CACHE_SECONDS = 600
USABLE_STATUSES = ("active", "inactive")


class LicenseError(Exception):
    def __init__(self, message: str, status: int = 403):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class License:
    key_hash: str
    plan: config.Plan
    email: str


_cache: dict[str, tuple[float, License]] = {}
_lock = threading.Lock()


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _fetch(key: str) -> dict:
    r = httpx.post(VALIDATE_URL, data={"license_key": key}, headers={"Accept": "application/json"}, timeout=10)
    # 404/400 carry {"valid": false, "error": ...}; anything else is a failure to verify.
    if r.status_code not in (200, 400, 404):
        raise LicenseError("could not verify license right now, try again in a minute", 503)
    return r.json()


def verify(key: str | None) -> License:
    s = config.settings
    key = (key or "").strip()
    if not key or len(key) > 100:
        raise LicenseError("license key required", 401)
    if not s.ls_store_id or not s.plan_variants:
        raise LicenseError("paid plans are not configured on this server", 503)
    h = key_hash(key)
    with _lock:
        hit = _cache.get(h)
        if hit and hit[0] > time.time():
            return hit[1]
    try:
        body = _fetch(key)
    except LicenseError:
        raise
    except Exception as exc:  # network, JSON, anything: do not let a key through
        raise LicenseError("could not verify license right now, try again in a minute", 503) from exc

    lk = body.get("license_key") or {}
    meta = body.get("meta") or {}
    # A fresh key is "inactive" (never activated on a device) and that is a paying
    # customer; "expired" (subscription ended) and "disabled" (refund/manual) are not.
    if body.get("valid") is not True or lk.get("status") not in USABLE_STATUSES:
        raise LicenseError("license key is not active (subscription ended or key is wrong)")
    if str(meta.get("store_id")) != s.ls_store_id:
        raise LicenseError("license key is not for CODGuard")
    plan_key = s.plan_variants.get(str(meta.get("variant_id")))
    plan = config.PLANS.get(plan_key or "")
    if plan is None:
        raise LicenseError("license key is for an unknown plan")
    lic = License(h, plan, meta.get("customer_email") or "")
    with _lock:
        _cache[h] = (time.time() + CACHE_SECONDS, lic)
    return lic


# --- monthly usage ----------------------------------------------------------------

@contextmanager
def _db():
    c = sqlite3.connect(config.settings.db_path, timeout=10)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS usage (key_hash TEXT, month TEXT, count INTEGER NOT NULL, "
                  "PRIMARY KEY (key_hash, month))")
        yield c
        c.commit()
    finally:
        c.close()


def month() -> str:
    return time.strftime("%Y-%m", time.gmtime())


def used(lic: License) -> int:
    with _db() as c:
        row = c.execute("SELECT count FROM usage WHERE key_hash=? AND month=?", (lic.key_hash, month())).fetchone()
    return row[0] if row else 0


def consume(lic: License, n: int) -> int:
    """Reserve n checks this month. Raises if it would exceed the plan; returns the new total."""
    with _db() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT count FROM usage WHERE key_hash=? AND month=?", (lic.key_hash, month())).fetchone()
        current = row[0] if row else 0
        if current + n > lic.plan.checks:
            left = max(0, lic.plan.checks - current)
            raise LicenseError(f"this would use {n} checks but your {lic.plan.name} plan has {left} left this month",
                               429)
        c.execute("INSERT INTO usage VALUES (?, ?, ?) ON CONFLICT(key_hash, month) DO UPDATE SET count=?",
                  (lic.key_hash, month(), current + n, current + n))
        return current + n
