# Next Session Prompt — RulHub field-name coverage

Paste this (or summarize) to start the next Claude session. Self-contained, assumes zero memory of 2026-04-17.

---

## Read first (2 min)

Before anything else, read these five memory files — they contain the full picture and the load-bearing constraints:

1. `memory/project_rulhub_is_the_engine.md` — **★★ The architectural truth.** RulHub (api.rulhub.com, Ripon's separate product at `J:\Enso Intelligence\ICC Rule Engine`) has 7,804 rules. trdrhub is the consumer. Do not rebuild RulHub.
2. `memory/feedback_dont_reinvent_rulhub.md` — **★★ The rule.** Before writing any UCP/ISBP/crossdoc logic in `apps/api/app/services/validation/`, check RulHub first.
3. `memory/reference_rulhub_api_conventions.md` — **★ Contracts.** POST /v1/validate/set shape, rule-catalog doc-type prefixes (`lc`/`invoice`/`bl`/`coo`/`insurance`/`packing_list`/`draft`), field-name alignments.
4. `memory/project_session_2026_04_17_rulhub_pivot.md` — Yesterday's session log. What was committed, what was reverted, why.
5. `memory/feedback_scope_trdrhub_only.md` — **★ Scope rule.** Do NOT edit the ICC Rule Engine repo from this session. If RulHub needs a rule, surface it to Ripon.

## What's live right now

- `USE_RULHUB_API=True`, `RULHUB_API_KEY` set on Render (`srv-d41dio8dl3ps73db8gpg`).
- Local validators (`doc_matcher`, `crossdoc_validator`, `ai_validator`, `tiered_validation`) are **skipped when RulHub is on** — they remain as fallback for `USE_RULHUB_API=False`.
- `POST /v1/validate/set` is called with proper shape: `{"type": "lc"|"invoice"|"bl"|"coo"|"insurance"|"packing_list", "fields": {...}}`.
- Current tip of master: `5921c84e` (all 2026-04-17 commits merged; C2-spine reverted).

## The exact problem to solve

Live IDEAL SAMPLE run (all 8 docs — `.playwright-mcp/ideal-sample/*.pdf`) returns:
- Verdict: **COMPLIANT**
- Compliance: **77%**
- Findings: **0**
- Time: **~4 seconds**

This is misleading. The IDEAL SAMPLE has real discrepancies (missing invoice signature, missing invoice date, missing COO date, missing "FULL SET" / "CLEAN" BL notation, invoice arithmetic gap $61,700). RulHub isn't catching them because:

**Root cause**: Most RulHub rule conditions return `insufficient_data` (= silent pass) because the field names we send don't match the paths the rules reference. Examples from `J:\Enso Intelligence\ICC Rule Engine\Data\crossdoc\lcopilot_crossdoc_v3.json`:

- `CROSSDOC-BL-LC-7`: checks `bl.clauses` for "clean" — we don't emit `bl.clauses`
- `CROSSDOC-BL-LC-11`: `on_board_notation` — passes because we have date+vessel, but no visible finding
- `CROSSDOC-REQ-2`: `copy_count_compliance` — no way to count copies from a single PDF

## The work — 3 items in order

### 1. Field-name coverage audit (highest leverage)

For each doc type, enumerate every path in RulHub's rule catalog, then extend the alias map in `apps/api/app/routers/validation/validation_execution.py` (`_FIELD_ALIASES_FOR_RULHUB`) to map trdrhub's extraction canonical names → RulHub-expected names.

```bash
# From a new shell
python -c "
import json, glob
paths = set()
for f in glob.glob(r'J:/Enso Intelligence/ICC Rule Engine/Data/crossdoc/*.json') + \
         glob.glob(r'J:/Enso Intelligence/ICC Rule Engine/Data/icc_core/**/*.json', recursive=True):
    try:
        rules = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(rules, list): continue
    for r in rules:
        for c in (r.get('conditions') or []):
            for k in ('source','target','first_path','second_path','path','field','first','second'):
                v = c.get(k)
                if isinstance(v, str) and '.' in v:
                    paths.add(v)
by_prefix = {}
for p in paths:
    pre, _, f = p.partition('.')
    by_prefix.setdefault(pre, set()).add(f)
for pre in sorted(by_prefix):
    print(f'{pre}: {sorted(by_prefix[pre])}')
"
```

Compare each prefix's fields against:
- what trdrhub's extractors emit (see `apps/api/app/services/extraction/multimodal_document_extractor.py:DOC_TYPE_SCHEMAS`)
- what `_FIELD_ALIASES_FOR_RULHUB` already maps

Extend the alias map. Each missing mapping = rules that start firing.

### 2. Add extraction for fields we don't emit but RulHub checks

Examples the 2026-04-17 diagnosis surfaced (not exhaustive — see the audit output):
- `bl.clauses` — free-text block of BL marks / clauses / "CLEAN ON BOARD" statement. The multimodal BL schema needs a `clauses` field and prompt nudge.
- `invoice.date` — the extractor schema lists `invoice_date` but RulHub expects `date`. Either alias or add to schema.
- `coo.consignee`, `coo.form_type` — extraction currently emits exporter/importer but not consignee.
- `packing_list.shipping_marks`, `packing_list.issuer`.
- `bl.originals_issued` / `bl.originals_presented` — for copy-count rules.

Each one that gets emitted = more rules can evaluate.

### 3. Manual Review panel (UI)

For the ~4 discrepancy kinds RulHub genuinely doesn't cover (invoice arithmetic, packing-list size_breakdown, AZO/EU-US safety statements, "6 copies" physical counts), add a "Manual Review" section in `apps/web/src/pages/ExporterResults.tsx` that renders the raw 46A/47A clauses with per-clause pass/fail tick buttons. Compliance score aggregates RulHub findings + operator ticks.

This is the only place LC-specific logic lives — outside RulHub's universal rulebook.

## Verify-live loop (use every cycle)

```bash
# After each commit:
render deploys list srv-d41dio8dl3ps73db8gpg -o json | head -5
# Wait for "live", then:
render logs -r srv-d41dio8dl3ps73db8gpg --limit 200 --text "validate/set,RulHub"
```

Look for:
- `RulHub /v1/validate/set → N discrepancies + M crossdoc = N+M findings` — should grow as field coverage improves.
- 422 errors → payload shape regression (check `type` not `document_type`).
- 200 OK with 0 findings → field-name mismatch continuing. Increase coverage.

## Live test credentials + auth

- **Supabase login**: `imran@iec.com` / `ripc0722`
- **Main flow**: https://trdrhub.com/lcopilot/exporter-dashboard?section=upload
- **Playwright** works for main flow (auth, upload, extract, validate). `/auth/me` + SSE still ERR_ABORTED per `memory/feedback_playwright_cloudflare_block.md`.
- **IDEAL SAMPLE**: `.playwright-mcp/ideal-sample/*.pdf` (8 files — LC, Invoice, BL, Packing List, COO, Insurance, Inspection, Beneficiary Cert). Gold-standard clean MT700 package.

## Rules that MUST NOT be broken

1. **Do not add local validators for things RulHub already covers.** Check `J:\Enso Intelligence\ICC Rule Engine\CLAUDE.md` + the Data/ folder first.
2. **Do not edit the ICC Rule Engine repo** — separate workspace. Surface needs to Ripon.
3. **Do not re-enable the local engines** (they're behind `USE_RULHUB_API` gates). Do not revert C1 (`5bcc50a3`).
4. **Do not reintroduce any LLM enforcement layer** — C2-spine was reverted for a reason. Read `memory/project_session_2026_04_17_rulhub_pivot.md` failure-modes section.
5. **Do not prompt-engineer against one set.** If you find yourself writing "when LC says X, handle Y" for the IDEAL SAMPLE, stop. Ripon catches this every time.

## Definition of done for this session

- Field-name audit done, `_FIELD_ALIASES_FOR_RULHUB` extended.
- Extraction additions for the top ~5 missing fields RulHub references.
- Live IDEAL SAMPLE returns **N ≥ 4 findings, all clause-cited, cross-checked against raw PDFs as legitimate.** Compliance score reflects actual rule-evaluation coverage (not "insufficient_data masquerading as pass").
- Manual Review panel either built OR explicitly deferred with a written plan.

If you hit 4+ legitimate findings with 0 false positives, that's launchable. The regression harness (20 labeled packages) is the next milestone after that.

## First commands to run

```bash
cd H:\.openclaw\workspace\trdrhub.com
git log --oneline -8
git status --short
# Then run the field-path audit command above.
# Then open memory/reference_rulhub_api_conventions.md + project_rulhub_is_the_engine.md.
```

Don't touch validation_execution.py or rulhub_client.py until you've read both memory files.
