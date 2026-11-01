import base64
import hashlib
import hmac
import json
import time

import pytest
from cryptography.fernet import Fernet

from app import config, crypto, db

SECRET = "test-app-secret"
API_KEY = "test-api-key"
SHOP = "demo-store.myshopify.com"


@pytest.fixture(autouse=True)
def settings(tmp_path, monkeypatch):
    s = config.Settings(
        api_key=API_KEY, api_secret=SECRET, app_url="https://codguard.test",
        db_path=str(tmp_path / "t.sqlite3"), token_key=Fernet.generate_key().decode(),
        phone_pepper="pepper", billing_test=True, wa_token="", wa_phone_number_id="", wa_template="",
    )
    monkeypatch.setattr(config, "settings", s)
    db.init()
    return s


class FakeAdmin:
    def __init__(self):
        self.tags, self.updates, self.calls = [], [], []

    def add_tags(self, gid, tags):
        self.tags.append((gid, tags))

    def update_order(self, gid, **kw):
        self.updates.append((gid, kw))

    def gql(self, query, variables=None):
        self.calls.append((query, variables))
        if "appUsageRecordCreate" in query:
            return {"appUsageRecordCreate": {"userErrors": []}}
        if "appSubscriptionCreate" in query:
            return {"appSubscriptionCreate": {"appSubscription": {"id": "gid://shopify/AppSubscription/1"},
                                              "confirmationUrl": "https://demo-store.myshopify.com/confirm",
                                              "userErrors": []}}
        if "node(id" in query:
            return {"node": {"status": "ACTIVE", "lineItems": [
                {"id": "gid://line/rec", "plan": {"pricingDetails": {"__typename": "AppRecurringPricing"}}},
                {"id": "gid://line/usage", "plan": {"pricingDetails": {"__typename": "AppUsagePricing"}}}]}}
        raise AssertionError(f"unexpected query {query}")


@pytest.fixture
def fake_admin(monkeypatch):
    from app import service
    fa = FakeAdmin()
    monkeypatch.setattr(service, "admin_for", lambda row: fa if row and row["token_enc"] else None)
    return fa


@pytest.fixture
def installed_shop():
    db.upsert_shop(SHOP, crypto.encrypt("shpat_test"), "read_orders,write_orders")
    db.set_subscription(SHOP, plan="starter", gid="gid://shopify/AppSubscription/1",
                        status="ACTIVE", usage_line_gid="gid://line/usage")
    return SHOP


def sign_webhook(body: bytes) -> str:
    return base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def session_token(shop=SHOP, aud=API_KEY, exp_in=60, secret=SECRET, iss_shop=None) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "iss": f"https://{iss_shop or shop}/admin", "dest": f"https://{shop}", "aud": aud,
        "sub": "1", "exp": now + exp_in, "nbf": now - 1, "iat": now - 1, "jti": "x",
    }).encode())
    sig = b64url(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def cod_order(order_id=1001, **addr):
    address = {"first_name": "Priya", "last_name": "Sharma", "name": "Priya Sharma",
               "address1": "Flat 302, Sunrise Apartments, 14th Main Road",
               "address2": "HSR Layout Sector 2", "city": "Bengaluru",
               "province": "Karnataka", "province_code": "KA", "zip": "560102",
               "phone": "+91 98450 12345"}
    address.update(addr)
    return {"id": order_id, "admin_graphql_api_id": f"gid://shopify/Order/{order_id}",
            "name": f"#{order_id}", "total_price": "1499.00",
            "payment_gateway_names": ["Cash on Delivery (COD)"], "shipping_address": address}
