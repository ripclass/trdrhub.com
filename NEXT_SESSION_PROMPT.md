# Next Session Prompt — 2026-04-21 (evening)

Paste to start a fresh Claude session. Self-contained, assumes zero memory of prior conversations.

## Current live state

- **master:** `9940ccb8` (no trdrhub commits this session — design/planning only)
- **Backend (Render):** `4febcd1c` on `srv-d41dio8dl3ps73db8gpg` — stable
- **OpenRouter credits:** still out. AI Examiner returns empty; arithmetic backstop + RulHub + Opus veto still run.
- **RulHub (api.rulhub.com):** significantly improved tonight — see Stream B below

## Two parallel work streams on the table

### Stream A — Importer parity with exporter (BRAINSTORM + PLAN DONE, NOT EXECUTED)

Full design + 4 execution plans written tonight. Ready to start Phase 1 whenever you give the go.

**Documents to read first (in order):**
- `docs/superpowers/specs/2026-04-21-importer-parity-design.md` — full design doc
- `docs/superpowers/plans/2026-04-21-phase-1-shared-extraction.md` — 9 tasks, pure refactor
- `docs/superpowers/plans/2026-04-21-phase-2-importer-flows.md` — 10 tasks, migration + routes + results rewrite
- `docs/superpowers/plans/2026-04-21-phase-3-importer-actions.md` — 9 tasks, 4 action endpoints
- `docs/superpowers/plans/2026-04-21-phase-4-shell-wireup.md` — 8 tasks, sidebars + dashboard wire-up + 5-second smoke

**Locked-in decisions (don't re-litigate):**
- Sessions are **independent** (no Moment 1 ↔ Moment 2 linkage) — billing clarity + stale-LC protection
- Two moments = two routes = two sidebar items (`/draft-lc`, `/supplier-docs`)
- Shared home: `apps/web/src/components/lcopilot/`
- Execution order: **extract-first** (refactor exporter into shared, THEN build importer on top)
- `ValidationSession.workflow_type` enum: `exporter_presentation` / `importer_draft_lc` / `importer_supplier_docs`
- Sidebars: **4 items exporter** (Dashboard · Upload · Billing · Settings), **5 items importer** (Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings)
- Reviews page stays at `/reviews` but removed from sidebar (reach via "View all →" on dashboard)
- Dashboard wire-up is the hard gate: **5-second smoke** (new session appears on dashboard within 5s of validation completing, no manual reload). Plan 4 Task 7.

**Execution mode chosen: INLINE** (not subagent-driven). Ripon has recurring bad experiences with subagents making mistakes. Inline carries full brainstorm context + memory rules forward.

**First action when resuming Stream A:** read the Phase 1 plan, confirm baseline exporter Playwright is green, start Task 0 (pre-flight recon).

### Stream B — RulHub consumer-side follow-up (NEW WORK LIST)

RulHub-side Claude shipped 5 big commits this evening. Probe jumped from **4 findings → 336 findings**, score 0.9468 → 0.6638, `rules_checked` now populated (744). Engine-error bugs gone. 1 expected finding surfaces cleanly (inspection-cert date mismatch); others need either trdrhub payload enrichment or RulHub msg-template fixes.

**Read first:**
- `memory/project_rulhub_2026_04_21_breakthrough.md` — full analysis with payload enrichment checklist and consumer-code checklist

**RulHub commits (their side only; don't try to edit their repo):**
- `b935d19b` — ISBP 821 skeleton supersession (62 rows)
- `04ef35a4` — Validator fixes: numeric preflight silent-pass + reverse path alias + days alias
- `8214aaa6` — CLAUDE.md docs update
- `702d08e6` — `/v1/validate/set` refactor: nested envelope + multi-family fan-out + `rules_checked`
- `1f15d5e1` — Category C: 4 new CROSSDOC rules + `computed_amount_comparison` validator + `conditional_logic` enhancement

**Probe scripts (ready to re-run, no OpenRouter credits needed):**
```
PYTHONIOENCODING=utf-8 RULHUB_API_KEY=<key> python scripts/rulhub_probe.py
PYTHONIOENCODING=utf-8 RULHUB_API_KEY=<key> python scripts/rulhub_probe_sources.py
```

Status note to RulHub Claude: `scripts/RULHUB_STATUS_NOTE.md` (from this session, summarizes the earlier 4-finding probe — now outdated but still a useful narrative).

**Work list (trdrhub side only; RulHub has its own separate work list on their repo):**

1. **Expand engine-error filter phrases** in `apps/api/app/routers/validation/validation_execution.py:_is_rule_engine_error` (~line 1995):
   - Add `"conditional_logic: {"` and `"computed_amount_comparison: {"` — these are RulHub rule-spec dumps that appear as finding messages when the newer rule types fire but don't render human text. Gate on `null field_a AND null field_b` as before to avoid dropping legit findings.

2. **Synthesize finding messages in `_normalize_rulhub_finding`** (~line 1929) when `finding` starts with a spec-dump marker. Use `field_a`/`field_b`/`rule_id` to build a human title. Example: CROSSDOC-INV-MATH-001 with `field_b: invoice.total_amount = 397050.0` → "Invoice arithmetic mismatch — stated total does not match computed total from quantity × unit_price".

3. **Enrich payload** in `validation_execution.py` dual-prefix builder (~line 1590-1870) and `_FIELD_ALIASES_FOR_RULHUB`. Needed new fields:
   - `invoice.quantity`, `invoice.unit_price` (for INV-MATH — partially works, verify)
   - `insurance_doc.currency_code`, `lc.incoterms` (for EXTRANEOUS-INSURANCE)
   - `lc.packing_list_per_carton_required` (new derivation from 46A text)
   - `packing_list.per_carton_detail` (new extractor field)
   - `document.original_marking`, `document.signature` (for A31 invoice-signed)
   - `bill_of_lading.clean_bl` (derive from `on_board_notation_present` + absence of "dirty" markers)

4. **Tighter dedup** — lc/credit duplicates + conditional_logic-dump variants. Current dedup key `(rule_id, title, expected, found)` won't catch variants with spec-dump titles. Consider `(rule_id, frozenset(documents_involved))` as a secondary key when msg is a spec dump.

5. **Wire `rules_checked` into diagnostic logs** in `apps/api/app/services/rulhub_client.py:validate_document_set` (~line 435):
   ```python
   logger.info(
       "RulHub %d rules_checked · %d discrepancies · %d crossdoc · score %.4f",
       result.get("rules_checked", 0),
       len(result.get("discrepancies", [])),
       len(result.get("cross_document_discrepancies", result.get("cross_doc_issues", []))),
       result.get("score", 0.0),
   )
   ```

6. **Filter "invalid value" noise on absent fields** — UCP600-2/3 rules report "'entity.role' has an invalid value" when trdrhub doesn't emit that field. Decide per field: populate with sensible default, or filter as noise. RulHub-should-fix too ("field missing" ≠ "invalid value"), but trdrhub may want a local filter in the meantime.

## RulHub engine bugs (THEIR side, surface but don't try to fix here)

- `CROSSDOC-BL-LC-12`: rule references `bl.carrier_name` but field only lives in `bill_of_lading` schema — path mismatch.
- conditional_logic + computed_amount_comparison rules dump their spec as the finding text.
- UCP600-20D/20E sometimes report "inconsistent" when values match (e.g. CHITTAGONG == CHITTAGONG).
- UCP600-2/3 fire "invalid value" on `None` — should fire "field missing" instead.

Don't try to fix these in trdrhub — they're in `J:\Enso Intelligence\ICC Rule Engine`. Surface to RulHub Claude if it comes up.

## Priority recommendation for next session

**Start with Stream A — Importer Phase 1** unless you want RulHub findings surfacing on the live UI first.

Why: Stream A is a pure refactor of exporter into shared components with zero behavior change. It unblocks all 4 phases of importer work. Stream B (RulHub consumer fixes) is a small set of targeted edits that can slot in later — doesn't block anything. Also Stream B is harder to verify end-to-end without OpenRouter credits (no Opus veto to validate the findings after filtering).

If you want to see RulHub findings on the UI tonight: do a small Stream B slice — items 1 + 2 + 5 above. ~1-2 hours of work. Leave payload enrichment (3) + dedup (4) + noise filter (6) for later once credits are back.

## Quick starter commands

**Resume importer Phase 1:**
```
cat docs/superpowers/plans/2026-04-21-phase-1-shared-extraction.md
cd apps/web && npm run type-check && npm run lint && npm run test
cd apps/web && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts --reporter=json > /tmp/phase1-baseline.json
```

**Re-probe RulHub to confirm current state:**
```
PYTHONIOENCODING=utf-8 RULHUB_API_KEY=<key> python scripts/rulhub_probe.py
```

**Read the big picture memories:**
```
cat CLAUDE.md
cat memory/project_importer_parity_brainstorm_2026_04_21.md
cat memory/project_rulhub_2026_04_21_breakthrough.md
cat memory/feedback_no_hardcoded_validators.md
cat memory/feedback_dont_reinvent_rulhub.md
```

## Reminders (from memory, don't violate)

- **Don't touch `J:\Enso Intelligence\ICC Rule Engine`** — separate Claude workspace, separate ball.
- **No hardcoded Python validators for discrepancy classes** — use the AI Examiner. Only exception is `validate_invoice_arithmetic` deterministic backstop.
- **Extraction is a blind transcriber** — no format validation at extraction time, no jurisdiction hardcoding.
- **Don't skip Opus veto.**
- **Don't re-add loops** (per the prior session's end state).
- **Vercel plugin hook nags are false positives** — repo is Vite + FastAPI, not Next.js.
- **Inline execution**, not subagents. Subagents make mistakes in this codebase.
