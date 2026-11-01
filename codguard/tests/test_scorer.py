import pytest

from app import countries, scorer
from app.scorer import History

IN = {"name": "Priya Sharma", "address1": "Flat 302, Sunrise Apartments, 14th Main Road",
      "address2": "HSR Layout Sector 2", "city": "Bengaluru", "province": "Karnataka",
      "province_code": "KA", "zip": "560102", "country_code": "IN", "phone": "+91 98450 12345"}
AE = {"name": "محمد العلي", "address1": "Villa 12, Street 7, Al Barsha 2", "address2": "",
      "city": "Dubai", "province_code": "DU", "zip": "", "country_code": "AE", "phone": "050 123 4567"}
SA = {"name": "Fahad Al-Qahtani", "address1": "Building 4521, King Fahd Road, Al Olaya", "address2": "",
      "city": "Riyadh", "zip": "12211", "country_code": "SA", "phone": "0551234567"}
MX = {"name": "María López", "address1": "Calle Durango 120, Int. 4", "address2": "Col. Roma Norte",
      "city": "Ciudad de México", "zip": "06700", "country_code": "MX", "phone": "55 1234 5678"}
BR = {"name": "João Silva", "address1": "Rua Augusta 1500, apto 81", "address2": "Consolação",
      "city": "São Paulo", "zip": "01304-001", "country_code": "BR", "phone": "(11) 91234-5678"}
ID = {"name": "Budi Santoso", "address1": "Jl. Sudirman No. 45, RT 03/RW 05", "address2": "Kebayoran Baru",
      "city": "Jakarta Selatan", "zip": "12190", "country_code": "ID", "phone": "0812-3456-7890"}
PL = {"name": "Anna Kowalska", "address1": "ul. Marszałkowska 84/92 m. 15", "address2": "",
      "city": "Warszawa", "zip": "00-514", "country_code": "PL", "phone": "512 345 678"}


def codes(result):
    return {r.code for r in result.reasons}


@pytest.mark.parametrize("addr", [IN, AE, SA, MX, BR, ID, PL], ids=lambda a: a["country_code"])
def test_complete_addresses_are_low_risk_everywhere(addr):
    r = scorer.score(addr)
    assert r.band == "low" and r.risk == 0, r.reasons


def test_non_latin_names_are_not_junk():
    assert "name_junk" not in codes(scorer.score(AE))
    assert "name_junk" not in codes(scorer.score({**IN, "name": "प्रिया शर्मा"}))


# --- landmarks: risk signal in India, normal addressing in the Gulf -------------

def test_landmark_only_is_flagged_in_india():
    r = scorer.score({**IN, "address1": "near hanuman temple", "address2": "behind school"})
    assert {"no_door", "landmark_only"} <= codes(r)
    assert r.band == "medium"


def test_landmark_addressing_is_normal_in_uae():
    r = scorer.score({**AE, "address1": "Al Wasl Road, near Safa Park, Jumeirah"})
    assert "landmark_only" not in codes(r) and r.band == "low"
    arabic = scorer.score({**AE, "address1": "بالقرب من مسجد الفاروق، حي الصفا، جميرا"})
    assert "landmark_only" not in codes(arabic) and arabic.band == "low"


def test_landmark_only_is_flagged_in_latin_america():
    r = scorer.score({**MX, "address1": "cerca de la iglesia", "address2": "atrás del mercado"})
    assert "landmark_only" in codes(r) and r.band == "medium"


def test_unit_words_are_recognised_in_many_languages():
    for addr in ({**MX, "address1": "Calle Durango, Edificio Torre Sol, Colonia Roma"},
                 {**ID, "address1": "Jalan Melati, Blok C, Kebayoran Baru"},
                 {**AE, "address1": "شارع الوصل، فيلا الرحمة، جميرا"}):
        assert "no_door" not in codes(scorer.score(addr)), addr["address1"]


# --- postal codes ---------------------------------------------------------------

def test_no_postcode_countries_are_not_penalised():
    assert not {"postal_missing", "postal_malformed"} & codes(scorer.score({**AE, "zip": ""}))


def test_postal_formats_per_country():
    assert "postal_malformed" in codes(scorer.score({**SA, "zip": "1221"}))
    assert "postal_missing" in codes(scorer.score({**SA, "zip": ""}))
    assert "postal_malformed" in codes(scorer.score({**BR, "zip": "0130400"}))
    assert not codes(scorer.score({**BR, "zip": "01304001"}))
    assert "postal_malformed" in codes(scorer.score({**PL, "zip": "00514X"}))
    assert not codes(scorer.score({**PL, "zip": "00514"}))


def test_unknown_country_skips_postal_rule_only():
    r = scorer.score({**MX, "country_code": "ZZ", "zip": "whatever", "phone": "+52 55 1234 5678"})
    assert not {"postal_missing", "postal_malformed"} & codes(r)


def test_india_pin_rules():
    assert "postal_malformed" in codes(scorer.score({**IN, "zip": "5601"}))
    assert "postal_malformed" in codes(scorer.score({**IN, "zip": "060102"}))
    assert "postal_unknown" in codes(scorer.score({**IN, "zip": "990102"}))
    assert "postal_region_mismatch" in codes(scorer.score({**IN, "zip": "400001"}))
    assert "postal_region_mismatch" not in codes(scorer.score({**IN, "zip": "400001", "province_code": "MH"}))
    assert "postal_region_mismatch" not in codes(scorer.score(
        {**IN, "zip": "110001", "province": "New Delhi", "province_code": ""}))


# --- phones ---------------------------------------------------------------------

def test_phone_rules_are_country_aware():
    assert "phone_missing" in codes(scorer.score({**AE, "phone": ""}))
    assert "phone_invalid" in codes(scorer.score({**AE, "phone": "12345"}))
    assert "phone_invalid" in codes(scorer.score({**IN, "phone": "+91 98450"}))  # too short
    assert not codes(scorer.score({**IN, "phone": "0512 345 6789"}))  # Kanpur landline is reachable
    assert "phone_fake" in codes(scorer.score({**IN, "phone": "9999999999"}))
    assert "phone_fake" in codes(scorer.score({**IN, "phone": "9876543210"}))
    # a valid Mexican number is invalid if the address says Saudi Arabia
    assert "phone_invalid" in codes(scorer.score({**SA, "phone": "55 1234 5678"}))
    # international format always works regardless of the address country
    assert not codes(scorer.score({**SA, "phone": "+52 55 1234 5678"}))


def test_unreachable_phone_alone_reaches_medium():
    # COD without a callable customer is a likely return anywhere, and in the Gulf
    # (landmark addressing) the courier relies on the call to find the door.
    for addr in (AE, MX, IN):
        for phone in ("", "123"):
            assert scorer.score({**addr, "phone": phone}).band == "medium", (addr["country_code"], phone)


def test_normalize_phone_returns_e164():
    assert scorer.normalize_phone("050 123 4567", "AE") == "+971501234567"
    assert scorer.normalize_phone("09845012345", "IN") == "+919845012345"
    assert scorer.normalize_phone("junk", "AE") == ""


# --- value + history ------------------------------------------------------------

def test_high_value_uses_store_baseline_when_available():
    h = History(typical_total=400, baseline_orders=50)
    assert "high_value" in codes(scorer.score(AE, order_total=1300, currency="AED", history=h))
    assert "high_value" not in codes(scorer.score(AE, order_total=700, currency="AED", history=h))


def test_high_value_falls_back_to_currency_without_baseline():
    assert "high_value" in codes(scorer.score(MX, order_total=6000, currency="MXN"))  # ~$330
    assert "high_value" not in codes(scorer.score(MX, order_total=800, currency="MXN"))
    assert "high_value" not in codes(scorer.score(MX, order_total=10**9, currency="XXX"))  # unknown


def test_history_raises_risk():
    r = scorer.score(IN, history=History(prior_rto=2, orders_last_24h=3))
    assert {"prior_rto", "burst"} <= codes(r)
    assert r.risk == 40 + 15


def test_junk_text_is_high_risk():
    r = scorer.score({**MX, "name": "test test", "address1": "asdfgh", "address2": "", "phone": "1111111111"})
    assert r.band == "high" and {"address_junk", "name_junk"} <= codes(r)


def test_real_building_names_are_not_junk():
    assert "address_junk" not in codes(scorer.score({**IN, "address1": "12 ABC Apartments, XYZ Road"}))


def test_risk_is_capped_and_asks_are_keys():
    r = scorer.score({"name": "", "address1": "", "zip": "", "phone": "", "city": "", "country_code": "SA"},
                     history=History(prior_rto=5))
    assert r.risk == 100
    from app import i18n
    assert r.asks and all(f"ask.{a}" in i18n.STRINGS["en"] for a in r.asks)


def test_band_boundaries():
    assert [scorer.band_for(x) for x in (29, 30, 59, 60)] == ["low", "medium", "medium", "high"]


# --- COD detection --------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Cash on Delivery (COD)", "COD", "Pago contra entrega", "Contra reembolso", "Pagamento na entrega",
    "Paiement à la livraison", "Za pobraniem", "Ramburs", "Dobírka", "Kapıda ödeme", "Bayar di tempat (COD)",
    "الدفع عند الاستلام", "Nachnahme",
])
def test_cod_gateway_names(name):
    assert countries.is_cod_gateway(name)


@pytest.mark.parametrize("name", ["shopify_payments", "razorpay", "PayPal", "Tabby", "Mercado Pago", "codigo promo"])
def test_prepaid_gateway_names(name):
    assert not countries.is_cod_gateway(name)
