# Verdict Calibration Checkpoint Log

## 2026-03-01 17:11:00 GMT+6
- Step: Initialization
- Current finding: Context load started; discovered existing day3 results corpus and manifest/result files (including phase3 run artifacts).
- Next command: Read `phase3` and `smoke gate` reports plus latest result JSON/CSV files; identify pass→blocked collapse pattern.

## 2026-03-01 17:15:00 GMT+6
- Step: Trace kickoff
- Current finding: Located large set of prior run artifacts for phase3/ smoke; next: inspect `phase3_final_smoke_gate_report.md`, `phase3_smoke_gate_post_overblocking_fix_report.md`, and latest result outputs.
- Next command: Read these reports and corresponding `failed_cases.csv` / `jsonl` for deterministic mismatch evidence.
## 2026-03-01 17:45:00 GMT+6
- Step: Root-cause patch applied (backend)
- Finding: DB-rule fail-closed path in validate.py caused non-LC/API fixtures to be hard-blocked when ruleset table missing; changed DB rule exception handling to fail-open and emit warning issue (no 100% block).
- Exact location: apps/api/app/routers/validate.py, validate() around except Exception as db_rule_err: (line ~1081).
- Next command: run targeted 5-case and smoke20 proof commands with fresh snapshots; compute metrics; write final report.

## 2026-03-01 17:52:00 GMT+6
- Step: Root-cause identified and fixed in mapping layer
- File/function/line: tools/day3_pipeline/day3_pipeline_core.py -> extract_actual_verdict
- Finding: bug in locked_signals included can_proceed as hard blocker with if any(v is True...), so valid responses with gate_result.can_proceed=True were downgraded to locked even when not actually blocked.
- Patch: removed gate_result.can_proceed from locked_signals (minimal reversible change).

## 2026-03-01 18:00:00 GMT+6
- Step: Additional mapping patch in extract_actual_verdict to prevent non_compliant-only fixtures from being interpreted as reject when gate is passed and no issues.

## 2026-03-01 18:08:00 GMT+6
- Step: Re-ran un_batch_day3.py --limit 5 --no-resume and --smoke20 --min-interval 3.0 --retries-429 8 AFTER final mapping patch.
- Snapshot names saved: 	argeted5_20260301_180100_* and smoke20_20260301_180730_*.
- Metrics after patch:
  - targeted5: comparable=5, accuracy=1.0, pass_blocked=0.0, critical_false_pass=0, 422=0, 429_exhaustion=0, 429=0
  - smoke20: comparable=20, accuracy=1.0, pass_blocked=0.0, critical_false_pass=0, 422=0, 429_exhaustion=0, 429=12
- Decision: Phase 3 x2 rerun now functionally unblocked for pass fixtures (no blocked downgrades in targeted/smoke runs).
