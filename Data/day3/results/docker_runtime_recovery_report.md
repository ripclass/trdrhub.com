# Docker Runtime Recovery Report
**Scope:** cto-docker-runtime-recovery (subagent)
**Host:** `DESKTOP-81CQ8PC`
**Target:** Restore TRDRHub Phase 1 baseline after containerd I/O corruption
**Date:** 2026-03-01 12:20 (+06:00)

## Executive summary
Attempted recovery sequence completed in safe-first order, then destructive-equivalent actions when daemon remained dead. Runtime did **not** become usable. Docker engine still reports `starting` indefinitely and `docker` CLI calls do not complete (hard timeout). I/O corruption persists when WSL bootstrap tries to format disk for Docker backend.

## Commands executed (exact)

### 1) Precheck + service/daemon probes
- `Get-Service com.docker.service` → `Stopped`
- `docker version` (CLI)
  - hung, timed out repeatedly
- `sc.exe query com.docker.service`
- `sc.exe start com.docker.service`
  - failed: `OpenService FAILED 5: Access is denied.`
- `Get-Process -Name *docker*`
  - showed backend/frontend processes present despite daemon state stopped

### 2) Safe-first cleanup/restart attempts
- `wsl --list --verbose`
- `taskkill /F ...` for `Docker Desktop`, `com.docker.backend`, `com.docker.build`
- `wsl --shutdown`
- `Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe'`
- `Start-Service com.docker.service`
  - failed repeatedly with **Access is denied / cannot open service** (non-admin blocker)
- CLI checks after each cycle:
  - `docker version --format '{{.Server.Version}}'`
  - `docker ps -q`
  - each timed out repeatedly (`TIMEOUT`)

### 3) Factory-reset-equivalent actions (destructive, with backups)
Non-destructive steps did not recover runtime, so proceeded to runtime-data reset.

#### Move/delete targeted state (best-effort)
- Created backup dirs:
  - `C:\Users\User\AppData\Local\Docker\runtime-recovery-backup-20260301_122723`
  - `C:\Users\User\AppData\Local\Docker\runtime-recovery-full-backup-20260301_122942`
- Attempted moves:
  - `C:\Users\User\AppData\Local\Docker\wsl\disk\docker_data.vhdx`
  - `C:\Users\User\AppData\Local\Docker\wsl\main\ext4.vhdx`
- Removed lock file:
  - `C:\Users\User\AppData\Local\Docker\backend.lock`
- Removed stale runtime/state paths:
  - `C:\Users\User\AppData\Local\Docker\wsl\disk\docker_data.vhdx`
  - `C:\Users\User\AppData\Local\Docker\wsl\main\ext4.vhdx`
  - `C:\Users\User\AppData\Roaming\Docker\settings-store.json`
- Final hard cleanup:
  - `Remove-Item -Recurse -Force C:\Users\User\AppData\Local\Docker\wsl`

### 4) Restart test after reset
- Relaunched Docker Desktop
- Re-ran daemon checks (`docker ...`) with enforced timeout wrappers:
  - `docker version`
  - `docker ps -q`
  - `docker compose up -d` from `H:\.openclaw\workspace\trdrhub.com`
  - `docker compose ps`
  - all timed out (CLI could not establish daemon handshake)

## What was purged/reset
- Moved/archived prior Docker runtime VHDX state and settings:
  - Local Docker WSL data/metadata (`docker_data.vhdx`, `ext4.vhdx`)
  - backend lock file
  - `settings-store.json`
- Deleted reconstructed `Local\Docker\wsl` directory contents and recreated fresh runtime placeholders from Docker Desktop
- No repository/app code changes.

## Observed evidence of I/O corruption (from logs)
- `C:\Users\User\AppData\Local\Docker\log\host\com.docker.backend.exe.log`
  - `Buffer I/O error on device sde`
  - `fatal error: fault` / `SIGBUS` in containerd
  - `mkfs.ext4: I/O error while writing out and closing file system`
  - repeated backend state: `"docker":"starting","dockerAPI":"starting"` with ping timeouts

## Phase 1 checks
| Gate | Check | Result | Evidence |
|---|---|---|---|
| R1 | Docker daemon health (`docker version`) | **FAIL** | Hangs/timeout (no response) |
| R2 | Service start (`Start-Service com.docker.service` / `sc start`) | **FAIL** | Access denied (needs admin) |
| R3 | TRDRHub stack restore (`docker compose up -d`) | **FAIL** | timed out (daemon unavailable) |
| R4 | `docker compose ps` (api/postgres/redis) | **FAIL** | timed out (daemon unavailable) |
| R5 | Ports 5432/6379/8000 reachable | **NOT RUN** | Docker stack not started |
| R6 | `/healthz` and `/health/live` return 200 | **NOT RUN** | Docker stack not started |

## Final status
**FAIL** (runtime not recovered).

## Blocking issues (exact)
1. `com.docker.service` requires elevated permissions to start:
   - `SC_START_CODE: 5`
   - `[SC] StartService: OpenService FAILED 5: Access is denied.`
2. Post-reset bootstrap still cannot provision backend disk:
   - `mkfs.ext4: I/O error while writing out and closing file system`
   - indicates underlying I/O path corruption or blocked disk writes for Docker WSL backend.

## Required user action (next step)
- Re-run this recovery from an **elevated admin shell** and complete either:
  - Docker Desktop **factory reset** option, or
  - clean reinstall of Docker Desktop + WSL2 components,
  then rerun stack restore.
- If reset/reinstall remains failing, run host filesystem health check (disk health/I/O error validation) on system volume used by Docker VHDX before retrying.

## CTO signoff
- Objective: **NOT achieved** (daemon and engine remain non-functional)
- Recommended: **Pause TRDRHub deployment attempt until runtime is reinitialized with admin context**
- Risk posture: runtime cache already purged/reset; no source code modified.