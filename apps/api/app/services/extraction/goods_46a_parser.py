# apps/api/app/services/extraction/goods_46a_parser.py

import re
from typing import Any, Dict, List, Optional, Tuple

from .hs_code_extractor import extract_hs_codes  # your existing helper

# Normalize common trade units
_UNIT_MAP = {
    "pcs": "PCS",
    "pc": "PCS",
    "piece": "PCS",
    "pieces": "PCS",
    "ctn": "CTNS",
    "ctns": "CTNS",
    "carton": "CTNS",
    "cartons": "CTNS",
    "dz": "DOZ",
    "doz": "DOZ",
    "dozen": "DOZ",
    "kg": "KG",
    "kgs": "KG",
    "kilogram": "KG",
    "kilograms": "KG",
    "g": "G",
    "gram": "G",
    "grams": "G",
    "mt": "MT",
    "ton": "MT",
    "tons": "MT",
    "tonne": "MT",
    "tonnes": "MT",
    "mtr": "MTR",
    "mtrs": "MTR",
    "meter": "MTR",
    "meters": "MTR",
    "m": "MTR",
    "set": "SET",
    "sets": "SET",
    "pair": "PAIR",
    "pairs": "PAIR",
    "pack": "PACK",
    "packs": "PACK",
}

_NUM = r"(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d+)?"
_UNIT = r"(?:pcs?|pieces?|ctns?|cartons?|dz|doz|dozen|kg|kgs|kilograms?|g|grams?|mt|tons?|tonnes?|mtr?s?|m|set|sets|pair|pairs|pack|packs)"
_QTY_UNIT = re.compile(rf"(?P<qty>{_NUM})\s*(?P<unit>{_UNIT})\b", re.I)

# Common 46A list markers: "1)", "1.", "- ", "• ", "Item 1:", etc.
_ITEM_SPLIT = re.compile(
    r"(?m)^(?:\s*(?:item\s*)?(?P<num>\d{1,3})[\)\.:]\s+|-+\s+|•\s+)",
    re.I,
)

_HS_INLINE = re.compile(r"\b(?:HS|H\.S\.|HSC|HS CODE|HS-CODE)\s*[:\-]?\s*(?P<hs>\d{6,10})\b", re.I)


def _to_float(s: str) -> float:
    return float(s.replace(",", "").replace(" ", ""))


def _norm_unit(u: str) -> str:
    return _UNIT_MAP.get(u.strip().lower(), u.strip().upper())


def _strip(s: Optional[str]) -> str:
    return (s or "").strip()


def _extract_qty_unit(line: str) -> Optional[Dict[str, Any]]:
    m = _QTY_UNIT.search(line)
    if not m:
        return None
    qty = _to_float(m.group("qty"))
    unit = _norm_unit(m.group("unit"))
    return {"value": qty, "unit": unit, "raw": m.group(0)}


def _extract_hs(desc: str) -> Optional[str]:
    """Extract first HS code from description, using inline pattern or fallback extractor."""
    m = _HS_INLINE.search(desc)
    if m:
        return m.group("hs")
    # Fallback: use existing extract_hs_codes and return first match
    codes = extract_hs_codes(desc)
    return codes[0] if codes else None


def _clean_description(text: str) -> str:
    # remove bullets, repeated whitespace, trailing punctuation noise
    cleaned = re.sub(r"^\s*(?:-+|•)\s*", "", text.strip())
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned


def parse_goods_46a(terms_text: str) -> List[Dict[str, Any]]:
    """
    Parse a 46A (or 45A) multi-line description into structured goods items.

    Handles:
      - Numbered/bulleted lines
      - Quantity + unit normalization
      - HS code inference (inline or extracted)

    Returns a list of items in canonical form.
    """
    raw = terms_text or ""
    if not raw.strip():
        return []

    # Split into candidate items on list markers; keep marker-less single-block fallback
    chunks: List[str] = []
    last_idx = 0
    for m in _ITEM_SPLIT.finditer(raw):
        idx = m.start()
        if idx > last_idx:
            chunks.append(raw[last_idx:idx])
        last_idx = idx

    # Add trailing tail
    if last_idx == 0:
        # No markers found; treat paragraph lines as one item each if they look like separate bullets
        paragraphs = [ln for ln in raw.splitlines() if ln.strip()]
        if len(paragraphs) > 1:
            chunks = paragraphs
        else:
            chunks = [raw]
    else:
        chunks.append(raw[last_idx:])

    items: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks, 1):
        desc = _clean_description(chunk)
        if not desc:
            continue

        qty_info = _extract_qty_unit(desc)
        hs = _extract_hs(desc)

        # Remove qty token from description (presentational cleanliness)
        if qty_info:
            desc = desc.replace(qty_info["raw"], "").strip(",;: \t")

        # Final item shape
        items.append({
            "line_no": i,
            "description": desc,
            "quantity": qty_info or None,  # {"value": float, "unit": "PCS"}
            "hs_code": hs or None,
            "notes": [],
            "source": "46A",
            "confidence": 0.85 if (qty_info or hs) else 0.70,
        })

    # Merge trivial one-liners that belong together (optional, conservative)
    items = _pass_merge_short_lines(items)
    return items


def _pass_merge_short_lines(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Conservative merge pass:
    If a line has no qty/hs and is very short, and the next line has qty/hs,
    append text to next line's description.
    """
    if not items:
        return items

    merged: List[Dict[str, Any]] = []
    i = 0
    while i < len(items):
        cur = items[i]
        if i < len(items) - 1 and not cur["quantity"] and not cur["hs_code"] and len(cur["description"]) < 24:
            nxt = items[i + 1]
            nxt["description"] = (cur["description"] + " " + nxt["description"]).strip()
            i += 2
            merged.append(nxt)
        else:
            merged.append(cur)
            i += 1

    # re-number line_no
    for idx, it in enumerate(merged, 1):
        it["line_no"] = idx

    return merged

