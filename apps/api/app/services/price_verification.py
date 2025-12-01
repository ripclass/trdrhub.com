"""
Price Verification Service

Verifies trade document prices against real-time and historical market data.
Detects over/under invoicing and TBML (Trade-Based Money Laundering) risks.
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)

# =============================================================================
# COMMODITY DATABASE
# =============================================================================
# Master list of supported commodities with typical price ranges (USD per unit)
# Updated regularly from market data

COMMODITIES_DATABASE = {
    # ==================== AGRICULTURE ====================
    "COTTON_RAW": {
        "name": "Raw Cotton",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["cotton", "cotton lint", "raw cotton fiber", "cotton bales"],
        "hs_codes": ["5201", "5201.00"],
        "typical_range": (1.50, 4.50),  # USD/kg
        "current_estimate": 2.20,
        "data_sources": ["world_bank", "fred", "usda"],
        "source_codes": {"world_bank": "COTTON_A_INDEX", "fred": "WPU0131"},
    },
    "RICE_WHITE": {
        "name": "White Rice",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["rice", "white rice", "milled rice", "polished rice"],
        "hs_codes": ["1006.30", "1006"],
        "typical_range": (350, 850),  # USD/mt
        "current_estimate": 520,
        "data_sources": ["world_bank", "fao"],
        "source_codes": {"world_bank": "RICE_05"},
    },
    "WHEAT": {
        "name": "Wheat",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["wheat", "wheat grain", "soft wheat", "hard wheat"],
        "hs_codes": ["1001", "1001.99"],
        "typical_range": (180, 450),
        "current_estimate": 280,
        "data_sources": ["world_bank", "fred"],
        "source_codes": {"world_bank": "WHEAT_US_HRW"},
    },
    "SUGAR_RAW": {
        "name": "Raw Sugar",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["sugar", "raw sugar", "cane sugar", "sugar cane"],
        "hs_codes": ["1701.14", "1701"],
        "typical_range": (300, 700),
        "current_estimate": 450,
        "data_sources": ["world_bank", "ice"],
        "source_codes": {"world_bank": "SUGAR_WLD"},
    },
    "COFFEE_ARABICA": {
        "name": "Coffee (Arabica)",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["coffee", "arabica coffee", "coffee beans"],
        "hs_codes": ["0901.11", "0901"],
        "typical_range": (3.00, 8.00),
        "current_estimate": 5.50,
        "data_sources": ["world_bank", "ice"],
        "source_codes": {"world_bank": "COFFEE_ARABIC"},
    },
    "COCOA_BEANS": {
        "name": "Cocoa Beans",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["cocoa", "cocoa beans", "cacao"],
        "hs_codes": ["1801.00", "1801"],
        "typical_range": (2000, 5500),
        "current_estimate": 4200,
        "data_sources": ["world_bank", "ice"],
        "source_codes": {"world_bank": "COCOA"},
    },
    "SOYBEANS": {
        "name": "Soybeans",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["soybean", "soya beans", "soy"],
        "hs_codes": ["1201", "1201.90"],
        "typical_range": (350, 700),
        "current_estimate": 480,
        "data_sources": ["world_bank", "cbot"],
        "source_codes": {"world_bank": "SOYBEAN"},
    },
    "PALM_OIL": {
        "name": "Palm Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["palm oil", "crude palm oil", "cpo"],
        "hs_codes": ["1511", "1511.10"],
        "typical_range": (600, 1400),
        "current_estimate": 850,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "PALM_OIL"},
    },
    "RUBBER_NATURAL": {
        "name": "Natural Rubber",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["rubber", "natural rubber", "latex", "rubber sheets"],
        "hs_codes": ["4001", "4001.10"],
        "typical_range": (1.20, 3.50),
        "current_estimate": 1.65,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "RUBBER1_MYSG"},
    },
    "TEA": {
        "name": "Tea",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["tea", "black tea", "green tea", "tea leaves"],
        "hs_codes": ["0902", "0902.30"],
        "typical_range": (2.00, 6.00),
        "current_estimate": 3.20,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "TEA_AVG"},
    },
    
    # ==================== ENERGY ====================
    "CRUDE_OIL_BRENT": {
        "name": "Crude Oil (Brent)",
        "category": "energy",
        "unit": "bbl",
        "aliases": ["crude oil", "brent", "brent crude", "oil"],
        "hs_codes": ["2709", "2709.00"],
        "typical_range": (50, 130),
        "current_estimate": 82,
        "data_sources": ["world_bank", "fred", "eia"],
        "source_codes": {"world_bank": "CRUDE_BRENT", "fred": "DCOILBRENTEU"},
    },
    "CRUDE_OIL_WTI": {
        "name": "Crude Oil (WTI)",
        "category": "energy",
        "unit": "bbl",
        "aliases": ["wti", "west texas intermediate", "us crude"],
        "hs_codes": ["2709", "2709.00"],
        "typical_range": (45, 125),
        "current_estimate": 78,
        "data_sources": ["fred", "eia"],
        "source_codes": {"fred": "DCOILWTICO"},
    },
    "NATURAL_GAS": {
        "name": "Natural Gas",
        "category": "energy",
        "unit": "mmbtu",
        "aliases": ["natural gas", "lng", "gas"],
        "hs_codes": ["2711.11", "2711.21"],
        "typical_range": (2.0, 10.0),
        "current_estimate": 3.2,
        "data_sources": ["world_bank", "fred"],
        "source_codes": {"world_bank": "NGAS_US", "fred": "DHHNGSP"},
    },
    "COAL": {
        "name": "Coal (Thermal)",
        "category": "energy",
        "unit": "mt",
        "aliases": ["coal", "thermal coal", "steam coal"],
        "hs_codes": ["2701", "2701.19"],
        "typical_range": (60, 250),
        "current_estimate": 130,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "COAL_AUS"},
    },
    "FUEL_OIL": {
        "name": "Fuel Oil",
        "category": "energy",
        "unit": "mt",
        "aliases": ["fuel oil", "furnace oil", "heavy fuel oil", "hfo"],
        "hs_codes": ["2710.19"],
        "typical_range": (350, 750),
        "current_estimate": 520,
        "data_sources": ["platts"],
    },
    
    # ==================== METALS ====================
    "STEEL_HRC": {
        "name": "Steel (Hot Rolled Coil)",
        "category": "metals",
        "unit": "mt",
        "aliases": ["steel", "hrc", "hot rolled coil", "hr coil", "steel coil"],
        "hs_codes": ["7208", "7208.27"],
        "typical_range": (400, 1200),
        "current_estimate": 650,
        "data_sources": ["lme", "platts"],
        "source_codes": {"world_bank": "STEEL_INDEX"},
    },
    "STEEL_CRC": {
        "name": "Steel (Cold Rolled Coil)",
        "category": "metals",
        "unit": "mt",
        "aliases": ["crc", "cold rolled coil", "cr coil", "cold rolled steel"],
        "hs_codes": ["7209", "7209.18"],
        "typical_range": (500, 1400),
        "current_estimate": 750,
        "data_sources": ["lme", "platts"],
    },
    "STEEL_REBAR": {
        "name": "Steel Rebar",
        "category": "metals",
        "unit": "mt",
        "aliases": ["rebar", "reinforcing bar", "tmt bar", "deformed bar"],
        "hs_codes": ["7214", "7214.20"],
        "typical_range": (400, 900),
        "current_estimate": 580,
        "data_sources": ["platts"],
    },
    "COPPER": {
        "name": "Copper",
        "category": "metals",
        "unit": "mt",
        "aliases": ["copper", "copper cathode", "refined copper"],
        "hs_codes": ["7403", "7403.11"],
        "typical_range": (5500, 11000),
        "current_estimate": 8500,
        "data_sources": ["world_bank", "lme"],
        "source_codes": {"world_bank": "COPPER"},
    },
    "ALUMINUM": {
        "name": "Aluminum",
        "category": "metals",
        "unit": "mt",
        "aliases": ["aluminum", "aluminium", "aluminum ingot"],
        "hs_codes": ["7601", "7601.10"],
        "typical_range": (1800, 3500),
        "current_estimate": 2400,
        "data_sources": ["world_bank", "lme"],
        "source_codes": {"world_bank": "ALUMINUM"},
    },
    "ZINC": {
        "name": "Zinc",
        "category": "metals",
        "unit": "mt",
        "aliases": ["zinc", "zinc ingot"],
        "hs_codes": ["7901", "7901.11"],
        "typical_range": (2000, 4500),
        "current_estimate": 2650,
        "data_sources": ["world_bank", "lme"],
        "source_codes": {"world_bank": "ZINC"},
    },
    "IRON_ORE": {
        "name": "Iron Ore",
        "category": "metals",
        "unit": "mt",
        "aliases": ["iron ore", "iron ore fines", "iron ore pellets"],
        "hs_codes": ["2601", "2601.11"],
        "typical_range": (60, 200),
        "current_estimate": 110,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "IRON_ORE"},
    },
    "NICKEL": {
        "name": "Nickel",
        "category": "metals",
        "unit": "mt",
        "aliases": ["nickel", "nickel cathode"],
        "hs_codes": ["7502"],
        "typical_range": (12000, 30000),
        "current_estimate": 18000,
        "data_sources": ["world_bank", "lme"],
        "source_codes": {"world_bank": "NICKEL"},
    },
    "TIN": {
        "name": "Tin",
        "category": "metals",
        "unit": "mt",
        "aliases": ["tin", "tin ingot"],
        "hs_codes": ["8001"],
        "typical_range": (18000, 45000),
        "current_estimate": 28000,
        "data_sources": ["world_bank", "lme"],
        "source_codes": {"world_bank": "TIN"},
    },
    "LEAD": {
        "name": "Lead",
        "category": "metals",
        "unit": "mt",
        "aliases": ["lead", "lead ingot"],
        "hs_codes": ["7801"],
        "typical_range": (1800, 3000),
        "current_estimate": 2100,
        "data_sources": ["world_bank", "lme"],
        "source_codes": {"world_bank": "LEAD"},
    },
    "GOLD": {
        "name": "Gold",
        "category": "metals",
        "unit": "oz",
        "aliases": ["gold", "gold bullion", "gold bar"],
        "hs_codes": ["7108"],
        "typical_range": (1200, 2500),
        "current_estimate": 2050,
        "data_sources": ["world_bank", "fred"],
        "source_codes": {"world_bank": "GOLD", "fred": "GOLDAMGBD228NLBM"},
    },
    "SILVER": {
        "name": "Silver",
        "category": "metals",
        "unit": "oz",
        "aliases": ["silver", "silver bullion"],
        "hs_codes": ["7106"],
        "typical_range": (15, 35),
        "current_estimate": 24,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "SILVER"},
    },
    
    # ==================== TEXTILES ====================
    "COTTON_YARN": {
        "name": "Cotton Yarn",
        "category": "textiles",
        "unit": "kg",
        "aliases": ["yarn", "cotton yarn", "spun yarn", "carded yarn"],
        "hs_codes": ["5205", "5206"],
        "typical_range": (2.50, 6.00),
        "current_estimate": 3.80,
        "data_sources": ["custom"],
    },
    "POLYESTER_YARN": {
        "name": "Polyester Yarn",
        "category": "textiles",
        "unit": "kg",
        "aliases": ["polyester", "poy", "fdy", "synthetic yarn"],
        "hs_codes": ["5402"],
        "typical_range": (1.20, 3.00),
        "current_estimate": 1.80,
        "data_sources": ["custom"],
    },
    "DENIM_FABRIC": {
        "name": "Denim Fabric",
        "category": "textiles",
        "unit": "m",
        "aliases": ["denim", "jeans fabric", "denim cloth"],
        "hs_codes": ["5209"],
        "typical_range": (2.00, 8.00),
        "current_estimate": 4.50,
        "data_sources": ["custom"],
    },
    "WOVEN_FABRIC": {
        "name": "Woven Fabric (Cotton)",
        "category": "textiles",
        "unit": "m",
        "aliases": ["fabric", "woven fabric", "cotton fabric"],
        "hs_codes": ["5208", "5209"],
        "typical_range": (1.50, 6.00),
        "current_estimate": 3.00,
        "data_sources": ["custom"],
    },
    "GARMENTS_TSHIRT": {
        "name": "T-Shirts (Basic)",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["t-shirt", "tshirt", "t shirt", "tee", "knit top"],
        "hs_codes": ["6109"],
        "typical_range": (1.50, 8.00),
        "current_estimate": 3.50,
        "data_sources": ["custom"],
    },
    "GARMENTS_JEANS": {
        "name": "Jeans/Denim Pants",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["jeans", "denim pants", "denim trousers"],
        "hs_codes": ["6203.42", "6204.62"],
        "typical_range": (5.00, 25.00),
        "current_estimate": 12.00,
        "data_sources": ["custom"],
    },
    
    # ==================== CHEMICALS ====================
    "UREA": {
        "name": "Urea (Fertilizer)",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["urea", "urea fertilizer", "carbamide"],
        "hs_codes": ["3102.10"],
        "typical_range": (200, 800),
        "current_estimate": 350,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "UREA_EE_BULK"},
    },
    "DAP": {
        "name": "DAP (Fertilizer)",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["dap", "diammonium phosphate"],
        "hs_codes": ["3105.30"],
        "typical_range": (350, 900),
        "current_estimate": 520,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "DAP"},
    },
    "POTASH": {
        "name": "Potash (MOP)",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["potash", "mop", "potassium chloride"],
        "hs_codes": ["3104.20"],
        "typical_range": (200, 700),
        "current_estimate": 320,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "POTASH"},
    },
    "CAUSTIC_SODA": {
        "name": "Caustic Soda",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["caustic soda", "sodium hydroxide", "naoh", "lye"],
        "hs_codes": ["2815.11", "2815.12"],
        "typical_range": (300, 700),
        "current_estimate": 450,
        "data_sources": ["custom"],
    },
    "PVC_RESIN": {
        "name": "PVC Resin",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["pvc", "polyvinyl chloride", "pvc resin"],
        "hs_codes": ["3904.10"],
        "typical_range": (800, 1600),
        "current_estimate": 1100,
        "data_sources": ["custom"],
    },
    "HDPE": {
        "name": "HDPE (Polyethylene)",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["hdpe", "high density polyethylene", "polyethylene"],
        "hs_codes": ["3901.20"],
        "typical_range": (1000, 1800),
        "current_estimate": 1250,
        "data_sources": ["custom"],
    },
    
    # ==================== FOOD & BEVERAGE ====================
    "SHRIMP_FROZEN": {
        "name": "Frozen Shrimp",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["shrimp", "frozen shrimp", "prawns", "frozen prawns"],
        "hs_codes": ["0306.17", "0306.16"],
        "typical_range": (5.00, 18.00),
        "current_estimate": 9.00,
        "data_sources": ["custom"],
    },
    "FISH_FROZEN": {
        "name": "Frozen Fish",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["fish", "frozen fish", "seafood"],
        "hs_codes": ["0303"],
        "typical_range": (2.00, 10.00),
        "current_estimate": 4.50,
        "data_sources": ["custom"],
    },
    "BEEF_FROZEN": {
        "name": "Frozen Beef",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["beef", "frozen beef", "beef cuts"],
        "hs_codes": ["0202"],
        "typical_range": (4.00, 12.00),
        "current_estimate": 6.50,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "BEEF"},
    },
    "CHICKEN_FROZEN": {
        "name": "Frozen Chicken",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["chicken", "frozen chicken", "poultry"],
        "hs_codes": ["0207"],
        "typical_range": (1.50, 4.00),
        "current_estimate": 2.20,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "CHICKEN"},
    },
    
    # ==================== ELECTRONICS ====================
    "SEMICONDUCTORS": {
        "name": "Semiconductors (IC)",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["ic", "integrated circuit", "chip", "semiconductor"],
        "hs_codes": ["8542"],
        "typical_range": (0.10, 50.00),
        "current_estimate": 2.50,
        "data_sources": ["custom"],
    },
    "LCD_PANELS": {
        "name": "LCD Panels",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["lcd", "lcd panel", "display panel", "lcd screen"],
        "hs_codes": ["8529.90"],
        "typical_range": (20, 300),
        "current_estimate": 80,
        "data_sources": ["custom"],
    },
    "SOLAR_PANELS": {
        "name": "Solar Panels",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["solar panel", "pv panel", "solar module", "photovoltaic"],
        "hs_codes": ["8541.40"],
        "typical_range": (50, 250),
        "current_estimate": 120,
        "data_sources": ["custom"],
    },
}

# Unit conversion factors to base unit
UNIT_CONVERSIONS = {
    # Weight
    "kg": 1.0,
    "mt": 1000.0,  # metric ton
    "ton": 1000.0,
    "lb": 0.453592,
    "oz": 0.0283495,
    "g": 0.001,
    # Volume
    "bbl": 1.0,  # barrel (oil)
    "gal": 0.0238095,  # gallon to barrel
    "l": 0.00628981,  # liter to barrel
    "mmbtu": 1.0,  # million BTU (gas)
    # Length
    "m": 1.0,
    "yd": 0.9144,
    "ft": 0.3048,
    # Pieces
    "pcs": 1.0,
    "doz": 12.0,
    "gross": 144.0,
}

# =============================================================================
# CURRENCY CONVERSION
# =============================================================================
# Exchange rates to USD (updated periodically)
# Will attempt to fetch live rates, fallback to these if unavailable

FALLBACK_FX_RATES = {
    "USD": 1.0,
    "EUR": 0.92,     # 1 EUR = 1.087 USD
    "GBP": 0.79,     # 1 GBP = 1.266 USD
    "JPY": 149.50,   # 1 USD = 149.50 JPY
    "CNY": 7.24,     # 1 USD = 7.24 CNY
    "INR": 84.50,    # 1 USD = 84.50 INR
    "BDT": 119.50,   # 1 USD = 119.50 BDT
    "AED": 3.67,     # 1 USD = 3.67 AED
    "SAR": 3.75,     # 1 USD = 3.75 SAR
    "PKR": 278.50,   # 1 USD = 278.50 PKR
    "AUD": 1.54,     # 1 USD = 1.54 AUD
    "CAD": 1.39,     # 1 USD = 1.39 CAD
    "CHF": 0.88,     # 1 CHF = 1.14 USD
    "SGD": 1.35,     # 1 USD = 1.35 SGD
    "HKD": 7.78,     # 1 USD = 7.78 HKD
    "KRW": 1380.0,   # 1 USD = 1380 KRW
    "MYR": 4.47,     # 1 USD = 4.47 MYR
    "THB": 35.50,    # 1 USD = 35.50 THB
    "VND": 24500.0,  # 1 USD = 24500 VND
    "IDR": 15850.0,  # 1 USD = 15850 IDR
    "PHP": 58.50,    # 1 USD = 58.50 PHP
    "ZAR": 18.50,    # 1 USD = 18.50 ZAR
    "BRL": 5.85,     # 1 USD = 5.85 BRL
    "MXN": 17.50,    # 1 USD = 17.50 MXN
    "TRY": 34.20,    # 1 USD = 34.20 TRY
    "RUB": 96.50,    # 1 USD = 96.50 RUB
    "EGP": 49.50,    # 1 USD = 49.50 EGP
    "NGN": 1550.0,   # 1 USD = 1550 NGN
    "KES": 154.0,    # 1 USD = 154 KES
}

# Cache for live FX rates
_fx_rate_cache: Dict[str, Any] = {
    "rates": {},
    "timestamp": None,
    "source": "fallback",
}

async def get_fx_rates(http_client: httpx.AsyncClient = None) -> Dict[str, float]:
    """
    Get current FX rates to USD.
    Attempts to fetch from free APIs, falls back to static rates.
    """
    global _fx_rate_cache
    
    # Check cache (rates valid for 1 hour)
    if _fx_rate_cache["timestamp"]:
        cache_age = datetime.now() - _fx_rate_cache["timestamp"]
        if cache_age.total_seconds() < 3600 and _fx_rate_cache["rates"]:
            return _fx_rate_cache["rates"]
    
    # Try to fetch live rates
    if http_client:
        try:
            # Try exchangerate-api.com (free tier)
            response = await http_client.get(
                "https://open.er-api.com/v6/latest/USD",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    rates = data.get("rates", {})
                    _fx_rate_cache = {
                        "rates": rates,
                        "timestamp": datetime.now(),
                        "source": "exchangerate-api",
                    }
                    logger.info(f"Fetched {len(rates)} FX rates from API")
                    return rates
        except Exception as e:
            logger.warning(f"Failed to fetch live FX rates: {e}")
    
    # Return fallback rates
    _fx_rate_cache = {
        "rates": FALLBACK_FX_RATES,
        "timestamp": datetime.now(),
        "source": "fallback",
    }
    return FALLBACK_FX_RATES


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str = "USD",
    fx_rates: Dict[str, float] = None,
) -> Tuple[float, str]:
    """
    Convert amount from one currency to another.
    
    Returns:
        Tuple of (converted_amount, rate_source)
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if from_currency == to_currency:
        return amount, "same_currency"
    
    rates = fx_rates or FALLBACK_FX_RATES
    
    # Convert to USD first (if not already)
    if from_currency == "USD":
        usd_amount = amount
    elif from_currency in rates:
        usd_amount = amount / rates[from_currency]
    else:
        logger.warning(f"Unknown currency: {from_currency}, using 1:1 rate")
        usd_amount = amount
    
    # Convert from USD to target currency
    if to_currency == "USD":
        result = usd_amount
    elif to_currency in rates:
        result = usd_amount * rates[to_currency]
    else:
        logger.warning(f"Unknown currency: {to_currency}, using 1:1 rate")
        result = usd_amount
    
    source = _fx_rate_cache.get("source", "fallback") if fx_rates else "fallback"
    return round(result, 4), source


class PriceVerificationService:
    """
    Service for verifying trade document prices against market data.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.commodities = COMMODITIES_DATABASE
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.http_client.aclose()
    
    # =========================================================================
    # COMMODITY LOOKUP
    # =========================================================================
    
    def find_commodity(self, search_term: str) -> Optional[Dict]:
        """
        Find a commodity by name, alias, or HS code.
        Uses fuzzy matching for best results.
        """
        search_lower = search_term.lower().strip()
        
        # Direct code match
        if search_lower.upper() in self.commodities:
            return {
                "code": search_lower.upper(),
                **self.commodities[search_lower.upper()]
            }
        
        # Search by name and aliases
        best_match = None
        best_score = 0
        
        for code, data in self.commodities.items():
            score = 0
            
            # Exact name match
            if search_lower == data["name"].lower():
                return {"code": code, **data}
            
            # Partial name match
            if search_lower in data["name"].lower():
                score = len(search_lower) / len(data["name"])
            
            # Alias match
            for alias in data.get("aliases", []):
                if search_lower == alias.lower():
                    return {"code": code, **data}
                if search_lower in alias.lower():
                    alias_score = len(search_lower) / len(alias)
                    score = max(score, alias_score)
            
            # HS code match
            for hs in data.get("hs_codes", []):
                if search_lower.replace(".", "") == hs.replace(".", ""):
                    return {"code": code, **data}
                if hs.startswith(search_lower.replace(".", "")):
                    score = max(score, 0.8)
            
            if score > best_score:
                best_score = score
                best_match = {"code": code, **data}
        
        # Return best match if score is good enough
        if best_score >= 0.5:
            return best_match
        
        return None
    
    def list_commodities(self, category: Optional[str] = None) -> List[Dict]:
        """List all available commodities, optionally filtered by category."""
        result = []
        for code, data in self.commodities.items():
            if category and data.get("category") != category:
                continue
            
            # Get typical range
            typical_range = data.get("typical_range", (0, 0))
            price_low = typical_range[0] if typical_range else 0
            price_high = typical_range[1] if typical_range else 0
            
            # Determine data source display name
            source_codes = data.get("source_codes", {})
            has_live_feed = bool(source_codes)
            if source_codes.get("world_bank"):
                source_display = "World Bank"
            elif source_codes.get("fred"):
                source_display = "FRED"
            elif source_codes.get("lme"):
                source_display = "LME"
            else:
                source_display = "TRDR Database"
            
            result.append({
                "code": code,
                "name": data["name"],
                "category": data["category"],
                "unit": data["unit"],
                "current_estimate": data.get("current_estimate"),
                "price_low": price_low,
                "price_high": price_high,
                "has_live_feed": has_live_feed,
                "source_display": source_display,
                "source_code": source_codes.get("world_bank") or source_codes.get("fred") or source_codes.get("lme"),
            })
        return sorted(result, key=lambda x: (x["category"], x["name"]))
    
    def get_categories(self) -> List[Dict]:
        """Get list of commodity categories."""
        categories = {}
        for data in self.commodities.values():
            cat = data["category"]
            if cat not in categories:
                categories[cat] = {"name": cat, "count": 0}
            categories[cat]["count"] += 1
        return sorted(categories.values(), key=lambda x: x["name"])
    
    # =========================================================================
    # PRICE FETCHING
    # =========================================================================
    
    async def fetch_world_bank_price(self, indicator: str) -> Optional[Dict]:
        """
        Fetch commodity price from World Bank Commodity Markets data.
        """
        try:
            # World Bank Commodity Prices API
            url = f"https://api.worldbank.org/v2/country/wld/indicator/{indicator}"
            params = {
                "format": "json",
                "per_page": 5,
                "date": f"{datetime.now().year - 1}:{datetime.now().year}",
            }
            
            response = await self.http_client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1 and data[1]:
                    latest = data[1][0]
                    if latest.get("value"):
                        return {
                            "price": float(latest["value"]),
                            "source": "world_bank",
                            "date": latest.get("date"),
                            "indicator": indicator,
                        }
        except Exception as e:
            logger.warning(f"World Bank API error for {indicator}: {e}")
        
        return None
    
    async def fetch_fred_price(self, series_id: str) -> Optional[Dict]:
        """
        Fetch price from FRED (Federal Reserve Economic Data).
        Note: Requires API key for production use.
        """
        try:
            # For demo, we'll use the public observation endpoint
            # In production, you'd use the API with a key
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv"
            params = {
                "id": series_id,
                "cosd": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            }
            
            response = await self.http_client.get(url, params=params)
            if response.status_code == 200:
                # Parse CSV response
                lines = response.text.strip().split("\n")
                if len(lines) > 1:
                    latest_line = lines[-1]
                    parts = latest_line.split(",")
                    if len(parts) >= 2 and parts[1] != ".":
                        return {
                            "price": float(parts[1]),
                            "source": "fred",
                            "date": parts[0],
                            "series_id": series_id,
                        }
        except Exception as e:
            logger.warning(f"FRED API error for {series_id}: {e}")
        
        return None
    
    async def get_market_price(self, commodity_code: str) -> Dict:
        """
        Get current market price for a commodity from available sources.
        Falls back to database estimates if APIs fail.
        """
        commodity = self.commodities.get(commodity_code)
        if not commodity:
            return {"error": "Unknown commodity"}
        
        # Try live data sources
        live_price = None
        source = "estimate"
        
        source_codes = commodity.get("source_codes", {})
        
        # Try World Bank
        if "world_bank" in source_codes:
            result = await self.fetch_world_bank_price(source_codes["world_bank"])
            if result:
                live_price = result["price"]
                source = "world_bank"
        
        # Try FRED if World Bank failed
        if not live_price and "fred" in source_codes:
            result = await self.fetch_fred_price(source_codes["fred"])
            if result:
                live_price = result["price"]
                source = "fred"
        
        # Use database estimate as fallback
        price = live_price or commodity.get("current_estimate")
        typical_range = commodity.get("typical_range", (0, 0))
        
        return {
            "commodity_code": commodity_code,
            "commodity_name": commodity["name"],
            "price": price,
            "price_low": typical_range[0],
            "price_high": typical_range[1],
            "unit": commodity["unit"],
            "currency": "USD",
            "source": source,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    
    # =========================================================================
    # PRICE VERIFICATION
    # =========================================================================
    
    def normalize_price(
        self,
        price: float,
        from_unit: str,
        to_unit: str,
        from_currency: str = "USD",
        to_currency: str = "USD",
        fx_rates: Dict[str, float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Normalize price from one unit/currency to another.
        
        Returns:
            Tuple of (normalized_price, conversion_details)
        """
        conversion_details = {
            "original_price": price,
            "original_unit": from_unit,
            "original_currency": from_currency,
            "target_unit": to_unit,
            "target_currency": to_currency,
            "unit_conversion_factor": 1.0,
            "currency_conversion_rate": 1.0,
            "currency_source": "same_currency",
        }
        
        # Unit conversion
        from_factor = UNIT_CONVERSIONS.get(from_unit.lower(), 1.0)
        to_factor = UNIT_CONVERSIONS.get(to_unit.lower(), 1.0)
        
        unit_factor = from_factor / to_factor
        normalized = price * unit_factor
        conversion_details["unit_conversion_factor"] = round(unit_factor, 6)
        
        # Currency conversion (using global convert_currency function)
        if from_currency.upper() != to_currency.upper():
            normalized, source = convert_currency(
                normalized,
                from_currency,
                to_currency,
                fx_rates
            )
            # Calculate effective rate
            if from_currency.upper() != "USD":
                from_rate = (fx_rates or FALLBACK_FX_RATES).get(from_currency.upper(), 1.0)
            else:
                from_rate = 1.0
            if to_currency.upper() != "USD":
                to_rate = (fx_rates or FALLBACK_FX_RATES).get(to_currency.upper(), 1.0)
            else:
                to_rate = 1.0
            effective_rate = to_rate / from_rate
            conversion_details["currency_conversion_rate"] = round(effective_rate, 6)
            conversion_details["currency_source"] = source
        
        return round(normalized, 4), conversion_details
    
    def calculate_variance(
        self,
        document_price: float,
        market_price: float
    ) -> Tuple[float, float]:
        """
        Calculate variance between document and market price.
        Returns (variance_percent, variance_absolute)
        """
        if market_price == 0:
            return (0.0, 0.0)
        
        variance_absolute = document_price - market_price
        variance_percent = (variance_absolute / market_price) * 100
        
        return (round(variance_percent, 2), round(variance_absolute, 2))
    
    def assess_risk(
        self,
        variance_percent: float,
        document_price: float,
        typical_range: Tuple[float, float]
    ) -> Dict:
        """
        Assess risk level based on variance and typical range.
        """
        abs_variance = abs(variance_percent)
        
        # Risk level based on variance
        if abs_variance < 10:
            risk_level = "low"
        elif abs_variance < 25:
            risk_level = "medium"
        elif abs_variance < 50:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        # Risk flags
        flags = []
        
        if variance_percent > 25:
            flags.append("potential_over_invoicing")
        elif variance_percent < -25:
            flags.append("potential_under_invoicing")
        
        if typical_range and document_price < typical_range[0]:
            flags.append("below_historical_minimum")
        elif typical_range and document_price > typical_range[1]:
            flags.append("above_historical_maximum")
        
        if abs_variance > 50:
            flags.append("tbml_risk")
        
        return {
            "risk_level": risk_level,
            "risk_flags": flags,
        }
    
    def determine_verdict(
        self,
        variance_percent: float,
        risk_level: str,
        risk_flags: List[str]
    ) -> Tuple[str, str]:
        """
        Determine final verdict for the price verification.
        Returns (verdict, reason)
        """
        abs_variance = abs(variance_percent)
        
        if abs_variance < 15 and risk_level == "low":
            return ("pass", "Price is within acceptable market range (±15%)")
        
        if abs_variance < 30 and risk_level in ["low", "medium"]:
            direction = "above" if variance_percent > 0 else "below"
            return ("warning", f"Price is {abs_variance:.1f}% {direction} market average. Review recommended.")
        
        if "tbml_risk" in risk_flags:
            direction = "over" if variance_percent > 0 else "under"
            return ("fail", f"High {direction}-invoicing risk detected. {abs_variance:.1f}% variance requires enhanced due diligence.")
        
        direction = "above" if variance_percent > 0 else "below"
        return ("fail", f"Price is {abs_variance:.1f}% {direction} market average. Significant deviation detected.")
    
    async def verify_price(
        self,
        commodity_input: str,
        document_price: float,
        document_unit: str,
        document_currency: str = "USD",
        quantity: Optional[float] = None,
        document_type: Optional[str] = None,
        document_reference: Optional[str] = None,
        origin_country: Optional[str] = None,
        destination_country: Optional[str] = None,
    ) -> Dict:
        """
        Main verification function.
        
        Args:
            commodity_input: Commodity name, code, or HS code
            document_price: Price from the document (per unit)
            document_unit: Unit of measure from document
            document_currency: Currency (default USD)
            quantity: Optional quantity
            document_type: Type of document (invoice, lc, contract)
            document_reference: Reference number
            origin_country: ISO country code
            destination_country: ISO country code
        
        Returns:
            Complete verification result
        """
        # Find commodity
        commodity = self.find_commodity(commodity_input)
        if not commodity:
            return {
                "success": False,
                "error": f"Commodity not found: {commodity_input}",
                "suggestions": self._suggest_commodities(commodity_input),
            }
        
        # Get market price
        market_data = await self.get_market_price(commodity["code"])
        if "error" in market_data:
            return {
                "success": False,
                "error": market_data["error"],
            }
        
        # Fetch FX rates if needed (for currency conversion)
        fx_rates = None
        if document_currency.upper() != "USD":
            fx_rates = await get_fx_rates(self.http_client)
        
        # Normalize document price to commodity's standard unit and USD
        normalized_price, conversion_details = self.normalize_price(
            document_price,
            document_unit,
            commodity["unit"],
            document_currency,
            "USD",
            fx_rates
        )
        
        # Calculate variance
        variance_percent, variance_absolute = self.calculate_variance(
            normalized_price,
            market_data["price"]
        )
        
        # Assess risk
        risk_assessment = self.assess_risk(
            variance_percent,
            normalized_price,
            commodity.get("typical_range")
        )
        
        # Determine verdict
        verdict, verdict_reason = self.determine_verdict(
            variance_percent,
            risk_assessment["risk_level"],
            risk_assessment["risk_flags"]
        )
        
        # Calculate total value if quantity provided
        total_value = None
        if quantity:
            total_value = document_price * quantity
        
        # Build result
        result = {
            "success": True,
            "verification_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            
            # Commodity info
            "commodity": {
                "code": commodity["code"],
                "name": commodity["name"],
                "category": commodity["category"],
                "matched_from": commodity_input,
            },
            
            # Document price
            "document_price": {
                "price": document_price,
                "unit": document_unit,
                "currency": document_currency,
                "normalized_price": round(normalized_price, 4),
                "normalized_unit": commodity["unit"],
                "normalized_currency": "USD",
                "quantity": quantity,
                "total_value": total_value,
                "conversion": conversion_details,
            },
            
            # Market price
            "market_price": {
                "price": market_data["price"],
                "price_low": market_data["price_low"],
                "price_high": market_data["price_high"],
                "unit": market_data["unit"],
                "currency": market_data["currency"],
                "source": market_data["source"],
                "fetched_at": market_data["fetched_at"],
            },
            
            # Variance
            "variance": {
                "percent": variance_percent,
                "absolute": variance_absolute,
                "direction": "over" if variance_percent > 0 else "under" if variance_percent < 0 else "match",
            },
            
            # Risk
            "risk": risk_assessment,
            
            # Verdict
            "verdict": verdict,
            "verdict_reason": verdict_reason,
            
            # Context
            "context": {
                "document_type": document_type,
                "document_reference": document_reference,
                "origin_country": origin_country,
                "destination_country": destination_country,
            },
        }
        
        # =================================================================
        # AI ENHANCEMENTS (async, non-blocking)
        # =================================================================
        try:
            from app.services.price_ai import get_price_ai_service
            ai_service = get_price_ai_service()
            
            # Add AI variance explanation for warnings/failures
            if verdict in ["warning", "fail"]:
                ai_explanation = await ai_service.explain_variance(
                    commodity_name=commodity["name"],
                    commodity_code=commodity["code"],
                    category=commodity["category"],
                    doc_price=normalized_price,
                    market_price=market_data["price"],
                    unit=commodity["unit"],
                    variance_percent=variance_percent,
                    risk_level=risk_assessment["risk_level"],
                )
                result["ai_explanation"] = ai_explanation
            
            # Add TBML narrative for critical risk
            if "tbml_risk" in risk_assessment.get("risk_flags", []):
                tbml_narrative = await ai_service.generate_tbml_narrative(
                    commodity_name=commodity["name"],
                    doc_price=normalized_price,
                    market_price=market_data["price"],
                    unit=commodity["unit"],
                    variance_percent=variance_percent,
                    risk_flags=risk_assessment.get("risk_flags", []),
                )
                result["tbml_assessment"] = tbml_narrative
                
        except Exception as e:
            logger.warning(f"AI enhancement skipped: {e}")
        
        return result
    
    def _suggest_commodities(self, search_term: str) -> List[Dict]:
        """Suggest similar commodities when exact match not found."""
        search_lower = search_term.lower()
        suggestions = []
        
        for code, data in self.commodities.items():
            score = 0
            
            # Check name
            if search_lower in data["name"].lower():
                score = 0.5
            
            # Check aliases
            for alias in data.get("aliases", []):
                if search_lower in alias.lower():
                    score = max(score, 0.4)
            
            # Check category
            if search_lower in data["category"]:
                score = max(score, 0.3)
            
            if score > 0:
                suggestions.append({
                    "code": code,
                    "name": data["name"],
                    "category": data["category"],
                    "score": score,
                })
        
        return sorted(suggestions, key=lambda x: -x["score"])[:5]
    
    async def get_ai_commodity_suggestion(self, search_term: str) -> Optional[Dict]:
        """
        Use AI to suggest a commodity when fuzzy matching fails.
        Useful for typos, regional names, and trade variations.
        """
        try:
            from app.services.price_ai import get_price_ai_service
            ai_service = get_price_ai_service()
            
            suggestion = await ai_service.suggest_commodity(search_term)
            
            if suggestion.get("likely_commodity") and suggestion.get("confidence", 0) > 0.5:
                # Try to find this commodity in our database
                matched = self.find_commodity(suggestion["likely_commodity"])
                if matched:
                    return {
                        "matched_commodity": matched,
                        "ai_suggestion": suggestion,
                        "original_search": search_term,
                    }
            
            return {
                "matched_commodity": None,
                "ai_suggestion": suggestion,
                "original_search": search_term,
            }
            
        except Exception as e:
            logger.warning(f"AI commodity suggestion failed: {e}")
            return None
    
    # =========================================================================
    # BATCH VERIFICATION
    # =========================================================================
    
    async def verify_batch(
        self,
        items: List[Dict],
        document_type: Optional[str] = None,
        document_reference: Optional[str] = None,
    ) -> Dict:
        """
        Verify multiple items in a single request.
        
        Args:
            items: List of dicts with keys: commodity, price, unit, quantity (optional)
            document_type: Type of source document
            document_reference: Document reference number
        
        Returns:
            Batch verification results with summary
        """
        results = []
        total_value = 0
        total_value_at_market = 0
        max_risk = "low"
        risk_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        
        for item in items:
            result = await self.verify_price(
                commodity_input=item.get("commodity", ""),
                document_price=item.get("price", 0),
                document_unit=item.get("unit", ""),
                document_currency=item.get("currency", "USD"),
                quantity=item.get("quantity"),
                document_type=document_type,
                document_reference=document_reference,
            )
            results.append(result)
            
            if result.get("success"):
                # Accumulate totals
                if result["document_price"].get("total_value"):
                    total_value += result["document_price"]["total_value"]
                
                qty = result["document_price"].get("quantity") or 1
                market_total = result["market_price"]["price"] * qty
                total_value_at_market += market_total
                
                # Track max risk
                item_risk = result["risk"]["risk_level"]
                if risk_levels.get(item_risk, 0) > risk_levels.get(max_risk, 0):
                    max_risk = item_risk
        
        # Summary
        passed = sum(1 for r in results if r.get("verdict") == "pass")
        warnings = sum(1 for r in results if r.get("verdict") == "warning")
        failed = sum(1 for r in results if r.get("verdict") == "fail")
        errors = sum(1 for r in results if not r.get("success"))
        
        overall_variance = 0
        if total_value_at_market > 0:
            overall_variance = ((total_value - total_value_at_market) / total_value_at_market) * 100
        
        return {
            "success": True,
            "batch_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_items": len(items),
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "errors": errors,
                "total_document_value": round(total_value, 2),
                "total_market_value": round(total_value_at_market, 2),
                "overall_variance_percent": round(overall_variance, 2),
                "max_risk_level": max_risk,
            },
            "items": results,
            "context": {
                "document_type": document_type,
                "document_reference": document_reference,
            },
        }


# Singleton instance
_service_instance: Optional[PriceVerificationService] = None


def get_price_verification_service(db_session=None) -> PriceVerificationService:
    """Get or create the price verification service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = PriceVerificationService(db_session)
    return _service_instance

