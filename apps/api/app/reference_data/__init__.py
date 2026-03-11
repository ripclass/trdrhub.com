"""
Reference Data Module - Production-grade normalization for trade finance.

This module provides canonical lookups for:
- Ports (UN/LOCODE)
- Currencies (ISO 4217)
- Countries (ISO 3166)
- Banks (SWIFT BIC) - future

All data is versioned and cached for fast lookups.
"""

from .ports import PortRegistry, Port, get_port_registry
from .currencies import CurrencyRegistry, Currency, get_currency_registry
from .countries import CountryRegistry, Country, get_country_registry

__all__ = [
    "PortRegistry",
    "Port",
    "get_port_registry",
    "CurrencyRegistry", 
    "Currency",
    "get_currency_registry",
    "CountryRegistry",
    "Country",
    "get_country_registry",
]

