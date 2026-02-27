# Validator Decomposition Progress (P0) — Phases A+B+C+D

## Scope completed in this run

- Mapped current validator responsibilities and proposed strangler split targets.
- Implemented **Phase A + Phase B + Phase C extractions** with no contract drift:
  - Phase A: DB rules loading + provenance assembly extracted to `validator_rules_loader.py`.
  - Phase B: rule execution loop + semantic condition evaluation extracted to `validator_rule_executor.py`.
  - Phase C: supplement/domain routing extracted to `validator_supplement_router.py`; verdict/result payload + provenance construction extracted to `validator_verdict_builder.py`.
  - `validate_document_async` now orchestrates: router → loader → activation → executor → verdict builder.
- Added/updated characterization snapshot tests for loader, router/verdict parity, end-to-end parity, and semantic issue fields.
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

- `app/services/validator_supplement_router.py` ✅ (Phase C created)
  - Owns requested/detected domain resolution and supplement routing logic.

- `app/services/validator_verdict_builder.py` ✅ (Phase C created)
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

## Phase C implementation details

### New modules
- `app/services/validator_supplement_router.py`
  - Added `resolve_domain_sequence(...)` and `detect_icc_ruleset_domains(...)`.
  - Preserves sequencing semantics:
    - explicit `domain` remains primary when provided
    - detected ICC supplements are additive
    - explicit `supplement_domains` are additive
    - cross-doc ICC domain appended when any ICC domain is active

- `app/services/validator_verdict_builder.py`
  - Added `build_validation_results(...)` for normalized issue payload shaping (including semantic projection).
  - Added `build_validation_provenance(...)` for top-level provenance payload assembly.

### Orchestrator update
- `app/services/validator.py`
  - `validate_document_async` now delegates:
    - domain routing → `resolve_domain_sequence`
    - DB loading → `load_rules_with_provenance`
    - execution → `execute_rules_with_semantics`
    - verdict/provenance payload shaping → verdict builder module

## Phase D implementation details

### New module
- `app/services/validator_audit_writer.py`
  - Extracted policy/audit side-effects from `validator.py`:
    - overlay load (`get_active_overlay`)
    - exception load (`get_active_exceptions`)
    - policy transforms (`apply_policy_overlay`, `apply_policy_exceptions`)
    - analytics/audit event persistence (`_write_policy_application_events`)
    - orchestration entrypoint (`apply_bank_policy`)
  - Preserves non-fatal behavior:
    - policy apply failures return original/partially-transformed results (no hard fail)
    - audit write failures are swallowed with warning + `db_session.rollback()`

### Orchestrator finalization
- `app/services/validator.py`
  - now re-exports `apply_bank_policy` from `validator_audit_writer`.
  - `validate_document_async` remains thin orchestration path:
    - supplement router (`resolve_domain_sequence`)
    - rules loader (`load_rules_with_provenance`)
    - activation filter (`activate_rules_for_lc`)
    - rule executor (`execute_rules_with_semantics`)
    - verdict/provenance builder (`build_validation_results`, `build_validation_provenance`)
  - removed obvious dead legacy helpers from pre-split path:
    - duplicate ICC domain detector/helpers no longer used after router extraction

## Final architecture map

- `validator.py` (thin orchestrator + LC activation/filtering + AI enrichment)
  - imports:
    - `validator_supplement_router.py`
    - `validator_rules_loader.py`
    - `validator_rule_executor.py`
    - `validator_verdict_builder.py`
    - `validator_audit_writer.py`
- `validator_supplement_router.py`: domain/supplement inference and sequence resolution
- `validator_rules_loader.py`: primary fail-closed + supplement best-effort DB ruleset loading with provenance
- `validator_rule_executor.py`: evaluator execution + semantic condition expansion
- `validator_verdict_builder.py`: normalized issue payload + provenance payload construction
- `validator_audit_writer.py`: policy overlay/exception application + audit analytics side-effects

## Phase status

- Phase A: ✅ Complete
- Phase B: ✅ Complete
- Phase C: ✅ Complete
- Phase D: ✅ Complete
