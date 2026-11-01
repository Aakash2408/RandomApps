"""Lifetimes server: serves the static game, verifies in-app purchases, hosts chat rooms.

Purchases are one-time Lemon Squeezy products with license keys. A key unlocks
a pack only if Lemon Squeezy says it is valid, not expired/disabled (a refund
disables it), belongs to OUR store, and its variant maps to a known pack.
Fails closed when unconfigured or when Lemon Squeezy is unreachable.

The game itself runs in the browser and saves to localStorage, so unlocks are
remembered client-side. A determined player can flip that flag in devtools; for
a single-player game that is an accepted trade-off (no accounts, no backend
state), and it can never grant anything on another person's device.

Chat rooms are deliberately small and public: a fixed set of rooms, nickname-only
(no accounts), in memory only, messages expire after 24 hours. See chat.py.
"""
from __future__ import annotations

import mimetypes
import os
import threading
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import chat

mimetypes.add_type("application/manifest+json", ".webmanifest")

PUBLIC = Path(__file__).resolve().parent.parent / "public"
VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
PACKS = ("plus", "editor", "rewind", "careers", "drama")
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


def client_ip(request: Request) -> str:
    """The caller's IP. Behind a proxy, CLIENT_IP_HEADER names the header it sets
    (last hop, which the proxy appended); otherwise the socket peer."""
    h = _env("CLIENT_IP_HEADER")
    ip = request.headers.get(h.lower(), "").split(",")[-1].strip() if h else (request.client.host if request.client else "")
    return ip or "unknown"


app = FastAPI(title="Lifetimes", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def _headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Content-Security-Policy",
                            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; "
                            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    elif request.url.path in ("/sw.js", "/", "/index.html", "/manifest.webmanifest"):
        # Always revalidate so a new release reaches installed copies; the service
        # worker itself provides the offline copy.
        resp.headers.setdefault("Cache-Control", "no-cache")
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


async def _json(request: Request):
    try:
        return await request.json()
    except Exception:
        return None


@app.post("/api/unlock")
async def unlock(request: Request):
    body = await _json(request)
    if body is None:
        return _err("send JSON", 400)
    key = body.get("key") if isinstance(body, dict) else None
    if not isinstance(key, str) or not 8 <= len(key.strip()) <= 100:
        return _err("enter the license key from your receipt email", 400)
    if not store_id() or not pack_variants():
        return _err("the store is not open yet", 503)
    if not _rate_ok(client_ip(request)):
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


# --- chat rooms ---------------------------------------------------------------------

@app.get("/api/rooms")
def rooms():
    return {"rooms": chat.board.room_list()}


@app.get("/api/rooms/{room}/messages")
def room_messages(room: str, after: int = 0):
    if room not in chat.ROOMS:
        return _err("no such room", 404)
    return {"messages": chat.board.messages(room, after)}


@app.post("/api/rooms/{room}/messages")
async def room_post(room: str, request: Request):
    if room not in chat.ROOMS:
        return _err("no such room", 404)
    body = await _json(request)
    if not isinstance(body, dict):
        return _err("send JSON", 400)
    try:
        msg = chat.board.post(room, client_ip(request), body.get("nick"), body.get("text"), body.get("life"))
    except chat.Rejected as e:
        return _err(str(e), e.status)
    return {"message": msg}


@app.post("/api/rooms/{room}/messages/{msg_id}/report")
def room_report(room: str, msg_id: int, request: Request):
    if room not in chat.ROOMS:
        return _err("no such room", 404)
    try:
        chat.board.report(room, msg_id, client_ip(request))
    except chat.Rejected as e:
        return _err(str(e), e.status)
    return {"ok": True}


app.mount("/", StaticFiles(directory=PUBLIC, html=True), name="game")
