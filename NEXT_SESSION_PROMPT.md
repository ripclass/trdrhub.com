# Next Session Prompt — verify AI Examiner live after OpenRouter top-up

Paste to start a fresh Claude session. Self-contained, assumes zero memory of 2026-04-17 evening.

---

## TL;DR (30 seconds)

- The validation pipeline's middle layer is now an **AI Examiner** — a constrained Sonnet 4.6 call that reads the full LC + all supporting docs and emits findings with verbatim-quote citations.
- Live on Render as of commit **`4febcd1c`**.
- Prototype (`scripts/examiner_prototype.py`) validated the design — surfaced 7 findings (5 real) on IDEAL SAMPLE, 0 hallucinated citations, 0 self-contradictions.
- **Blocked on OpenRouter credit top-up.** Ripon ran out mid-session. When topped up, re-run IDEAL SAMPLE and confirm the 5-7 real findings surface.

## Read first (5 min, in this order)

1. `memory/project_session_2026_04_17_ai_examiner.md` — ★★ the full story of why hardcoded checks were wrong and the examiner is right
2. `memory/feedback_no_hardcoded_validators.md` — ★ the rule going forward
3. `memory/reference_ai_examiner_design.md` — ★ how `run_ai_examiner` works + debugging cheatsheet
4. `CLAUDE.md` "Current Focus" section — live pipeline state
5. `scripts/examiner_prototype.py` — standalone replica for prompt iteration

## Live state

- master tip: `4febcd1c`
- Render deploy: `srv-d41dio8dl3ps73db8gpg` (trdrhub-api) — live
- RulHub API: live (`USE_RULHUB_API=True` + `RULHUB_API_KEY` set)
- OpenRouter: **credits out as of 2026-04-17 ~15:30 UTC**. Examiner returns empty until topped up. Arithmetic backstop still produces the invoice $61,700 finding.

## Architecture as live

```
run_ai_validation()
  ├─ Step 3: run_ai_examiner(lc_text, docs_by_type)      ← primary
  │     └─ Sonnet 4.6 via OpenRouter (model_override)
  │     └─ Substring citation filter + self-contradict filter
  └─ Step 4: validate_invoice_arithmetic()               ← math backstop

Parallel: RulHub /v1/validate/set (generic UCP rules)

Downstream (validation_execution.py):
  ├─ Engine-error filter (drops RulHub "Unknown condition type" noise)
  ├─ Auto-confirm pre-pass (skips LLM on concrete value mismatches)
  └─ Opus veto (L3) — final arbiter, drops/confirms/modifies
```

## First action in the new session

1. **Verify OpenRouter credits**. If Ripon has topped up:
   ```bash
   # Refresh auth
   curl -sX POST "https://nnmmhgnriisfsncphipd.supabase.co/auth/v1/token?grant_type=password" \
     -H "apikey: sb_publishable_db40L4wNiQX0jOTCRJi-8g_9p-PWmN3" \
     -H "Content-Type: application/json" \
     -d '{"email":"imran@iec.com","password":"ripc0722"}' \
     -o /tmp/auth.json

   # Run IDEAL SAMPLE
   # (full recipe in memory/reference_curl_validate_orchestration.md)
   ```

2. **Grep Render logs** for examiner output:
   ```bash
   render logs -r srv-d41dio8dl3ps73db8gpg --text "examiner" -o text --limit 50
   ```

   Expected markers:
   - `Step 3: AI examiner — N doc types have raw_text: [...]` (should show ≥ 6 types)
   - `AI examiner: M raw → K survivors (dropped C citation + D contradiction)`
   - `AI examiner overall: <one-sentence summary>`

## Expected findings on IDEAL SAMPLE (from prototype)

If the pipeline is healthy, UI should show ~5-7 findings. Prototype produced these verbatim:

| # | Severity | Doc | Finding |
|---|---|---|---|
| 1 | critical | invoice | Invoice total does not match sum of line items ($397,050 vs $458,750, gap $61,700) |
| 2 | critical | invoice | Invoice not signed as required |
| 3 | critical | bill_of_lading | Bill of Lading missing CLEAN ON-BOARD notation |
| 4 | critical | inspection_certificate | Inspection certificate shipment date (2026-04-20) conflicts with BL shipment date (2026-09-24) |
| 5 | major | packing_list | Packing list lacks carton-wise breakdown of sizes |
| 6 | minor | insurance_certificate | Insurance certificate extraneous under FOB |
| 7 | major (over-strict, veto may drop) | invoice | Unit price per piece labeling |

If UI shows 0 or 1 findings after credit top-up → examiner not firing. Check logs for error type. Most likely causes:
- `AI examiner failed (type=HTTPError, ...)` — model id or credits
- `Step 3: AI examiner — 0 doc types have raw_text` — extraction pipeline changed, `_merged_doc_data` broken

## Rules (still in force from prior sessions)

- **No hardcoded discrepancy validators.** Add to the examiner prompt or filters, not new Python functions. Only exception is `validate_invoice_arithmetic` (math backstop). See `memory/feedback_no_hardcoded_validators.md`.
- **Do not touch `J:\Enso Intelligence\ICC Rule Engine\`** — separate Claude workspace. If RulHub needs a new rule, surface to Ripon.
- **Do not skip the Opus veto when RulHub is on** (see reverted commit `c6e05d1c`). The veto is the final examiner, not a noise filter over LLM hallucinations.
- **Do not re-add LLM enforcement loops** (C2-spine pattern, reverted). The examiner is bounded by substring-verified evidence; don't unbound it.

## When examiner prompt needs tuning

Use the prototype — it's faster than redeploying.

```bash
cd H:/.openclaw/workspace/trdrhub.com
python scripts/examiner_prototype.py "anthropic/claude-sonnet-4.6"
```

Prompt lives in `apps/api/app/services/validation/ai_validator.py` as `_EXAMINER_SYSTEM_PROMPT`. Filters in `_verify_examiner_finding` + `_EXAMINER_SELF_CONTRADICTING_PHRASES`. Model pinned via `AI_EXAMINER_MODEL` env.

## What NOT to do

- Don't write `validate_X_Y()` Python functions for specific discrepancy classes.
- Don't widen the auto-confirm pre-pass criteria (currently two-sided concrete value mismatches only — narrow by design).
- Don't skip the veto when USE_RULHUB_API=True.
- Don't fetch the RulHub repo or edit seed rules.

## Credentials + test infra

- Supabase login: `imran@iec.com` / `ripc0722`
- OpenRouter publishable key (extractable from bundle): `sb_publishable_db40L4wNiQX0jOTCRJi-8g_9p-PWmN3`
- IDEAL SAMPLE docs: `.playwright-mcp/ideal-sample/*.pdf` (LC + 7 supporting)
- Render service: `srv-d41dio8dl3ps73db8gpg` (trdrhub-api)
- Stress corpus: `apps/api/tests/stress_corpus/` (gitignored, 27 labeled sets)

## Today's commits (chronological)

Extraction: unchanged.

Payload alignment (morning 2026-04-17):
- `0a438978` `f66811a7` `1fb94792` `1d284fa0` `fe0bd036` — RulHub dual-prefix, `_name`/`_code` suffixes, derived booleans, canonical envelope
- `c6e05d1c` — reverted (skip-veto-when-RulHub-on)
- `5b999b1c` — veto restored + pre-veto engine-error filter

UI alignment (afternoon):
- `5cb8e79b` `949a9eda` — VerdictTab + Findings tab count consistency

Middle-AI + examiner (evening):
- `0efab19c` — middle AI unconditional + rule-based first-pass before Opus
- `de3483be` — AI findings actually reach Opus (dataclass coercion)
- `e737ee7e` — merged-data lookup for raw_text
- `11891fa1` — three hardcoded checks (invoice arith, BL clean-on-board, signature presence) — *partially superseded by examiner, invoice arithmetic kept as backstop*

AI Examiner ship:
- `c33ef01e` — primary ship
- `ff0d354c` — fix docs_by_type build + pin Sonnet 4.5
- `dd44ed2d` — correct model id to 4.6
- `4febcd1c` — raw_text via extraction_artifacts_v1 + richer error logs

## Summary of pipeline today

- 0 findings (start of day) → 70 findings after payload alignment → 2 after filters → 1 stuck at arithmetic (examiner blocked on credits)
- With credits restored: should surface 5-7 real findings in UI, verdict REJECT, correct bank_verdict summary
