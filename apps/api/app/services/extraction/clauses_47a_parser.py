from __future__ import annotations

import re

from typing import Dict, Any, List

BLOCK_RE = re.compile(r"\b47A\b[^\S\r\n]*\–?[^\S\r\n]*Additional Conditions(.*?)(?:\n\d{2,3}[A-Z]\b|\Z)", re.I | re.S)
ITEM_RE = re.compile(r"^\s*(\d+)\)\s*(.+)$", re.M)

def parse_47a_block(text: str) -> Dict[str, Any]:
    """
    Tokenizes 47A Additional Conditions into structured conditions.
    """
    block = ""
    m = BLOCK_RE.search(text or "")
    if m:
        block = m.group(1).strip()

    conditions: List[Dict[str, Any]] = []
    idx = 0
    for im in ITEM_RE.finditer(block):
        idx += 1
        raw = " ".join(im.group(2).split())
        conditions.append({
            "id": f"47A-{idx}",
            "text": raw,
            "type": "text_condition",
        })

    return {"conditions": conditions}
