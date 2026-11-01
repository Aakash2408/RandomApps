import pytest
from fastapi.testclient import TestClient

from server import main

KEY = "80e15db5-c796-436b-850c-8f9c98a48abe"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LEMONSQUEEZY_STORE_ID", "77")
    monkeypatch.setenv("LEMONSQUEEZY_PACK_VARIANTS", "1:plus,2:editor,3:rewind,4:bogus")
    monkeypatch.setenv("CHECKOUT_URL_PLUS", "https://lifetimes.lemonsqueezy.com/buy/plus")
    monkeypatch.setenv("PRICE_PLUS", "$2.99")
    main._hits.clear()


@pytest.fixture
def client():
    return TestClient(main.app)


def ls(monkeypatch, valid=True, status="inactive", store=77, variant=1):
    calls = []

    def fake(key):
        calls.append(key)
        return {"valid": valid, "license_key": {"status": status}, "meta": {"store_id": store, "variant_id": variant}}
    monkeypatch.setattr(main, "_fetch", fake)
    return calls


def test_game_is_served_with_strict_script_policy(client):
    r = client.get("/")
    assert r.status_code == 200 and "Lifetimes" in r.text and '<script src="/game.js">' in r.text
    csp = r.headers["content-security-policy"]
    assert "script-src 'self';" in csp and "frame-ancestors 'none'" in csp
    assert client.get("/game.js").status_code == 200 and client.get("/style.css").status_code == 200


def test_config_lists_only_configured_checkouts(client):
    j = client.get("/api/config").json()
    assert j == {"checkout": {"plus": "https://lifetimes.lemonsqueezy.com/buy/plus"}, "prices": {"plus": "$2.99"}}


@pytest.mark.parametrize("variant,pack", [(1, "plus"), (2, "editor"), (3, "rewind")])
def test_fresh_key_unlocks_its_pack(client, monkeypatch, variant, pack):
    ls(monkeypatch, variant=variant)
    assert client.post("/api/unlock", json={"key": KEY}).json() == {"packs": [pack]}


@pytest.mark.parametrize("kw,msg", [
    ({"valid": False}, "not valid"), ({"status": "disabled"}, "refunded"), ({"status": "expired"}, "not valid"),
    ({"store": 999}, "not for Lifetimes"), ({"variant": 4}, "unknown item"), ({"variant": 50}, "unknown item"),
])
def test_bad_keys_are_rejected(client, monkeypatch, kw, msg):
    ls(monkeypatch, **kw)
    r = client.post("/api/unlock", json={"key": KEY})
    assert r.status_code == 403 and msg in r.json()["error"]


def test_input_validation(client, monkeypatch):
    calls = ls(monkeypatch)
    for body in ({}, {"key": 5}, {"key": "short"}, {"key": "x" * 101}, ["x"]):
        assert client.post("/api/unlock", json=body).status_code == 400
    assert client.post("/api/unlock", content=b"nope").status_code == 400
    assert calls == []


def test_unconfigured_store_fails_closed(client, monkeypatch):
    calls = ls(monkeypatch)
    monkeypatch.setenv("LEMONSQUEEZY_STORE_ID", "")
    assert client.post("/api/unlock", json={"key": KEY}).status_code == 503 and calls == []


def test_lemon_squeezy_outage_fails_closed(client, monkeypatch):
    def boom(key):
        raise ConnectionError
    monkeypatch.setattr(main, "_fetch", boom)
    assert client.post("/api/unlock", json={"key": KEY}).status_code == 503


def test_unlock_is_rate_limited(client, monkeypatch):
    ls(monkeypatch, valid=False)
    codes = [client.post("/api/unlock", json={"key": KEY}).status_code for _ in range(main.UNLOCKS_PER_HOUR + 1)]
    assert codes[:-1] == [403] * main.UNLOCKS_PER_HOUR and codes[-1] == 429
