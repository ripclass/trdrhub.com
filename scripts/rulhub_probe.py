"""
RulHub /v1/validate/set diagnostic probe.

Sends a minimal IDEAL-SAMPLE-shaped payload that matches what
validation_execution.py builds today (dual-prefix lc/credit +
bl/bill_of_lading + insurance/insurance_doc, _name/_code suffix
variants, derived booleans). Prints a breakdown of the response
so we can tell whether the RulHub ISBP fix is live.

Usage:
    RULHUB_API_KEY=... python scripts/rulhub_probe.py
    # or
    python scripts/rulhub_probe.py --key <key>

Exit codes:
    0 — probe completed (response analyzed, see output)
    1 — request failed (network / 4xx / 5xx)
"""
import argparse
import json
import os
import sys

import requests

RULHUB_URL = os.environ.get("RULHUB_API_URL", "https://api.rulhub.com").rstrip("/")

# Engine-error phrases currently filtered pre-veto on trdrhub
# (apps/api/app/routers/validation/validation_execution.py:2003-2012).
# Any finding matching one of these AND lacking field_a/field_b gets dropped.
ENGINE_ERROR_PHRASES = (
    "unknown condition type",
    "one or both values are not numeric",
    "requires max_days",
    "presentation_period requires",
    "cannot evaluate",
    "insufficient_data",
)

# Minimal LC fields — matches IDEAL SAMPLE shape. Keep in sync with
# validation_execution.py's _rulhub_docs builder (~line 1590-1870).
LC_FIELDS = {
    "lc_number": "LC2026BD001",
    "number": "LC2026BD001",
    "issue_date": "2026-03-15",
    "expiry_date": "2026-10-15",
    "latest_shipment_date": "2026-09-30",
    "amount": 458750.0,
    "available_amount": 458750.0,
    "currency": "USD",
    "currency_code": "USD",
    "applicant": "Global Importers Inc.",
    "applicant_name": "Global Importers Inc.",
    "beneficiary": "Dhaka Knitwear & Exports Ltd.",
    "beneficiary_name": "Dhaka Knitwear & Exports Ltd.",
    "country_of_origin": "BANGLADESH",
    "port_of_loading": "CHITTAGONG",
    "port_of_discharge": "NEW YORK",
    "goods_description": "100% COTTON KNITTED T-SHIRTS",
    "hs_code": "6109.10",
    "incoterms": "FOB CHITTAGONG",
    "partial_shipments_permitted": False,
    "transhipment_prohibited": True,
    "transhipment_allowed": False,
    "irrevocable": True,
    "is_transferred": False,
    "subject_to_ucp": True,
    "insurance_all_risks_required": False,
    "insurance_prohibited": True,  # FOB — buyer arranges
    "cover_note_permitted": False,
    "payment_terms": "SIGHT",
    # Ask C #5 — RulHub vocab is documentary_credit / standby_credit
    # (UCP600 Art 1 enum). SWIFT 40A "IRREVOCABLE" maps to
    # documentary_credit. trdrhub derives this in _derive_lc_booleans.
    "type": "documentary_credit",
    "form_of_documentary_credit": "IRREVOCABLE",
    # Packing-list per-carton requirement — derived from 46A mention.
    "packing_list_per_carton_required": True,
    "per_carton_required": True,
}

INVOICE_FIELDS = {
    "issuer": "Dhaka Knitwear & Exports Ltd.",
    "issuer_name": "Dhaka Knitwear & Exports Ltd.",
    "buyer": "Global Importers Inc.",
    "buyer_name": "Global Importers Inc.",
    "applicant_name": "Global Importers Inc.",
    "currency": "USD",
    "currency_code": "USD",
    "amount": 397050.0,  # intentionally $61,700 short of LC — arithmetic gap
    "total_amount": 397050.0,
    "quantity": 30000,
    "total_quantity": 30000,
    "unit_price": 15.30,  # 15.30 * 30000 = 459000, not 397050 — mismatch
    "goods_description": "100% COTTON KNITTED T-SHIRTS",
    "hs_code": "6109.10",
    "date": "2026-09-20",
    "incoterms": "FOB CHITTAGONG",
    "full_quantity_shipped": True,
    "full_amount_due": True,
    "goods_description_matches_lc": True,
    # IDEAL SAMPLE invoice is unsigned — test that ISBP821-A31 fires.
    "signature_present": False,
    "signed": False,
    "has_signature": False,
    "signature": None,
    "original_marking": "ORIGINAL",
}

BL_FIELDS = {
    "shipper": "Dhaka Knitwear & Exports Ltd.",
    "shipper_name": "Dhaka Knitwear & Exports Ltd.",
    "consignee": "TO ORDER OF ISSUING BANK",
    "consignee_name": "TO ORDER OF ISSUING BANK",
    "notify_party": "Global Importers Inc.",
    "notify_party_name": "Global Importers Inc.",
    "carrier": "MAERSK LINE",          # short-prefix convention
    "carrier_name": "MAERSK LINE",     # long-prefix / _name convention
    "port_of_loading": "CHITTAGONG",
    "port_of_discharge": "NEW YORK",
    "shipment_date": "2026-09-24",
    "on_board_date": "2026-09-24",
    "date_of_shipment": "2026-09-24",
    "vessel_name": "MSC GAYA",
    "voyage_number": "V-4411E",
    "container_number": "MAEU1234567",
    "seal_number": "SL998877",
    "goods_description": "100% COTTON KNITTED T-SHIRTS",
    "freight_terms": "FREIGHT COLLECT",
    "freight_prepaid_marking": False,
    "transhipment": False,
    "transhipment_allowed": False,
    # IDEAL SAMPLE BL is missing the CLEAN ON-BOARD notation
    "on_board_notation_present": False,
    "carrier_identified": True,
    "full_set_required": True,
    "signed_by_authorised_party": True,
    "signature_party": "AS AGENT FOR THE CARRIER",
    "originals_issued": 3,
    "originals_presented": 3,
    "original_set": 3,
    "shipping_marks": "GI/NY/2026/001-300",
    "number_of_packages": 300,
    # Clean-BL / CLEAN ON-BOARD — test ISBP821-E20 with multiple aliases.
    # IDEAL SAMPLE BL lacks CLEAN ON-BOARD notation → all False.
    "clean_bl": False,
    "clean_on_board": False,
    "clean_on_board_notation_present": False,
}

COO_FIELDS = {
    "issuer": "Bangladesh Chamber of Commerce",
    "issuer_name": "Bangladesh Chamber of Commerce",
    "form_type": "GSP FORM A",
    "country_of_origin": "BANGLADESH",
    "goods": "100% COTTON KNITTED T-SHIRTS",
    "goods_description": "100% COTTON KNITTED T-SHIRTS",
    "hs_code": "6109.10",
    "consignee": "Global Importers Inc.",
    "consignee_name": "Global Importers Inc.",
    "date": "2026-09-22",
}

INSURANCE_FIELDS = {
    # FOB Incoterm — insurance is extraneous (seller shouldn't arrange)
    "issuer": "Green Delta Insurance Co.",
    "issuer_name": "Green Delta Insurance Co.",
    # Ask C #23: issuer_type is RulHub's UCP600-28 enum:
    #   insurance_company, underwriter, agent_for_insurer, proxy_for_insurer.
    # trdrhub derives this in the insurance_doc branch of
    # validation_execution.py from the issuer text.
    "issuer_type": "insurance_company",
    "insurer_name": "Green Delta Insurance Co.",
    "currency": "USD",
    "currency_code": "USD",
    "insured_amount": 504625.0,   # 110% of LC
    "effective_date": "2026-09-15",
    "goods_description": "100% COTTON KNITTED T-SHIRTS",
    "risks_covered": "INSTITUTE CARGO CLAUSES (A)",
    "coverage_percentage": 110,
}

PL_FIELDS = {
    "issuer": "Dhaka Knitwear & Exports Ltd.",
    "issuer_name": "Dhaka Knitwear & Exports Ltd.",
    "container_number": "MAEU1234567",
    "seal_number": "SL998877",
    "shipping_marks": "GI/NY/2026/001-300",
    # IDEAL SAMPLE packing list missing carton-wise breakdown
    "total_cartons": None,
    "total_quantity": 30000,
    "number_of_packages": 300,
    # Per-carton detail absent — test CROSSDOC-PL-PER-CARTON-001 with aliases.
    "per_carton_detail": False,
    "has_carton_breakdown": False,
    "per_carton_present": False,
    "carton_wise_breakdown": False,
    "line_items": [],
}

INSPECTION_FIELDS = {
    "issuer": "SGS Bangladesh Ltd.",
    "issuer_name": "SGS Bangladesh Ltd.",
    "goods_description": "100% COTTON KNITTED T-SHIRTS",
    # IDEAL SAMPLE inspection cert has WRONG shipment date (doesn't match BL)
    "shipment_date": "2026-04-20",
    "date_of_inspection": "2026-09-20",
    "date": "2026-09-20",
}

BEN_CERT_FIELDS = {
    "issuer": "Dhaka Knitwear & Exports Ltd.",
    "issuer_name": "Dhaka Knitwear & Exports Ltd.",
    "date": "2026-09-22",
    "statement": "WE HEREBY CERTIFY THAT ONE SET OF NON-NEGOTIABLE DOCS HAS BEEN SENT TO APPLICANT BY COURIER",
}

PRESENTATION_FIELDS = {
    "date": "2026-09-25",
}

# Build full dual-prefix documents list — mirrors validation_execution.py.
# Order matches what the 2026-04-17 session saw in the RulHub raw log.
DOCUMENTS = [
    {"type": "lc", "fields": LC_FIELDS},
    {"type": "credit", "fields": LC_FIELDS},
    {"type": "invoice", "fields": INVOICE_FIELDS},
    {"type": "bl", "fields": BL_FIELDS},
    {"type": "bill_of_lading", "fields": BL_FIELDS},
    {"type": "packing_list", "fields": PL_FIELDS},
    {"type": "coo", "fields": COO_FIELDS},
    {"type": "insurance", "fields": INSURANCE_FIELDS},
    {"type": "insurance_doc", "fields": INSURANCE_FIELDS},
    {"type": "inspection_certificate", "fields": INSPECTION_FIELDS},
    {"type": "beneficiary_certificate", "fields": BEN_CERT_FIELDS},
    {"type": "presentation", "fields": PRESENTATION_FIELDS},
]


def is_engine_error(finding):
    """Replicates _is_rule_engine_error from validation_execution.py:1995."""
    if finding.get("field_a") or finding.get("field_b"):
        return False
    if finding.get("value_a") is not None or finding.get("value_b") is not None:
        return False
    msg = str(finding.get("finding") or finding.get("message") or "").lower()
    return any(p in msg for p in ENGINE_ERROR_PHRASES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("RULHUB_API_KEY"))
    ap.add_argument("--jurisdiction", default="bd")
    ap.add_argument("--raw", action="store_true", help="Dump full raw JSON response")
    args = ap.parse_args()

    if not args.key:
        print("ERROR: set RULHUB_API_KEY env var or pass --key", file=sys.stderr)
        return 1

    url = f"{RULHUB_URL}/v1/validate/set"
    payload = {"documents": DOCUMENTS, "jurisdiction": args.jurisdiction}

    print(f"POST {url}")
    print(f"  documents: {[d['type'] for d in DOCUMENTS]}")
    print(f"  jurisdiction: {args.jurisdiction}")
    print()

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "X-API-Key": args.key},
            timeout=60,
        )
    except requests.RequestException as e:
        print(f"ERROR: request failed: {e}", file=sys.stderr)
        return 1

    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text[:2000])
        return 1

    body = resp.json()
    # Server wraps in {"data": {...}} or returns flat — handle both.
    data = body.get("data", body)

    if args.raw:
        print(json.dumps(data, indent=2, default=str)[:20000])
        return 0

    # ---- Summary ---------------------------------------------------------
    disc = data.get("discrepancies") or []
    crossdoc = (
        data.get("cross_document_discrepancies")
        or data.get("cross_doc_issues")
        or []
    )
    all_findings = list(disc) + list(crossdoc)

    compliant = data.get("compliant")
    score = data.get("score")
    can_proceed = data.get("can_proceed")
    rules_checked = data.get("rules_checked") or data.get("rules_evaluated")
    docs_checked = data.get("documents_checked")

    with_field_a = [f for f in all_findings if f.get("field_a")]
    without_field_a = [f for f in all_findings if not f.get("field_a")]
    engine_errors = [f for f in all_findings if is_engine_error(f)]
    real_after_filter = [f for f in all_findings if not is_engine_error(f)]

    sev = {}
    for f in all_findings:
        s = (f.get("severity") or "unknown").lower()
        sev[s] = sev.get(s, 0) + 1

    print("=" * 60)
    print("RESPONSE SUMMARY")
    print("=" * 60)
    print(f"compliant:          {compliant}")
    print(f"score:              {score}")
    print(f"can_proceed:        {can_proceed}")
    print(f"rules_checked:      {rules_checked}")
    print(f"documents_checked:  {docs_checked}")
    print()
    print(f"discrepancies:      {len(disc)}")
    print(f"cross_document:     {len(crossdoc)}")
    print(f"total findings:     {len(all_findings)}")
    print(f"severity breakdown: {sev}")
    print()
    print("-" * 60)
    print("EVIDENCE QUALITY (the RulHub ISBP fix indicator)")
    print("-" * 60)
    print(f"with field_a populated:   {len(with_field_a):3d}  <- real findings")
    print(f"without field_a:          {len(without_field_a):3d}  <- suspicious, likely engine noise")
    print()
    print(f"matches engine-error filter phrase list: {len(engine_errors)}")
    print(f"passes filter to reach Opus veto:        {len(real_after_filter)}")
    print()

    # ---- Verdict ---------------------------------------------------------
    print("=" * 60)
    print("VERDICT")
    print("=" * 60)
    if len(all_findings) == 0:
        print("[WARN] Zero findings. Either the payload is cleanly compliant (unlikely on")
        print("  IDEAL SAMPLE which has a $61,700 invoice gap) or rules silently")
        print("  passed due to null==null / filter-miss.")
        print("  ->Grep response for 'insufficient_data' markers or bump payload logging.")
    elif len(with_field_a) == 0 and len(engine_errors) == len(all_findings):
        print("[FAIL] ISBP FIX NOT LANDED — every finding is engine noise with null field_a.")
        print("  RulHub rules still fire but condition evaluators return error strings.")
        print("  ->Confirm rulhub-side deploy went out. Surface to Ripon.")
    elif len(with_field_a) >= int(0.8 * len(all_findings)):
        print("[OK] ISBP FIX LOOKS LIVE — most findings carry real field_a evidence.")
        print(f"  {len(real_after_filter)} findings will flow through trdrhub's filter")
        print("  and reach the Opus veto + UI.")
        print("  ->Next step: live trdrhub e2e against IDEAL SAMPLE, verify tab count.")
    else:
        print(f"[WARN] PARTIAL — {len(with_field_a)}/{len(all_findings)} findings carry field_a evidence,")
        print(f"  {len(engine_errors)} still hit the engine-error filter.")
        print("  ->Mixed state. Inspect the per-finding sample below and")
        print("    decide whether the filter phrase list needs tuning.")
    print()

    # ---- Sample findings -------------------------------------------------
    print("-" * 60)
    print("SAMPLE FINDINGS (first 20)")
    print("-" * 60)
    for i, f in enumerate(all_findings[:20], 1):
        rule_id = f.get("rule_id") or f.get("rule") or "?"
        sev_s = f.get("severity") or "?"
        msg = (f.get("finding") or f.get("message") or "")[:120]
        fa = f.get("field_a") or "—"
        va = f.get("value_a") if f.get("value_a") is not None else "—"
        fb = f.get("field_b") or "—"
        vb = f.get("value_b") if f.get("value_b") is not None else "—"
        docs = f.get("documents_involved") or f.get("documents") or []
        engine_flag = " [ENGINE-ERROR]" if is_engine_error(f) else ""
        print(f"{i}. {rule_id} [{sev_s}]{engine_flag}")
        print(f"   msg:       {msg}")
        print(f"   field_a:   {fa} = {va}")
        print(f"   field_b:   {fb} = {vb}")
        print(f"   docs:      {docs}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
