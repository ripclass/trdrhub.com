from __future__ import annotations

import re

from typing import Dict, Any, Optional

F40E_UCP_RE = re.compile(r":40E:.*?(UCP.*?)(?:\n:|$)", re.S | re.I)
F31C_ISSUE_RE = re.compile(r":31C:\s*([0-9]{6,8})")
F31D_EXPIRY_RE = re.compile(r":31D:\s*([0-9]{6,8})")
F20_NO_RE = re.compile(r":20:\s*([A-Z0-9\/\-]+)")
F32B_AMT_RE = re.compile(r":32B:\s*[A-Z]{3}([\d,\.]+)")
F44E_SHIP_FROM_RE = re.compile(r":44E:\s*(.+)")
F44F_SHIP_TO_RE = re.compile(r":44F:\s*(.+)")

def _strip(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s

def parse_mt700_core(text: str) -> Dict[str, Any]:
    """
    Minimal MT700 core field parser (robust enough for production baselines).
    """
    t = text or ""
    m20 = re.search(F20_NO_RE, t)
    number = _strip(m20.group(1)) if m20 else None
    
    m32b = re.search(F32B_AMT_RE, t)
    amount = _strip(m32b.group(1)) if m32b else None
    
    m40e = re.search(F40E_UCP_RE, t)
    ucp = _strip(m40e.group(1)) if m40e else None
    
    m31c = re.search(F31C_ISSUE_RE, t)
    issue_date = _strip(m31c.group(1)) if m31c else None
    
    m31d = re.search(F31D_EXPIRY_RE, t)
    expiry_date = _strip(m31d.group(1)) if m31d else None
    
    m44e = re.search(F44E_SHIP_FROM_RE, t)
    pol = _strip(m44e.group(1)) if m44e else None
    
    m44f = re.search(F44F_SHIP_TO_RE, t)
    pod = _strip(m44f.group(1)) if m44f else None

    ports = {}
    if pol: ports["loading"] = pol
    if pod: ports["discharge"] = pod

    return {
        "number": number,
        "amount": amount,
        "ucp_reference": ucp,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "ports": ports,
    }
