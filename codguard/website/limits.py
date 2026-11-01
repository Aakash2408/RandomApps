"""Limits for the free, anonymous checker on the landing page.

Two layers: a per-client daily allowance, and a global daily ceiling so the
free tier's total cost is bounded even if the per-client key is evaded.
In-memory on purpose: one replica, and losing counts on restart is harmless.
"""
from __future__ import annotations

import os
import threading
import time

GLOBAL_PER_DAY = int(os.environ.get("FREE_CHECKS_GLOBAL_PER_DAY", "5000"))
# Behind Railway's proxy request.client is the proxy. Set to the header the proxy
# APPENDS the real client to (e.g. "x-forwarded-for"); its LAST entry is used,
# since earlier entries are client-supplied and spoofable.
CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "").strip().lower()

_lock = threading.Lock()
_day = ""
_per_client: dict[str, int] = {}
_global = 0


def client_id(headers, peer: str | None) -> str:
    if CLIENT_IP_HEADER:
        raw = headers.get(CLIENT_IP_HEADER, "")
        last = raw.split(",")[-1].strip()
        if last:
            return last
    return peer or "unknown"


def allow(client: str, per_day: int) -> tuple[bool, int]:
    """(allowed, remaining today for this client)."""
    global _day, _global
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with _lock:
        if today != _day:
            _day, _global = today, 0
            _per_client.clear()
        n = _per_client.get(client, 0)
        if n >= per_day or _global >= GLOBAL_PER_DAY:
            return False, max(0, per_day - n)
        _per_client[client] = n + 1
        _global += 1
        return True, per_day - n - 1


def reset() -> None:  # tests
    global _day, _global
    with _lock:
        _day, _global = "", 0
        _per_client.clear()
