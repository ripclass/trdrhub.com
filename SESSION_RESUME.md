# SESSION_RESUME — TRDR Hub launch mission (2026-07-03, session 2: Phases 1–4 code complete)

**Mission:** 6-phase launch (audit → LCopilot e2e → sanctions → CBAM/EUDR → park tools → Stripe).
Service-as-software / concierge model. Full brief + constraints in
`memory/project_launch_mission_2026_07.md`. Playbook: `J:\Enso Intelligence\_shipwt66\docs\gtm\GTM-PLAYBOOK-2026-07.md` (§1-4, §11).

## Resume prompt
```
Resume the TRDR Hub launch mission. Phase 0 DONE (f29555b5). Phases 1-4 CODE
COMPLETE (P1: 98e85565 + c74931b8/2e940ce9/a2192a3b · P2: 1cf4ec4c · P3: deea9b62 ·
P4: 16daaccd). Read memory: project_launch_mission_2026_07 +
reference_concierge_review_queue + reference_sanctions_rulhub_wire +
reference_readiness_tools + reference_phase4_parked_tools. Two workstreams left:

(A) If RulHub billing has resumed (~Jul 5), run the blocked acceptances:
/v1/compliance/check live test · Phase 1 acceptance (exporter + importer
upload→delivered PDF through the queue, LCOPILOT_REVIEW_QUEUE_ENABLED=true in test
env) + Render migration job for 20260703_add_report_review · sanctions sentinel e2e
(scripts/sanctions_sentinel_e2e.py, rh_test_* key) + batch CSV of 10 names ·
readiness live m13 citation test · crawl deployed site for dead links (Phase 4).

(B) Phase 5 — Stripe launch-ready (acct Enso Intelligence Labs
acct_1T4IAtBG8gnvAJXa): products/prices $29/$49/$79 (LCopilot) + $149/$149/$249
(readiness) + hidden $299/mo retainer; Stripe Checkout (hosted) at intake — pay
first, then job enters the queue; checkout.session.completed webhook flips job to
submitted + confirmation email (billing.py webhook already signature-verified);
refunds via dashboard reflected by webhook; receipts via Stripe built-ins (no
custom invoicing); test-mode e2e; write LAUNCH-NOTES.md with Ripon's manual
live-switch steps. Pricing values live in apps/web/src/lib/pricing.ts
(CONCIERGE_REPORTS + READINESS_REPORTS).
```

## Done this session (2026-07-03, session 2) — Phase 1 frontend + wire
- **Admin review screen** — `apps/web/src/pages/admin/sections/review/ReviewQueue.tsx`,
  AdminShell section `review-queue`, "Concierge" sidebar group. Queue list → detail →
  edit/suppress/annotate findings, reviewer note, needs-info, Approve & Deliver.
- **Customer status page** — `/lcopilot/status/:jobId` (`pages/lcopilot/ReviewStatusPage.tsx`),
  4-step tracker, 30s poll, needs-info callout, report download + results link.
  New backend endpoint `GET /api/lcopilot/status/{id}/report` (presigned cited report);
  status payload now carries `workflow_type`.
- **Results-gate redirect** — 403 `{error_code: under_review}` from /api/results now
  routes to the status page (both fetch paths in `use-lcopilot.ts`).
- **/lcopilot landing rewritten** per playbook §3.1 — concierge copy, 3 steps,
  $29/$49/$79 (`CONCIERGE_REPORTS` in `lib/pricing.ts`), export+import sides, trust
  anchors, sample redacted report at `/samples/lcopilot-sample-report.pdf`
  (generated from the real template by `scripts/gen_sample_report.py`; .gitignore
  exception added), ISBP 821 only, fabricated metrics/testimonials removed,
  advisory footer.
- **check_compliance wired** — pipeline prefers `POST /v1/compliance/check` (nested
  envelope; adapter `check_compliance_set` flattens response to validate/set shape;
  ESCALATION log on block/reject/sanctions hits), falls back to `/v1/validate/set`
  in-request. Kill switch `RULHUB_USE_COMPLIANCE_CHECK=false`. Stub-tested.
- Verified: tsc clean on touched files (pre-existing errors unchanged),
  useCanonicalJobResult 7/7, Vite build green, backend per-module imports OK.

## Also done this session — Phase 2: sanctions → RulHub, fail-closed (`1cf4ec4c`)
- `RulHubClient.screen_sanctions` fixed to the real schema ({entity,country,vessel,
  transaction}); new `services/sanctions_rulhub.py` fail-closed mapping (unavailable ≠
  clear; 9 pytest cases); `routers/sanctions.py` rewired — party/vessel/goods/quick/
  batch through RulHub, 503 screening_unavailable on failure, all fake surfaces
  (sync stats, notifications, API keys, webhooks, CSV jobs, certificates) now honest.
- Frontend: `screeningShared.tsx` (fail-closed banner, disclaimer w/ OFAC-50%, real
  list registry), party/vessel/goods pages fail-closed UX + action badges, batch page
  real CSV → /screen/batch (was a client-side mock simulation).
- `scripts/sanctions_sentinel_e2e.py` ready for the rh_test_* sentinel check.

## Also done this session — Phase 3: CBAM/EUDR readiness tools (`deea9b62`)
- Backend: `services/readiness.py` (question sets, annex-based scope verdicts, m13
  engine w/ runtime source discovery + outage degradation) + `routers/readiness.py`
  (questions / scope-check public / scope-summary email-gate / submit auth → SAME
  review queue, workflow_type cbam/eudr/cbam_eudr_readiness, unconditional).
  Admin `POST /{id}/rerun-engine` + ReviewQueue intake-answers panel + rerun button.
  `lc_report` titles keyed by workflow_type. `RulHubClient.lookup_rules`. 12 pytest.
- Frontend: `/tools/cbam-readiness-check` + `/tools/eudr-readiness-check` (SEO via
  useSeoMeta, §3.2 anchors, scope widget + email gate), `/tools/readiness/apply`
  intake (RequireAuth), `READINESS_REPORTS` pricing, status-page readiness copy.

## Blocked on RulHub billing resume (~2026-07-05)
1. Phase 1: live test /v1/compliance/check (any 400/404 auto-falls-back — prod safe).
2. Phase 1 acceptance: exporter + importer run, upload → status page → admin queue →
   Approve & Deliver → PDF. Needs `LCOPILOT_REVIEW_QUEUE_ENABLED=true` in a test env.
3. After deploy: `render jobs create srv-d41dio8dl3ps73db8gpg --start-command
   "alembic upgrade head"` (migration `20260703_add_report_review`).
4. Phase 2 acceptance: sentinel e2e (3 PASS) + batch CSV of 10 names in the UI.
5. Phase 3 acceptance: one paid readiness intake → findings cite the m13 corpus
   (clause_cited populated); free scope check + landings already verified locally.

## Also done this session — Phase 4: tools parked + homepage rebuilt (`16daaccd`)
- 14 tools → `ParkedToolPage` via route wildcards (code in-tree). DocGenerator +
  LC Builder evaluated (real backends, but no e2e pass + type rot + dilution) → parked.
- Homepage: hero = LCopilot service framing + sample-PDF download; ToolsSection = 4
  live tools + RulGPT (tfrules.com) cross-link; PartnersSection (fabricated bank
  logos/certifications) removed; FAQ rewritten honest; fake newsletter form removed.
- /tools index + footer rebuilt; ISBP745→821 sweep across 12 files (0 remaining).
- Verified: build green, tsc error count identical to baseline (845), no live surface
  links to parked routes.

## Next phase
- **Phase 5** — Stripe (see resume prompt B). Last build phase before launch cutover.

## Gotchas
- Local full-app boot (`import main`) fails on PRE-EXISTING audit_events/organizations
  mapper error — verify via per-module import.
- `/deliver` endpoint body is Optional — send NO body when there's no note ({} 422s).
- Global `*.pdf` gitignore: public sample PDFs need the scoped exception (already added).
- Standing rules: push every commit; Sonnet 4.6/Opus only; never edit the rulhub repo.
