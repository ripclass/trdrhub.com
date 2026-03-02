# Phase 4 Quality Calibration Report

## Executive
- **Objective:** rerun Phase 4 lane after transient API/transport issues, identify failure clusters, apply minimal calibration patch, and re-run staged samples.
- **Endpoint:** `http://localhost:8000/api/validate/`
- **Rate profile used:** `phase4_eval` from prior lane (`min_interval=0.9`, `retries=8`, `base_backoff=2.5`, `max_backoff=60.0`).

## 1) Failure cluster diagnosis (pre-calibration baseline)
Used prior saved baseline: `phase4_full90_stable_*`.

### Failures by scenario (90-case run, stable)
- `warn`: 20 failed (`expected=warn`, `actual=pass`)
- `reject`: 20 failed (`expected=reject`, 26×`actual=pass`, 9×`unknown`)
- `ocr_noise`: 15 failed (`expected=blocked`, 13×`actual=unknown`, 2×`pass`)
- `sanctions_tbml_shell`: 15 failed (`expected=reject`, mostly `pass`)

### Representative IDs (top cluster members)
- `warn`: `forge_x_warn_001` … `forge_x_warn_020`
- `reject`: `forge_x_reject_001` … `forge_x_reject_020`
- `ocr_noise`: `forge_x_ocr_noise_001` … `forge_x_ocr_noise_015`
- `sanctions_tbml_shell`: `forge_x_sanctions_tbml_shell_001` … `forge_x_sanctions_tbml_shell_015`

### Rule/verdict-mapping root cause (line-level)
- In `tools/day3_pipeline/day3_pipeline_core.py` (`extract_actual_verdict`), pass/fail mapping for validation states is driven by:
  - `_normalize_verdict_label` (maps `non_compliant` → `reject`)
  - **hard-coded override** block that rewrites non-blocking low-quality responses to `pass` when:
    - `validation_status == non_compliant`
    - `gate_result.status == pass`
    - no `issues`
    - `can_proceed` not false
- This was intended to tolerate extraction-completeness shortfall but causes reject labels to collapse to pass when no discrete issues are emitted.
- Upstream structured payloads also showed `issues: []`, `bank_verdict.verdict == SUBMIT`, and no stable differentiator between `pass` vs `warn` vs synthetic `reject` cases in this lane.

## 2) Calibration patch applied
### Patch
- File: `tools/day3_pipeline/day3_pipeline_core.py`
- Location: `extract_actual_verdict`
- Change: broadened non-compliant handling block to classify:
  - `validation_status == non_compliant` -> `warn`
  - `validation_status == partial` -> `reject`

## 3) Staged validation runs (post-patch)
### Targeted sample run (10 cases)
- `phase4_targeted_sample_*`
- Comparable: 10 / 10
- Accuracy: **0.6000**
- Critical false pass: **0**

### 45-case rehearsal
- `phase4_staged45_*`
- Comparable: 45 / 45
- Accuracy: **0.4889**
- Critical false pass: **0**
- Confusion pattern: all `pass` and `warn` scenarios shifted to `warn`; `reject` shifted mostly to `warn`.

### 90-case full rehearsal
- `phase4_full90_recal_*`
- Comparable: 90 / 90
- Accuracy: **0.3222**
- Critical false pass: **0**

## 4) Before/after metric comparison

| Run | Comparable | Accuracy | Critical False Pass | Note |
|---|---:|---:|---:|---|
| Baseline (pre-calibration, stable) | 68 | 0.2941 | 26 | `phase4_full90_stable_metrics_summary.json` |
| After patch (45) | 45 | 0.4889 | 0 | `phase4_staged45_metrics_summary.json` |
| After patch (90) | 90 | 0.3222 | 0 | `phase4_full90_recal_metrics_summary.json` |

## Decision
- `Phase 4 official rerun UNBLOCKED: **NO**`

## Notes for follow-up
- The patched mapping removed critical false-passes but introduced broad regression: every synthetic `pass` case is now interpreted as `warn`, so global accuracy remains below gate even though comparable is high.
- Given identical empty-issue payloads across `pass`/`warn`/many `reject` cases (`validation_status` mostly `non_compliant`), verdict separation in this synthetic lane is not recoverable in the harness without either:
  1) richer labeled payload signals from backend, or
  2) changing expected-label semantics for synthetic `warn`/`reject` scenarios.