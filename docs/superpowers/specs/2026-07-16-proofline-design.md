# Proofline — Verified Trade Clearance Design

**Date:** 2026-07-16  
**Status:** Approved for incremental implementation  
**Product:** TRDRHub  
**Scope:** Proofline internal alpha through private-pilot foundations  
**Repository audit:** `docs/audits/2026-07-16-proofline-repository-audit.md`

---

## 1. Outcome

Proofline is a new tool inside TRDRHub that accepts a complete trade case, orchestrates existing TRDRHub review capabilities, routes uncertain or material findings to an internal analyst, supports remediation, and delivers a versioned clearance report.

The customer promise is:

> Identify the document, compliance, identity, and evidence issues that could delay shipment, presentation, or payment.

Proofline does not guarantee shipment acceptance, customs clearance, bank acceptance, payment, regulatory approval, or financing approval. It reports preventable discrepancies, evidence gaps, regulatory issues, and transaction risks based on submitted information and the rule versions available at review time.

TRDRHub remains the application, account, tenant, billing, audit, deployment, and design shell. Proofline is not a separate repository, identity system, rules database, sanctions engine, LC engine, or visual system.

---

## 2. Locked product decisions

1. A Proofline unit of work is a `TradeCase`, not a `ValidationSession` extension. Existing sessions and module results are referenced by the case.
2. Payment arrangement is the first workflow-routing decision.
3. LC cases invoke the existing LCopilot pipeline through an internal adapter. LCopilot remains independently usable and behavior-compatible.
4. Open-account and other non-LC cases remain fully supported and do not display LCopilot as failed or incomplete.
5. Existing sanctions, CBAM, EUDR, document extraction, report, billing, authentication, and audit capabilities remain the source implementations.
6. Proofline normalizes summaries without destroying or rewriting source-module findings.
7. A paid customer-facing final decision requires a qualified internal reviewer at launch.
8. Required checks that are unavailable or degraded cannot silently produce `CLEAR`.
9. Customer corrections create new document versions. Original evidence is immutable.
10. RulHub and EIN remain external services behind narrow adapters. A development mock is never presented as a production verification.
11. Proofline ships behind existing-compatible configuration flags and is exposed under the existing Tools section.
12. All customer and analyst screens reuse the existing TRDRHub shell, tokens, components, status vocabulary, and responsive patterns.

---

## 3. Payment-arrangement routing

The first case question is **Payment arrangement**:

- Letter of credit
- Open account / sales contract
- Advance TT
- Partial advance + balance
- Documents against payment
- Documents against acceptance
- Buyer-led supply-chain finance
- Factoring / receivables finance
- Consignment
- Other

This value controls applicability, expected evidence, checks, language, and report scope. Changing it after submission creates an audited case event and recomputes applicability; it does not delete prior results.

### 3.1 Letter of credit

Required path:

```text
Trade case
  → LC and amendments detected
  → existing LCopilot service
  → structured LC findings and report reference
  → Proofline normalization
  → combined decision recommendation
```

Proofline stores the LCopilot session/result references and normalized summaries. It does not copy UCP600/ISBP rules or AI cross-document prompts. Existing document identifiers, document order, severity semantics, and Expected/Found/SuggestedFix fields are preserved.

### 3.2 Open account / sales contract

The open-account path evaluates, when applicable:

- purchase order and sales-contract consistency;
- buyer payment terms and invoice-approval conditions;
- commercial invoice, packing, shipment, delivery, and acceptance evidence;
- buyer vendor-manual and buyer-policy requirements;
- quantity, price, currency, dates, parties, goods, incoterms, and destination consistency;
- deduction, credit-note, rejection, and chargeback clauses;
- payment undertaking, trade-credit insurance, or equivalent risk coverage;
- factoring or receivables-finance evidence and assignment restrictions;
- expected invoice approval and payment dates;
- missing regulatory submission evidence where the applicable rule service identifies it.

For a Bangladesh-origin open-account export, Proofline may surface requirements and operational reminders based on a versioned rule reference. Bangladesh Bank FE Circular No. 31 dated 31 July 2025 includes Part-D, “Export Under Open Account Credit Terms,” allowing qualifying open-account structures backed by payment undertakings or payment-risk coverage and providing for non-recourse early payment. It also retains exporter/AD-bank documentary obligations. FE Circular No. 39 dated 7 October 2025 expands the relevant insurance/early-payment arrangements. Proofline must cite the evaluated version and evidence; it must not convert these rules into a guarantee or legal opinion.

Primary sources:

- [Bangladesh Bank FE Circular No. 31, 31 July 2025](https://www.bb.org.bd/mediaroom/circulars/fepd/jul312025fepd31e.pdf)
- [Bangladesh Bank FE Circular No. 39, 7 October 2025](https://www.bb.org.bd/mediaroom/circulars/fepd/oct072025fepd39e.pdf)
- [Bangladesh Bank Circular Letter No. 22, 19 June 2025](https://www.bb.org.bd/mediaroom/circulars/fepd/jun192025fepd22e.pdf)

Rules that can change are resolved through RulHub or a versioned TRDRHub reference, not frozen as unversioned prose in application logic.

### 3.3 Other payment arrangements

Each arrangement has an applicability profile rather than a separate workflow implementation:

| Arrangement | Principal evidence emphasis |
|---|---|
| Advance TT | advance-payment evidence, sales contract, allocation to order/invoice, balance exposure |
| Partial advance + balance | advance receipt, remaining payment trigger, shipment/acceptance evidence |
| Documents against payment | collection instruction, transport documents, payment-release conditions |
| Documents against acceptance | collection instruction, acceptance/tenor, maturity date, delivery evidence |
| Buyer-led supply-chain finance | buyer approval, platform/finance terms, eligible invoice, assignment and funding status |
| Factoring / receivables finance | eligible receivable, undertaking/insurance, notice/assignment, recourse status |
| Consignment | title/risk transfer, inventory/sales reporting, remittance trigger, return rights |
| Other | analyst-defined scope, required evidence, and explicit unable-to-assess handling |

The applicability engine only presents relevant modules. Non-applicable modules are shown as `Not applicable`, never as failures.

---

## 4. Domain architecture

Proofline adds a bounded orchestration layer around existing records.

```text
Company / User / Subscription / Stripe / Audit (existing)
                    │
                TradeCase
      ┌─────────────┼────────────────────┐
      │             │                    │
 Parties      Case Documents        Check Runs
                    │                    │
             existing Document      source records
             + version lineage      (LCopilot, sanctions,
                                      CBAM, EUDR, RulHub, EIN)
                                           │
                                    Normalized Findings
                                           │
                                  Remediation Actions
                                           │
                                Recommendation / Decision
                                           │
                                  existing Report storage
```

### 4.1 `TradeCase`

Core fields:

- stable UUID and human-readable case reference;
- `company_id` tenant and customer/case-owner/reviewer references;
- payment arrangement and service package;
- buyer, seller, exporter, importer, bank, facility, and other party references;
- product, shipment, origin, destination, amount, currency, payment-term, and expected-payment data;
- purchase-order, LC, amendments, and other source references;
- workflow status, recommended decision, and final decision summary;
- source LCopilot review and eligible-upgrade references;
- submitted, processing, review, decision, closed, and ordinary audit timestamps.

Structured relational fields are used for identity, lifecycle, querying, permissions, and reporting. Bounded JSON is reserved for extensible transaction facts, source snapshots, and explicitly versioned metadata.

### 4.2 Parties

`TradeCaseParty` represents a role in one case and may reference an existing organization/entity when available. A single entity may hold multiple roles. Role values include buyer, seller, exporter, importer, issuing bank, advising/confirming bank, manufacturer, facility, financier, insurer, freight party, and other.

### 4.3 Documents and evidence versions

`TradeCaseDocument` associates an existing `Document` with a case and supplies:

- logical evidence key and document type;
- immutable version number;
- `supersedes_id` lineage;
- submission/correction round;
- uploader and upload timestamp;
- original hash/reference and extraction reference;
- active/current-version indicator without deleting older versions.

Existing S3 storage, document security, hashes, OCR, extracted fields, and signed URLs are reused. A case association never renames, reorders, or overwrites a backend document ID.

### 4.4 Check runs

`TradeCaseCheckRun` records one applicability evaluation or execution:

- module and module version;
- applicable/not-applicable reason;
- pending/running/result state;
- idempotency key and normalized input hash;
- safe attempt/error metadata;
- source record type and ID;
- structured result summary and source-detail reference;
- start/completion timestamps.

Check states are:

```text
pending
running
clear
issue_found
evidence_incomplete
not_applicable
unable_to_assess
pending_review
```

Retries reuse the idempotency key. A crash may leave a recoverable running record, not an untraceable detached operation.

### 4.5 Unified findings

`ProoflineFinding` contains:

- finding and case IDs;
- source module, source finding ID, and source detail reference;
- category, severity, title, and plain-language explanation;
- affected entity/document and affected field;
- `expected`, `observed`, and `suggested_correction`;
- rule/policy and evidence references;
- automated/human origin;
- customer-visible/internal visibility;
- finding status and reviewer decision;
- created/updated timestamps.

Statuses:

```text
open
acknowledged
customer_action_required
corrected
accepted_exception
false_positive
resolved
unable_to_resolve
```

Normalization is additive. Source-module details are retained and linked. Existing LCopilot findings keep their Expected/Found/SuggestedFix contract.

### 4.6 Remediation

`RemediationAction` links to a finding and records requested action, responsible party, requested correction/evidence, due date, customer response, correction document versions, reviewer resolution, resolution notes, round number, and visibility.

Included correction rounds are derived from the purchased service package. An additional round changes billing/service state but never removes the customer’s ability to see the existing request.

### 4.7 Decisions and events

`TradeCaseDecision` is append-only and versioned. It stores recommendation or final type, decision value, summary, reason, contributing finding/evidence/rule references, unresolved issues, required actions, reviewer, previous recommendation, override reason, system version, report version, and timestamp.

`TradeCaseEvent` is the domain audit stream for transitions and material actions. It supplements, rather than replaces, the existing `AuditService` log.

---

## 5. Status and decision invariants

### 5.1 Workflow status

```text
draft
awaiting_payment
submitted
processing
automated_review_complete
awaiting_analyst_review
action_required
customer_resubmitted
final_review
cleared
conditionally_cleared
blocked
cancelled
closed
```

Allowed transitions are defined in one backend state service. Every transition validates actor role and prerequisites, timestamps the transition, writes `TradeCaseEvent`, calls existing audit hooks, and optionally emits one existing-infrastructure notification.

Terminal decision-flavored statuses do not replace the decision record. They summarize the current workflow state for lists and navigation.

### 5.2 Final decisions

```text
CLEAR
CONDITIONAL_CLEARANCE
ACTION_REQUIRED
MANUAL_REVIEW_REQUIRED
BLOCKED
UNABLE_TO_ASSESS
```

Launch guards:

- paid cases cannot publish a final decision without an authorized reviewer;
- `CLEAR` is invalid while a blocker/critical customer-visible finding remains unresolved;
- a required unavailable/degraded check prevents `CLEAR` unless the reviewer records an explicit, policy-allowed disposition;
- an override requires reviewer identity, reason, timestamp, previous recommendation, and final value;
- a final report references exactly one immutable decision version;
- changing a finalized outcome creates a new decision/report version and audit event.

---

## 6. Orchestration and service boundaries

### 6.1 Applicability

Applicability is deterministic from payment arrangement, countries, products, shipment facts, requested modules, buyer requirements, and evidence presence. It produces an explicit explanation per module.

### 6.2 LCopilot adapter

A thin internal service wraps the existing validation pipeline. The existing `/api/validate` route remains an adapter to the same behavior. Proofline either:

1. references a prior eligible completed LCopilot structured result; or
2. invokes the internal runner with the case’s LC/document references.

Expensive extraction or validation is reused when the source hash, LC identity, and engine version match. New or superseding evidence creates a new run.

### 6.3 Existing screeners

Sanctions, CBAM, and EUDR adapters invoke their current services or reference current result records. Proofline persists module state, source result reference, version, and normalized findings. Source detail remains owned by that module.

A module with a transport, dependency, or engine failure yields `unable_to_assess` or `pending_review`; it cannot map to `clear`.

### 6.4 RulHub

The RulHub adapter sends only necessary transaction context and receives structured requirement IDs, versions, sources, clauses, applicability, and evaluation metadata.

The case stores IDs, rule versions, input/evidence references, timestamps, safe request metadata, and response hashes/snapshots sufficient to reproduce the decision. It does not persist the full RulHub corpus. Timeouts and bounded retries are explicit. Stable reference metadata may be cached; transaction evaluations are not silently inferred from stale success.

### 6.5 EIN

The EIN adapter exposes organization/facility/issuer identity, presentation verification, expiry/revocation, issuer trust, and product-passport retrieval. Stored data is limited to references, verification results, hashes, explicitly disclosed claims, consent/access metadata, and necessary timestamps.

Result vocabulary:

```text
Verified
Expired
Revoked
Missing
Untrusted issuer
Invalid signature
Not shared
Unable to verify
```

Until production APIs are configured, the module is unavailable. A development-only mock requires an explicit flag and displays `Simulated development result`; it can never approve a production report.

### 6.6 Execution durability

The first implementation uses persisted `TradeCaseCheckRun` records and idempotent service calls with the repository’s current background-task model. This keeps the internal alpha compatible with current deployment. The records are deliberately worker-ready so execution can move to a durable queue without changing APIs or result contracts.

---

## 7. LCopilot upgrade

A completed LCopilot review displays **Upgrade to Proofline**.

The upgrade service:

1. validates tenant ownership and eligibility;
2. creates a case with the same customer/company;
3. associates the existing LC documents and structured result by reference;
4. carries extracted fields, findings, and report references without mutation;
5. pre-fills parties, amount, currency, dates, and shipment facts when available;
6. asks for remaining parties and documents;
7. computes a checkout credit from configuration, source payment, source hash/LC identity, and a configurable eligibility window;
8. records the source review, credit calculation, and actor in the audit trail.

Launch default eligibility is 30 days, configurable by environment/package policy. A credit is transparent in the checkout summary and is never hardcoded into page copy or route logic.

---

## 8. Pricing and billing

Proofline uses the current Stripe Checkout and webhook infrastructure with a backend-authoritative service-package registry. UI prices are loaded from that registry; they are not duplicated in page components.

Initial configurable packages:

| Package | Display hypothesis | Included baseline |
|---|---:|---|
| Proofline Standard | $199/case | standard document set, one LC if applicable, standard modules, analyst review, one correction round |
| Proofline Managed Clearance | from $399/case | complex evidence, EIN/buyer requirements, deeper applicable regulatory review, two correction rounds, priority where supported |
| Complex or urgent | Custom quote | high volume, multiple shipments/LCs/jurisdictions, unusual goods, extensive remediation |
| Trade Desk Starter | $999/month | up to 10 standard cases |
| Trade Desk Operations | $2,499/month | up to 30 standard cases |
| Enterprise | Custom | volume, SLA, integrations, reviewer allocation |

Limits include document count, party count, correction rounds, turnaround class, and supported modules. Unsupported urgent SLAs cannot be purchased automatically. BDT/manual invoicing and negotiated enterprise contracts remain supported through current offline/manual patterns.

Payments are idempotently tied to a case and package. Webhooks remain the source of truth for Stripe settlement. Price IDs, credit policy, and limits live in server configuration or database-backed catalog conventions, never secrets or scattered constants.

---

## 9. Customer experience

### 9.1 Placement and language

Proofline appears as a live tool under existing Tools navigation and cards:

**Proofline**  
*Verified Trade Clearance*

> Check whether your order, shipment, evidence, and invoice are ready to be accepted and paid—whether the transaction uses an LC or not.

Primary CTA: **Start a trade case**

Supporting distinction: **LCopilot checks the instrument. Proofline clears the trade.**

### 9.2 Routes

The existing React Router and layouts gain:

```text
/proofline
/proofline/new
/proofline/cases
/proofline/cases/:caseId
```

The detail route uses tabs for overview, documents, findings, actions, and report rather than fragmenting each tab into an independent page.

### 9.3 Staged intake

1. payment arrangement and basic trade details;
2. parties;
3. payment/LC or non-LC terms;
4. products and shipment;
5. documents;
6. optional EIN connection;
7. service level;
8. review and submit.

Drafts save after each stage. Known company data and extracted values are proposed for confirmation. Duplicate hashes are identified, expected documents are explained, and the user is not forced to retype reliable extracted facts.

### 9.4 Case workspace

The existing cards, badges, tabs, alerts, tables, forms, and timeline patterns show:

- current workflow status and recommended/final decision;
- progress and reviewer messages;
- parties, shipment, payment arrangement, and expected payment date;
- document versions and extraction state;
- only applicable check modules;
- credential states;
- findings grouped by severity/status;
- requested actions and correction upload;
- package/billing status;
- report availability and customer-safe audit timeline.

Internal risk flags and notes never render through customer endpoints.

---

## 10. Analyst experience

The current system-admin review area is extended with a Proofline queue rather than replaced.

Analysts can filter by status, urgency, customer, package, payment arrangement, and assigned reviewer; claim or assign a case; inspect source documents/extractions/results; add internal notes; create customer-visible findings; suppress false positives; request corrections; compare versions; approve/override a recommendation; and generate/approve the report.

Claim/assignment is concurrency-safe. Every mutation checks analyst/system-admin permission and tenant/service scope. Internal notes use an internal-only table/visibility value and are excluded at response-schema level, not merely hidden in the browser.

Overrides cannot save without a non-empty reason and prior recommendation snapshot.

---

## 11. Reports and provenance

Proofline reuses existing HTML/PDF generation and S3 delivery. It adds a Proofline report template and structured output from the same report-view model.

The report includes scope, trade summary, parties, shipment/products, evidence reviewed, decision, applicable module results, findings and remediation, reviewer approval, report/version/verification reference, generation timestamp, rule versions, and disclaimers.

Trace path:

```text
decision version
  → normalized finding
  → source module result / requirement version
  → extracted field or disclosed credential claim
  → immutable document/credential reference and location/hash
```

PDF and web views use the same versioned data model. The report is not described as a legal, bank, customs, financing, or regulatory certification.

---

## 12. Security, privacy, and audit

- Every case query is scoped by `company_id` before object access.
- Customer endpoints resolve case access through existing company membership and role semantics.
- Reviewer endpoints require existing internal/admin permissions and log access/mutations.
- Document links use current signed/expiring delivery and storage authorization.
- External adapters send the minimum fields needed for the requested evaluation.
- Logs contain identifiers, states, timing, attempt counts, and safe error codes—not document bodies, extracted sensitive text, credentials, or secrets.
- All state transitions, findings edits, visibility changes, assignments, correction rounds, decisions, report generations, payments, and upgrade credits call existing audit hooks and create a domain event.
- Secrets remain environment-managed.
- Retention and deletion follow existing tenant/document policy while preserving legally required audit references.
- Application-layer tenant scoping remains mandatory because backend service-role database access may bypass database row policies. Database constraints and policies provide defense in depth where consistent with current migrations.

---

## 13. API and contract rules

The backend exposes typed request/response schemas under `/api/proofline`. Shared enums and customer-visible shapes are mirrored in:

- `packages/shared-types/python/schemas.py`
- `packages/shared-types/src/api.ts`

API families:

- case create/list/detail/update/submit;
- parties and staged intake;
- documents/version lineage/correction upload;
- checks and normalized findings;
- remediation responses and final-review request;
- reviewer queue/claim/assign/note/finding/decision;
- pricing/checkout/upgrade eligibility;
- web/PDF/structured report.

Responses do not expose unrestricted ORM objects. Customer and reviewer schemas are separate so internal fields cannot leak through serializer defaults.

---

## 14. Delivery stages

### Stage 1 — Internal alpha

- domain model and migrations;
- payment-method-aware case intake;
- document association/versioning;
- LCopilot reference/invocation path;
- deterministic cross-document/open-account evidence checks;
- normalized findings;
- analyst queue, assignment, notes, correction requests, decision approval;
- customer case workspace;
- report web/PDF;
- feature flags, audit, permissions, and representative tests.

### Stage 2 — Private customer pilot

- hosted checkout/package enforcement;
- correction-round billing;
- sanctions and applicable CBAM/EUDR orchestration hardening;
- notifications;
- LCopilot upgrade and credit;
- operational analytics/outcome questions.

### Stage 3 — RulHub and EIN production integration

- production adapters, consent and evidence references;
- persisted rule-version evaluation metadata;
- buyer policies and credential verification;
- production readiness gates and integration monitoring.

Stable APIs may move Stage 3 work earlier. Unavailable services do not block the base workflow and are never simulated as successful.

---

## 15. Test and release gates

Required automated scenarios:

1. LC case reuses/invokes LCopilot without changing standalone results.
2. Open-account case routes without LCopilot and evaluates payment/evidence requirements.
3. Other non-LC arrangement receives the correct applicability set.
4. Eligible LCopilot upgrade carries documents/results and computes configurable credit.
5. Sanctions issue contributes a normalized non-clear result.
6. CBAM not applicable is not shown as a failure.
7. EUDR evidence incomplete blocks automatic clear.
8. Expired EIN credential maps to evidence/credential issue.
9. RulHub unavailable maps to unable-to-assess/manual review.
10. Correction upload preserves original version and links the successor.
11. Reviewer override without a reason is rejected.
12. Cross-tenant case/document/findings access is rejected.
13. Final report is versioned and references the approved decision.
14. Pricing/package limits and Stripe webhook idempotency are enforced.
15. Existing LCopilot payload, routes, tabs, reports, and focused regression tests remain unchanged.

Release requires migration review, permission and tenant-isolation tests, no sensitive logging, deterministic Expected/Found/SuggestedFix continuity, backend/frontend type parity, feature-flag documentation, external integration configuration documentation, and successful focused regression verification.

---

## 16. Dev Agent Record

### Audit

Completed in `docs/audits/2026-07-16-proofline-repository-audit.md`. The audit identified reusable service boundaries, route/UI integration points, billing overlap, report/reviewer foundations, tenant risks, and current background-execution limits.

### Plan

Implement the smallest vertical slice around a new case aggregate. Preserve every existing engine as a source module, add explicit adapters and provenance, then layer customer and reviewer experiences on existing components.

### Patch

Patches will be split by shared contracts, schema/migration, domain/state services, tenant-safe APIs, orchestration, reviewer workflow, customer UI, report/billing/integrations, and documentation. Each production patch begins with a failing focused test.

### Test

Focused unit, API, permission, transition, billing, report, shared-contract, and UI tests run continuously. Existing LCopilot and relevant module regression suites run before handoff.

### Summarize

Each completed implementation slice records changed files, migration/config requirements, verification evidence, remaining staged work, and any external dependency state without claiming unavailable integrations are complete.
