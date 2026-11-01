"""Shopify's own authentication mechanisms, verified exactly as Shopify documents them.

Three callers reach this app, each with Shopify's mechanism for it:
  * OAuth install redirect   -> query-string HMAC (hex SHA-256 with the app secret)
  * Webhooks                  -> X-Shopify-Hmac-Sha256 (base64 SHA-256 of the raw body)
  * Embedded admin API calls  -> App Bridge session token (HS256 JWT signed with the app secret)

Every check is fail-closed: a missing app secret raises, and every comparison is
constant-time.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import urllib.parse

import httpx

from . import config

_SHOP_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")


class AuthError(Exception):
    pass


def _secret() -> bytes:
    return config.require(config.settings.api_secret, "SHOPIFY_API_SECRET").encode()


def valid_shop(shop: str | None) -> str | None:
    """Return the shop domain if it is a real *.myshopify.com host, else None.

    Every outbound call goes to https://{shop}/..., so an unvalidated shop
    parameter would be an SSRF and open-redirect vector.
    """
    s = (shop or "").strip().lower()
    return s if _SHOP_RE.match(s) else None


# --- OAuth -------------------------------------------------------------------

def verify_query_hmac(params: dict[str, str]) -> bool:
    given = params.get("hmac", "")
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if k not in ("hmac", "signature"))
    expected = hmac.new(_secret(), message.encode(), hashlib.sha256).hexdigest()
    return bool(given) and hmac.compare_digest(expected, given)


def authorize_url(shop: str, state: str) -> str:
    q = urllib.parse.urlencode({
        "client_id": config.require(config.settings.api_key, "SHOPIFY_API_KEY"),
        "scope": config.settings.scopes,
        "redirect_uri": f"{config.settings.app_url}/auth/callback",
        "state": state,
    })
    return f"https://{shop}/admin/oauth/authorize?{q}"


def exchange_code(shop: str, code: str) -> dict:
    r = httpx.post(
        f"https://{shop}/admin/oauth/access_token",
        json={"client_id": config.settings.api_key, "client_secret": _secret().decode(), "code": code},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()  # {"access_token": ..., "scope": ...}


# --- webhooks ----------------------------------------------------------------

def verify_webhook(raw_body: bytes, header_hmac: str | None) -> bool:
    if not header_hmac:
        return False
    digest = base64.b64encode(hmac.new(_secret(), raw_body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(digest, header_hmac)


# --- session tokens ----------------------------------------------------------

def _b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def verify_session_token(token: str, leeway: int = 5) -> str:
    """Verify an App Bridge session token and return the shop domain it is for."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        sig = _b64url_decode(sig_b64)
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("malformed session token") from exc
    if header.get("alg") != "HS256":
        raise AuthError("unexpected token algorithm")
    expected = hmac.new(_secret(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig):
        raise AuthError("bad session token signature")
    t = time.time()
    if payload.get("exp", 0) + leeway < t or payload.get("nbf", 0) - leeway > t:
        raise AuthError("session token expired or not yet valid")
    if payload.get("aud") != config.settings.api_key:
        raise AuthError("session token is for another app")
    shop = valid_shop(urllib.parse.urlparse(payload.get("dest", "")).hostname)
    iss_host = urllib.parse.urlparse(payload.get("iss", "")).hostname
    if not shop or iss_host != shop:
        raise AuthError("session token shop mismatch")
    return shop


# --- Admin GraphQL -----------------------------------------------------------

class Admin:
    def __init__(self, shop: str, access_token: str, client: httpx.Client | None = None):
        self.url = f"https://{shop}/admin/api/{config.settings.api_version}/graphql.json"
        self.token = access_token
        self.client = client or httpx.Client(timeout=15)

    def gql(self, query: str, variables: dict | None = None) -> dict:
        r = self.client.post(self.url, json={"query": query, "variables": variables or {}},
                             headers={"X-Shopify-Access-Token": self.token})
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise RuntimeError(f"Shopify GraphQL error: {body['errors']}")
        return body["data"]

    def add_tags(self, gid: str, tags: list[str]) -> None:
        data = self.gql(
            """mutation($id: ID!, $tags: [String!]!) {
                 tagsAdd(id: $id, tags: $tags) { userErrors { field message } } }""",
            {"id": gid, "tags": tags},
        )
        _raise_user_errors(data["tagsAdd"])

    def update_order(self, gid: str, *, note: str | None = None, address2: str | None = None) -> None:
        inp: dict = {"id": gid}
        if note is not None:
            inp["note"] = note
        if address2 is not None:
            inp["shippingAddress"] = {"address2": address2}
        data = self.gql(
            """mutation($input: OrderInput!) {
                 orderUpdate(input: $input) { userErrors { field message } } }""",
            {"input": inp},
        )
        _raise_user_errors(data["orderUpdate"])

    def subscribe_webhook(self, topic: str, callback_url: str) -> None:
        data = self.gql(
            """mutation($topic: WebhookSubscriptionTopic!, $url: URL!) {
                 webhookSubscriptionCreate(topic: $topic,
                   webhookSubscription: {callbackUrl: $url, format: JSON}) {
                   userErrors { field message } } }""",
            {"topic": topic, "url": callback_url},
        )
        errs = data["webhookSubscriptionCreate"]["userErrors"]
        # Re-installs hit "address already taken"; that is the desired end state.
        if errs and not all("taken" in e["message"].lower() for e in errs):
            raise RuntimeError(f"webhook {topic}: {errs}")


def _raise_user_errors(payload: dict) -> None:
    if payload.get("userErrors"):
        raise RuntimeError(f"Shopify userErrors: {payload['userErrors']}")


def order_gid(order_id: int | str) -> str:
    return f"gid://shopify/Order/{order_id}"
