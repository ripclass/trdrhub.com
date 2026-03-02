# Phase 4 Semantic Class-Separation Patch Report

## Scope
- Workspace: `H:\.openclaw\workspace\trdrhub.com`
- API endpoint: `DAY3_API_URL=http://localhost:8000/api/validate/`
- Focus: deterministic pass/warn/reject class signaling and evaluator consumption

## 1) Root-cause (line-level)

1. **Evaluator fallback ambiguity pre-fix**
   - `tools/day3_pipeline/day3_pipeline_core.py:371-437` (`extract_actual_verdict`)
   - Mapping relied on legacy fields (`final_verdict`, `verdict`, `status`, `validation_status`, issue severities) without a dedicated class signal.
   - For non-compliant payloads with low issue detail, this path could coerce multiple classes to similar outputs.

2. **API payload lacked a canonical class token**
   - `apps/api/app/routers/validate.py:1961-1962`
   - Before, responses exposed verdict-like values but no single, explicit machine-readable field that consistently distinguishes pass/warn/reject semantics (bank-level and blocked paths were mixed)

3. **No deterministic class propagation from API to QA evaluator**
   - `tools/day3_pipeline/day3_pipeline_core.py` did not check a dedicated marker in priority order before heuristic fallback, so class separation relied on best-effort rules and issue-severity inference.

## 2) Changes made (minimal, reversible)

### `apps/api/app/routers/validate.py`
- Added deterministic mapping helpers:
  - `_map_verdict_token_to_class`
  - `_resolve_bank_verdict_class`
  - `_build_verdict_signature`
- Added explicit marker payloads:
  - `_build_verdict_signature(..., verdict_class=...)` now emits:
    - `version`
    - `source`
    - `verdict_class` (`pass|warn|reject|blocked`)
    - `verdict_token`
    - `validation_status`
    - issue counts (`critical_count/major_count/minor_count`)
    - `compliance_score`, `reason`, `schema_version`
  - Injected into:
    - normal path: `structured_result["verdict_signature"]` (around line 1962)
    - blocked path: `_build_blocked_structured_result` (around 4052)
    - db-rules failure path: `_build_db_rules_blocked_structured_result` (around 4616)
- Added `bank_verdict`-local marker in `_build_bank_submission_verdict` with `verdict_class` and `verdict_signature`.

### `tools/day3_pipeline/day3_pipeline_core.py`
- Added deterministic marker resolver:
  - `def _normalize_bank_verdict(...)`
- Updated `extract_actual_verdict(...)` (line ~371) to consume markers first:
  1) `structured_result.verdict_signature`
  2) `structured_result.bank_verdict.verdict_signature`
  3) direct bank token fallback
  4) legacy fallback heuristics.

## 3) Validation runs executed (hardened phase4_eval profile)

- **Targeted sample (10 cases) / phase4_eval / no-resume**
- **45-case rehearsal / phase4_eval / no-resume**
- **90-case rehearsal / phase4_eval / no-resume**

### Targeted sample
- Before: `phase4_targeted_sample_metrics_summary.json`
  - comparable: 10
  - accuracy: 0.6
  - critical_false_pass: 0
- After: `phase4_semantic_targeted_metrics_after.json`
  - comparable: 10
  - accuracy: 0.6
  - critical_false_pass: 0

### 45-case
- Before: `phase4_staged45_metrics_summary.json`
  - comparable: 45
  - accuracy: 0.4889
  - critical_false_pass: 0
- After: `phase4_semantic_45_metrics_after.json`
  - comparable: 45
  - accuracy: 0.4889
  - critical_false_pass: 0

### 90-case
- Before: `phase4_full90_stable_metrics_summary.json`
  - comparable: 68
  - accuracy: 0.2941
  - critical_false_pass: 26
- After: `phase4_semantic_full90_metrics_after.json`
  - comparable: 90
  - accuracy: 0.3222
  - critical_false_pass: 0

## 4) Confusion-matrix delta (before → after)

### Targeted sample
- Before file: `phase4_targeted_sample_confusion_matrix.csv`
- After file: `phase4_semantic_targeted_confusion_matrix.csv`
- **No delta in counts across pass/warn/reject/blocked rows in this lane.**

### 45-case
- Before file: `phase4_staged45_confusion_matrix.csv`
- After file: `phase4_semantic_45_confusion_matrix.csv`
- **No delta in counts across pass/warn/reject/blocked rows in this lane.**

### 90-case
- Before: `phase4_full90_stable_confusion_matrix.csv`
- After: `phase4_semantic_full90_confusion_matrix.csv`
- Delta highlights:
  - `pass` row: `pass 20 → 0`, `warn 0 → 20`
  - `warn` row: `warn 0 → 20`, `pass 20 → 0`
  - `reject` row: `reject 26 → 9`, `warn 26 → 0` *(shift in diagonal vs off-diagonal due sample/response behavior changes in this run context)*
  - `blocked` row: `blocked 0 → 0`, `warn 2 → 0`, `reject 13 → 0`

## 5) Decision

**Phase 4 official rerun UNBLOCKED: NO**

## 6) Notes for main agent
- Reproducibility artifacts written:
  - `phase4_semantic_targeted_metrics_after.json`
  - `phase4_semantic_targeted_confusion_matrix.csv`
  - `phase4_semantic_45_metrics_after.json`
  - `phase4_semantic_45_confusion_matrix.csv`
  - `phase4_semantic_full90_metrics_after.json`
  - `phase4_semantic_full90_confusion_matrix.csv`
- This patch improves explicit class signaling surface area, but current 90-case accuracy indicates further model/API-path remediation is still required for full Phase 4 unblock.
