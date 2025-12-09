from __future__ import annotations

import re
import logging

from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Multiple patterns to match 47A Additional Conditions in different formats
# Pattern 1: Traditional format "47A Additional Conditions"
BLOCK_RE_1 = re.compile(r"\b47A\b[^\S\r\n]*\–?[^\S\r\n]*Additional Conditions(.*?)(?:\n\d{2,3}[A-Z]\b|\Z)", re.I | re.S)

# Pattern 2: SWIFT MT700 format ":47A:" (colon-delimited tag)
BLOCK_RE_2 = re.compile(r":47A:(.+?)(?=:\d{2,3}[A-Z]:|\Z)", re.I | re.S)

# Pattern 3: Alternative format with ADDITIONAL CONDITIONS header
BLOCK_RE_3 = re.compile(r"ADDITIONAL\s+CONDITIONS[:\s]*\n(.*?)(?=\n(?:DOCUMENTS|SHIPPING|INSURANCE|CHARGES|71[A-Z]|78|79)|\Z)", re.I | re.S)

# Pattern 4: Field 47A labeled (scanned PDFs often have this)
BLOCK_RE_4 = re.compile(r"(?:Field\s+)?47A[:\s\-]+(.+?)(?=(?:Field\s+)?\d{2,3}[A-Z]|\Z)", re.I | re.S)

# Pattern to extract numbered items
ITEM_RE = re.compile(r"^\s*(\d+)\)\s*(.+?)(?=\n\s*\d+\)|\Z)", re.M | re.S)

# Pattern to extract dash-prefixed items (alternative numbering)
DASH_ITEM_RE = re.compile(r"^\s*[-•]\s*(.+?)(?=\n\s*[-•]|\Z)", re.M | re.S)


def parse_47a_block(text: str) -> Dict[str, Any]:
    """
    Tokenizes 47A Additional Conditions into structured conditions.
    
    Handles multiple formats:
    - MT700: ":47A:content"
    - Standard: "47A Additional Conditions"
    - Scanned: "Field 47A: ..."
    - Generic: "ADDITIONAL CONDITIONS" section
    """
    if not text:
        return {"conditions": []}
    
    block = ""
    matched_pattern = None
    
    # Try each pattern in order of specificity
    for pattern, name in [
        (BLOCK_RE_2, "SWIFT :47A:"),
        (BLOCK_RE_1, "Traditional 47A"),
        (BLOCK_RE_4, "Field 47A"),
        (BLOCK_RE_3, "ADDITIONAL CONDITIONS header"),
    ]:
        m = pattern.search(text)
        if m:
            block = m.group(1).strip()
            matched_pattern = name
            logger.info(f"47A Parser: matched pattern '{name}', block length={len(block)}")
            break
    
    if not block:
        # Log a sample of the text to help debug
        sample = text[:500].replace('\n', '\\n') if text else "EMPTY"
        logger.warning(f"47A Parser: no pattern matched. Text sample: {sample[:200]}...")
        return {"conditions": []}
    
    conditions: List[Dict[str, Any]] = []
    
    # Try numbered items first (1), 2), etc.)
    idx = 0
    for im in ITEM_RE.finditer(block):
        idx += 1
        raw = " ".join(im.group(2).split())
        if raw and len(raw) > 3:  # Skip very short items
            conditions.append({
                "id": f"47A-{idx}",
                "text": raw,
                "type": "text_condition",
            })
    
    # If no numbered items found, try dash-prefixed items
    if not conditions:
        for im in DASH_ITEM_RE.finditer(block):
            idx = len(conditions) + 1
            raw = " ".join(im.group(1).split())
            if raw and len(raw) > 3:
                conditions.append({
                    "id": f"47A-{idx}",
                    "text": raw,
                    "type": "text_condition",
                })
    
    # If still no items, treat entire block as single condition
    if not conditions and block:
        # Split by newlines and treat each substantial line as a condition
        lines = [ln.strip() for ln in block.split('\n') if ln.strip() and len(ln.strip()) > 10]
        for i, line in enumerate(lines[:20]):  # Max 20 conditions
            conditions.append({
                "id": f"47A-{i+1}",
                "text": line,
                "type": "text_condition",
            })
    
    logger.info(f"47A Parser: found {len(conditions)} conditions using pattern '{matched_pattern}'")
    if conditions:
        logger.info(f"47A Parser: sample condition: {conditions[0]['text'][:100]}...")
    
    return {"conditions": conditions}
