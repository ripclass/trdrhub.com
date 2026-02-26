#!/usr/bin/env python3
"""
TRDR Auth E2E Smoke Test
========================

Tests the core auth flow: login → /auth/me → /onboarding/status → /usage/*

Usage:
    python auth_smoke.py [BASE_URL] [EMAIL] [PASSWORD]

Examples:
    python auth_smoke.py http://localhost:8000 exporter@example.com TestPass123!
    python auth_smoke.py https://trdrhub-api.onrender.com test@trdr.io mypass

Exit code 0 = all pass, 1 = one or more failures.
"""

import sys
import json
import time
import urllib.request
import urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
EMAIL = sys.argv[2] if len(sys.argv) > 2 else "exporter@example.com"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "TestPass123!"

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"
INFO = "\033[94mℹ️  INFO\033[0m"


def http(method: str, path: str, data=None, token=None, timeout=15):
    """Make an HTTP request, return (status_code, body_dict, error_str)."""
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw), None
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw.decode(errors="replace")}, None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body = json.loads(raw)
        except Exception:
            body = {"_raw": raw.decode(errors="replace")}
        return e.code, body, None
    except Exception as ex:
        return None, None, str(ex)


def check(name: str, cond: bool, detail: str = "") -> bool:
    icon = PASS if cond else FAIL
    suffix = f"  [{detail}]" if detail else ""
    print(f"    {icon}  {name}{suffix}")
    return cond


# ─────────────────────────────────────────────────────────
# Test state
# ─────────────────────────────────────────────────────────
token: str | None = None
user_data: dict = {}
results: list[tuple[str, bool]] = []


def test(name: str, fn) -> bool:
    print(f"\n── {name}")
    ok = fn()
    results.append((name, ok))
    return ok


# ─────────────────────────────────────────────────────────
# 1. Health baseline
# ─────────────────────────────────────────────────────────
def test_health() -> bool:
    status, body, err = http("GET", "/health/live")
    if err:
        check("/health/live reachable", False, err)
        return False
    ok = check("GET /health/live → 200", status == 200, f"got {status}")
    if body:
        check("status=ok in body", body.get("status") == "ok", str(body.get("status")))
    return ok


test("Health baseline", test_health)


# ─────────────────────────────────────────────────────────
# 2. Unauthenticated /auth/me must be 401
# ─────────────────────────────────────────────────────────
def test_unauth_me() -> bool:
    status, body, err = http("GET", "/auth/me")
    if err:
        check("Network reachable", False, err)
        return False
    return check("GET /auth/me (no token) → 401", status == 401, f"got {status}")


test("Unauthenticated /auth/me → 401", test_unauth_me)


# ─────────────────────────────────────────────────────────
# 3. Bad credentials must be 401/422
# ─────────────────────────────────────────────────────────
def test_bad_login() -> bool:
    status, _, err = http("POST", "/auth/login",
                          data={"email": EMAIL, "password": "WRONG_PASSWORD_XYZ"})
    if err:
        check("Network reachable", False, err)
        return False
    return check("POST /auth/login (bad pw) → 401", status == 401, f"got {status}")


test("Bad-password login → 401", test_bad_login)


# ─────────────────────────────────────────────────────────
# 4. Successful login
# ─────────────────────────────────────────────────────────
def test_login() -> bool:
    global token
    status, body, err = http("POST", "/auth/login",
                              data={"email": EMAIL, "password": PASSWORD})
    if err:
        check("Network reachable", False, err)
        return False

    ok = check("POST /auth/login → 200", status == 200, f"got {status}")
    if not ok:
        print(f"    {FAIL}  Login response: {json.dumps(body, indent=2)[:300]}")
        return False

    token = (body or {}).get("access_token")
    check("access_token present", bool(token), "(none)" if not token else "ok")
    check("token_type=bearer", body.get("token_type") == "bearer", str(body.get("token_type")))
    check("role present", bool(body.get("role")), str(body.get("role")))
    check("expires_in > 0", (body.get("expires_in") or 0) > 0, str(body.get("expires_in")))
    return ok and bool(token)


test("Login (valid credentials)", test_login)


# ─────────────────────────────────────────────────────────
# 5. /auth/me authenticated
# ─────────────────────────────────────────────────────────
def test_me() -> bool:
    if not token:
        print(f"    {WARN}  Skipped — no token from login")
        return False

    t0 = time.perf_counter()
    status, body, err = http("GET", "/auth/me", token=token)
    latency_ms = round((time.perf_counter() - t0) * 1000)

    if err:
        check("/auth/me reachable", False, err)
        return False

    ok = check("GET /auth/me → 200", status == 200, f"got {status}")
    if not ok:
        print(f"    {FAIL}  Response: {json.dumps(body, indent=2)[:300]}")
        return False

    user_data.update(body)
    check(f"latency < 3000ms", latency_ms < 3000, f"{latency_ms}ms")
    check("email matches", body.get("email") == EMAIL, str(body.get("email")))
    check("role is valid string", isinstance(body.get("role"), str) and bool(body.get("role")),
          str(body.get("role")))

    # Sentinel check — "Unknown User" means DB lookup failed but fallback ran
    sentinel = body.get("full_name") in (None, "Unknown User", "")
    if sentinel:
        print(f"    {WARN}  full_name is sentinel '{body.get('full_name')}' — "
              f"DB upsert may have produced a stub user")
    else:
        check("full_name not sentinel", True, str(body.get("full_name")))

    check("is_active=true", body.get("is_active") is True, str(body.get("is_active")))
    check("id present", bool(body.get("id")))
    return ok


test("/auth/me (authenticated)", test_me)


# ─────────────────────────────────────────────────────────
# 6. Onboarding status
# ─────────────────────────────────────────────────────────
def test_onboarding() -> bool:
    if not token:
        print(f"    {WARN}  Skipped — no token from login")
        return False

    status, body, err = http("GET", "/onboarding/status", token=token)
    if err:
        check("/onboarding/status reachable", False, err)
        return False

    ok = check("GET /onboarding/status → 200", status == 200, f"got {status}")
    if not ok:
        print(f"    {FAIL}  Response: {json.dumps(body, indent=2)[:300]}")
        return False

    check("user_id present", bool(body.get("user_id")))
    check("role present", bool(body.get("role")), str(body.get("role")))
    check("completed field present", "completed" in body)

    cid = body.get("company_id")
    if not cid:
        print(f"    {WARN}  company_id is null — /usage/* endpoints will return 400. "
              f"Check onboarding auto-create logic in backend logs.")
        check("company_id non-null", False, "null")
    else:
        check("company_id non-null", True, str(cid)[:18] + "…")

    # Role consistency
    if user_data.get("role") and body.get("role"):
        # Note: /auth/me role and /onboarding role may differ (infer_effective_role vs raw)
        # Just warn rather than fail
        if user_data["role"] != body["role"]:
            print(f"    {WARN}  role differs: /auth/me={user_data['role']} "
                  f"vs /onboarding/status={body['role']} — check infer_effective_role()")

    return ok


test("Onboarding status", test_onboarding)


# ─────────────────────────────────────────────────────────
# 7. Usage endpoints
# ─────────────────────────────────────────────────────────
def test_usage() -> bool:
    if not token:
        print(f"    {WARN}  Skipped — no token from login")
        return False

    all_ok = True
    for path, key_check in [
        ("/usage/limits", None),
        ("/usage/subscription", "has_subscription"),
        ("/usage/logs?limit=5", "logs"),
        ("/usage/current", None),
    ]:
        status, body, err = http("GET", path, token=token)
        if err:
            check(f"GET {path} reachable", False, err)
            all_ok = False
            continue

        # 400 = no company_id — not a real auth failure
        if status == 400:
            print(f"    {WARN}  GET {path} → 400 (user has no company_id; "
                  f"fix: complete onboarding)")
            continue

        ok = check(f"GET {path} → 200", status == 200, f"got {status}")
        all_ok = all_ok and ok

        if ok and key_check and body:
            check(f"  '{key_check}' field present", key_check in body,
                  str(list(body.keys())[:5]))

    return all_ok


test("Usage endpoints", test_usage)


# ─────────────────────────────────────────────────────────
# 8. members/me/permissions — soft-fail acceptable
# ─────────────────────────────────────────────────────────
def test_permissions() -> bool:
    if not token:
        print(f"    {WARN}  Skipped — no token from login")
        return False

    status, body, err = http("GET", "/members/me/permissions", token=token)
    if err:
        check("/members/me/permissions reachable", False, err)
        return False

    acceptable = status in (200, 403, 404)
    if status == 200:
        print(f"    {PASS}  GET /members/me/permissions → 200 (RBAC record found)")
    elif status in (403, 404):
        print(f"    {WARN}  GET /members/me/permissions → {status} "
              f"(tolerated — frontend treats missing RBAC as 'owner')")
    else:
        print(f"    {FAIL}  GET /members/me/permissions → {status} (unexpected)")

    return acceptable


test("Members permissions (soft-fail ok)", test_permissions)


# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
print("\n" + "═" * 55)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"  Results: {passed}/{total} test groups passed")

if passed < total:
    failed = [name for name, ok in results if not ok]
    print(f"\n  {FAIL}  Failed groups:")
    for name in failed:
        print(f"    • {name}")
    print()
    sys.exit(1)
else:
    print(f"\n  \033[92mAll {total} test groups passed! ✅\033[0m")
    print()
    sys.exit(0)
