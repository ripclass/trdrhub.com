"""
US HTS Data Import Script

Imports US Harmonized Tariff Schedule data into the database.
Data source: https://hts.usitc.gov/current

Usage:
    python -m scripts.import_hts_data [--sample]
    
    --sample: Import sample data for testing
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.hs_code import (
    HSCodeTariff, DutyRate, FTAAgreement, FTARule,
    ChapterNote, BindingRuling, Section301Rate
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample US HTS Data - Top commodities and common products
SAMPLE_HTS_DATA = [
    # Chapter 01-05: Live Animals & Animal Products
    {"code": "0101.21.0000", "description": "Horses: Pure-bred breeding animals", "unit": "NO.", "mfn_rate": 0, "chapter": "01", "heading": "0101"},
    {"code": "0201.10.0500", "description": "Bovine carcasses and half-carcasses, fresh or chilled", "unit": "KG", "mfn_rate": 4.4, "chapter": "02", "heading": "0201"},
    {"code": "0201.30.0200", "description": "Bovine meat, boneless, fresh or chilled, described in additional US note 3", "unit": "KG", "mfn_rate": 4.4, "chapter": "02", "heading": "0201"},
    {"code": "0207.11.0000", "description": "Chickens, not cut in pieces, fresh or chilled", "unit": "KG", "mfn_rate": 0, "chapter": "02", "heading": "0207"},
    {"code": "0207.14.0010", "description": "Chicken cuts and offal, frozen: Leg quarters", "unit": "KG", "mfn_rate": 17.6, "chapter": "02", "heading": "0207"},
    {"code": "0303.11.0000", "description": "Sockeye salmon (red salmon), frozen, excluding fillets", "unit": "KG", "mfn_rate": 0, "chapter": "03", "heading": "0303"},
    {"code": "0304.81.1010", "description": "Fish fillets, frozen: Atlantic salmon", "unit": "KG", "mfn_rate": 0, "chapter": "03", "heading": "0304"},
    {"code": "0306.17.0003", "description": "Shrimps and prawns, frozen, shell-on", "unit": "KG", "mfn_rate": 0, "chapter": "03", "heading": "0306"},
    {"code": "0402.10.1000", "description": "Milk and cream, concentrated, in powder form, not exceeding 1.5% fat", "unit": "KG", "mfn_rate": 0, "chapter": "04", "heading": "0402"},
    {"code": "0406.10.0800", "description": "Fresh cheese (unripened), mozzarella", "unit": "KG", "mfn_rate": 0, "chapter": "04", "heading": "0406"},

    # Chapter 06-14: Vegetable Products
    {"code": "0713.33.2040", "description": "Beans, dried, kidney beans", "unit": "KG", "mfn_rate": 0, "chapter": "07", "heading": "0713"},
    {"code": "0803.90.0045", "description": "Bananas, fresh, other than plantains", "unit": "KG", "mfn_rate": 0, "chapter": "08", "heading": "0803"},
    {"code": "0805.10.0040", "description": "Oranges, fresh, Navels", "unit": "KG", "mfn_rate": 1.9, "chapter": "08", "heading": "0805"},
    {"code": "0901.11.0015", "description": "Coffee, not roasted, not decaffeinated, Arabica", "unit": "KG", "mfn_rate": 0, "chapter": "09", "heading": "0901"},
    {"code": "0901.21.0010", "description": "Coffee, roasted, not decaffeinated, in retail containers", "unit": "KG", "mfn_rate": 0, "chapter": "09", "heading": "0901"},
    {"code": "1001.99.0085", "description": "Wheat and meslin, other than durum wheat, other", "unit": "KG", "mfn_rate": 0, "chapter": "10", "heading": "1001"},
    {"code": "1006.30.9010", "description": "Rice, semi-milled or wholly milled, long grain", "unit": "KG", "mfn_rate": 1.4, "chapter": "10", "heading": "1006"},
    {"code": "1201.90.0090", "description": "Soybeans, whether or not broken, other", "unit": "KG", "mfn_rate": 0, "chapter": "12", "heading": "1201"},

    # Chapter 15-24: Prepared Foods
    {"code": "1507.90.4000", "description": "Soybean oil and its fractions, refined", "unit": "KG", "mfn_rate": 19.1, "chapter": "15", "heading": "1507"},
    {"code": "1511.90.4000", "description": "Palm oil and its fractions, refined", "unit": "KG", "mfn_rate": 0, "chapter": "15", "heading": "1511"},
    {"code": "1701.14.1000", "description": "Raw cane sugar, for refining", "unit": "KG", "mfn_rate": 1.4606, "chapter": "17", "heading": "1701"},
    {"code": "1806.32.0600", "description": "Chocolate, blocks/slabs/bars, not filled, over 2kg", "unit": "KG", "mfn_rate": 5.6, "chapter": "18", "heading": "1806"},
    {"code": "2009.11.0000", "description": "Orange juice, frozen, concentrated", "unit": "LITER", "mfn_rate": 7.85, "chapter": "20", "heading": "2009"},
    {"code": "2106.90.9998", "description": "Food preparations not elsewhere specified, other", "unit": "KG", "mfn_rate": 6.4, "chapter": "21", "heading": "2106"},
    {"code": "2202.10.0000", "description": "Waters, including mineral and aerated, with sugar", "unit": "LITER", "mfn_rate": 0.2, "chapter": "22", "heading": "2202"},

    # Chapter 27-38: Chemicals & Plastics
    {"code": "2709.00.1000", "description": "Petroleum oils and oils from bituminous minerals, crude, testing under 25 degrees API", "unit": "BBL", "mfn_rate": 5.25, "chapter": "27", "heading": "2709"},
    {"code": "2710.19.0500", "description": "Petroleum oils, distillate and residual fuel oils", "unit": "BBL", "mfn_rate": 5.25, "chapter": "27", "heading": "2710"},
    {"code": "2711.11.0000", "description": "Natural gas, liquefied", "unit": "KG", "mfn_rate": 0, "chapter": "27", "heading": "2711"},
    {"code": "3004.90.9210", "description": "Medicaments, in measured doses, containing hormones", "unit": "KG", "mfn_rate": 0, "chapter": "30", "heading": "3004"},
    {"code": "3901.20.0000", "description": "Polyethylene, specific gravity 0.94 or more, in primary forms", "unit": "KG", "mfn_rate": 6.5, "chapter": "39", "heading": "3901"},
    {"code": "3902.10.0000", "description": "Polypropylene, in primary forms", "unit": "KG", "mfn_rate": 6.5, "chapter": "39", "heading": "3902"},
    {"code": "3904.10.0000", "description": "Polyvinyl chloride, not mixed with other substances", "unit": "KG", "mfn_rate": 5.8, "chapter": "39", "heading": "3904"},
    {"code": "3926.90.9996", "description": "Other articles of plastics, other", "unit": "KG", "mfn_rate": 5.3, "chapter": "39", "heading": "3926"},

    # Chapter 44-49: Wood & Paper
    {"code": "4407.29.0155", "description": "Lumber, tropical hardwood, sawn lengthwise", "unit": "CBM", "mfn_rate": 0, "chapter": "44", "heading": "4407"},
    {"code": "4412.31.0520", "description": "Plywood, with face ply of tropical wood, birch", "unit": "CBM", "mfn_rate": 8, "chapter": "44", "heading": "4412"},
    {"code": "4802.55.2000", "description": "Paper and paperboard, uncoated, 40g/m2 to 150g/m2", "unit": "KG", "mfn_rate": 0, "chapter": "48", "heading": "4802"},
    {"code": "4819.10.0040", "description": "Cartons, boxes, cases of corrugated paper", "unit": "KG", "mfn_rate": 0, "chapter": "48", "heading": "4819"},

    # Chapter 50-63: Textiles & Apparel
    {"code": "5201.00.1400", "description": "Cotton, not carded or combed, having staple length 1-1/8 inches or more", "unit": "KG", "mfn_rate": 0, "chapter": "52", "heading": "5201"},
    {"code": "5205.11.0000", "description": "Cotton yarn, single, uncombed, 714.29 decitex or more", "unit": "KG", "mfn_rate": 5, "chapter": "52", "heading": "5205"},
    {"code": "5209.42.0060", "description": "Woven fabrics of cotton, denim, weighing more than 200g/m2", "unit": "M2", "mfn_rate": 8.4, "chapter": "52", "heading": "5209"},
    {"code": "6109.10.0004", "description": "T-shirts, singlets, tank tops, of cotton, men's or boys'", "unit": "DOZ", "mfn_rate": 16.5, "chapter": "61", "heading": "6109"},
    {"code": "6109.10.0012", "description": "T-shirts, singlets, tank tops, of cotton, women's or girls'", "unit": "DOZ", "mfn_rate": 16.5, "chapter": "61", "heading": "6109"},
    {"code": "6109.90.1007", "description": "T-shirts, singlets, of man-made fibers, men's or boys'", "unit": "DOZ", "mfn_rate": 32, "chapter": "61", "heading": "6109"},
    {"code": "6110.20.2079", "description": "Sweaters, pullovers, of cotton, men's or boys'", "unit": "DOZ", "mfn_rate": 16.5, "chapter": "61", "heading": "6110"},
    {"code": "6203.42.4015", "description": "Men's or boys' trousers, of cotton, not corduroy", "unit": "DOZ", "mfn_rate": 16.6, "chapter": "62", "heading": "6203"},
    {"code": "6203.42.4020", "description": "Men's or boys' jeans, of cotton denim", "unit": "DOZ", "mfn_rate": 16.6, "chapter": "62", "heading": "6203"},
    {"code": "6204.62.4015", "description": "Women's or girls' trousers, of cotton, not corduroy", "unit": "DOZ", "mfn_rate": 16.6, "chapter": "62", "heading": "6204"},
    {"code": "6205.20.2025", "description": "Men's or boys' shirts, of cotton, other", "unit": "DOZ", "mfn_rate": 19.7, "chapter": "62", "heading": "6205"},
    {"code": "6206.40.3030", "description": "Women's or girls' blouses, of man-made fibers", "unit": "DOZ", "mfn_rate": 26.9, "chapter": "62", "heading": "6206"},

    # Chapter 64-67: Footwear
    {"code": "6403.59.9065", "description": "Footwear with outer soles of rubber/plastic, leather uppers, other", "unit": "PRS", "mfn_rate": 10, "chapter": "64", "heading": "6403"},
    {"code": "6404.11.9050", "description": "Sports footwear, tennis shoes, basketball shoes, etc.", "unit": "PRS", "mfn_rate": 20, "chapter": "64", "heading": "6404"},
    {"code": "6404.19.9060", "description": "Footwear with outer soles of rubber or plastics, textile uppers", "unit": "PRS", "mfn_rate": 12.5, "chapter": "64", "heading": "6404"},

    # Chapter 72-83: Metals
    {"code": "7208.27.0060", "description": "Hot-rolled iron/steel, coils, thickness 4.75mm or more", "unit": "KG", "mfn_rate": 0, "chapter": "72", "heading": "7208"},
    {"code": "7209.17.0090", "description": "Cold-rolled iron/steel, coils, thickness 0.5mm to 1mm", "unit": "KG", "mfn_rate": 0, "chapter": "72", "heading": "7209"},
    {"code": "7326.90.8688", "description": "Other articles of iron or steel, other", "unit": "KG", "mfn_rate": 2.9, "chapter": "73", "heading": "7326"},
    {"code": "7403.11.0000", "description": "Refined copper, cathodes and sections of cathodes", "unit": "KG", "mfn_rate": 0, "chapter": "74", "heading": "7403"},
    {"code": "7601.10.3000", "description": "Aluminum, unwrought, not alloyed, primary", "unit": "KG", "mfn_rate": 2.6, "chapter": "76", "heading": "7601"},
    {"code": "7606.11.3060", "description": "Aluminum plates/sheets, rectangular, not alloyed", "unit": "KG", "mfn_rate": 3, "chapter": "76", "heading": "7606"},

    # Chapter 84-85: Machinery & Electronics
    {"code": "8414.30.4000", "description": "Compressors for refrigerating equipment", "unit": "NO.", "mfn_rate": 0, "chapter": "84", "heading": "8414"},
    {"code": "8414.51.0040", "description": "Fans, table, floor, wall, ceiling, with motor not exceeding 125W", "unit": "NO.", "mfn_rate": 4.7, "chapter": "84", "heading": "8414"},
    {"code": "8418.10.0010", "description": "Refrigerator-freezers, combined units, household type", "unit": "NO.", "mfn_rate": 0, "chapter": "84", "heading": "8418"},
    {"code": "8450.11.0080", "description": "Household washing machines, fully automatic, capacity 10kg or less", "unit": "NO.", "mfn_rate": 1.4, "chapter": "84", "heading": "8450"},
    {"code": "8471.30.0100", "description": "Portable automatic data processing machines weighing 10kg or less (laptops)", "unit": "NO.", "mfn_rate": 0, "chapter": "84", "heading": "8471"},
    {"code": "8471.41.0150", "description": "Other automatic data processing machines, desktop computers", "unit": "NO.", "mfn_rate": 0, "chapter": "84", "heading": "8471"},
    {"code": "8471.70.2000", "description": "Storage units for automatic data processing machines (hard drives)", "unit": "NO.", "mfn_rate": 0, "chapter": "84", "heading": "8471"},
    {"code": "8473.30.1180", "description": "Parts for automatic data processing machines, other", "unit": "NO.", "mfn_rate": 0, "chapter": "84", "heading": "8473"},
    {"code": "8501.10.4060", "description": "Electric motors, DC, output not exceeding 750W", "unit": "NO.", "mfn_rate": 2.8, "chapter": "85", "heading": "8501"},
    {"code": "8504.40.9550", "description": "Static converters, rectifiers and rectifying apparatus", "unit": "NO.", "mfn_rate": 1.5, "chapter": "85", "heading": "8504"},
    {"code": "8507.60.0010", "description": "Lithium-ion batteries", "unit": "NO.", "mfn_rate": 3.4, "chapter": "85", "heading": "8507"},
    {"code": "8517.12.0050", "description": "Telephones for cellular networks (smartphones)", "unit": "NO.", "mfn_rate": 0, "chapter": "85", "heading": "8517"},
    {"code": "8517.62.0090", "description": "Machines for reception/conversion/transmission of voice/data (routers)", "unit": "NO.", "mfn_rate": 0, "chapter": "85", "heading": "8517"},
    {"code": "8518.21.0000", "description": "Single loudspeakers, mounted in their enclosures", "unit": "NO.", "mfn_rate": 4.9, "chapter": "85", "heading": "8518"},
    {"code": "8518.30.2000", "description": "Headphones and earphones", "unit": "NO.", "mfn_rate": 4.9, "chapter": "85", "heading": "8518"},
    {"code": "8525.80.5010", "description": "Television cameras (webcams)", "unit": "NO.", "mfn_rate": 0, "chapter": "85", "heading": "8525"},
    {"code": "8528.72.6400", "description": "Color video monitors, flat panel, LCD, LED", "unit": "NO.", "mfn_rate": 5, "chapter": "85", "heading": "8528"},
    {"code": "8541.40.2000", "description": "Light-emitting diodes (LEDs)", "unit": "NO.", "mfn_rate": 0, "chapter": "85", "heading": "8541"},
    {"code": "8542.31.0000", "description": "Electronic integrated circuits: Processors and controllers", "unit": "NO.", "mfn_rate": 0, "chapter": "85", "heading": "8542"},
    {"code": "8544.42.9090", "description": "Electric conductors, insulated, fitted with connectors", "unit": "KG", "mfn_rate": 2.6, "chapter": "85", "heading": "8544"},

    # Chapter 87: Vehicles
    {"code": "8703.23.0190", "description": "Motor cars, spark-ignition engine, 1500cc to 3000cc", "unit": "NO.", "mfn_rate": 2.5, "chapter": "87", "heading": "8703"},
    {"code": "8703.24.0190", "description": "Motor cars, spark-ignition engine, exceeding 3000cc", "unit": "NO.", "mfn_rate": 2.5, "chapter": "87", "heading": "8703"},
    {"code": "8703.32.0110", "description": "Motor cars, compression-ignition engine, 1500cc to 2500cc (diesel)", "unit": "NO.", "mfn_rate": 2.5, "chapter": "87", "heading": "8703"},
    {"code": "8703.80.0100", "description": "Electric motor vehicles for transport of persons", "unit": "NO.", "mfn_rate": 2.5, "chapter": "87", "heading": "8703"},
    {"code": "8704.21.0000", "description": "Motor vehicles for transport of goods, diesel, GVW not exceeding 5 tonnes", "unit": "NO.", "mfn_rate": 25, "chapter": "87", "heading": "8704"},
    {"code": "8708.29.5160", "description": "Parts of motor vehicles, bodies, other", "unit": "NO.", "mfn_rate": 2.5, "chapter": "87", "heading": "8708"},
    {"code": "8708.99.8180", "description": "Other parts of motor vehicles, other", "unit": "NO.", "mfn_rate": 2.5, "chapter": "87", "heading": "8708"},
    {"code": "8711.20.0080", "description": "Motorcycles, 50cc to 250cc", "unit": "NO.", "mfn_rate": 0, "chapter": "87", "heading": "8711"},

    # Chapter 90-97: Instruments & Misc
    {"code": "9001.50.0000", "description": "Spectacle lenses of materials other than glass", "unit": "NO.", "mfn_rate": 2, "chapter": "90", "heading": "9001"},
    {"code": "9013.80.9000", "description": "Other optical devices and instruments, other", "unit": "NO.", "mfn_rate": 3.5, "chapter": "90", "heading": "9013"},
    {"code": "9018.90.8000", "description": "Medical instruments and appliances, other", "unit": "NO.", "mfn_rate": 0, "chapter": "90", "heading": "9018"},
    {"code": "9401.71.0010", "description": "Seats, upholstered, with metal frames", "unit": "NO.", "mfn_rate": 0, "chapter": "94", "heading": "9401"},
    {"code": "9403.20.0018", "description": "Metal furniture, desks", "unit": "NO.", "mfn_rate": 0, "chapter": "94", "heading": "9403"},
    {"code": "9403.60.8081", "description": "Wooden furniture, other", "unit": "NO.", "mfn_rate": 0, "chapter": "94", "heading": "9403"},
    {"code": "9503.00.0073", "description": "Toys, building blocks and similar construction toys", "unit": "NO.", "mfn_rate": 0, "chapter": "95", "heading": "9503"},
    {"code": "9504.50.0000", "description": "Video game consoles and machines", "unit": "NO.", "mfn_rate": 0, "chapter": "95", "heading": "9504"},
    {"code": "9506.91.0030", "description": "Fitness equipment, exercise machines", "unit": "NO.", "mfn_rate": 4.6, "chapter": "95", "heading": "9506"},
]

# Sample FTA Agreements
SAMPLE_FTAS = [
    {
        "code": "USMCA",
        "name": "United States-Mexico-Canada Agreement",
        "full_name": "Agreement between the United States of America, the United Mexican States, and Canada",
        "member_countries": ["US", "CA", "MX"],
        "certificate_types": ["USMCA Certificate of Origin"],
        "cumulation_type": "full",
        "de_minimis_threshold": 10.0,
        "effective_from": "2020-07-01"
    },
    {
        "code": "RCEP",
        "name": "Regional Comprehensive Economic Partnership",
        "full_name": "Regional Comprehensive Economic Partnership Agreement",
        "member_countries": ["AU", "BN", "KH", "CN", "ID", "JP", "KR", "LA", "MY", "MM", "NZ", "PH", "SG", "TH", "VN"],
        "certificate_types": ["RCEP Certificate of Origin", "Form D"],
        "cumulation_type": "diagonal",
        "de_minimis_threshold": 10.0,
        "effective_from": "2022-01-01"
    },
    {
        "code": "CPTPP",
        "name": "Comprehensive and Progressive TPP",
        "full_name": "Comprehensive and Progressive Agreement for Trans-Pacific Partnership",
        "member_countries": ["AU", "BN", "CA", "CL", "JP", "MY", "MX", "NZ", "PE", "SG", "VN"],
        "certificate_types": ["CPTPP Certificate of Origin"],
        "cumulation_type": "full",
        "de_minimis_threshold": 10.0,
        "effective_from": "2018-12-30"
    },
    {
        "code": "GSP",
        "name": "Generalized System of Preferences",
        "full_name": "US Generalized System of Preferences",
        "member_countries": ["BD", "KH", "ET", "NP", "PK", "LK", "TZ", "UG"],
        "certificate_types": ["GSP Form A"],
        "cumulation_type": "bilateral",
        "de_minimis_threshold": 35.0,
        "effective_from": "1976-01-01"
    },
    {
        "code": "KORUS",
        "name": "US-Korea Free Trade Agreement",
        "full_name": "United States-Korea Free Trade Agreement",
        "member_countries": ["US", "KR"],
        "certificate_types": ["KORUS Certificate of Origin"],
        "cumulation_type": "bilateral",
        "de_minimis_threshold": 10.0,
        "effective_from": "2012-03-15"
    },
]

# Sample Chapter Notes for key chapters
SAMPLE_CHAPTER_NOTES = [
    {"chapter": "61", "note_type": "chapter_note", "note_number": 1, "note_text": "This Chapter applies only to made-up knitted or crocheted articles. Garments made up of knitted or crocheted fabric and cut and sewn from knitted or crocheted fabric are classified in chapter 61."},
    {"chapter": "61", "note_type": "chapter_note", "note_number": 2, "note_text": "This Chapter does not cover: (a) Goods of heading 62.12; (b) Worn clothing or other worn articles of heading 63.09; or (c) Orthopedic appliances, surgical belts, trusses or the like (heading 90.21)."},
    {"chapter": "62", "note_type": "chapter_note", "note_number": 1, "note_text": "This Chapter applies only to made-up articles of any textile fabric other than wadding, excluding knitted or crocheted articles (other than those of heading 62.12)."},
    {"chapter": "84", "note_type": "chapter_note", "note_number": 1, "note_text": "This Chapter does not cover: (a) Millstones, grindstones or other articles of Chapter 68; (b) Machinery or appliances (for example, pumps) of ceramic material and ceramic parts (Chapter 69)."},
    {"chapter": "84", "note_type": "chapter_note", "note_number": 2, "note_text": "Subject to the operation of Note 3 to Section XVI and subject to Note 9 to this Chapter, a machine or appliance which answers to a description in one or more of the headings 84.01 to 84.24..."},
    {"chapter": "85", "note_type": "chapter_note", "note_number": 1, "note_text": "This Chapter does not cover: (a) Electrically warmed blankets, bed pads, foot-muffs or the like; electrically warmed clothing, footwear or ear pads or other electrically warmed articles worn on or about the person (Section XI)."},
    {"chapter": "87", "note_type": "chapter_note", "note_number": 1, "note_text": "This Chapter does not cover railway or tramway rolling-stock designed solely for running on rails."},
    {"chapter": "87", "note_type": "chapter_note", "note_number": 2, "note_text": "For the purposes of this Chapter, 'tractors' means vehicles constructed essentially for hauling or pushing another vehicle, appliance or load."},
]

# Sample Section 301 rates (US-China tariffs)
SAMPLE_301_RATES = [
    {"hs_code": "8471.30.0100", "list_number": "List 1", "rate": 25.0, "origin": "CN"},  # Laptops
    {"hs_code": "8542.31.0000", "list_number": "List 1", "rate": 25.0, "origin": "CN"},  # Processors
    {"hs_code": "9403.60.8081", "list_number": "List 3", "rate": 25.0, "origin": "CN"},  # Furniture
    {"hs_code": "6109.10.0004", "list_number": "List 4A", "rate": 7.5, "origin": "CN"},  # T-shirts
    {"hs_code": "6203.42.4020", "list_number": "List 4A", "rate": 7.5, "origin": "CN"},  # Jeans
    {"hs_code": "8507.60.0010", "list_number": "List 3", "rate": 25.0, "origin": "CN"},  # Lithium batteries
]


def import_sample_data(db: Session):
    """Import sample HTS data for testing."""
    logger.info("Starting sample HTS data import...")
    
    # Import HTS codes
    for item in SAMPLE_HTS_DATA:
        code = item["code"]
        existing = db.query(HSCodeTariff).filter(HSCodeTariff.code == code).first()
        if existing:
            continue
        
        # Parse code hierarchy
        code_clean = code.replace(".", "")
        
        tariff = HSCodeTariff(
            id=uuid.uuid4(),
            code=code,
            code_2=code_clean[:2],
            code_4=code_clean[:4],
            code_6=code_clean[:6] if len(code_clean) >= 6 else None,
            code_8=code_clean[:8] if len(code_clean) >= 8 else None,
            code_10=code_clean[:10] if len(code_clean) >= 10 else None,
            description=item["description"],
            country_code="US",
            schedule_type="HTS",
            unit_of_quantity=item.get("unit"),
            is_active=True,
        )
        db.add(tariff)
        
        # Add MFN duty rate
        if item.get("mfn_rate") is not None:
            duty = DutyRate(
                id=uuid.uuid4(),
                hs_code_id=tariff.id,
                rate_type="mfn",
                rate_code="MFN",
                ad_valorem_rate=item["mfn_rate"],
                is_active=True,
            )
            db.add(duty)
    
    db.commit()
    logger.info(f"Imported {len(SAMPLE_HTS_DATA)} HTS codes")
    
    # Import FTA agreements
    for fta_data in SAMPLE_FTAS:
        existing = db.query(FTAAgreement).filter(FTAAgreement.code == fta_data["code"]).first()
        if existing:
            continue
        
        fta = FTAAgreement(
            id=uuid.uuid4(),
            code=fta_data["code"],
            name=fta_data["name"],
            full_name=fta_data["full_name"],
            member_countries=fta_data["member_countries"],
            certificate_types=fta_data["certificate_types"],
            cumulation_type=fta_data["cumulation_type"],
            de_minimis_threshold=fta_data["de_minimis_threshold"],
            effective_from=datetime.fromisoformat(fta_data["effective_from"]),
            is_active=True,
        )
        db.add(fta)
    
    db.commit()
    logger.info(f"Imported {len(SAMPLE_FTAS)} FTA agreements")
    
    # Import chapter notes
    for note_data in SAMPLE_CHAPTER_NOTES:
        existing = db.query(ChapterNote).filter(
            ChapterNote.chapter == note_data["chapter"],
            ChapterNote.note_type == note_data["note_type"],
            ChapterNote.note_number == note_data["note_number"]
        ).first()
        if existing:
            continue
        
        note = ChapterNote(
            id=uuid.uuid4(),
            chapter=note_data["chapter"],
            note_type=note_data["note_type"],
            note_number=note_data["note_number"],
            note_text=note_data["note_text"],
            country_code="US",
            is_active=True,
        )
        db.add(note)
    
    db.commit()
    logger.info(f"Imported {len(SAMPLE_CHAPTER_NOTES)} chapter notes")
    
    # Import Section 301 rates
    for rate_data in SAMPLE_301_RATES:
        existing = db.query(Section301Rate).filter(
            Section301Rate.hs_code == rate_data["hs_code"],
            Section301Rate.origin_country == rate_data["origin"]
        ).first()
        if existing:
            continue
        
        rate = Section301Rate(
            id=uuid.uuid4(),
            hs_code=rate_data["hs_code"],
            origin_country=rate_data["origin"],
            list_number=rate_data["list_number"],
            additional_rate=rate_data["rate"],
            is_active=True,
        )
        db.add(rate)
    
    db.commit()
    logger.info(f"Imported {len(SAMPLE_301_RATES)} Section 301 rates")
    
    logger.info("Sample data import complete!")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Import HTS data")
    parser.add_argument("--sample", action="store_true", help="Import sample data")
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.sample:
            import_sample_data(db)
        else:
            logger.info("No import mode specified. Use --sample for sample data.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

