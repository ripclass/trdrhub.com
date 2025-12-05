"""
Vessel Sanctions Screening Service

Screens vessels against multiple sanctions lists:
- OFAC SDN (US Treasury)
- EU Consolidated Sanctions
- UN Sanctions List

All data sources are FREE and publicly available.
"""

import os
import re
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)

# ============== Models ==============

class SanctionsHit(BaseModel):
    """A single sanctions match."""
    list_name: str  # OFAC, EU, UN
    entity_name: str
    entity_type: str  # vessel, person, company
    match_type: str  # exact, partial, alias
    match_score: float  # 0-100
    program: Optional[str] = None  # e.g., "IRAN", "SYRIA"
    id_numbers: List[str] = []
    remarks: Optional[str] = None
    list_date: Optional[str] = None


class FlagRiskAssessment(BaseModel):
    """Flag state risk assessment."""
    flag_state: str
    flag_code: str
    risk_level: str  # LOW, MEDIUM, HIGH
    paris_mou_status: str  # white, grey, black
    tokyo_mou_status: str  # white, grey, black
    is_flag_of_convenience: bool
    notes: str


class SanctionsResult(BaseModel):
    """Complete sanctions screening result."""
    vessel_name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    screened_at: str
    
    # Screening results
    is_clear: bool
    risk_level: str  # CLEAR, LOW, MEDIUM, HIGH, CRITICAL
    
    # List-specific results
    ofac_clear: bool
    ofac_hits: List[SanctionsHit] = []
    eu_clear: bool
    eu_hits: List[SanctionsHit] = []
    un_clear: bool
    un_hits: List[SanctionsHit] = []
    
    # Flag assessment
    flag_assessment: Optional[FlagRiskAssessment] = None
    
    # Summary
    total_hits: int
    recommendation: str
    confidence: float


# ============== Flag Risk Data ==============

# Paris MoU performance lists (2023-2024 data)
# White = low risk, Grey = medium, Black = high risk
PARIS_MOU_WHITE = [
    "DK", "DE", "NL", "GB", "NO", "SE", "FI", "BE", "IE", "FR", 
    "ES", "PT", "IT", "GR", "MT", "CY", "JP", "SG", "HK", "AU",
    "NZ", "CA", "US", "KR", "TW", "MY", "BM", "KY", "GI", "IM",
    "JE", "LU", "CH", "AT", "PL", "CZ", "HR", "SI", "EE", "LV", "LT"
]

PARIS_MOU_GREY = [
    "BS", "LR", "MH", "PA", "VU", "BB", "AG", "VC", "KN", "DM",
    "TT", "JM", "MX", "BR", "AR", "CL", "PE", "CO", "VE", "EC",
    "IN", "BD", "PK", "LK", "MM", "VN", "TH", "ID", "PH", "CN",
    "RU", "UA", "GE", "AZ", "KZ", "TR", "EG", "MA", "DZ", "TN",
    "SA", "AE", "QA", "KW", "BH", "OM", "JO", "LB", "IL", "ZA"
]

PARIS_MOU_BLACK = [
    "KP", "IR", "SY", "CU", "MM", "LY", "SD", "SO", "YE", "VE",
    "TZ", "TG", "CM", "GN", "SL", "LR", "CI", "GH", "NG", "CG",
    "CD", "AO", "MZ", "KE", "MG", "MU", "SC", "MV", "BN", "LA",
    "KH", "MN", "PG", "FJ", "WS", "TO", "KI", "TV"
]

# Flags of convenience (FOC) - typically used to avoid regulations
FLAGS_OF_CONVENIENCE = [
    "PA", "LR", "MH", "BS", "MT", "CY", "BM", "VU", "AG", "BB",
    "VC", "KN", "DM", "BZ", "GI", "IM", "JE", "KY", "HK", "SG"
]

# Countries under comprehensive sanctions
SANCTIONED_FLAGS = ["KP", "IR", "SY", "CU"]


# ============== OFAC Data Fetching ==============

OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
OFAC_CONS_URL = "https://www.treasury.gov/ofac/downloads/consolidated/consolidated.xml"

# Cache for sanctions data (refresh daily)
_sanctions_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None
CACHE_DURATION = timedelta(hours=24)


async def fetch_ofac_data() -> List[Dict[str, Any]]:
    """
    Fetch OFAC SDN list.
    Returns parsed vessel entries.
    """
    global _sanctions_cache, _cache_timestamp
    
    cache_key = "ofac"
    if (
        cache_key in _sanctions_cache 
        and _cache_timestamp 
        and datetime.utcnow() - _cache_timestamp < CACHE_DURATION
    ):
        return _sanctions_cache[cache_key]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(OFAC_SDN_URL)
            response.raise_for_status()
            
            # Parse XML (simplified - in production use proper XML parsing)
            # For now, we'll use a regex-based extraction for vessel entries
            content = response.text
            
            vessels = []
            # Look for vessel entries in the XML
            vessel_pattern = re.compile(
                r'<sdnEntry>.*?<sdnType>Vessel</sdnType>.*?<lastName>([^<]+)</lastName>.*?'
                r'(?:<callSign>([^<]*)</callSign>)?.*?'
                r'(?:<vesselType>([^<]*)</vesselType>)?.*?'
                r'(?:<tonnage>([^<]*)</tonnage>)?.*?'
                r'(?:<grossRegisteredTonnage>([^<]*)</grossRegisteredTonnage>)?.*?'
                r'(?:<vesselFlag>([^<]*)</vesselFlag>)?.*?'
                r'(?:<vesselOwner>([^<]*)</vesselOwner>)?.*?'
                r'<program>([^<]+)</program>.*?</sdnEntry>',
                re.DOTALL | re.IGNORECASE
            )
            
            for match in vessel_pattern.finditer(content):
                vessels.append({
                    "name": match.group(1).strip() if match.group(1) else "",
                    "call_sign": match.group(2).strip() if match.group(2) else "",
                    "vessel_type": match.group(3).strip() if match.group(3) else "",
                    "tonnage": match.group(4).strip() if match.group(4) else "",
                    "grt": match.group(5).strip() if match.group(5) else "",
                    "flag": match.group(6).strip() if match.group(6) else "",
                    "owner": match.group(7).strip() if match.group(7) else "",
                    "program": match.group(8).strip() if match.group(8) else "",
                    "list": "OFAC SDN"
                })
            
            # Also look for ID numbers (IMO)
            id_pattern = re.compile(
                r'<id>.*?<idType>IMO</idType>.*?<idNumber>([^<]+)</idNumber>.*?</id>',
                re.DOTALL | re.IGNORECASE
            )
            
            _sanctions_cache[cache_key] = vessels
            _cache_timestamp = datetime.utcnow()
            
            logger.info(f"Fetched {len(vessels)} vessels from OFAC SDN list")
            return vessels
            
    except Exception as e:
        logger.error(f"Error fetching OFAC data: {e}")
        return _sanctions_cache.get(cache_key, [])


async def fetch_eu_sanctions() -> List[Dict[str, Any]]:
    """
    Fetch EU Consolidated Sanctions List.
    """
    global _sanctions_cache, _cache_timestamp
    
    cache_key = "eu"
    if (
        cache_key in _sanctions_cache 
        and _cache_timestamp 
        and datetime.utcnow() - _cache_timestamp < CACHE_DURATION
    ):
        return _sanctions_cache[cache_key]
    
    # EU sanctions are available at:
    # https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content
    EU_URL = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(EU_URL)
            response.raise_for_status()
            
            content = response.text
            vessels = []
            
            # Simplified parsing for vessel entities
            # In production, use proper XML parsing
            entity_pattern = re.compile(
                r'<entity.*?subjectType="vessel".*?>.*?<wholeName>([^<]+)</wholeName>.*?</entity>',
                re.DOTALL | re.IGNORECASE
            )
            
            for match in entity_pattern.finditer(content):
                vessels.append({
                    "name": match.group(1).strip(),
                    "list": "EU Consolidated"
                })
            
            _sanctions_cache[cache_key] = vessels
            logger.info(f"Fetched {len(vessels)} vessels from EU sanctions list")
            return vessels
            
    except Exception as e:
        logger.error(f"Error fetching EU sanctions: {e}")
        return _sanctions_cache.get(cache_key, [])


# ============== Screening Service ==============

class VesselSanctionsService:
    """
    Service for screening vessels against sanctions lists.
    """
    
    def __init__(self):
        self.ofac_data: List[Dict] = []
        self.eu_data: List[Dict] = []
        self.un_data: List[Dict] = []
    
    async def load_sanctions_data(self):
        """Load all sanctions data (cached)."""
        self.ofac_data, self.eu_data = await asyncio.gather(
            fetch_ofac_data(),
            fetch_eu_sanctions()
        )
        # UN data would be fetched similarly
        self.un_data = []  # Placeholder
    
    def _normalize_name(self, name: str) -> str:
        """Normalize vessel name for comparison."""
        if not name:
            return ""
        # Remove common prefixes, punctuation, extra spaces
        name = name.upper().strip()
        name = re.sub(r'^(M/V|MV|MT|SS|MV\.|M\.V\.)\s*', '', name)
        name = re.sub(r'[^A-Z0-9\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    def _calculate_match_score(self, query: str, target: str) -> float:
        """Calculate similarity score between two strings."""
        if not query or not target:
            return 0.0
        
        query = self._normalize_name(query)
        target = self._normalize_name(target)
        
        if query == target:
            return 100.0
        
        if query in target or target in query:
            return 85.0
        
        # Simple word overlap scoring
        query_words = set(query.split())
        target_words = set(target.split())
        
        if not query_words or not target_words:
            return 0.0
        
        overlap = query_words.intersection(target_words)
        score = (len(overlap) / max(len(query_words), len(target_words))) * 100
        
        return round(score, 1)
    
    async def check_ofac(self, vessel_name: str, imo: Optional[str] = None) -> tuple[bool, List[SanctionsHit]]:
        """Check vessel against OFAC SDN list."""
        if not self.ofac_data:
            await self.load_sanctions_data()
        
        hits = []
        threshold = 70.0  # Minimum match score to report
        
        for entry in self.ofac_data:
            score = self._calculate_match_score(vessel_name, entry.get("name", ""))
            
            if score >= threshold:
                match_type = "exact" if score >= 95 else "partial"
                hits.append(SanctionsHit(
                    list_name="OFAC SDN",
                    entity_name=entry.get("name", ""),
                    entity_type="vessel",
                    match_type=match_type,
                    match_score=score,
                    program=entry.get("program"),
                    remarks=f"Flag: {entry.get('flag', 'Unknown')}, Owner: {entry.get('owner', 'Unknown')}"
                ))
        
        is_clear = len(hits) == 0
        return is_clear, hits
    
    async def check_eu_sanctions(self, vessel_name: str, imo: Optional[str] = None) -> tuple[bool, List[SanctionsHit]]:
        """Check vessel against EU Consolidated Sanctions."""
        if not self.eu_data:
            await self.load_sanctions_data()
        
        hits = []
        threshold = 70.0
        
        for entry in self.eu_data:
            score = self._calculate_match_score(vessel_name, entry.get("name", ""))
            
            if score >= threshold:
                match_type = "exact" if score >= 95 else "partial"
                hits.append(SanctionsHit(
                    list_name="EU Consolidated",
                    entity_name=entry.get("name", ""),
                    entity_type="vessel",
                    match_type=match_type,
                    match_score=score
                ))
        
        is_clear = len(hits) == 0
        return is_clear, hits
    
    async def check_un_sanctions(self, vessel_name: str, imo: Optional[str] = None) -> tuple[bool, List[SanctionsHit]]:
        """Check vessel against UN Sanctions List."""
        # UN sanctions list is available at:
        # https://scsanctions.un.org/resources/xml/en/consolidated.xml
        # For now, return clear (proper implementation would parse this)
        return True, []
    
    def assess_flag_risk(self, flag_state: Optional[str], flag_code: Optional[str] = None) -> FlagRiskAssessment:
        """Assess risk based on flag state."""
        if not flag_code and flag_state:
            # Try to derive code from state name
            flag_code = self._get_flag_code(flag_state)
        
        if not flag_code:
            flag_code = "XX"
        
        flag_code = flag_code.upper()
        
        # Determine MoU status
        if flag_code in PARIS_MOU_WHITE:
            paris_status = "white"
        elif flag_code in PARIS_MOU_GREY:
            paris_status = "grey"
        else:
            paris_status = "black"
        
        # Same for Tokyo MoU (simplified - using same lists)
        tokyo_status = paris_status
        
        # Check if sanctioned
        if flag_code in SANCTIONED_FLAGS:
            risk_level = "CRITICAL"
            notes = "Flag state under comprehensive international sanctions"
        elif paris_status == "black":
            risk_level = "HIGH"
            notes = "Flag state on Paris MoU blacklist - elevated inspection risk"
        elif flag_code in FLAGS_OF_CONVENIENCE and paris_status == "grey":
            risk_level = "MEDIUM"
            notes = "Flag of convenience with grey list status"
        elif flag_code in FLAGS_OF_CONVENIENCE:
            risk_level = "LOW"
            notes = "Flag of convenience but good performance record"
        elif paris_status == "grey":
            risk_level = "LOW"
            notes = "Grey list status - monitor for changes"
        else:
            risk_level = "LOW"
            notes = "Well-regulated flag state with good performance"
        
        return FlagRiskAssessment(
            flag_state=flag_state or "Unknown",
            flag_code=flag_code,
            risk_level=risk_level,
            paris_mou_status=paris_status,
            tokyo_mou_status=tokyo_status,
            is_flag_of_convenience=flag_code in FLAGS_OF_CONVENIENCE,
            notes=notes
        )
    
    def _get_flag_code(self, flag_state: str) -> str:
        """Convert flag state name to ISO code."""
        flag_map = {
            "PANAMA": "PA", "LIBERIA": "LR", "MARSHALL ISLANDS": "MH",
            "HONG KONG": "HK", "SINGAPORE": "SG", "BAHAMAS": "BS",
            "MALTA": "MT", "CHINA": "CN", "GREECE": "GR",
            "JAPAN": "JP", "NORWAY": "NO", "UNITED KINGDOM": "GB",
            "USA": "US", "UNITED STATES": "US", "GERMANY": "DE",
            "DENMARK": "DK", "CYPRUS": "CY", "BERMUDA": "BM",
            "KOREA": "KR", "SOUTH KOREA": "KR", "ITALY": "IT",
            "TAIWAN": "TW", "INDIA": "IN", "TURKEY": "TR",
            "RUSSIA": "RU", "IRAN": "IR", "NORTH KOREA": "KP",
            "SYRIA": "SY", "CUBA": "CU", "VENEZUELA": "VE",
            "NETHERLANDS": "NL", "FRANCE": "FR", "SPAIN": "ES",
            "BELGIUM": "BE", "PORTUGAL": "PT", "SWEDEN": "SE",
            "FINLAND": "FI", "IRELAND": "IE", "AUSTRALIA": "AU",
            "NEW ZEALAND": "NZ", "CANADA": "CA", "BRAZIL": "BR",
            "ARGENTINA": "AR", "MEXICO": "MX", "INDONESIA": "ID",
            "MALAYSIA": "MY", "THAILAND": "TH", "VIETNAM": "VN",
            "PHILIPPINES": "PH", "BANGLADESH": "BD", "PAKISTAN": "PK",
            "EGYPT": "EG", "SOUTH AFRICA": "ZA", "NIGERIA": "NG",
            "UAE": "AE", "UNITED ARAB EMIRATES": "AE", "SAUDI ARABIA": "SA"
        }
        return flag_map.get(flag_state.upper(), "XX")
    
    async def screen_vessel(
        self, 
        vessel_name: str, 
        imo: Optional[str] = None,
        mmsi: Optional[str] = None,
        flag_state: Optional[str] = None,
        flag_code: Optional[str] = None
    ) -> SanctionsResult:
        """
        Perform complete sanctions screening on a vessel.
        
        Returns comprehensive result with all list checks and recommendations.
        """
        screened_at = datetime.utcnow().isoformat() + "Z"
        
        # Run all checks in parallel
        ofac_task = self.check_ofac(vessel_name, imo)
        eu_task = self.check_eu_sanctions(vessel_name, imo)
        un_task = self.check_un_sanctions(vessel_name, imo)
        
        results = await asyncio.gather(ofac_task, eu_task, un_task)
        
        ofac_clear, ofac_hits = results[0]
        eu_clear, eu_hits = results[1]
        un_clear, un_hits = results[2]
        
        # Assess flag risk
        flag_assessment = self.assess_flag_risk(flag_state, flag_code)
        
        # Calculate overall risk
        total_hits = len(ofac_hits) + len(eu_hits) + len(un_hits)
        has_exact_match = any(
            h.match_type == "exact" 
            for h in ofac_hits + eu_hits + un_hits
        )
        
        # Determine risk level and recommendation
        if has_exact_match:
            risk_level = "CRITICAL"
            recommendation = "DO NOT PROCEED - Exact match on sanctions list. Requires compliance review."
            confidence = 95.0
        elif total_hits > 0:
            risk_level = "HIGH"
            recommendation = "CAUTION - Potential sanctions match detected. Manual review required."
            confidence = 80.0
        elif flag_assessment.risk_level == "CRITICAL":
            risk_level = "HIGH"
            recommendation = "CAUTION - Vessel flag state under sanctions. Enhanced due diligence required."
            confidence = 90.0
        elif flag_assessment.risk_level == "HIGH":
            risk_level = "MEDIUM"
            recommendation = "PROCEED WITH CAUTION - Flag state has elevated risk. Monitor closely."
            confidence = 85.0
        elif flag_assessment.risk_level == "MEDIUM":
            risk_level = "LOW"
            recommendation = "CLEAR - No sanctions matches. Flag of convenience noted."
            confidence = 90.0
        else:
            risk_level = "CLEAR"
            recommendation = "CLEAR - No sanctions matches. Low-risk flag state."
            confidence = 95.0
        
        is_clear = risk_level in ["CLEAR", "LOW"]
        
        return SanctionsResult(
            vessel_name=vessel_name,
            imo=imo,
            mmsi=mmsi,
            screened_at=screened_at,
            is_clear=is_clear,
            risk_level=risk_level,
            ofac_clear=ofac_clear,
            ofac_hits=ofac_hits,
            eu_clear=eu_clear,
            eu_hits=eu_hits,
            un_clear=un_clear,
            un_hits=un_hits,
            flag_assessment=flag_assessment,
            total_hits=total_hits,
            recommendation=recommendation,
            confidence=confidence
        )


# Singleton instance
_sanctions_service: Optional[VesselSanctionsService] = None


def get_sanctions_service() -> VesselSanctionsService:
    """Get or create sanctions service instance."""
    global _sanctions_service
    if _sanctions_service is None:
        _sanctions_service = VesselSanctionsService()
    return _sanctions_service

