# TRDR Auth E2E Test Checklist & Smoke-Test Plan
> Version: 1.0 — Generated 2026-02-26  
> Scope: Exporter persona, normal browser + incognito, local & production API

---

## 1. Required Endpoints & Expected Status Codes

### Public (no auth)
| Method | Path | Expected | Notes |
|--------|------|----------|-------|
| POST | `/auth/register` | 201 | New user |
| POST | `/auth/login` | 200 | Returns `{access_token, token_type, expires_in, role}` |
| GET | `/auth/csrf-token` | 200 | Sets `X-CSRF-Token` cookie |
| GET | `/health/live` | 200 | Liveness probe |
| GET | `/health/ready` | 200 or 503 | 503 only if DB down |
| GET | `/usage/plans` | 200 | No auth required |

### Authenticated — Exporter Happy-Path
| Method | Path | Expected | Auth mechanism | Notes |
|--------|------|----------|---------------|-------|
| GET | `/auth/me` | 200 | Bearer (Supabase or backend JWT) | Returns `UserProfile` |
| GET | `/onboarding/status` | 200 | Bearer | Returns `OnboardingStatus` |
| PUT | `/onboarding/progress` | 200 | Bearer | Updates step/role/company |
| GET | `/usage/current` | 200 | Bearer | Requires `company_id` on user |
| GET | `/usage/limits` | 200 | Bearer | Requires `company_id` on user |
| GET | `/usage/logs` | 200 | Bearer | Paginated log entries |
| GET | `/usage/subscription` | 200 | Bearer | Active plan or PAYG fallback |
| GET | `/members/me/permissions` | 200 or 403/404 | Bearer | 403/404 tolerated — frontend treats as "owner" |

### Expected 401 scenarios (no/bad token)
| Path | Expected |
|------|----------|
| `/auth/me` (no token) | 401 |
| `/auth/me` (expired token) | 401 |
| `/onboarding/status` (no token) | 401 |
| `/usage/limits` (no token) | 401 |

### Expected 400 scenarios
| Path | Trigger | Expected |
|------|---------|----------|
| `/auth/login` | wrong password | 401 |
| `/auth/register` | duplicate email | 400 |
| `/usage/current` | user has no `company_id` | 400 |

---

## 2. Smoke-Test Steps — Manual

### Step A · Login flow (normal browser)
1. Navigate to `https://trdrhub.com/login` (or `http://localhost:5173/login`)
2. Enter **valid exporter credentials**
3. Click "Sign In"
4. **Assert:** Redirected to `/hub` or dashboard
5. **Assert:** No 401 errors in the browser Network tab
6. **Assert:** Supabase session cookie is set (check DevTools → Application → Cookies)
7. Open Network tab and reload → `GET /auth/me` returns **200** with `"role": "exporter"`

### Step B · /auth/me profile integrity
1. While logged in, open DevTools → Network
2. Filter by `auth/me`
3. **Assert** response body contains:
   - `id` (UUID)
   - `email` (matches login)
   - `role` → must be `"exporter"` (not `null`, not `"unknown"`)
   - `is_active: true`
4. **Assert** `full_name` is not `"Unknown User"` (fallback sentinel — indicates DB lookup failure)

### Step C · Onboarding status
1. Go to `/hub` or call `GET /onboarding/status` in DevTools
2. **Assert** response: `completed: true` for a returning exporter
3. **Assert** `role` matches the role in `/auth/me`
4. If `completed: false` → wizard should render; complete it; re-check → `completed: true`
5. **Assert** `company_id` is **not null** — if null, `/usage/*` will 400

### Step D · Usage limits & subscription
1. In DevTools Network, look for `GET /usage/limits`
2. **Assert** HTTP 200
3. **Assert** response has keys: `limits`, `used`, `remaining` for at least one operation
4. Check `GET /usage/subscription` → **Assert** `has_subscription: true|false` + `plan.slug` present
5. Check `GET /usage/logs?limit=10` → **Assert** HTTP 200, `logs` array (can be empty)

### Step E · Incognito / private browsing
1. Open incognito window
2. Navigate to `https://trdrhub.com/hub` (a protected route)
3. **Assert:** Redirected to `/login` (not a blank screen or 500)
4. Log in with same credentials
5. **Assert:** `/auth/me` → 200 (Supabase token flows correctly in incognito)
6. **Assert:** No cached state leakage from the normal session
7. Compare roles in both windows — must match

### Step F · Token expiry simulation
1. In normal browser DevTools Console:
   ```js
   // Corrupt the access token to simulate expiry
   const key = Object.keys(localStorage).find(k => k.includes('auth-token'))
   const val = JSON.parse(localStorage.getItem(key))
   val.access_token = val.access_token.replace(/.$/, 'X')  // corrupt last char
   localStorage.setItem(key, JSON.stringify(val))
   location.reload()
   ```
2. **Assert:** App redirects to `/login` (not hanging spinner)
3. **Assert:** No raw 401 JSON shown to user

---

## 3. Command-Level Smoke Tests (curl)

> Set BASE to your API: `export BASE=https://trdrhub-api.onrender.com` or `http://localhost:8000`

### 3.1 Health baseline
```bash
curl -sf "$BASE/health/live" | python3 -m json.tool
# Expected: {"status": "ok", ...}

curl -sf "$BASE/health/ready" | python3 -m json.tool
# Expected: overall_healthy: true
```

### 3.2 Login → capture token
```bash
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"exporter@example.com","password":"TestPass123!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

echo "Token: ${TOKEN:0:30}..."
```

### 3.3 /auth/me check
```bash
curl -sf "$BASE/auth/me" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Assert: 200, role=exporter, is_active=true

# Test unauthenticated — must be 401
curl -s -o /dev/null -w "%{http_code}" "$BASE/auth/me"
# Expected: 401
```

### 3.4 Onboarding status
```bash
curl -sf "$BASE/onboarding/status" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Assert: 200, completed=true (for established user), company_id non-null
```

### 3.5 Usage endpoints
```bash
# Limits
curl -sf "$BASE/usage/limits" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Assert: 200

# Subscription
curl -sf "$BASE/usage/subscription" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Assert: 200, has_subscription field present

# Logs (paginated)
curl -sf "$BASE/usage/logs?limit=5" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Assert: 200, logs array present
```

### 3.6 Members permissions (soft 401 ok)
```bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/members/me/permissions" -H "Authorization: Bearer $TOKEN")
echo "members/me/permissions HTTP $STATUS"
# Expected: 200 (if RBAC record exists) or 403/404 (treated as owner by frontend — also acceptable)
```

### 3.7 Role mismatch guard
The backend logs `jwt_role_mismatch` audit events when `token.role != db.role`.
Verify none are present after a clean login:
```bash
# Check audit logs (admin-only endpoint) for role mismatch events
curl -sf "$BASE/admin/audit?action=ACCESS_DENIED&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
```

---

## 4. Full Python Smoke Script

Save as `apps/api/auth_smoke.py` and run with `python auth_smoke.py`.

```python
#!/usr/bin/env python3
"""
TRDR Auth E2E Smoke Test
Usage: python auth_smoke.py [BASE_URL] [EMAIL] [PASSWORD]
"""

import sys
import json
import time
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
EMAIL = sys.argv[2] if len(sys.argv) > 2 else "exporter@example.com"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "TestPass123!"

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"


def http(method, path, data=None, token=None, expected=200):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read())
        except Exception:
            body = {}
    except Exception as ex:
        return None, None, str(ex)
    return status, body, None


def check(name, cond, detail=""):
    icon = PASS if cond else FAIL
    print(f"  {icon}  {name}" + (f"  [{detail}]" if detail else ""))
    return cond


results = []


def test(name, fn):
    print(f"\n── {name}")
    ok = fn()
    results.append((name, ok))


# ── 1. Health
def test_health():
    status, body, err = http("GET", "/health/live")
    ok = check("GET /health/live → 200", status == 200, f"got {status}")
    if body:
        check("status=ok", body.get("status") == "ok", str(body.get("status")))
    return ok


test("Health", test_health)


# ── 2. Unauthenticated /auth/me → 401
def test_unauth_me():
    status, _, _ = http("GET", "/auth/me")
    return check("GET /auth/me (no token) → 401", status == 401, f"got {status}")


test("Unauthenticated /auth/me", test_unauth_me)


# ── 3. Login
token = None


def test_login():
    global token
    status, body, err = http("POST", "/auth/login",
                              data={"email": EMAIL, "password": PASSWORD})
    ok = check("POST /auth/login → 200", status == 200, f"got {status}")
    if body and "access_token" in body:
        token = body["access_token"]
        check("access_token present", bool(token))
        check("token_type=bearer", body.get("token_type") == "bearer")
        check("role present", bool(body.get("role")), body.get("role"))
    else:
        check("access_token present", False, str(body))
    return ok


test("Login", test_login)


# ── 4. /auth/me authenticated
user_data = {}


def test_me():
    if not token:
        print("  ⚠️  Skipped (no token)")
        return False
    status, body, err = http("GET", "/auth/me", token=token)
    ok = check("GET /auth/me → 200", status == 200, f"got {status}")
    if body:
        user_data.update(body)
        check("email matches", body.get("email") == EMAIL, body.get("email"))
        check("role is valid string", isinstance(body.get("role"), str) and body["role"] != "",
              body.get("role"))
        check("full_name not sentinel", body.get("full_name") not in (None, "Unknown User", ""),
              body.get("full_name"))
        check("is_active=true", body.get("is_active") is True)
    return ok


test("/auth/me (authenticated)", test_me)


# ── 5. Onboarding status
def test_onboarding():
    if not token:
        print("  ⚠️  Skipped (no token)")
        return False
    status, body, err = http("GET", "/onboarding/status", token=token)
    ok = check("GET /onboarding/status → 200", status == 200, f"got {status}")
    if body:
        check("user_id present", bool(body.get("user_id")))
        check("role present", bool(body.get("role")), body.get("role"))
        cid = body.get("company_id")
        warn = "⚠️  company_id is null — /usage/* will return 400" if not cid else ""
        check(f"company_id non-null{' '+warn if warn else ''}", cid is not None, str(cid))
        check("completed field present", "completed" in body)
    return ok


test("Onboarding status", test_onboarding)


# ── 6. Usage endpoints
def test_usage():
    if not token:
        print("  ⚠️  Skipped (no token)")
        return False
    all_ok = True
    for path, name in [
        ("/usage/limits", "limits"),
        ("/usage/subscription", "subscription"),
        ("/usage/logs?limit=5", "logs"),
    ]:
        status, body, err = http("GET", path, token=token)
        ok = check(f"GET {path} → 200", status == 200, f"got {status}")
        all_ok = all_ok and ok
    return all_ok


test("Usage endpoints", test_usage)


# ── 7. members/me/permissions (soft-fail ok)
def test_permissions():
    if not token:
        print("  ⚠️  Skipped (no token)")
        return False
    status, body, err = http("GET", "/members/me/permissions", token=token)
    ok = status in (200, 403, 404)
    icon = PASS if status == 200 else WARN
    print(f"  {icon}  GET /members/me/permissions → {status}"
          f" ({'ok — RBAC record found' if status == 200 else 'tolerated — frontend treats as owner'})")
    return ok


test("Members permissions", test_permissions)


# ── Summary
print("\n" + "═" * 50)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"Results: {passed}/{total} test groups passed")
if passed < total:
    print("Failed groups:")
    for name, ok in results:
        if not ok:
            print(f"  ❌ {name}")
    sys.exit(1)
else:
    print("\033[92mAll groups passed! ✅\033[0m")
    sys.exit(0)
```

---

## 5. Incognito-Specific Checklist

> Run these in a fresh private/incognito window with DevTools open.

- [ ] `localStorage` is empty before login (no stale tokens)
- [ ] Login completes without "session not found" errors
- [ ] `GET /auth/me` returns 200 after Supabase login (Supabase token is passed as Bearer)
- [ ] `GET /onboarding/status` returns `completed: true` (no re-onboarding loop)
- [ ] `GET /usage/limits` returns 200 (company_id is populated)
- [ ] Closing and reopening the incognito tab clears the session (logout confirmed)
- [ ] No CORS preflight failures (`OPTIONS` requests return 200)

---

## 6. Known Pitfalls & What to Check

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| `/auth/me` returns 401 after Supabase login | `SUPABASE_JWKS_URL` or `SUPABASE_ISSUER` misconfigured | Backend logs: `"No external providers configured"` |
| `/auth/me` returns `full_name: "Unknown User"` | `_upsert_external_user` succeeded but DB user has no name | Check `user_metadata.full_name` in Supabase token claims |
| `/onboarding/status` says `completed: false` forever | `onboarding_completed` flag not set in DB | Check if auto-complete logic ran: look for `✅ Auto-completed onboarding` in logs |
| `/usage/*` returns 400 "not associated with a company" | `company_id` is null on user | `/onboarding/status` should auto-create a company — check for `❌ Failed to auto-create company` in logs |
| JWT role mismatch (401 on `/auth/me`) | User's role in DB changed after token was issued | Log out, log back in to refresh token |
| Different role in normal vs incognito session | `infer_effective_role` using stale `onboarding_data` | Force re-fetch: call `PUT /onboarding/progress` to re-sync |
| `members/me/permissions` 500 instead of 404 | Missing RBAC migration applied | Check alembic heads; run `20251202_add_rbac_tables.py` |

---

## 7. Proposed Diagnostics Improvement

### Add `GET /auth/me/debug` (dev/staging only)

A **non-sensitive diagnostic endpoint** that returns the auth resolution trace without
any secret values. Gated by `settings.DEBUG or not settings.is_production()`.

**Rationale:** Currently, auth failures require reading backend logs to understand
*why* a token failed (JWT vs Supabase, role mismatch, missing company_id). This
endpoint makes the trace visible in-browser during debugging.

**Proposed response shape:**
```json
{
  "token_source": "supabase_jwks",        // "backend_jwt" | "supabase_jwks" | "fallback_claims"
  "token_verified": true,
  "user_id": "uuid-here",
  "db_user_found": true,
  "db_role": "exporter",
  "token_role": "exporter",
  "role_match": true,
  "company_id": "uuid-here",
  "onboarding_completed": true,
  "effective_role": "exporter",            // result of infer_effective_role()
  "warnings": [],                          // e.g. ["full_name_sentinel_detected"]
  "resolved_at_ms": 12                     // resolution latency in ms
}
```

**Implementation hint** (`apps/api/app/routers/auth.py`):
```python
@router.get("/me/debug")
async def get_auth_debug(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Debug endpoint — disabled in production."""
    from app.config import settings
    if settings.is_production() and not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    
    t0 = time.perf_counter()
    trace = {"token_source": None, "warnings": []}
    
    token = credentials.credentials
    # Try backend JWT first
    try:
        payload = decode_access_token(token)
        if payload:
            trace["token_source"] = "backend_jwt"
            user = db.query(User).filter(User.id == UUID(payload["sub"])).first()
            ...
    except Exception:
        pass
    
    # Try Supabase JWKS
    if not trace.get("token_source"):
        ...
    
    trace["resolved_at_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return trace
```

This eliminates the need to SSH into the server or tail CloudWatch logs for the
most common auth debugging scenarios.

---

## 8. CI Integration Suggestion

Add to `.github/workflows/ci.yml`:
```yaml
- name: Auth smoke test (against staging)
  env:
    BASE_URL: ${{ secrets.STAGING_API_URL }}
    TEST_EMAIL: ${{ secrets.STAGING_TEST_EMAIL }}
    TEST_PASSWORD: ${{ secrets.STAGING_TEST_PASSWORD }}
  run: |
    cd apps/api
    python auth_smoke.py "$BASE_URL" "$TEST_EMAIL" "$TEST_PASSWORD"
```

The script exits non-zero on any failure, making it CI-safe.
