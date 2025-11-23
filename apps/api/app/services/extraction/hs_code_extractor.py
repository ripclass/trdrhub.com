# apps/api/app/services/extraction/hs_code_extractor.py

import re

from typing import Dict, List

HS_RX = re.compile(r"\b(?:hs\s*code[:\s]*)?(?P<hs>\d{6}(?:\d{2})?(?:\d{2})?)\b")


def extract_hs_codes(*texts: str) -> Dict[str, List[str]]:
    found: List[str] = []

    for t in texts:
        if not t:
            continue

        for m in HS_RX.finditer(t):
            code = m.group("hs")
            # normalize to 6/8/10
            if len(code) >= 6:
                found.append(code[:10])

    # unique, keep order
    seen, uniq = set(), []
    for c in found:
        if c not in seen:
            uniq.append(c)
            seen.add(c)

    # derive 6/8 base lists
    base6 = sorted({c[:6] for c in uniq})
    base8 = sorted({c[:8] for c in uniq if len(c) >= 8})

    return {"hs_full": uniq, "hs8": base8, "hs6": base6}

