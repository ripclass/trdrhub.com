# Proofline setup and operations

Proofline is the **Verified Trade Clearance** tool inside TRDR Hub. It uses the
existing TRDR Hub authentication, company tenancy, document storage, extraction,
LCopilot, screening, readiness, billing, notifications, audit, and report systems.
It is not deployed as a separate application.

## Release controls

Set the API and web flags together:

```env
PROOFLINE_ENABLED=true
VITE_PROOFLINE_ENABLED=true
```

The backend flag returns 404 from Proofline customer, billing, and analyst APIs
when disabled. The web flag hides Proofline routes and tool links. Neither flag
changes standalone LCopilot, sanctions, CBAM, or EUDR behavior.

Suggested rollout:

1. Internal alpha: enable both flags for the internal environment; leave checkout
   and EIN disabled.
2. Private pilot: configure service packages, Stripe, notifications, screeners,
   and correction-round operations before enabling selected customer workspaces.
3. External evidence: enable RulHub and EIN only after real API credentials and
   response contracts have been verified.

## Database migration

Proofline migrations extend the existing Alembic chain and reuse current
`companies`, `users`, `documents`, `validation_sessions`, and `reports` tables.

```powershell
cd apps/api
alembic upgrade head
alembic current
```

The migrations add trade cases, parties, document lineage, check runs, normalized
findings, remediation actions, decisions, events, buyer requirements, configurable
service packages, document-session linkage, and voluntary post-report outcomes.
Corrected files create new `Document` and case-association versions; originals are
not overwritten.

## Required existing services

Use the repository's normal API configuration for:

- PostgreSQL/Supabase database and Supabase authentication;
- S3-compatible storage and expiring object links;
- Google Document AI with the existing Textract fallback;
- SMTP for email notifications, when enabled by user preferences;
- Stripe hosted Checkout and the existing `/billing/webhooks/stripe` endpoint;
- the existing Render API and Vercel web deployment model.

Do not put credentials in source code or send document bodies to ordinary logs.

## Proofline configuration

```env
PROOFLINE_ENABLED=true
PROOFLINE_CHECKOUT_ENABLED=false
PROOFLINE_LCOPILOT_CREDIT_DAYS=30
PROOFLINE_LCOPILOT_CREDIT_PERCENT=100
PROOFLINE_MAX_UPLOAD_BYTES=26214400
```

- `PROOFLINE_CHECKOUT_ENABLED=false` preserves manual invoicing and lets cases
  enter the service workflow without changing established LCopilot checkout.
- Enabling checkout also requires `STRIPE_SECRET_KEY` and a verified
  `STRIPE_WEBHOOK_SECRET`.
- The credit window and percentage are configuration, not hard-coded commercial
  policy. Eligibility is limited to the same paid LCopilot review/LC reference.
- Upload size is per file. Existing content-type, hash, tenant, and S3 controls
  still apply.

Service packages are database-backed in `proofline_service_packages`. Initial
rows are commercial hypotheses: Standard ($199), Managed (from $399), custom
quote, and non-public negotiated trade-desk plans. Change active prices, limits,
Stripe price IDs, correction rounds, public visibility, and self-service eligibility
in the package records—not throughout frontend code. Unsupported urgent service
must remain manual quote.

Bangladesh/local contracts may use manual BDT invoicing. Proofline V1 deliberately
does not add exchange-rate automation.

## RulHub

RulHub remains external and API-only:

```env
USE_RULHUB_API=true
RULHUB_API_URL=https://api.rulhub.com
RULHUB_API_KEY=rlh_replace_me
```

Proofline sends bounded transaction context and stores evaluation metadata, rule
IDs/versions, request hashes, evidence references, and timestamps. Transient
requests use bounded retries. Timeout, malformed response, incomplete coverage,
or downtime produces an unavailable/pending-review state; it is never converted
to `Clear`. The full RulHub corpus is not copied into TRDR Hub.

## EIN

EIN remains external identity, credential, and Digital Product Passport
infrastructure:

```env
PROOFLINE_EIN_ENABLED=true
EIN_API_URL=https://ein.example
EIN_API_KEY=replace_me
EIN_VERIFY_PATH=/v1/presentations/verify
EIN_API_TIMEOUT_SECONDS=15
```

Enable EIN only with a production API and verified credentials. If disabled or
unavailable, the case records pending/manual review and does not display mocked
verification. Proofline stores references, result states, issuer and validity
metadata, disclosed claims, and hashes—not wallets, private keys, or unnecessary
credential payloads. EIN consent and selective-disclosure controls remain
authoritative.

## Buyer requirements

System administrators can configure versioned buyer policies through the existing
admin-authenticated Proofline API:

- `GET /api/admin/proofline/buyer-requirements?company_id=...`
- `POST /api/admin/proofline/buyer-requirements`
- `PATCH /api/admin/proofline/buyer-requirements/{id}/activation`

The customer supplies the buyer reference during case intake. Policies are matched
deterministically by tenant, buyer reference, active state, and effective date.
No general no-code rule builder is introduced.

## Workflow and operations

The first intake choice is the payment arrangement: LC, open account/sales
contract, advance TT, partial advance, documents against payment, documents
against acceptance, buyer-led supply-chain finance, factoring/receivables finance,
consignment, or other.

- LC cases reuse an existing LCopilot result/runner and do not copy UCP600 logic.
- Open-account cases check order/contract/invoice/shipment/payment evidence and
  Bangladesh AD-bank/payment-risk evidence where applicable.
- Only applicable sanctions, CBAM, EUDR, RulHub, EIN, and buyer-policy modules are
  shown. Unavailable is not clear; not-applicable is not failure.
- Every paid final decision requires an internal reviewer. Overrides preserve the
  prior recommendation, reviewer, reason, and timestamp.
- Customer corrections create immutable document versions and consume the
  package's configured correction-round entitlement.

Internal operations:

- queue: `GET /api/admin/proofline`
- case review: `GET /api/admin/proofline/{case_id}`
- metrics: `GET /api/admin/proofline/metrics?days=30`

Metrics contain case-level counts, review time, findings, correction rounds,
decision mix, LCopilot conversions, collected revenue, service-package volume,
and voluntary customer outcomes. Gross margin is intentionally unset until
validated analyst-cost data exists. Customer-reported acceptance/payment outcomes
are labelled as unvalidated operational feedback.

Current processing uses persisted idempotent check-run records with the repository's
existing in-process background-task boundary. A deployed durable worker remains a
scale-hardening requirement before unattended high-volume operation.

## Verification

From the repository root:

```powershell
$env:TEMP='H:\tmp'
$env:TMP='H:\tmp'
$env:PYTHONPATH='apps/api'
$tests = Get-ChildItem apps/api/tests -Filter 'proofline*_test.py' | ForEach-Object FullName
python -m pytest $tests -q
npm --workspace apps/web exec vitest run src/lib/proofline src/pages/proofline src/components/proofline
cd apps/api
alembic heads
```

Run the existing LCopilot validation, checkout/webhook, results-mapper, sanctions,
CBAM, and EUDR regression suites before enabling production traffic.

## Customer-facing limitation

Proofline identifies preventable discrepancies, missing evidence, regulatory
issues, identity/credential states, and transaction risks based on submitted
information. Its report is not a legal guarantee, bank guarantee, customs decision,
regulatory certification, shipment acceptance guarantee, or payment guarantee.
