# apps/api/app/services/extraction/docs_46a_parser.py

import re

from typing import List, Dict, Optional


def _clean(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return re.sub(r"\s+", " ", s.strip())


def parse_docs_46A(text: str) -> List[Dict]:
    """
    Converts 46A – Documents Required block into structured items.
    """
    if not text:
        return []

    lines = [
        _clean(l) for l in text.split("\n")
        if _clean(l) and len(_clean(l)) > 3
    ]

    results = []

    for line in lines:
        l = line.lower()

        # --- Commercial Invoice
        if "invoice" in l:
            copies = None
            cm = re.search(r"(\d+)\s*cop", l)
            if cm:
                copies = int(cm.group(1))

            results.append({
                "type": "commercial_invoice",
                "copies": copies,
                "notes": line
            })
            continue

        # --- Bill of Lading
        if "bill of lading" in l or "b/l" in l:
            results.append({
                "type": "bill_of_lading",
                "copies": "full set" if "full set" in l else None,
                "freight": "collect" if "freight collect" in l else None,
                "notes": line
            })
            continue

        # --- Packing List
        if "packing list" in l:
            cp = re.search(r"(\d+)\s*cop", l)
            results.append({
                "type": "packing_list",
                "copies": int(cp.group(1)) if cp else None,
                "notes": line
            })
            continue

        # --- Certificate of Origin
        if "certificate of origin" in l:
            issuer = None
            if "epb" in l:
                issuer = "EPB"
            if "chamber" in l:
                issuer = "Chamber"

            results.append({
                "type": "certificate_of_origin",
                "issuer": issuer,
                "notes": line
            })
            continue

        # --- Inspection Certificate
        if "inspection" in l and "certificate" in l:
            issuer = None
            if "sgs" in l:
                issuer = "SGS"
            if "intertek" in l:
                issuer = "Intertek"

            results.append({
                "type": "inspection_certificate",
                "issuer": issuer,
                "notes": line
            })
            continue

        # --- Beneficiary Certificate
        if "beneficiary certificate" in l:
            results.append({
                "type": "beneficiary_certificate",
                "notes": line
            })
            continue

        # --- Fallback Unknown
        results.append({
            "type": "other",
            "notes": line
        })

    return results

