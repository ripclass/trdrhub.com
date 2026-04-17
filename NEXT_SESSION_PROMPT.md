# Next Session Prompt — RulHub payload rewrite

Paste to start a fresh Claude session. Self-contained, assumes zero memory of 2026-04-17 evening.

---

## Read first (3 min, in this order)

1. `memory/project_rulhub_payload_audit_2026_04_17_evening.md` — **★★ THE DEFINITIVE DIAGNOSIS.** Four layered problems, full UCP600 path inventory, example payload. This is your specification for the fix.
2. `memory/project_rulhub_is_the_engine.md` — why RulHub is the engine, trdrhub the consumer.
3. `memory/feedback_dont_reinvent_rulhub.md` — do not write local validators.
4. `memory/feedback_scope_trdrhub_only.md` — do not touch `J:\Enso Intelligence\ICC Rule Engine`.
5. `memory/reference_rulhub_api_conventions.md` — endpoint shapes + prefix rules.

## Live state

- master tip: `df5bb357`. `USE_RULHUB_API=True`. RULHUB_API_KEY set on Render.
- IDEAL SAMPLE (`.playwright-mcp/ideal-sample/*.pdf`) returns COMPLIANT / 77% / **0 findings**.
- Zero findings is wrong — real discrepancies exist (invoice arithmetic $61,700, port literal conflict, BL missing CLEAN ON-BOARD, LC "UCP LATEST VERSION" ambiguity, missing dates, missing signature).

## Why 0 findings (authoritative from RulHub-side Claude's source-code dump)

**My fixable problems (trdrhub side):**

1. **Prefix mismatch.** Rules use BOTH short (`bl.*`, `coo.*`, `insurance.*`) AND long (`bill_of_lading.*`, `insurance_doc.*`) prefixes. `lc.*` AND `credit.*` coexist too. My yesterday's payload sent short prefixes only. Every long-prefix rule silently passed.
2. **Suffix mismatch.** UCP600 rules want `issuer_name`, `buyer_name`, `applicant_name`, `beneficiary_name`, `currency_code`. My alias map sends bare `issuer`, `buyer`, etc.
3. **Missing derived booleans.** Rules expect `lc.is_transferred`, `lc.partial_shipments_permitted`, `bill_of_lading.on_board_notation_present`, `bill_of_lading.full_set_required`, `invoice.goods_description_matches_lc`, etc. — computed fields trdrhub must derive from existing extractions.

**NOT my problem (Ripon is fixing on RulHub side):**

4. ISBP 821 deep rules (60+) have 0 conditions — skeletons. Backfill in progress by RulHub-Claude.
5. RulHub `null == null → is_valid=True` silent-pass bug. Can't fix from trdrhub. Workaround: ensure every referenced path has a non-null value.

## The work — in order

### Commit 1: Rewrite the RulHub doc-list builder

File: `apps/api/app/routers/validation/validation_execution.py` lines ~1590-1725.

Changes:
- Emit each doc under BOTH prefixes where they differ (`bl` + `bill_of_lading`; `insurance` + `insurance_doc`). Same field payload, two entries in the `documents[]` list.
- Duplicate LC data under both `lc` and `credit` type entries.
- Expand `_FIELD_ALIASES_FOR_RULHUB`:
  - party fields: `issuer` → `issuer` + `issuer_name`; same for `buyer`, `applicant`, `beneficiary`.
  - currency: `currency` → `currency` + `currency_code`.
- Add derived boolean computation helper. From existing extracted fields:
  - `lc.partial_shipments_permitted = (lc.partial_shipments == "ALLOWED")`
  - `lc.transhipment_prohibited = (lc.transshipment == "NOT ALLOWED")`
  - `lc.irrevocable = (lc.form_of_documentary_credit in {"IRREVOCABLE", ...})`
  - `lc.subject_to_ucp = ("UCP" in lc.applicable_rules)`
  - `lc.is_transferred = (lc.form_of_documentary_credit contains "TRANSFER")`
  - `bill_of_lading.on_board_notation_present = (bool(bl.on_board_date) or "ON BOARD" in bl text)`
  - `bill_of_lading.full_set_required = True` (LC 46A #2 says "FULL SET" — derive from LC or hardcode)
  - `bill_of_lading.transhipment_allowed = not lc.transhipment_prohibited`

Full path inventory (LC / invoice / BL / insurance / credit) is in `project_rulhub_payload_audit_2026_04_17_evening.md`. Emit every one you can derive. Null-leave the rest (null==null silent-pass bug works in our favor for fields we can't compute).

### Commit 2: Raw response logging

File: `apps/api/app/services/rulhub_client.py` `validate_document_set`.

Add `logger.info("RulHub raw response: %s", json.dumps(result, default=str)[:5000])` right before returning. We need to SEE the full response.

Key unknown: the RulHub validation_logs showed `70 discrepancies` on a 06:51 crossdoc call but trdrhub UI showed 0. Either the 70 was a different tenant/call, OR my `_normalize_rulhub_finding` is eating them. Raw log will tell us.

### Commit 3: Live test + cross-check

Deploy. Run IDEAL SAMPLE via Playwright. Grep logs:
```bash
render logs -r srv-d41dio8dl3ps73db8gpg --limit 200 --text "RulHub raw response,RulHub /v1/validate/set"
```

Look for:
- `rules_checked: N` — target N ≥ 50 (some rules firing).
- Actual discrepancy count and content.
- Cross-check each surviving finding against raw PDFs (per `feedback_cross_check_findings_against_docs.md`).

## Definition of done

- IDEAL SAMPLE returns ≥ 4 legitimate findings, each cited to a specific RulHub rule_id.
- Findings include at least 2 of: invoice arithmetic mismatch, port literal conflict (Chittagong vs Chattogram), missing CLEAN ON-BOARD, missing invoice/COO dates.
- Compliance score reflects rule evaluation (not "insufficient_data masquerading as pass").
- No duplicate findings across `lc`/`credit` or `bl`/`bill_of_lading` submissions — dedupe in `_normalize_rulhub_finding` if needed.

## Rules (still in force)

- **Do not rebuild RulHub inside trdrhub.** `apps/api/app/services/validation/` local validators are dormant behind `USE_RULHUB_API` gates. Don't re-enable them.
- **Do not touch** `J:\Enso Intelligence\ICC Rule Engine\` — separate Claude workspace. ISBP 821 backfill is Ripon's / RulHub-Claude's job.
- **Do not prompt-engineer to IDEAL SAMPLE.** All field names + derivations must be general — any LC with similar structure should benefit.
- **Do not re-introduce an LLM enforcement layer.** C2-spine was reverted for a reason. Read `project_session_2026_04_17_rulhub_pivot.md` "failure modes" section.
- **Keep C1 kill switches** (`5bcc50a3`). Don't re-enable local doc_matcher / ai_validator / CrossDocValidator / L3 anomaly review.

## First commands

```bash
cd H:\.openclaw\workspace\trdrhub.com
git log --oneline -5
git status --short

# Read the audit memory FIRST
cat "C:\Users\User\.claude\projects\H---openclaw-workspace-trdrhub-com\memory\project_rulhub_payload_audit_2026_04_17_evening.md"

# Then open the target file
code apps/api/app/routers/validation/validation_execution.py
# Navigate to the `_FIELD_ALIASES_FOR_RULHUB` block around line 1639.
```

Do NOT edit code until you've read the audit memory. The spec is already written there — don't reinvent it.

## Credentials + test infra

- Supabase login: `imran@iec.com` / `ripc0722`
- Upload URL: https://trdrhub.com/lcopilot/exporter-dashboard?section=upload
- IDEAL SAMPLE docs: `.playwright-mcp/ideal-sample/*.pdf` (LC + 7 supporting)
- Render backend: `srv-d41dio8dl3ps73db8gpg` (trdrhub-api)
- Render RulHub: `srv-d35ovhndiees738g995g` (icc-rule-engine — READ-ONLY from this session)
