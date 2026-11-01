import hashlib
import hmac

import pytest

from app import shopify
from tests.conftest import API_KEY, SECRET, SHOP, session_token, sign_webhook


def test_valid_shop_rejects_non_shopify_hosts():
    assert shopify.valid_shop("Demo-Store.myshopify.com") == "demo-store.myshopify.com"
    for bad in ("evil.com", "x.myshopify.com.evil.com", "x.myshopify.com/../", "", None,
                "a b.myshopify.com", "-x.myshopify.com"):
        assert shopify.valid_shop(bad) is None


def _signed(params):
    msg = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return {**params, "hmac": hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()}


def test_query_hmac():
    p = _signed({"shop": SHOP, "code": "abc", "state": "s", "timestamp": "1"})
    assert shopify.verify_query_hmac(p)
    assert not shopify.verify_query_hmac({**p, "code": "tampered"})
    assert not shopify.verify_query_hmac({k: v for k, v in p.items() if k != "hmac"})


def test_webhook_hmac():
    body = b'{"id": 1}'
    assert shopify.verify_webhook(body, sign_webhook(body))
    assert not shopify.verify_webhook(b'{"id": 2}', sign_webhook(body))
    assert not shopify.verify_webhook(body, None)


def test_session_token_valid():
    assert shopify.verify_session_token(session_token()) == SHOP


@pytest.mark.parametrize("token", [
    session_token(exp_in=-60),                       # expired
    session_token(aud="other-app"),                   # another app's token
    session_token(secret="wrong-secret"),             # forged
    session_token(iss_shop="other.myshopify.com"),    # iss/dest disagree
    session_token(shop="evil.com"),                   # not a Shopify host
    "not.a.jwt", "garbage",
])
def test_session_token_rejected(token):
    with pytest.raises(shopify.AuthError):
        shopify.verify_session_token(token)


def test_missing_secret_fails_closed(monkeypatch, settings):
    import dataclasses
    from app import config
    monkeypatch.setattr(config, "settings", dataclasses.replace(settings, api_secret=""))
    with pytest.raises(RuntimeError):
        shopify.verify_webhook(b"{}", "anything")


def test_api_key_is_used_as_audience():
    assert API_KEY in shopify.authorize_url(SHOP, "state123")
