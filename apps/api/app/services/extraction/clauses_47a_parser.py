from __future__ import annotations

import re
import logging

from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# =============================================================================
# 47A ADDITIONAL CONDITIONS PATTERNS
# =============================================================================
# These patterns extract Field 47A from various LC formats (MT700, scanned PDFs, etc.)

# Pattern 1: Traditional format "47A Additional Conditions"
BLOCK_RE_1 = re.compile(r"\b47A\b[^\S\r\n]*[\-–]?[^\S\r\n]*Additional\s+Conditions[:\s]*(.+?)(?=\n(?:\d{2,3}[A-Z]|Field)|\Z)", re.I | re.S)

# Pattern 2: SWIFT MT700 format ":47A:" (colon-delimited tag)
BLOCK_RE_2 = re.compile(r":47A:(.+?)(?=:\d{2,3}[A-Z]:|\Z)", re.I | re.S)

# Pattern 3: Alternative format with ADDITIONAL CONDITIONS header
BLOCK_RE_3 = re.compile(r"ADDITIONAL\s+CONDITIONS[:\s]*\n(.+?)(?=\n(?:DOCUMENTS|SHIPPING|INSURANCE|CHARGES|71[A-Z]|78|79|Field\s+\d{2})|\Z)", re.I | re.S)

# Pattern 4: Field 47A labeled (scanned PDFs often have this)
BLOCK_RE_4 = re.compile(r"(?:Field\s+)?47A[:\s\-–]+(.+?)(?=(?:Field\s+)?\d{2,3}[A-Z]|\Z)", re.I | re.S)

# Pattern 5: 47A followed by newline and content (common in bank PDFs)
BLOCK_RE_5 = re.compile(r"\b47A\s*\n(.+?)(?=\n\d{2,3}[A-Z]\b|\n:|\Z)", re.I | re.S)

# Pattern 6: Just "47A" with content on same/next line (simpler catch-all)
BLOCK_RE_6 = re.compile(r"(?:^|\n)47A[:\s\-–]*(.+?)(?=\n(?:46[A-Z]|48|49|71|72|78|79|\d{2}[A-Z])|\Z)", re.I | re.S)

# Pattern 7: ADDITIONAL CONDITIONS section without 47A prefix (some bank formats)
BLOCK_RE_7 = re.compile(r"(?:^|\n)ADDL?\s*COND(?:ITION)?S?[:\s]*\n(.+?)(?=\n(?:DOC|SHIP|INS|CHARG|BANK)|\Z)", re.I | re.S)

# Pattern to extract numbered items
ITEM_RE = re.compile(r"^\s*(\d+)\)\s*(.+?)(?=\n\s*\d+\)|\Z)", re.M | re.S)

# Pattern to extract dash-prefixed items (alternative numbering)
DASH_ITEM_RE = re.compile(r"^\s*[-•]\s*(.+?)(?=\n\s*[-•]|\Z)", re.M | re.S)

# Pattern for Roman numeral items (i), ii), iii), etc.
ROMAN_ITEM_RE = re.compile(r"^\s*(?:([ivxlc]+)\)|([ivxlc]+)\.)\s*(.+?)(?=\n\s*[ivxlc]+[.\)]|\Z)", re.M | re.S | re.I)

# Pattern for letter items (a), b), c), etc.
LETTER_ITEM_RE = re.compile(r"^\s*([a-z])\)\s*(.+?)(?=\n\s*[a-z]\)|\Z)", re.M | re.S | re.I)

# All patterns in order of specificity (most specific first)
PATTERNS = [
    (BLOCK_RE_2, "SWIFT :47A:"),
    (BLOCK_RE_1, "Traditional 47A Additional Conditions"),
    (BLOCK_RE_4, "Field 47A"),
    (BLOCK_RE_5, "47A with newline"),
    (BLOCK_RE_6, "47A catch-all"),
    (BLOCK_RE_3, "ADDITIONAL CONDITIONS header"),
    (BLOCK_RE_7, "ADDL CONDS section"),
]


def parse_47a_block(text: str) -> Dict[str, Any]:
    """
    Tokenizes 47A Additional Conditions into structured conditions.
    
    Handles multiple formats:
    - MT700: ":47A:content"
    - Standard: "47A Additional Conditions"
    - Scanned: "Field 47A: ..."
    - Generic: "ADDITIONAL CONDITIONS" section
    - Bank PDFs with various 47A labeling
    """
    if not text:
        logger.debug("47A Parser: empty text input")
        return {"conditions": [], "_debug": {"input_empty": True}}
    
    text_length = len(text)
    logger.debug(f"47A Parser: processing {text_length} chars of text")
    
    # Check if 47A or ADDITIONAL CONDITIONS appears anywhere in text
    has_47a_marker = bool(re.search(r'\b47A\b', text, re.I))
    has_addl_cond_marker = bool(re.search(r'ADDITIONAL\s+CONDITIONS?', text, re.I))
    has_addl_abbrev = bool(re.search(r'ADDL?\s*COND', text, re.I))
    
    logger.info(
        "47A Parser: markers found - 47A=%s, ADDITIONAL_CONDITIONS=%s, ADDL_COND=%s",
        has_47a_marker, has_addl_cond_marker, has_addl_abbrev
    )
    
    block = ""
    matched_pattern = None
    match_start = -1
    match_end = -1
    
    # Try each pattern in order of specificity
    for pattern, name in PATTERNS:
        m = pattern.search(text)
        if m:
            candidate_block = m.group(1).strip()
            # Skip empty or very short matches
            if len(candidate_block) < 5:
                logger.debug(f"47A Parser: pattern '{name}' matched but content too short ({len(candidate_block)} chars)")
                continue
            block = candidate_block
            matched_pattern = name
            match_start = m.start()
            match_end = m.end()
            logger.info(
                "47A Parser: matched pattern '%s' at pos %d-%d, block length=%d chars",
                name, match_start, match_end, len(block)
            )
            break
    
    if not block:
        # Log diagnostic info for debugging
        logger.warning("47A Parser: NO PATTERN MATCHED")
        
        # Log text sample around any 47A marker for debugging
        if has_47a_marker:
            m47a = re.search(r'.{0,50}\b47A\b.{0,150}', text, re.I | re.S)
            if m47a:
                sample = m47a.group(0).replace('\n', '\\n').replace('\r', '\\r')
                logger.warning(f"47A Parser: Found 47A marker but patterns failed. Context: ...{sample}...")
        elif has_addl_cond_marker:
            m_add = re.search(r'.{0,30}ADDITIONAL\s+CONDITIONS?.{0,100}', text, re.I | re.S)
            if m_add:
                sample = m_add.group(0).replace('\n', '\\n').replace('\r', '\\r')
                logger.warning(f"47A Parser: Found ADDITIONAL CONDITIONS but patterns failed. Context: ...{sample}...")
        else:
            sample = text[:300].replace('\n', '\\n').replace('\r', '\\r') if text else "EMPTY"
            logger.warning(f"47A Parser: No 47A markers found. Text start: {sample[:200]}...")
        
        return {
            "conditions": [],
            "_debug": {
                "pattern_matched": False,
                "has_47a_marker": has_47a_marker,
                "has_addl_cond_marker": has_addl_cond_marker,
                "text_length": text_length,
            }
        }
    
    conditions: List[Dict[str, Any]] = []
    extraction_method = None
    
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
    if conditions:
        extraction_method = "numbered_items"
    
    # If no numbered items found, try letter items (a), b), c), etc.)
    if not conditions:
        for im in LETTER_ITEM_RE.finditer(block):
            idx = len(conditions) + 1
            raw = " ".join(im.group(2).split())
            if raw and len(raw) > 3:
                conditions.append({
                    "id": f"47A-{idx}",
                    "text": raw,
                    "type": "text_condition",
                })
        if conditions:
            extraction_method = "letter_items"
    
    # If no letter items, try dash-prefixed items
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
        if conditions:
            extraction_method = "dash_items"
    
    # If still no items, split by common separators
    if not conditions and block:
        # Try splitting by semicolons first (common in 47A)
        if ';' in block:
            parts = [p.strip() for p in block.split(';') if p.strip() and len(p.strip()) > 5]
            for i, part in enumerate(parts[:30]):  # Max 30 conditions
                conditions.append({
                    "id": f"47A-{i+1}",
                    "text": part,
                    "type": "text_condition",
                })
            if conditions:
                extraction_method = "semicolon_split"
    
    # Last resort: split by newlines
    if not conditions and block:
        lines = [ln.strip() for ln in block.split('\n') if ln.strip() and len(ln.strip()) > 10]
        for i, line in enumerate(lines[:30]):  # Max 30 conditions
            conditions.append({
                "id": f"47A-{i+1}",
                "text": line,
                "type": "text_condition",
            })
        if conditions:
            extraction_method = "newline_split"
    
    # If absolutely nothing worked but we have a block, treat whole thing as one condition
    if not conditions and block and len(block) > 10:
        conditions.append({
            "id": "47A-1",
            "text": " ".join(block.split()),  # Normalize whitespace
            "type": "text_condition",
        })
        extraction_method = "whole_block"
    
    logger.info(
        "47A Parser: found %d conditions using pattern '%s', method='%s'",
        len(conditions), matched_pattern, extraction_method
    )
    if conditions:
        logger.info(f"47A Parser: first condition: {conditions[0]['text'][:100]}...")
        if len(conditions) > 1:
            logger.debug(f"47A Parser: last condition: {conditions[-1]['text'][:100]}...")
    
    return {
        "conditions": conditions,
        "_debug": {
            "pattern_matched": matched_pattern,
            "extraction_method": extraction_method,
            "match_position": f"{match_start}-{match_end}",
            "block_length": len(block),
            "conditions_count": len(conditions),
        }
    }
