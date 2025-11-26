"""
ISO 3166 Country Registry - Canonical country name resolution.

Usage:
    registry = CountryRegistry()
    country = registry.resolve("Bangladesh")  # Returns Country with code="BD"
    country = registry.resolve("US")          # Returns Country with code="US"
    registry.same_country("USA", "United States")  # True
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Country:
    """ISO 3166-1 country."""
    alpha2: str         # 2-letter code (e.g., "BD")
    alpha3: str         # 3-letter code (e.g., "BGD")
    numeric: str        # Numeric code (e.g., "050")
    name: str           # Official name
    aliases: List[str] = field(default_factory=list)
    
    @property
    def code(self) -> str:
        """Primary code (alpha2)."""
        return self.alpha2


class CountryRegistry:
    """
    Registry for ISO 3166-1 country lookups.
    """
    
    # Countries commonly involved in trade finance
    COUNTRIES = [
        # Asia
        ("BD", "BGD", "050", "Bangladesh", ["BANGLADESH", "PEOPLES REPUBLIC OF BANGLADESH"]),
        ("IN", "IND", "356", "India", ["INDIA", "REPUBLIC OF INDIA", "BHARAT"]),
        ("PK", "PAK", "586", "Pakistan", ["PAKISTAN", "ISLAMIC REPUBLIC OF PAKISTAN"]),
        ("LK", "LKA", "144", "Sri Lanka", ["SRI LANKA", "CEYLON"]),
        ("NP", "NPL", "524", "Nepal", ["NEPAL"]),
        ("CN", "CHN", "156", "China", ["CHINA", "PEOPLES REPUBLIC OF CHINA", "PRC"]),
        ("HK", "HKG", "344", "Hong Kong", ["HONG KONG", "HONGKONG", "HKSAR"]),
        ("TW", "TWN", "158", "Taiwan", ["TAIWAN", "CHINESE TAIPEI", "ROC"]),
        ("JP", "JPN", "392", "Japan", ["JAPAN"]),
        ("KR", "KOR", "410", "South Korea", ["SOUTH KOREA", "KOREA", "REPUBLIC OF KOREA", "ROK"]),
        ("SG", "SGP", "702", "Singapore", ["SINGAPORE", "SINGAPURA"]),
        ("MY", "MYS", "458", "Malaysia", ["MALAYSIA"]),
        ("TH", "THA", "764", "Thailand", ["THAILAND", "SIAM"]),
        ("VN", "VNM", "704", "Vietnam", ["VIETNAM", "VIET NAM", "SOCIALIST REPUBLIC OF VIETNAM"]),
        ("ID", "IDN", "360", "Indonesia", ["INDONESIA"]),
        ("PH", "PHL", "608", "Philippines", ["PHILIPPINES", "PILIPINAS"]),
        ("MM", "MMR", "104", "Myanmar", ["MYANMAR", "BURMA"]),
        ("KH", "KHM", "116", "Cambodia", ["CAMBODIA", "KAMPUCHEA"]),
        
        # Middle East
        ("AE", "ARE", "784", "United Arab Emirates", ["UAE", "EMIRATES", "DUBAI"]),
        ("SA", "SAU", "682", "Saudi Arabia", ["SAUDI ARABIA", "KSA"]),
        ("QA", "QAT", "634", "Qatar", ["QATAR"]),
        ("KW", "KWT", "414", "Kuwait", ["KUWAIT"]),
        ("BH", "BHR", "048", "Bahrain", ["BAHRAIN"]),
        ("OM", "OMN", "512", "Oman", ["OMAN"]),
        ("TR", "TUR", "792", "Turkey", ["TURKEY", "TURKIYE"]),
        ("IL", "ISR", "376", "Israel", ["ISRAEL"]),
        ("JO", "JOR", "400", "Jordan", ["JORDAN"]),
        ("LB", "LBN", "422", "Lebanon", ["LEBANON"]),
        ("IR", "IRN", "364", "Iran", ["IRAN", "ISLAMIC REPUBLIC OF IRAN"]),
        ("IQ", "IRQ", "368", "Iraq", ["IRAQ"]),
        
        # Europe
        ("GB", "GBR", "826", "United Kingdom", ["UK", "UNITED KINGDOM", "GREAT BRITAIN", "BRITAIN", "ENGLAND"]),
        ("DE", "DEU", "276", "Germany", ["GERMANY", "DEUTSCHLAND"]),
        ("FR", "FRA", "250", "France", ["FRANCE"]),
        ("IT", "ITA", "380", "Italy", ["ITALY", "ITALIA"]),
        ("ES", "ESP", "724", "Spain", ["SPAIN", "ESPANA"]),
        ("PT", "PRT", "620", "Portugal", ["PORTUGAL"]),
        ("NL", "NLD", "528", "Netherlands", ["NETHERLANDS", "HOLLAND"]),
        ("BE", "BEL", "056", "Belgium", ["BELGIUM"]),
        ("CH", "CHE", "756", "Switzerland", ["SWITZERLAND", "SWISS"]),
        ("AT", "AUT", "040", "Austria", ["AUSTRIA"]),
        ("SE", "SWE", "752", "Sweden", ["SWEDEN"]),
        ("NO", "NOR", "578", "Norway", ["NORWAY"]),
        ("DK", "DNK", "208", "Denmark", ["DENMARK"]),
        ("FI", "FIN", "246", "Finland", ["FINLAND"]),
        ("PL", "POL", "616", "Poland", ["POLAND"]),
        ("CZ", "CZE", "203", "Czech Republic", ["CZECH REPUBLIC", "CZECHIA"]),
        ("GR", "GRC", "300", "Greece", ["GREECE", "HELLAS"]),
        ("IE", "IRL", "372", "Ireland", ["IRELAND", "EIRE"]),
        ("RU", "RUS", "643", "Russia", ["RUSSIA", "RUSSIAN FEDERATION"]),
        
        # Americas
        ("US", "USA", "840", "United States", ["USA", "US", "UNITED STATES", "UNITED STATES OF AMERICA", "AMERICA"]),
        ("CA", "CAN", "124", "Canada", ["CANADA"]),
        ("MX", "MEX", "484", "Mexico", ["MEXICO"]),
        ("BR", "BRA", "076", "Brazil", ["BRAZIL", "BRASIL"]),
        ("AR", "ARG", "032", "Argentina", ["ARGENTINA"]),
        ("CL", "CHL", "152", "Chile", ["CHILE"]),
        ("CO", "COL", "170", "Colombia", ["COLOMBIA"]),
        ("PE", "PER", "604", "Peru", ["PERU"]),
        
        # Africa
        ("ZA", "ZAF", "710", "South Africa", ["SOUTH AFRICA", "RSA"]),
        ("EG", "EGY", "818", "Egypt", ["EGYPT"]),
        ("NG", "NGA", "566", "Nigeria", ["NIGERIA"]),
        ("KE", "KEN", "404", "Kenya", ["KENYA"]),
        ("ET", "ETH", "231", "Ethiopia", ["ETHIOPIA"]),
        ("MA", "MAR", "504", "Morocco", ["MOROCCO"]),
        ("TN", "TUN", "788", "Tunisia", ["TUNISIA"]),
        ("GH", "GHA", "288", "Ghana", ["GHANA"]),
        ("CI", "CIV", "384", "Ivory Coast", ["IVORY COAST", "COTE DIVOIRE"]),
        
        # Oceania
        ("AU", "AUS", "036", "Australia", ["AUSTRALIA"]),
        ("NZ", "NZL", "554", "New Zealand", ["NEW ZEALAND"]),
    ]
    
    def __init__(self):
        """Initialize country registry."""
        self._by_alpha2: Dict[str, Country] = {}
        self._by_alpha3: Dict[str, Country] = {}
        self._alias_map: Dict[str, str] = {}  # Normalized alias -> alpha2
        
        self._load_data()
        logger.info("CountryRegistry initialized: %d countries", len(self._by_alpha2))
    
    def _load_data(self):
        """Load country data."""
        for alpha2, alpha3, numeric, name, aliases in self.COUNTRIES:
            country = Country(
                alpha2=alpha2,
                alpha3=alpha3,
                numeric=numeric,
                name=name,
                aliases=aliases,
            )
            self._by_alpha2[alpha2] = country
            self._by_alpha3[alpha3] = country
            
            # Build alias map
            self._alias_map[alpha2.upper()] = alpha2
            self._alias_map[alpha3.upper()] = alpha2
            self._alias_map[numeric] = alpha2
            self._alias_map[self._normalize(name)] = alpha2
            for alias in aliases:
                self._alias_map[self._normalize(alias)] = alpha2
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        return re.sub(r'[^a-z0-9]', '', text.lower())
    
    def get(self, code: str) -> Optional[Country]:
        """Get country by alpha2 or alpha3 code."""
        upper = code.upper()
        if len(upper) == 2 and upper in self._by_alpha2:
            return self._by_alpha2[upper]
        if len(upper) == 3 and upper in self._by_alpha3:
            return self._by_alpha3[upper]
        return None
    
    def resolve(self, query: str) -> Optional[Country]:
        """
        Resolve any country reference to canonical Country.
        
        Args:
            query: Country code (2 or 3 letter), numeric, or name/alias
            
        Returns:
            Country if found, None otherwise
        """
        if not query:
            return None
        
        query = query.strip()
        
        # Try direct code match
        upper = query.upper()
        if upper in self._by_alpha2:
            return self._by_alpha2[upper]
        if upper in self._by_alpha3:
            return self._by_alpha3[upper]
        
        # Try alias map
        norm = self._normalize(query)
        if norm in self._alias_map:
            return self._by_alpha2[self._alias_map[norm]]
        
        # Try partial match
        for alpha2, country in self._by_alpha2.items():
            if norm in self._normalize(country.name):
                return country
        
        return None
    
    def same_country(self, name1: str, name2: str) -> bool:
        """Check if two country names refer to the same country."""
        country1 = self.resolve(name1)
        country2 = self.resolve(name2)
        
        if country1 and country2:
            return country1.alpha2 == country2.alpha2
        
        # Fallback: direct string comparison
        if not country1 and not country2:
            return self._normalize(name1) == self._normalize(name2)
        
        return False
    
    def get_canonical_name(self, query: str) -> str:
        """Get canonical country name from any reference."""
        country = self.resolve(query)
        if country:
            return country.name
        return query


# Singleton instance
_registry: Optional[CountryRegistry] = None


def get_country_registry() -> CountryRegistry:
    """Get or create the singleton country registry."""
    global _registry
    if _registry is None:
        _registry = CountryRegistry()
    return _registry

