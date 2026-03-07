from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.services.validation.day1_configs import load_day1_anchors


@dataclass(frozen=True)
class AnchorCheck:
    field: str
    hit_count: int
    score: float
    has_evidence: bool


# maps day1 canonical fields -> anchor dictionary keys
_FIELD_TO_ANCHOR_KEYS = {
    "bin": ["bin_tin"],
    "tin": ["bin_tin"],
    "voyage": ["bl_voyage"],
    "gross_weight": ["gross_weight"],
    "net_weight": ["net_weight"],
    "doc_date": ["issue_date"],
    "issuer": ["issuer"],
}


def _build_alias_map() -> Dict[str, List[str]]:
    data = load_day1_anchors()
    entities = (data.get("anchor_dictionary_v1") or {}).get("entities") or []
    out: Dict[str, List[str]] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        key = str(entity.get("key") or "").strip()
        aliases = [str(a).strip().lower() for a in (entity.get("aliases") or []) if str(a).strip()]
        if key:
            out[key] = aliases
    return out


def _anchor_hits(text: str, aliases: List[str]) -> int:
    if not text or not aliases:
        return 0
    lowered = text.lower()
    hits = 0
    for alias in aliases:
        if alias and alias in lowered:
            hits += 1
    return hits


def evaluate_anchor_evidence(extracted_text: str, min_score: float = 0.15) -> Dict[str, AnchorCheck]:
    alias_map = _build_alias_map()
    checks: Dict[str, AnchorCheck] = {}

    for field, anchor_keys in _FIELD_TO_ANCHOR_KEYS.items():
        aliases: List[str] = []
        for key in anchor_keys:
            aliases.extend(alias_map.get(key) or [])

        hits = _anchor_hits(extracted_text or "", aliases)
        denom = max(1, len(aliases))
        score = float(hits) / float(denom)
        checks[field] = AnchorCheck(
            field=field,
            hit_count=hits,
            score=score,
            has_evidence=(hits > 0) or (score >= min_score),
        )
    return checks


def apply_anchor_evidence_floor(
    raw_candidates: Dict[str, Optional[str]],
    extracted_text: str,
    min_score: float = 0.15,
) -> Tuple[Dict[str, Optional[str]], List[str], Dict[str, Dict[str, float]]]:
    """Fail-safe retrieval guard.

    If field text has no anchor evidence, candidate is nulled (abstain behavior).
    Returns: filtered_candidates, error_codes, per_field_scores
    """
    checks = evaluate_anchor_evidence(extracted_text, min_score=min_score)
    filtered = dict(raw_candidates or {})
    errors: List[str] = []
    scores: Dict[str, Dict[str, float]] = {}

    for field, check in checks.items():
        scores[field] = {"hits": float(check.hit_count), "score": check.score}
        value = filtered.get(field)
        if value in (None, ""):
            continue
        if not check.has_evidence:
            filtered[field] = None
            errors.append("RET_NO_HIT" if check.hit_count == 0 else "RET_LOW_RELEVANCE")

    return filtered, errors, scores
