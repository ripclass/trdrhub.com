# SESSION_RESUME — TRDR Hub launch mission (2026-07-03)

**Mission:** 6-phase launch (audit → LCopilot e2e → sanctions → CBAM/EUDR → park tools → Stripe).
Service-as-software / concierge model. Full brief + constraints in
`memory/project_launch_mission_2026_07.md`. Playbook: `J:\Enso Intelligence\_shipwt66\docs\gtm\GTM-PLAYBOOK-2026-07.md` (§1-4, §11).

## Resume prompt
```
Resume the TRDR Hub launch mission. Phase 0 (audit) DONE at f29555b5; Phase 1 backend
spine DONE at 98e85565. Read memory: project_launch_mission_2026_07 +
reference_concierge_review_queue. Continue Phase 1 frontend: (1) admin review screen,
(2) customer status page /lcopilot/status/:jobId, (3) /lcopilot landing rewrite per
playbook §3.1. Then wire pipeline to check_compliance + integration-test after RulHub
resumes. Then Phases 2-5.
```

## Done this session
- **Phase 0 — COMPLETE** (commit `f29555b5`). Security+code audit (3 agents + Codex gate),
  `docs/audits/2026-07-launch-audit.md`. Fixed 5 CRITICAL + 7 HIGH: unauth ATO (/auth/fix-password),
  role escalation (onboarding+register), unauth admin vault/dr/governance + price-verify, 2 IDOR
  clusters, JWT guard, upload DoS cap, 2FA log, vuln dep bumps, token file, +Codex-found price-verify
  leak & member-seed. `npm audit fix` (35→11, zero runtime crit/high). Removed ~90 junk files.
- **Phase 1 — backend spine COMPLETE** (commit `98e85565`). Concierge review queue. Full map in
  `memory/reference_concierge_review_queue.md`. Behind `LCOPILOT_REVIEW_QUEUE_ENABLED` (default off).
  New: report_review state machine + migration `20260703_add_report_review`, pipeline enrollment hook,
  results gate, `/api/lcopilot/status/{id}` + `/api/admin/review-queue/*` router, `lc_report.py` cited
  PDF, 2 notification types, `RulHubClient.check_compliance`.

## Next up — Phase 1 remaining (frontend + wire)
1. **Admin review screen** (`apps/web`) — list `/api/admin/review-queue`, open a job, edit/suppress/
   annotate findings, set note, **Approve & Deliver**. Add under AdminShell (`pages/admin/`).
2. **Customer status page** — route `/lcopilot/status/:jobId` → `GET /api/lcopilot/status/{id}`
   (review_state + timeline + delivered flag + report link). New page component.
3. **`/lcopilot` landing rewrite** — `apps/web/src/pages/Index.tsx` per playbook §3.1 (concierge copy,
   "Your LC pack, checked before the bank sees it", 3 steps, $29/$49/$79 table from `lib/pricing.ts`,
   sample redacted report download, confidentiality + refund line). Honesty: ISBP 821 not 745.
4. **Wire the pipeline to prefer `check_compliance`** (`/v1/compliance/check`) over the old
   `validate_document_set` list shape — integration-test after RulHub billing resumes ~2026-07-05.
5. **Acceptance:** one exporter + one importer run, upload→delivered PDF through the queue, no DB fiddling.

## Gotchas
- Local full-app boot (`import main`) fails on a PRE-EXISTING `audit_events.organization_id` →
  missing `organizations` mapper error in `.venv-b1` — unrelated to these changes. Verify via
  per-module import (`import app.routers.lcopilot_review`), not full boot.
- RulHub `api.rulhub.com` billing-suspended until ~2026-07-05 AM. Build now, integration-test after.
- Render has NO auto-migration: after deploy run `render jobs create srv-d41dio8dl3ps73db8gpg
  --start-command "alembic upgrade head"` (see `memory/reference_render_migrations.md`).
- Standing rules: push every commit immediately; keep Sonnet 4.6/Opus (never downgrade); trdrhub-only
  (never edit the rulhub repo — surface needs to Ripon).
