# Constraints & Assumptions

## Execution constraints

- Beta execution is being optimized for an aggressive 4-week sprint.
- Exporter must stay the gold path throughout the sprint.
- Importer must reuse the same auth, validation, and result machinery.
- Bank is parked from launch-critical scope.
- Docs must reflect current repo truth, not aspirational architecture.

## Product assumptions

- Public beta can launch in English only.
- A hard paywall is acceptable if users receive a small free-entry allowance first.
- Self-serve guided onboarding is acceptable, but wrong-dashboard or stale-session behavior is not.
- Trust in the results loop matters more than breadth of features.

## Technical assumptions

- `structured_result` remains the canonical backend truth for exporter and importer results.
- `GET /api/results/{jobId}` remains the canonical read path for persisted results.
- Frontend compatibility layers may still exist, but they should not redefine product truth.
- Shared types must stay aligned with the runtime contract.

## Scope discipline

The sprint should favor blocker removal over feature expansion.

Cut first:

- secondary surfaces that fork auth or result logic
- parallel importer behavior
- non-essential polish that does not improve trust in login, validation, results, history, or paywall behavior
