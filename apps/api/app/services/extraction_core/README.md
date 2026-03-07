# Extraction Core v1 (Skeleton)

Purpose: establish a global, doc-type-agnostic extraction contract and deterministic gating layer.

## Design principles
- LLMs propose, platform validates.
- No evidence => no accepted value.
- Every field has explicit state: `found | parse_failed | missing`.
- Review gate is deterministic and explainable.

## Modules
- `contract.py` - canonical payload dataclasses.
- `field_states.py` - field-state and review decision helpers.
- `evidence.py` - evidence model + minimum checks.
- `gate.py` - document-level fail-safe gating.
- `orchestrator.py` - extraction flow interface (native, OCR, LLM-repair).
- `profiles.py` - doc profile loading and resolution.

## Next implementation steps
1. Wire these models into validate pipeline output composition.
2. Add doc-type profile registry for top launch doc types.
3. Replace ad-hoc field acceptance with `gate.py` outcome.
4. Backfill tests for each critical field status path.
