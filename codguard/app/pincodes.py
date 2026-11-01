"""India PIN code -> state consistency checks.

The first two digits of a PIN code identify a postal circle, and each circle
covers a known set of states/UTs. This is coarse (it cannot say whether a
specific PIN exists), but it catches the two failures that matter for RTO:
a PIN that cannot exist at all, and a PIN that contradicts the state the
customer typed. A full PIN directory (India Post's public dataset, ~19k
PINs) can replace this later without changing the scorer's interface.
"""
from __future__ import annotations

import re

_UP, _UK = "uttar pradesh", "uttarakhand"
_TG, _AP = "telangana", "andhra pradesh"
_BR, _JH = "bihar", "jharkhand"
_NE = {"arunachal pradesh", "meghalaya", "manipur", "mizoram", "nagaland", "tripura", "assam"}

# two-digit prefix -> states/UTs that PINs with that prefix can belong to
_PREFIX_STATES: dict[str, set[str]] = {
    "11": {"delhi"},
    "12": {"haryana"}, "13": {"haryana"},
    "14": {"punjab"}, "15": {"punjab"},
    "16": {"punjab", "chandigarh", "haryana"},
    "17": {"himachal pradesh"},
    "18": {"jammu and kashmir"}, "19": {"jammu and kashmir", "ladakh"},
    **{p: {_UP} for p in ("20", "21", "22", "23", "27", "28")},
    **{p: {_UP, _UK} for p in ("24", "25", "26")},
    **{p: {"rajasthan"} for p in ("30", "31", "32", "33", "34")},
    **{p: {"gujarat"} for p in ("36", "37", "38")},
    "39": {"gujarat", "dadra and nagar haveli and daman and diu"},
    "40": {"maharashtra", "goa"},
    **{p: {"maharashtra"} for p in ("41", "42", "43", "44")},
    **{p: {"madhya pradesh"} for p in ("45", "46", "47", "48")},
    "49": {"chhattisgarh"},
    **{p: {_TG, _AP} for p in ("50", "51", "52", "53")},
    **{p: {"karnataka"} for p in ("56", "57", "58", "59")},
    "60": {"tamil nadu", "puducherry"},
    **{p: {"tamil nadu"} for p in ("61", "62", "63", "64")},
    "67": {"kerala"}, "68": {"kerala", "lakshadweep"}, "69": {"kerala"},
    **{p: {"west bengal"} for p in ("70", "71", "72")},
    "73": {"west bengal", "sikkim"},
    "74": {"west bengal", "andaman and nicobar islands"},
    **{p: {"odisha"} for p in ("75", "76", "77")},
    "78": {"assam"},
    "79": _NE,
    **{p: {_BR, _JH} for p in ("80", "81", "82", "83", "84", "85")},
}

# Shopify sends `province` (name) and `province_code` (e.g. "MH").
_CODE_TO_STATE = {
    "AN": "andaman and nicobar islands", "AP": _AP, "AR": "arunachal pradesh",
    "AS": "assam", "BR": _BR, "CH": "chandigarh", "CG": "chhattisgarh",
    "CT": "chhattisgarh", "DN": "dadra and nagar haveli and daman and diu",
    "DD": "dadra and nagar haveli and daman and diu", "DL": "delhi", "GA": "goa",
    "GJ": "gujarat", "HR": "haryana", "HP": "himachal pradesh",
    "JK": "jammu and kashmir", "JH": _JH, "KA": "karnataka", "KL": "kerala",
    "LA": "ladakh", "LD": "lakshadweep", "MP": "madhya pradesh", "MH": "maharashtra",
    "MN": "manipur", "ML": "meghalaya", "MZ": "mizoram", "NL": "nagaland",
    "OR": "odisha", "OD": "odisha", "PY": "puducherry", "PB": "punjab",
    "RJ": "rajasthan", "SK": "sikkim", "TN": "tamil nadu", "TG": _TG, "TS": _TG,
    "TR": "tripura", "UP": _UP, "UK": _UK, "UT": _UK, "WB": "west bengal",
}

_ALIASES = {
    "new delhi": "delhi", "nct of delhi": "delhi", "orissa": "odisha",
    "pondicherry": "puducherry", "uttaranchal": _UK, "j&k": "jammu and kashmir",
    "jammu & kashmir": "jammu and kashmir", "andaman & nicobar islands": "andaman and nicobar islands",
    "daman and diu": "dadra and nagar haveli and daman and diu",
    "dadra and nagar haveli": "dadra and nagar haveli and daman and diu",
}

_PIN_RE = re.compile(r"^[1-9][0-9]{5}$")


def normalize_pin(raw: str | None) -> str:
    return re.sub(r"\s+", "", raw or "")


def is_well_formed(pin: str) -> bool:
    return bool(_PIN_RE.match(pin))


def prefix_exists(pin: str) -> bool:
    return pin[:2] in _PREFIX_STATES


def normalize_state(name: str | None, code: str | None) -> str | None:
    """Best-effort canonical state name, or None when nothing usable was sent."""
    if code:
        c = code.strip().upper()
        if c.startswith("IN-"):
            c = c[3:]
        if c in _CODE_TO_STATE:
            return _CODE_TO_STATE[c]
    if name:
        n = re.sub(r"\s+", " ", name.strip().lower())
        return _ALIASES.get(n, n)
    return None


def state_matches(pin: str, state: str) -> bool:
    return state in _PREFIX_STATES.get(pin[:2], set())
