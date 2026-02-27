# BANK-GRADE READINESS CHECKLIST (V1)
_Last updated: 2026-02-27 (Asia/Dhaka)_

## Objective
Upgrade LCopilot/TRDR Hub from pilot-grade to bank-grade by enforcing deterministic compliance decisions, strict governance, and auditable operations.

---

## Gate 1 — Strict Ruleset Enforcement (Fail-Closed)
**Target:** No verdict is produced unless required DB rulesets are loaded and executed.

### Requirements
- [ ] `STRICT_DB_RULES=true` runtime mode introduced.
- [ ] If no active ruleset for required domain/jurisdiction → validation `BLOCKED`.
- [ ] If DB rules execution fails/timeouts → validation `BLOCKED`.
- [ ] No silent fallback for core verdict path.

### Pass Criteria
- 100% of runs include successful DB-rules execution OR are explicitly blocked.

Owner: CTO (Backend + SRE)
Priority: P0

---

## Gate 2 — Verdict Provenance & Auditability
**Target:** Every issue/verdict is traceable to a specific rule/version/evidence.

### Requirements
- [ ] Issue schema includes: `rule_id`, `ruleset_id`, `ruleset_version`, `domain`, `jurisdiction`, `evidence_ref`.
- [ ] Job-level audit trail stores: model version, ruleset versions, timestamps, actor, decision transitions.
- [ ] Exportable compliance packet (JSON/PDF) for audit review.

### Pass Criteria
- Independent reviewer can reproduce verdict from stored artifacts for sampled jobs.

Owner: CTO + Compliance Office
Priority: P0

---

## Gate 3 — Deterministic Decision Policy
**Target:** AI is assistive, not authoritative over deterministic fails.

### Requirements
- [ ] Decision ladder codified: deterministic criticals override AI confidence.
- [ ] AI suggestions cannot downgrade critical rule failures.
- [ ] Rule severity matrix signed off (critical/major/minor → verdict effect).

### Pass Criteria
- 0 cases where AI overrode deterministic hard-fail in test corpus.

Owner: CTO + Product
Priority: P0

---

## Gate 4 — Data Contract Integrity (API ↔ UI)
**Target:** Summary, overview, docs, and issues never diverge.

### Requirements
- [ ] Single canonical status source in payload (`documents_structured.status` + counts from same source).
- [ ] Frontend consumes mapped canonical model only (no duplicate local remap paths).
- [ ] Contract tests for mismatch classes (2/2/2 vs all-verified impossible by design).

### Pass Criteria
- 0 cross-widget count mismatches across regression suite.

Owner: Frontend + Backend + QA
Priority: P0

---

## Gate 5 — Validation Quality Certification
**Target:** Measurable reliability against known oracle sets.

### Required Test Packs
- [ ] 20 PASS cases
- [ ] 20 WARN cases
- [ ] 20 REJECT cases
- [ ] 15 Adversarial/OCR-noise cases
- [ ] 15 Sanctions/TBML/shell-risk flag cases

### Metrics
- [ ] Critical false-pass rate <= 0.5%
- [ ] Verdict accuracy >= 95% on oracle set
- [ ] Re-run consistency >= 99%

Owner: QA + AI/ML + Forge-X
Priority: P0

---

## Gate 6 — Security, Access, and Data Controls
**Target:** Bank-safe operational controls.

### Requirements
- [ ] RBAC with role-scoped admin actions.
- [ ] Tenant isolation tests.
- [ ] Secret rotation and exposure monitoring.
- [ ] Encryption in transit + at rest confirmed.
- [ ] Immutable audit logs for compliance events.

### Pass Criteria
- Security review sign-off with no unresolved high/critical findings.

Owner: Security + SRE
Priority: P1

---

## Gate 7 — Reliability, Release, and Incident Discipline
**Target:** Stable production behavior under stress/failure.

### Requirements
- [ ] SLOs defined (availability, p95 latency, error budget).
- [ ] Health checks and alerting wired (API, DB, queue, OCR pipeline).
- [ ] Rollback playbook tested.
- [ ] P0/P1 incident runbook enforced.

### Pass Criteria
- Two successful game-day drills and one rollback drill passed.

Owner: DevOps/SRE + CTO
Priority: P1

---

## 30-Day Execution Plan

### Week 1 (P0 Core)
- Strict DB rules fail-closed
- Verdict provenance fields
- Canonical API/UI contract freeze

### Week 2 (P0 Quality)
- Golden suite + adversarial packs
- CI gates for mismatch/regression
- Deterministic policy lock

### Week 3 (P1 Controls)
- Security hardening + RBAC audit
- Compliance packet export
- Operational dashboards/SLOs

### Week 4 (Readiness)
- Game-day drills
- Bank-style UAT pack
- Final go/no-go review

---

## Go/No-Go Rule
**Go live only when all P0 gates pass and no unresolved critical risk remains.**

If any P0 gate fails, release is automatically **NO-GO**.
