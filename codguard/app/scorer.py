"""Deterministic RTO-risk scorer for cash-on-delivery shipping addresses, any country.

Every point of risk comes from a named rule with a human-readable reason, so a
merchant can see exactly why an order was flagged. No model is involved: the
score must be reproducible and explainable, and each rule is unit-tested.

Risk is 0-100 (higher = more likely to come back undelivered):
    < 30  low     ship normally
    30-59 medium  ask the customer to confirm
    >= 60 high    confirm before shipping; consider prepaid-only

Reasons carry an `ask` KEY (not text): the customer page renders it in the
shopper's language via i18n.py. Reason `message`s are for the merchant (English).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import phonenumbers
from phonenumbers import PhoneNumberType

from . import countries, pincodes

LOW_MAX = 29
HIGH_MIN = 60

_VAGUE = re.compile(
    r"\b(near|nr\.?|behind|opp\.?|opposite|beside|besides|next to|in front of|close to|nearby|"
    r"backside|cerca de|frente a|enfrente de|atr[aá]s de|junto a|perto de|em frente|ao lado de|"
    r"pr[eè]s de|derri[eè]re|en face de|dekat|depan|belakang|samping|naproti|obok|l[aâ]ng[aă]|"
    r"vicino a|dietro)\b"
    r"|بجانب|بالقرب من|قرب|خلف|مقابل|أمام|جنب",
    re.I,
)
# Words that point to a specific door or building the courier can find.
_UNIT = re.compile(
    r"\b(flat|flt|house|h\.?\s?no|hno|plot|door|d\.?\s?no|room|rm|floor|flr|block|blk|wing|tower|"
    r"apt|apartment|bldg|building|shop|gali|lane|sector|street|st\.?|road|rd\.?|ward|qtr|quarter|"
    r"villa|bungalow|unit|suite|avenue|ave|"
    r"calle|avenida|av\.?|carrera|cra|edificio|edif|apto|apartamento|piso|depto|departamento|"
    r"casa|n[uú]mero|n[º°o]\.?|interior|int\.?|colonia|col\.?|rua|travessa|bloco|"
    r"rue|b[aâ]timent|appartement|"
    r"jalan|jl\.?|blok|gang|gg\.?|rt|rw|lorong|"
    r"ulica|ul\.?|strada|str\.?|bloc|sc\.?|ap\.?|via|piazza|sokak|sk\.?|mahalle|mah\.?|cadde|cd\.?|"
    r"odos|οδός)\b"
    r"|شارع|عمارة|مبنى|فيلا|شقة|برج|طابق|بناية",
    re.I,
)
_JUNK_TOKENS = re.compile(
    # Deliberately excludes short real-world words like "abc"/"xyz" (ABC Apartments).
    r"\b(test|testing|asdf\w*|qwerty\w*|dummy|fake|sample|n/a|none|null|xxx+|prueba|teste)\b|تجربة",
    re.I,
)
_REPEAT_CHAR = re.compile(r"(.)\1{3,}")
_CONSONANT_RUN = re.compile(r"[bcdfghjklmnpqrstvwxz]{6,}", re.I)
_LETTER = re.compile(r"[^\W\d_]")

# Approximate USD value of one unit of currency, for a COARSE "high value" flag
# only when the shop has too little history for its own baseline. Not for billing.
_USD_PER_UNIT = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "AED": 0.272, "SAR": 0.267, "QAR": 0.275, "KWD": 3.25,
    "BHD": 2.65, "OMR": 2.6, "EGP": 0.02, "MAD": 0.1, "TRY": 0.03, "INR": 0.012, "PKR": 0.0036,
    "BDT": 0.0085, "IDR": 0.000063, "PHP": 0.017, "MYR": 0.22, "THB": 0.028, "VND": 0.00004,
    "MXN": 0.055, "BRL": 0.18, "COP": 0.00025, "PEN": 0.27, "CLP": 0.0011, "PLN": 0.25,
    "RON": 0.22, "CZK": 0.043, "HUF": 0.0027, "BGN": 0.55, "NGN": 0.00065, "KES": 0.0077,
}
MIN_BASELINE_ORDERS = 20


@dataclass
class Reason:
    code: str
    points: int
    message: str
    ask: str = ""  # i18n key of what to ask the customer, if anything


@dataclass
class Result:
    risk: int
    band: str
    reasons: list[Reason] = field(default_factory=list)

    @property
    def asks(self) -> list[str]:
        return list(dict.fromkeys(r.ask for r in self.reasons if r.ask))

    def to_dict(self) -> dict:
        return {"risk": self.risk, "band": self.band, "reasons": [r.__dict__ for r in self.reasons]}


@dataclass
class History:
    """What we already know about this phone number and this shop."""
    prior_rto: int = 0             # earlier orders the merchant marked returned/cancelled
    orders_last_24h: int = 0       # other COD orders from the same phone in the last day
    typical_total: float = 0.0     # median COD order value at this shop (shop currency)
    baseline_orders: int = 0       # how many orders typical_total is based on


def band_for(risk: int) -> str:
    if risk >= HIGH_MIN:
        return "high"
    if risk > LOW_MAX:
        return "medium"
    return "low"


def parse_phone(raw: str | None, country: str) -> phonenumbers.PhoneNumber | None:
    if not raw or not raw.strip():
        return None
    try:
        return phonenumbers.parse(raw, country or None)
    except phonenumbers.NumberParseException:
        return None


def normalize_phone(raw: str | None, country: str) -> str:
    """E.164 (e.g. +971501234567) for valid numbers, '' otherwise."""
    num = parse_phone(raw, country)
    if num is None or not phonenumbers.is_valid_number(num):
        return ""
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def _phone_reasons(raw: str | None, country: str) -> list[Reason]:
    if not raw or not raw.strip():
        return [Reason("phone_missing", 30, "No phone number, so the courier cannot call.", "phone")]
    num = parse_phone(raw, country)
    if num is None or not phonenumbers.is_valid_number(num):
        return [Reason("phone_invalid", 30, f"Phone number '{raw}' is not a valid number"
                       f"{' for ' + country if country else ''}.", "phone")]
    national = str(num.national_number)
    if len(set(national)) <= 2 or national in "0123456789012" or national in "9876543210987":
        return [Reason("phone_fake", 30, "Phone number looks made up (repeated or sequential digits).", "phone")]
    if phonenumbers.number_type(num) not in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE,
                                             PhoneNumberType.FIXED_LINE):
        return [Reason("phone_unreachable", 15, "Phone number is not a mobile or landline number.", "phone")]
    return []


def _postal_reasons(address: dict, country: str) -> list[Reason]:
    raw = address.get("zip")
    if country == "IN":  # deeper check: PIN prefix must exist and match the state
        pin = pincodes.normalize_pin(raw)
        if not pincodes.is_well_formed(pin):
            return [Reason("postal_malformed", 35, f"PIN code '{raw or ''}' is not 6 digits.", "postal")]
        if not pincodes.prefix_exists(pin):
            return [Reason("postal_unknown", 35, f"PIN code {pin} does not belong to any Indian postal circle.",
                           "postal")]
        state = pincodes.normalize_state(address.get("province"), address.get("province_code"))
        if state and not pincodes.state_matches(pin, state):
            return [Reason("postal_region_mismatch", 25, f"PIN code {pin} is not in {state.title()}.",
                           "postal_region")]
        return []
    status = countries.postal_status(country, raw)
    if status == "missing":
        return [Reason("postal_missing", 25, f"Postal code is missing ({country} uses postal codes).", "postal")]
    if status == "malformed":
        return [Reason("postal_malformed", 30, f"Postal code '{raw}' is not a valid {country} format.", "postal")]
    return []


def _text_is_junk(text: str) -> bool:
    return bool(_JUNK_TOKENS.search(text) or _REPEAT_CHAR.search(text) or _CONSONANT_RUN.search(text))


def _value_reason(total: float, currency: str, h: History) -> Reason | None:
    label = f"{total:,.0f} {currency}".strip()
    if h.baseline_orders >= MIN_BASELINE_ORDERS and h.typical_total > 0:
        ratio = total / h.typical_total
        if ratio >= 3:
            return Reason("high_value", 15, f"COD order of {label} is {ratio:.1f}x this store's typical order.")
        if ratio >= 2:
            return Reason("high_value", 10, f"COD order of {label} is {ratio:.1f}x this store's typical order.")
        return None
    rate = _USD_PER_UNIT.get(currency.upper())
    if rate is None:
        return None
    usd = total * rate
    if usd > 250:
        return Reason("high_value", 15, f"High-value COD order ({label}).")
    if usd > 120:
        return Reason("high_value", 10, f"Above-average COD order value ({label}).")
    return None


def score(address: dict, *, order_total: float = 0.0, currency: str = "",
          history: History | None = None) -> Result:
    """Score one Shopify shipping_address dict."""
    h = history or History()
    country = countries.normalize_country(address.get("country_code"))
    reasons: list[Reason] = []

    line1 = (address.get("address1") or "").strip()
    line2 = (address.get("address2") or "").strip()
    street = f"{line1} {line2}".strip()
    city = (address.get("city") or "").strip()
    name = (address.get("name") or
            f"{address.get('first_name') or ''} {address.get('last_name') or ''}").strip()

    reasons.extend(_postal_reasons(address, country))

    # --- street address -------------------------------------------------------
    chars = re.sub(r"[\W_]", "", street)
    has_number = bool(re.search(r"\d", street))
    has_unit = bool(_UNIT.search(street))
    landmark_addressing = country in countries.LANDMARK_ADDRESSING
    if len(chars) < 15:
        reasons.append(Reason("address_short", 20, "Street address is too short to locate.", "full_address"))
    if not has_number and not has_unit:
        # Where landmark-based addressing is the norm the courier usually calls
        # ahead, so a missing door number matters less than a bad phone.
        pts = 10 if landmark_addressing else 20
        reasons.append(Reason("no_door", pts, "No house, flat, building or street number.", "door"))
    # A landmark with no door number is the classic failed-delivery address, so
    # outside landmark-addressing countries these two reach "medium" (20+15) alone.
    if not landmark_addressing and _VAGUE.search(street) and not has_number:
        reasons.append(Reason("landmark_only", 15, "Address relies on a landmark with no door number.", "door"))
    if street and _text_is_junk(street):
        reasons.append(Reason("address_junk", 30, "Street address looks like placeholder or random text.",
                              "full_address"))
    if not city:
        reasons.append(Reason("city_missing", 10, "City is missing.", "city"))

    # --- customer -------------------------------------------------------------
    if len(_LETTER.findall(name)) < 2 or re.search(r"\d", name) or _text_is_junk(name):
        reasons.append(Reason("name_junk", 15, "Customer name looks fake or is missing."))
    reasons.extend(_phone_reasons(address.get("phone"), country))

    # --- order + history ------------------------------------------------------
    value = _value_reason(order_total, currency, h)
    if value:
        reasons.append(value)
    if h.prior_rto:
        reasons.append(Reason("prior_rto", min(40, 20 * h.prior_rto),
                              f"{h.prior_rto} earlier order(s) from this phone were returned or cancelled."))
    if h.orders_last_24h >= 2:
        reasons.append(Reason("burst", 15,
                              f"{h.orders_last_24h} other COD orders from this phone in the last 24 hours."))

    risk = min(100, sum(r.points for r in reasons))
    return Result(risk=risk, band=band_for(risk), reasons=reasons)
