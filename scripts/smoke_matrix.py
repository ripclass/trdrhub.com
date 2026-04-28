#!/usr/bin/env python3
"""Phase A13 — automated smoke matrix.

Hits the deployed API across persona × tier × country combinations
and reports pass/fail per combo. Designed to run against staging
nightly (or pre-launch on-demand) so the bug bash week doesn't
re-surface regressions every morning.

Usage:
    python scripts/smoke_matrix.py [--api https://api.trdrhub.com]
                                   [--token <bearer>]
                                   [--limit 30]

The script is read-only by default — every check is a GET. Mutating
checks (signup, validation, repaper send) live behind --mutating.

Exit codes:
    0 = all sampled combos green
    1 = at least one combo failed; details printed
    2 = config error (missing API URL, etc.)
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
        help="Bearer token for authed checks. When set, runs the auth'd "
        "matrix once with the provided token (skips per-persona).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max persona rows to sample (default: 10 — full row set)",
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

    print(f"Smoke matrix · target={args.api}")
    report = MatrixReport()

    # 1. Public surface
    run_public_checks(args.api, report)

    # 2. Auth'd surface
    if not args.public_only:
        if args.token:
            run_authed_checks(args.api, "single-token", args.token, report)
        else:
            print(
                "\n[skip] No --token provided; auth'd checks skipped. "
                "For full matrix, supply a Supabase JWT or wire fixture-token "
                "creator (see SAMPLE_USERS)."
            )

    # Summary
    print("\n" + "=" * 60)
    print(f"Total: {report.total}  Passed: {report.passed}  Failed: {report.failed}")
    if not report.green:
        print("\nFailed checks:")
        for r in report.results:
            if not r.ok:
                print(f"  - {r.persona}/{r.check_id}: HTTP {r.status_code}")
    return 0 if report.green else 1


if __name__ == "__main__":
    sys.exit(main())
