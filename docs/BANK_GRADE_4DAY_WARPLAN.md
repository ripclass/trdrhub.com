# BANK-GRADE 4-DAY WARPLAN (E2E)
_Last updated: 2026-02-27 (Asia/Dhaka)_

## Non-Negotiable Outcome (Day 4)
- Deterministic + DB-rules fail-closed validation
- Consistent API/UI status contract
- Golden/adversarial test evidence
- Deployment + rollback + incident readiness
- Clear GO/NO-GO with evidence

---

## Day 1 — Core Determinism + `validator.py` Hardening (P0)
### Mission
Eliminate ambiguity in validation source and fallback behavior.

### Tasks
1. Enforce `STRICT_DB_RULES=true` in `validator.py` / validate path:
   - no active ruleset => BLOCKED
   - DB rule execution error/timeout => BLOCKED
   - no silent continuation for core verdict path
2. Add response provenance fields:
   - `ruleset_id`, `ruleset_version`, `domain`, `jurisdiction`, `rule_count_used`
3. Fix ruleset hygiene issues:
   - sanctions.eu `rule_count` mismatch
   - metadata label typos

### Exit Criteria
- 0 silent fallbacks in logs for validation verdict path
- Provenance fields present in every validation response

---

## Day 2 — Contract Integrity (P0)
### Mission
Make mismatch class impossible by design.

### Tasks
1. Freeze canonical payload contract (`documents_structured.status`, `issues_count`, `discrepancyCount`).
2. Ensure all summary/analytics distributions derive from same per-document status source.
3. Frontend reads mapped canonical source only.
4. Add contract regression tests (backend + frontend).

### Exit Criteria
- No Summary/Overview/Documents drift in regression suite

---

## Day 3 — AI Lead Test Marathon (P0)
### Mission
Prove quality with adversarial evidence.

### Required Test Packs
- 20 PASS
- 20 WARN
- 20 REJECT
- 15 OCR/adversarial
- 15 sanctions/TBML/shell-risk

### Metrics
- Critical false-pass <= 0.5%
- Verdict accuracy >= 95%
- Re-run consistency >= 99%

### Exit Criteria
- AI Lead signs off with evidence report + failed-case list resolved or explicitly deferred

---

## Day 4 — Production Readiness Drill (P0/P1)
### Mission
Operational readiness and controlled release.

### Tasks
1. Security/RBAC sanity and secret checks
2. SLO checks + alerting sanity
3. Rollback drill and incident simulation
4. Final GO/NO-GO board review

### Exit Criteria
- All P0 green
- No unresolved critical risk
- Signed GO/NO-GO memo generated

---

## `validator.py` Concern — What we do
Current concern: DB-rule issues can fail open (continue with other validators).

### Decision
Move to **fail-closed** for core compliance decisions.
- Keep optional fallback only for non-verdict helper insights (clearly marked)
- Never produce pass/warn/reject without successful DB rules execution

This is the single biggest bank-grade blocker and must be fixed first.
