"""Lifetimes server: serves the static game and verifies in-app purchases.

Purchases are one-time Lemon Squeezy products with license keys. A key unlocks
a pack only if Lemon Squeezy says it is valid, not expired/disabled (a refund
disables it), belongs to OUR store, and its variant maps to a known pack.
Fails closed when unconfigured or when Lemon Squeezy is unreachable.

The game itself runs in the browser and saves to localStorage, so unlocks are
remembered client-side. A determined player can flip that flag in devtools; for
a single-player game that is an accepted trade-off (no accounts, no backend
state), and it can never grant anything on another person's device.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

PUBLIC = Path(__file__).resolve().parent.parent / "public"
VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
PACKS = ("plus", "editor", "rewind")
USABLE = ("active", "inactive")  # a fresh, never-activated key is "inactive"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def pack_variants() -> dict[str, str]:
    out = {}
    for part in _env("LEMONSQUEEZY_PACK_VARIANTS").split(","):
        if ":" in part:
            v, p = (x.strip() for x in part.split(":", 1))
            if v and p in PACKS:
                out[v] = p
    return out


def store_id() -> str:
    return _env("LEMONSQUEEZY_STORE_ID")


app = FastAPI(title="Lifetimes", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def _headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Content-Security-Policy",
                            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; "
                            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    return resp


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/config")
def store_config():
    return {
        "checkout": {p: _env(f"CHECKOUT_URL_{p.upper()}") for p in PACKS if _env(f"CHECKOUT_URL_{p.upper()}")},
        "prices": {p: _env(f"PRICE_{p.upper()}") for p in PACKS if _env(f"PRICE_{p.upper()}")},
    }


# --- unlock -----------------------------------------------------------------------

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}
UNLOCKS_PER_HOUR = 20


def _rate_ok(client: str) -> bool:
    now = time.time()
    with _lock:
        recent = [t for t in _hits.get(client, []) if t > now - 3600]
        if len(recent) >= UNLOCKS_PER_HOUR:
            _hits[client] = recent
            return False
        recent.append(now)
        _hits[client] = recent
        return True


def _fetch(key: str) -> dict:
    r = httpx.post(VALIDATE_URL, data={"license_key": key}, headers={"Accept": "application/json"}, timeout=10)
    if r.status_code not in (200, 400, 404):
        raise RuntimeError(f"lemon squeezy returned {r.status_code}")
    return r.json()


def _err(msg: str, status: int) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=status)


@app.post("/api/unlock")
async def unlock(request: Request):
    try:
        body = await request.json()
    except Exception:
        return _err("send JSON", 400)
    key = body.get("key") if isinstance(body, dict) else None
    if not isinstance(key, str) or not 8 <= len(key.strip()) <= 100:
        return _err("enter the license key from your receipt email", 400)
    if not store_id() or not pack_variants():
        return _err("the store is not open yet", 503)
    client = request.headers.get(_env("CLIENT_IP_HEADER").lower(), "").split(",")[-1].strip() \
        if _env("CLIENT_IP_HEADER") else (request.client.host if request.client else "unknown")
    if not _rate_ok(client or "unknown"):
        return _err("too many attempts, try again later", 429)
    try:
        data = _fetch(key.strip())
    except Exception:
        return _err("could not verify right now, try again in a minute", 503)
    lk, meta = data.get("license_key") or {}, data.get("meta") or {}
    if data.get("valid") is not True or lk.get("status") not in USABLE:
        return _err("that key is not valid (or was refunded)", 403)
    if str(meta.get("store_id")) != store_id():
        return _err("that key is not for Lifetimes", 403)
    pack = pack_variants().get(str(meta.get("variant_id")))
    if not pack:
        return _err("that key is for an unknown item", 403)
    return {"packs": [pack]}


app.mount("/", StaticFiles(directory=PUBLIC, html=True), name="game")
