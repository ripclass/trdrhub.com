from __future__ import annotations

import re

from typing import Dict, Any, Optional

# Support BOTH ":TAG:" and "TAG:" formats (raw SWIFT vs formatted PDF)
F40E_UCP_RE = re.compile(r":?40E:.*?(UCP.*?)(?:\n:?|$)", re.S | re.I)
F31C_ISSUE_RE = re.compile(r":?31C:\s*([0-9]{6,8})")
F31D_EXPIRY_RE = re.compile(r":?31D:\s*([0-9]{6,8})")
F20_NO_RE = re.compile(r":?20:\s*([A-Z0-9\/\-]+)")
F32B_AMT_RE = re.compile(r":?32B:\s*([A-Z]{3})[ ]?([\d,\.]+)")  # Capture currency AND amount
F44E_SHIP_FROM_RE = re.compile(r":?44E:\s*(.+)")
F44F_SHIP_TO_RE = re.compile(r":?44F:\s*(.+)")
# Applicant (50) and Beneficiary (59) - multiline fields
F50_APPLICANT_RE = re.compile(r":?50:\s*\n?([\s\S]*?)(?=\n:?\d{2}[A-Z]?:|\Z)")
F59_BENEFICIARY_RE = re.compile(r":?59:\s*\n?([\s\S]*?)(?=\n:?\d{2}[A-Z]?:|\Z)")

def _strip(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s

def parse_mt700_core(text: str) -> Dict[str, Any]:
    """
    Minimal MT700 core field parser (robust enough for production baselines).
    Handles both raw SWIFT (:TAG:) and formatted (TAG:) formats.
    """
    t = text or ""
    
    # LC Number (Field 20)
    m20 = re.search(F20_NO_RE, t)
    number = _strip(m20.group(1)) if m20 else None
    
    # Amount and Currency (Field 32B)
    m32b = re.search(F32B_AMT_RE, t)
    currency = None
    amount = None
    if m32b:
        currency = _strip(m32b.group(1))
        amount_raw = _strip(m32b.group(2))
        # Clean the amount string
        if amount_raw:
            amount = amount_raw.replace(",", "")
    
    # UCP Reference (Field 40E)
    m40e = re.search(F40E_UCP_RE, t)
    ucp = _strip(m40e.group(1)) if m40e else None
    
    # Issue Date (Field 31C)
    m31c = re.search(F31C_ISSUE_RE, t)
    issue_date = _strip(m31c.group(1)) if m31c else None
    
    # Expiry Date (Field 31D)
    m31d = re.search(F31D_EXPIRY_RE, t)
    expiry_date = _strip(m31d.group(1)) if m31d else None
    
    # Port of Loading (Field 44E)
    m44e = re.search(F44E_SHIP_FROM_RE, t)
    pol = _strip(m44e.group(1)) if m44e else None
    
    # Port of Discharge (Field 44F)
    m44f = re.search(F44F_SHIP_TO_RE, t)
    pod = _strip(m44f.group(1)) if m44f else None
    
    # Applicant (Field 50) - multiline
    m50 = re.search(F50_APPLICANT_RE, t)
    applicant = None
    if m50:
        applicant_raw = _strip(m50.group(1))
        if applicant_raw:
            # Take first non-empty line as name, rest as address
            lines = [ln.strip() for ln in applicant_raw.splitlines() if ln.strip()]
            if lines:
                applicant = lines[0]
    
    # Beneficiary (Field 59) - multiline
    m59 = re.search(F59_BENEFICIARY_RE, t)
    beneficiary = None
    if m59:
        beneficiary_raw = _strip(m59.group(1))
        if beneficiary_raw:
            lines = [ln.strip() for ln in beneficiary_raw.splitlines() if ln.strip()]
            if lines:
                beneficiary = lines[0]

    ports = {}
    if pol: ports["loading"] = pol
    if pod: ports["discharge"] = pod

    return {
        "number": number,
        "amount": amount,
        "currency": currency,
        "applicant": applicant,
        "beneficiary": beneficiary,
        "ucp_reference": ucp,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "ports": ports,
    }
