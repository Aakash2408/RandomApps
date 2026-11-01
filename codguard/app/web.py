"""HTTP surface.

Who can call what:
  /auth, /auth/callback      Shopify OAuth. Callback is HMAC- and state-verified.
  /webhooks                  Shopify only. Raw-body HMAC verified before parsing.
  /api/*                     Embedded admin only. App Bridge session token required.
  /billing/return            Merchant browser after approving a charge. Trusts nothing
                             from the query: status is read back from Shopify.
  /c/{token}                 The shopper. Public by design; the 32-char random
                             token in the URL is the capability, single-use, expiring.
  /, /app, /healthz          Static shells with no store data in them.
"""
from __future__ import annotations

import html
import json
import logging
import secrets
import urllib.parse
from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from . import billing, config, crypto, db, service, shopify

@asynccontextmanager
async def _lifespan(_app):
    db.init()
    yield


log = logging.getLogger("codguard.web")
app = FastAPI(title="CODGuard", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan)

WEBHOOK_TOPICS = ("ORDERS_CREATE", "ORDERS_CANCELLED", "APP_UNINSTALLED", "APP_SUBSCRIPTIONS_UPDATE")


@app.middleware("http")
async def _headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
    return resp


@app.get("/healthz")
def healthz():
    return {"ok": True}


# --- install / OAuth -----------------------------------------------------------

@app.get("/")
def index(shop: str | None = None, host: str | None = None):
    s = shopify.valid_shop(shop)
    if not s:
        return HTMLResponse(_page("CODGuard", "<p>Install CODGuard from the Shopify App Store.</p>"))
    row = db.get_shop(s)
    if not row or not row["token_enc"]:
        return RedirectResponse(f"/auth?shop={s}")
    return RedirectResponse(f"/app?shop={s}" + (f"&host={urllib.parse.quote(host, safe='')}" if host else ""))


@app.get("/auth")
def auth(shop: str):
    s = shopify.valid_shop(shop)
    if not s:
        raise HTTPException(400, "invalid shop domain")
    state = secrets.token_urlsafe(24)
    db.save_state(state, s)
    return RedirectResponse(shopify.authorize_url(s, state))


@app.get("/auth/callback")
def auth_callback(request: Request):
    params = dict(request.query_params)
    shop = shopify.valid_shop(params.get("shop"))
    if not shop or not shopify.verify_query_hmac(params):
        raise HTTPException(401, "invalid OAuth callback signature")
    if not db.pop_state(params.get("state", ""), shop):
        raise HTTPException(401, "invalid or expired OAuth state")
    token = shopify.exchange_code(shop, params.get("code", ""))
    granted = set(token.get("scope", "").split(","))
    wanted = set(config.settings.scopes.split(","))
    if not wanted <= granted:
        raise HTTPException(403, f"missing scopes: {sorted(wanted - granted)}")
    db.upsert_shop(shop, crypto.encrypt(token["access_token"]), token.get("scope", ""))
    admin = shopify.Admin(shop, token["access_token"])
    for topic in WEBHOOK_TOPICS:
        admin.subscribe_webhook(topic, f"{config.settings.app_url}/webhooks")
    return RedirectResponse(_admin_app_url(shop))


def _admin_app_url(shop: str) -> str:
    return f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/{config.settings.api_key}"


# --- embedded admin ------------------------------------------------------------

def current_shop(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "session token required")
    try:
        shop = shopify.verify_session_token(authorization[7:])
    except shopify.AuthError as exc:
        raise HTTPException(401, str(exc))
    row = db.get_shop(shop)
    if not row or not row["token_enc"]:
        raise HTTPException(403, "app not installed for this shop")
    return shop


@app.get("/app")
def embedded_app(shop: str):
    s = shopify.valid_shop(shop)
    if not s:
        raise HTTPException(400, "invalid shop domain")
    resp = HTMLResponse(ADMIN_HTML.replace("__API_KEY__", html.escape(config.settings.api_key)))
    # Shopify requires embedded apps to allow framing by the shop admin only.
    resp.headers["Content-Security-Policy"] = f"frame-ancestors https://{s} https://admin.shopify.com"
    return resp


@app.get("/api/summary")
def api_summary(shop: str = Depends(current_shop)):
    row = db.get_shop(shop)
    month = db.month_key()
    s = db.month_summary(shop, month)
    plan = billing.PLANS.get(row["plan"] or "")
    # Each high-risk order the customer fixed or cancelled before dispatch is one
    # failed delivery avoided, at the merchant's own two-way shipping cost.
    avoided = s["updated"] + s["cancel_requested"]
    return {
        "month": month,
        "plan": plan.__dict__ if plan else None,
        "subscription_status": row["subscription_status"],
        "used": db.usage_count(shop, month),
        "summary": s,
        "rto_cost": row["rto_cost"],
        "estimated_saved_inr": avoided * row["rto_cost"],
        "whatsapp_enabled": service.notifier.enabled(),
        "plans": [p.__dict__ for p in billing.PLANS.values()],
    }


@app.get("/api/checks")
def api_checks(band: str | None = None, shop: str = Depends(current_shop)):
    if band not in (None, "low", "medium", "high"):
        raise HTTPException(400, "band must be low, medium or high")
    checks = db.list_checks(shop, band)
    for c in checks:
        tok = c.pop("confirm_token")
        c["confirm_url"] = service.confirm_link(tok) if tok else None
    return {"checks": checks}


@app.post("/api/checks/{check_id}/outcome")
async def api_outcome(check_id: int, request: Request, shop: str = Depends(current_shop)):
    outcome = (await request.json()).get("outcome")
    if outcome not in ("delivered", "returned"):
        raise HTTPException(400, "outcome must be delivered or returned")
    if not db.get_check(shop, check_id):
        raise HTTPException(404, "no such check")
    db.update_check(check_id, status=outcome)
    return {"ok": True}


@app.post("/api/settings")
async def api_settings(request: Request, shop: str = Depends(current_shop)):
    cost = (await request.json()).get("rto_cost")
    if not isinstance(cost, int) or not 0 <= cost <= 5000:
        raise HTTPException(400, "rto_cost must be an integer between 0 and 5000")
    db.set_rto_cost(shop, cost)
    return {"ok": True}


@app.post("/api/subscribe")
async def api_subscribe(request: Request, shop: str = Depends(current_shop)):
    plan = billing.PLANS.get((await request.json()).get("plan", ""))
    if not plan:
        raise HTTPException(400, "unknown plan")
    admin = service.admin_for(db.get_shop(shop))
    gid, confirmation_url = billing.create_subscription(
        admin, plan, f"{config.settings.app_url}/billing/return?shop={shop}")
    db.set_subscription(shop, plan=plan.key, gid=gid, status="PENDING")
    return {"confirmation_url": confirmation_url}


@app.get("/billing/return")
def billing_return(shop: str):
    s = shopify.valid_shop(shop)
    row = db.get_shop(s) if s else None
    if not row or not row["subscription_gid"]:
        raise HTTPException(400, "no pending subscription")
    status, usage_line = billing.fetch_subscription(service.admin_for(row), row["subscription_gid"])
    db.set_subscription(s, status=status, usage_line_gid=usage_line)
    return RedirectResponse(_admin_app_url(s))


# --- webhooks ------------------------------------------------------------------

@app.post("/webhooks")
async def webhooks(request: Request, background: BackgroundTasks,
                   x_shopify_hmac_sha256: str | None = Header(default=None),
                   x_shopify_topic: str = Header(default=""),
                   x_shopify_shop_domain: str = Header(default=""),
                   x_shopify_webhook_id: str = Header(default="")):
    raw = await request.body()
    if not shopify.verify_webhook(raw, x_shopify_hmac_sha256):
        raise HTTPException(401, "invalid webhook signature")
    shop = shopify.valid_shop(x_shopify_shop_domain)
    if not shop:
        raise HTTPException(400, "invalid shop domain")
    if not db.first_delivery(x_shopify_webhook_id):
        return Response(status_code=200)
    payload = json.loads(raw or b"{}")
    topic = x_shopify_topic.lower()

    if topic == "orders/create":
        # Shopify wants a response within 5s; scoring + Admin API calls run after it.
        background.add_task(_safe_order_created, shop, payload)
    elif topic == "orders/cancelled":
        gid = payload.get("admin_graphql_api_id") or shopify.order_gid(payload.get("id"))
        check = _check_for_order(shop, gid)
        if check and check["status"] in ("flagged", "clear"):
            db.update_check(check["id"], status="cancelled")
    elif topic == "app/uninstalled":
        db.mark_uninstalled(shop)
    elif topic == "app_subscriptions/update":
        sub = payload.get("app_subscription") or {}
        row = db.get_shop(shop)
        if row and sub.get("admin_graphql_api_id") == row["subscription_gid"]:
            db.set_subscription(shop, status=sub.get("status", "").upper())
    elif topic == "customers/data_request":
        # We hold no customer data beyond what is already in the merchant's order
        # (a keyed phone hash and a copy of the shipping address). Logged for audit.
        log.info("customers/data_request for %s: %s", shop, payload.get("orders_requested"))
    elif topic == "customers/redact":
        ids = [shopify.order_gid(i) for i in payload.get("orders_to_redact") or []]
        db.redact_orders(shop, ids)
    elif topic == "shop/redact":
        db.delete_shop_data(shop)
    return Response(status_code=200)


def _safe_order_created(shop: str, order: dict) -> None:
    try:
        log.info("order %s on %s -> %s", order.get("name"), shop, service.handle_order_created(shop, order))
    except Exception:
        log.exception("failed to process order %s on %s", order.get("id"), shop)


def _check_for_order(shop: str, gid: str):
    with db.conn() as c:
        return c.execute("SELECT * FROM checks WHERE shop=? AND order_gid=?", (shop, gid)).fetchone()


# --- shopper confirmation page -------------------------------------------------

def _live_check(token: str):
    check = db.get_check_by_token(token) if 20 <= len(token) <= 64 else None
    if not check or (check["token_expires_at"] or 0) < db.now():
        return None
    return check


@app.get("/c/{token}")
def confirm_page(token: str):
    check = _live_check(token)
    if not check:
        return HTMLResponse(_page("Link expired", "<p>This link has expired or was already used.</p>"), 404)
    addr = json.loads(check["address_json"] or "{}")
    asks = [r.get("ask") for r in json.loads(check["reasons_json"]) if r.get("ask")]
    e = html.escape
    lines = ", ".join(e(str(addr.get(k))) for k in ("address1", "address2", "city", "province", "zip") if addr.get(k))
    ask_html = "".join(f"<li>{e(a)}</li>" for a in dict.fromkeys(asks))
    body = f"""
      <p>Hi {e(check['first_name'] or 'there')}, please confirm your cash-on-delivery order
         <strong>{e(check['order_name'] or '')}</strong> so the courier can find you.</p>
      <p class="addr">{lines}</p>
      {f'<p>To help the courier:</p><ul>{ask_html}</ul>' if ask_html else ''}
      <form method="post">
        <button name="action" value="confirm">Yes, this address is correct</button>
      </form>
      <form method="post">
        <label for="landmark">Add a house number or landmark</label>
        <input id="landmark" name="landmark" maxlength="120" required
               placeholder="e.g. Flat 302, opposite SBI ATM">
        <button name="action" value="update">Save and confirm</button>
      </form>
      <form method="post">
        <button class="secondary" name="action" value="cancel">Cancel this order</button>
      </form>"""
    return HTMLResponse(_page("Confirm your order", body))


@app.post("/c/{token}")
def confirm_submit(token: str, action: str = Form(...), landmark: str = Form("")):
    check = _live_check(token)
    if not check:
        return HTMLResponse(_page("Link expired", "<p>This link has expired or was already used.</p>"), 404)
    try:
        status = service.customer_response(check, action, landmark)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    msg = {"confirmed": "Thanks! Your order is confirmed.",
           "updated": "Thanks! We've added your details for the courier.",
           "cancel_requested": "Your cancellation request has been sent to the store."}[status]
    return HTMLResponse(_page("Done", f"<p>{msg}</p>"))


# --- HTML ----------------------------------------------------------------------

def _page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:32rem;margin:2rem auto;padding:0 1rem;color:#1a1a1a;background:#fff;line-height:1.5}}
 .addr{{background:#f4f4f4;color:#1a1a1a;padding:.75rem;border-radius:6px}}
 form{{margin:1rem 0}} label{{display:block;font-weight:600;margin-bottom:.25rem}}
 input{{width:100%;box-sizing:border-box;padding:.6rem;font-size:1rem;margin-bottom:.5rem;border:1px solid #767676;border-radius:6px}}
 button{{width:100%;padding:.75rem;font-size:1rem;border:0;border-radius:6px;background:#0b5cad;color:#fff;cursor:pointer}}
 button.secondary{{background:#fff;color:#a4232a;border:1px solid #a4232a}}
 button:focus-visible,input:focus-visible{{outline:3px solid #f2a900;outline-offset:2px}}
</style></head><body><main><h1>{html.escape(title)}</h1>{body}</main></body></html>"""


ADMIN_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="shopify-api-key" content="__API_KEY__">
<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
<title>CODGuard</title>
<style>
 body{font-family:system-ui,sans-serif;margin:1.5rem;color:#1a1a1a;background:#fff}
 .cards{display:flex;gap:1rem;flex-wrap:wrap} .card{border:1px solid #ddd;border-radius:8px;padding:1rem;min-width:10rem;background:#fff;color:#1a1a1a}
 .big{font-size:1.75rem;font-weight:700} table{border-collapse:collapse;width:100%;margin-top:1rem}
 th,td{text-align:left;padding:.4rem;border-bottom:1px solid #eee;vertical-align:top}
 .high{color:#a4232a;font-weight:600}.medium{color:#8a5a00;font-weight:600}.low{color:#1f6f3f}
 button{padding:.5rem .9rem;border-radius:6px;border:1px solid #0b5cad;background:#0b5cad;color:#fff;cursor:pointer}
 button:focus-visible{outline:3px solid #f2a900;outline-offset:2px}
</style></head><body>
<h1>CODGuard</h1>
<div id="plans" hidden><h2>Choose a plan (7-day free trial)</h2><div class="cards" id="plan-cards"></div></div>
<section id="main" hidden aria-live="polite">
 <div class="cards">
  <div class="card"><div>Saved this month (est.)</div><div class="big" id="saved"></div></div>
  <div class="card"><div>COD orders checked</div><div class="big" id="checked"></div><div id="quota"></div></div>
  <div class="card"><div>High risk</div><div class="big high" id="high"></div></div>
  <div class="card"><div>Fixed or cancelled by customer</div><div class="big" id="fixed"></div></div>
 </div>
 <p id="wa"></p>
 <h2>Recent COD orders</h2>
 <table><thead><tr><th scope="col">Order</th><th scope="col">Risk</th><th scope="col">Why</th><th scope="col">Status</th><th scope="col">Outcome</th></tr></thead><tbody id="rows"></tbody></table>
</section>
<script>
async function api(path, opts={}) {
  const token = await shopify.idToken();
  const r = await fetch(path, {...opts, headers: {"Authorization": "Bearer " + token, "Content-Type": "application/json"}});
  if (!r.ok) throw new Error(path + " " + r.status);
  return r.json();
}
function el(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
async function subscribe(plan) {
  const r = await api("/api/subscribe", {method: "POST", body: JSON.stringify({plan})});
  window.open(r.confirmation_url, "_top");
}
async function outcome(id, value) {
  await api(`/api/checks/${id}/outcome`, {method: "POST", body: JSON.stringify({outcome: value})});
  load();
}
async function load() {
  const s = await api("/api/summary");
  if (s.subscription_status !== "ACTIVE") {
    const cards = document.getElementById("plan-cards"); cards.replaceChildren();
    for (const p of s.plans) {
      const c = el("div", undefined, "card");
      c.append(el("h3", p.name), el("div", `$${p.monthly_usd}/month (about Rs ${p.approx_inr})`),
               el("div", `${p.included_checks} COD checks included, then $${p.overage_usd} each`));
      const b = el("button", `Start ${p.name} trial`); b.onclick = () => subscribe(p.key); c.append(b);
      cards.append(c);
    }
    document.getElementById("plans").hidden = false; return;
  }
  document.getElementById("main").hidden = false;
  document.getElementById("saved").textContent = "Rs " + s.estimated_saved_inr.toLocaleString("en-IN");
  document.getElementById("checked").textContent = s.summary.checked;
  document.getElementById("quota").textContent = `${s.used} of ${s.plan.included_checks} included`;
  document.getElementById("high").textContent = s.summary.high;
  document.getElementById("fixed").textContent = s.summary.updated + s.summary.cancel_requested;
  document.getElementById("wa").textContent = s.whatsapp_enabled ? "" :
    "WhatsApp confirmations are off. Use \\"Copy confirm link\\" on a flagged order to send it from your own WhatsApp or SMS.";
  const rows = document.getElementById("rows"); rows.replaceChildren();
  for (const c of (await api("/api/checks")).checks) {
    const tr = el("tr");
    const why = c.reasons.map(r => r.message).join(" ");
    const act = el("td");
    if (c.confirm_url) {
      const cp = el("button", "Copy confirm link");
      cp.onclick = async () => { await navigator.clipboard.writeText(c.confirm_url); cp.textContent = "Copied"; };
      act.append(cp, " ");
    }
    for (const v of ["delivered", "returned"]) { const b = el("button", v); b.onclick = () => outcome(c.id, v); act.append(b, " "); }
    tr.append(el("td", c.order_name), el("td", `${c.risk} ${c.band}`, c.band), el("td", why || "-"), el("td", c.status), act);
    rows.append(tr);
  }
}
load().catch(e => { document.body.append(el("p", "Could not load: " + e.message)); });
</script></body></html>"""
