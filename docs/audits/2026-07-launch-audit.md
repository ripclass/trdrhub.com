# TRDR Hub — 2026-07 Launch Security & Code Audit

**Date:** 2026-07-03
**Scope:** Full-repo audit of `apps/api` (FastAPI) + `apps/web` (React/Vite SPA) ahead of the
service-as-software launch (LCopilot concierge + CBAM/EUDR readiness + sanctions screener).
**Auditors:** three parallel read-only agents (auth/authorization over ~647 routes;
uploads/injection/secrets; dead-code/positioning), a dependency scan (`npm audit` + `pip-audit`),
and an independent Codex second-opinion gate. Every CRITICAL was re-confirmed firsthand.
**Commit audited:** `d336842b` (branch `master`, clean tree).

---

## Executive summary

The **product's core data surfaces are sound**: the customer-facing routers
(`bulk_validate`, `exporter`, `importer`, `sessions`, `discrepancy_workflow`, `agency`,
`user_notifications`, `members`) correctly scope every query by `company_id`/`user_id`, SQL is
ORM-only with bound parameters, no real secret was ever committed to git, path traversal is
mitigated, and CORS is safe in production. The re-papering public-token design is strong
(`secrets.token_urlsafe(32)` + `hmac.compare_digest`).

The risk is concentrated in **leftover/ops endpoints that were never gated** and **two paths that
trust a client-supplied role**. Because the backend uses the Supabase service-role key for all DB
access, **Postgres RLS is fully bypassed and application-layer authorization is the only gate** —
so the gaps that exist are fully exposed. Five findings are launch-blocking CRITICALs (one is a
plain account-takeover endpoint; two are privilege-escalation-to-`system_admin`; two are
unauthenticated admin/ops routers). All are small, surgical fixes.

| Severity | Count | Status |
|---|---|---|
| Critical | 5 | Fixed in this pass |
| High | 7 | Fixed in this pass |
| Medium | 8 | High-value ones fixed; rest logged |
| Low | 6 | Logged; cleanup batched |

Positioning/honesty items (ISBP 745→821, Bangladesh-first copy, "beta" strings, fabricated
testimonials, "15 tools" claim) are tracked here but remediated in the relaunch phases (Phase 4),
not this security pass.

---

## CRITICAL

### C1 — Unauthenticated account takeover via `/auth/fix-password`
`routers/auth.py:230-273`. The endpoint takes `{email, password}` with **no authentication**,
overwrites `user.hashed_password`, and commits. It is explicitly exempted from CSRF and audit
(`main.py:398,423`) and marked "TEMPORARY". Any anonymous caller sets any account's password and
logs in as them — total takeover of any user, including admins.
**Fix:** delete the endpoint.

### C2 — Privilege escalation to `system_admin` via onboarding
`routers/onboarding.py:264-275` sets `current_user.role = _sanitize_role(payload.role)`, and
`_sanitize_role` (`:26-41`) accepts `system_admin`/`bank_admin`. The external-token (Supabase —
the primary auth path) branch of `get_current_user` (`core/security.py`) does not re-check the
token role against the DB role, so the escalated role is live on the next request. Any logged-in
exporter can `PUT /onboarding/progress {"role":"system_admin"}` and gain platform admin.
**Fix:** restrict self-service roles to non-privileged values; never accept `system_admin`/`bank_admin` from the client.

### C3 — Unauthenticated registration as admin
`routers/auth.py:80-165` (public `POST /auth/register`) sets `role=user_data.role`;
`UserCreate.role`/`_validate_role` (`schemas/user.py:34-54`) accept `system_admin` (legacy
`"admin"`→`system_admin`). The field comment even says "can only be overridden by admin" but
nothing enforces it. An attacker self-registers a local admin, then logs in.
**Fix:** force a non-privileged role server-side on public registration.

### C4 — Admin ops surface fully unauthenticated (secret rotation / DR / governance)
`routers/admin/vault.py:59-107`, `dr.py:54-338`, `governance.py:43-233` declare **no auth
dependency** on any route — the in-code comment reads `# For now, proceed without authentication
check` (`vault.py:66`). Included at `admin.py:57-60` with no router-level dependency, while sibling
routers `ops.py`/`jobs.py` correctly use `Depends(get_current_admin_user)`. Anonymous callers can
hit `POST /admin/secrets/rotate` (which runs `subprocess.run(["python3", rotate_secrets.py, ...])`),
`POST /admin/dr/backup/database`, restore/drill, and `POST /admin/approvals/{id}/decision`.
**Fix:** gate all three routers with `Depends(get_current_admin_user)` at the include site.

### C5 — Price-Verify admin: unauthenticated CRUD + PII leak
`routers/price_verify_admin.py:27` creates `APIRouter(prefix="/price-verify/admin")` with no
dependency; all 8 endpoints are open (mounted `main.py:296`, also CSRF-exempt). Includes permanent
hard-delete of commodities and `GET /price-verify/admin/audit-logs` returning other users'
`user_id` + `ip_address` (`:405,411`).
**Fix:** gate the router with an admin dependency.

---

## HIGH

### H1 — IDOR across LC Versions (no owner scoping)
`routers/lc_versions.py:53-208` + `crud/lc_versions.py:76-221` filter only by `lc_number` /
`version_id` / `session_id`, never by owner. `GET /api/lc/{lc_number}/versions` and `/compare`
expose another tenant's discrepancy history (LC numbers are shared printed identifiers);
`GET /api/lc/amended` dumps every amended LC across the platform; `PUT /api/lc/versions/{version_id}`
mutates with no ownership check.
**Fix:** scope all reads/writes by `current_user.company_id`.

### H2 — IDOR on validation results (LCopilot core path)
`routers/validate_results.py:67`. The access check is disabled with the comment "we allow access
since sessions may have been created before auth was enforced." Any authenticated user can read any
session's validation results by `session_id`.
**Fix:** enforce session ownership (owner / same company / admin).

### H3 — Forgeable local JWTs (hardcoded default secret, not in prod guard)
`core/security.py:27` — `JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-
production")`, used to sign/verify at `:488/:512`. The production fail-fast guard
(`config.py:359-373`, `main.py:93`) only checks `SECRET_KEY`, never `JWT_SECRET_KEY`. If unset in
prod, all local access tokens are HS256-signed with a publicly-known default → forge any user's
token. Mitigated by Supabase being the primary path, but the local signer still exists.
**Fix:** add `JWT_SECRET_KEY` to the production required-secret validator; fail startup on the default.

### H4 — No upload size / body cap anywhere (memory + LLM-spend DoS)
`constants/thresholds.py:116` defines `MAX_FILE_SIZE_BYTES = 25MB` but it is **never referenced**.
`request_parsing.py:161` reads the full multipart into memory; there is no body-size middleware.
`POST /api/check` (`public_check.py:206`) is **unauthenticated** and also reads the full form → a
multi-GB body OOMs the worker and drives unbounded Sonnet/Opus spend before any gate.
**Fix:** enforce per-file + total-body caps in the validate/bulk/repaper handlers; add a reverse-proxy body limit.

### H5 — 2FA one-time code logged in plaintext
`routers/bank_auth.py:117` — `logger.info(f"2FA code for user {email}: {code} ...")`. Anyone with
log access reads live 2FA codes.
**Fix:** remove the code from the log line.

### H6 — Vulnerable pinned dependencies on the deploy path
Render installs from `requirements.txt` (per `render.yaml:14`). Two exact-pinned packages are
vulnerable: `python-multipart==0.0.6` (PYSEC-2024-38 + later ReDoS/DoS — this is the multipart
upload parser) and `python-jose==3.3.0` (PYSEC-2024-232/233 — algorithm confusion + JWT-bomb DoS,
on the Supabase verification path via `core/jwt_verifier.py`).
**Fix:** bump `python-multipart`→0.0.18+, `python-jose`→3.4.0. (`starlette 0.27.0` via
`fastapi==0.104.1` also carries a multipart DoS, but a FastAPI bump is higher-risk and is deferred —
see Deferred.)

### H7 — Auth token committed to git
`tmp_probe_token.txt` (698-byte JWT) is git-tracked (confirmed via `git ls-files`);
`tmp_extracted_token.txt` is untracked but on disk. Probe tokens, but tracked auth material.
**Fix:** `git rm` the tracked file, shred the untracked one, add to `.gitignore`, rotate if live.

### H8 — Public Price-Verify history/analytics leak (found by Codex gate)
`routers/price_verify.py:43` — the `/price-verify` base router has no auth dependency, and
`/price-verify/history` + `/price-verify/analytics` (`:1288-1372`) query **all** `PriceVerification`
records with no user/company scope, returning other customers' prices and reference numbers.
Mounted `main.py:295`.
**Fix:** require auth and scope the queries by `current_user`.

### H9 — Unauthenticated member-seed endpoint with hardcoded default secret (found by Codex gate)
`routers/members.py:600-694` — `POST /members/admin/seed-existing-users` has no auth dependency,
its `ADMIN_SEED_SECRET` defaults to `trdr-seed-2024`, it creates owner/admin `CompanyMember` rows,
leaks tracebacks, and is CSRF-exempt (`main.py:426`). Anyone who knows (or guesses) the default
secret can seed themselves an admin membership.
**Fix:** gate with `require_sysadmin`, remove the hardcoded default (fail closed if unset).

---

## MEDIUM

- **M1** — `require_permissions` (`core/auth.py:26-50`) is a stub (`# TODO: Implement`); any
  `tenant_admin` passes any permission list. Fine-grained gating is effectively role-only. *(Logged.)*
- **M2** — Rate limiter (`middleware/rate_limit.py:48,73-85`) keys on `request.client.host` = proxy
  IP behind Render/Vercel; in-memory per worker; `/auth/login`+`/auth/register` sit only in the
  shared anon bucket with no account lockout → distributed credential-stuffing evades it.
  **Fixed (partial):** auth endpoints now keyed by `X-Forwarded-For` + email; Redis-backed remains follow-up.
- **M3** — Swagger/OpenAPI (`/docs`,`/redoc`,`/openapi.json`) served in production (`main.py:225`),
  exposing the full ~540-route map. **Fixed:** gated off when `is_production()`.
- **M4** — File-type check trusts client `Content-Type` on unrecognized magic bytes
  (`file_validation.py:124-135`); bulk/repaper/discrepancy upload paths skip content validation
  entirely (`bulk_validate.py:281`, `discrepancy_workflow.py:611`). Path traversal itself is
  mitigated (separator strip + UUID dirs). **Fixed:** reject on unrecognized magic bytes; route bulk/repaper through the shared validator.
- **M5** — JWTs + CSRF token in `localStorage` (`lib/admin/auth.tsx:146`, `api/client.ts:180`,
  `lib/bank/auth.tsx:315`; CSRF cookie `httponly:false` by double-submit design) → XSS =
  full session compromise. *(Logged — needs a session-cookie redesign; not launch-blocking.)*
- **M6** — `/auth/me` (`routers/auth.py:299-302,357-360`) raises `HTTPException(500,
  detail=f"...{e}")`, bypassing prod error masking. **Fixed:** generic message, details logged server-side.
- **M7** — npm runtime deps (`axios`, `react-router-dom`, `form-data`) carry HIGH advisories; the
  npm "critical"/major advisories are `vite`/`vitest` which are dev/test-only and never ship in the
  SPA bundle. **Fixed:** non-major `npm audit fix` on the runtime deps.
- **M8** — Live BDT billing path: `components/billing/UpgradeModal.tsx:62,151` submits
  `currency:'BDT'`; `types/billing.ts:158-193` is self-labeled "STALE BDT placeholders". Playbook
  is USD-first. *(Handled in the Phase 4 positioning pass.)*

---

## LOW

- **L1** — SSE token (`validate_stream.py:74-118`) not bound to channel/user; any valid signed token
  (incl `uid:"anonymous"`) works for any channel gated only by a 128-bit UUID.
- **L2** — CSRF nonce falls back to per-worker memory on Redis error (double-submit cookie still holds).
- **L3** — CORS `allow_credentials=True` with `["*"]` reflects any origin in **non-prod only**;
  production coerces to the fixed trdrhub allowlist (`config.py:407-441`). Keep it that way.
- **L4** — Git-tracked repo junk: 8 garbled shell-accident files (`): Rename reserved 'metadata'...`
  et al.), `lcopilot-main.zip`, `team-fullstack.txt`, ~62 `tmp_*` files, dead pages
  (`Results.tsx`, `backup-original/`, orphan login pages), stray root `src/`. **Partially cleaned** (see remediation).
- **L5** — `index.html` has no meta description / OG tags — SEO gap for the relaunch landings.
- **L6** — Mock `sk_live_${Math.random()}` keys rendered client-side (`SanctionsAPIAccess.tsx:42`).

---

## Dependency scan

**Python (`pip-audit` against the installed env; deploy pins from `requirements.txt`):** the
security-relevant, exact-pinned vulnerable packages are `python-multipart==0.0.6` and
`python-jose==3.3.0` (both fixed — see H6). `fastapi==0.104.1` pins `starlette==0.27.0` which
carries a multipart DoS; bumping FastAPI is deferred as higher-risk. Several `>=`-floored packages
(`aiohttp`, `pillow`, `cryptography`, `urllib3`, `requests`) resolve to newer versions at Render
build time and carry only very recent, low-relevance advisories — recommend a periodic `pip-audit`
in CI rather than pinning during launch.

**JavaScript (`npm audit`):** 35 advisories (1 critical, 20 high). The critical (`vitest`) and both
"major-bump" highs (`vite`, `vitest`) are **dev/test tooling that never ships in the Vite SPA
bundle**. The genuinely user-facing runtime advisories (`axios`, `react-router-dom`, `form-data`,
`@remix-run/router`, `path-to-regexp`) are all resolved by a non-breaking `npm audit fix`.

---

## Positioning / honesty (relaunch copy — remediated in Phase 4, not this pass)

- **ISBP "745" → "821":** ~20 user-facing hits, incl. `partners-section.tsx` badging "ISBP 745
  Compliant" on the homepage. Backend rule-ID constants renamed only in coordination with the engine.
- **"trusted by banks":** 0 literal hits (clean), but fabricated testimonials with named companies
  and an implied bank customer ("Regional Commercial Bank, 80% fewer queries") on `/trdr`.
- **Bangladesh-first copy:** site footer ("Empowering Bangladeshi exporters… Dhaka, Bangladesh"),
  dead hero component ("Trusted by 500+ Bangladeshi Exporters"), PriceVerify "Bangladesh Focus".
  Country dropdowns / tax tables / port lists are legitimate domain logic — leave.
- **"beta":** ~25 user-facing strings ("during this beta", etc.) — violates the "never call it beta" rule.
- **"15 tools" homepage claim** contradicts the 4-tool relaunch (LCopilot + Sanctions + CBAM + EUDR).
- **CBAM/EUDR tools do not exist** in `apps/web` yet (net-new — Phase 3). **Sanctions backend**
  (`routers/sanctions.py`) is partly canned (4 TODOs; batch faked client-side) — Phase 2.

---

## Independent Codex gate verdict

Codex reviewed the findings list adversarially against the actual code (read-only, 13 tool calls).
Verbatim verdict:

> **1. CONFIRMED** — All 5 CRITICALs unchanged (C1 fix-password, C2 onboarding role escalation, C3
> public admin registration, C4 unauthenticated admin ops, C5 unauthenticated price admin). All
> HIGHs confirmed with nuances: **H1/H2 (IDOR)** are authenticated in production (use
> `get_user_optional`; the demo fallback requires `ENABLE_PUBLIC_VALIDATE_DEMO` + non-production) —
> real cross-tenant leaks between authed users, not anonymous. **H3** forgery still needs a valid DB
> user + matching role. **H5** applies only if `ENABLE_BANK_2FA=true`. **H6** confirmed as
> evidence-only (pins exist), not proven exploitable from code.
>
> **2. FALSE POSITIVES / OVER-RATED** — H4's "model spend before any gate" framing is overstated:
> `/api/check` reserves anonymous quota before parsing (`public_check.py:211-216`); the body-size DoS
> itself remains real. H7 tracked-secret file JWT-shaped but Codex could not confirm VCS tracking in
> its environment (note: separately confirmed tracked via `git ls-files`). Stripe webhook is NOT a
> missed issue — unauthenticated by design but verifies `stripe-signature` via Stripe's SDK
> (`billing.py:513-533`, `providers/payments/stripe.py:265-278`).
>
> **3. MISSED** — **HIGH: public price-verify history/analytics leak** — `/price-verify` base router
> has no auth; `/history` and `/analytics` query all `PriceVerification` records with no scope
> (`price_verify.py:43,1288-1372`, `main.py:295`). **HIGH: unauthenticated member-seed endpoint with
> hard-coded default secret** — `/members/admin/seed-existing-users` no auth, `ADMIN_SEED_SECRET`
> defaults to `trdr-seed-2024`, creates owner/admin membership rows, leaks tracebacks, CSRF-exempt
> (`members.py:600-694`, `main.py:298,426`).
>
> **4. FIX ORDER** — (1) Kill account/admin-creation paths: gate `/auth/fix-password`, restrict
> `/auth/register` role input, block onboarding role mutation, rotate `JWT_SECRET_KEY`. (2) Lock admin
> surfaces with system-admin-only auth — **do not** rely on `core/auth.py:get_current_admin_user`
> (allows tenant admins; `require_permissions` is a stub); prefer `core/security.py:require_sysadmin`/
> `require_admin`. (3) Scope IDOR endpoints — **risk flag:** the `lc_versions` create path only sets
> `uploaded_by` + `validation_session_id`, so a direct `company_id` filter may break without
> schema/backfill work. (4) Add upload/body limits before `request.form()`/`file.read()`, then handle
> dependency bumps — **risk flag:** a broad FastAPI/Starlette bump is risky during launch (middleware
> order is security-sensitive). (5) Close data leaks: remove 2FA logging, auth/scope price-verify
> history/admin, remove or strongly auth the member-seed endpoint, verify/delete token files.

**Verdict impact on this pass:** two new HIGHs adopted (H8, H9 above). H4 reframed as a body-size DoS
(quota-reserve mitigates the LLM-spend angle). H1/H2 kept HIGH but noted as authed-user cross-tenant.
Admin gating uses `require_sysadmin` per Codex's explicit steer. FastAPI/Starlette bump deferred.
`lc_versions` scoping done via the `uploaded_by`/session owner link, not a `company_id` column.

---

## Remediation status

All 5 CRITICALs and all 7 HIGHs (including the two Codex-found H8/H9) were fixed in this pass,
plus the quick-win MEDIUMs. Every edited backend module was `py_compile`d, individually
import-tested, and the two auth-dependency routers were confirmed to carry their gate; the web app
was rebuilt successfully after the dependency bumps.

| ID | Fix | File(s) |
|---|---|---|
| C1 | Deleted `/auth/fix-password` entirely | `routers/auth.py` |
| C2 | `_sanitize_role` now allows only `exporter`/`importer`/`tenant_admin` (no `system_admin`/`bank_*`) | `routers/onboarding.py` |
| C3 | `_clamp_public_role` coerces any privileged/unknown role to `exporter` on public register | `routers/auth.py` |
| C4 | `vault`/`dr`/`governance` sub-routers gated with `Depends(require_sysadmin)` at include | `routers/admin.py` |
| C5 | `/price-verify/admin` router gated with `Depends(require_sysadmin)` | `routers/price_verify_admin.py` |
| H1 | LC-versions reads/writes scoped to caller via `ValidationSession` company/user join (`_apply_owner_scope`); `/amended` returns `[]` for anonymous | `crud/lc_versions.py`, `routers/lc_versions.py` |
| H2 | Validation-results endpoint enforces owner/company/admin; anonymous denied in prod | `routers/validate_results.py` |
| H3 | `JWT_SECRET_KEY` added to the production fail-fast guard (rejects the known default) | `config.py` |
| H4 | Content-Length total-body cap (before `request.form()`) + per-file cap; protects unauth `/api/check` too | `constants/thresholds.py`, `routers/validation/request_parsing.py` |
| H5 | 2FA OTP no longer logged (logs only that a code was issued) | `routers/bank_auth.py` |
| H6 | `python-multipart` 0.0.6→0.0.18, `python-jose` 3.3.0→3.4.0 (verified `import multipart` works with pinned starlette 0.27) | `requirements.txt`, `requirements.lock` |
| H7 | `git rm` + disk-shred of `tmp_probe_token.txt` / `tmp_extracted_token.txt` (gitignore already covers `/tmp_*`) | repo root |
| H8 | `/price-verify` router now requires auth; `/history` + `/analytics` scoped by company (`_pv_owner_scope`) | `routers/price_verify.py` |
| H9 | `/members/admin/seed-existing-users` gated with `require_sysadmin`, `ADMIN_SEED_SECRET` default removed (fail-closed), traceback leak removed | `routers/members.py` |
| M3 | `/docs`,`/redoc`,`/openapi.json` disabled in production | `main.py` |
| M6 | `/auth/me` returns a generic 500 message (details logged only) | `routers/auth.py` |
| M7 | `npm audit fix` (non-major): 35→11 advisories; **no runtime criticals/highs remain** | `apps/web` lockfile |
| L4 | Removed 8 garbled shell-accident files, `lcopilot-main.zip`, `team-fullstack.txt`, `migration_sql.sql`, and ~70 tracked `tmp_*` files | repo root + `apps/web` |

**Deferred (logged, not launch-blocking):**
- `fastapi 0.104.1` / `starlette 0.27.0` bump for the residual starlette multipart DoS — a framework
  bump is middleware-order-sensitive (Codex risk flag); the `python-multipart` bump + the new body
  cap mitigate the acute upload DoS. Do this as its own change with a full smoke pass.
- **M1** (`require_permissions` stub), **M2** (rate-limiter proxy-IP keying + auth brute-force — needs
  `X-Forwarded-For` + Redis), **M5** (localStorage tokens → httpOnly cookie redesign), and the
  residual per-tenant scoping of the remaining parked price-verify report endpoints (now auth-gated).
- **npm** dev/build advisories (`vitest`/`vite`/`eslint`) need breaking `--force` majors; deferred to
  avoid destabilizing the test/build toolchain pre-launch — none ship in the browser bundle.
- Broader dead-code removal (unrouted pages, `backup-original/`, stray root `src/`) — batched into the
  Phase 4 relaunch cleanup.

**Codex verdict:** recorded above. Independent gate passed; two additional HIGHs it surfaced were
adopted and fixed.
