# SESSION_RESUME — TRDR Hub launch mission (2026-07-03, session 2: Phases 1+2+3 code complete)

**Mission:** 6-phase launch (audit → LCopilot e2e → sanctions → CBAM/EUDR → park tools → Stripe).
Service-as-software / concierge model. Full brief + constraints in
`memory/project_launch_mission_2026_07.md`. Playbook: `J:\Enso Intelligence\_shipwt66\docs\gtm\GTM-PLAYBOOK-2026-07.md` (§1-4, §11).

## Resume prompt
```
Resume the TRDR Hub launch mission. Phase 0 DONE (f29555b5). Phases 1-3 CODE
COMPLETE (Phase 1: 98e85565 + c74931b8/2e940ce9/a2192a3b · Phase 2: 1cf4ec4c ·
Phase 3: deea9b62). Read memory: project_launch_mission_2026_07 +
reference_concierge_review_queue + reference_sanctions_rulhub_wire +
reference_readiness_tools. If RulHub billing has resumed (~Jul 5), run the blocked
acceptances: (a) /v1/compliance/check live test, (b) Phase 1 acceptance (exporter +
importer upload→delivered PDF through the queue, flag ON in test env) + Render
migration job for 20260703_add_report_review, (c) sanctions sentinel e2e
(scripts/sanctions_sentinel_e2e.py, rh_test_* key) + batch CSV of 10 names,
(d) readiness live m13 citation test (one paid intake → findings carry
clause_cited). Otherwise proceed to Phase 4: park unfit tools (keep LCopilot,
Sanctions, CBAM Check, EUDR Check; evaluate DocGenerator + LC Builder against the
works-e2e/zero-maintenance/no-dilution bar; parked landings → polite page, no dead
links) + homepage rebuild (hero = LCopilot service framing, then 4 live tools, then
RulGPT cross-link). Then Phase 5 (Stripe: products/prices, Checkout at intake,
webhook → submitted, LAUNCH-NOTES.md).
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

## Next phases
- **Phase 4** — Park all tools except LCopilot/Sanctions/CBAM Check/EUDR Check (evaluate
  DocGenerator + LC Builder against the works-e2e/zero-maintenance/no-dilution bar);
  parked landings → polite "not available" page, keep code, no dead links; homepage
  rebuild (hero = LCopilot service framing → 4 live tools → RulGPT cross-link).
- **Phase 5** — Stripe (acct Enso Intelligence Labs): products $29/$49/$79/$149/$149/$249
  + hidden $299 retainer; Checkout at intake; checkout.session.completed → submitted +
  confirmation email; refunds via dashboard reflected by webhook; LAUNCH-NOTES.md.

## Gotchas
- Local full-app boot (`import main`) fails on PRE-EXISTING audit_events/organizations
  mapper error — verify via per-module import.
- `/deliver` endpoint body is Optional — send NO body when there's no note ({} 422s).
- Global `*.pdf` gitignore: public sample PDFs need the scoped exception (already added).
- Standing rules: push every commit; Sonnet 4.6/Opus only; never edit the rulhub repo.
