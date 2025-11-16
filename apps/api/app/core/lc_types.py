from __future__ import annotations

from enum import Enum
from typing import Literal, TypedDict, Optional


LCTypeLiteral = Literal["import", "export", "unknown"]


class LCType(str, Enum):
    IMPORT = "import"
    EXPORT = "export"
    UNKNOWN = "unknown"


VALID_LC_TYPES: set[str] = {member.value for member in LCType}


class LCTypeGuess(TypedDict):
    lc_type: LCTypeLiteral
    reason: str
    confidence: float


def normalize_lc_type(value: Optional[str]) -> Optional[str]:
    """
    Normalize a candidate lc_type string to one of the supported values.
    Returns None if the value cannot be interpreted as a valid LC type.
    """
    if not value:
        return None
    candidate = value.strip().lower()
    if candidate in VALID_LC_TYPES:
        return candidate
    return None

