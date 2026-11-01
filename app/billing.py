"""Plans and Shopify Billing API calls.

Each plan is one AppSubscription with two line items:
  * a recurring monthly fee that includes N COD checks
  * a usage line for checks above N, billed per check up to a monthly cap
Shopify charges the merchant and pays out to the partner account, so the app
never handles card data. Prices are USD because that is what the Billing API
charges in for Indian stores; the INR figures in PLANS are only for display.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config
from .shopify import Admin


@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    monthly_usd: float
    included_checks: int
    overage_usd: float      # per check above included_checks
    overage_cap_usd: float  # max usage charge per 30-day cycle
    approx_inr: int


PLANS = {
    p.key: p for p in (
        Plan("starter", "Starter", 9.0, 300, 0.03, 30.0, 799),
        Plan("growth", "Growth", 29.0, 1500, 0.02, 60.0, 2499),
        Plan("pro", "Pro", 79.0, 6000, 0.015, 150.0, 6799),
    )
}
TRIAL_DAYS = 7
ACTIVE = "ACTIVE"


def create_subscription(admin: Admin, plan: Plan, return_url: str) -> tuple[str, str]:
    """Returns (subscription gid, confirmationUrl the merchant must approve)."""
    data = admin.gql(
        """mutation($name: String!, $returnUrl: URL!, $trialDays: Int, $test: Boolean,
                    $lineItems: [AppSubscriptionLineItemInput!]!) {
             appSubscriptionCreate(name: $name, returnUrl: $returnUrl, trialDays: $trialDays,
                                   test: $test, lineItems: $lineItems) {
               appSubscription { id }
               confirmationUrl
               userErrors { field message } } }""",
        {
            "name": f"CODGuard {plan.name}",
            "returnUrl": return_url,
            "trialDays": TRIAL_DAYS,
            "test": config.settings.billing_test,
            "lineItems": [
                {"plan": {"appRecurringPricingDetails": {
                    "price": {"amount": plan.monthly_usd, "currencyCode": "USD"},
                    "interval": "EVERY_30_DAYS"}}},
                {"plan": {"appUsagePricingDetails": {
                    "terms": f"${plan.overage_usd} per COD check above {plan.included_checks} a month",
                    "cappedAmount": {"amount": plan.overage_cap_usd, "currencyCode": "USD"}}}},
            ],
        },
    )
    out = data["appSubscriptionCreate"]
    if out["userErrors"]:
        raise RuntimeError(f"appSubscriptionCreate: {out['userErrors']}")
    return out["appSubscription"]["id"], out["confirmationUrl"]


def fetch_subscription(admin: Admin, gid: str) -> tuple[str, str | None]:
    """(status, usage line item gid) for a subscription."""
    data = admin.gql(
        """query($id: ID!) { node(id: $id) { ... on AppSubscription {
             status
             lineItems { id plan { pricingDetails { __typename } } } } } }""",
        {"id": gid},
    )
    node = data["node"] or {}
    usage = next((li["id"] for li in node.get("lineItems", [])
                  if li["plan"]["pricingDetails"]["__typename"] == "AppUsagePricing"), None)
    return node.get("status", "UNKNOWN"), usage


def record_overage(admin: Admin, usage_line_gid: str, plan: Plan, order_name: str, order_gid: str) -> None:
    # The idempotency key is the order, so a retried webhook never bills twice.
    data = admin.gql(
        """mutation($id: ID!, $price: MoneyInput!, $desc: String!, $key: String) {
             appUsageRecordCreate(subscriptionLineItemId: $id, price: $price,
                                  description: $desc, idempotencyKey: $key) {
               userErrors { field message } } }""",
        {"id": usage_line_gid, "price": {"amount": plan.overage_usd, "currencyCode": "USD"},
         "desc": f"COD check {order_name}", "key": order_gid[-255:]},
    )
    if data["appUsageRecordCreate"]["userErrors"]:
        raise RuntimeError(f"appUsageRecordCreate: {data['appUsageRecordCreate']['userErrors']}")
