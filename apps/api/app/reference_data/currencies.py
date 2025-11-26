"""
ISO 4217 Currency Registry - Canonical currency validation.

Usage:
    registry = CurrencyRegistry()
    currency = registry.get("USD")  # Returns Currency object
    registry.is_valid("XYZ")        # False
    registry.normalize("us dollar") # "USD"
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Currency:
    """ISO 4217 currency."""
    code: str           # 3-letter code (e.g., "USD")
    name: str           # Full name (e.g., "US Dollar")
    numeric: str        # Numeric code (e.g., "840")
    decimals: int       # Minor units (e.g., 2 for cents)
    symbol: Optional[str] = None
    aliases: List[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class CurrencyRegistry:
    """
    Registry for ISO 4217 currency lookups.
    """
    
    # ISO 4217 currencies commonly used in trade finance
    CURRENCIES = {
        "USD": Currency("USD", "US Dollar", "840", 2, "$", ["DOLLAR", "US DOLLAR", "DOLLARS"]),
        "EUR": Currency("EUR", "Euro", "978", 2, "€", ["EURO", "EUROS"]),
        "GBP": Currency("GBP", "Pound Sterling", "826", 2, "£", ["POUND", "STERLING", "POUNDS"]),
        "JPY": Currency("JPY", "Japanese Yen", "392", 0, "¥", ["YEN"]),
        "CNY": Currency("CNY", "Chinese Yuan", "156", 2, "¥", ["YUAN", "RMB", "RENMINBI"]),
        "CNH": Currency("CNH", "Chinese Yuan Offshore", "156", 2, "¥", ["OFFSHORE YUAN"]),
        "HKD": Currency("HKD", "Hong Kong Dollar", "344", 2, "HK$", ["HK DOLLAR"]),
        "SGD": Currency("SGD", "Singapore Dollar", "702", 2, "S$", ["SINGAPORE DOLLAR"]),
        "AUD": Currency("AUD", "Australian Dollar", "036", 2, "A$", ["AUSTRALIAN DOLLAR"]),
        "NZD": Currency("NZD", "New Zealand Dollar", "554", 2, "NZ$", ["NEW ZEALAND DOLLAR"]),
        "CAD": Currency("CAD", "Canadian Dollar", "124", 2, "C$", ["CANADIAN DOLLAR"]),
        "CHF": Currency("CHF", "Swiss Franc", "756", 2, "CHF", ["FRANC", "SWISS FRANC"]),
        "SEK": Currency("SEK", "Swedish Krona", "752", 2, "kr", ["KRONA"]),
        "NOK": Currency("NOK", "Norwegian Krone", "578", 2, "kr", ["KRONE"]),
        "DKK": Currency("DKK", "Danish Krone", "208", 2, "kr", ["DANISH KRONE"]),
        "INR": Currency("INR", "Indian Rupee", "356", 2, "₹", ["RUPEE", "RUPEES"]),
        "BDT": Currency("BDT", "Bangladeshi Taka", "050", 2, "৳", ["TAKA"]),
        "PKR": Currency("PKR", "Pakistani Rupee", "586", 2, "₨", ["PAKISTANI RUPEE"]),
        "LKR": Currency("LKR", "Sri Lankan Rupee", "144", 2, "Rs", ["SRI LANKAN RUPEE"]),
        "THB": Currency("THB", "Thai Baht", "764", 2, "฿", ["BAHT"]),
        "MYR": Currency("MYR", "Malaysian Ringgit", "458", 2, "RM", ["RINGGIT"]),
        "IDR": Currency("IDR", "Indonesian Rupiah", "360", 2, "Rp", ["RUPIAH"]),
        "PHP": Currency("PHP", "Philippine Peso", "608", 2, "₱", ["PESO"]),
        "VND": Currency("VND", "Vietnamese Dong", "704", 0, "₫", ["DONG"]),
        "KRW": Currency("KRW", "South Korean Won", "410", 0, "₩", ["WON"]),
        "TWD": Currency("TWD", "Taiwan Dollar", "901", 2, "NT$", ["TAIWAN DOLLAR"]),
        "AED": Currency("AED", "UAE Dirham", "784", 2, "د.إ", ["DIRHAM", "EMIRATI DIRHAM"]),
        "SAR": Currency("SAR", "Saudi Riyal", "682", 2, "﷼", ["RIYAL"]),
        "QAR": Currency("QAR", "Qatari Riyal", "634", 2, "﷼", ["QATARI RIYAL"]),
        "KWD": Currency("KWD", "Kuwaiti Dinar", "414", 3, "د.ك", ["DINAR"]),
        "BHD": Currency("BHD", "Bahraini Dinar", "048", 3, "BD", ["BAHRAINI DINAR"]),
        "OMR": Currency("OMR", "Omani Rial", "512", 3, "﷼", ["OMANI RIAL"]),
        "TRY": Currency("TRY", "Turkish Lira", "949", 2, "₺", ["LIRA", "TURKISH LIRA"]),
        "ZAR": Currency("ZAR", "South African Rand", "710", 2, "R", ["RAND"]),
        "EGP": Currency("EGP", "Egyptian Pound", "818", 2, "£", ["EGYPTIAN POUND"]),
        "NGN": Currency("NGN", "Nigerian Naira", "566", 2, "₦", ["NAIRA"]),
        "KES": Currency("KES", "Kenyan Shilling", "404", 2, "KSh", ["SHILLING"]),
        "BRL": Currency("BRL", "Brazilian Real", "986", 2, "R$", ["REAL"]),
        "MXN": Currency("MXN", "Mexican Peso", "484", 2, "$", ["MEXICAN PESO"]),
        "ARS": Currency("ARS", "Argentine Peso", "032", 2, "$", ["ARGENTINE PESO"]),
        "CLP": Currency("CLP", "Chilean Peso", "152", 0, "$", ["CHILEAN PESO"]),
        "COP": Currency("COP", "Colombian Peso", "170", 2, "$", ["COLOMBIAN PESO"]),
        "PEN": Currency("PEN", "Peruvian Sol", "604", 2, "S/", ["SOL"]),
        "RUB": Currency("RUB", "Russian Ruble", "643", 2, "₽", ["RUBLE"]),
        "PLN": Currency("PLN", "Polish Zloty", "985", 2, "zł", ["ZLOTY"]),
        "CZK": Currency("CZK", "Czech Koruna", "203", 2, "Kč", ["KORUNA"]),
        "HUF": Currency("HUF", "Hungarian Forint", "348", 2, "Ft", ["FORINT"]),
        "RON": Currency("RON", "Romanian Leu", "946", 2, "lei", ["LEU"]),
        "ILS": Currency("ILS", "Israeli Shekel", "376", 2, "₪", ["SHEKEL"]),
        "XOF": Currency("XOF", "CFA Franc BCEAO", "952", 0, "CFA", ["CFA FRANC"]),
        "XAF": Currency("XAF", "CFA Franc BEAC", "950", 0, "FCFA", ["CENTRAL AFRICAN CFA"]),
    }
    
    def __init__(self):
        """Initialize currency registry."""
        self._by_code: Dict[str, Currency] = dict(self.CURRENCIES)
        self._alias_map: Dict[str, str] = {}
        self._build_alias_map()
        
        logger.info("CurrencyRegistry initialized: %d currencies", len(self._by_code))
    
    def _build_alias_map(self):
        """Build alias -> code mapping."""
        for code, currency in self._by_code.items():
            # Code itself
            self._alias_map[code.upper()] = code
            
            # Numeric code
            if currency.numeric:
                self._alias_map[currency.numeric] = code
            
            # Name variations
            norm_name = self._normalize(currency.name)
            self._alias_map[norm_name] = code
            
            # Explicit aliases
            for alias in currency.aliases:
                self._alias_map[self._normalize(alias)] = code
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        return re.sub(r'[^a-z0-9]', '', text.lower())
    
    def get(self, code: str) -> Optional[Currency]:
        """Get currency by code."""
        return self._by_code.get(code.upper())
    
    def is_valid(self, code: str) -> bool:
        """Check if currency code is valid."""
        return code.upper() in self._by_code
    
    def normalize(self, query: str) -> Optional[str]:
        """
        Normalize any currency reference to ISO code.
        
        Args:
            query: Currency code, name, or alias
            
        Returns:
            ISO 4217 code if found, None otherwise
        """
        if not query:
            return None
        
        # Try direct code match
        upper = query.strip().upper()
        if upper in self._by_code:
            return upper
        
        # Try alias map
        norm = self._normalize(query)
        if norm in self._alias_map:
            return self._alias_map[norm]
        
        return None
    
    def parse_amount(self, amount_str: str) -> Optional[Dict]:
        """
        Parse amount string like "USD 100,000.00" or "100000 EUR".
        
        Returns:
            {"currency": "USD", "value": 100000.0} or None
        """
        if not amount_str:
            return None
        
        # Try pattern: CCY followed by amount
        match = re.match(r'^([A-Z]{3})\s*([\d,.\s]+)$', amount_str.strip(), re.I)
        if match:
            ccy = self.normalize(match.group(1))
            if ccy:
                try:
                    value = float(re.sub(r'[,\s]', '', match.group(2)))
                    return {"currency": ccy, "value": value}
                except ValueError:
                    pass
        
        # Try pattern: Amount followed by CCY
        match = re.match(r'^([\d,.\s]+)\s*([A-Z]{3})$', amount_str.strip(), re.I)
        if match:
            ccy = self.normalize(match.group(2))
            if ccy:
                try:
                    value = float(re.sub(r'[,\s]', '', match.group(1)))
                    return {"currency": ccy, "value": value}
                except ValueError:
                    pass
        
        return None


# Singleton instance
_registry: Optional[CurrencyRegistry] = None


def get_currency_registry() -> CurrencyRegistry:
    """Get or create the singleton currency registry."""
    global _registry
    if _registry is None:
        _registry = CurrencyRegistry()
    return _registry

