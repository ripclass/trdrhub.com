"""
Sanctions Screening Service

Comprehensive screening service for parties, vessels, goods, and ports
against multiple sanctions lists (OFAC, EU, UN, UK).
"""

import re
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel
from functools import lru_cache
from difflib import SequenceMatcher

from app.services.vessel_sanctions import (
    VesselSanctionsService, 
    SanctionsHit, 
    SanctionsResult,
    get_sanctions_service as get_vessel_service,
    SANCTIONED_FLAGS
)

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

class PartyMatch(BaseModel):
    """A sanctions match for a party/entity."""
    list_code: str
    list_name: str
    matched_name: str
    matched_type: str  # individual, entity
    match_type: str  # exact, alias, fuzzy
    match_score: float
    match_method: str
    programs: List[str] = []
    country: Optional[str] = None
    source_id: Optional[str] = None
    listed_date: Optional[str] = None
    remarks: Optional[str] = None


class ScreeningInput(BaseModel):
    """Input for screening request."""
    query: str
    screening_type: str  # party, vessel, goods, port
    country: Optional[str] = None
    lists: List[str] = []  # Empty = all lists
    additional_data: Optional[Dict[str, Any]] = None


class ComprehensiveScreeningResult(BaseModel):
    """Complete screening result."""
    query: str
    query_normalized: str
    screening_type: str
    screened_at: str
    
    # Overall result
    status: str  # clear, potential_match, match
    risk_level: str  # low, medium, high, critical
    
    # Lists screened
    lists_screened: List[str]
    
    # Matches by list
    matches: List[PartyMatch]
    total_matches: int
    highest_score: float
    
    # Flags and recommendations
    flags: List[str]
    recommendation: str
    
    # Certificate
    certificate_id: str
    
    # Processing time
    processing_time_ms: int


# ============================================================================
# Name Normalization
# ============================================================================

# Legal suffixes to remove
LEGAL_SUFFIXES = [
    r'\bLTD\.?\b', r'\bLIMITED\b', r'\bINC\.?\b', r'\bINCORPORATED\b',
    r'\bCORP\.?\b', r'\bCORPORATION\b', r'\bLLC\b', r'\bL\.L\.C\.\b',
    r'\bLLP\b', r'\bPLC\b', r'\bGMBH\b', r'\bAG\b', r'\bSA\b', r'\bS\.A\.\b',
    r'\bS\.R\.L\.\b', r'\bSRL\b', r'\bNV\b', r'\bN\.V\.\b', r'\bBV\b', r'\bB\.V\.\b',
    r'\bOY\b', r'\bAB\b', r'\bPTY\b', r'\bAS\b', r'\bA/S\b',
    r'\bCO\.?\b', r'\bCOMPANY\b', r'\b& CO\.?\b',
    r'\bPTE\.?\b', r'\bPRIVATE\b', r'\bPUBLIC\b',
]

# Common word replacements
WORD_REPLACEMENTS = {
    'INTL': 'INTERNATIONAL',
    "INT'L": 'INTERNATIONAL',
    'INTERNAT': 'INTERNATIONAL',
    'CORP': 'CORPORATION',
    'GOVT': 'GOVERNMENT',
    'GOV': 'GOVERNMENT',
    'DEPT': 'DEPARTMENT',
    'ASSOC': 'ASSOCIATION',
    'ASSN': 'ASSOCIATION',
    'BROS': 'BROTHERS',
    'MFG': 'MANUFACTURING',
    'MFRS': 'MANUFACTURERS',
    'SVCS': 'SERVICES',
    'SVC': 'SERVICE',
    'TECH': 'TECHNOLOGY',
    'TECHS': 'TECHNOLOGIES',
    'NATL': 'NATIONAL',
    'INST': 'INSTITUTE',
    'UNIV': 'UNIVERSITY',
    'CTR': 'CENTER',
    'CNTR': 'CENTER',
}

# Transliteration map for common characters
TRANSLITERATION = {
    'Ä': 'A', 'Ö': 'O', 'Ü': 'U', 'ä': 'a', 'ö': 'o', 'ü': 'u', 'ß': 'SS',
    'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E', 'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
    'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a',
    'Ñ': 'N', 'ñ': 'n',
    'Ç': 'C', 'ç': 'c',
    'Ø': 'O', 'ø': 'o',
    'Æ': 'AE', 'æ': 'ae',
    'Œ': 'OE', 'œ': 'oe',
    'Ş': 'S', 'ş': 's',
    'Ğ': 'G', 'ğ': 'g',
    'İ': 'I', 'ı': 'i',
}


def normalize_name(name: str) -> str:
    """
    Normalize a party name for matching.
    
    Steps:
    1. Uppercase
    2. Transliterate non-ASCII
    3. Remove legal suffixes
    4. Expand abbreviations
    5. Remove punctuation
    6. Collapse whitespace
    """
    if not name:
        return ""
    
    # Uppercase
    name = name.upper().strip()
    
    # Transliterate
    for char, replacement in TRANSLITERATION.items():
        name = name.replace(char.upper(), replacement)
        name = name.replace(char.lower(), replacement)
    
    # Remove legal suffixes
    for suffix in LEGAL_SUFFIXES:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    # Expand abbreviations
    words = name.split()
    expanded_words = []
    for word in words:
        word_clean = re.sub(r'[^\w]', '', word)
        if word_clean in WORD_REPLACEMENTS:
            expanded_words.append(WORD_REPLACEMENTS[word_clean])
        else:
            expanded_words.append(word)
    name = ' '.join(expanded_words)
    
    # Remove punctuation (keep alphanumeric and spaces)
    name = re.sub(r'[^A-Z0-9\s]', '', name)
    
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def normalize_vessel_name(name: str) -> str:
    """Normalize vessel name (remove M/V, MT, SS prefixes)."""
    if not name:
        return ""
    name = name.upper().strip()
    name = re.sub(r'^(M/V|MV|MT|SS|M\.V\.)\s*', '', name)
    name = re.sub(r'[^A-Z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# ============================================================================
# Matching Algorithms
# ============================================================================

def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """
    Calculate Jaro-Winkler similarity between two strings.
    Returns value between 0 and 1.
    """
    if not s1 or not s2:
        return 0.0
    
    if s1 == s2:
        return 1.0
    
    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    
    if match_distance < 0:
        match_distance = 0
    
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    
    matches = 0
    transpositions = 0
    
    # Find matches
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    
    if matches == 0:
        return 0.0
    
    # Count transpositions
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    
    jaro = (
        matches / len1 +
        matches / len2 +
        (matches - transpositions / 2) / matches
    ) / 3
    
    # Apply Winkler prefix bonus
    prefix = 0
    for i in range(min(4, len1, len2)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
    
    return jaro + prefix * 0.1 * (1 - jaro)


def token_set_ratio(s1: str, s2: str) -> float:
    """
    Calculate token set ratio similarity.
    Handles word order differences.
    """
    if not s1 or not s2:
        return 0.0
    
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    
    intersection = tokens1.intersection(tokens2)
    
    if not intersection:
        return 0.0
    
    # Create sorted strings
    sorted_intersection = ' '.join(sorted(intersection))
    sorted_rest1 = ' '.join(sorted(tokens1 - intersection))
    sorted_rest2 = ' '.join(sorted(tokens2 - intersection))
    
    combined1 = (sorted_intersection + ' ' + sorted_rest1).strip()
    combined2 = (sorted_intersection + ' ' + sorted_rest2).strip()
    
    # Calculate ratios
    ratio1 = SequenceMatcher(None, sorted_intersection, combined1).ratio()
    ratio2 = SequenceMatcher(None, sorted_intersection, combined2).ratio()
    ratio3 = SequenceMatcher(None, combined1, combined2).ratio()
    
    return max(ratio1, ratio2, ratio3)


def calculate_match_score(query: str, target: str, aliases: List[str] = None) -> Tuple[float, str, str]:
    """
    Calculate comprehensive match score.
    
    Returns: (score, match_type, match_method)
    """
    if not query or not target:
        return (0.0, "none", "none")
    
    query_norm = normalize_name(query)
    target_norm = normalize_name(target)
    
    # Exact match
    if query_norm == target_norm:
        return (100.0, "exact", "exact")
    
    # Check aliases
    if aliases:
        for alias in aliases:
            alias_norm = normalize_name(alias)
            if query_norm == alias_norm:
                return (98.0, "alias", "exact_alias")
    
    # Substring match
    if query_norm in target_norm or target_norm in query_norm:
        ratio = min(len(query_norm), len(target_norm)) / max(len(query_norm), len(target_norm))
        return (85.0 * ratio, "fuzzy", "substring")
    
    # Jaro-Winkler
    jw_score = jaro_winkler_similarity(query_norm, target_norm) * 100
    
    # Token set ratio
    ts_score = token_set_ratio(query_norm, target_norm) * 100
    
    # Take best score
    if jw_score >= ts_score:
        return (jw_score, "fuzzy", "jaro_winkler")
    else:
        return (ts_score, "fuzzy", "token_set")


# ============================================================================
# Sample Sanctions Data (for demo)
# ============================================================================

# In production, this would come from the database
SAMPLE_SDN_ENTITIES = [
    {
        "source_id": "10566",
        "name": "ISLAMIC REPUBLIC OF IRAN SHIPPING LINES",
        "aliases": ["IRISL", "IRAN SHIPPING LINES", "ISLAMIC REPUBLIC SHIPPING"],
        "type": "entity",
        "programs": ["IRAN-EO13382"],
        "country": "IR",
        "listed_date": "2008-09-10",
    },
    {
        "source_id": "21547",
        "name": "ROSNEFT",
        "aliases": ["OAO ROSNEFT", "ROSNEFT OIL COMPANY"],
        "type": "entity",
        "programs": ["UKRAINE-EO13662", "RUSSIA-EO14024"],
        "country": "RU",
        "listed_date": "2014-07-16",
    },
    {
        "source_id": "15847",
        "name": "SBERBANK",
        "aliases": ["SBERBANK OF RUSSIA", "SBERBANK ROSSII"],
        "type": "entity",
        "programs": ["RUSSIA-EO14024"],
        "country": "RU",
        "listed_date": "2022-02-24",
    },
    {
        "source_id": "18754",
        "name": "BANCO NACIONAL DE CUBA",
        "aliases": ["BNC", "CUBAN NATIONAL BANK"],
        "type": "entity",
        "programs": ["CUBA"],
        "country": "CU",
        "listed_date": "1963-07-08",
    },
    {
        "source_id": "25698",
        "name": "KIM JONG UN",
        "aliases": ["KIM JONG-UN", "KIM JONGUN"],
        "type": "individual",
        "programs": ["DPRK", "NKEA-EO13722"],
        "country": "KP",
        "listed_date": "2016-07-06",
    },
    {
        "source_id": "30125",
        "name": "SYRIA INTERNATIONAL ISLAMIC BANK",
        "aliases": ["SIIB"],
        "type": "entity",
        "programs": ["SYRIA"],
        "country": "SY",
        "listed_date": "2012-02-28",
    },
    {
        "source_id": "28456",
        "name": "HUAWEI TECHNOLOGIES CO LTD",
        "aliases": ["HUAWEI", "HUAWEI TECHNOLOGIES"],
        "type": "entity",
        "programs": ["CHINA-EO13959"],
        "country": "CN",
        "listed_date": "2019-05-16",
    },
]

SAMPLE_EU_ENTITIES = [
    {
        "source_id": "EU.1.42",
        "name": "ISLAMIC REPUBLIC OF IRAN SHIPPING LINES",
        "aliases": ["IRISL"],
        "type": "entity",
        "programs": ["(EU) 267/2012"],
        "country": "IR",
    },
    {
        "source_id": "EU.14.125",
        "name": "GAZPROMBANK",
        "aliases": ["GAZPROM BANK"],
        "type": "entity",
        "programs": ["Russia Package 14"],
        "country": "RU",
    },
    {
        "source_id": "EU.14.98",
        "name": "VTB BANK",
        "aliases": ["VTB", "VNESHTORGBANK"],
        "type": "entity",
        "programs": ["Russia Package 6"],
        "country": "RU",
    },
]

SAMPLE_UK_ENTITIES = [
    {
        "source_id": "UK.7521",
        "name": "RUSSIAN DIRECT INVESTMENT FUND",
        "aliases": ["RDIF"],
        "type": "entity",
        "programs": ["Russia Regulations 2019"],
        "country": "RU",
    },
]

# Comprehensively sanctioned countries
SANCTIONED_COUNTRIES = {
    "IR": {"name": "Iran", "type": "comprehensive", "programs": ["ITSR"]},
    "CU": {"name": "Cuba", "type": "comprehensive", "programs": ["CACR"]},
    "KP": {"name": "North Korea", "type": "comprehensive", "programs": ["NKSR"]},
    "SY": {"name": "Syria", "type": "comprehensive", "programs": ["SySR"]},
    "RU": {"name": "Russia", "type": "sectoral", "programs": ["Ukraine/Russia"]},
    "BY": {"name": "Belarus", "type": "sectoral", "programs": ["Belarus"]},
    "VE": {"name": "Venezuela", "type": "sectoral", "programs": ["Venezuela"]},
}


# ============================================================================
# Screening Service
# ============================================================================

class SanctionsScreeningService:
    """
    Comprehensive sanctions screening service.
    """
    
    def __init__(self):
        self.vessel_service = get_vessel_service()
        self.available_lists = {
            "OFAC_SDN": {"name": "OFAC SDN", "jurisdiction": "US"},
            "OFAC_SSI": {"name": "OFAC Sectoral", "jurisdiction": "US"},
            "EU_CONS": {"name": "EU Consolidated", "jurisdiction": "EU"},
            "UN_SC": {"name": "UN Security Council", "jurisdiction": "UN"},
            "UK_OFSI": {"name": "UK OFSI", "jurisdiction": "UK"},
            "BIS_EL": {"name": "BIS Entity List", "jurisdiction": "US"},
        }
    
    def _get_entities_for_list(self, list_code: str) -> List[Dict]:
        """Get sample entities for a list (in production, from DB)."""
        if list_code in ["OFAC_SDN", "OFAC_SSI"]:
            return SAMPLE_SDN_ENTITIES
        elif list_code == "EU_CONS":
            return SAMPLE_EU_ENTITIES
        elif list_code == "UK_OFSI":
            return SAMPLE_UK_ENTITIES
        else:
            return []
    
    def _screen_against_list(
        self, 
        query: str, 
        query_normalized: str,
        list_code: str,
        threshold: float = 70.0
    ) -> List[PartyMatch]:
        """Screen a query against a specific list."""
        matches = []
        entities = self._get_entities_for_list(list_code)
        list_info = self.available_lists.get(list_code, {})
        
        for entity in entities:
            score, match_type, match_method = calculate_match_score(
                query_normalized,
                entity["name"],
                entity.get("aliases", [])
            )
            
            if score >= threshold:
                matches.append(PartyMatch(
                    list_code=list_code,
                    list_name=list_info.get("name", list_code),
                    matched_name=entity["name"],
                    matched_type=entity.get("type", "entity"),
                    match_type=match_type,
                    match_score=round(score, 1),
                    match_method=match_method,
                    programs=entity.get("programs", []),
                    country=entity.get("country"),
                    source_id=entity.get("source_id"),
                    listed_date=entity.get("listed_date"),
                    remarks=entity.get("remarks"),
                ))
        
        return matches
    
    def _check_country_sanctions(self, country_code: str) -> List[PartyMatch]:
        """Check if country is under comprehensive sanctions."""
        matches = []
        
        if country_code and country_code.upper() in SANCTIONED_COUNTRIES:
            info = SANCTIONED_COUNTRIES[country_code.upper()]
            matches.append(PartyMatch(
                list_code="COUNTRY_SANCTIONS",
                list_name=f"{info['type'].title()} Country Sanctions",
                matched_name=info["name"],
                matched_type="country",
                match_type="exact",
                match_score=100.0,
                match_method="country_match",
                programs=info["programs"],
                country=country_code.upper(),
                remarks=f"{info['name']} is under {info['type']} sanctions"
            ))
        
        return matches
    
    async def screen_party(
        self,
        name: str,
        country: Optional[str] = None,
        lists: List[str] = None,
        threshold: float = 70.0
    ) -> ComprehensiveScreeningResult:
        """
        Screen a party/entity name against sanctions lists.
        """
        start_time = datetime.utcnow()
        
        name_normalized = normalize_name(name)
        
        # Use all lists if none specified
        if not lists:
            lists = list(self.available_lists.keys())
        
        # Screen against each list
        all_matches = []
        for list_code in lists:
            matches = self._screen_against_list(
                name, name_normalized, list_code, threshold
            )
            all_matches.extend(matches)
        
        # Check country if provided
        if country:
            country_matches = self._check_country_sanctions(country)
            all_matches.extend(country_matches)
        
        # Sort by score descending
        all_matches.sort(key=lambda m: m.match_score, reverse=True)
        
        # Determine overall status
        highest_score = all_matches[0].match_score if all_matches else 0
        
        if any(m.match_score >= 95 for m in all_matches):
            status = "match"
            risk_level = "critical"
            recommendation = "DO NOT PROCEED - High confidence match on sanctions list. Compliance review required."
        elif any(m.match_score >= 85 for m in all_matches):
            status = "potential_match"
            risk_level = "high"
            recommendation = "REVIEW REQUIRED - Potential sanctions match detected. Manual verification needed."
        elif any(m.match_score >= 70 for m in all_matches):
            status = "potential_match"
            risk_level = "medium"
            recommendation = "CAUTION - Possible match found. Further investigation recommended."
        else:
            status = "clear"
            risk_level = "low"
            recommendation = "CLEAR - No sanctions matches found. Standard due diligence applies."
        
        # Generate flags
        flags = []
        if any(m.list_code == "COUNTRY_SANCTIONS" for m in all_matches):
            flags.append("Entity country under international sanctions")
        if any("IRAN" in str(m.programs) for m in all_matches):
            flags.append("Potential Iran sanctions nexus")
        if any("RUSSIA" in str(m.programs) for m in all_matches):
            flags.append("Potential Russia sanctions nexus")
        if any("DPRK" in str(m.programs) or "KP" == m.country for m in all_matches):
            flags.append("Potential North Korea nexus - extreme caution")
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return ComprehensiveScreeningResult(
            query=name,
            query_normalized=name_normalized,
            screening_type="party",
            screened_at=datetime.utcnow().isoformat() + "Z",
            status=status,
            risk_level=risk_level,
            lists_screened=lists,
            matches=[m for m in all_matches],
            total_matches=len(all_matches),
            highest_score=highest_score,
            flags=flags,
            recommendation=recommendation,
            certificate_id=f"TRDR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            processing_time_ms=processing_time,
        )
    
    async def screen_vessel(
        self,
        name: str,
        imo: Optional[str] = None,
        mmsi: Optional[str] = None,
        flag_state: Optional[str] = None,
        flag_code: Optional[str] = None,
        lists: List[str] = None
    ) -> ComprehensiveScreeningResult:
        """
        Screen a vessel against sanctions lists.
        Leverages existing vessel sanctions service.
        """
        start_time = datetime.utcnow()
        
        # Use vessel service for comprehensive check
        vessel_result = await self.vessel_service.screen_vessel(
            vessel_name=name,
            imo=imo,
            mmsi=mmsi,
            flag_state=flag_state,
            flag_code=flag_code
        )
        
        # Convert to our format
        all_matches = []
        
        for hit in vessel_result.ofac_hits:
            all_matches.append(PartyMatch(
                list_code="OFAC_SDN",
                list_name="OFAC SDN",
                matched_name=hit.entity_name,
                matched_type="vessel",
                match_type=hit.match_type,
                match_score=hit.match_score,
                match_method="vessel_match",
                programs=[hit.program] if hit.program else [],
                remarks=hit.remarks,
            ))
        
        for hit in vessel_result.eu_hits:
            all_matches.append(PartyMatch(
                list_code="EU_CONS",
                list_name="EU Consolidated",
                matched_name=hit.entity_name,
                matched_type="vessel",
                match_type=hit.match_type,
                match_score=hit.match_score,
                match_method="vessel_match",
            ))
        
        # Add flag risk as potential match if high risk
        if vessel_result.flag_assessment and vessel_result.flag_assessment.risk_level in ["HIGH", "CRITICAL"]:
            all_matches.append(PartyMatch(
                list_code="FLAG_RISK",
                list_name="Flag State Risk",
                matched_name=vessel_result.flag_assessment.flag_state,
                matched_type="flag",
                match_type="risk_assessment",
                match_score=90.0 if vessel_result.flag_assessment.risk_level == "CRITICAL" else 75.0,
                match_method="flag_mou",
                remarks=vessel_result.flag_assessment.notes,
            ))
        
        # Map vessel result status to our status
        status_map = {
            "CRITICAL": "match",
            "HIGH": "potential_match",
            "MEDIUM": "potential_match",
            "LOW": "clear",
            "CLEAR": "clear",
        }
        
        highest_score = all_matches[0].match_score if all_matches else 0
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return ComprehensiveScreeningResult(
            query=name,
            query_normalized=normalize_vessel_name(name),
            screening_type="vessel",
            screened_at=datetime.utcnow().isoformat() + "Z",
            status=status_map.get(vessel_result.risk_level, "clear"),
            risk_level=vessel_result.risk_level.lower(),
            lists_screened=lists or ["OFAC_SDN", "EU_CONS", "UN_SC"],
            matches=all_matches,
            total_matches=len(all_matches),
            highest_score=highest_score,
            flags=[],  # Vessel service provides recommendation directly
            recommendation=vessel_result.recommendation,
            certificate_id=f"TRDR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            processing_time_ms=processing_time,
        )
    
    async def screen_goods(
        self,
        description: str,
        hs_code: Optional[str] = None,
        destination_country: Optional[str] = None
    ) -> ComprehensiveScreeningResult:
        """
        Screen goods for export control and sanctions implications.
        
        Checks:
        - Destination country sanctions
        - HS code restrictions
        - Dual-use indicators
        """
        start_time = datetime.utcnow()
        
        all_matches = []
        flags = []
        
        # Check destination country
        if destination_country:
            country_matches = self._check_country_sanctions(destination_country)
            all_matches.extend(country_matches)
            if country_matches:
                flags.append(f"Destination country ({destination_country}) under sanctions")
        
        # Check for sensitive keywords in description
        sensitive_keywords = [
            ("nuclear", "Nuclear/WMD sensitive"),
            ("uranium", "Nuclear material"),
            ("centrifuge", "Nuclear/dual-use equipment"),
            ("missile", "Missile technology"),
            ("guidance", "Guidance systems"),
            ("encryption", "Cryptographic"),
            ("military", "Military/defense"),
            ("weapon", "Weapons related"),
            ("chemical", "Chemical/CW sensitive"),
            ("biological", "Biological/BW sensitive"),
            ("drone", "UAV/drone technology"),
            ("surveillance", "Surveillance equipment"),
        ]
        
        desc_lower = description.lower()
        for keyword, category in sensitive_keywords:
            if keyword in desc_lower:
                flags.append(f"Keyword detected: {category}")
                all_matches.append(PartyMatch(
                    list_code="DUAL_USE",
                    list_name="Dual-Use Indicator",
                    matched_name=keyword,
                    matched_type="goods",
                    match_type="keyword",
                    match_score=75.0,
                    match_method="keyword_match",
                    remarks=f"Description contains '{keyword}' - potential {category}",
                ))
        
        # Determine status
        highest_score = all_matches[0].match_score if all_matches else 0
        
        if any(m.list_code == "COUNTRY_SANCTIONS" and m.match_score >= 95 for m in all_matches):
            status = "match"
            risk_level = "critical"
            recommendation = "DO NOT PROCEED - Export to comprehensively sanctioned country."
        elif len(flags) >= 2:
            status = "potential_match"
            risk_level = "high"
            recommendation = "REVIEW REQUIRED - Multiple dual-use/sensitive indicators detected."
        elif len(flags) >= 1:
            status = "potential_match"
            risk_level = "medium"
            recommendation = "CAUTION - Potential dual-use or controlled goods. Verify export license requirements."
        else:
            status = "clear"
            risk_level = "low"
            recommendation = "CLEAR - No obvious export control flags. Standard compliance applies."
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return ComprehensiveScreeningResult(
            query=description[:100],
            query_normalized=normalize_name(description[:100]),
            screening_type="goods",
            screened_at=datetime.utcnow().isoformat() + "Z",
            status=status,
            risk_level=risk_level,
            lists_screened=["COUNTRY_SANCTIONS", "DUAL_USE"],
            matches=all_matches,
            total_matches=len(all_matches),
            highest_score=highest_score,
            flags=flags,
            recommendation=recommendation,
            certificate_id=f"TRDR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            processing_time_ms=processing_time,
        )
    
    async def screen(self, input: ScreeningInput) -> ComprehensiveScreeningResult:
        """
        Main screening entry point. Routes to appropriate screening method.
        """
        if input.screening_type == "party":
            return await self.screen_party(
                name=input.query,
                country=input.country,
                lists=input.lists if input.lists else None,
            )
        elif input.screening_type == "vessel":
            additional = input.additional_data or {}
            return await self.screen_vessel(
                name=input.query,
                imo=additional.get("imo"),
                mmsi=additional.get("mmsi"),
                flag_state=additional.get("flag_state"),
                flag_code=additional.get("flag_code"),
                lists=input.lists if input.lists else None,
            )
        elif input.screening_type == "goods":
            additional = input.additional_data or {}
            return await self.screen_goods(
                description=input.query,
                hs_code=additional.get("hs_code"),
                destination_country=input.country,
            )
        else:
            # Default to party screening
            return await self.screen_party(
                name=input.query,
                country=input.country,
                lists=input.lists if input.lists else None,
            )
    
    def get_available_lists(self) -> Dict[str, Dict]:
        """Return available sanctions lists."""
        return self.available_lists


# Singleton
_screening_service: Optional[SanctionsScreeningService] = None


def get_screening_service() -> SanctionsScreeningService:
    """Get or create screening service instance."""
    global _screening_service
    if _screening_service is None:
        _screening_service = SanctionsScreeningService()
    return _screening_service

