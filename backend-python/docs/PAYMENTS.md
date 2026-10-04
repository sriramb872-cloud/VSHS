# Payments — Razorpay (UPI only, India / INR)

One implementation, two providers behind the same interface
(`app/services/payment_providers/`):

| Provider | `PAYMENT_PROVIDER` | Used for |
|---|---|---|
| `MockPaymentProvider` | `INTERNAL` | development only — **hard-disabled when `ENVIRONMENT=production`** |
| `RazorpayProvider`  | `RAZORPAY`  | real one-time prepaid **UPI** payments |

Both flow through `PaymentService` and the *same* payment row; the frontend
only ever branches on `MePlans.payment_provider`.

## Why ORDERS (not Subscriptions)

Our plans are fixed-duration rows and access is granted by
`SubscriptionService.apply_entitlement`. Razorpay is therefore used only to
move money for **exactly the price stored on the plan row**: an ORDER is
created for that amount, and when it is verified we extend access ourselves.
Razorpay's Subscriptions API would introduce a second source of truth for
"what the customer owes" (proration, cancellations) — deliberately avoided.

## Environment variables

Set these in the backend environment (Railway → Variables). Names only live
in `.env.example`; **never commit real values**.

| Variable | Required when | Meaning |
|---|---|---|
| `PAYMENT_PROVIDER` | always | `INTERNAL` (default) or `RAZORPAY` |
| `RAZORPAY_KEY_ID` | `RAZORPAY` | publishable key `rzp_test_...` / `rzp_live_...` — the only payment value that may reach the browser |
| `RAZORPAY_KEY_SECRET` | `RAZORPAY` | server-side secret; signs/verifies the checkout callback |
| `RAZORPAY_WEBHOOK_SECRET` | `RAZORPAY` | webhook secret; HMAC key over the raw request body |

Startup check (`validate_payment_settings`, runs at import):
`ENVIRONMENT=production` **and** `PAYMENT_PROVIDER=RAZORPAY` → the app refuses
to start unless all three `RAZORPAY_*` values exist. Only the missing
**names** are printed, never a value.

## Razorpay dashboard setup

1. **API keys** — Dashboard → *Settings → API Keys*. Create a **Test mode**
   key pair first; swap to Live keys only after the checklist below passes.
2. **Webhook** — Dashboard → *Settings → Webhooks → + Add New Webhook*:
   * URL: `https://<your-railway-domain>/api/v1/subscriptions/webhooks/razorpay`
     (note the **plural** `subscriptions` — this endpoint is deliberately on
     its own router, unauthenticated and rate-limit exempt; authenticity comes
     from the signature, not a session)
   * Secret: any long random string — this is `RAZORPAY_WEBHOOK_SECRET`
   * Active events: **`payment.captured`** and **`payment.failed`**
3. **UPI only** — Dashboard → *Settings → Payment Methods*: disable every
   instrument except **UPI** (cards, netbanking, wallets, EMI, pay-later,
   cardless). The API rejects a non-UPI payment anyway (`method != "upi"` →
   `PAYMENT_VERIFICATION_FAILED`), and Checkout.js is opened with UPI as the
   only instrument — this setting makes the dashboard consistent with both.

## Frontend

* `checkout.razorpay.com/v1/checkout.js` is lazy-loaded the first time a user
  opens a checkout (`src/utils/razorpayCheckout.ts`) — never on page load.
* CSP in `frontend/vercel.json` allows Razorpay:
  * `script-src https://checkout.razorpay.com`
  * `frame-src  https://checkout.razorpay.com https://api.razorpay.com`
  * `connect-src https://api.razorpay.com https://lumberjack.razorpay.com`

## The flow

```
browser                    backend                          Razorpay
   |  POST /subscription/payments {plan_id}
   |------------------------>|  amount/currency FROM THE PLAN ROW
   |                          |  provider.create_order(amount in paise)
   |<- CheckoutResponse ------|  key_id + order_id + amount_paise
   |  Checkout.js (UPI only)
   |--------------------------------------------------------->|
   |<- {razorpay_payment_id, razorpay_signature} --------------|
   |  POST /payments/{id}/verify  (2 values only)
   |------------------------>|  signature check
   |                          |  payment.fetch(id)  <- from Razorpay
   |                          |  order/amount/currency/method == "upi"
   |<- SubscriptionPayment ----|  _finalize (row lock, idempotent)
   |
   |                                   POST /subscriptions/webhooks/razorpay
   |                                   | HMAC over RAW bytes, verified FIRST
   |                                   | payment.captured -> SUCCESS + entitlement
```

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/v1/subscription/payments` | user | open a PENDING payment (amount from the DB) |
| `GET  /api/v1/subscription/payments/{id}` | user (owner only, else 404) | poll while UPI awaits its app approval |
| `POST /api/v1/subscription/payments/{id}/verify` | user (owner only) | browser callback → server-side verification |
| `POST /api/v1/subscriptions/webhooks/razorpay` | **signature only** | `payment.captured` / `payment.failed` |
| `POST /api/v1/subscription/payments/{id}/cancel` | user (owner only) | local cancel of a PENDING row (Razorpay orders are not cancellable through the API) |

`POST /payments` keeps the development route
`/payments/{id}/mock/complete`, which is 404 whenever the provider is not
`INTERNAL` or `ENVIRONMENT=production`.

## Security invariants

* **Amount, currency and order id always come from OUR payment row** — the
  client sends only `plan_id` (at checkout) and the two ids Razorpay handed it
  (at verification).
* **Key secret and webhook secret never leave the server** — not in a response,
  not in a log, not in a client bundle. Only the publishable key id is exposed.
* **Webhook verifies the RAW body bytes before any DB write** — no Pydantic
  body model, `await request.body()` first, HMAC-SHA256 with
  `RAZORPAY_WEBHOOK_SECRET`; a bad signature is `400`, never a silent 200.
* **Non-UPI is rejected server-side** on both paths, regardless of dashboard or
  frontend settings.
* **Idempotent + race-safe**: every state change goes through
  `PaymentService._finalize`, which re-reads the row `WITH FOR UPDATE`. The
  browser callback and the webhook routinely race; exactly one extends the
  subscription, and a replay is a no-op.
* **No hidden retries**: the SDK retry loop is disabled and every call has an
  explicit 15 s timeout — a retry on a money-moving request is how a customer
  gets charged twice.
* `PENDING` stays `PENDING` until a webhook (or a verified capture) resolves it.

## TEST-mode end-to-end checklist

Test UPI IDs (Razorpay Test mode):

| Virtual UPI ID | Result |
|---|---|
| `success@razorpay` | payment captured |
| `failure@razorpay`  | payment failed |

1. Backend `.env`: `PAYMENT_PROVIDER=RAZORPAY` + the three test values
   (restart the API).
2. Frontend `npm run dev`, sign in as a student, open **Subscription**.
3. Pick a plan → the dialog shows *Pay ₹… via UPI* (no "Simulate…" buttons —
   those exist only for `INTERNAL`).
4. In Checkout.js choose UPI, enter `success@razorpay` →
   *Expect: status `SUCCESS`, plan active, "Payment received", one
   "Payment successful" + one "Subscription activated" notification.*
5. Repeat with `failure@razorpay` →
   *Expect: status `FAILED`, no entitlement, one "Payment failed" notification.*
6. Close Checkout.js without paying → *Expect: "Payment not completed" + Try again.*
7. Re-run step 4 and watch the API log for the webhook
   `POST /api/v1/subscriptions/webhooks/razorpay` → 200. Replaying a verify or
   a webhook must **not** extend the subscription twice (the row is locked and
   already `SUCCESS`).
8. Amount tampering: edit `amount_paise` in the browser response and re-post →
   the server still compares against Razorpay's fetched amount, so nothing
   changes (this is covered by unit tests; no manual step needed).
9. Verify the UPI-only rule: with a card enabled in the dashboard, paying by
   card must be rejected with `PAYMENT_VERIFICATION_FAILED`.

Manual webhook test (signature over the raw body):

```bash
python - <<'PY'
import hashlib, hmac, json, os, urllib.request
body = json.dumps({
    "event": "payment.captured",
    "payload": {"payment": {"entity": {
        "id": "pay_TEST", "order_id": "<order id from your payment row>",
        "amount": 10000, "currency": "INR", "method": "upi", "status": "captured"}}}
}).encode()
sig = hmac.new(os.environ["RAZORPAY_WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest()
req = urllib.request.Request(
    "https://<your-railway-domain>/api/v1/subscriptions/webhooks/razorpay",
    data=body, headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig})
print(urllib.request.urlopen(req).status)
PY
```

## Tests

```bash
cd backend-python
python -m ruff check .
python -m pytest tests/test_razorpay_payments.py tests/test_subscription.py -q
```

`tests/test_razorpay_payments.py` mocks the SDK (`razorpay.Client` seam) —
**no network, no real keys** — and covers: paise amount from the DB price,
valid captured UPI, bad signature, amount/currency mismatch, card rejection,
authorized→PENDING→webhook, webhook good/bad signature, replay + callback/webhook
race, FAILED + notification, another user's 404, missing-credential 400,
production startup validation, and that the mock provider is unchanged.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `400 RAZORPAY_NOT_CONFIGURED` | one of the three `RAZORPAY_*` variables is missing |
| Checkout never opens | CSP: `script-src`/`frame-src` missing `checkout.razorpay.com` |
| Verify returns `400 PAYMENT_VERIFICATION_FAILED` | wrong key secret, or the payment is not `captured` / not UPI / wrong amount |
| Payment stays `PENDING` forever | webhook not configured (wrong URL or secret) — the browser callback alone does not finalize an `authorized` payment |
| Webhook returns `400` | secret mismatch, or a proxy re-encoded the body (the signature is over the **raw** bytes) |
| Startup error mentioning `RAZORPAY_KEY_*` | production + `PAYMENT_PROVIDER=RAZORPAY` with missing values |
