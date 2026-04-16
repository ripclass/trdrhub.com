# Next Session Prompt — Fix the 4 validator false-positive clusters

Paste or summarize this to kick off the next Claude session. Self-contained; assumes zero memory of the 2026-04-16 session.

---

## Context

Previous session (2026-04-16) shipped 19 commits hardening the **extraction** side: ISO 20022 extractor fixed (0/9 → 9/9 currency), the 4-tab verdict view restored (+60/-937 lines), extraction-core's illegitimate format validators removed, and 10 Bangladesh-hardcoded sites globalized. **Don't redo any of that.**

Then a browser test against the IDEAL SAMPLE MT700 LC package at `F:\New Download\LC Copies\Synthetic\Export LC\IDEAL SAMPLE\` (8 docs — LC, Invoice, BL, Packing List, COO, Insurance, Inspection, Beneficiary Cert) produced:

- `final_verdict: review`
- 12 findings (0 critical, 3 major, 9 advisory)
- 31% compliance score

**After cross-checking each finding against raw document text: 2/12 legitimate, 10/12 false positives.** An operator looking at this output would dismiss the tool. Fix this before anything else.

## The #1 priority

Fix the 4 validator false-positive clusters documented in `memory/project_validator_false_positive_clusters.md`. Each cluster is self-contained; any can ship independently.

Read these memory files first:

1. `project_validator_false_positive_clusters.md` — THE target. Full cross-check matrix + root-cause groupings + suggested fix order.
2. `feedback_cross_check_findings_against_docs.md` — how to verify your fix (don't trust summary metrics).
3. `feedback_extraction_is_blind_transcriber.md` — don't accidentally put format validators back at extraction layer.
4. `project_session_2026_04_16_full.md` — what shipped yesterday so you don't re-do it.
5. `arch_extraction_contract.md` + `feedback_extraction_gotchas.md` — load-bearing contracts.

## Fix order (recommended)

### Cluster A — "No commercial invoice available to verify" (4 findings collapsed into one fix)

Findings #9, #10, #11, #12 from the IDEAL SAMPLE all say the same "Found" text:

```
No commercial invoice available to verify
```

But the invoice IS available and extracted with 14 fields (LC No, PO number, BIN, TIN, HS codes, quantities, prices, total). One lookup bug producing 4 duplicate false positives.

**Investigation:**
```bash
# Find where the phrase comes from
grep -rn "No commercial invoice available" apps/api/app/services/validation/
```

Likely a validator is looking for a document with key `commercial_invoice` in a dict, but the extracted docs collection is keyed differently (e.g., doc_type field `invoice` vs `commercial_invoice`, or docs list vs dict). Or the validator reads from a different part of the context than where the extraction results land.

**One fix → 4 findings eliminated.** Fastest win and sets the pattern for the others.

### Cluster C — Port of loading alias check (1 MAJOR finding)

Finding #7: LC says `44E: CHITTAGONG SEA PORT, BANGLADESH`. BL says `Port of Loading: Chattogram, Bangladesh`. Same city. "Chattogram" is the official current Bangladeshi name for what was called "Chittagong." Commit `2ef8a17c` yesterday added `BDCGP: ["Chattogram", "Chitagong", "CTG", "Chittagong Port"]` to `apps/api/app/reference_data/ports.py`, but the crossdoc port-of-loading check does a raw string compare instead of using the registry.

**Investigation:**
```bash
grep -rn "port_of_loading" apps/api/app/services/validation/crossdoc_validator.py
```

Find the check (probably `_check_port_of_loading` or similar). Replace the raw comparison with a normalized comparison using the port registry:
- Look up both LC port and BL port in the registry
- If they resolve to the same UN/LOCODE, they're equivalent

This fix alone removes a MAJOR-severity false positive from the verdict page.

### Cluster B — "Not found in document" when field IS in document (3 findings)

Findings #3, #4, #5. Validator says field is missing but it's in the raw text:

| Finding | Field | Document | Actual text |
|---|---|---|---|
| #3 | `freight_status` | Bill of Lading | `Freight: Collect` |
| #4 | `quantity` | Inspection Certificate | `30,000 PCS / 12,000 PCS / 8,500 PCS` |
| #5 | `buyer_purchase_order_number` | Beneficiary Certificate | `Purchase Order No.: GBE-44592` |

Field-name drift between what validator asks for and what extractor labeled. The extractor likely wrote `freight` / `quantity` (or `total_quantity`) / `po_number` / `purchase_order_no`, and the validator does raw dict access with the canonical name instead of going through alias resolution.

**Investigation:**
```bash
# Find the checks
grep -rn 'freight_status\|"quantity"\|buyer_purchase_order_number' apps/api/app/services/validation/crossdoc_validator.py

# Look at how they access the field value
```

**Fix:** Replace raw dict lookup (e.g., `doc.get("freight_status")`) with alias-aware lookup via `doc_matcher._find_field_value(doc_fields, "freight_status")` — that function already walks `_CANONICAL_ALIASES`. Or import the alias resolver.

Related open task: centralize field aliases (currently split across `launch_pipeline._FIELD_NAME_ALIASES`, `ExtractionReview.FIELD_ALIAS_MAP`, `doc_matcher._CANONICAL_ALIASES`). If you're already in this area, consider doing the centralization at the same time — one source of truth for all alias consumers.

### Cluster D — Insurance coverage math + Incoterm awareness (1 MAJOR finding)

Finding #1: "Insurance Coverage Below LC Requirement"
- EXPECTED: `>= 914,695.05 (110% of LC amount)`
- FOUND: `110.00`
- LC amount: USD 458,750.00

**Three distinct bugs:**

1. **"110" treated as dollars.** Insurance Certificate has `Coverage: 110% of invoice value`. Extractor pulled `110` (number). Validator compared `110 < 914,695 → fail`. But the value is a *percentage*, not dollars. The check should compare percentage-to-percentage (`110 >= 110 → pass`) OR compute the dollar coverage (`invoice * 110% = 504,625`) and compare to the insurance dollar amount.

2. **Math is wrong.** 110% of 458,750 = **504,625**, not 914,695.05. The expected figure appears to be ~200% of LC. Either the validator is doubling (maybe for CIF safety margin?) or there's a plain calculation bug. Trace the formula.

3. **FOB context ignored.** LC Incoterm is `FOB CHITTAGONG`. Under FOB, the buyer arranges insurance, not the seller. Insurance Certificate explicitly says `Incoterm: FOB (Buyer Covers Insurance)` and `Insurer: Buyer-arranged coverage`. Per UCP600 Art 28, insurance is only required when the credit calls for it. This check should be skipped entirely (or downgraded to advisory) when the LC Incoterm doesn't require seller-arranged insurance.

**Investigation:**
```bash
grep -rn "Insurance Coverage Below" apps/api/app/services/validation/
```

Find `_check_insurance_coverage` or similar. Fix in layers: (a) percentage-aware parsing, (b) correct the 110% math base, (c) respect Incoterm context.

## Test infrastructure

### Credentials (unchanged)
- **Supabase login:** `imran@iec.com` / `ripc0722`
- **API base:** `https://api.trdrhub.com`
- **Upload route:** `https://trdrhub.com/lcopilot/exporter-dashboard?section=upload`
- **Supabase JWT TTL:** 60 minutes. User will paste fresh when needed.

### IDEAL SAMPLE docs

Copied to `.playwright-mcp/ideal-sample/` for Playwright sandbox access. Source at `F:\New Download\LC Copies\Synthetic\Export LC\IDEAL SAMPLE\`. Use this for regression testing after each cluster fix — it's the known-clean 8-doc package that should produce a near-pass verdict.

### Browser test via Playwright

Playwright works for most of the flow (login, upload, extract, validate). See `feedback_playwright_cloudflare_block.md` — the 2026-04-15 "all blocked" note is outdated; as of 2026-04-16 only `/auth/me` and SSE streams are blocked. Main user flow works.

### curl orchestration for stress matrix

`reference_curl_validate_orchestration.md` + `project_session_2026_04_15_afternoon.md` have the recipes. The 27-set stress corpus at `apps/api/tests/stress_corpus/` is gitignored but ready for re-runs.

### Render

- `trdrhub-api` = `srv-d41dio8dl3ps73db8gpg` (FastAPI backend)
- `icc-rule-engine` = `srv-d35ovhndiees738g995g` (RulHub — READ only, don't deploy per `feedback_scope_trdrhub_only.md`)

Deploy monitor command:
```bash
render deploys list srv-d41dio8dl3ps73db8gpg -o json | python -c "import sys,json; d=json.load(sys.stdin)[0]; print(d.get('status'), d.get('commit',{}).get('message','')[:60])"
```

## Definition of done for the session

After fixing the 4 clusters, re-run the IDEAL SAMPLE in Playwright and cross-check the findings. Target:

- Findings drop from 12 → ≤3
- Verdict stays `review` or improves to `pass`
- Compliance score improves from 31% → ≥80%
- **Every remaining finding cross-checks as legitimate** per `feedback_cross_check_findings_against_docs.md`
- No MAJOR severity false positives remain

If any cluster fix introduces regressions on the Turkey-ISO stress corpus, roll it back and investigate.

## Execution style reminders

- **Do, don't ask.** Ship commits fast as long as they're tested. Ripon is fine with a commit cadence.
- **Cross-check findings against raw docs** before claiming verification. Don't trust summary metrics (see `feedback_cross_check_findings_against_docs.md`).
- **Extraction is a blind transcriber** — don't accidentally put format validators back in when fixing the validator (see `feedback_extraction_is_blind_transcriber.md`).
- **Trdrhub only.** If rulhub needs a change, surface it and ask the user to relay to rulhub Claude.
- **No vague answers.** Trace the code. Never "most likely" without file:line proof.

## What NOT to touch

- **Extraction side** — just hardened across 8 commits. ISO 20022, blind-transcriber contract, global BIN/TIN, port registry. Don't regress.
- **Frozen commits `0368a97a` → `8825118a`** — parallel vision LLM, missing-doc dialog, incremental extraction, Documents Required list.
- **Rulhub / icc-rule-engine code.**
- **Bangladesh de-hardcoding fixes** (residency, currency, SSLCommerz, doc generator, port normalization, locale profiles, pricing FX, LC clause library) — if you find another BD reference, check it's not legitimate (BD is a real country).

## First command to run

```bash
grep -rn "No commercial invoice available" apps/api/app/services/validation/
```

Start with Cluster A. Fast win, sets the pattern.
