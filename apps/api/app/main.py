"""
Compatibility module exposing the FastAPI app instance under ``app.main``.

Some tests and legacy tools import ``app.main`` even though the actual entry
point lives at ``apps/api/main.py``.  This thin adapter ensures that import
continues to work without duplicating application setup logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

from main import app  # type: ignore  # pylint: disable=wrong-import-position

__all__ = ["app"]
