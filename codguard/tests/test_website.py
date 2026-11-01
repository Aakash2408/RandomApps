import csv
import dataclasses
import io

import pytest
from fastapi.testclient import TestClient

from website import bulk, config, licenses, limits, main

STORE = "4242"
KEY = "38b1460a-5104-4067-a91d-77b872934d51"


@pytest.fixture(autouse=True)
def site(tmp_path, monkeypatch):
    s = dataclasses.replace(config.settings, db_path=str(tmp_path / "w.sqlite3"), ls_store_id=STORE,
                            plan_variants={"11": "starter", "22": "growth"}, free_checks_per_day=3,
                            checkout_urls={"starter": "https://codguard.lemonsqueezy.com/buy/a", "growth": "", "pro": ""})
    monkeypatch.setattr(config, "settings", s)
    limits.reset()
    licenses._cache.clear()
    return s


@pytest.fixture
def client():
    return TestClient(main.app)


def ls_response(valid=True, status="active", store=STORE, variant=11):
    return {"valid": valid, "error": None if valid else "license_key not found",
            "license_key": {"status": status, "key": KEY},
            "meta": {"store_id": int(store), "variant_id": variant, "customer_email": "owner@example.com"}}


@pytest.fixture
def ls(monkeypatch):
    calls = []
    state = {"resp": ls_response()}

    def fake(key):
        calls.append(key)
        return state["resp"]
    monkeypatch.setattr(licenses, "_fetch", fake)
    return state, calls


AUTH = {"Authorization": f"Bearer {KEY}"}

SHOPIFY_EXPORT = (
    "Name,Email,Financial Status,Total,Currency,Lineitem name,Payment Method,Shipping Name,Shipping Address1,"
    "Shipping Address2,Shipping City,Shipping Zip,Shipping Province,Shipping Country,Shipping Phone\n"
    "#1001,a@x.com,pending,250.00,AED,Ivory Bloom,Cash on Delivery (COD),Mariam K,Villa 18 Street 22b Al Barsha 2,,"
    "Dubai,,DU,AE,050 412 7781\n"
    "#1001,a@x.com,,,,Mauve Bow,,,,,,,,,\n"
    "#1002,b@x.com,pending,129.00,AED,Mauve Bow,Cash on Delivery (COD),test,near mall,,,,,AE,0500000000\n"
    "#1003,c@x.com,pending,199.00,AED,Black Lace,Cash on Delivery (COD),=HYPERLINK(\"http://evil\"),"
    "Flat 1204 Marina Gate 1,,Dubai,,DU,AE,+971 52 908 1146\n"
)


# --- pages + free checker ---------------------------------------------------------

def test_landing_renders_with_checkout_links(client):
    r = client.get("/")
    assert r.status_code == 200 and "Stop shipping COD orders" in r.text
    assert "https://codguard.lemonsqueezy.com/buy/a" in r.text
    assert 'aria-disabled="true"' in r.text  # growth/pro have no checkout configured yet
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_free_check_scores_and_is_rate_limited(client):
    body = {"country_code": "AE", "name": "test", "address1": "near mall", "phone": "0500000000"}
    r = client.post("/api/check", json=body)
    assert r.status_code == 200 and r.json()["band"] == "high" and r.json()["free_checks_left_today"] == 2
    client.post("/api/check", json=body)
    client.post("/api/check", json=body)
    r = client.post("/api/check", json=body)
    assert r.status_code == 429 and "Subscribe" in r.json()["error"]


def test_free_check_validates_input(client):
    assert client.post("/api/check", content=b"not json").status_code == 400
    assert client.post("/api/check", json=["x"]).status_code == 400
    assert client.post("/api/check", json={"address1": "x" * 301}).status_code == 400
    assert client.post("/api/check", json={"address1": 5}).status_code == 400
    assert client.post("/api/check", json={"order_total": "lots"}).status_code == 400


def test_global_free_ceiling(client, monkeypatch):
    monkeypatch.setattr(limits, "GLOBAL_PER_DAY", 2)
    monkeypatch.setattr(limits, "CLIENT_IP_HEADER", "x-forwarded-for")
    for i, ip in enumerate(["1.1.1.1", "2.2.2.2"]):
        assert client.post("/api/check", json={}, headers={"X-Forwarded-For": ip}).status_code == 200
    assert client.post("/api/check", json={}, headers={"X-Forwarded-For": "3.3.3.3"}).status_code == 429


def test_client_ip_uses_last_forwarded_hop(monkeypatch):
    monkeypatch.setattr(limits, "CLIENT_IP_HEADER", "x-forwarded-for")
    assert limits.client_id({"x-forwarded-for": "6.6.6.6, 9.9.9.9"}, "10.0.0.1") == "9.9.9.9"
    monkeypatch.setattr(limits, "CLIENT_IP_HEADER", "")
    assert limits.client_id({"x-forwarded-for": "6.6.6.6"}, "10.0.0.1") == "10.0.0.1"


# --- license gate -------------------------------------------------------------------

def test_paid_routes_require_a_license(client, ls):
    assert client.get("/api/v1/usage").status_code == 401
    assert client.post("/api/v1/check", json={}).status_code == 401
    assert client.post("/api/bulk", files={"file": ("o.csv", b"a")}).status_code == 401


@pytest.mark.parametrize("resp,why", [
    (ls_response(valid=False), "not active"),
    (ls_response(status="expired"), "not active"),
    (ls_response(status="disabled"), "not active"),
    (ls_response(store="9999"), "not for CODGuard"),     # another Lemon Squeezy seller's key
    (ls_response(variant=77), "unknown plan"),
])
def test_bad_licenses_are_rejected(client, ls, resp, why):
    ls[0]["resp"] = resp
    r = client.get("/api/v1/usage", headers=AUTH)
    assert r.status_code == 403 and why in r.json()["error"]


def test_unconfigured_store_fails_closed(client, ls, site, monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(site, ls_store_id=""))
    assert client.get("/api/v1/usage", headers=AUTH).status_code == 503
    assert ls[1] == []  # never even asked Lemon Squeezy


def test_lemon_squeezy_outage_fails_closed(client, monkeypatch):
    def boom(key):
        raise ConnectionError("down")
    monkeypatch.setattr(licenses, "_fetch", boom)
    assert client.get("/api/v1/usage", headers=AUTH).status_code == 503


def test_valid_license_is_cached(client, ls):
    for _ in range(3):
        assert client.get("/api/v1/usage", headers=AUTH).json()["plan"] == "Starter"
    assert len(ls[1]) == 1


# --- paid check + bulk ----------------------------------------------------------------

def test_paid_check_counts_usage_and_enforces_quota(client, ls, monkeypatch):
    monkeypatch.setitem(config.PLANS, "starter", config.Plan("starter", "Starter", 9, 2))
    body = {"country_code": "AE", "name": "Fatima Ali", "address1": "Villa 12, Street 7, Al Barsha 2", "city": "Dubai",
            "phone": "0501234567"}
    assert client.post("/api/v1/check", json=body, headers=AUTH).json()["band"] == "low"
    assert client.post("/api/v1/check", json=body, headers=AUTH).status_code == 200
    r = client.post("/api/v1/check", json=body, headers=AUTH)
    assert r.status_code == 429 and "0 left" in r.json()["error"]
    assert client.get("/api/v1/usage", headers=AUTH).json()["used_this_month"] == 2


def test_bulk_scores_a_shopify_export(client, ls):
    r = client.post("/api/bulk", headers=AUTH, files={"file": ("orders_export.csv", SHOPIFY_EXPORT.encode())})
    assert r.status_code == 200
    assert r.headers["content-disposition"] == 'attachment; filename="orders_export-codguard.csv"'
    assert (r.headers["x-codguard-orders"], r.headers["x-codguard-flagged"]) == ("3", "1")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert [x["order"] for x in rows][0] == "#1002"           # riskiest first
    assert rows[0]["band"] == "high" and "made up" in rows[0]["reasons"] and "too short" in rows[0]["reasons"]
    by = {x["order"]: x for x in rows}
    assert by["#1001"]["band"] == "low"                        # line-item rows merged, not double-counted
    assert by["#1003"]["name"].startswith("'=")                # formula injection neutralised
    assert client.get("/api/v1/usage", headers=AUTH).json()["used_this_month"] == 3


def test_bulk_quota_is_checked_before_scoring(client, ls, monkeypatch):
    monkeypatch.setitem(config.PLANS, "starter", config.Plan("starter", "Starter", 9, 2))
    r = client.post("/api/bulk", headers=AUTH, files={"file": ("o.csv", SHOPIFY_EXPORT.encode())})
    assert r.status_code == 429 and "3 checks" in r.json()["error"]
    assert client.get("/api/v1/usage", headers=AUTH).json()["used_this_month"] == 0


def test_bulk_generic_csv_with_default_country(client, ls):
    data = b"order,customer,address,city,postcode,phone\nA1,Juan Perez,cerca de la iglesia,Puebla,72000,222 123 4567\n"
    r = client.post("/api/bulk", headers=AUTH, files={"file": ("x.csv", data)}, data={"default_country": "MX"})
    [row] = list(csv.DictReader(io.StringIO(r.text)))
    assert row["country"] == "MX" and row["band"] == "medium"


def test_bulk_rejects_bad_files(client, ls):
    assert "address and a phone" in client.post("/api/bulk", headers=AUTH,
        files={"file": ("x.csv", b"foo,bar\n1,2\n")}).json()["error"]
    assert client.post("/api/bulk", headers=AUTH, files={"file": ("x.csv", b"")}).status_code == 400
    big = b"address,phone\n" + b"x,1\n" * (bulk.MAX_BYTES // 4 + 10)
    assert "larger than" in client.post("/api/bulk", headers=AUTH, files={"file": ("x.csv", big)}).json()["error"]


def test_hostile_filename_is_sanitised(client, ls):
    r = client.post("/api/bulk", headers=AUTH, files={"file": ('a"\r\nX-Evil: 1.csv', SHOPIFY_EXPORT.encode())})
    assert "x-evil" not in r.headers and '"\r\n' not in r.headers["content-disposition"]


# --- deploy guard -------------------------------------------------------------------

def test_public_host_requires_https_and_lemon_squeezy(site):
    with pytest.raises(RuntimeError):
        config.check_deployable(dataclasses.replace(site, host="0.0.0.0", site_url="http://x"))
    with pytest.raises(RuntimeError):
        config.check_deployable(dataclasses.replace(site, host="0.0.0.0", site_url="https://x", ls_store_id=""))
    config.check_deployable(dataclasses.replace(site, host="0.0.0.0", site_url="https://x"))
