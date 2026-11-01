"""WhatsApp confirmation messages via Meta's WhatsApp Cloud API.

Business-initiated WhatsApp messages must use a template Meta has approved, so
this sends a template with three body parameters:
    {{1}} customer first name   {{2}} order name   {{3}} confirmation link
Until WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TEMPLATE are all set,
sending is disabled and every call returns "disabled" -- the order is still
tagged, so the merchant can call the customer instead.
"""
from __future__ import annotations

import logging

import httpx

from . import config

log = logging.getLogger("codguard.whatsapp")
GRAPH = "https://graph.facebook.com/v21.0"


def enabled() -> bool:
    s = config.settings
    return bool(s.wa_token and s.wa_phone_number_id and s.wa_template)


def send_confirmation(phone10: str, first_name: str, order_name: str, link: str,
                      client: httpx.Client | None = None) -> str:
    """Returns 'sent', 'disabled', 'no_phone' or 'failed'. Never raises."""
    if not enabled():
        return "disabled"
    if len(phone10) != 10:
        return "no_phone"
    s = config.settings
    body = {
        "messaging_product": "whatsapp",
        "to": f"91{phone10}",
        "type": "template",
        "template": {
            "name": s.wa_template,
            "language": {"code": s.wa_template_lang},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": first_name or "there"},
                {"type": "text", "text": order_name},
                {"type": "text", "text": link},
            ]}],
        },
    }
    try:
        c = client or httpx.Client(timeout=10)
        r = c.post(f"{GRAPH}/{s.wa_phone_number_id}/messages", json=body,
                   headers={"Authorization": f"Bearer {s.wa_token}"})
        if r.status_code >= 300:
            log.warning("whatsapp send failed for %s: %s %s", order_name, r.status_code, r.text[:300])
            return "failed"
        return "sent"
    except httpx.HTTPError as exc:
        log.warning("whatsapp send failed for %s: %s", order_name, exc)
        return "failed"
