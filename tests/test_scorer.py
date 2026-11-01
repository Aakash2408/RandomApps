from app import scorer
from app.scorer import History

GOOD = {"name": "Priya Sharma", "address1": "Flat 302, Sunrise Apartments, 14th Main Road",
        "address2": "HSR Layout Sector 2", "city": "Bengaluru", "province": "Karnataka",
        "province_code": "KA", "zip": "560102", "phone": "+91 98450 12345"}


def codes(result):
    return {r.code for r in result.reasons}


def test_complete_address_is_low_risk():
    r = scorer.score(GOOD, order_total=1499)
    assert r.band == "low" and r.risk == 0, r.reasons


def test_landmark_only_address_is_flagged():
    r = scorer.score({**GOOD, "address1": "near hanuman temple", "address2": "behind school"})
    assert {"no_door", "landmark_only"} <= codes(r)
    assert r.band == "medium"


def test_malformed_and_impossible_pins():
    assert "pin_malformed" in codes(scorer.score({**GOOD, "zip": "5601"}))
    assert "pin_malformed" in codes(scorer.score({**GOOD, "zip": "060102"}))
    assert "pin_unknown" in codes(scorer.score({**GOOD, "zip": "990102"}))  # army postal / unused


def test_pin_state_mismatch_uses_province_code():
    r = scorer.score({**GOOD, "zip": "400001"})  # Mumbai PIN, Karnataka state
    assert "pin_state_mismatch" in codes(r)
    assert "pin_state_mismatch" not in codes(scorer.score({**GOOD, "zip": "400001", "province_code": "MH"}))


def test_state_aliases_and_shared_circles():
    assert "pin_state_mismatch" not in codes(scorer.score(
        {**GOOD, "zip": "110001", "province": "New Delhi", "province_code": ""}))
    assert "pin_state_mismatch" not in codes(scorer.score(
        {**GOOD, "zip": "403001", "province_code": "GA"}))  # Goa sits in the 40 circle


def test_phone_rules():
    assert "phone_missing" in codes(scorer.score({**GOOD, "phone": ""}))
    assert "phone_invalid" in codes(scorer.score({**GOOD, "phone": "12345"}))
    assert "phone_invalid" in codes(scorer.score({**GOOD, "phone": "5123456789"}))
    assert "phone_fake" in codes(scorer.score({**GOOD, "phone": "9999999999"}))
    assert "phone_fake" in codes(scorer.score({**GOOD, "phone": "9876543210"}))
    assert not codes(scorer.score({**GOOD, "phone": "09845012345"}))


def test_junk_text_is_high_risk():
    r = scorer.score({**GOOD, "name": "test test", "address1": "asdfgh", "address2": "", "phone": "1111111111"})
    assert r.band == "high"
    assert {"address_junk", "name_junk"} <= codes(r)


def test_real_building_names_are_not_junk():
    r = scorer.score({**GOOD, "address1": "12 ABC Apartments, XYZ Road"})
    assert "address_junk" not in codes(r)


def test_history_and_value_raise_risk():
    r = scorer.score(GOOD, order_total=12000, history=History(prior_rto=2, orders_last_24h=3))
    assert {"high_value", "prior_rto", "burst"} <= codes(r)
    assert r.risk == 15 + 40 + 15 and r.band == "high"


def test_risk_is_capped_and_asks_are_offered():
    r = scorer.score({"name": "", "address1": "", "zip": "", "phone": "", "city": ""},
                     history=History(prior_rto=5))
    assert r.risk == 100
    assert r.asks and all(isinstance(a, str) for a in r.asks)


def test_band_boundaries():
    assert scorer.band_for(29) == "low"
    assert scorer.band_for(30) == "medium"
    assert scorer.band_for(59) == "medium"
    assert scorer.band_for(60) == "high"
