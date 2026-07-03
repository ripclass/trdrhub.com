"""Sanctions sentinel e2e — run after RulHub billing resumes (~2026-07-05).

Verifies the Phase 2 acceptance with the deterministic test fixtures:
    RULHUB TEST HIT             -> match / block
    RULHUB TEST POSSIBLE MATCH  -> potential_match / review
    RULHUB TEST CLEAR           -> clear

Requires an rh_test_* API key (test keys bypass quota and return fixtures):

    RULHUB_API_KEY=rh_test_xxx apps/api/venv/Scripts/python scripts/sanctions_sentinel_e2e.py

The script calls RulHub POST /v1/screen/sanctions directly, then runs each
raw response through trdrhub's fail-closed mapping
(app.services.sanctions_rulhub.map_rulhub_result) — the same path the
/api/sanctions/screen/* endpoints use — and asserts the mapped statuses.
"""

import asyncio
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "apps" / "api"))

EXPECTED = {
    "RULHUB TEST HIT": ("match", "block"),
    "RULHUB TEST POSSIBLE MATCH": ("potential_match", "review"),
    "RULHUB TEST CLEAR": ("clear", None),
}


async def main() -> int:
    key = os.getenv("RULHUB_API_KEY", "")
    if not key.startswith("rh_test_"):
        print(f"WARNING: RULHUB_API_KEY does not look like a test key ({key[:8]}…) — "
              "sentinel fixtures only fire in test mode.")

    from app.services.sanctions_rulhub import map_rulhub_result
    from app.services.rulhub_client import get_rulhub_client

    client = get_rulhub_client()
    failures = 0
    for name, (want_status, want_action) in EXPECTED.items():
        try:
            raw = await client.screen_sanctions(entity=name)
        except Exception as exc:
            print(f"FAIL  {name}: RulHub call errored: {exc}")
            failures += 1
            continue
        mapped = map_rulhub_result(raw, query=name, screening_type="party", expect_list_match=True)
        got_status = mapped["status"]
        got_action = next((m["action"] for m in mapped["matches"]), None)
        ok = got_status == want_status and (want_action is None or got_action == want_action)
        print(f"{'PASS' if ok else 'FAIL'}  {name}: status={got_status} action={got_action} "
              f"(want {want_status}/{want_action})")
        if not ok:
            failures += 1

    print("\nAll sentinels PASS" if failures == 0 else f"\n{failures} sentinel(s) FAILED")
    return failures


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
