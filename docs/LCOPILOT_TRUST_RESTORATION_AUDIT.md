# LCopilot Trust Restoration Audit (M1–M5)

## Scope
Focused fixes for extraction/compliance semantic clarity, contradiction removal, and audit-grade explanations.

## Before → After Behavior Matrix

- **Status semantics**
  - Before: extraction/compliance labels mixed (`error`, `warning`, `issues`) with ambiguous UI text.
  - After: canonical domains enforced:
    - `extraction_status`: `success|partial|failed`
    - `compliance_status`: `clean|warning|reject`
    - `pipeline_verification_status`: `VERIFIED|UNVERIFIED`

- **Document cards**
  - Before: labels like `3 Errors` conflated extraction failures with compliance findings.
  - After: explicit split:
    - extraction badge (`Extraction Success|Partial|Failed`)
    - compliance badge (`N Compliance Issues`)

- **View Details drawer**
  - Before: no clear extraction-vs-compliance separation.
  - After: two explicit sections:
    - Extraction Quality (status/confidence/failed reason)
    - Compliance Findings (status/issue count)

- **Blocked vs allowed semantics**
  - Before: customs/bank wording could conflict with verdict state.
  - After: decisions derive from canonical block conditions (`final_verdict`, `compliance_status`, `pipeline_verification_status`) with `Blocked|Allowed|Review Required` wording.

- **Issue transparency**
  - Before: issue cards lacked concise audit explanation structure.
  - After: each issue includes:
    - `issue_type`
    - `why_flagged`
    - `evidence_fields`
    - `required_user_action`
  - Reject path now includes explicit `blocking_reasons`.

## What users now see (top block / documents / issues / customs)

- **Top block:** bank/customs decisions now reflect block-vs-allow state consistently.
- **Documents tab:** extraction status and compliance issue counts are presented as separate concepts.
- **Issues tab:** each issue includes concise explanation metadata for why it was flagged and what action is required.
- **Customs readiness:** readiness language no longer implies allowance when pipeline is unverified or reject conditions exist.

## Reliability checks run

- `python -m py_compile apps/api/app/routers/validation/semantics.py apps/api/app/routers/validation/response_builder.py apps/api/app/routers/validate.py` ✅
- `python -m pytest -q apps/api/tests/option_e_document_status_contract_test.py apps/api/tests/day1_p0_failclosed_provenance_test.py` ⚠️ blocked during collection due local SQLAlchemy/Python 3.13 compatibility assertion in environment.
- `npx vitest run apps/web/src/__tests__/resultsMapper.test.ts` ⚠️ blocked due local alias resolution/config mismatch when run from repo root.

## Known remaining risks

1. Full backend regression run blocked by local env dependency mismatch (SQLAlchemy typing assertion on current Python build).
2. Frontend isolated test invocation needs project-local Vitest alias context.
3. Canonical semantics are enforced in backend and mapper path; additional legacy consumers should be migrated to the same contract to eliminate drift.
