from __future__ import annotations

import re

from typing import List

HS_RE = re.compile(r"\b(?:HS\s*CODE\s*[:\- ]\s*)?([0-9]{6,10})\b")

def extract_hs_codes(text: str) -> List[str]:
    codes = []
    seen = set()
    for m in HS_RE.finditer(text or ""):
        code = m.group(1)
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes
