"""CODGuard website.

Public (anonymous by design -- this is the marketing site):
  GET  /                landing page with the free checker
  POST /api/check       free single check, rate limited per client and globally
  GET  /healthz
Paid (Lemon Squeezy subscription license key, verified with Lemon Squeezy):
  GET  /app             the bulk-check page (static shell; holds no data)
  POST /api/bulk        CSV in -> scored CSV out
  POST /api/v1/check    single check for integrations, counts against the plan
  GET  /api/v1/usage    plan + checks used this month
"""
from __future__ import annotations

import json
import re

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app import countries, scorer

from . import bulk, config, licenses, limits, pages

app = FastAPI(title="CODGuard", docs_url=None, redoc_url=None, openapi_url=None)

_FIELDS = ("name", "address1", "address2", "city", "zip", "province", "country_code", "phone")
_MAX_FIELD = 300


@app.middleware("http")
async def _headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Content-Security-Policy",
                            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                            "img-src 'self' data:; frame-ancestors 'none'; form-action 'self' https://*.lemonsqueezy.com")
    return resp


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _address_from(body: dict) -> tuple[dict, float, str] | JSONResponse:
    if not isinstance(body, dict):
        return _error("send a JSON object", 400)
    addr = {}
    for f in _FIELDS:
        v = body.get(f, "")
        if not isinstance(v, str) or len(v) > _MAX_FIELD:
            return _error(f"{f} must be text under {_MAX_FIELD} characters", 400)
        addr[f] = v
    addr["country_code"] = countries.normalize_country(addr["country_code"])
    total = body.get("order_total", 0) or 0
    if not isinstance(total, (int, float)) or not 0 <= total < 1e9:
        return _error("order_total must be a number", 400)
    currency = body.get("currency", "") or ""
    if not isinstance(currency, str) or len(currency) > 3:
        return _error("currency must be a 3-letter code", 400)
    return addr, float(total), currency.upper()


def _result(addr: dict, total: float, currency: str) -> dict:
    r = scorer.score(addr, order_total=total, currency=currency)
    return {"risk": r.risk, "band": r.band,
            "reasons": [{"code": x.code, "points": x.points, "message": x.message} for x in r.reasons]}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def landing():
    return pages.landing(config.settings, config.PLANS)


@app.get("/app", response_class=HTMLResponse)
def app_page():
    return pages.app_page(config.settings)


@app.post("/api/check")
async def free_check(request: Request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error("send a JSON object", 400)
    parsed = _address_from(body)
    if isinstance(parsed, JSONResponse):
        return parsed
    who = limits.client_id(request.headers, request.client.host if request.client else None)
    ok, left = limits.allow(who, config.settings.free_checks_per_day)
    if not ok:
        return _error("free checks used up for today. Subscribe to check whole order files.", 429)
    return {**_result(*parsed), "free_checks_left_today": left}


# --- paid ---------------------------------------------------------------------------

def _license(header_value: str | None) -> licenses.License | JSONResponse:
    key = (header_value or "").removeprefix("Bearer ").strip()
    try:
        return licenses.verify(key)
    except licenses.LicenseError as exc:
        return _error(str(exc), exc.status)


@app.get("/api/v1/usage")
def usage(authorization: str | None = Header(default=None)):
    lic = _license(authorization)
    if isinstance(lic, JSONResponse):
        return lic
    return {"plan": lic.plan.name, "checks_per_month": lic.plan.checks, "used_this_month": licenses.used(lic)}


@app.post("/api/v1/check")
async def paid_check(request: Request, authorization: str | None = Header(default=None)):
    lic = _license(authorization)
    if isinstance(lic, JSONResponse):
        return lic
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error("send a JSON object", 400)
    parsed = _address_from(body)
    if isinstance(parsed, JSONResponse):
        return parsed
    try:
        licenses.consume(lic, 1)
    except licenses.LicenseError as exc:
        return _error(str(exc), exc.status)
    return _result(*parsed)


@app.post("/api/bulk")
async def bulk_check(file: UploadFile = File(...), default_country: str = Form(""),
                     authorization: str | None = Header(default=None)):
    lic = _license(authorization)
    if isinstance(lic, JSONResponse):
        return lic
    data = await file.read(bulk.MAX_BYTES + 1)
    try:
        rows = bulk.parse(data, countries.normalize_country(default_country))
    except bulk.CsvError as exc:
        return _error(str(exc), 400)
    try:
        licenses.consume(lic, len(rows))
    except licenses.LicenseError as exc:
        return _error(str(exc), exc.status)
    scored = bulk.score_rows(rows)
    flagged = sum(1 for r in scored if r["band"] != "low")
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", (file.filename or "orders").rsplit(".", 1)[0])[:60] or "orders"
    return Response(bulk.to_csv(scored), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{stem}-codguard.csv"',
        "X-CODGuard-Orders": str(len(scored)), "X-CODGuard-Flagged": str(flagged)})
