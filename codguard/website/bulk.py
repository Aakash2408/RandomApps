"""Bulk CSV checking: accepts a Shopify order export or a simple generic CSV.

Shopify's "Export orders" CSV has one row per LINE ITEM, so an order with three
products appears three times; rows are grouped by the order's Name (#1001) and
each order is scored once.
"""
from __future__ import annotations

import csv
import io

from app import scorer

MAX_BYTES = 3 * 1024 * 1024
MAX_ORDERS = 5_000

# canonical field -> accepted headers (lowercased), first match wins
_COLUMNS = {
    "order":    ("name", "order", "order id", "order number", "order_id"),
    "name":     ("shipping name", "customer name", "customer", "full name", "recipient"),
    "address1": ("shipping address1", "shipping street", "address1", "address 1", "address", "street"),
    "address2": ("shipping address2", "address2", "address 2"),
    "city":     ("shipping city", "city"),
    "zip":      ("shipping zip", "zip", "postcode", "postal code", "pin", "pincode"),
    "province": ("shipping province", "province", "state", "region"),
    "country":  ("shipping country", "country", "country code"),
    "phone":    ("shipping phone", "phone", "mobile", "billing phone"),
    "total":    ("total", "order total", "amount"),
    "currency": ("currency",),
    "payment":  ("payment method", "gateway", "payment"),
}

# Country names merchants type in generic CSVs -> ISO code (target markets).
_COUNTRY_NAMES = {
    "united arab emirates": "AE", "uae": "AE", "saudi arabia": "SA", "ksa": "SA", "kuwait": "KW",
    "qatar": "QA", "bahrain": "BH", "oman": "OM", "egypt": "EG", "morocco": "MA", "jordan": "JO",
    "turkey": "TR", "türkiye": "TR", "india": "IN", "pakistan": "PK", "bangladesh": "BD",
    "indonesia": "ID", "philippines": "PH", "malaysia": "MY", "vietnam": "VN", "thailand": "TH",
    "mexico": "MX", "méxico": "MX", "brazil": "BR", "brasil": "BR", "colombia": "CO", "peru": "PE",
    "chile": "CL", "argentina": "AR", "poland": "PL", "romania": "RO", "czechia": "CZ",
    "czech republic": "CZ", "greece": "GR", "italy": "IT", "spain": "ES", "united states": "US",
    "usa": "US", "united kingdom": "GB", "uk": "GB", "nigeria": "NG", "kenya": "KE",
}

OUT_COLUMNS = ["order", "risk", "band", "reasons", "name", "address1", "address2", "city", "zip", "country", "phone"]


class CsvError(ValueError):
    pass


def country_code(raw: str, default: str) -> str:
    v = (raw or "").strip()
    if len(v) == 2 and v.isalpha():
        return v.upper()
    return _COUNTRY_NAMES.get(v.lower(), default)


def _safe_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection: the merchant opens this in Excel."""
    v = str(value)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def parse(data: bytes, default_country: str = "") -> list[dict]:
    if len(data) > MAX_BYTES:
        raise CsvError(f"file is larger than {MAX_BYTES // (1024 * 1024)} MB; split it into smaller files")
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CsvError("the file has no header row")
    lower = {h.strip().lower(): h for h in reader.fieldnames if h}
    mapping = {}
    for field, names in _COLUMNS.items():
        for n in names:
            if n in lower:
                mapping[field] = lower[n]
                break
    if "address1" not in mapping or "phone" not in mapping:
        raise CsvError("could not find an address and a phone column (e.g. 'Shipping Address1' and 'Shipping Phone')")

    orders: dict[str, dict] = {}
    for i, row in enumerate(reader):
        rec = {f: (row.get(col) or "").strip() for f, col in mapping.items()}
        key = rec.get("order") or f"row {i + 2}"
        if key in orders:
            # Later line-item rows in a Shopify export leave shipping fields blank.
            for f, v in rec.items():
                if v and not orders[key].get(f):
                    orders[key][f] = v
            continue
        if len(orders) >= MAX_ORDERS:
            raise CsvError(f"more than {MAX_ORDERS} orders in one file; split it")
        rec["order"] = key
        orders[key] = rec
    if not orders:
        raise CsvError("the file has no orders")
    for rec in orders.values():
        rec["country"] = country_code(rec.get("country", ""), default_country)
    return list(orders.values())


def _total(raw: str) -> float:
    try:
        return float((raw or "0").replace(",", ""))
    except ValueError:
        return 0.0


def score_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        result = scorer.score(
            {"name": r.get("name"), "address1": r.get("address1"), "address2": r.get("address2"),
             "city": r.get("city"), "zip": r.get("zip"), "province": r.get("province"),
             "country_code": r.get("country"), "phone": r.get("phone")},
            order_total=_total(r.get("total", "")), currency=r.get("currency", ""),
        )
        out.append({**{c: r.get(c, "") for c in OUT_COLUMNS}, "risk": result.risk, "band": result.band,
                    "reasons": "; ".join(x.message for x in result.reasons)})
    # Riskiest first: the merchant's to-do list is the top of the file.
    out.sort(key=lambda x: -x["risk"])
    return out


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(OUT_COLUMNS)
    for r in rows:
        w.writerow([_safe_cell(r[c]) for c in OUT_COLUMNS])
    return buf.getvalue()
