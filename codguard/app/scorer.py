"""Deterministic RTO-risk scorer for Indian COD shipping addresses.

Every point of risk comes from a named rule with a human-readable reason, so a
merchant can see exactly why an order was flagged. No model is involved: the
score must be reproducible and explainable, and each rule is unit-tested.

Risk is 0-100 (higher = more likely to come back undelivered):
    < 30  low     ship normally
    30-59 medium  ask the customer to confirm
    >= 60 high    confirm before shipping; consider prepaid-only
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import pincodes

LOW_MAX = 29
HIGH_MIN = 60

_VAGUE = re.compile(
    r"\b(near|nr\.?|behind|opp\.?|opposite|beside|besides|next to|in front of|"
    r"close to|nearby|backside|back side)\b",
    re.I,
)
# Words that indicate a specific door the courier can find.
_UNIT = re.compile(
    r"\b(flat|flt|house|h\.?\s?no|hno|plot|door|d\.?\s?no|room|rm|floor|flr|"
    r"block|blk|wing|tower|apt|apartment|bldg|building|shop|gali|lane|sector|"
    r"street|st\.?|road|rd\.?|ward|qtr|quarter|villa|bungalow)\b",
    re.I,
)
_JUNK_TOKENS = re.compile(
    # Deliberately excludes short real-world words like "abc"/"xyz" (ABC Apartments).
    r"\b(test|testing|asdf\w*|qwerty\w*|dummy|fake|sample|n/a|none|null|xxx+)\b",
    re.I,
)
_REPEAT_CHAR = re.compile(r"(.)\1{3,}")
_CONSONANT_RUN = re.compile(r"[bcdfghjklmnpqrstvwxz]{6,}", re.I)


@dataclass
class Reason:
    code: str
    points: int
    message: str
    ask: str = ""  # what to ask the customer to fix, if anything


@dataclass
class Result:
    risk: int
    band: str
    reasons: list[Reason] = field(default_factory=list)

    @property
    def asks(self) -> list[str]:
        return [r.ask for r in self.reasons if r.ask]

    def to_dict(self) -> dict:
        return {
            "risk": self.risk,
            "band": self.band,
            "reasons": [r.__dict__ for r in self.reasons],
        }


@dataclass
class History:
    """What we already know about this phone number at this shop."""
    prior_rto: int = 0           # earlier orders the merchant marked returned/cancelled
    orders_last_24h: int = 0     # other COD orders from the same phone in the last day


def band_for(risk: int) -> str:
    if risk >= HIGH_MIN:
        return "high"
    if risk > LOW_MAX:
        return "medium"
    return "low"


def normalize_phone(raw: str | None) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _phone_reasons(raw: str | None) -> list[Reason]:
    phone = normalize_phone(raw)
    if not phone:
        return [Reason("phone_missing", 25, "No phone number, so the courier cannot call.",
                       "Share a phone number the courier can reach.")]
    if len(phone) != 10 or phone[0] not in "6789":
        return [Reason("phone_invalid", 25, f"Phone number '{raw}' is not a valid Indian mobile number.",
                       "Share a valid 10-digit mobile number.")]
    if len(set(phone)) <= 2 or phone in "01234567890" or phone in "98765432109":
        return [Reason("phone_fake", 30, "Phone number looks made up (repeated or sequential digits).",
                       "Share a phone number the courier can reach.")]
    return []


def _text_is_junk(text: str) -> bool:
    return bool(_JUNK_TOKENS.search(text) or _REPEAT_CHAR.search(text) or _CONSONANT_RUN.search(text))


def score(address: dict, *, order_total: float = 0.0, history: History | None = None) -> Result:
    """Score one Shopify shipping_address dict."""
    history = history or History()
    reasons: list[Reason] = []

    line1 = (address.get("address1") or "").strip()
    line2 = (address.get("address2") or "").strip()
    street = f"{line1} {line2}".strip()
    city = (address.get("city") or "").strip()
    name = (address.get("name") or
            f"{address.get('first_name') or ''} {address.get('last_name') or ''}").strip()

    # --- PIN code -------------------------------------------------------------
    pin = pincodes.normalize_pin(address.get("zip"))
    if not pincodes.is_well_formed(pin):
        reasons.append(Reason("pin_malformed", 35, f"PIN code '{address.get('zip') or ''}' is not 6 digits.",
                              "Confirm your 6-digit PIN code."))
    elif not pincodes.prefix_exists(pin):
        reasons.append(Reason("pin_unknown", 35, f"PIN code {pin} does not belong to any Indian postal circle.",
                              "Confirm your 6-digit PIN code."))
    else:
        state = pincodes.normalize_state(address.get("province"), address.get("province_code"))
        if state and not pincodes.state_matches(pin, state):
            reasons.append(Reason("pin_state_mismatch", 25,
                                  f"PIN code {pin} is not in {state.title()}.",
                                  "Confirm your PIN code and state."))

    # --- street address -------------------------------------------------------
    alnum = re.sub(r"[^0-9a-z]", "", street.lower())
    has_number = bool(re.search(r"\d", street))
    has_unit = bool(_UNIT.search(street))
    if len(alnum) < 15:
        reasons.append(Reason("address_short", 20, "Street address is too short to locate.",
                              "Add your house/flat number, street and area."))
    # A landmark with no door number is the classic failed-delivery address, so
    # these two together must reach "medium" (20 + 15 = 35) on their own.
    if not has_number and not has_unit:
        reasons.append(Reason("no_door", 20, "No house, flat or plot number.",
                              "Add your house/flat/plot number."))
    if _VAGUE.search(street) and not has_number:
        reasons.append(Reason("landmark_only", 15, "Address relies on a landmark with no door number.",
                              "Add a door number along with the landmark."))
    if street and _text_is_junk(street):
        reasons.append(Reason("address_junk", 30, "Street address looks like placeholder or random text.",
                              "Re-enter your full delivery address."))
    if not city:
        reasons.append(Reason("city_missing", 10, "City is missing.", "Add your city."))

    # --- customer -------------------------------------------------------------
    letters = re.sub(r"[^a-z]", "", name.lower())
    if len(letters) < 2 or re.search(r"\d", name) or _text_is_junk(name):
        reasons.append(Reason("name_junk", 15, "Customer name looks fake or is missing."))
    reasons.extend(_phone_reasons(address.get("phone")))

    # --- order + history ------------------------------------------------------
    if order_total > 10000:
        reasons.append(Reason("high_value", 15, f"High-value COD order (Rs {order_total:,.0f})."))
    elif order_total > 5000:
        reasons.append(Reason("high_value", 10, f"Above-average COD order value (Rs {order_total:,.0f})."))
    if history.prior_rto:
        pts = min(40, 20 * history.prior_rto)
        reasons.append(Reason("prior_rto", pts,
                              f"{history.prior_rto} earlier order(s) from this phone were returned or cancelled."))
    if history.orders_last_24h >= 2:
        reasons.append(Reason("burst", 15,
                              f"{history.orders_last_24h} other COD orders from this phone in the last 24 hours."))

    risk = min(100, sum(r.points for r in reasons))
    return Result(risk=risk, band=band_for(risk), reasons=reasons)
