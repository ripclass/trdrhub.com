from __future__ import annotations

import re

from typing import Dict, Any, List, Optional

BLOCK_RE = re.compile(r"\b46A\b[^\S\r\n]*\–?[^\S\r\n]*Documents Required(.*?)(?:\n\d{2,3}[A-Z]\b|\Z)", re.I | re.S)
GOODS_RE = re.compile(r"^\s*\d+\)\s*(.+?)\s*(?:HS\s*CODE\s*[: ]\s*([0-9]{6,10}))?.*$", re.I | re.M)
SHIPMENT_RE = re.compile(r"(?:latest shipment|last date of shipment)\s*[:\-]?\s*([0-9]{6,8}|[0-9]{2}\s*[A-Za-z]{3}\s*[0-9]{2,4})", re.I)

def parse_46a_block(text: str) -> Dict[str, Any]:
    block = ""
    m = BLOCK_RE.search(text or "")
    if m:
        block = m.group(1).strip()

    # Extract goods lines (if 46A often holds itemized lines)
    goods: List[Dict[str, Any]] = []
    for gm in GOODS_RE.finditer(block):
        line = gm.group(1).strip()
        hs = (gm.group(2) or "").strip() or None
        goods.append({"line": line, **({"hs_code": hs} if hs else {})})

    # Rough pickup for documents list (split by line and keep non-empty)
    documents_required: List[str] = []
    if block:
        for ln in block.splitlines():
            ln = ln.strip("-• \t")
            if ln and not GOODS_RE.match(ln):
                documents_required.append(ln)

    latest_shipment = None
    ms = SHIPMENT_RE.search(block)
    if ms:
        latest_shipment = ms.group(1).strip()

    # De-dup and trim docs
    docs_clean = []
    seen = set()
    for d in documents_required:
        dnorm = " ".join(d.split())
        if dnorm and dnorm.lower() not in seen:
            docs_clean.append(dnorm)
            seen.add(dnorm.lower())

    return {
        "goods": goods,
        "documents_required": docs_clean,
        "latest_shipment": latest_shipment,
    }
