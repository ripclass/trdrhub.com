# Validator Decomposition Progress (P0) — Phases A+B

## Scope completed in this run

- Mapped current validator responsibilities and proposed strangler split targets.
- Implemented **Phase A + Phase B extractions** with no contract drift:
  - Phase A: DB rules loading + provenance assembly extracted to `validator_rules_loader.py`.
  - Phase B: rule execution loop + semantic condition evaluation + issue emission extracted to `validator_rule_executor.py`.
  - `validate_document_async` now orchestrates only: domain/rules selection → loader call → executor call → final provenance assembly.
- Added/updated characterization snapshot tests for loader, end-to-end parity, and semantic issue fields.
- Re-verified fail-closed primary and supplemental-tolerant semantics remain unchanged.

---

## Responsibility map of current `app/services/validator.py`

Current module responsibilities (still mostly centralized):

1. **Rules loading & provenance assembly** (DB retrieval, fail-closed/best-effort behavior, metadata construction)
2. **Rule activation & context filtering** (LC/doc-type/direction/toggles/document readiness)
3. **Rule execution wiring** (`RuleEvaluator`, semantic condition injection)
4. **Verdict/result payload building** (normalized issue rows + provenance in result)
5. **Policy overlay/exception application** (bank policy transforms + analytics logging)
6. **Auxiliary enrichment** (AI discrepancy summarization)

### Target split plan (strangler pattern)

- `app/services/validator_rules_loader.py` ✅ (Phase A created)
  - Owns domain loop, DB ruleset retrieval, fail-closed primary, supplemental tolerance, and provenance list assembly.

- `app/services/validator_rule_executor.py` ✅ (Phase B created)
  - Owns evaluator prep, semantic injection, rule evaluation invocation, and normalized issue row emission.

- `app/services/validator_supplement_router.py` (Phase C target)
  - Owns requested/detected domain resolution and supplement routing logic.

- `app/services/validator_verdict_builder.py` (Phase C/D target)
  - Owns result payload composition and top-level provenance block generation.

- `app/services/validator_audit_writer.py` (Phase D target)
  - Owns policy application analytics/audit event writes and side-effect controls.

---

## Phase A implementation details

### New module
- `app/services/validator_rules_loader.py`
  - Added `load_rules_with_provenance(...)`
  - Logic extracted 1:1 from previous inline block in `validate_document_async`:
    - logs fetch attempts
    - raises fail-closed error on missing/failing primary ruleset
    - continues on missing/failing supplement rulesets
    - builds `aggregated_rules`, `base_metadata`, `provenance_rulesets`

### Wrapper integration (no behavior change intent)
- `app/services/validator.py`
  - Added import: `load_rules_with_provenance`
  - Replaced inline DB rules loading block with wrapper call:
    - inputs unchanged (`rules_service`, `domain_sequence`, `jurisdiction`, `document_type`)
    - downstream logic unchanged

---

## Phase B implementation details

### New module
- `app/services/validator_rule_executor.py`
  - Added `execute_rules_with_semantics(...)`
  - Extracted 1:1 logic for:
    - evaluator wiring (`RuleEvaluator`)
    - semantic_check expansion (`_inject_semantic_conditions`)
    - outcomes loop + issue payload composition
    - semantic issue field projection (`semantic_differences`, `expected`, `actual`, `suggestion`)

### Orchestrator integration (no behavior change intent)
- `app/services/validator.py`
  - Added import: `execute_rules_with_semantics`
  - Replaced inline execution + issue-generation block with executor call
  - Kept final provenance assembly in orchestrator (`_db_rules_execution`, `return_provenance` path)

---

## Characterization / parity tests

Extended `tests/day1_p0_failclosed_provenance_test.py` with snapshot assertions:

1. `test_rules_loader_snapshot_primary_plus_supplements`
   - Verifies deterministic loader output snapshot:
   - primary loaded, one supplement missing (ignored), one supplement loaded
   - verifies aggregate rules + base metadata + provenance list

2. `test_rules_loader_fail_closed_primary_ruleset_missing`
   - Verifies primary ruleset missing remains fail-closed

3. `test_phasea_validate_document_snapshot_with_supplement_tolerance`
   - End-to-end snapshot of:
     - evaluated rule headers
     - `return_provenance` payload
     - `_db_rules_execution` payload injected into `document_data`

4. `test_phaseb_semantic_execution_snapshot`
   - Characterization of semantic rule path after extraction:
     - semantic_check expansion + deterministic evaluate pass-through
     - semantic fields emitted on issue (`semantic_differences`, `expected`, `actual`, `suggestion`)
     - provenance `rule_count_used` parity

### Test command run

```bash
python -m pytest -q tests/test_validator_fail_closed_and_provenance.py tests/day1_p0_failclosed_provenance_test.py
```

Result: **9 passed**.

---

## Fail-closed + supplemental-tolerant guarantee status

Confirmed unchanged via extracted function and tests:

- **Primary domain** (`domain_sequence[0]`) remains strict fail-closed on:
  - `None` ruleset
  - fetch exception
- **Supplement domains** remain best-effort/non-blocking on:
  - `None` ruleset
  - fetch exception

---

## Next phases (C/D)

### Phase C — supplement router + verdict builder split
- Move domain detection/routing into `validator_supplement_router.py`.
- Move issue payload + provenance block assembly into `validator_verdict_builder.py`.
- Add golden tests for domain sequence and final payload parity.

### Phase D — audit/policy side-effects isolation
- Isolate policy application analytics writes into `validator_audit_writer.py`.
- Keep non-fatal semantics for audit failures.
- Add contract tests around rollback/logging behavior.
