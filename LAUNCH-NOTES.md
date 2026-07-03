# LAUNCH-NOTES — Ripon's manual switch steps (2026-07 launch)

Everything below is a manual step only you can do. The code side of Phases 0–5 is
shipped; this checklist takes it from "built" to "live and charging money".
Work top to bottom. Items marked **[test first]** should be done in Stripe TEST
mode end-to-end before repeating with live keys.

---

## 1. Stripe (account: Enso Intelligence Labs, `acct_1T4IAtBG8gnvAJXa`)

### 1a. Test mode first **[test first]**
1. Dashboard → Developers → API keys (Test mode) → copy `sk_test_…`.
2. On **Render** (srv-d41dio8dl3ps73db8gpg → Environment) set:
   - `STRIPE_SECRET_KEY=sk_test_…`
   - `STRIPE_CHECKOUT_ENABLED=true`
3. Create the test webhook: Dashboard → Developers → Webhooks → Add endpoint
   - URL: `https://api.trdrhub.com/billing/webhooks/stripe`
   - Events: `checkout.session.completed`, `charge.refunded`
   - Copy the signing secret → Render env `STRIPE_WEBHOOK_SECRET=whsec_…`
4. (Optional, tidy dashboard) create the products/prices:
   `STRIPE_SECRET_KEY=sk_test_… apps/api/venv/Scripts/python scripts/stripe_setup_products.py`
5. **E2E test** with card `4242 4242 4242 4242` (any future expiry/CVC):
   - LCopilot: upload + validate a pack (flag `LCOPILOT_REVIEW_QUEUE_ENABLED=true`
     needed — see §3) → status page shows the $29/$49/$79 buttons → pay →
     "Confirming payment" → job appears in Admin → Review Queue → Approve &
     Deliver → customer gets the PDF. ✔
   - Readiness: /tools/cbam-readiness-check → paid intake → redirected to
     Stripe → pay → job in the queue → deliver. ✔
   - Refund: refund the payment in the dashboard → job's status page shows
     "This purchase was refunded" within a minute. ✔

### 1b. Live mode (cutover)
1. Repeat 1a with **Live mode** keys: `sk_live_…` + a live webhook endpoint +
   its `whsec_…`. Same URL, same two events.
2. Re-run `scripts/stripe_setup_products.py` with the live key.
3. Dashboard settings to switch on (once, live mode):
   - Settings → Emails → **enable customer receipt emails** (we build no
     invoicing — Stripe's receipts are the receipts).
   - Settings → Payment methods → enable **Adaptive Pricing** (customers see
     local currency; we settle USD).
   - Branding: upload the TRDR Hub logo so the Checkout page looks like us.
4. The $299/mo retainer: `retainer_monthly` price exists but is hidden.
   Offer it manually — Dashboard → Payment Links → create a link from that
   price and send it to a customer at their ~3rd repeat purchase.
5. Refund policy = you, in the dashboard (full refund, no questions). The app
   reflects it automatically via webhook — nothing else to do.

## 2. Render (backend)

1. **Migrations are NOT automatic.** After the next deploy run:
   `render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head"`
   This applies BOTH pending migrations:
   - `20260703_add_report_review` (review queue)
   - `20260703_add_payment_fields` (payments)
   Verify: `https://api.trdrhub.com/health/db-schema`.
2. Env vars to confirm/set (Environment tab):
   - `LCOPILOT_REVIEW_QUEUE_ENABLED=true` ← the concierge cutover switch
   - `STRIPE_CHECKOUT_ENABLED=true` + the three STRIPE_* keys (§1)
   - `RULHUB_API_KEY=` your Internal-tier key (after billing resumes)
   - `RULHUB_USE_COMPLIANCE_CHECK=true` (default; kill switch if the bundle
     endpoint misbehaves)
   - `READINESS_LEADS_EMAIL` (optional; defaults to support@trdrhub.com)
   - SMTP_* already set (emails live since the DNS cutover)
3. Render billing: keep the card current + set a billing alarm — the June DB
   outage and the July RulHub suspension were both billing, not code.

## 3. RulHub (after billing resumes ~2026-07-05)

1. Confirm `https://api.rulhub.com/health` is green; top up/resume billing.
2. Run the blocked acceptance tests from trdrhub:
   - Sanctions sentinels: `RULHUB_API_KEY=rh_test_… apps/api/venv/Scripts/python scripts/sanctions_sentinel_e2e.py` → 3 PASS
   - One LCopilot validation → confirm findings cite rules (compliance bundle).
   - One readiness intake → findings carry `clause_cited` from the m13 corpus.

## 4. Pre-marketing checklist (from the playbook §11)

- [ ] `/health`, `/health/db`, `/health/sanctions-lists` green; UptimeRobot covers them.
- [ ] `ADMIN_PASSWORD` rotated.
- [ ] Crawl the deployed site once — no 404s/dead links (parked tools should show
      the "not available" page).
- [ ] Honesty grep on the deployed bundle: "ISBP 745", "trusted by banks",
      "Bangladesh SMEs" — all must be absent (already swept in code).
- [ ] Sample report downloads at `https://trdrhub.com/samples/lcopilot-sample-report.pdf`.

## 5. Day-to-day operations once live

- New paid jobs appear in **Admin Console → Concierge → Review Queue** only
  after payment. Curate findings → add your note → **Approve & Deliver**.
- CBAM/EUDR jobs that arrived while RulHub was down show an orange
  "engine unreachable" warning — hit **Re-run engine** before delivering.
- Refunds: Stripe dashboard → the job shows "refunded" automatically.
- Leads from the free scope checks land in support@trdrhub.com
  (`[lead] CBAM scope check — …`).
