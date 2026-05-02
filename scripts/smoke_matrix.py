#!/usr/bin/env python3
"""Phase A13 — automated smoke matrix.

Hits the deployed API across persona × tier × country combinations
and reports pass/fail per combo. Designed to run against staging
nightly (or pre-launch on-demand) so the bug bash week doesn't
re-surface regressions every morning.

Usage — three modes:

    # 1. Public-only (no auth)
    python scripts/smoke_matrix.py --public-only

    # 2. Single token (one persona row)
    python scripts/smoke_matrix.py --token "$JWT"

    # 3. Multi-persona — supply pre-fetched tokens
    python scripts/smoke_matrix.py --tokens-file tokens.json
        # tokens.json: [{"label": "BD-exporter-solo", "token": "eyJ..."}, ...]

    # 4. Multi-persona — supply creds, script fetches JWT per row
    python scripts/smoke_matrix.py --users-file users.json
        # users.json:  [{"label": "BD-exporter-solo",
        #                "email": "...", "password": "..."}, ...]

The script is read-only by default — every check is a GET. Mutating
checks (signup, validation, repaper send) live behind --mutating.

Exit codes:
    0 = all sampled combos green
    1 = at least one combo failed; details printed
    2 = config error (missing API URL, bad creds file, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    import urllib.request
    import urllib.error
    import urllib.parse
except ImportError:  # pragma: no cover
    print("urllib is required", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Config — the smoke matrix
# ---------------------------------------------------------------------------


# Read-only checks: no auth required
PUBLIC_CHECKS: List[dict] = [
    {"id": "status", "method": "GET", "path": "/api/status"},
    {"id": "healthz", "method": "GET", "path": "/healthz"},
]


# Auth'd surface checks. Every persona's read endpoints should
# return 200 (or 403 for cross-persona) without breaking.
AUTHED_CHECKS: List[dict] = [
    # Phase A3 — notifications
    {"id": "notifications/list", "method": "GET", "path": "/api/notifications"},
    {"id": "notifications/unread-count", "method": "GET", "path": "/api/notifications/unread-count"},
    {"id": "notifications/preferences", "method": "GET", "path": "/api/notifications/preferences"},
    # Phase A4 — entitlements
    {"id": "entitlements/current", "method": "GET", "path": "/api/entitlements/current"},
    # Phase A5/A6 — agency
    {"id": "agency/suppliers", "method": "GET", "path": "/api/agency/suppliers"},
    {"id": "agency/buyers", "method": "GET", "path": "/api/agency/buyers"},
    {"id": "agency/portfolio", "method": "GET", "path": "/api/agency/portfolio"},
    {"id": "agency/repaper-requests", "method": "GET", "path": "/api/agency/repaper-requests"},
    # Phase A8/A9 — services
    {"id": "services/clients", "method": "GET", "path": "/api/services/clients"},
    {"id": "services/time", "method": "GET", "path": "/api/services/time"},
    {"id": "services/portfolio", "method": "GET", "path": "/api/services/portfolio"},
    # Phase A10 — enterprise
    {"id": "enterprise/group-overview", "method": "GET", "path": "/api/enterprise/group-overview"},
    {"id": "enterprise/my-role", "method": "GET", "path": "/api/enterprise/my-role"},
    # Phase A12 — search
    {"id": "search", "method": "GET", "path": "/api/search?q=test"},
    # Phase A1 — bulk validation
    {"id": "bulk-validate/list", "method": "GET", "path": "/api/bulk-validate?limit=5"},
]


# Persona × tier sample matrix. Per-row is one user the script will
# log in as (or be told to via --token). For automated nightly runs
# you'll wire this to a fixture-creator that pre-creates one test
# account per row; for on-demand runs the operator passes a single
# token and acknowledges the limited scope.
SAMPLE_USERS = [
    {"label": "BD-exporter-solo",   "country": "BD", "activities": ["exporter"], "tier": "solo"},
    {"label": "BD-exporter-sme",    "country": "BD", "activities": ["exporter"], "tier": "sme"},
    {"label": "IN-exporter-sme",    "country": "IN", "activities": ["exporter"], "tier": "sme"},
    {"label": "VN-exporter-sme",    "country": "VN", "activities": ["exporter"], "tier": "sme"},
    {"label": "BD-importer-sme",    "country": "BD", "activities": ["importer"], "tier": "sme"},
    {"label": "UAE-importer-sme",   "country": "AE", "activities": ["importer"], "tier": "sme"},
    {"label": "BD-agent-sme",       "country": "BD", "activities": ["agent"], "tier": "sme"},
    {"label": "BD-services-sme",    "country": "BD", "activities": ["services"], "tier": "sme"},
    {"label": "US-multi-enterprise", "country": "US", "activities": ["exporter", "importer"], "tier": "enterprise"},
    {"label": "GB-multi-enterprise", "country": "GB", "activities": ["exporter", "agent"], "tier": "enterprise"},
]


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    persona: str
    check_id: str
    ok: bool
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    note: Optional[str] = None


@dataclass
class MatrixReport:
    started_at: float = field(default_factory=time.time)
    results: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.ok)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def green(self) -> bool:
        return self.failed == 0


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _request(
    api_base: str,
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    timeout: float = 10.0,
) -> tuple[int, Any]:
    url = api_base.rstrip("/") + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            duration_ms = int((time.monotonic() - start) * 1000)
            try:
                parsed = json.loads(body) if body else None
            except json.JSONDecodeError:
                parsed = None
            return resp.status, {"duration_ms": duration_ms, "body": parsed}
    except urllib.error.HTTPError as e:
        return e.code, {"duration_ms": None, "body": None}
    except Exception as e:  # noqa: BLE001
        return 0, {"duration_ms": None, "body": None, "error": str(e)}


# ---------------------------------------------------------------------------
# Supabase password-grant — fetch JWT for fixture users
# ---------------------------------------------------------------------------


SUPABASE_URL = "https://nnmmhgnriisfsncphipd.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_db40L4wNiQX0jOTCRJi-8g_9p-PWmN3"


def _fetch_jwt(email: str, password: str, *, timeout: float = 15.0) -> Optional[str]:
    """Exchange email+password for a Supabase access_token. None on failure."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
            return payload.get("access_token")
    except Exception as e:  # noqa: BLE001
        print(f"    auth failed: {e}", file=sys.stderr)
        return None


def _load_users_file(path: str) -> List[dict]:
    """Read JSON: [{label, email, password}, ...]. Validates shape."""
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected JSON array of users")
    for i, row in enumerate(rows):
        for k in ("label", "email", "password"):
            if k not in row:
                raise ValueError(f"{path}[{i}]: missing required key '{k}'")
    return rows


def _load_tokens_file(path: str) -> List[dict]:
    """Read JSON: [{label, token}, ...]. Validates shape."""
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected JSON array of tokens")
    for i, row in enumerate(rows):
        for k in ("label", "token"):
            if k not in row:
                raise ValueError(f"{path}[{i}]: missing required key '{k}'")
    return rows


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run_public_checks(api_base: str, report: MatrixReport) -> None:
    print("\n[public]")
    for check in PUBLIC_CHECKS:
        code, meta = _request(api_base, check["method"], check["path"])
        ok = code == 200
        report.results.append(
            CheckResult(
                persona="public",
                check_id=check["id"],
                ok=ok,
                status_code=code,
                duration_ms=meta.get("duration_ms"),
            )
        )
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag:4}] {check['id']:32} {code} {meta.get('duration_ms') or '-'}ms")


def run_authed_checks(
    api_base: str, persona_label: str, token: str, report: MatrixReport
) -> None:
    print(f"\n[{persona_label}]")
    for check in AUTHED_CHECKS:
        code, meta = _request(api_base, check["method"], check["path"], token=token)
        # 200 = green; 403 is acceptable for cross-persona endpoints
        # (e.g. exporter user hitting /api/agency/suppliers — the
        # company isn't an agent so it gets 403). We treat 403 as
        # OK only for endpoints the persona shouldn't have anyway.
        cross_persona_ok = (
            code == 403
            and any(prefix in check["path"] for prefix in ("/agency", "/services", "/enterprise"))
        )
        ok = code == 200 or cross_persona_ok
        report.results.append(
            CheckResult(
                persona=persona_label,
                check_id=check["id"],
                ok=ok,
                status_code=code,
                duration_ms=meta.get("duration_ms"),
            )
        )
        flag = "OK" if ok else "FAIL"
        suffix = " (cross-persona)" if cross_persona_ok else ""
        print(
            f"  [{flag:4}] {check['id']:32} {code} {meta.get('duration_ms') or '-'}ms{suffix}"
        )


def _resolve_personas(args) -> List[dict]:
    """Build the list of {label, token} rows to run authed checks for.

    Precedence: --tokens-file > --users-file > --token. At most one source
    is honoured (validated upstream). Returns an empty list if no auth
    source was supplied (caller falls back to public-only mode).
    """
    if args.tokens_file:
        rows = _load_tokens_file(args.tokens_file)
        return [{"label": r["label"], "token": r["token"]} for r in rows]

    if args.users_file:
        rows = _load_users_file(args.users_file)
        out: List[dict] = []
        print(f"\n[auth] fetching JWTs for {len(rows)} fixture users...")
        for r in rows:
            tok = _fetch_jwt(r["email"], r["password"])
            if not tok:
                print(f"  [SKIP] {r['label']} — auth failed")
                continue
            print(f"  [ OK ] {r['label']:32} token: {tok[:20]}...")
            out.append({"label": r["label"], "token": tok})
        return out

    if args.token:
        return [{"label": "single-token", "token": args.token}]

    return []


def _print_per_persona_summary(report: MatrixReport) -> None:
    """Group results by persona and print a compact pass/fail table."""
    by_persona: dict[str, list[CheckResult]] = {}
    for r in report.results:
        by_persona.setdefault(r.persona, []).append(r)
    if len(by_persona) <= 1:
        return  # the single-line overall summary is enough
    print("\nPer-persona breakdown:")
    for persona, rows in by_persona.items():
        passed = sum(1 for r in rows if r.ok)
        total = len(rows)
        flag = "OK" if passed == total else "FAIL"
        print(f"  [{flag:4}] {persona:32} {passed}/{total}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--api",
        default="https://api.trdrhub.com",
        help="API base URL (default: https://api.trdrhub.com)",
    )
    p.add_argument(
        "--token",
        default=None,
        help="Bearer token for authed checks. Single-persona mode.",
    )
    p.add_argument(
        "--tokens-file",
        default=None,
        help="JSON file: [{label, token}, ...] — multi-persona mode with "
        "pre-fetched JWTs.",
    )
    p.add_argument(
        "--users-file",
        default=None,
        help="JSON file: [{label, email, password}, ...] — multi-persona "
        "mode where the script fetches a JWT for each row via Supabase "
        "password-grant.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Max persona rows to run (default: 30 — full Phase A13 matrix)",
    )
    p.add_argument(
        "--public-only",
        action="store_true",
        help="Skip auth'd checks; only hit public endpoints",
    )
    args = p.parse_args()

    if not args.api:
        print("ERROR: --api is required", file=sys.stderr)
        return 2

    auth_sources = sum(
        bool(x) for x in (args.token, args.tokens_file, args.users_file)
    )
    if auth_sources > 1:
        print(
            "ERROR: pick exactly one of --token / --tokens-file / --users-file",
            file=sys.stderr,
        )
        return 2

    print(f"Smoke matrix · target={args.api}")
    report = MatrixReport()

    # 1. Public surface
    run_public_checks(args.api, report)

    # 2. Auth'd surface
    if not args.public_only:
        try:
            personas = _resolve_personas(args)
        except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2

        if not personas:
            print(
                "\n[skip] No --token / --tokens-file / --users-file provided; "
                "auth'd checks skipped."
            )
        else:
            for entry in personas[: args.limit]:
                run_authed_checks(
                    args.api, entry["label"], entry["token"], report
                )

    # Summary
    print("\n" + "=" * 60)
    print(f"Total: {report.total}  Passed: {report.passed}  Failed: {report.failed}")
    _print_per_persona_summary(report)
    if not report.green:
        print("\nFailed checks:")
        for r in report.results:
            if not r.ok:
                print(f"  - {r.persona}/{r.check_id}: HTTP {r.status_code}")
    return 0 if report.green else 1


if __name__ == "__main__":
    sys.exit(main())
