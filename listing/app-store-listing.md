# CODGuard — Shopify App Store listing

Character limits below are the ones I understand the Partner Dashboard enforces;
the form itself is authoritative — re-check each field when pasting.

Shopify's listing rules to keep in mind while editing: no unverifiable outcome
claims ("cut RTO by 40%"), no "best"/"#1", no competitor names, no contact
details or pricing inside the description (pricing has its own section), and
screenshots must show the real app UI.

---

## App name (max 30)

CODGuard: COD Address Check

## App card subtitle (max 62)

Catch bad COD addresses before you ship, and confirm on WhatsApp

## App introduction (max 100)

Score every cash-on-delivery order's address, flag risky ones, and let shoppers fix them before dispatch.

## App details (max 500)

Every COD order that comes back undelivered costs you shipping both ways. Most of
those returns start with an address the courier can't find: no door number, only
a landmark, a PIN code that doesn't match the state, or a fake phone number.

CODGuard checks each new COD order the moment it's placed, tags it low, medium or
high risk with plain-English reasons, and sends risky customers a link to confirm
their order or add a landmark. Their fix is written straight into the order.

## Feature list (up to 5, max 80 each)

1. Checks every new COD order automatically. Prepaid orders are skipped.
2. Explains each flag: bad PIN, missing door number, fake phone and more
3. Customers confirm or add a landmark through a one-tap link
4. Tags orders in Shopify so your team can filter and act fast
5. Dashboard shows flagged orders and estimated return costs avoided

## Pricing plans

All plans include a 7-day free trial. Billed by Shopify every 30 days.

| Plan | Price | Includes | Above the included checks |
|---|---|---|---|
| Starter | $9/month | 300 COD order checks | $0.03 per check, capped at $30 |
| Growth | $29/month | 1,500 COD order checks | $0.02 per check, capped at $60 |
| Pro | $79/month | 6,000 COD order checks | $0.015 per check, capped at $150 |

Plan descriptions (one line each, shown under the plan):
- Starter: For new stores shipping up to about 10 COD orders a day.
- Growth: For growing stores shipping up to about 50 COD orders a day.
- Pro: For high-volume stores shipping up to about 200 COD orders a day.

## Search terms (up to 5)

cod verification, rto reduction, address validation, cash on delivery, order confirmation

## Categories

Primary: Orders and shipping › Order management (or the closest current equivalent)
Secondary: Store management › Fraud prevention

## Screenshots (1600×900) — captions and alt text

1. Dashboard
   - Caption: See this month's checks, high-risk orders and estimated savings at a glance.
   - Alt: CODGuard dashboard with cards for estimated savings, orders checked, high-risk orders and customer fixes.
2. Flagged order with reasons
   - Caption: Every flag comes with a reason your team can act on.
   - Alt: Table of recent COD orders showing risk score, band and reasons such as "No house, flat or plot number".
3. Customer confirmation page (mobile)
   - Caption: Shoppers confirm or add a landmark in one tap, with no login.
   - Alt: Mobile page asking the customer to confirm their address or add a house number or landmark.
4. Order tags in Shopify admin
   - Caption: Risk tags land on the order, so you can filter before you fulfil.
   - Alt: Shopify order list filtered by the CODGuard-high tag.

## Demo store URL

(Fill in after the dev store is set up: https://<your-dev-store>.myshopify.com)

## Privacy and data (for the listing's data section and the review form)

- Reads: order number, total, payment method, shipping address, customer first name and phone (to score the address).
- Stores: the risk score and reasons, a copy of the shipping address for the confirmation page, and a keyed hash of the phone number (never the number itself) to recognise repeat returns.
- Shares: if you turn on WhatsApp confirmations, the customer's phone number and order number are sent to Meta's WhatsApp Cloud API to deliver the message.
- Deletion: honours Shopify's customer redact and shop redact requests. Uninstalling stops all processing immediately.

## Review notes for the Shopify app reviewer

To test:
1. Install on the review store and start any plan (test charges are on during review).
2. Place an order using the "Cash on Delivery (COD)" manual payment method with
   address line 1 "near temple", no address line 2, PIN 560102, state Karnataka.
3. Within a few seconds the order is tagged CODGuard-medium and appears in the
   app dashboard with its reasons.
4. In the app dashboard, click "Copy confirm link" on that order, open the link,
   add "House 12" as a landmark and save. The order's address line 2 updates and
   the link stops working (it is single-use).
WhatsApp sending is optional and disabled on the review store; flagged orders are still tagged.
