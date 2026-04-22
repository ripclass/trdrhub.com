"""
Trade-corridor configurations.

Each corridor describes a realistic applicant/beneficiary pair plus the
ecosystem around them: issuing/advising banks, port pairs, currency,
typical Incoterm, local tax-identifier regime, sanctions block, and
language/regulatory peculiarities. All rendering pulls from these dicts —
there's no jurisdiction-specific code path anywhere else.

When adding a new corridor, copy an existing entry and swap every
field. Don't reuse identifiers across corridors (defeats the point of
the fixture).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict


def _future(days: int, base: date | None = None) -> str:
    """ISO date `days` ahead of today (or `base`)."""
    b = base or date.today()
    return (b + timedelta(days=days)).isoformat()


def _mt700_date(iso: str) -> str:
    """Convert YYYY-MM-DD to the MT700 YYMMDD form used in 31C/31D/44C."""
    y, m, d = iso.split("-")
    return f"{y[2:]}{m}{d}"


CORRIDORS: Dict[str, Dict[str, Any]] = {
    # -----------------------------------------------------------------
    # US importer ← Vietnam supplier
    # Apparel and furniture corridor; US EIN on tax-ID side; USD all the
    # way; Incoterm FOB (importer arranges freight through its freight
    # forwarder); JPMorgan Chase NY issuing, Vietcombank advising.
    # -----------------------------------------------------------------
    "US-VN": {
        "lc_number": "CHASE2026USVN019",
        "issue_date": _future(0),
        "expiry_date": _future(90),
        "expiry_place": "VIETNAM",
        "latest_shipment_date": _future(60),
        "applicable_rules": "UCP LATEST VERSION",
        "currency": "USD",
        "amount": "412,500.00",
        "incoterm": "FOB HAI PHONG (INCOTERMS 2020)",
        "partial_shipments": "NOT ALLOWED",
        "transhipment": "NOT ALLOWED",
        "port_loading": "HAI PHONG PORT, VIETNAM",
        "port_discharge": "LONG BEACH, CALIFORNIA, USA",
        "final_destination": "JPMC BONDED WAREHOUSE, LOS ANGELES, CA 90021, USA",
        "applicant_name": "MERIDIAN HOME GOODS LLC",
        "applicant_address": "4120 WEST ADAMS BLVD, LOS ANGELES, CA 90018, USA",
        "applicant_tax_ids": [
            ("EIN", "84-3921075"),
            ("DUNS", "123456789"),
            ("Importer of Record", "IOR-MHG-2026"),
        ],
        "beneficiary_name": "HAI LONG FURNITURE EXPORT CO., LTD.",
        "beneficiary_address": "LOT 12, NGUYEN KIM INDUSTRIAL PARK, HAI PHONG, VIETNAM",
        "beneficiary_account_hint": "/1002876543291",
        "issuing_bank_bic": "CHASUS33XXX",
        "issuing_bank_name": "JPMORGAN CHASE BANK N.A.",
        "issuing_bank_address": "383 MADISON AVENUE, NEW YORK, NY 10179, USA",
        "advising_bank_bic": "BFTVVNVX",
        "advising_bank_name": "VIETCOMBANK",
        "advise_through_bic": "BFTVVNVXHPG",
        "drawee_bic": "CHASUS33XXX",
        "available_with": "ANY BANK IN VIETNAM BY NEGOTIATION",
        "goods_description": (
            "SOLID ACACIA WOOD DINING FURNITURE COLLECTION INCLUDING "
            "DINING TABLES 900 UNITS AT USD 285.00 PER UNIT AND MATCHING "
            "SIDE CHAIRS 3,600 UNITS AT USD 43.75 PER UNIT. TOTAL "
            "QUANTITY 4,500 UNITS. HS CODES 94036000 AND 94018100. "
            "SHIPPING MARKS: MERIDIAN HOME GOODS, LOS ANGELES, PO "
            "MHG-2026-0114. AS PER PROFORMA INVOICE NO. HLF-US-0114 "
            "DATED 2026-04-01 OF BENEFICIARY."
        ),
        "documents_required": [
            "(1) SIGNED COMMERCIAL INVOICE IN 4 COPIES INDICATING HS CODE, QUANTITY, UNIT PRICE, LINE TOTALS AND INVOICE GRAND TOTAL.",
            "(2) FULL SET 3/3 ORIGINAL CLEAN ON BOARD OCEAN BILL OF LADING MADE OUT TO ORDER OF JPMORGAN CHASE BANK N.A. MARKED \"FREIGHT COLLECT\", NOTIFY APPLICANT AND ALSO NOTIFY JPMORGAN CHASE BANK N.A. TRADE SERVICES. B/L TO SHOW VESSEL NAME, VOYAGE, CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT.",
            "(3) DETAILED PACKING LIST IN 4 COPIES SHOWING CARTON-WISE BREAKDOWN, DIMENSIONS, G.W., N.W., NUMBER OF PACKAGES.",
            "(4) CERTIFICATE OF ORIGIN FORM B ISSUED BY THE VIETNAM CHAMBER OF COMMERCE AND INDUSTRY (VCCI).",
            "(5) FUMIGATION CERTIFICATE / ISPM 15 CERTIFICATE FOR WOODEN PACKAGING.",
            "(6) BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW, KILN-DRIED, AND MANUFACTURED IN 2026.",
            "(7) COPIES OF ALL DOCUMENTS ABOVE MUST BE DISPATCHED TO APPLICANT WITHIN 3 DAYS AFTER SHIPMENT BY COURIER OR EMAIL.",
            "(8) ALL DOCUMENTS MUST BEAR LC NO. CHASE2026USVN019 AND BUYER PURCHASE ORDER NO. MHG-2026-0114.",
        ],
        "additional_conditions": [
            "(1) DOCUMENTS MUST NOT BE DATED EARLIER THAN THE LC ISSUE DATE.",
            "(2) SHORT FORM, BLANK BACK, CLAUSED, OR STALE BILL OF LADING NOT ACCEPTABLE.",
            "(3) THIRD-PARTY DOCUMENTS ACCEPTABLE EXCEPT BILL OF EXCHANGE AND COMMERCIAL INVOICE.",
            "(4) APPLICANT'S EIN 84-3921075 AND PURCHASE ORDER NO. MHG-2026-0114 MUST BE PRINTED ON ALL SHIPPING DOCUMENTS.",
            "(5) COUNTRY OF ORIGIN (VIETNAM) MUST BE INDELIBLY MARKED ON EACH CARTON.",
            "(6) ALL DOCUMENTS MUST BE IN THE ENGLISH LANGUAGE.",
            "(7) INSURANCE COVERED BY APPLICANT; BENEFICIARY TO NOTIFY APPLICANT WITHIN 5 WORKING DAYS AFTER SHIPMENT.",
            "(8) DISCREPANCY FEE USD 85 WILL BE DEDUCTED FROM BILL VALUE FOR EACH DISCREPANT PRESENTATION.",
            "(9) ALL PARTIES TO THIS TRANSACTION ARE ADVISED THAT THE ISSUING BANK MAY BE UNABLE TO PROCESS A TRANSACTION THAT INVOLVES COUNTRIES, ENTITIES, VESSELS, OR INDIVIDUALS SANCTIONED BY OFAC, UN, EU, OR UK.",
            "(10) INCOTERM FOB HAI PHONG (INCOTERMS 2020).",
            "(11) +/- 5% TOLERANCE IN QUANTITY AND VALUE IS ACCEPTABLE.",
        ],
        "charges_clause": "ALL BANKING CHARGES OUTSIDE USA ARE ON BENEFICIARY'S ACCOUNT.",
        "presentation_period_days": 15,
        "confirmation": "WITHOUT",
        "instructions_78": (
            "UPON RECEIPT OF DOCUMENTS STRICTLY COMPLYING WITH CREDIT TERMS WE SHALL ARRANGE "
            "REMITTANCE TO YOUR DESIGNATED BANK. DOCUMENTS TO BE FORWARDED TO JPMORGAN CHASE "
            "TRADE SERVICES, 383 MADISON AVENUE, NEW YORK, NY 10179, USA, BY COURIER WITHIN "
            "5 BUSINESS DAYS AFTER NEGOTIATION."
        ),
        "sender_bic": "CHASUS33133",
        "receiver_bic": "BFTVVNVXHPG",
        # Document bundle specifics
        "goods_line_items": [
            {"description": "Solid Acacia Dining Table (seat 6)", "hs": "94036000", "qty": 900, "unit": "PCS", "unit_price": "285.00"},
            {"description": "Solid Acacia Side Chair (matching)", "hs": "94018100", "qty": 3600, "unit": "PCS", "unit_price": "43.75"},
        ],
        "invoice_number": "HLF-INV-2026-0114",
        "proforma_reference": "HLF-US-0114",
        "vessel_name": "MSC BRUNELLA",
        "voyage_number": "FE2612W",
        "bl_number": "COSU6241905103",
        "container_numbers": ["MSKU8412073", "BMOU5601882"],
        "seal_numbers": ["VN8821604", "VN8821605"],
        "origin_country": "VIETNAM",
        "chamber_of_commerce": "VIETNAM CHAMBER OF COMMERCE AND INDUSTRY (VCCI)",
        "insurance_cover_mode": "BY APPLICANT",
        "inspection_body": "SGS VIETNAM LIMITED",
        "language": "English",
    },

    # -----------------------------------------------------------------
    # UK importer ← India supplier
    # Textile corridor; GBP; Incoterm CIF (seller arranges insurance
    # because the letter is UK-bound); HSBC UK issuing, SBI advising.
    # -----------------------------------------------------------------
    "UK-IN": {
        "lc_number": "HSBCUK2026INGB044",
        "issue_date": _future(0),
        "expiry_date": _future(85),
        "expiry_place": "UNITED KINGDOM",
        "latest_shipment_date": _future(55),
        "applicable_rules": "UCP 600",
        "currency": "GBP",
        "amount": "287,450.00",
        "incoterm": "CIF FELIXSTOWE (INCOTERMS 2020)",
        "partial_shipments": "ALLOWED",
        "transhipment": "ALLOWED",
        "port_loading": "MUNDRA PORT, INDIA",
        "port_discharge": "FELIXSTOWE, UNITED KINGDOM",
        "final_destination": "HSBC BONDED WAREHOUSE FACILITY, CAMBRIDGE, CB4 0WS, UNITED KINGDOM",
        "applicant_name": "HARROW & HEATH TEXTILES LTD.",
        "applicant_address": "17 BLENHEIM PARK ROAD, LONDON WC2A 3DJ, UNITED KINGDOM",
        "applicant_tax_ids": [
            ("VAT", "GB 418 7732 21"),
            ("EORI", "GB418773221000"),
            ("Company Number", "09287451"),
        ],
        "beneficiary_name": "JAIPUR COTTON MILLS PRIVATE LIMITED",
        "beneficiary_address": "PLOT 17, MALVIYA INDUSTRIAL ESTATE, JAIPUR, RAJASTHAN 302017, INDIA",
        "beneficiary_account_hint": "/0409381120022",
        "issuing_bank_bic": "MIDLGB22XXX",
        "issuing_bank_name": "HSBC UK BANK PLC",
        "issuing_bank_address": "1 CENTENARY SQUARE, BIRMINGHAM B1 1HQ, UNITED KINGDOM",
        "advising_bank_bic": "SBININBB104",
        "advising_bank_name": "STATE BANK OF INDIA",
        "advise_through_bic": "SBININBB104",
        "drawee_bic": "MIDLGB22XXX",
        "available_with": "ANY BANK IN INDIA BY NEGOTIATION",
        "goods_description": (
            "PREMIUM COTTON APPAREL SHIPMENT INCLUDING MEN'S COTTON "
            "POLO SHIRTS 18,500 PCS AT GBP 7.85 PER PC AND WOMEN'S "
            "COTTON BLOUSES 12,400 PCS AT GBP 11.90 PER PC. TOTAL "
            "QUANTITY 30,900 PCS. HS CODES 61051000 AND 62063000. "
            "SHIPPING MARKS: HARROW & HEATH, LONDON, PO HH-2026-0207. "
            "AS PER PROFORMA INVOICE NO. JCM-UK-0207 DATED 2026-03-28 "
            "OF BENEFICIARY. INCOTERM CIF FELIXSTOWE (INCOTERMS 2020)."
        ),
        "documents_required": [
            "(1) MANUALLY SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS AND 3 COPIES INDICATING HS CODE, QUANTITY, UNIT PRICE, LINE TOTALS, AND GRAND TOTAL IN GBP.",
            "(2) FULL SET 3/3 ORIGINAL CLEAN ON BOARD OCEAN BILL OF LADING MADE OUT TO ORDER OF HSBC UK BANK PLC, MARKED \"FREIGHT PREPAID\", NOTIFY APPLICANT.",
            "(3) INSURANCE POLICY OR CERTIFICATE ENDORSED IN BLANK FOR 110 PERCENT OF CIF INVOICE VALUE COVERING INSTITUTE CARGO CLAUSES (A), INSTITUTE WAR CLAUSES (CARGO), AND INSTITUTE STRIKES CLAUSES (CARGO).",
            "(4) PACKING LIST IN 3 COPIES SHOWING CARTON-WISE BREAKDOWN, DIMENSIONS, GROSS AND NET WEIGHT.",
            "(5) CERTIFICATE OF ORIGIN ISSUED BY A RECOGNISED INDIAN CHAMBER OF COMMERCE INDICATING COUNTRY OF ORIGIN: INDIA.",
            "(6) GSP FORM A DECLARATION IF APPLICABLE.",
            "(7) BENEFICIARY CERTIFICATE CONFIRMING COTTON CONTENT IS MIN. 95 PERCENT AND COMPLIES WITH REACH AND CPSIA.",
            "(8) NON-NEGOTIABLE COPIES OF ALL DOCUMENTS MUST BE EMAILED TO APPLICANT WITHIN 3 CALENDAR DAYS AFTER SHIPMENT.",
            "(9) ALL DOCUMENTS MUST QUOTE LC NO. HSBCUK2026INGB044 AND APPLICANT PURCHASE ORDER NO. HH-2026-0207.",
        ],
        "additional_conditions": [
            "(1) DOCUMENTS DATED PRIOR TO LC ISSUE DATE ARE NOT ACCEPTABLE.",
            "(2) APPLICANT'S VAT REGISTRATION GB 418 7732 21 AND EORI GB418773221000 MUST APPEAR ON ALL DOCUMENTS.",
            "(3) CERTIFICATE OF ORIGIN AND COMMERCIAL INVOICE MUST STATE COUNTRY OF ORIGIN: INDIA.",
            "(4) DOCUMENTS MUST BE IN ENGLISH.",
            "(5) ALL BANKING AND REIMBURSEMENT CHARGES OUTSIDE UNITED KINGDOM ARE ON BENEFICIARY'S ACCOUNT.",
            "(6) DISCREPANCY FEE GBP 65 WILL BE DEDUCTED PER DISCREPANT PRESENTATION.",
            "(7) ALL PARTIES ARE ADVISED THAT THE ISSUING BANK MAY BE UNABLE TO PROCESS A TRANSACTION INVOLVING COUNTRIES, ENTITIES, OR INDIVIDUALS SANCTIONED BY THE UNITED NATIONS, EUROPEAN UNION, UNITED KINGDOM (OFSI), OR UNITED STATES (OFAC).",
            "(8) INCOTERM CIF FELIXSTOWE (INCOTERMS 2020).",
            "(9) +/- 10% TOLERANCE IN QUANTITY AND VALUE IS ACCEPTABLE.",
        ],
        "charges_clause": "ALL BANK CHARGES OUTSIDE UNITED KINGDOM INCLUDING REIMBURSEMENT BANK'S CHARGES ARE ON BENEFICIARY'S ACCOUNT.",
        "presentation_period_days": 21,
        "confirmation": "WITHOUT",
        "instructions_78": (
            "UPON RECEIPT OF DOCUMENTS STRICTLY COMPLYING WITH CREDIT TERMS WE SHALL REMIT "
            "FUNDS TO YOUR NOSTRO ACCOUNT IN ACCORDANCE WITH YOUR INSTRUCTIONS. DOCUMENTS "
            "TO BE FORWARDED TO HSBC UK TRADE FINANCE OPERATIONS, 1 CENTENARY SQUARE, "
            "BIRMINGHAM B1 1HQ, BY COURIER TO OFFICE PREMISES ONLY."
        ),
        "sender_bic": "MIDLGB22104",
        "receiver_bic": "SBININBB104",
        "goods_line_items": [
            {"description": "Men's Cotton Polo Shirts", "hs": "61051000", "qty": 18500, "unit": "PCS", "unit_price": "7.85"},
            {"description": "Women's Cotton Blouses", "hs": "62063000", "qty": 12400, "unit": "PCS", "unit_price": "11.90"},
        ],
        "invoice_number": "JCM-INV-2026-0207",
        "proforma_reference": "JCM-UK-0207",
        "vessel_name": "CMA CGM MARCO POLO",
        "voyage_number": "FAL8W026",
        "bl_number": "CMAU2026INGB044",
        "container_numbers": ["CMAU7392041"],
        "seal_numbers": ["IN0207441"],
        "origin_country": "INDIA",
        "chamber_of_commerce": "FEDERATION OF INDIAN EXPORT ORGANISATIONS (FIEO)",
        "insurance_cover_mode": "BY BENEFICIARY (CIF)",
        "inspection_body": "BUREAU VERITAS INDIA PRIVATE LIMITED",
        "language": "English",
    },

    # -----------------------------------------------------------------
    # Germany importer ← China supplier
    # Industrial-goods corridor; EUR; Incoterm FCA; Deutsche Bank
    # issuing, BOC Shanghai advising; USt-IdNr on tax side.
    # -----------------------------------------------------------------
    "DE-CN": {
        "lc_number": "DBFR2026DECN081",
        "issue_date": _future(0),
        "expiry_date": _future(95),
        "expiry_place": "GERMANY",
        "latest_shipment_date": _future(65),
        "applicable_rules": "UCP LATEST VERSION",
        "currency": "EUR",
        "amount": "548,700.00",
        "incoterm": "FCA SHANGHAI (INCOTERMS 2020)",
        "partial_shipments": "NOT ALLOWED",
        "transhipment": "ALLOWED",
        "port_loading": "SHANGHAI PORT, CHINA",
        "port_discharge": "HAMBURG, GERMANY",
        "final_destination": "DEUTSCHE BANK BONDED CENTRE, OSNABRUECK, 49084, GERMANY",
        "applicant_name": "KALTENBERG MASCHINENBAU GMBH",
        "applicant_address": "INDUSTRIESTRASSE 44, 49084 OSNABRUECK, GERMANY",
        "applicant_tax_ids": [
            ("USt-IdNr", "DE249871503"),
            ("EORI", "DE249871503000"),
            ("Handelsregister", "HRB 28871 Osnabrueck"),
        ],
        "beneficiary_name": "SHANGHAI HAIRUI PRECISION MACHINERY CO., LTD.",
        "beneficiary_address": "NO. 188 XINZHUANG INDUSTRIAL ZONE, MINHANG DISTRICT, SHANGHAI 201108, PEOPLE'S REPUBLIC OF CHINA",
        "beneficiary_account_hint": "/621700019210008172",
        "issuing_bank_bic": "DEUTDEFF",
        "issuing_bank_name": "DEUTSCHE BANK AG",
        "issuing_bank_address": "TAUNUSANLAGE 12, 60325 FRANKFURT AM MAIN, GERMANY",
        "advising_bank_bic": "BKCHCNBJ300",
        "advising_bank_name": "BANK OF CHINA, SHANGHAI BRANCH",
        "advise_through_bic": "BKCHCNBJ300",
        "drawee_bic": "DEUTDEFF",
        "available_with": "ANY BANK IN CHINA BY NEGOTIATION",
        "goods_description": (
            "INDUSTRIAL CNC MACHINING CENTRES 4 UNITS AT EUR 119,800 "
            "PER UNIT AND HIGH-PRECISION TOOLING KITS 28 UNITS AT "
            "EUR 2,525 PER UNIT. TOTAL 32 UNITS. HS CODES 84571010 "
            "AND 82079030. SHIPPING MARKS: KALTENBERG, OSNABRUECK, "
            "PO KM-2026-0318. AS PER PROFORMA INVOICE NO. SHPM-DE-"
            "0318 DATED 2026-03-15 OF BENEFICIARY. INCOTERM FCA "
            "SHANGHAI (INCOTERMS 2020)."
        ),
        "documents_required": [
            "(1) SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS AND 3 COPIES INDICATING CN CODE, QUANTITY, UNIT PRICE IN EUR, LINE TOTALS AND GRAND TOTAL.",
            "(2) FULL SET 3/3 ORIGINAL CLEAN ON BOARD OCEAN BILL OF LADING MADE OUT TO ORDER OF DEUTSCHE BANK AG MARKED \"FREIGHT COLLECT\", NOTIFY APPLICANT. B/L MUST INDICATE VESSEL, VOYAGE, CONTAINER AND SEAL NUMBERS.",
            "(3) DETAILED PACKING LIST IN 3 COPIES SHOWING CARTON AND CRATE BREAKDOWN WITH G.W. AND N.W.",
            "(4) CERTIFICATE OF ORIGIN ISSUED BY CHINA COUNCIL FOR THE PROMOTION OF INTERNATIONAL TRADE (CCPIT) STATING COUNTRY OF ORIGIN: CHINA.",
            "(5) CE CONFORMITY DECLARATION FOR MACHINERY DIRECTIVE 2006/42/EC.",
            "(6) FACTORY INSPECTION CERTIFICATE ISSUED BY TUV RHEINLAND OR SGS CERTIFYING QUANTITY, QUALITY AND WORKMANSHIP.",
            "(7) BENEFICIARY CERTIFICATE CONFIRMING MACHINERY IS BRAND NEW, YEAR OF MANUFACTURE 2026.",
            "(8) NON-NEGOTIABLE COPIES OF ALL DOCUMENTS TO BE DISPATCHED TO APPLICANT BY EMAIL WITHIN 3 CALENDAR DAYS OF SHIPMENT.",
            "(9) ALL DOCUMENTS MUST QUOTE LC NO. DBFR2026DECN081 AND APPLICANT PURCHASE ORDER NO. KM-2026-0318.",
        ],
        "additional_conditions": [
            "(1) DOCUMENTS DATED PRIOR TO LC ISSUE DATE NOT ACCEPTABLE.",
            "(2) APPLICANT'S USt-IdNr DE249871503 AND EORI DE249871503000 MUST APPEAR ON ALL DOCUMENTS.",
            "(3) CERTIFICATE OF ORIGIN AND INVOICE MUST STATE COUNTRY OF ORIGIN: CHINA.",
            "(4) DOCUMENTS MUST BE IN ENGLISH OR GERMAN.",
            "(5) INSURANCE COVERED BY APPLICANT UNDER GERMAN MARINE INSURANCE; BENEFICIARY TO ADVISE APPLICANT WITHIN 7 CALENDAR DAYS AFTER SHIPMENT.",
            "(6) DISCREPANCY FEE EUR 95 PER DISCREPANT PRESENTATION.",
            "(7) ALL PARTIES ARE ADVISED THAT THE ISSUING BANK MAY BE UNABLE TO PROCESS A TRANSACTION INVOLVING COUNTRIES, ENTITIES, OR INDIVIDUALS SANCTIONED BY THE EUROPEAN UNION, GERMANY, UNITED NATIONS, OR UNITED STATES (OFAC).",
            "(8) INCOTERM FCA SHANGHAI (INCOTERMS 2020).",
            "(9) +/- 2% TOLERANCE IN QUANTITY AND VALUE IS ACCEPTABLE.",
        ],
        "charges_clause": "ALL BANKING CHARGES OUTSIDE GERMANY ARE ON BENEFICIARY'S ACCOUNT.",
        "presentation_period_days": 21,
        "confirmation": "MAY ADD",
        "instructions_78": (
            "UPON RECEIPT OF DOCUMENTS COMPLYING WITH CREDIT TERMS WE WILL REMIT FUNDS TO "
            "YOUR NOSTRO ACCOUNT. DOCUMENTS TO BE FORWARDED TO DEUTSCHE BANK AG, TRADE "
            "FINANCE OPERATIONS, TAUNUSANLAGE 12, 60325 FRANKFURT AM MAIN, BY COURIER."
        ),
        "sender_bic": "DEUTDEFFXXX",
        "receiver_bic": "BKCHCNBJ300",
        "goods_line_items": [
            {"description": "CNC Machining Centre (5-axis)", "hs": "84571010", "qty": 4, "unit": "UNIT", "unit_price": "119800.00"},
            {"description": "High-Precision Tooling Kit", "hs": "82079030", "qty": 28, "unit": "KIT", "unit_price": "2525.00"},
        ],
        "invoice_number": "SHPM-INV-2026-0318",
        "proforma_reference": "SHPM-DE-0318",
        "vessel_name": "HAMBURG EXPRESS",
        "voyage_number": "FE2608",
        "bl_number": "HAPAG2026DECN081",
        "container_numbers": ["HLXU8462190", "HLXU8462208"],
        "seal_numbers": ["CN0318902", "CN0318903"],
        "origin_country": "CHINA",
        "chamber_of_commerce": "CHINA COUNCIL FOR THE PROMOTION OF INTERNATIONAL TRADE (CCPIT)",
        "insurance_cover_mode": "BY APPLICANT",
        "inspection_body": "TUV RHEINLAND (SHANGHAI) CO., LTD.",
        "language": "English and German",
    },

    # -----------------------------------------------------------------
    # Bangladesh importer ← China supplier (validates against real
    # reference corpus at F:/New Download/LC Copies/2024-2025). Mirrors
    # the IBBL-issued real LC shape captured there. Represents one of
    # the largest real import flows in Ripon's production data.
    # -----------------------------------------------------------------
    "BD-CN": {
        "lc_number": "IBBLBDCN2026041",
        "issue_date": _future(0),
        "expiry_date": _future(85),
        "expiry_place": "CHINA",
        "latest_shipment_date": _future(60),
        "applicable_rules": "UCP LATEST VERSION",
        "currency": "USD",
        "amount": "184,250.00",
        "incoterm": "CFR CHATTOGRAM (INCOTERMS 2020)",
        "partial_shipments": "NOT ALLOWED",
        "transhipment": "ALLOWED",
        "port_loading": "ANY PORT IN CHINA",
        "port_discharge": "CHATTOGRAM, BANGLADESH",
        "final_destination": "ICD KAMALAPUR, DHAKA, BANGLADESH",
        "applicant_name": "DELTA PROCESS INDUSTRIES LIMITED",
        "applicant_address": "PLOT 29, DEPZ INDUSTRIAL AREA, SAVAR, DHAKA 1349, BANGLADESH",
        "applicant_tax_ids": [
            ("TIN", "632874951003"),
            ("BIN", "000482917-0304"),
            ("IRC", "260412987000115"),
        ],
        "beneficiary_name": "NINGBO FENGYUAN PRECISION PARTS CO., LTD.",
        "beneficiary_address": "NO. 88 FENGHUA ROAD, YINZHOU DISTRICT, NINGBO, ZHEJIANG 315100, CHINA",
        "beneficiary_account_hint": "/622848001920410016",
        "issuing_bank_bic": "IBBLBDDH137",
        "issuing_bank_name": "ISLAMI BANK BANGLADESH PLC, SAVAR BRANCH",
        "issuing_bank_address": "PLOT 47, DEPZ ROAD, SAVAR, DHAKA, BANGLADESH",
        "advising_bank_bic": "BKNBCN2N",
        "advising_bank_name": "BANK OF NINGBO",
        "advise_through_bic": "BKNBCN2NNGB",
        "drawee_bic": "IBBLBDDH137",
        "available_with": "ANY BANK IN CHINA BY NEGOTIATION",
        "goods_description": (
            "PRECISION-MACHINED INDUSTRIAL FASTENERS AND ROLLER "
            "ASSEMBLIES FOR TEXTILE MACHINERY: ROLLER BEARINGS "
            "1,800 PCS AT USD 46.25 PER PC AND HIGH-STRENGTH "
            "FASTENER SETS 6,400 SETS AT USD 15.75 PER SET. "
            "TOTAL 8,200 PCS / SETS. HS CODES 84821010 AND "
            "73181500. CFR CHATTOGRAM (INCOTERMS 2020) AS PER "
            "PROFORMA INVOICE NO. NFP-BD-0418 DATED 2026-04-04 OF "
            "BENEFICIARY."
        ),
        "documents_required": [
            "(1) BENEFICIARY'S DRAFT IN DUPLICATE DRAWN ON ISLAMI BANK BANGLADESH PLC, SAVAR BRANCH, FOR FULL INVOICE VALUE.",
            "(2) BENEFICIARY'S MANUALLY SIGNED 6 FOLD INVOICE MENTIONING GOODS VALUE AND FREIGHT SEPARATELY AND CERTIFYING GOODS ARE OF CHINA ORIGIN AGAINST H.S. CODES 84821010 AND 73181500 AND IRC NO. 260412987000115.",
            "(3) FULL SET SHIPPED ON BOARD BILL OF LADING PLUS 03 NON-NEGOTIABLE COPIES MARKED \"FREIGHT PREPAID\" DRAWN ON OR ENDORSED TO THE ORDER OF ISLAMI BANK BANGLADESH PLC, NOTIFY APPLICANT AND ISLAMI BANK BANGLADESH PLC, SAVAR BRANCH.",
            "(4) INSURANCE COVERED BY APPLICANT. BENEFICIARY TO ADVISE KARNAPHULI INSURANCE COMPANY LIMITED AND APPLICANT BY EMAIL WITHIN 10 WORKING DAYS AFTER SHIPMENT.",
            "(5) CERTIFICATE OF ORIGIN IN DUPLICATE ISSUED BY CCPIT.",
            "(6) DETAILED PACKING LIST IN 6 FOLD DULY SIGNED BY THE BENEFICIARY.",
            "(7) ONE SET OF NON-NEGOTIABLE DOCUMENTS MUST BE DISPATCHED TO APPLICANT BY COURIER OR EMAIL WITHIN 05 DAYS AFTER SHIPMENT.",
            "(8) COUNTRY OF ORIGIN MUST BE MENTIONED CLEARLY ON PACKAGES OF GOODS.",
            "(9) APPLICANT'S NAME, ADDRESS, TIN 632874951003 AND BIN 000482917-0304 MUST BE INSCRIBED IN INDELIBLE INK ON AT LEAST 2% OF THE LARGEST PACKET / CASE.",
            "(10) GOODS MUST BE NEW WITHOUT ANY MANUFACTURING DEFECT, QUANTITY AND QUALITY AS PER L/C TERMS.",
        ],
        "additional_conditions": [
            "(1) DOCUMENTS EVIDENCING SHIPMENT PRIOR TO LC DATE NOT ACCEPTABLE.",
            "(2) LC NUMBER, DATE, APPLICANT NAME AND ISSUING BANK MUST APPEAR IN ALL DOCUMENTS.",
            "(3) SHORT FORM, CLAUSED, BLANK BACK, STALE BILL OF LADING NOT ACCEPTABLE.",
            "(4) PACKING MUST BE IN STANDARD EXPORT PACKING.",
            "(5) DISCREPANCY FEE USD 75 PER PRESENTATION.",
            "(6) ALL DOCUMENTS MUST BE IN ENGLISH.",
            "(7) SHIPMENT TO BE EFFECTED ON TRANSPORT AUTHORIZED TO ENTER PORTS OF BANGLADESH.",
            "(8) APPLICANT'S BIN 000482917-0304 MUST BE MENTIONED IN ALL SHIPPING DOCUMENTS.",
            "(9) +/- 10% TOLERANCE IN QUANTITY AND VALUE IS ACCEPTABLE.",
            "(10) ALL PARTIES TO THIS TRANSACTION ARE ADVISED THAT BANKS MAY BE UNABLE TO PROCESS A TRANSACTION THAT INVOLVES COUNTRIES, REGIONS, ENTITIES, VESSELS, OR INDIVIDUALS SANCTIONED BY UN, US, EU, UK, OR ANY OTHER RELEVANT GOVERNMENT AND/OR REGULATORY AUTHORITY.",
        ],
        "charges_clause": "ALL FOREIGN BANK CHARGES INCLUDING REIMBURSEMENT BANK'S CHARGES OUTSIDE BANGLADESH ARE ON BENEFICIARY'S ACCOUNT.",
        "presentation_period_days": 21,
        "confirmation": "WITHOUT",
        "instructions_78": (
            "UPON RECEIPT OF DOCUMENTS STRICTLY COMPLYING CREDIT TERMS WE SHALL ARRANGE "
            "REMITTANCE TO YOUR DESIGNATED BANK. ON THE DATE OF NEGOTIATION NEGOTIATING "
            "BANK MUST INFORM TO ISSUING BANK REGARDING STATUS OF NEGOTIATION. DOCUMENTS "
            "TO BE FORWARDED TO ISLAMI BANK BANGLADESH PLC, SAVAR BRANCH, BY COURIER."
        ),
        "sender_bic": "IBBLBDDH137",
        "receiver_bic": "BKNBCN2NNGB",
        "goods_line_items": [
            {"description": "Roller Bearings for Textile Machinery", "hs": "84821010", "qty": 1800, "unit": "PCS", "unit_price": "46.25"},
            {"description": "High-Strength Fastener Set", "hs": "73181500", "qty": 6400, "unit": "SET", "unit_price": "15.75"},
        ],
        "invoice_number": "NFP-INV-2026-0418",
        "proforma_reference": "NFP-BD-0418",
        "vessel_name": "MAERSK NINGBO",
        "voyage_number": "ME218W",
        "bl_number": "MAEU2026BDCN041",
        "container_numbers": ["MAEU8710244"],
        "seal_numbers": ["CN0418501"],
        "origin_country": "CHINA",
        "chamber_of_commerce": "CHINA COUNCIL FOR THE PROMOTION OF INTERNATIONAL TRADE (CCPIT)",
        "insurance_cover_mode": "BY APPLICANT",
        "inspection_body": "SGS-CSTC STANDARDS TECHNICAL SERVICES CO., LTD.",
        "language": "English",
    },
}


def corridor_keys() -> list[str]:
    return list(CORRIDORS.keys())


def get_corridor(key: str) -> Dict[str, Any]:
    if key not in CORRIDORS:
        raise KeyError(
            f"Unknown corridor {key!r}. Known: {', '.join(corridor_keys())}"
        )
    return CORRIDORS[key]
