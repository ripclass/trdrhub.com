# LCopilot Day3 - Phase 1 Recovery Report

**Gate Decision:** FAIL

## Objective
Restart and stabilize postgres/redis/api services until API container is healthy in `docker-compose ps`; capture evidence and determine exact API health failure cause.

## Evidence Captured

### 1) `docker-compose ps`

Observed values:

- Initial check (pre-repair):
  - `trdrhub-api ... Up 5 seconds (health: starting)`
  - postgres/redis healthy
- Post hotfix checks:
  - `trdrhub-api ... Up 30 seconds (health: starting)`
- Later:
  - `trdrhub-api ... Up 2 minutes (unhealthy)`
  - postgres/redis healthy

### 2) `Test-NetConnection localhost`

- `localhost:5432` => `TcpTestSucceeded : True`
- `localhost:6379` => `TcpTestSucceeded : True`
- `localhost:8000` => `TcpTestSucceeded : True`

### 3) Health endpoints (`curl`)

- `GET /healthz` => `200` with body `{"status":"ok"}`
- `GET /health/live` => `200` with body including `status/version/environment/uptime_seconds`
- `GET /health` (added compat endpoint) => `200`

### 4) `docker-compose logs api --tail 200`

- Service startup succeeds and routes respond 200 for `/healthz` and `/health/live`.
- No hard DB startup fatal shown at capture time.
- Historical health entries (container inspect) show repeated failures in container healthcheck:
  - `Output: /bin/sh: 1: curl: not found`

### 5) Container health state (from inspect)

- `.State.Health` previously showed:
  - `Status: starting` then `unhealthy`
  - repeated `FailingStreak` increments
  - each failure output: `curl: not found`

## Exact failing cause(s)

1. **Primary failure (hard):** API container healthcheck is configured to call `/health` using `curl`, but image does not contain `curl` (`/bin/sh: 1: curl: not found`).
2. **Operational blocker:** subsequent attempts to rebuild/restart API container hit host/containerd I/O errors, preventing container refresh:
   - `commit failed: write ... metadata.db: input/output error`
   - `open .../etc/passwd: input/output error`

## Repair actions attempted

- Added `curl` install in `apps/api/Dockerfile`:
  - `apt-get install -y curl` added with compiler deps.
- Added compat route `GET /health` in `apps/api/main.py`.
- Attempted rebuild + restart of API service.

## Gate Decision

**FAIL** (cannot mark PASS)

- API service remained `unhealthy` in compose health view due container healthcheck dependency on missing `curl`.
- Runtime/container-layer I/O failures blocked completion of rebuild/restart sequence and prevented durable recovery state transition.

## Exact fix required to pass

1. Ensure API image is rebuilt and instantiated with `curl` present or replace healthcheck with non-curl probe (python/urllib).
2. Resolve docker/containerd disk/I/O issue (`metadata.db` write errors) then restart API with new image.
3. Re-run and confirm:
   - `docker-compose ps` shows `trdrhub-api` as `healthy`
   - `/healthz` and `/health/live` remain stable 200s.
