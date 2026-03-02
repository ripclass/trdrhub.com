# LCopilot Day3 — CTO SOLID GREEN GO PLAN

**Owner:** Prometheus CTO
**Context date:** 2026-03-01
**Root issue state:** Current state is **NO-GO** (local API/API infra down, docker offline, DB/Redis down, prod routes 404, live API behavior uniform-blocked)

## 0) Decision target
Convert from NO-GO to **SOLID GREEN GO** via hard-gate remediation and evidence-backed reruns.

## 1) CORE_TECH_TEAM hierarchy (execution model)
- **CTO (Apex):** final decision, go/no-go approval, risk acceptance.
- **CORE_TECH_TEAM -> Active Squad (default, lean):**
  - **Infra Lead** (Docker/DB/Redis/host networking)
  - **Platform/API Lead** (services startup, route config, validate endpoint)
  - **QA Lead** (smoke/full reruns, metric computation, evidence)
  - **Data/Model Lead** (document packaging quality, blocked-uniform diagnosis)
- **RING-0 on-call advisors:**
  - **SRE Lead** (rate limit, reliability, rollback controls)
  - **Security/Compliance Lead** (prod routing, secret handling, audit logging)
  - **Frontend/Release Lead** (prod domain/app deployment recovery)

## 2) Current blockers (from cycle-1 artifacts)
1. `localhost:8000` API unreachable (connection refused / preflight timeout).
2. Docker Desktop engine offline.
3. PostgreSQL + Redis unavailable on local ports.
4. `api.trdrhub.com` and `app.trdrhub.com` returning 404 in prod checks.
5. Day3 live run pattern: **100% `blocked`** verdicts -> degenerate 5% accuracy signal.

## 3) What counts as **SOLID GREEN GO** (hard criteria)
### A. Infrastructure readiness (all MUST PASS)
- Docker engine running and healthy.
- `trdrhub-postgres` and `trdrhub-redis` healthy.
- `trdrhub-api` running and listening on `:8000`.
- Health probes:
  - `GET /healthz` == 200
  - `GET /health/live` == 200
- Local validation endpoint reachable: `POST/GET /api/validate/` responds without transport error.
- Prod smoke baseline:
  - `https://api.trdrhub.com/healthz` != 404
  - `https://app.trdrhub.com/` returns app route (non-404)

### B. Day3 quality gates
- **Smoke run:** 20 cases (smoke20)
  - Comparable records >= 18/20
  - Oracle agreement (accuracy) >= **0.70**
  - Pass class recall >= **0.60**
  - Critical false-pass (`expected=reject`, `actual=pass`) = **0**
  - 422 count = **0**
  - HTTP429 exhaustion rate <= **5%**
  - Pass-blocked anomaly check: `pass_actual_blocked / pass_expected < 0.30`
- **Full run readiness:** 90 cases
  - Comparable records >= 85/90
  - Accuracy >= **0.65**
  - Critical false-pass = **0**
  - 429 exhaustion <= **5%**
  - Rate-limit sleep + retry behavior bounded (no single run > 45m)
- **Uniform-block anti-pattern guard:** if `actual_blocked` share > 70% overall or >30% for any non-`blocked` expected class -> hard fail regardless of raw accuracy.

### C. Reliability + safety
- End-to-end test duration controlled, with deterministic rerun evidence.
- No raw credential/log leakage in logs/artifacts.
- No fallback to demo stub mode for SOLID GREEN GO decision (must run real extraction pipeline unless explicitly waived by CTO).
- All artifacts reproducible from git-tracked commands.

## 4) Statistical confidence requirements
- **Minimum reruns:**
  - **Smoke20 × 2 independent runs** (separate invocations, same environment). Must pass hard gates in both.
  - If smoke passes, run **Full-90 × 1**.
  - If Full-90 fails any hard gate, stop and execute targeted fix before any further runs.
- **Confidence note:**
  - n=20 has wide CI; therefore 2 consecutive smoke passes required.
  - For smoke proportion `p`, report Wilson 95% CI and require lower bound `> 0.60`.
  - For Full-90, if smoke gate is clean, report Wilson 95% CI; if lower bound < 0.55, do **not** hard-go.
- **Rerun consistency:** identical sample set re-run consistency >= **0.95** (second smoke against first smoke in same 20-case seed).

## 5) Acceptance gates by phase (execution checklist)

### Phase 0 — Stop/Reset controls
- [ ] Freeze auto-retry agents and any external autonomous loops.
- [ ] Snapshot current `Data/day3/results` (copy to `Data/day3/results/rollback_prefix_$TS/`).
- [ ] Confirm maintenance window for rate-limit tests.

**Stop criteria:** missing evidence artifacts -> do not proceed.

### Phase 1 — Local infrastructure recovery
**Owner:** Infra Lead + CTO

Commands:
- `docker version`
- `Start-Service docker` (or start Docker Desktop)
- `cd H:\.openclaw\workspace\trdrhub.com`
- `docker-compose up -d`
- `docker-compose ps`
- `docker-compose logs -f trdrhub-postgres --tail 80`
- `docker-compose logs -f trdrhub-redis --tail 80`
- `docker-compose logs -f trdrhub-api --tail 120`

Checks:
- `docker-compose ps` shows `trdrhub-postgres`, `trdrhub-redis`, `trdrhub-api` Up/Healthy.
- DB connectivity: `Test-NetConnection localhost -Port 5432` success.
- Redis connectivity: `Test-NetConnection localhost -Port 6379` success.
- API TCP: `Test-NetConnection localhost -Port 8000` success.
- API health:
  - `Invoke-WebRequest -Uri http://localhost:8000/healthz`
  - `Invoke-WebRequest -Uri http://localhost:8000/health/live`

**Stop/go criteria (Go to Phase 2):** all 4 checks pass and no startup-critical issues in API logs.

**Rollback point R1 (if fail):**
- `docker-compose down -v`
- `docker volume ls` review unused volumes
- restore previous `.env` and return to Phase 0.

### Phase 2 — API configuration + document/route hardening
**Owners:** Platform/API Lead + Data/Model Lead

Files/actions:
- Copy `.env.example` -> `.env` if missing.
- Set explicit endpoint env:
  - `DAY3_API_URL=http://localhost:8000/api/validate/`
  - `DAY3_API_TOKEN=` (empty unless local auth enabled)
- Ensure stub mode is intentionally set for this phase test:
  - For real extraction test, enforce `USE_STUBS=false` in compose/service override if current container uses stub defaults.
- Confirm `docker-compose` service env and mount paths.

Checks:
- API startup log includes `Application configuration` and `Database connection established`.
- Optional manual payload probe (single case) to confirm non-uniform behavior:
  ```powershell
  $env:DAY3_API_URL='http://localhost:8000/api/validate/'
  python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --limit 1 --min-interval 2 --retries-429 4
  ```
- Parse first result; if actual verdict equals blocked for all inputs, inspect raw response fields:
  - structured_result keys
  - extraction summary / issue severity breakdown
  - LC detection / document presence flags

**Stop/go criteria:** single-case manual run not uniformly blocked; logs show `document_type` and OCR processing path executed.

**Rollback point R2 (if uniform blocked persists):**
- Switch back to documented demo-safe config:
  - `USE_STUBS=true` only for controlled demonstration (not Day3 decision evidence),
  - revert validate payload or document bundle format changes from this phase and investigate offline.

### Phase 3 — Smoke validation gate
**Owner:** QA Lead + API Lead

Run sequence:
1. `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8`
2. Parse artifacts:
   - `data/day3/results/metrics_summary.json`
   - `data/day3/results/confusion_matrix.csv`
   - `data/day3/results/day3_results.jsonl`
3. Re-run once immediately with same seed/inputs (or `--smoke20` identical manifest):
   - `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8`

Hard gate checklist:
- [ ] run1 comparable >= 18/20
- [ ] run1 accuracy >= 0.70
- [ ] run1 critical_false_pass == 0
- [ ] run1 pass_blocked_ratio < 0.30
- [ ] run1 422 == 0, 429 exhaustion <= 5%
- [ ] run2 passes all above and matches rerun consistency >= 0.95

**Rollback point R3 (if fail):**
- Stop automated full run.
- Freeze config at latest failing state and revert to R2 investigation.
- Return to manual triage with issue evidence to Product/Infra owners.

### Phase 4 — Full-cycle go decision gates
**Owner:** CTO (Approve) + QA Lead

Command:
- `python .\tools\day3_pipeline\run_batch_day3.py --min-interval 3.0 --retries-429 8`

Hard gate checklist:
- [ ] Comparable records >= 85/90
- [ ] Accuracy >= 0.65 (95% CI lower bound > 0.55)
- [ ] Critical false-pass == 0
- [ ] pass-blocked anomaly check passes
- [ ] 429 exhaustion <= 5%
- [ ] no new infra/runtime blocking errors

### Phase 5 — Production readiness verification (non-blocking for local go, required for deployment gate)
**Owner:** Frontend/Release Lead + SRE Lead + Security

Checks:
- `https://api.trdrhub.com/healthz`, `/health/live`, `/api/validate/` return expected response type.
- `https://app.trdrhub.com/` no 404, app loads.
- Edge/proxy rewrite rules point to API service for `/api/*` path.

## 6) Anti-regression guardrails
- Keep `data/day3/results/day3_results.jsonl` append-only for this cycle; do not overwrite until evidence archived.
- `run_batch` always with `--min-interval >= 2.5` (prefer 3.0+) and 429 retry cap >= 6.
- Add alert on “all-blocked” signature:
  - `if actual_blocked/total > 0.7 -> fail hard gate immediately`
- Add manifest sanity check before each run: scenario counts, expected verdict distribution present.
- Capture and diff `confusion_matrix.csv` against prior run; any major drift in non-block classes (>30% absolute drop) requires root-cause review.
- Keep prod route checks and local checks separate and timestamped.

## 7) Concrete timeline (suggested)
- **T+0:00–0:30**: Phase 0 + Phase 1 restore
- **T+0:30–1:20**: Phase 2 config hardening + single-case manual probe
- **T+1:20–1:50**: Smoke rerun ×2 (with cooldown if 429 observed)
- **T+1:50–3:00**: Full 90-case run (if smoke clear)
- **T+3:00–3:30**: Go/No-Go report drafting + PROD checks + rollback planning

## 8) Stop/Go criteria summary
### STOP immediately if:
- Any infrastructure check in Phase 1 fails twice.
- Uniform-block anomaly persists after Phase 2 triage.
- Any hard gate fails in smoke2 or Phase 4.

### GO only when:
- All hard gates in Sections 3A, 3B, and 4 are satisfied.
- Two independent smoke reruns pass.
- Full run passes (or is explicitly not required by CTO due risk-managed scope).
- CTO approves the evidence bundle.

## 9) Evidence bundle (must be attached to Day3 signoff)
- `Data/day3/results/metrics_summary.json`
- `Data/day3/results/confusion_matrix.csv`
- `Data/day3/results/day3_results.jsonl`
- `Data/day3/results/failed_cases.csv`
- `Data/day3/results/rate_limit_stats.json`
- `Data/day3/results/DAY3_SIGNOFF.md`
- This plan and execution checklist

## 10) Rerun evidence script template (required command sequence)
```powershell
cd H:\.openclaw\workspace\trdrhub.com
$env:DAY3_API_URL='http://localhost:8000/api/validate/'

# Phase 2/3 smoke
python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8
python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8

# Gate decision from metrics
Get-Content .\data\day3\results\metrics_summary.json
Get-Content .\data\day3\results\rate_limit_stats.json

# Full run
python .\tools\day3_pipeline\run_batch_day3.py --min-interval 3.0 --retries-429 8
```

---
**End state:** move from current NO-GO to **SOLID GREEN GO** only after above gates pass and CTO signs.
