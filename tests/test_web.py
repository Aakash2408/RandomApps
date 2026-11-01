import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import crypto, db, service, shopify, web
from tests.conftest import SECRET, SHOP, cod_order, session_token, sign_webhook


@pytest.fixture
def client():
    return TestClient(web.app)


def post_webhook(client, topic, payload, webhook_id="wh-1", shop=SHOP, signature=None):
    body = json.dumps(payload).encode()
    return client.post("/webhooks", content=body, headers={
        "X-Shopify-Hmac-Sha256": signature or sign_webhook(body), "X-Shopify-Topic": topic,
        "X-Shopify-Shop-Domain": shop, "X-Shopify-Webhook-Id": webhook_id,
        "Content-Type": "application/json"})


def auth_header(shop=SHOP):
    return {"Authorization": f"Bearer {session_token(shop)}"}


# --- webhooks ------------------------------------------------------------------

def test_webhook_rejects_bad_signature(client, installed_shop):
    r = post_webhook(client, "orders/create", cod_order(), signature="bogus")
    assert r.status_code == 401
    assert db.list_checks(SHOP, None) == []


def test_risky_cod_order_is_scored_tagged_and_billed(client, installed_shop, fake_admin):
    order = cod_order(address1="near temple", address2="", phone="9999999999")
    assert post_webhook(client, "orders/create", order).status_code == 200
    [check] = db.list_checks(SHOP, None)
    assert check["band"] == "high" and check["status"] == "flagged"
    assert fake_admin.tags == [("gid://shopify/Order/1001", ["CODGuard-high"])]
    assert db.usage_count(SHOP, db.month_key()) == 1
    with db.conn() as c:
        row = c.execute("SELECT token, wa_status, phone_hash FROM checks").fetchone()
    assert row["token"] and row["wa_status"] == "disabled"
    assert "9999999999" not in row["phone_hash"]


def test_clean_order_gets_no_confirmation_link(client, installed_shop, fake_admin):
    post_webhook(client, "orders/create", cod_order())
    with db.conn() as c:
        row = c.execute("SELECT band, status, token FROM checks").fetchone()
    assert (row["band"], row["status"], row["token"]) == ("low", "clear", None)


def test_duplicate_delivery_is_ignored(client, installed_shop, fake_admin):
    post_webhook(client, "orders/create", cod_order(), webhook_id="same")
    post_webhook(client, "orders/create", cod_order(), webhook_id="same")
    post_webhook(client, "orders/create", cod_order(), webhook_id="different-id-same-order")
    assert len(db.list_checks(SHOP, None)) == 1
    assert db.usage_count(SHOP, db.month_key()) == 1


def test_prepaid_and_unsubscribed_orders_are_skipped(installed_shop, fake_admin):
    prepaid = {**cod_order(2001), "payment_gateway_names": ["razorpay"]}
    assert service.handle_order_created(SHOP, prepaid) == "skipped:prepaid"
    db.set_subscription(SHOP, status="CANCELLED")
    assert service.handle_order_created(SHOP, cod_order(2002)) == "skipped:no_subscription"


def test_overage_billed_only_above_included(installed_shop, fake_admin, monkeypatch):
    from app import billing
    monkeypatch.setitem(billing.PLANS, "starter", billing.Plan("starter", "Starter", 9, 2, 0.03, 30, 799))
    for i in range(3):
        service.handle_order_created(SHOP, cod_order(3000 + i))
    usage_calls = [v for q, v in fake_admin.calls if "appUsageRecordCreate" in q]
    assert len(usage_calls) == 1 and usage_calls[0]["key"] == "gid://shopify/Order/3002"


def test_repeat_rto_phone_is_remembered(installed_shop, fake_admin):
    service.handle_order_created(SHOP, cod_order(4001))
    db.set_status_by_order(SHOP, "gid://shopify/Order/4001", "returned")
    service.handle_order_created(SHOP, cod_order(4002))
    check = [c for c in db.list_checks(SHOP, None) if c["order_name"] == "#4002"][0]
    assert any(r["code"] == "prior_rto" for r in check["reasons"])


def test_uninstall_and_shop_redact(client, installed_shop, fake_admin):
    post_webhook(client, "orders/create", cod_order(), webhook_id="a")
    post_webhook(client, "app/uninstalled", {}, webhook_id="b")
    assert db.get_shop(SHOP)["token_enc"] is None
    post_webhook(client, "shop/redact", {"shop_domain": SHOP}, webhook_id="c")
    assert db.get_shop(SHOP) is None and db.list_checks(SHOP, None) == []


def test_customer_redact_clears_personal_fields(client, installed_shop, fake_admin):
    post_webhook(client, "orders/create", cod_order(address1="near temple", address2=""), webhook_id="a")
    post_webhook(client, "customers/redact", {"orders_to_redact": [1001]}, webhook_id="b")
    with db.conn() as c:
        row = c.execute("SELECT first_name, phone_hash, address_json, token FROM checks").fetchone()
    assert tuple(row) == (None, None, None, None)


# --- embedded admin API ----------------------------------------------------------

def test_api_requires_valid_session_token(client, installed_shop):
    assert client.get("/api/summary").status_code == 401
    assert client.get("/api/summary", headers={"Authorization": "Bearer x.y.z"}).status_code == 401
    other = "other-store.myshopify.com"
    assert client.get("/api/summary", headers=auth_header(other)).status_code == 403


def test_summary_counts_savings(client, installed_shop, fake_admin):
    service.handle_order_created(SHOP, cod_order(5001, address1="near temple", address2=""))
    token = db.list_checks(SHOP, None)  # ensure stored
    with db.conn() as c:
        tok = c.execute("SELECT token FROM checks").fetchone()["token"]
    client.post(f"/c/{tok}", data={"action": "update", "landmark": "Flat 2, opp SBI ATM"})
    s = client.get("/api/summary", headers=auth_header()).json()
    assert s["summary"]["updated"] == 1
    assert s["estimated_saved_inr"] == 150
    assert token


def test_merchant_gets_confirm_link_until_used(client, installed_shop, fake_admin):
    service.handle_order_created(SHOP, cod_order(8001, address1="near temple", address2=""))
    service.handle_order_created(SHOP, cod_order(8002))  # clean -> no link
    by_name = {c["order_name"]: c for c in client.get("/api/checks", headers=auth_header()).json()["checks"]}
    url = by_name["#8001"]["confirm_url"]
    assert url.startswith("https://codguard.test/c/") and by_name["#8002"]["confirm_url"] is None
    assert "token" not in by_name["#8001"] and "phone_hash" not in by_name["#8001"]
    client.post(url.replace("https://codguard.test", ""), data={"action": "confirm"})
    after = client.get("/api/checks", headers=auth_header()).json()["checks"]
    assert all(c["confirm_url"] is None for c in after)


def test_shops_cannot_read_each_others_checks(client, installed_shop, fake_admin):
    other = "other-store.myshopify.com"
    db.upsert_shop(other, crypto.encrypt("t2"), "read_orders,write_orders")
    service.handle_order_created(SHOP, cod_order(6001))
    assert client.get("/api/checks", headers=auth_header(other)).json()["checks"] == []
    check_id = db.list_checks(SHOP, None)[0]["id"]
    r = client.post(f"/api/checks/{check_id}/outcome", json={"outcome": "returned"}, headers=auth_header(other))
    assert r.status_code == 404


def test_subscribe_and_billing_return(client, fake_admin):
    db.upsert_shop(SHOP, crypto.encrypt("shpat"), "read_orders,write_orders")
    r = client.post("/api/subscribe", json={"plan": "growth"}, headers=auth_header())
    assert r.json()["confirmation_url"].startswith("https://demo-store.myshopify.com/")
    assert db.get_shop(SHOP)["subscription_status"] == "PENDING"
    r = client.get(f"/billing/return?shop={SHOP}", follow_redirects=False)
    assert r.status_code == 307
    row = db.get_shop(SHOP)
    assert (row["plan"], row["subscription_status"], row["usage_line_gid"]) == ("growth", "ACTIVE", "gid://line/usage")


def test_settings_validation(client, installed_shop):
    assert client.post("/api/settings", json={"rto_cost": "lots"}, headers=auth_header()).status_code == 400
    assert client.post("/api/settings", json={"rto_cost": 220}, headers=auth_header()).status_code == 200
    assert db.get_shop(SHOP)["rto_cost"] == 220


# --- customer confirmation page -------------------------------------------------

def _flag_order(**addr):
    service.handle_order_created(SHOP, cod_order(7001, **addr))
    with db.conn() as c:
        return c.execute("SELECT token FROM checks").fetchone()["token"]


def test_confirm_page_escapes_customer_input(client, installed_shop, fake_admin):
    tok = _flag_order(address1="<script>alert('x')</script> near temple", address2="")
    page = client.get(f"/c/{tok}").text
    assert "Confirm your order" in page
    assert "<script>alert" not in page and "&lt;script&gt;" in page


def test_update_writes_landmark_back_and_link_is_single_use(client, installed_shop, fake_admin):
    tok = _flag_order(address1="near hanuman temple", address2="")
    r = client.post(f"/c/{tok}", data={"action": "update", "landmark": "House 14, blue gate"})
    assert r.status_code == 200 and "added your details" in r.text
    assert fake_admin.updates == [("gid://shopify/Order/7001", {"address2": "Landmark: House 14, blue gate"})]
    assert ("gid://shopify/Order/7001", ["CODGuard-address-updated"]) in fake_admin.tags
    assert client.get(f"/c/{tok}").status_code == 404
    assert client.post(f"/c/{tok}", data={"action": "confirm"}).status_code == 404


def test_update_requires_landmark_and_unknown_actions_fail(client, installed_shop, fake_admin):
    tok = _flag_order(address1="near temple", address2="")
    assert client.post(f"/c/{tok}", data={"action": "update", "landmark": "  "}).status_code == 400
    assert client.post(f"/c/{tok}", data={"action": "drop table"}).status_code == 400


def test_expired_or_unknown_tokens_404(client, installed_shop, fake_admin):
    tok = _flag_order(address1="near temple", address2="")
    with db.conn() as c:
        c.execute("UPDATE checks SET token_expires_at=1")
    assert client.get(f"/c/{tok}").status_code == 404
    assert client.get("/c/" + "x" * 32).status_code == 404


# --- OAuth -----------------------------------------------------------------------

def _signed(params):
    msg = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return {**params, "hmac": hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()}


def test_auth_rejects_bad_shop(client):
    assert client.get("/auth?shop=evil.com", follow_redirects=False).status_code == 400


def test_oauth_callback_requires_hmac_and_state(client, monkeypatch):
    calls = []
    monkeypatch.setattr(shopify, "exchange_code",
                        lambda shop, code: {"access_token": "shpat_new", "scope": "read_orders,write_orders"})
    monkeypatch.setattr(shopify.Admin, "subscribe_webhook", lambda self, t, u: calls.append(t))

    r = client.get("/auth?shop=" + SHOP, follow_redirects=False)
    state = r.headers["location"].split("state=")[1].split("&")[0]

    bad = _signed({"shop": SHOP, "code": "c", "state": state, "timestamp": "1"})
    bad["code"] = "tampered"
    assert client.get("/auth/callback", params=bad, follow_redirects=False).status_code == 401

    wrong_state = _signed({"shop": SHOP, "code": "c", "state": "forged", "timestamp": "1"})
    assert client.get("/auth/callback", params=wrong_state, follow_redirects=False).status_code == 401

    good = _signed({"shop": SHOP, "code": "c", "state": state, "timestamp": "1"})
    r = client.get("/auth/callback", params=good, follow_redirects=False)
    assert r.status_code == 307 and "admin.shopify.com/store/demo-store/apps/" in r.headers["location"]
    assert crypto.decrypt(db.get_shop(SHOP)["token_enc"]) == "shpat_new"
    assert set(calls) == set(web.WEBHOOK_TOPICS)
    # state is single-use
    assert client.get("/auth/callback", params=good, follow_redirects=False).status_code == 401


def test_embedded_page_frame_policy(client):
    r = client.get(f"/app?shop={SHOP}")
    assert r.headers["content-security-policy"] == f"frame-ancestors https://{SHOP} https://admin.shopify.com"
    assert client.get("/c/" + "x" * 32).headers["content-security-policy"] == "frame-ancestors 'none'"
