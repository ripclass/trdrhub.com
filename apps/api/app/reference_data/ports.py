"""
UN/LOCODE Port Registry - Canonical port name resolution.

UN/LOCODE is the United Nations Code for Trade and Transport Locations.
It provides unique codes for ~100,000 locations worldwide.

Usage:
    registry = PortRegistry()
    port = registry.resolve("Chattogram")  # Returns Port with code="BDCGP"
    port = registry.resolve("Chittagong")  # Same port
    
    # Check if two names refer to same port
    registry.same_port("Chittagong", "Chattogram")  # True
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Port:
    """A port/location from UN/LOCODE."""
    code: str           # UN/LOCODE (e.g., "BDCGP")
    name: str           # Primary name (e.g., "Chittagong")
    country_code: str   # ISO 3166-1 alpha-2 (e.g., "BD")
    country_name: str   # Full country name
    subdivision: Optional[str] = None  # State/province
    function: Optional[str] = None     # Port function codes (1=port, 2=rail, etc.)
    coordinates: Optional[Tuple[float, float]] = None
    aliases: List[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        """Return 'Port Name, Country'."""
        return f"{self.name}, {self.country_name}"
    
    def matches(self, query: str) -> bool:
        """Check if query matches this port (name or alias)."""
        q = self._normalize(query)
        if q == self._normalize(self.name):
            return True
        for alias in self.aliases:
            if q == self._normalize(alias):
                return True
        return False
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r'[^a-z0-9]', '', text.lower())


class PortRegistry:
    """
    Registry for UN/LOCODE port lookups with fuzzy matching.
    
    Features:
    - Exact match on UN/LOCODE code
    - Fuzzy match on port name + aliases
    - Country-scoped lookups
    - Similarity scoring for ambiguous matches
    """
    
    # Common aliases not in UN/LOCODE data
    MANUAL_ALIASES = {
        "BDCGP": ["Chattogram", "Chitagong", "CTG", "Chittagong Port"],
        "USNYC": ["New York", "NY", "NYC", "New York City", "Port of New York"],
        "CNSHA": ["Shanghai", "SH", "Port of Shanghai"],
        "HKHKG": ["Hong Kong", "HK", "Hongkong", "HKSAR"],
        "SGSIN": ["Singapore", "SG", "Singapura", "Port of Singapore"],
        "GBFXT": ["Felixstowe", "Port of Felixstowe"],
        "NLRTM": ["Rotterdam", "RTM", "Port of Rotterdam"],
        "DEHAM": ["Hamburg", "HAM", "Port of Hamburg"],
        "AEJEA": ["Jebel Ali", "Dubai", "Port Rashid"],
        "LKCMB": ["Colombo", "CMB", "Port of Colombo"],
        "INMUN": ["Mundra", "Mundra Port"],
        "INNSA": ["Nhava Sheva", "JNPT", "Jawaharlal Nehru Port"],
        "INMAA": ["Chennai", "Madras", "MAA"],
        "INBOM": ["Mumbai", "Bombay", "BOM"],
        "CNNGB": ["Ningbo", "Ningbo-Zhoushan"],
        "CNSGH": ["Shenzhen", "Shekou"],
        "KRPUS": ["Busan", "Pusan", "PUS"],
        "JPYOK": ["Yokohama", "YOK"],
        "JPTYO": ["Tokyo", "TYO"],
        "TWKHH": ["Kaohsiung", "KHH"],
        "VNSGN": ["Ho Chi Minh City", "Saigon", "SGN", "Cat Lai"],
        "VNHPH": ["Hai Phong", "Haiphong", "HPH"],
        "MYPKG": ["Port Klang", "Klang", "PKG"],
        "MYTPP": ["Tanjung Pelepas", "PTP"],
        "THBKK": ["Bangkok", "BKK", "Laem Chabang"],
        "THLCH": ["Laem Chabang", "LCH"],
        "PHMNL": ["Manila", "MNL", "Port of Manila"],
        "IDTPP": ["Tanjung Priok", "Jakarta", "JKT"],
        "EGPSD": ["Port Said", "PSD"],
        "EGALY": ["Alexandria", "ALY"],
        "ZADUR": ["Durban", "DUR"],
        "ZACPT": ["Cape Town", "CPT"],
        "BRSSZ": ["Santos", "SSZ", "Port of Santos"],
        "BRRIG": ["Rio Grande", "RIG"],
        "ARBUE": ["Buenos Aires", "BUE"],
        "MXZLO": ["Manzanillo", "ZLO"],
        "USLAX": ["Los Angeles", "LA", "LAX", "Port of LA"],
        "USLGB": ["Long Beach", "LGB"],
        "USOAK": ["Oakland", "OAK"],
        "USSEA": ["Seattle", "SEA"],
        "USHOU": ["Houston", "HOU"],
        "USSAV": ["Savannah", "SAV"],
        "USBAL": ["Baltimore", "BAL"],
        "CAHAL": ["Halifax", "HAL"],
        "CAMTR": ["Montreal", "MTR", "YMQ"],
        "CAVAN": ["Vancouver", "VAN", "YVR"],
    }
    
    def __init__(self, data_file: Optional[Path] = None):
        """
        Initialize port registry.
        
        Args:
            data_file: Path to UN/LOCODE JSON. If None, uses embedded data.
        """
        self._ports_by_code: Dict[str, Port] = {}
        self._ports_by_name: Dict[str, List[Port]] = {}  # Normalized name -> ports
        self._alias_map: Dict[str, str] = {}  # Normalized alias -> UN/LOCODE
        
        self._load_data(data_file)
        self._build_alias_map()
        
        logger.info(
            "PortRegistry initialized: %d ports, %d aliases",
            len(self._ports_by_code),
            len(self._alias_map),
        )
    
    def _load_data(self, data_file: Optional[Path] = None):
        """Load port data from file or embedded data."""
        if data_file and data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    port = Port(
                        code=entry["code"],
                        name=entry["name"],
                        country_code=entry["country_code"],
                        country_name=entry.get("country_name", ""),
                        subdivision=entry.get("subdivision"),
                        function=entry.get("function"),
                        aliases=entry.get("aliases", []),
                    )
                    self._ports_by_code[port.code] = port
        else:
            # Use embedded essential ports
            self._load_embedded_ports()
    
    def _load_embedded_ports(self):
        """Load essential ports when full UN/LOCODE not available."""
        # Essential ports for trade finance
        essential = [
            ("BDCGP", "Chittagong", "BD", "Bangladesh"),
            ("BDDAC", "Dhaka", "BD", "Bangladesh"),
            ("BDMGL", "Mongla", "BD", "Bangladesh"),
            ("USNYC", "New York", "US", "United States"),
            ("USLAX", "Los Angeles", "US", "United States"),
            ("USLGB", "Long Beach", "US", "United States"),
            ("USHOU", "Houston", "US", "United States"),
            ("USSAV", "Savannah", "US", "United States"),
            ("CNSHA", "Shanghai", "CN", "China"),
            ("CNNGB", "Ningbo", "CN", "China"),
            ("CNSGH", "Shenzhen", "CN", "China"),
            ("HKHKG", "Hong Kong", "HK", "Hong Kong"),
            ("SGSIN", "Singapore", "SG", "Singapore"),
            ("KRPUS", "Busan", "KR", "South Korea"),
            ("JPYOK", "Yokohama", "JP", "Japan"),
            ("JPTYO", "Tokyo", "JP", "Japan"),
            ("TWKHH", "Kaohsiung", "TW", "Taiwan"),
            ("VNSGN", "Ho Chi Minh City", "VN", "Vietnam"),
            ("VNHPH", "Hai Phong", "VN", "Vietnam"),
            ("MYPKG", "Port Klang", "MY", "Malaysia"),
            ("MYTPP", "Tanjung Pelepas", "MY", "Malaysia"),
            ("THLCH", "Laem Chabang", "TH", "Thailand"),
            ("THBKK", "Bangkok", "TH", "Thailand"),
            ("PHMNL", "Manila", "PH", "Philippines"),
            ("IDTPP", "Tanjung Priok", "ID", "Indonesia"),
            ("INMUN", "Mundra", "IN", "India"),
            ("INNSA", "Nhava Sheva", "IN", "India"),
            ("INMAA", "Chennai", "IN", "India"),
            ("INBOM", "Mumbai", "IN", "India"),
            ("LKCMB", "Colombo", "LK", "Sri Lanka"),
            ("AEJEA", "Jebel Ali", "AE", "United Arab Emirates"),
            ("EGPSD", "Port Said", "EG", "Egypt"),
            ("EGALY", "Alexandria", "EG", "Egypt"),
            ("ZADUR", "Durban", "ZA", "South Africa"),
            ("ZACPT", "Cape Town", "ZA", "South Africa"),
            ("GBFXT", "Felixstowe", "GB", "United Kingdom"),
            ("GBLGP", "Liverpool", "GB", "United Kingdom"),
            ("GBSOU", "Southampton", "GB", "United Kingdom"),
            ("NLRTM", "Rotterdam", "NL", "Netherlands"),
            ("DEHAM", "Hamburg", "DE", "Germany"),
            ("DEBHV", "Bremerhaven", "DE", "Germany"),
            ("BEANR", "Antwerp", "BE", "Belgium"),
            ("FRLEH", "Le Havre", "FR", "France"),
            ("ITGOA", "Genoa", "IT", "Italy"),
            ("ESVLC", "Valencia", "ES", "Spain"),
            ("ESALG", "Algeciras", "ES", "Spain"),
            ("GPPIR", "Piraeus", "GR", "Greece"),
            ("TRIST", "Istanbul", "TR", "Turkey"),
            ("BRSSZ", "Santos", "BR", "Brazil"),
            ("ARBUE", "Buenos Aires", "AR", "Argentina"),
            ("MXZLO", "Manzanillo", "MX", "Mexico"),
            ("CAHAL", "Halifax", "CA", "Canada"),
            ("CAMTR", "Montreal", "CA", "Canada"),
            ("CAVAN", "Vancouver", "CA", "Canada"),
            ("AUMEL", "Melbourne", "AU", "Australia"),
            ("AUSYD", "Sydney", "AU", "Australia"),
            ("NZAKL", "Auckland", "NZ", "New Zealand"),
        ]
        
        for code, name, country_code, country_name in essential:
            port = Port(
                code=code,
                name=name,
                country_code=country_code,
                country_name=country_name,
                aliases=self.MANUAL_ALIASES.get(code, []),
            )
            self._ports_by_code[code] = port
    
    def _build_alias_map(self):
        """Build normalized alias -> code mapping."""
        for code, port in self._ports_by_code.items():
            # Primary name
            norm_name = self._normalize(port.name)
            self._alias_map[norm_name] = code
            
            # Add to name lookup
            if norm_name not in self._ports_by_name:
                self._ports_by_name[norm_name] = []
            self._ports_by_name[norm_name].append(port)
            
            # Aliases from port data
            for alias in port.aliases:
                norm_alias = self._normalize(alias)
                if norm_alias:
                    self._alias_map[norm_alias] = code
            
            # Manual aliases
            if code in self.MANUAL_ALIASES:
                for alias in self.MANUAL_ALIASES[code]:
                    norm_alias = self._normalize(alias)
                    if norm_alias:
                        self._alias_map[norm_alias] = code
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        # Remove common prefixes
        text = re.sub(r'^(port\s+of\s+|porto\s+de\s+|puerto\s+de\s+)', '', text, flags=re.I)
        # Keep only alphanumeric
        return re.sub(r'[^a-z0-9]', '', text.lower())
    
    def get_by_code(self, code: str) -> Optional[Port]:
        """Get port by UN/LOCODE."""
        return self._ports_by_code.get(code.upper())
    
    def resolve(self, query: str, country_hint: Optional[str] = None) -> Optional[Port]:
        """
        Resolve a port name/alias to canonical Port.
        
        Args:
            query: Port name, alias, or UN/LOCODE
            country_hint: ISO country code to prefer matches from
            
        Returns:
            Port if found, None otherwise
        """
        if not query:
            return None
        
        query = query.strip()
        
        # Try exact UN/LOCODE match first
        if len(query) == 5 and query.upper() in self._ports_by_code:
            return self._ports_by_code[query.upper()]
        
        # Normalize and look up
        norm = self._normalize(query)
        if not norm:
            return None
        
        # Direct alias match
        if norm in self._alias_map:
            return self._ports_by_code[self._alias_map[norm]]
        
        # Try with country extracted from query
        country_match = re.search(r',\s*([A-Za-z\s]+)$', query)
        if country_match:
            country_name = country_match.group(1).strip()
            port_name = query[:country_match.start()].strip()
            norm_port = self._normalize(port_name)
            
            if norm_port in self._alias_map:
                port = self._ports_by_code[self._alias_map[norm_port]]
                # Verify country matches
                if self._normalize(country_name) in self._normalize(port.country_name):
                    return port
        
        # Fuzzy match (simple substring)
        candidates = []
        for code, port in self._ports_by_code.items():
            if norm in self._normalize(port.name):
                candidates.append((port, 0.9))
            elif any(norm in self._normalize(a) for a in port.aliases):
                candidates.append((port, 0.8))
        
        if candidates:
            # Prefer country hint
            if country_hint:
                for port, score in candidates:
                    if port.country_code.upper() == country_hint.upper():
                        return port
            return candidates[0][0]
        
        return None
    
    def same_port(self, name1: str, name2: str) -> bool:
        """
        Check if two port names refer to the same port.
        
        Returns True if both resolve to same UN/LOCODE.
        """
        port1 = self.resolve(name1)
        port2 = self.resolve(name2)
        
        if port1 and port2:
            return port1.code == port2.code
        
        # Fallback: direct string comparison if neither resolves
        if not port1 and not port2:
            return self._normalize(name1) == self._normalize(name2)
        
        return False
    
    def get_canonical_name(self, query: str) -> str:
        """
        Get canonical port name from any alias.
        
        Returns original query if not found.
        """
        port = self.resolve(query)
        if port:
            return port.full_name
        return query


# Singleton instance for app-wide use
_registry: Optional[PortRegistry] = None


def get_port_registry() -> PortRegistry:
    """Get or create the singleton port registry."""
    global _registry
    if _registry is None:
        _registry = PortRegistry()
    return _registry

