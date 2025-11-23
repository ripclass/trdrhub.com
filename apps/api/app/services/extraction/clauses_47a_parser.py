# apps/api/app/services/extraction/clauses_47a_parser.py

import re

from typing import List, Dict, Optional

_WHITESPACE = re.compile(r"\s+")

def _clean(s: Optional[str]) -> str:
    return _WHITESPACE.sub(" ", s.strip()) if s else ""

_PATTERNS = [
    # generic constraints
    (r"documents must not be dated earlier than lc issue date", "no_backdating", {}),
    (r"any corrections must be authenticated", "auth_corrections", {}),
    (r"third[- ]party documents (?:are )?acceptable except (?:bill of exchange|draft) and invoice", "third_party_docs", {"except": ["bill_of_exchange", "invoice"]}),
    (r"country of origin must be printed on all cartons", "origin_marking", {"medium": "carton_print"}),
    (r"no israeli flag vessels permitted", "flag_restriction", {"flag": "IL"}),
    (r"bin:\s*(?P<bin>\d{9,})", "exporter_bin", {}),
    (r"tin:\s*(?P<tin>[\d\-]{6,})", "exporter_tin", {}),
    (r"discrepancy fee\s*(?P<amt>usd?\s*\d+)", "fee_discrepancy", {}),
    (r"payment charge\s*(?P<amt>usd?\s*\d+)", "fee_payment", {}),
    (r"container must have min\.\s*(?P<days>\d+)\s*days free time", "demurrage_free_time", {}),
    (r"free from azo dyes|eu/us safety standards", "safety_standards", {"refs": ["azo_dyes","eu_us"]}),
]

def tokenize_47a(text: str) -> List[Dict]:
    if not text:
        return []

    t = _clean(text.lower())

    items: List[Dict] = []

    # itemized (1)…(n)
    for raw in re.split(r"(?:^|\n)\s*\d+\)\s*", text, flags=re.I)[1:]:
        chunk = _clean(raw)
        if not chunk:
            continue

        entry = {"type": "other", "raw": chunk, "params": {}}

        # classify by quick heuristics
        if "commercial invoice" in chunk.lower():
            entry["type"] = "commercial_invoice_clause"
        elif "bill of lading" in chunk.lower():
            entry["type"] = "bl_clause"
        elif "packing list" in chunk.lower():
            entry["type"] = "packing_list_clause"
        elif "certificate of origin" in chunk.lower():
            entry["type"] = "coo_clause"
        elif "inspection certificate" in chunk.lower():
            entry["type"] = "inspection_clause"

        # enrich via patterns
        for rx, tcode, extras in _PATTERNS:
            m = re.search(rx, chunk.lower())
            if m:
                entry.setdefault("tokens", []).append({
                    "code": tcode,
                    "params": {**extras, **m.groupdict()}
                })

        items.append(entry)

    return items

