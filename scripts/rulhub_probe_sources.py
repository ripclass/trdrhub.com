"""
Ancillary probe: try different `rules` source filters to see whether
RulHub will engage UCP600 and ISBP821 deep rules if we ask explicitly.

The primary probe (rulhub_probe.py) uses no `rules` filter — server
default. This probe hits /v1/validate/set four ways:

  1. no filter          (current trdrhub behaviour)
  2. rules="crossdoc"   (explicit crossdoc only)
  3. rules="ucp600"     (UCP600 core)
  4. rules="isbp821"    (ISBP821 deep rules)

Reports finding counts per source so we can see which rule catalogs
actually fire.
"""
import os
import sys

import requests

# Import the payload from the main probe — keep payloads in sync.
sys.path.insert(0, os.path.dirname(__file__))
from rulhub_probe import DOCUMENTS, RULHUB_URL, is_engine_error  # noqa: E402


def probe(key, rules_filter=None, jurisdiction="bd"):
    payload = {"documents": DOCUMENTS, "jurisdiction": jurisdiction}
    if rules_filter:
        payload["rules"] = rules_filter
    resp = requests.post(
        f"{RULHUB_URL}/v1/validate/set",
        json=payload,
        headers={"Content-Type": "application/json", "X-API-Key": key},
        timeout=60,
    )
    if resp.status_code != 200:
        return {"error": resp.status_code, "body": resp.text[:400]}
    data = resp.json()
    data = data.get("data", data)
    disc = data.get("discrepancies") or []
    cross = (
        data.get("cross_document_discrepancies")
        or data.get("cross_doc_issues")
        or []
    )
    all_findings = list(disc) + list(cross)
    with_evidence = [f for f in all_findings if f.get("field_a")]
    engine_errs = [f for f in all_findings if is_engine_error(f)]
    return {
        "compliant": data.get("compliant"),
        "score": data.get("score"),
        "rules_checked": data.get("rules_checked") or data.get("rules_evaluated"),
        "total": len(all_findings),
        "with_evidence": len(with_evidence),
        "engine_errors": len(engine_errs),
        "real": len(all_findings) - len(engine_errs),
        "sample_ids": [(f.get("rule_id") or "?", f.get("severity") or "?")
                       for f in all_findings[:10]],
    }


def main():
    key = os.environ.get("RULHUB_API_KEY")
    if not key:
        print("ERROR: set RULHUB_API_KEY env var", file=sys.stderr)
        return 1

    filters = [None, "crossdoc", "ucp600", "isbp821", "isbp745", "ucp"]
    print(f"{'rules filter':<15} {'HTTP':<5} {'score':<8} {'total':<6} {'evidence':<9} {'engine':<7} {'real':<5}")
    print("-" * 70)
    for rf in filters:
        result = probe(key, rules_filter=rf)
        rf_label = rf or "(default)"
        if "error" in result:
            print(f"{rf_label:<15} {result['error']:<5} {result['body'][:60]}")
            continue
        print(
            f"{rf_label:<15} 200   "
            f"{result['score']:<8.4f} "
            f"{result['total']:<6} "
            f"{result['with_evidence']:<9} "
            f"{result['engine_errors']:<7} "
            f"{result['real']:<5}"
        )
        if result["sample_ids"]:
            ids = ", ".join(f"{rid}[{sev}]" for rid, sev in result["sample_ids"][:6])
            print(f"    {ids}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
