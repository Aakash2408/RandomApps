"""Business logic: what happens when a COD order arrives or a customer responds."""
from __future__ import annotations

import json
import logging
import re
import secrets

from . import billing, config, crypto, db, notifier, scorer
from .shopify import Admin, order_gid

log = logging.getLogger("codguard.service")

TAG_PREFIX = "CODGuard"
_COD_RE = re.compile(r"cash on delivery|\bcod\b")


def is_cod(order: dict) -> bool:
    gateways = [g.lower() for g in order.get("payment_gateway_names") or []]
    gateways.append((order.get("gateway") or "").lower())
    return any(_COD_RE.search(g) for g in gateways if g)


def admin_for(shop_row) -> Admin | None:
    if not shop_row or not shop_row["token_enc"]:
        return None
    return Admin(shop_row["shop"], crypto.decrypt(shop_row["token_enc"]))


def subscription_active(shop_row) -> bool:
    return bool(shop_row) and shop_row["subscription_status"] == billing.ACTIVE \
        and shop_row["plan"] in billing.PLANS


def confirm_link(token: str) -> str:
    return f"{config.settings.app_url}/c/{token}"


def handle_order_created(shop: str, order: dict, admin: Admin | None = None) -> str:
    """Score a new order. Returns a short outcome string (used by tests and logs)."""
    shop_row = db.get_shop(shop)
    if not subscription_active(shop_row):
        return "skipped:no_subscription"
    if not is_cod(order):
        return "skipped:prepaid"
    address = order.get("shipping_address") or {}
    if not address:
        return "skipped:no_shipping_address"
    admin = admin or admin_for(shop_row)
    if admin is None:
        return "skipped:no_token"

    gid = order.get("admin_graphql_api_id") or order_gid(order["id"])
    phone10 = scorer.normalize_phone(address.get("phone") or order.get("phone"))
    phash = crypto.phone_hash(shop, phone10)
    prior_rto, burst = db.history_for(shop, phash, gid)
    total = float(order.get("total_price") or 0)
    result = scorer.score({**address, "phone": address.get("phone") or order.get("phone")},
                          order_total=total, history=scorer.History(prior_rto, burst))

    needs_confirm = result.band != "low"
    token = secrets.token_urlsafe(24) if needs_confirm else None
    check_id = db.insert_check(
        shop=shop, order_gid=gid, order_name=order.get("name") or str(order.get("id")),
        first_name=(address.get("first_name") or "")[:40], phone_hash=phash,
        risk=result.risk, band=result.band, reasons_json=json.dumps(result.to_dict()["reasons"]),
        address_json=json.dumps({k: address.get(k) for k in ("address1", "address2", "city", "province", "zip")}),
        total=total, status="flagged" if needs_confirm else "clear", token=token,
        token_expires_at=db.now() + config.settings.confirm_ttl_days * 86400 if token else None,
    )
    if check_id is None:
        return "skipped:duplicate"

    _bill(shop_row, admin, order.get("name") or gid, gid)

    try:
        admin.add_tags(gid, [f"{TAG_PREFIX}-{result.band}"])
    except Exception:  # tagging is best effort; the check itself is already stored
        log.exception("tagging failed for %s %s", shop, gid)

    if needs_confirm:
        wa = notifier.send_confirmation(phone10, address.get("first_name") or "",
                                        order.get("name") or "", confirm_link(token))
        db.update_check(check_id, wa_status=wa)
    return f"scored:{result.band}"


def _bill(shop_row, admin: Admin, order_name: str, gid: str) -> None:
    plan = billing.PLANS[shop_row["plan"]]
    count = db.bump_usage(shop_row["shop"], db.month_key())
    if count <= plan.included_checks:
        return
    if not shop_row["usage_line_gid"]:
        log.error("shop %s is over its included checks but has no usage line item", shop_row["shop"])
        return
    try:
        billing.record_overage(admin, shop_row["usage_line_gid"], plan, order_name, gid)
    except Exception:
        # Most likely the merchant's usage cap is reached. Keep checking; do not drop protection.
        log.exception("overage charge failed for %s", shop_row["shop"])


# --- customer responses -------------------------------------------------------

ACTIONS = ("confirm", "update", "cancel")


def customer_response(check, action: str, landmark: str = "", admin: Admin | None = None) -> str:
    if action not in ACTIONS:
        raise ValueError("unknown action")
    admin = admin or admin_for(db.get_shop(check["shop"]))
    landmark = " ".join(landmark.split())[:120]
    if action == "update" and not landmark:
        raise ValueError("landmark required")

    status = {"confirm": "confirmed", "update": "updated", "cancel": "cancel_requested"}[action]
    tag = {"confirm": "confirmed", "update": "address-updated", "cancel": "cancel-requested"}[action]
    db.update_check(check["id"], status=status, token=None)  # link is single-use

    if admin is None:
        return status
    try:
        admin.add_tags(check["order_gid"], [f"{TAG_PREFIX}-{tag}"])
        if action == "update":
            addr = json.loads(check["address_json"] or "{}")
            new2 = " ".join(filter(None, [addr.get("address2"), f"Landmark: {landmark}"]))
            admin.update_order(check["order_gid"], address2=new2[:255])
    except Exception:
        log.exception("could not write customer response back to %s", check["order_gid"])
    return status
