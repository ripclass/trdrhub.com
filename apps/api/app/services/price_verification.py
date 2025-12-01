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
    
    # ==================== TOOLS & HARDWARE ====================
    "SOCKET_WRENCH": {
        "name": "Socket Wrench Set",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["socket wrench", "wrench set", "socket set", "ratchet wrench"],
        "hs_codes": ["8204.11", "8204"],
        "typical_range": (15, 150),
        "current_estimate": 45,
        "data_sources": ["custom"],
    },
    "HAND_TOOLS": {
        "name": "Hand Tools (General)",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["hand tools", "tools", "tool set", "mechanic tools"],
        "hs_codes": ["8205", "8206"],
        "typical_range": (5, 100),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "POWER_DRILL": {
        "name": "Power Drill",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["drill", "power drill", "electric drill", "cordless drill"],
        "hs_codes": ["8467.21"],
        "typical_range": (30, 300),
        "current_estimate": 85,
        "data_sources": ["custom"],
    },
    "SCREWDRIVER_SET": {
        "name": "Screwdriver Set",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["screwdriver", "screwdriver set", "screw driver"],
        "hs_codes": ["8205.40"],
        "typical_range": (5, 50),
        "current_estimate": 18,
        "data_sources": ["custom"],
    },
    "HAMMER": {
        "name": "Hammer",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["hammer", "claw hammer", "ball peen hammer"],
        "hs_codes": ["8205.20"],
        "typical_range": (5, 40),
        "current_estimate": 15,
        "data_sources": ["custom"],
    },
    "PLIERS": {
        "name": "Pliers",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["pliers", "combination pliers", "cutting pliers", "needle nose pliers"],
        "hs_codes": ["8203.20"],
        "typical_range": (3, 35),
        "current_estimate": 12,
        "data_sources": ["custom"],
    },
    "SAW_BLADE": {
        "name": "Saw Blade",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["saw blade", "circular saw blade", "cutting blade"],
        "hs_codes": ["8202.31", "8202.39"],
        "typical_range": (5, 80),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "MEASURING_TAPE": {
        "name": "Measuring Tape",
        "category": "tools",
        "unit": "pcs",
        "aliases": ["tape measure", "measuring tape", "ruler tape"],
        "hs_codes": ["9017.80"],
        "typical_range": (2, 25),
        "current_estimate": 8,
        "data_sources": ["custom"],
    },
    
    # ==================== REFRIGERANTS & GASES ====================
    "R600A": {
        "name": "Refrigerant R600a (Isobutane)",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["r600a", "refrigerant r600a", "isobutane", "r-600a", "hc-600a"],
        "hs_codes": ["2901.10", "2711.13"],
        "typical_range": (3, 15),
        "current_estimate": 7,
        "data_sources": ["custom"],
    },
    "R134A": {
        "name": "Refrigerant R134a",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["r134a", "refrigerant r134a", "r-134a", "hfc-134a"],
        "hs_codes": ["2903.39"],
        "typical_range": (5, 25),
        "current_estimate": 12,
        "data_sources": ["custom"],
    },
    "R410A": {
        "name": "Refrigerant R410a",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["r410a", "refrigerant r410a", "r-410a", "puron"],
        "hs_codes": ["3824.78"],
        "typical_range": (8, 30),
        "current_estimate": 15,
        "data_sources": ["custom"],
    },
    "R22": {
        "name": "Refrigerant R22",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["r22", "refrigerant r22", "r-22", "freon 22", "hcfc-22"],
        "hs_codes": ["2903.71"],
        "typical_range": (10, 50),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "NITROGEN_GAS": {
        "name": "Nitrogen Gas",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["nitrogen", "n2", "liquid nitrogen"],
        "hs_codes": ["2804.30"],
        "typical_range": (0.50, 3.00),
        "current_estimate": 1.20,
        "data_sources": ["custom"],
    },
    "OXYGEN_GAS": {
        "name": "Oxygen Gas",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["oxygen", "o2", "liquid oxygen"],
        "hs_codes": ["2804.40"],
        "typical_range": (0.30, 2.00),
        "current_estimate": 0.80,
        "data_sources": ["custom"],
    },
    "ARGON_GAS": {
        "name": "Argon Gas",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["argon", "ar", "liquid argon"],
        "hs_codes": ["2804.21"],
        "typical_range": (1.00, 5.00),
        "current_estimate": 2.50,
        "data_sources": ["custom"],
    },
    "CO2_GAS": {
        "name": "Carbon Dioxide Gas",
        "category": "chemicals",
        "unit": "kg",
        "aliases": ["co2", "carbon dioxide", "carbonic acid gas"],
        "hs_codes": ["2811.21"],
        "typical_range": (0.20, 1.50),
        "current_estimate": 0.50,
        "data_sources": ["custom"],
    },
    
    # ==================== SEAFOOD & FISH ====================
    "DRY_FISH": {
        "name": "Dry Fish",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["dry fish", "dried fish", "stockfish", "salted fish", "cured fish"],
        "hs_codes": ["0305.51", "0305.59", "0305"],
        "typical_range": (3, 20),
        "current_estimate": 8,
        "data_sources": ["custom"],
    },
    "TUNA_FROZEN": {
        "name": "Frozen Tuna",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["tuna", "frozen tuna", "yellowfin tuna", "skipjack tuna"],
        "hs_codes": ["0303.41", "0303.42", "0303.43"],
        "typical_range": (5, 25),
        "current_estimate": 12,
        "data_sources": ["custom"],
    },
    "SALMON_FROZEN": {
        "name": "Frozen Salmon",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["salmon", "frozen salmon", "atlantic salmon"],
        "hs_codes": ["0303.11", "0303.12", "0303.13"],
        "typical_range": (8, 25),
        "current_estimate": 15,
        "data_sources": ["custom"],
    },
    "TILAPIA": {
        "name": "Tilapia (Frozen)",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["tilapia", "frozen tilapia", "tilapia fillet"],
        "hs_codes": ["0303.23", "0304.61"],
        "typical_range": (2, 8),
        "current_estimate": 4,
        "data_sources": ["custom"],
    },
    "CRAB_FROZEN": {
        "name": "Frozen Crab",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["crab", "frozen crab", "crab meat", "king crab"],
        "hs_codes": ["0306.14", "0306.24"],
        "typical_range": (10, 50),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "LOBSTER_FROZEN": {
        "name": "Frozen Lobster",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["lobster", "frozen lobster", "rock lobster"],
        "hs_codes": ["0306.11", "0306.21"],
        "typical_range": (20, 80),
        "current_estimate": 45,
        "data_sources": ["custom"],
    },
    "SQUID_FROZEN": {
        "name": "Frozen Squid",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["squid", "frozen squid", "calamari"],
        "hs_codes": ["0307.43", "0307.49"],
        "typical_range": (3, 12),
        "current_estimate": 6,
        "data_sources": ["custom"],
    },
    "OCTOPUS": {
        "name": "Octopus (Frozen)",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["octopus", "frozen octopus"],
        "hs_codes": ["0307.51", "0307.59"],
        "typical_range": (5, 18),
        "current_estimate": 10,
        "data_sources": ["custom"],
    },
    "FISH_FILLET": {
        "name": "Fish Fillet (Frozen)",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["fish fillet", "fillet", "frozen fillet", "white fish fillet"],
        "hs_codes": ["0304.81", "0304.89"],
        "typical_range": (4, 15),
        "current_estimate": 7,
        "data_sources": ["custom"],
    },
    
    # ==================== GRAINS & CEREALS ====================
    "CORN_MAIZE": {
        "name": "Corn (Maize)",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["corn", "maize", "yellow corn", "feed corn"],
        "hs_codes": ["1005", "1005.90"],
        "typical_range": (150, 350),
        "current_estimate": 220,
        "data_sources": ["world_bank", "cbot"],
        "source_codes": {"world_bank": "MAIZE"},
    },
    "BARLEY": {
        "name": "Barley",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["barley", "feed barley", "malting barley"],
        "hs_codes": ["1003", "1003.90"],
        "typical_range": (150, 350),
        "current_estimate": 200,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "BARLEY"},
    },
    "OATS": {
        "name": "Oats",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["oats", "oat grain"],
        "hs_codes": ["1004", "1004.90"],
        "typical_range": (200, 400),
        "current_estimate": 280,
        "data_sources": ["custom"],
    },
    "SORGHUM": {
        "name": "Sorghum",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["sorghum", "milo", "grain sorghum"],
        "hs_codes": ["1007", "1007.90"],
        "typical_range": (150, 350),
        "current_estimate": 230,
        "data_sources": ["custom"],
    },
    "RICE_BASMATI": {
        "name": "Basmati Rice",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["basmati", "basmati rice", "aromatic rice"],
        "hs_codes": ["1006.30"],
        "typical_range": (600, 1500),
        "current_estimate": 950,
        "data_sources": ["custom"],
    },
    "RICE_PARBOILED": {
        "name": "Parboiled Rice",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["parboiled rice", "converted rice"],
        "hs_codes": ["1006.30"],
        "typical_range": (350, 700),
        "current_estimate": 480,
        "data_sources": ["custom"],
    },
    
    # ==================== PULSES & LEGUMES ====================
    "LENTILS": {
        "name": "Lentils",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["lentils", "red lentils", "green lentils", "masoor dal"],
        "hs_codes": ["0713.40"],
        "typical_range": (400, 1200),
        "current_estimate": 700,
        "data_sources": ["custom"],
    },
    "CHICKPEAS": {
        "name": "Chickpeas",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["chickpeas", "garbanzo beans", "chana", "gram"],
        "hs_codes": ["0713.20"],
        "typical_range": (400, 1000),
        "current_estimate": 650,
        "data_sources": ["custom"],
    },
    "BLACK_BEANS": {
        "name": "Black Beans",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["black beans", "turtle beans", "black kidney beans"],
        "hs_codes": ["0713.33"],
        "typical_range": (500, 1200),
        "current_estimate": 750,
        "data_sources": ["custom"],
    },
    "KIDNEY_BEANS": {
        "name": "Kidney Beans",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["kidney beans", "red kidney beans", "rajma"],
        "hs_codes": ["0713.33"],
        "typical_range": (500, 1100),
        "current_estimate": 700,
        "data_sources": ["custom"],
    },
    "GREEN_PEAS": {
        "name": "Green Peas (Dried)",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["peas", "green peas", "dried peas", "split peas"],
        "hs_codes": ["0713.10"],
        "typical_range": (300, 800),
        "current_estimate": 500,
        "data_sources": ["custom"],
    },
    "MUNG_BEANS": {
        "name": "Mung Beans",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["mung beans", "moong beans", "green gram"],
        "hs_codes": ["0713.31"],
        "typical_range": (500, 1300),
        "current_estimate": 800,
        "data_sources": ["custom"],
    },
    
    # ==================== OILS & FATS ====================
    "SOYBEAN_OIL": {
        "name": "Soybean Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["soybean oil", "soya oil", "soy oil"],
        "hs_codes": ["1507", "1507.90"],
        "typical_range": (800, 1600),
        "current_estimate": 1100,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "SOYBEAN_OIL"},
    },
    "SUNFLOWER_OIL": {
        "name": "Sunflower Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["sunflower oil", "sunflower seed oil"],
        "hs_codes": ["1512", "1512.11"],
        "typical_range": (900, 1800),
        "current_estimate": 1200,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "SUNFLOWER_OIL"},
    },
    "COCONUT_OIL": {
        "name": "Coconut Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["coconut oil", "copra oil"],
        "hs_codes": ["1513.11"],
        "typical_range": (800, 2000),
        "current_estimate": 1300,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "COCONUT_OIL"},
    },
    "OLIVE_OIL": {
        "name": "Olive Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["olive oil", "extra virgin olive oil", "evoo"],
        "hs_codes": ["1509"],
        "typical_range": (2500, 8000),
        "current_estimate": 4500,
        "data_sources": ["custom"],
    },
    "RAPESEED_OIL": {
        "name": "Rapeseed/Canola Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["rapeseed oil", "canola oil", "colza oil"],
        "hs_codes": ["1514"],
        "typical_range": (800, 1600),
        "current_estimate": 1100,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "RAPESEED_OIL"},
    },
    "GROUNDNUT_OIL": {
        "name": "Groundnut/Peanut Oil",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["groundnut oil", "peanut oil", "arachis oil"],
        "hs_codes": ["1508"],
        "typical_range": (1200, 2500),
        "current_estimate": 1800,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "GROUNDNUT_OIL"},
    },
    
    # ==================== SPICES ====================
    "BLACK_PEPPER": {
        "name": "Black Pepper",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["pepper", "black pepper", "peppercorn"],
        "hs_codes": ["0904.11"],
        "typical_range": (3, 12),
        "current_estimate": 6,
        "data_sources": ["custom"],
    },
    "CARDAMOM": {
        "name": "Cardamom",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["cardamom", "elaichi", "green cardamom"],
        "hs_codes": ["0908.31"],
        "typical_range": (15, 60),
        "current_estimate": 35,
        "data_sources": ["custom"],
    },
    "TURMERIC": {
        "name": "Turmeric",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["turmeric", "haldi", "curcuma"],
        "hs_codes": ["0910.30"],
        "typical_range": (2, 8),
        "current_estimate": 4,
        "data_sources": ["custom"],
    },
    "GINGER": {
        "name": "Ginger",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["ginger", "fresh ginger", "dried ginger"],
        "hs_codes": ["0910.11", "0910.12"],
        "typical_range": (1.5, 6),
        "current_estimate": 3,
        "data_sources": ["custom"],
    },
    "CINNAMON": {
        "name": "Cinnamon",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["cinnamon", "cassia", "cinnamon bark"],
        "hs_codes": ["0906.11", "0906.19"],
        "typical_range": (3, 15),
        "current_estimate": 7,
        "data_sources": ["custom"],
    },
    "CLOVES": {
        "name": "Cloves",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["cloves", "whole cloves"],
        "hs_codes": ["0907.10"],
        "typical_range": (8, 25),
        "current_estimate": 15,
        "data_sources": ["custom"],
    },
    "CUMIN": {
        "name": "Cumin Seeds",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["cumin", "cumin seeds", "jeera"],
        "hs_codes": ["0909.31"],
        "typical_range": (3, 12),
        "current_estimate": 6,
        "data_sources": ["custom"],
    },
    "CORIANDER": {
        "name": "Coriander Seeds",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["coriander", "coriander seeds", "dhania"],
        "hs_codes": ["0909.21"],
        "typical_range": (1.5, 5),
        "current_estimate": 2.5,
        "data_sources": ["custom"],
    },
    "CHILI_PEPPER": {
        "name": "Chili/Red Pepper",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["chili", "chilli", "red pepper", "dried chili", "paprika"],
        "hs_codes": ["0904.21", "0904.22"],
        "typical_range": (2, 10),
        "current_estimate": 5,
        "data_sources": ["custom"],
    },
    
    # ==================== NUTS ====================
    "CASHEW_NUTS": {
        "name": "Cashew Nuts",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["cashew", "cashew nuts", "cashews", "kaju"],
        "hs_codes": ["0801.32"],
        "typical_range": (6, 18),
        "current_estimate": 10,
        "data_sources": ["custom"],
    },
    "ALMONDS": {
        "name": "Almonds",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["almonds", "almond nuts", "badam"],
        "hs_codes": ["0802.11", "0802.12"],
        "typical_range": (5, 15),
        "current_estimate": 9,
        "data_sources": ["custom"],
    },
    "WALNUTS": {
        "name": "Walnuts",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["walnuts", "walnut", "akhrot"],
        "hs_codes": ["0802.31", "0802.32"],
        "typical_range": (4, 12),
        "current_estimate": 7,
        "data_sources": ["custom"],
    },
    "PISTACHIOS": {
        "name": "Pistachios",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["pistachios", "pistachio nuts", "pista"],
        "hs_codes": ["0802.51", "0802.52"],
        "typical_range": (8, 25),
        "current_estimate": 14,
        "data_sources": ["custom"],
    },
    "PEANUTS": {
        "name": "Peanuts/Groundnuts",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["peanuts", "groundnuts", "groundnut", "moong phali"],
        "hs_codes": ["1202", "1202.42"],
        "typical_range": (800, 2000),
        "current_estimate": 1200,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "GROUNDNUTS"},
    },
    "HAZELNUTS": {
        "name": "Hazelnuts",
        "category": "agriculture",
        "unit": "kg",
        "aliases": ["hazelnuts", "filberts", "cobnuts"],
        "hs_codes": ["0802.21", "0802.22"],
        "typical_range": (6, 18),
        "current_estimate": 11,
        "data_sources": ["custom"],
    },
    
    # ==================== FRUITS ====================
    "BANANAS": {
        "name": "Bananas",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["banana", "bananas", "cavendish banana"],
        "hs_codes": ["0803.90"],
        "typical_range": (400, 1200),
        "current_estimate": 750,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "BANANA_US"},
    },
    "ORANGES": {
        "name": "Oranges",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["oranges", "orange", "citrus orange"],
        "hs_codes": ["0805.10"],
        "typical_range": (400, 1000),
        "current_estimate": 650,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "ORANGE"},
    },
    "APPLES": {
        "name": "Apples",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["apples", "apple", "fresh apples"],
        "hs_codes": ["0808.10"],
        "typical_range": (500, 1500),
        "current_estimate": 900,
        "data_sources": ["custom"],
    },
    "GRAPES": {
        "name": "Grapes",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["grapes", "grape", "table grapes"],
        "hs_codes": ["0806.10"],
        "typical_range": (800, 2500),
        "current_estimate": 1400,
        "data_sources": ["custom"],
    },
    "MANGOES": {
        "name": "Mangoes",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["mango", "mangoes", "fresh mango"],
        "hs_codes": ["0804.50"],
        "typical_range": (600, 2000),
        "current_estimate": 1100,
        "data_sources": ["custom"],
    },
    "PINEAPPLES": {
        "name": "Pineapples",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["pineapple", "pineapples", "ananas"],
        "hs_codes": ["0804.30"],
        "typical_range": (300, 900),
        "current_estimate": 550,
        "data_sources": ["custom"],
    },
    "DATES": {
        "name": "Dates",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["dates", "date fruit", "khajoor"],
        "hs_codes": ["0804.10"],
        "typical_range": (800, 3000),
        "current_estimate": 1600,
        "data_sources": ["custom"],
    },
    
    # ==================== VEGETABLES ====================
    "ONIONS": {
        "name": "Onions",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["onions", "onion", "red onion", "white onion"],
        "hs_codes": ["0703.10"],
        "typical_range": (150, 600),
        "current_estimate": 300,
        "data_sources": ["custom"],
    },
    "POTATOES": {
        "name": "Potatoes",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["potatoes", "potato", "fresh potatoes"],
        "hs_codes": ["0701.90"],
        "typical_range": (150, 500),
        "current_estimate": 280,
        "data_sources": ["custom"],
    },
    "TOMATOES": {
        "name": "Tomatoes",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["tomatoes", "tomato", "fresh tomatoes"],
        "hs_codes": ["0702.00"],
        "typical_range": (300, 1000),
        "current_estimate": 550,
        "data_sources": ["custom"],
    },
    "GARLIC": {
        "name": "Garlic",
        "category": "agriculture",
        "unit": "mt",
        "aliases": ["garlic", "fresh garlic"],
        "hs_codes": ["0703.20"],
        "typical_range": (500, 2000),
        "current_estimate": 1000,
        "data_sources": ["custom"],
    },
    
    # ==================== MEAT & POULTRY ====================
    "LAMB_FROZEN": {
        "name": "Frozen Lamb",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["lamb", "frozen lamb", "lamb meat", "mutton"],
        "hs_codes": ["0204.42", "0204.43"],
        "typical_range": (5, 15),
        "current_estimate": 9,
        "data_sources": ["custom"],
    },
    "PORK_FROZEN": {
        "name": "Frozen Pork",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["pork", "frozen pork", "pork meat"],
        "hs_codes": ["0203.29"],
        "typical_range": (2, 7),
        "current_estimate": 4,
        "data_sources": ["custom"],
    },
    "TURKEY_FROZEN": {
        "name": "Frozen Turkey",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["turkey", "frozen turkey", "turkey meat"],
        "hs_codes": ["0207.26", "0207.27"],
        "typical_range": (2, 6),
        "current_estimate": 3.5,
        "data_sources": ["custom"],
    },
    "DUCK_FROZEN": {
        "name": "Frozen Duck",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["duck", "frozen duck", "duck meat"],
        "hs_codes": ["0207.44", "0207.45"],
        "typical_range": (3, 10),
        "current_estimate": 6,
        "data_sources": ["custom"],
    },
    
    # ==================== DAIRY ====================
    "MILK_POWDER": {
        "name": "Milk Powder (Whole)",
        "category": "food_beverage",
        "unit": "mt",
        "aliases": ["milk powder", "whole milk powder", "wmp", "dried milk"],
        "hs_codes": ["0402.21"],
        "typical_range": (2500, 5000),
        "current_estimate": 3500,
        "data_sources": ["custom"],
    },
    "SKIM_MILK_POWDER": {
        "name": "Skim Milk Powder",
        "category": "food_beverage",
        "unit": "mt",
        "aliases": ["skim milk powder", "smp", "nonfat dry milk"],
        "hs_codes": ["0402.10"],
        "typical_range": (2000, 4500),
        "current_estimate": 2800,
        "data_sources": ["custom"],
    },
    "BUTTER": {
        "name": "Butter",
        "category": "food_beverage",
        "unit": "mt",
        "aliases": ["butter", "dairy butter", "unsalted butter"],
        "hs_codes": ["0405.10"],
        "typical_range": (3500, 7000),
        "current_estimate": 5000,
        "data_sources": ["custom"],
    },
    "CHEESE": {
        "name": "Cheese (Cheddar)",
        "category": "food_beverage",
        "unit": "mt",
        "aliases": ["cheese", "cheddar", "cheddar cheese"],
        "hs_codes": ["0406.90"],
        "typical_range": (3000, 6000),
        "current_estimate": 4200,
        "data_sources": ["custom"],
    },
    "GHEE": {
        "name": "Ghee (Clarified Butter)",
        "category": "food_beverage",
        "unit": "kg",
        "aliases": ["ghee", "clarified butter", "butter oil"],
        "hs_codes": ["0405.90"],
        "typical_range": (5, 15),
        "current_estimate": 9,
        "data_sources": ["custom"],
    },
    
    # ==================== BEVERAGES ====================
    "ORANGE_JUICE": {
        "name": "Orange Juice (Concentrate)",
        "category": "food_beverage",
        "unit": "mt",
        "aliases": ["orange juice", "oj", "fcoj", "orange juice concentrate"],
        "hs_codes": ["2009.11", "2009.12"],
        "typical_range": (1500, 4000),
        "current_estimate": 2500,
        "data_sources": ["custom"],
    },
    "APPLE_JUICE": {
        "name": "Apple Juice (Concentrate)",
        "category": "food_beverage",
        "unit": "mt",
        "aliases": ["apple juice", "apple juice concentrate"],
        "hs_codes": ["2009.71"],
        "typical_range": (1000, 2500),
        "current_estimate": 1600,
        "data_sources": ["custom"],
    },
    
    # ==================== CONSTRUCTION MATERIALS ====================
    "CEMENT": {
        "name": "Portland Cement",
        "category": "construction",
        "unit": "mt",
        "aliases": ["cement", "portland cement", "opc", "ppc"],
        "hs_codes": ["2523.29", "2523.21"],
        "typical_range": (50, 150),
        "current_estimate": 85,
        "data_sources": ["custom"],
    },
    "GLASS_FLOAT": {
        "name": "Float Glass",
        "category": "construction",
        "unit": "sqm",
        "aliases": ["glass", "float glass", "window glass", "sheet glass"],
        "hs_codes": ["7005.21", "7005.29"],
        "typical_range": (3, 20),
        "current_estimate": 8,
        "data_sources": ["custom"],
    },
    "PLYWOOD": {
        "name": "Plywood",
        "category": "construction",
        "unit": "cbm",
        "aliases": ["plywood", "ply wood", "plywood sheet"],
        "hs_codes": ["4412"],
        "typical_range": (200, 600),
        "current_estimate": 350,
        "data_sources": ["custom"],
    },
    "TIMBER_HARDWOOD": {
        "name": "Hardwood Timber",
        "category": "construction",
        "unit": "cbm",
        "aliases": ["timber", "hardwood", "lumber", "wood"],
        "hs_codes": ["4407.29", "4407.99"],
        "typical_range": (300, 1200),
        "current_estimate": 600,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "LOGS_MYS"},
    },
    "TILES_CERAMIC": {
        "name": "Ceramic Tiles",
        "category": "construction",
        "unit": "sqm",
        "aliases": ["tiles", "ceramic tiles", "floor tiles", "wall tiles"],
        "hs_codes": ["6907", "6908"],
        "typical_range": (3, 25),
        "current_estimate": 10,
        "data_sources": ["custom"],
    },
    "MARBLE": {
        "name": "Marble Slabs",
        "category": "construction",
        "unit": "sqm",
        "aliases": ["marble", "marble slab", "marble tile"],
        "hs_codes": ["6802.91"],
        "typical_range": (20, 150),
        "current_estimate": 60,
        "data_sources": ["custom"],
    },
    "GRANITE": {
        "name": "Granite Slabs",
        "category": "construction",
        "unit": "sqm",
        "aliases": ["granite", "granite slab", "granite tile"],
        "hs_codes": ["6802.93"],
        "typical_range": (15, 100),
        "current_estimate": 45,
        "data_sources": ["custom"],
    },
    "SAND": {
        "name": "Construction Sand",
        "category": "construction",
        "unit": "mt",
        "aliases": ["sand", "river sand", "construction sand", "silica sand"],
        "hs_codes": ["2505.10"],
        "typical_range": (10, 50),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "GRAVEL": {
        "name": "Gravel/Aggregate",
        "category": "construction",
        "unit": "mt",
        "aliases": ["gravel", "aggregate", "crushed stone"],
        "hs_codes": ["2517.10"],
        "typical_range": (10, 40),
        "current_estimate": 20,
        "data_sources": ["custom"],
    },
    "BRICKS": {
        "name": "Clay Bricks",
        "category": "construction",
        "unit": "pcs",
        "aliases": ["bricks", "clay bricks", "red bricks", "building bricks"],
        "hs_codes": ["6904.10"],
        "typical_range": (0.10, 0.50),
        "current_estimate": 0.25,
        "data_sources": ["custom"],
    },
    
    # ==================== MACHINERY & EQUIPMENT ====================
    "GENERATOR": {
        "name": "Diesel Generator",
        "category": "machinery",
        "unit": "pcs",
        "aliases": ["generator", "diesel generator", "genset", "power generator"],
        "hs_codes": ["8502.11", "8502.12", "8502.13"],
        "typical_range": (1000, 50000),
        "current_estimate": 8000,
        "data_sources": ["custom"],
    },
    "ELECTRIC_MOTOR": {
        "name": "Electric Motor",
        "category": "machinery",
        "unit": "pcs",
        "aliases": ["motor", "electric motor", "ac motor", "induction motor"],
        "hs_codes": ["8501.51", "8501.52", "8501.53"],
        "typical_range": (50, 5000),
        "current_estimate": 500,
        "data_sources": ["custom"],
    },
    "PUMP_WATER": {
        "name": "Water Pump",
        "category": "machinery",
        "unit": "pcs",
        "aliases": ["pump", "water pump", "centrifugal pump", "submersible pump"],
        "hs_codes": ["8413.70", "8413.81"],
        "typical_range": (50, 3000),
        "current_estimate": 400,
        "data_sources": ["custom"],
    },
    "COMPRESSOR": {
        "name": "Air Compressor",
        "category": "machinery",
        "unit": "pcs",
        "aliases": ["compressor", "air compressor"],
        "hs_codes": ["8414.40", "8414.80"],
        "typical_range": (200, 10000),
        "current_estimate": 1500,
        "data_sources": ["custom"],
    },
    "TRANSFORMER": {
        "name": "Electrical Transformer",
        "category": "machinery",
        "unit": "pcs",
        "aliases": ["transformer", "power transformer", "distribution transformer"],
        "hs_codes": ["8504.21", "8504.22", "8504.23"],
        "typical_range": (500, 50000),
        "current_estimate": 5000,
        "data_sources": ["custom"],
    },
    "SEWING_MACHINE": {
        "name": "Industrial Sewing Machine",
        "category": "machinery",
        "unit": "pcs",
        "aliases": ["sewing machine", "industrial sewing machine", "garment machine"],
        "hs_codes": ["8452.21", "8452.29"],
        "typical_range": (200, 3000),
        "current_estimate": 800,
        "data_sources": ["custom"],
    },
    
    # ==================== AUTOMOTIVE PARTS ====================
    "TIRES_PASSENGER": {
        "name": "Passenger Car Tires",
        "category": "automotive",
        "unit": "pcs",
        "aliases": ["tires", "tyres", "car tires", "passenger tires"],
        "hs_codes": ["4011.10"],
        "typical_range": (30, 200),
        "current_estimate": 80,
        "data_sources": ["custom"],
    },
    "TIRES_TRUCK": {
        "name": "Truck Tires",
        "category": "automotive",
        "unit": "pcs",
        "aliases": ["truck tires", "truck tyres", "commercial tires"],
        "hs_codes": ["4011.20"],
        "typical_range": (150, 800),
        "current_estimate": 350,
        "data_sources": ["custom"],
    },
    "CAR_BATTERY": {
        "name": "Car Battery",
        "category": "automotive",
        "unit": "pcs",
        "aliases": ["battery", "car battery", "auto battery", "lead acid battery"],
        "hs_codes": ["8507.10"],
        "typical_range": (50, 200),
        "current_estimate": 100,
        "data_sources": ["custom"],
    },
    "BRAKE_PADS": {
        "name": "Brake Pads",
        "category": "automotive",
        "unit": "set",
        "aliases": ["brake pads", "brake shoes", "disc pads"],
        "hs_codes": ["6813.81"],
        "typical_range": (15, 100),
        "current_estimate": 40,
        "data_sources": ["custom"],
    },
    "OIL_FILTER": {
        "name": "Oil Filter",
        "category": "automotive",
        "unit": "pcs",
        "aliases": ["oil filter", "engine oil filter", "car filter"],
        "hs_codes": ["8421.23"],
        "typical_range": (3, 25),
        "current_estimate": 10,
        "data_sources": ["custom"],
    },
    "SPARK_PLUGS": {
        "name": "Spark Plugs",
        "category": "automotive",
        "unit": "pcs",
        "aliases": ["spark plug", "spark plugs", "ignition plug"],
        "hs_codes": ["8511.10"],
        "typical_range": (2, 20),
        "current_estimate": 8,
        "data_sources": ["custom"],
    },
    
    # ==================== PAPER & PACKAGING ====================
    "PAPER_PRINTING": {
        "name": "Printing Paper",
        "category": "paper",
        "unit": "mt",
        "aliases": ["paper", "printing paper", "offset paper", "copy paper"],
        "hs_codes": ["4802.55", "4802.56"],
        "typical_range": (600, 1200),
        "current_estimate": 850,
        "data_sources": ["custom"],
    },
    "PAPER_KRAFT": {
        "name": "Kraft Paper",
        "category": "paper",
        "unit": "mt",
        "aliases": ["kraft paper", "kraft", "brown paper"],
        "hs_codes": ["4804.11", "4804.19"],
        "typical_range": (500, 1000),
        "current_estimate": 700,
        "data_sources": ["custom"],
    },
    "CARDBOARD": {
        "name": "Cardboard/Carton",
        "category": "paper",
        "unit": "mt",
        "aliases": ["cardboard", "carton", "corrugated board", "packaging board"],
        "hs_codes": ["4808.10"],
        "typical_range": (400, 900),
        "current_estimate": 600,
        "data_sources": ["custom"],
    },
    "TISSUE_PAPER": {
        "name": "Tissue Paper",
        "category": "paper",
        "unit": "mt",
        "aliases": ["tissue", "tissue paper", "facial tissue", "toilet paper"],
        "hs_codes": ["4818.10", "4818.20"],
        "typical_range": (800, 1800),
        "current_estimate": 1200,
        "data_sources": ["custom"],
    },
    
    # ==================== PHARMACEUTICALS & MEDICAL ====================
    "PARACETAMOL": {
        "name": "Paracetamol/Acetaminophen",
        "category": "pharmaceuticals",
        "unit": "kg",
        "aliases": ["paracetamol", "acetaminophen", "tylenol api"],
        "hs_codes": ["2924.29", "3004.90"],
        "typical_range": (3, 15),
        "current_estimate": 7,
        "data_sources": ["custom"],
    },
    "AMOXICILLIN": {
        "name": "Amoxicillin",
        "category": "pharmaceuticals",
        "unit": "kg",
        "aliases": ["amoxicillin", "amoxycillin"],
        "hs_codes": ["2941.10", "3004.10"],
        "typical_range": (20, 80),
        "current_estimate": 45,
        "data_sources": ["custom"],
    },
    "VITAMIN_C": {
        "name": "Vitamin C (Ascorbic Acid)",
        "category": "pharmaceuticals",
        "unit": "kg",
        "aliases": ["vitamin c", "ascorbic acid"],
        "hs_codes": ["2936.27"],
        "typical_range": (3, 12),
        "current_estimate": 6,
        "data_sources": ["custom"],
    },
    "SURGICAL_GLOVES": {
        "name": "Surgical Gloves",
        "category": "medical",
        "unit": "pcs",
        "aliases": ["gloves", "surgical gloves", "latex gloves", "nitrile gloves", "examination gloves"],
        "hs_codes": ["4015.11", "4015.19"],
        "typical_range": (0.02, 0.15),
        "current_estimate": 0.05,
        "data_sources": ["custom"],
    },
    "FACE_MASKS": {
        "name": "Face Masks (Medical)",
        "category": "medical",
        "unit": "pcs",
        "aliases": ["mask", "face mask", "surgical mask", "medical mask", "n95"],
        "hs_codes": ["6307.90", "6210.10"],
        "typical_range": (0.03, 0.50),
        "current_estimate": 0.10,
        "data_sources": ["custom"],
    },
    "SYRINGES": {
        "name": "Disposable Syringes",
        "category": "medical",
        "unit": "pcs",
        "aliases": ["syringe", "syringes", "disposable syringe"],
        "hs_codes": ["9018.31"],
        "typical_range": (0.02, 0.20),
        "current_estimate": 0.08,
        "data_sources": ["custom"],
    },
    
    # ==================== PLASTICS ====================
    "PET_RESIN": {
        "name": "PET Resin",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["pet", "pet resin", "polyethylene terephthalate"],
        "hs_codes": ["3907.61"],
        "typical_range": (900, 1600),
        "current_estimate": 1150,
        "data_sources": ["custom"],
    },
    "PP_RESIN": {
        "name": "Polypropylene Resin",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["pp", "polypropylene", "pp resin"],
        "hs_codes": ["3902.10", "3902.30"],
        "typical_range": (1000, 1700),
        "current_estimate": 1250,
        "data_sources": ["custom"],
    },
    "LDPE": {
        "name": "LDPE (Low Density Polyethylene)",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["ldpe", "low density polyethylene"],
        "hs_codes": ["3901.10"],
        "typical_range": (1000, 1700),
        "current_estimate": 1200,
        "data_sources": ["custom"],
    },
    "PS_RESIN": {
        "name": "Polystyrene Resin",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["ps", "polystyrene", "gpps", "hips"],
        "hs_codes": ["3903.11", "3903.19"],
        "typical_range": (1100, 1800),
        "current_estimate": 1350,
        "data_sources": ["custom"],
    },
    "ABS_RESIN": {
        "name": "ABS Resin",
        "category": "chemicals",
        "unit": "mt",
        "aliases": ["abs", "acrylonitrile butadiene styrene"],
        "hs_codes": ["3903.30"],
        "typical_range": (1400, 2200),
        "current_estimate": 1700,
        "data_sources": ["custom"],
    },
    
    # ==================== ADDITIONAL METALS ====================
    "STAINLESS_STEEL": {
        "name": "Stainless Steel",
        "category": "metals",
        "unit": "mt",
        "aliases": ["stainless steel", "ss", "ss304", "ss316", "inox"],
        "hs_codes": ["7218", "7219"],
        "typical_range": (2000, 4500),
        "current_estimate": 2800,
        "data_sources": ["custom"],
    },
    "BRASS": {
        "name": "Brass",
        "category": "metals",
        "unit": "mt",
        "aliases": ["brass", "brass ingot", "brass sheet"],
        "hs_codes": ["7403.21"],
        "typical_range": (4000, 8000),
        "current_estimate": 5500,
        "data_sources": ["custom"],
    },
    "BRONZE": {
        "name": "Bronze",
        "category": "metals",
        "unit": "mt",
        "aliases": ["bronze", "bronze alloy"],
        "hs_codes": ["7403.29"],
        "typical_range": (5000, 10000),
        "current_estimate": 7000,
        "data_sources": ["custom"],
    },
    "TITANIUM": {
        "name": "Titanium",
        "category": "metals",
        "unit": "kg",
        "aliases": ["titanium", "ti", "titanium alloy"],
        "hs_codes": ["8108.20"],
        "typical_range": (15, 50),
        "current_estimate": 28,
        "data_sources": ["custom"],
    },
    "PLATINUM": {
        "name": "Platinum",
        "category": "metals",
        "unit": "oz",
        "aliases": ["platinum", "pt"],
        "hs_codes": ["7110.11"],
        "typical_range": (800, 1500),
        "current_estimate": 1000,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "PLATINUM"},
    },
    "PALLADIUM": {
        "name": "Palladium",
        "category": "metals",
        "unit": "oz",
        "aliases": ["palladium", "pd"],
        "hs_codes": ["7110.21"],
        "typical_range": (900, 2500),
        "current_estimate": 1200,
        "data_sources": ["custom"],
    },
    "SCRAP_STEEL": {
        "name": "Steel Scrap",
        "category": "metals",
        "unit": "mt",
        "aliases": ["scrap", "steel scrap", "ferrous scrap", "hms"],
        "hs_codes": ["7204"],
        "typical_range": (250, 550),
        "current_estimate": 380,
        "data_sources": ["custom"],
    },
    "SCRAP_COPPER": {
        "name": "Copper Scrap",
        "category": "metals",
        "unit": "mt",
        "aliases": ["copper scrap", "copper wire scrap"],
        "hs_codes": ["7404"],
        "typical_range": (5000, 9000),
        "current_estimate": 7000,
        "data_sources": ["custom"],
    },
    "SCRAP_ALUMINUM": {
        "name": "Aluminum Scrap",
        "category": "metals",
        "unit": "mt",
        "aliases": ["aluminum scrap", "aluminium scrap", "alu scrap"],
        "hs_codes": ["7602"],
        "typical_range": (1200, 2500),
        "current_estimate": 1700,
        "data_sources": ["custom"],
    },
    
    # ==================== TEXTILES ADDITIONAL ====================
    "SILK_RAW": {
        "name": "Raw Silk",
        "category": "textiles",
        "unit": "kg",
        "aliases": ["silk", "raw silk", "silk yarn"],
        "hs_codes": ["5002", "5004"],
        "typical_range": (30, 80),
        "current_estimate": 50,
        "data_sources": ["custom"],
    },
    "WOOL_RAW": {
        "name": "Raw Wool",
        "category": "textiles",
        "unit": "kg",
        "aliases": ["wool", "raw wool", "sheep wool", "greasy wool"],
        "hs_codes": ["5101"],
        "typical_range": (3, 15),
        "current_estimate": 7,
        "data_sources": ["world_bank"],
        "source_codes": {"world_bank": "WOOL_COARSE"},
    },
    "LINEN_FABRIC": {
        "name": "Linen Fabric",
        "category": "textiles",
        "unit": "m",
        "aliases": ["linen", "linen fabric", "flax fabric"],
        "hs_codes": ["5309"],
        "typical_range": (4, 20),
        "current_estimate": 10,
        "data_sources": ["custom"],
    },
    "LEATHER": {
        "name": "Leather (Bovine)",
        "category": "textiles",
        "unit": "sqft",
        "aliases": ["leather", "bovine leather", "cowhide", "cattle leather"],
        "hs_codes": ["4104", "4107"],
        "typical_range": (2, 12),
        "current_estimate": 5,
        "data_sources": ["custom"],
    },
    "JUTE_RAW": {
        "name": "Raw Jute",
        "category": "textiles",
        "unit": "mt",
        "aliases": ["jute", "raw jute", "jute fiber"],
        "hs_codes": ["5303"],
        "typical_range": (400, 900),
        "current_estimate": 600,
        "data_sources": ["custom"],
    },
    "JUTE_BAGS": {
        "name": "Jute Bags",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["jute bag", "jute sack", "burlap bag", "hessian bag"],
        "hs_codes": ["6305.10"],
        "typical_range": (0.50, 3.00),
        "current_estimate": 1.50,
        "data_sources": ["custom"],
    },
    "GARMENTS_SHIRTS": {
        "name": "Woven Shirts",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["shirts", "woven shirt", "dress shirt", "formal shirt"],
        "hs_codes": ["6205", "6206"],
        "typical_range": (3, 20),
        "current_estimate": 8,
        "data_sources": ["custom"],
    },
    "GARMENTS_JACKETS": {
        "name": "Jackets/Blazers",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["jacket", "blazer", "coat", "suit jacket"],
        "hs_codes": ["6203.31", "6203.32", "6203.33"],
        "typical_range": (15, 80),
        "current_estimate": 35,
        "data_sources": ["custom"],
    },
    "GARMENTS_SWEATERS": {
        "name": "Sweaters/Pullovers",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["sweater", "pullover", "knitwear", "cardigan"],
        "hs_codes": ["6110"],
        "typical_range": (4, 25),
        "current_estimate": 10,
        "data_sources": ["custom"],
    },
    "GARMENTS_UNDERWEAR": {
        "name": "Underwear",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["underwear", "briefs", "boxers", "panties"],
        "hs_codes": ["6107", "6108"],
        "typical_range": (0.50, 5.00),
        "current_estimate": 2.00,
        "data_sources": ["custom"],
    },
    "GARMENTS_SOCKS": {
        "name": "Socks",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["socks", "hosiery", "stockings"],
        "hs_codes": ["6115"],
        "typical_range": (0.30, 3.00),
        "current_estimate": 1.00,
        "data_sources": ["custom"],
    },
    "FOOTWEAR_LEATHER": {
        "name": "Leather Footwear",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["shoes", "leather shoes", "footwear", "leather boots"],
        "hs_codes": ["6403"],
        "typical_range": (8, 60),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "FOOTWEAR_SPORTS": {
        "name": "Sports Footwear",
        "category": "textiles",
        "unit": "pcs",
        "aliases": ["sneakers", "sports shoes", "athletic shoes", "trainers"],
        "hs_codes": ["6404.11"],
        "typical_range": (5, 50),
        "current_estimate": 18,
        "data_sources": ["custom"],
    },
    
    # ==================== HOME APPLIANCES ====================
    "REFRIGERATOR": {
        "name": "Refrigerator",
        "category": "appliances",
        "unit": "pcs",
        "aliases": ["refrigerator", "fridge", "freezer"],
        "hs_codes": ["8418.10", "8418.21"],
        "typical_range": (150, 1000),
        "current_estimate": 400,
        "data_sources": ["custom"],
    },
    "WASHING_MACHINE": {
        "name": "Washing Machine",
        "category": "appliances",
        "unit": "pcs",
        "aliases": ["washing machine", "washer", "laundry machine"],
        "hs_codes": ["8450.11", "8450.12"],
        "typical_range": (150, 800),
        "current_estimate": 350,
        "data_sources": ["custom"],
    },
    "AIR_CONDITIONER": {
        "name": "Air Conditioner",
        "category": "appliances",
        "unit": "pcs",
        "aliases": ["air conditioner", "ac", "split ac", "window ac"],
        "hs_codes": ["8415.10", "8415.81"],
        "typical_range": (200, 1500),
        "current_estimate": 500,
        "data_sources": ["custom"],
    },
    "TELEVISION": {
        "name": "Television",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["tv", "television", "led tv", "lcd tv", "smart tv"],
        "hs_codes": ["8528.72"],
        "typical_range": (100, 2000),
        "current_estimate": 400,
        "data_sources": ["custom"],
    },
    "MICROWAVE_OVEN": {
        "name": "Microwave Oven",
        "category": "appliances",
        "unit": "pcs",
        "aliases": ["microwave", "microwave oven"],
        "hs_codes": ["8516.50"],
        "typical_range": (40, 300),
        "current_estimate": 100,
        "data_sources": ["custom"],
    },
    "FAN_CEILING": {
        "name": "Ceiling Fan",
        "category": "appliances",
        "unit": "pcs",
        "aliases": ["fan", "ceiling fan", "electric fan"],
        "hs_codes": ["8414.51"],
        "typical_range": (15, 100),
        "current_estimate": 40,
        "data_sources": ["custom"],
    },
    
    # ==================== CONSUMER ELECTRONICS ====================
    "SMARTPHONE": {
        "name": "Smartphone",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["phone", "smartphone", "mobile phone", "cell phone"],
        "hs_codes": ["8517.12"],
        "typical_range": (50, 1500),
        "current_estimate": 300,
        "data_sources": ["custom"],
    },
    "LAPTOP": {
        "name": "Laptop Computer",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["laptop", "notebook", "portable computer"],
        "hs_codes": ["8471.30"],
        "typical_range": (200, 2500),
        "current_estimate": 600,
        "data_sources": ["custom"],
    },
    "TABLET": {
        "name": "Tablet Computer",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["tablet", "ipad", "tab"],
        "hs_codes": ["8471.30"],
        "typical_range": (100, 1200),
        "current_estimate": 350,
        "data_sources": ["custom"],
    },
    "HEADPHONES": {
        "name": "Headphones/Earphones",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["headphones", "earphones", "earbuds", "headset"],
        "hs_codes": ["8518.30"],
        "typical_range": (5, 400),
        "current_estimate": 50,
        "data_sources": ["custom"],
    },
    "USB_CABLE": {
        "name": "USB Cable",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["usb cable", "charging cable", "data cable", "usb-c cable"],
        "hs_codes": ["8544.42"],
        "typical_range": (0.50, 20),
        "current_estimate": 3,
        "data_sources": ["custom"],
    },
    "POWER_BANK": {
        "name": "Power Bank",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["power bank", "portable charger", "battery pack"],
        "hs_codes": ["8507.60"],
        "typical_range": (5, 80),
        "current_estimate": 20,
        "data_sources": ["custom"],
    },
    "LED_BULB": {
        "name": "LED Light Bulb",
        "category": "electronics",
        "unit": "pcs",
        "aliases": ["led bulb", "led lamp", "led light", "light bulb"],
        "hs_codes": ["8539.50"],
        "typical_range": (1, 15),
        "current_estimate": 4,
        "data_sources": ["custom"],
    },
    
    # ==================== TOYS & GAMES ====================
    "TOYS_PLASTIC": {
        "name": "Plastic Toys",
        "category": "toys",
        "unit": "pcs",
        "aliases": ["toys", "plastic toys", "children toys"],
        "hs_codes": ["9503.00"],
        "typical_range": (0.50, 50),
        "current_estimate": 8,
        "data_sources": ["custom"],
    },
    "TOYS_ELECTRONIC": {
        "name": "Electronic Toys",
        "category": "toys",
        "unit": "pcs",
        "aliases": ["electronic toys", "battery toys", "remote control toys"],
        "hs_codes": ["9503.00"],
        "typical_range": (5, 100),
        "current_estimate": 25,
        "data_sources": ["custom"],
    },
    "BICYCLES": {
        "name": "Bicycles",
        "category": "toys",
        "unit": "pcs",
        "aliases": ["bicycle", "bike", "cycle"],
        "hs_codes": ["8712.00"],
        "typical_range": (50, 500),
        "current_estimate": 150,
        "data_sources": ["custom"],
    },
    
    # ==================== FURNITURE ====================
    "FURNITURE_WOODEN": {
        "name": "Wooden Furniture",
        "category": "furniture",
        "unit": "pcs",
        "aliases": ["furniture", "wooden furniture", "wood furniture"],
        "hs_codes": ["9403.50", "9403.60"],
        "typical_range": (50, 500),
        "current_estimate": 150,
        "data_sources": ["custom"],
    },
    "FURNITURE_METAL": {
        "name": "Metal Furniture",
        "category": "furniture",
        "unit": "pcs",
        "aliases": ["metal furniture", "steel furniture", "office furniture"],
        "hs_codes": ["9403.20"],
        "typical_range": (30, 400),
        "current_estimate": 120,
        "data_sources": ["custom"],
    },
    "MATTRESS": {
        "name": "Mattress",
        "category": "furniture",
        "unit": "pcs",
        "aliases": ["mattress", "bed mattress", "foam mattress", "spring mattress"],
        "hs_codes": ["9404.21", "9404.29"],
        "typical_range": (50, 500),
        "current_estimate": 150,
        "data_sources": ["custom"],
    },
    
    # ==================== PRECIOUS STONES ====================
    "DIAMONDS": {
        "name": "Diamonds (Industrial)",
        "category": "precious_stones",
        "unit": "ct",
        "aliases": ["diamond", "diamonds", "industrial diamond"],
        "hs_codes": ["7102.10", "7102.21"],
        "typical_range": (50, 500),
        "current_estimate": 150,
        "data_sources": ["custom"],
    },
    "RUBIES": {
        "name": "Rubies",
        "category": "precious_stones",
        "unit": "ct",
        "aliases": ["ruby", "rubies"],
        "hs_codes": ["7103.91"],
        "typical_range": (100, 5000),
        "current_estimate": 500,
        "data_sources": ["custom"],
    },
    "SAPPHIRES": {
        "name": "Sapphires",
        "category": "precious_stones",
        "unit": "ct",
        "aliases": ["sapphire", "sapphires", "blue sapphire"],
        "hs_codes": ["7103.91"],
        "typical_range": (50, 3000),
        "current_estimate": 300,
        "data_sources": ["custom"],
    },
    "EMERALDS": {
        "name": "Emeralds",
        "category": "precious_stones",
        "unit": "ct",
        "aliases": ["emerald", "emeralds"],
        "hs_codes": ["7103.91"],
        "typical_range": (100, 5000),
        "current_estimate": 600,
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
        self._resolution_service = None
    
    async def close(self):
        await self.http_client.aclose()
    
    def _get_resolution_service(self):
        """Get or create commodity resolution service."""
        if self._resolution_service is None:
            from app.services.commodity_resolution import CommodityResolutionService
            self._resolution_service = CommodityResolutionService(self.db)
        return self._resolution_service
    
    # =========================================================================
    # COMMODITY LOOKUP (Enhanced with Resolution Service)
    # =========================================================================
    
    async def resolve_commodity(
        self,
        search_term: str,
        hs_code: Optional[str] = None,
    ) -> Dict:
        """
        Resolve a commodity using the full resolution chain.
        This NEVER returns None - always provides usable data.
        
        Resolution chain:
        1. Exact match in database
        2. Fuzzy match
        3. HS code lookup
        4. AI classification
        5. Category fallback
        
        Returns:
            Dict with commodity data including resolution metadata
        """
        service = self._get_resolution_service()
        resolved = await service.resolve(search_term, hs_code)
        
        # Convert to legacy format for backward compatibility
        return {
            "code": resolved.code or search_term.upper().replace(" ", "_"),
            "name": resolved.name,
            "category": resolved.category,
            "unit": resolved.unit,
            "aliases": [],
            "hs_codes": [resolved.hs_code] if resolved.hs_code else [],
            "typical_range": (resolved.price_low, resolved.price_high),
            "current_estimate": resolved.current_estimate,
            "data_sources": [],
            # Resolution metadata (new fields)
            "_resolution": {
                "source": resolved.source.value,
                "confidence": resolved.confidence,
                "matched_to": resolved.matched_to,
                "verified": resolved.verified,
                "has_live_feed": resolved.has_live_feed,
                "suggestions": resolved.suggestions,
                "warnings": resolved.warnings,
            }
        }
    
    def find_commodity(self, search_term: str) -> Optional[Dict]:
        """
        Find a commodity by name, alias, or HS code.
        Uses fuzzy matching for best results.
        
        NOTE: This is the LEGACY method. For new code, use resolve_commodity()
        which never returns None and provides better results.
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
            
            # Determine data source display name - be honest about sources
            source_codes = data.get("source_codes", {})
            has_live_feed = bool(source_codes)
            if source_codes.get("world_bank"):
                source_display = "World Bank"
            elif source_codes.get("fred"):
                source_display = "FRED"
            elif source_codes.get("lme"):
                source_display = "LME"
            else:
                source_display = "Curated Estimate"  # Honest - not real market data
            
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
        
        IMPORTANT: Includes sanity check to ensure API prices are reasonable.
        Some APIs return index values (like FRED PPI) instead of actual prices.
        """
        commodity = self.commodities.get(commodity_code)
        if not commodity:
            return {"error": "Unknown commodity"}
        
        # Get expected price range for sanity checking
        typical_range = commodity.get("typical_range", (0, 0))
        price_low, price_high = typical_range
        estimate = commodity.get("current_estimate", (price_low + price_high) / 2 if price_low else 0)
        
        # Define reasonable bounds (5x the typical range allows for market volatility)
        max_reasonable = price_high * 5 if price_high else estimate * 5
        min_reasonable = price_low * 0.2 if price_low else estimate * 0.2
        
        # Try live data sources
        live_price = None
        source = "estimate"
        
        source_codes = commodity.get("source_codes", {})
        
        # Try World Bank
        if "world_bank" in source_codes:
            result = await self.fetch_world_bank_price(source_codes["world_bank"])
            if result:
                fetched_price = result["price"]
                # Sanity check: is this price reasonable?
                if min_reasonable <= fetched_price <= max_reasonable:
                    live_price = fetched_price
                    source = "world_bank"
                else:
                    logger.warning(
                        f"World Bank price {fetched_price} for {commodity_code} outside reasonable range "
                        f"({min_reasonable:.2f} - {max_reasonable:.2f}), using estimate"
                    )
        
        # Try FRED if World Bank failed
        if not live_price and "fred" in source_codes:
            result = await self.fetch_fred_price(source_codes["fred"])
            if result:
                fetched_price = result["price"]
                # Sanity check: FRED often returns index values, not actual prices!
                # Index values are typically 50-500, actual commodity prices vary
                if min_reasonable <= fetched_price <= max_reasonable:
                    live_price = fetched_price
                    source = "fred"
                else:
                    logger.warning(
                        f"FRED price {fetched_price} for {commodity_code} looks like an index value "
                        f"(not in range {min_reasonable:.2f} - {max_reasonable:.2f}), using estimate"
                    )
        
        # Use database estimate as fallback
        price = live_price or estimate
        
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
    
    def _get_unit_type(self, unit: str) -> str:
        """Categorize unit into types for comparison."""
        unit_lower = unit.lower().strip()
        
        # Weight units
        if unit_lower in ["kg", "g", "lb", "lbs", "oz", "mt", "ton", "tons", "tonne", "tonnes", "kilogram", "gram", "pound"]:
            return "weight"
        
        # Volume units
        if unit_lower in ["l", "liter", "liters", "litre", "litres", "ml", "bbl", "barrel", "barrels", "gal", "gallon"]:
            return "volume"
        
        # Piece/count units
        if unit_lower in ["pcs", "pc", "piece", "pieces", "unit", "units", "ea", "each", "no", "nos", "set", "sets", "pair", "pairs"]:
            return "count"
        
        # Container units
        if unit_lower in ["carton", "cartons", "box", "boxes", "bag", "bags", "ctn", "case", "cases"]:
            return "container"
        
        # Length units
        if unit_lower in ["m", "meter", "meters", "ft", "feet", "yard", "yards", "yd"]:
            return "length"
        
        # Area units
        if unit_lower in ["sqm", "sqft", "square meter", "square feet"]:
            return "area"
        
        return "unknown"
    
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
        hs_code: Optional[str] = None,
    ) -> Dict:
        """
        Main verification function.
        
        Args:
            commodity_input: Commodity name, code, or HS code
            document_price: Price from the document (per unit)
            document_unit: Unit of measure from document
            document_currency: Currency (default USD)
            quantity: Optional quantity
            hs_code: Optional HS code for better commodity resolution
            document_type: Type of document (invoice, lc, contract)
            document_reference: Reference number
            origin_country: ISO country code
            destination_country: ISO country code
        
        Returns:
            Complete verification result
        """
        # Use resolution service - NEVER fails, always returns usable data
        # Pass hs_code if available for better matching
        commodity = await self.resolve_commodity(commodity_input, hs_code)
        resolution_meta = commodity.get("_resolution", {})
        
        # Get market price (use estimate if not in database)
        if commodity.get("current_estimate") and resolution_meta.get("source") in ["category_fallback", "ai_estimate", "hs_code"]:
            # For unknown commodities, use the estimated price range
            typical_range = commodity.get("typical_range", (None, None))
            price_low = typical_range[0] if typical_range else None
            price_high = typical_range[1] if typical_range else None
            
            market_data = {
                "price": commodity["current_estimate"],
                "price_low": price_low,
                "price_high": price_high,
                "source": resolution_meta.get("source", "estimate"),
                "unit": commodity.get("unit", "kg"),
                "currency": "USD",
                "fetched_at": datetime.utcnow().isoformat(),
                "typical_range": typical_range,
            }
        else:
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
        
        # Check for unit mismatch warning
        unit_mismatch_warning = None
        doc_unit_type = self._get_unit_type(document_unit)
        market_unit_type = self._get_unit_type(commodity["unit"])
        
        if doc_unit_type != market_unit_type and doc_unit_type != "unknown" and market_unit_type != "unknown":
            unit_mismatch_warning = (
                f"Unit mismatch: Document uses '{document_unit}' ({doc_unit_type}) "
                f"but market data uses '{commodity['unit']}' ({market_unit_type}). "
                f"Price comparison may not be accurate."
            )
            # Add to risk flags
            if "unit_mismatch" not in risk_assessment["risk_flags"]:
                risk_assessment["risk_flags"].append("unit_mismatch")
            # Add warning to resolution warnings
            if resolution_meta.get("warnings") is None:
                resolution_meta["warnings"] = []
            resolution_meta["warnings"].append(unit_mismatch_warning)
        
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
            
            # Resolution metadata (for unknown commodities)
            "resolution": {
                "source": resolution_meta.get("source", "exact_match"),
                "confidence": resolution_meta.get("confidence", 1.0),
                "matched_to": resolution_meta.get("matched_to"),
                "verified": resolution_meta.get("verified", True),
                "suggestions": resolution_meta.get("suggestions", []),
                "warnings": resolution_meta.get("warnings", []),
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

