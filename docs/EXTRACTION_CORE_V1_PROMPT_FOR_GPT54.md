# Prompt for GPT-5.4 — Implement Extraction Core v1 (Patch Set C)

Use this prompt in VS Code GPT-5.4:

---

You are implementing Patch Set C in `trdrhub.com`.

Context:
- P0 Patchset 1+2 already merged.
- Extraction Core v1 skeleton already exists under `apps/api/app/services/extraction_core`.
- Profiles exist under `apps/api/app/config/extraction_profiles`.

Goal:
Integrate fail-safe field states + review gating into existing validate pipeline while preserving backward compatibility.

Requirements:
1. For each critical field extracted in launch profiles, emit field state:
   - `found | parse_failed | missing`
2. Add review gate:
   - review_required=true if any critical field is missing/parse_failed
   - review_required=true if critical found field has no evidence
   - review_required=true if critical found field confidence < profile threshold
3. Keep current response shape, add only additive fields:
   - `_extraction_core_v1` block in structured_result
   - per-document review metadata in processing_summary docs
4. Use profile-driven critical fields from `apps/api/app/config/extraction_profiles/*.yaml`
5. Add deterministic tests (>=10) for:
   - state inference
n   - evidence gate
   - low confidence gate
   - backward-compat no-break
6. No massive refactor. Minimal targeted edits.

Deliver:
- A) File changes list
- B) Unified diffs
- C) Test commands
- D) Rollback toggle/feature flag

Constraints:
- Deterministic behavior only
- No new external dependencies
- Python tests must pass in existing venv

---
