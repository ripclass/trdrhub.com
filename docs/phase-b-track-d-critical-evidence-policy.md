# Phase B / Track D — Critical Evidence Enforcement (Extraction Layer)

## Scope
Applied in `apps/api/app/services/extraction/lc_baseline.py` during extraction arbitration/output shaping (not verdict scoring).

## Enforcement rules
1. **Critical fields require evidence span**
   - A critical field is accepted only when evidence is attached (`evidence_text`, `evidence_page`, or `evidence_location`) or recoverable as an OCR snippet.

2. **OCR-present + LLM-missed -> retry candidate**
   - If a critical field value is missing but `_field_diagnostics.<field>.valid_candidates` contains a candidate, the baseline attempts an `ocr_retry_candidate` fill.
   - Candidate is accepted only when evidence can be attached.

3. **LLM-present without evidence -> downgrade/reject**
   - If a critical value is present but evidence cannot be found, status is downgraded to `invalid` and value is cleared.

## Deterministic reason coding
For evidence-enforcement failures, missing reason is deterministic:
- `parser_failed` (status `invalid`) when critical value/candidate cannot be evidence-backed.

Existing deterministic mappings remain unchanged for:
- `missing_in_source`
- `conflict_detected`
