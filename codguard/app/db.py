"""SQLite persistence. One file, WAL mode, a short-lived connection per call."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS shops (
    shop                TEXT PRIMARY KEY,
    token_enc           TEXT,
    scope               TEXT,
    installed_at        INTEGER,
    uninstalled_at      INTEGER,
    plan                TEXT,
    subscription_gid    TEXT,
    subscription_status TEXT,
    usage_line_gid      TEXT,
    currency            TEXT,
    -- the merchant's two-way cost of one failed COD delivery, in `currency`; 0 = not set
    rto_cost            INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS oauth_states (
    state      TEXT PRIMARY KEY,
    shop       TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS webhook_seen (
    webhook_id  TEXT PRIMARY KEY,
    received_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS checks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    shop             TEXT NOT NULL,
    order_gid        TEXT NOT NULL,
    order_name       TEXT,
    first_name       TEXT,
    phone_hash       TEXT,
    risk             INTEGER NOT NULL,
    band             TEXT NOT NULL,
    reasons_json     TEXT NOT NULL,
    address_json     TEXT,
    total            REAL,
    currency         TEXT,
    country          TEXT,
    locale           TEXT,
    status           TEXT NOT NULL,
    token            TEXT UNIQUE,
    token_expires_at INTEGER,
    wa_status        TEXT,
    created_at       INTEGER NOT NULL,
    updated_at       INTEGER NOT NULL,
    UNIQUE (shop, order_gid)
);
CREATE INDEX IF NOT EXISTS checks_phone ON checks (shop, phone_hash);
CREATE INDEX IF NOT EXISTS checks_created ON checks (shop, created_at);
CREATE TABLE IF NOT EXISTS usage (
    shop  TEXT NOT NULL,
    month TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (shop, month)
);
"""

# Outcomes that count against a phone number next time it orders COD.
RTO_STATUSES = ("returned", "cancelled")


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(config.settings.db_path, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=WAL")
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    parent = os.path.dirname(os.path.abspath(config.settings.db_path))
    os.makedirs(parent, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)


def now() -> int:
    return int(time.time())


def month_key(ts: int | None = None) -> str:
    return time.strftime("%Y-%m", time.gmtime(ts or now()))


# --- shops -------------------------------------------------------------------

def upsert_shop(shop: str, token_enc: str, scope: str) -> None:
    with conn() as c:
        c.execute(
            """INSERT INTO shops (shop, token_enc, scope, installed_at, uninstalled_at)
               VALUES (?, ?, ?, ?, NULL)
               ON CONFLICT(shop) DO UPDATE SET token_enc=excluded.token_enc,
                   scope=excluded.scope, installed_at=excluded.installed_at, uninstalled_at=NULL""",
            (shop, token_enc, scope, now()),
        )


def get_shop(shop: str) -> sqlite3.Row | None:
    with conn() as c:
        return c.execute("SELECT * FROM shops WHERE shop=?", (shop,)).fetchone()


def mark_uninstalled(shop: str) -> None:
    with conn() as c:
        c.execute(
            """UPDATE shops SET token_enc=NULL, uninstalled_at=?, subscription_status='CANCELLED'
               WHERE shop=?""",
            (now(), shop),
        )


def set_subscription(shop: str, *, plan: str | None = None, gid: str | None = None,
                     status: str | None = None, usage_line_gid: str | None = None) -> None:
    fields = {"plan": plan, "subscription_gid": gid, "subscription_status": status,
              "usage_line_gid": usage_line_gid}
    sets = {k: v for k, v in fields.items() if v is not None}
    if not sets:
        return
    cols = ", ".join(f"{k}=?" for k in sets)
    with conn() as c:
        c.execute(f"UPDATE shops SET {cols} WHERE shop=?", (*sets.values(), shop))


def set_rto_cost(shop: str, amount: int) -> None:
    with conn() as c:
        c.execute("UPDATE shops SET rto_cost=? WHERE shop=?", (amount, shop))


def set_currency(shop: str, currency: str) -> None:
    with conn() as c:
        c.execute("UPDATE shops SET currency=? WHERE shop=?", (currency, shop))


def delete_shop_data(shop: str) -> None:
    with conn() as c:
        for table in ("checks", "usage", "oauth_states", "shops"):
            c.execute(f"DELETE FROM {table} WHERE shop=?", (shop,))


# --- oauth state / webhook dedupe --------------------------------------------

def save_state(state: str, shop: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM oauth_states WHERE created_at < ?", (now() - 600,))
        c.execute("INSERT INTO oauth_states VALUES (?, ?, ?)", (state, shop, now()))


def pop_state(state: str, shop: str) -> bool:
    """Single-use: a state is valid once, for the shop it was issued to, for 10 minutes."""
    with conn() as c:
        row = c.execute("SELECT shop, created_at FROM oauth_states WHERE state=?", (state,)).fetchone()
        c.execute("DELETE FROM oauth_states WHERE state=?", (state,))
    return bool(row) and row["shop"] == shop and row["created_at"] >= now() - 600


def first_delivery(webhook_id: str) -> bool:
    """True the first time a webhook id is seen. Shopify retries deliveries."""
    if not webhook_id:
        return True
    with conn() as c:
        c.execute("DELETE FROM webhook_seen WHERE received_at < ?", (now() - 7 * 86400,))
        cur = c.execute("INSERT OR IGNORE INTO webhook_seen VALUES (?, ?)", (webhook_id, now()))
        return cur.rowcount == 1


# --- checks ------------------------------------------------------------------

def history_for(shop: str, phone_hash: str, exclude_order: str) -> tuple[int, int]:
    """(prior RTO-like outcomes, other orders in last 24h) for this phone."""
    if not phone_hash:
        return 0, 0
    placeholders = ",".join("?" * len(RTO_STATUSES))
    with conn() as c:
        rto = c.execute(
            f"SELECT COUNT(*) FROM checks WHERE shop=? AND phone_hash=? AND status IN ({placeholders})",
            (shop, phone_hash, *RTO_STATUSES),
        ).fetchone()[0]
        burst = c.execute(
            "SELECT COUNT(*) FROM checks WHERE shop=? AND phone_hash=? AND order_gid<>? AND created_at>=?",
            (shop, phone_hash, exclude_order, now() - 86400),
        ).fetchone()[0]
    return rto, burst


def typical_total(shop: str, sample: int = 200) -> tuple[float, int]:
    """(median COD order value, orders it is based on) over the shop's recent checks."""
    with conn() as c:
        vals = sorted(r[0] for r in c.execute(
            "SELECT total FROM checks WHERE shop=? AND total>0 ORDER BY created_at DESC LIMIT ?",
            (shop, sample)))
    if not vals:
        return 0.0, 0
    mid = len(vals) // 2
    median = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
    return median, len(vals)


def insert_check(**row) -> int | None:
    """Insert a check. Returns None if this order was already checked."""
    row.setdefault("created_at", now())
    row.setdefault("updated_at", row["created_at"])
    cols = ", ".join(row)
    with conn() as c:
        cur = c.execute(
            f"INSERT OR IGNORE INTO checks ({cols}) VALUES ({','.join('?' * len(row))})",
            tuple(row.values()),
        )
        return cur.lastrowid if cur.rowcount == 1 else None


def get_check_by_token(token: str) -> sqlite3.Row | None:
    with conn() as c:
        return c.execute("SELECT * FROM checks WHERE token=?", (token,)).fetchone()


def get_check(shop: str, check_id: int) -> sqlite3.Row | None:
    with conn() as c:
        return c.execute("SELECT * FROM checks WHERE shop=? AND id=?", (shop, check_id)).fetchone()


def update_check(check_id: int, **fields) -> None:
    fields["updated_at"] = now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE checks SET {cols} WHERE id=?", (*fields.values(), check_id))


def set_status_by_order(shop: str, order_gid: str, status: str) -> None:
    with conn() as c:
        c.execute("UPDATE checks SET status=?, updated_at=? WHERE shop=? AND order_gid=?",
                  (status, now(), shop, order_gid))


def list_checks(shop: str, band: str | None, limit: int = 100) -> list[dict]:
    q = "SELECT * FROM checks WHERE shop=?"
    args: list = [shop]
    if band:
        q += " AND band=?"
        args.append(band)
    q += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with conn() as c:
        rows = c.execute(q, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reasons"] = json.loads(d.pop("reasons_json"))
        # The live link is the merchant's to share (e.g. from their own WhatsApp)
        # while the order still awaits the customer; never after it is used.
        d["confirm_token"] = d["token"] if d["status"] == "flagged" else None
        for private in ("token", "phone_hash", "address_json", "first_name", "locale"):
            d.pop(private, None)
        out.append(d)
    return out


def redact_orders(shop: str, order_gids: list[str]) -> None:
    if not order_gids:
        return
    with conn() as c:
        c.execute(
            f"""UPDATE checks SET first_name=NULL, phone_hash=NULL, address_json=NULL, token=NULL
                WHERE shop=? AND order_gid IN ({','.join('?' * len(order_gids))})""",
            (shop, *order_gids),
        )


def month_summary(shop: str, month: str) -> dict:
    with conn() as c:
        rows = c.execute(
            "SELECT band, status, COUNT(*) n FROM checks WHERE shop=? AND strftime('%Y-%m', created_at, 'unixepoch')=? "
            "GROUP BY band, status",
            (shop, month),
        ).fetchall()
    s = {"checked": 0, "low": 0, "medium": 0, "high": 0,
         "confirmed": 0, "updated": 0, "cancel_requested": 0, "awaiting": 0}
    for r in rows:
        s["checked"] += r["n"]
        s[r["band"]] += r["n"]
        if r["status"] in ("confirmed", "updated", "cancel_requested"):
            s[r["status"]] += r["n"]
        elif r["status"] == "flagged":
            s["awaiting"] += r["n"]
    return s


# --- usage -------------------------------------------------------------------

def bump_usage(shop: str, month: str) -> int:
    with conn() as c:
        c.execute(
            "INSERT INTO usage (shop, month, count) VALUES (?, ?, 1) "
            "ON CONFLICT(shop, month) DO UPDATE SET count=count+1",
            (shop, month),
        )
        return c.execute("SELECT count FROM usage WHERE shop=? AND month=?", (shop, month)).fetchone()[0]


def usage_count(shop: str, month: str) -> int:
    with conn() as c:
        row = c.execute("SELECT count FROM usage WHERE shop=? AND month=?", (shop, month)).fetchone()
    return row[0] if row else 0
