"""Per-country address rules.

Three things vary by country and change what a "bad" address looks like:

* Postal codes: format differs, and several COD-heavy markets (UAE, Qatar,
  Hong Kong, much of Africa) have none at all. A missing postcode there is normal.
* Landmarks: in the Gulf a landmark ("near X mosque", "behind Y mall") with no
  door number is a standard deliverable address and couriers call ahead.
  Elsewhere (India, Pakistan, LatAm...) landmark-only is still a real risk signal.
* Payment method names: merchants name their manual COD method in their own
  language, so "Cash on Delivery" alone misses most non-English stores.

Countries not listed still get the universal checks (door number, junk text,
phone validity, value, history); only the postal-format rule is skipped.
"""
from __future__ import annotations

import re

# ISO 3166-1 alpha-2 -> full-match postal code pattern (uppercased, spaces kept as typed).
POSTAL = {
    # South Asia
    "IN": r"[1-9]\d{5}", "PK": r"\d{5}", "BD": r"\d{4}", "LK": r"\d{5}", "NP": r"\d{5}",
    # Middle East / North Africa
    "SA": r"\d{5}(-?\d{4})?", "KW": r"\d{5}", "BH": r"\d{3,4}", "OM": r"\d{3}",
    "JO": r"\d{5}", "EG": r"\d{5}", "MA": r"\d{5}", "TN": r"\d{4}", "DZ": r"\d{5}",
    "TR": r"\d{5}", "IL": r"\d{5}(\d{2})?",
    # South-East Asia
    "ID": r"\d{5}", "PH": r"\d{4}", "MY": r"\d{5}", "TH": r"\d{5}", "VN": r"\d{6}", "SG": r"\d{6}",
    # Latin America
    "MX": r"\d{5}", "BR": r"\d{5}-?\d{3}", "CO": r"\d{6}", "PE": r"\d{5}", "CL": r"\d{7}",
    "AR": r"([A-Z]\d{4}[A-Z]{3}|\d{4})", "EC": r"\d{6}",
    # Europe
    "PL": r"\d{2}-?\d{3}", "RO": r"\d{6}", "CZ": r"\d{3} ?\d{2}", "SK": r"\d{3} ?\d{2}",
    "HU": r"\d{4}", "BG": r"\d{4}", "GR": r"\d{3} ?\d{2}", "IT": r"\d{5}", "ES": r"\d{5}",
    "PT": r"\d{4}-?\d{3}", "FR": r"\d{5}", "DE": r"\d{5}", "NL": r"\d{4} ?[A-Z]{2}",
    "GB": r"[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}", "UA": r"\d{5}", "RS": r"\d{5}", "HR": r"\d{5}",
    # Elsewhere
    "US": r"\d{5}(-\d{4})?", "CA": r"[A-Z]\d[A-Z] ?\d[A-Z]\d", "AU": r"\d{4}",
    "NG": r"\d{6}", "KE": r"\d{5}", "ZA": r"\d{4}",
}
_POSTAL_RE = {k: re.compile(rf"^(?:{v})$") for k, v in POSTAL.items()}

# No national postcode system in practical use: never penalise a missing one.
NO_POSTCODE = {"AE", "QA", "HK", "MO", "PA", "JM", "BS", "GH", "UG", "TZ", "RW"}

# Addresses here are routinely built from area + landmark without a door number,
# and couriers call ahead. A landmark is not a risk signal; door-number weight is lowered.
LANDMARK_ADDRESSING = {"AE", "SA", "QA", "KW", "BH", "OM", "JO"}

# Lowercased fragments of manual payment method names meaning "pay on delivery".
COD_NAMES = (
    "cash on delivery", "pay on delivery", "cod",
    "contra reembolso", "contrareembolso", "pago contra entrega", "pago en efectivo", "pago al recibir",
    "pagamento na entrega", "pagamento à cobrança",
    "paiement à la livraison", "paiement a la livraison",
    "nachnahme", "za pobraniem", "płatność przy odbiorze", "ramburs", "plata la livrare",
    "dobírka", "dobierka", "utánvét", "наложен платеж", "αντικαταβολή", "contrassegno",
    "kapıda ödeme", "bayar di tempat", "thanh toán khi nhận hàng",
    "เก็บเงินปลายทาง", "الدفع عند الاستلام", "الدفع نقدا عند الاستلام",
)
_COD_RE = re.compile("|".join(rf"\b{re.escape(n)}\b" if n.isascii() else re.escape(n) for n in COD_NAMES))


def is_cod_gateway(name: str) -> bool:
    return bool(_COD_RE.search(name.lower()))


def normalize_country(code: str | None) -> str:
    return (code or "").strip().upper()[:2]


def postal_status(country: str, raw: str | None) -> str:
    """'ok', 'missing', 'malformed', or 'unchecked' (country without a known format)."""
    value = (raw or "").strip().upper()
    if not value:
        return "ok" if country in NO_POSTCODE else ("missing" if country in _POSTAL_RE else "unchecked")
    pattern = _POSTAL_RE.get(country)
    if pattern is None:
        return "unchecked"
    return "ok" if pattern.match(value) else "malformed"
