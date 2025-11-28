"""
Party Name Matcher - Soft matching for company/party names.

Handles variations like:
- "DHAKA KNITWEAR & EXPORTS LTD." vs "Dhaka Knitwear and Exports Limited"
- "ABC CORP." vs "ABC CORPORATION"
- "XYZ CO., LTD" vs "XYZ COMPANY LIMITED"

Features:
- Suffix normalization (Ltd, Limited, Inc, Corp, etc.)
- Ampersand/and normalization
- Common abbreviation expansion
- Fuzzy matching with confidence score
"""

import re
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PartyMatchResult:
    """Result of party name matching."""
    is_match: bool
    confidence: float
    normalized_name1: str
    normalized_name2: str
    transformations_applied: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "is_match": self.is_match,
            "confidence": round(self.confidence, 3),
            "normalized_name1": self.normalized_name1,
            "normalized_name2": self.normalized_name2,
            "transformations": self.transformations_applied,
        }


# Common suffixes and their variations
COMPANY_SUFFIXES = {
    # Full forms → normalized
    "limited": "",
    "ltd": "",
    "ltd.": "",
    "incorporated": "",
    "inc": "",
    "inc.": "",
    "corporation": "",
    "corp": "",
    "corp.": "",
    "company": "",
    "co": "",
    "co.": "",
    "llc": "",
    "l.l.c.": "",
    "l.l.c": "",
    "plc": "",
    "p.l.c.": "",
    "pvt": "",
    "pvt.": "",
    "private": "",
    "public": "",
    "gmbh": "",
    "ag": "",
    "sa": "",
    "s.a.": "",
    "bv": "",
    "b.v.": "",
    "nv": "",
    "n.v.": "",
    "pty": "",
    "pty.": "",
    "sdn": "",
    "sdn.": "",
    "bhd": "",
    "bhd.": "",
}

# Words to normalize
WORD_NORMALIZATIONS = {
    "&": "and",
    "intl": "international",
    "int'l": "international",
    "mfg": "manufacturing",
    "mfrs": "manufacturers",
    "bros": "brothers",
    "svcs": "services",
    "assoc": "associates",
    "grp": "group",
    "hldgs": "holdings",
    "indus": "industries",
    "inds": "industries",
    "mgmt": "management",
    "natl": "national",
    "dept": "department",
}


def normalize_party_name(name: str) -> Tuple[str, List[str]]:
    """
    Normalize a party/company name for comparison.
    
    Returns:
        Tuple of (normalized_name, list_of_transformations_applied)
    """
    if not name:
        return "", []
    
    transformations = []
    original = name
    
    # Convert to uppercase for consistent processing
    normalized = name.upper().strip()
    
    # Remove common punctuation
    normalized = re.sub(r'[.,;:!?\'"()\[\]{}]', ' ', normalized)
    transformations.append("punctuation_removed")
    
    # Normalize ampersand to "AND"
    if "&" in normalized:
        normalized = normalized.replace("&", " AND ")
        transformations.append("ampersand_to_and")
    
    # Normalize common abbreviations
    words = normalized.split()
    new_words = []
    for word in words:
        word_lower = word.lower()
        if word_lower in WORD_NORMALIZATIONS:
            new_words.append(WORD_NORMALIZATIONS[word_lower].upper())
            if "abbreviation_expanded" not in transformations:
                transformations.append("abbreviation_expanded")
        else:
            new_words.append(word)
    normalized = " ".join(new_words)
    
    # Remove company suffixes
    words = normalized.split()
    filtered_words = []
    for word in words:
        word_lower = word.lower().strip(".,")
        if word_lower not in COMPANY_SUFFIXES:
            filtered_words.append(word)
        elif "suffix_removed" not in transformations:
            transformations.append("suffix_removed")
    
    normalized = " ".join(filtered_words)
    
    # Remove extra whitespace
    normalized = " ".join(normalized.split())
    
    # Remove trailing/leading articles
    for article in ["THE ", " THE"]:
        if normalized.startswith(article) or normalized.endswith(article):
            normalized = normalized.replace(article, "").strip()
            if "article_removed" not in transformations:
                transformations.append("article_removed")
    
    return normalized, transformations


def _calculate_token_similarity(tokens1: set, tokens2: set) -> float:
    """Calculate Jaccard similarity between token sets."""
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    
    return len(intersection) / len(union)


def _calculate_char_similarity(s1: str, s2: str) -> float:
    """Calculate character-level similarity using longest common subsequence ratio."""
    if not s1 or not s2:
        return 0.0
    
    # Simple implementation of LCS ratio
    m, n = len(s1), len(s2)
    
    # Create a table to store lengths of longest common suffixes
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    lcs_length = dp[m][n]
    return (2 * lcs_length) / (m + n)


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Calculate Levenshtein distance ratio (similarity)."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    
    distances = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        new_distances = [i + 1]
        for j, c2 in enumerate(s2):
            if c1 == c2:
                new_distances.append(distances[j])
            else:
                new_distances.append(1 + min((distances[j], distances[j + 1], new_distances[-1])))
        distances = new_distances
    
    distance = distances[-1]
    max_len = max(len(s1), len(s2))
    return 1 - (distance / max_len)


def parties_match(
    name1: str,
    name2: str,
    threshold: float = 0.7,
    strict: bool = False,
) -> PartyMatchResult:
    """
    Check if two party names match with soft matching.
    
    Args:
        name1: First party name
        name2: Second party name
        threshold: Minimum similarity for match (default 0.7)
        strict: If True, require higher confidence (0.85)
        
    Returns:
        PartyMatchResult with match status and confidence
    """
    if strict:
        threshold = 0.85
    
    # Handle empty inputs
    if not name1 or not name2:
        return PartyMatchResult(
            is_match=False,
            confidence=0.0,
            normalized_name1=name1 or "",
            normalized_name2=name2 or "",
            transformations_applied=["empty_input"],
        )
    
    # Normalize both names
    norm1, trans1 = normalize_party_name(name1)
    norm2, trans2 = normalize_party_name(name2)
    
    all_transformations = list(set(trans1 + trans2))
    
    # Exact match after normalization
    if norm1 == norm2:
        return PartyMatchResult(
            is_match=True,
            confidence=1.0,
            normalized_name1=norm1,
            normalized_name2=norm2,
            transformations_applied=all_transformations + ["exact_match"],
        )
    
    # Check if one contains the other
    if norm1 in norm2 or norm2 in norm1:
        # Shorter name contained in longer = high confidence
        containment_ratio = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
        confidence = 0.85 + (containment_ratio * 0.1)
        return PartyMatchResult(
            is_match=True,
            confidence=confidence,
            normalized_name1=norm1,
            normalized_name2=norm2,
            transformations_applied=all_transformations + ["containment_match"],
        )
    
    # Token-based similarity
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    token_sim = _calculate_token_similarity(tokens1, tokens2)
    
    # Character-level similarity
    char_sim = _calculate_char_similarity(norm1, norm2)
    
    # Levenshtein ratio
    lev_sim = _levenshtein_ratio(norm1, norm2)
    
    # Combined score (weighted average)
    # Token similarity is most important for company names
    confidence = (token_sim * 0.5) + (char_sim * 0.3) + (lev_sim * 0.2)
    
    # Boost confidence if key tokens match
    key_tokens1 = {t for t in tokens1 if len(t) > 3}
    key_tokens2 = {t for t in tokens2 if len(t) > 3}
    if key_tokens1 and key_tokens2:
        key_overlap = len(key_tokens1 & key_tokens2) / len(key_tokens1 | key_tokens2)
        if key_overlap > 0.5:
            confidence = min(1.0, confidence + 0.1)
            all_transformations.append("key_token_boost")
    
    is_match = confidence >= threshold
    
    return PartyMatchResult(
        is_match=is_match,
        confidence=confidence,
        normalized_name1=norm1,
        normalized_name2=norm2,
        transformations_applied=all_transformations,
    )


def match_party_to_candidates(
    party_name: str,
    candidates: List[str],
    threshold: float = 0.7,
) -> Optional[Tuple[str, float]]:
    """
    Find the best matching candidate for a party name.
    
    Args:
        party_name: Name to match
        candidates: List of candidate names
        threshold: Minimum similarity for match
        
    Returns:
        Tuple of (best_match, confidence) or None if no match
    """
    best_match = None
    best_confidence = 0.0
    
    for candidate in candidates:
        result = parties_match(party_name, candidate, threshold=threshold)
        if result.is_match and result.confidence > best_confidence:
            best_match = candidate
            best_confidence = result.confidence
    
    if best_match:
        return best_match, best_confidence
    return None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "parties_match",
    "normalize_party_name",
    "match_party_to_candidates",
    "PartyMatchResult",
]

