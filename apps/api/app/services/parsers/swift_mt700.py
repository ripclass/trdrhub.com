# apps/api/app/services/parsers/swift_mt700.py

import re

from typing import Dict


TAG_RX = re.compile(r"(?ms)^\s*:(\d{2}[A-Z]?):\s*(.*?)\s*(?=(?:^\s*:\d{2}[A-Z]?:)|\Z)")


def parse_mt700(text: str) -> Dict:
    """
    Robust tag slicer for MT700. Handles multiline fields and continuation.

    Returns a dict keyed by tag (e.g., '20','40A','31D','50','59','32B','39A','44E','44F','44B','45A','46A','47A').
    """
    if not text:
        return {}

    # normalize EOLs and remove hidden chars
    t = re.sub(r"\r\n?", "\n", text)
    t = re.sub(r"[^\S\n]+", " ", t)

    data = {}

    for tag, body in TAG_RX.findall(t):
        data[tag] = body.strip()

    # convenience mapping
    return {
        "20": data.get("20"),   # Sender's Reference
        "40A": data.get("40A"),  # Form of Documentary Credit
        "31D": data.get("31D"),  # Date/Place of Expiry
        "50": data.get("50"),   # Applicant
        "59": data.get("59"),   # Beneficiary
        "32B": data.get("32B"),  # Currency/Amount
        "39A": data.get("39A"),  # Tolerances
        "44E": data.get("44E"),  # Shipment from
        "44F": data.get("44F"),  # Shipment to
        "44B": data.get("44B"),  # Latest Date of Shipment
        "45A": data.get("45A"),  # Goods/Services
        "46A": data.get("46A"),  # Documents Required
        "47A": data.get("47A"),  # Additional Conditions
        "_raw": data
    }

