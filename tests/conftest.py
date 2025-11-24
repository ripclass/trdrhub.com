from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps" / "api"

if API_SRC.exists():
    api_str = str(API_SRC)
    if api_str not in sys.path:
        sys.path.insert(0, api_str)

