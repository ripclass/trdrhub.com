# SESSION_RESUME — TRDR Hub launch mission (2026-07-03, session 2)

**Mission:** 6-phase launch (audit → LCopilot e2e → sanctions → CBAM/EUDR → park tools → Stripe).
Service-as-software / concierge model. Full brief + constraints in
`memory/project_launch_mission_2026_07.md`. Playbook: `J:\Enso Intelligence\_shipwt66\docs\gtm\GTM-PLAYBOOK-2026-07.md` (§1-4, §11).

## Resume prompt
```
Resume the TRDR Hub launch mission. Phase 0 DONE (f29555b5). Phase 1 CODE COMPLETE
(backend 98e85565; frontend+wire c74931b8/2e940ce9/a2192a3b). Read memory:
project_launch_mission_2026_07 + reference_concierge_review_queue. If RulHub billing
has resumed (~Jul 5): integration-test /v1/compliance/check + run the Phase 1
acceptance (exporter + importer upload→delivered PDF through the queue, flag ON in
test env), then Render migration job for 20260703_add_report_review. Otherwise
proceed to Phase 2 (sanctions screener → POST /v1/screen/sanctions, fail-closed,
sentinel names) and Phase 3 (CBAM/EUDR questionnaire tools).
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

## Phase 1 remaining (blocked on RulHub billing resume ~2026-07-05)
1. Live integration test vs api.rulhub.com — confirm /v1/compliance/check accepts the
   envelope (any 400/404 auto-falls-back, so prod is safe either way).
2. Acceptance: one exporter + one importer run, upload → status page → admin queue →
   Approve & Deliver → PDF, no DB fiddling. Needs `LCOPILOT_REVIEW_QUEUE_ENABLED=true`.
3. After deploy: `render jobs create srv-d41dio8dl3ps73db8gpg --start-command
   "alembic upgrade head"` (migration `20260703_add_report_review`).

## Next phases
- **Phase 2** — Sanctions screener → `POST /v1/screen/sanctions`, fail-closed, sentinel
  test names. `routers/sanctions.py` exists with 4 TODOs + client-side-faked batch.
- **Phase 3** — CBAM ($149) + EUDR ($149, both $249) questionnaire tools, net-new, RulHub
  m13 rules, same review queue, SEO landings `/tools/cbam-readiness-check` + eudr.
- **Phase 4** — Park all tools except LCopilot/Sanctions/CBAM/EUDR; homepage rebuild.
- **Phase 5** — Stripe checkout at intake → webhook flips job to submitted; LAUNCH-NOTES.md.

## Gotchas
- Local full-app boot (`import main`) fails on PRE-EXISTING audit_events/organizations
  mapper error — verify via per-module import.
- `/deliver` endpoint body is Optional — send NO body when there's no note ({} 422s).
- Global `*.pdf` gitignore: public sample PDFs need the scoped exception (already added).
- Standing rules: push every commit; Sonnet 4.6/Opus only; never edit the rulhub repo.
