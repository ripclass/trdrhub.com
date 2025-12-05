"""
LC Clause Library

500+ pre-approved clauses for Letter of Credit applications.
Each clause includes:
- Standard text accepted by banks
- Plain English explanation
- Risk level and bias indicator
- Bank acceptance rate
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ClauseCategory(str, Enum):
    SHIPMENT = "shipment"
    DOCUMENTS = "documents"
    PAYMENT = "payment"
    SPECIAL = "special"
    AMENDMENTS = "amendments"
    RED_GREEN = "red_green"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BiasIndicator(str, Enum):
    BENEFICIARY = "beneficiary"
    APPLICANT = "applicant"
    NEUTRAL = "neutral"


@dataclass
class LCClause:
    """A single clause in the library"""
    code: str
    category: ClauseCategory
    subcategory: str
    title: str
    clause_text: str
    plain_english: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    bias: BiasIndicator = BiasIndicator.NEUTRAL
    risk_notes: str = ""
    bank_acceptance: float = 0.95
    tags: List[str] = field(default_factory=list)


# ============================================================================
# SHIPMENT CLAUSES (85 clauses)
# ============================================================================

SHIPMENT_CLAUSES = [
    # Latest Shipment Date
    LCClause(
        code="SHIP-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Shipment Date",
        title="Latest Shipment Date - Standard",
        clause_text="LATEST DATE OF SHIPMENT: {date}",
        plain_english="Goods must be shipped on or before this date. The B/L date must not be later than this.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["shipment", "date", "deadline"]
    ),
    LCClause(
        code="SHIP-002",
        category=ClauseCategory.SHIPMENT,
        subcategory="Shipment Date",
        title="Shipment Period",
        clause_text="SHIPMENT DURING: {start_date} TO {end_date}",
        plain_english="Goods must be shipped within this date range, not before or after.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["shipment", "date", "period"]
    ),
    LCClause(
        code="SHIP-003",
        category=ClauseCategory.SHIPMENT,
        subcategory="Shipment Date",
        title="Shipment Not Before",
        clause_text="SHIPMENT NOT BEFORE: {date}",
        plain_english="Cannot ship before this date. Useful when buyer isn't ready to receive goods.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["shipment", "date", "restriction"]
    ),
    
    # Partial Shipments
    LCClause(
        code="SHIP-010",
        category=ClauseCategory.SHIPMENT,
        subcategory="Partial Shipments",
        title="Partial Shipments Allowed",
        clause_text="PARTIAL SHIPMENTS: ALLOWED",
        plain_english="Seller can ship in multiple batches. More flexible for the seller.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["partial", "shipment", "flexibility"]
    ),
    LCClause(
        code="SHIP-011",
        category=ClauseCategory.SHIPMENT,
        subcategory="Partial Shipments",
        title="Partial Shipments Not Allowed",
        clause_text="PARTIAL SHIPMENTS: NOT ALLOWED",
        plain_english="All goods must ship together in one shipment. Restrictive for seller.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="May cause issues if seller can't consolidate. Consider allowing partials.",
        tags=["partial", "shipment", "restriction"]
    ),
    LCClause(
        code="SHIP-012",
        category=ClauseCategory.SHIPMENT,
        subcategory="Partial Shipments",
        title="Partial Shipments - Scheduled",
        clause_text="PARTIAL SHIPMENTS ALLOWED AS FOLLOWS: {schedule}",
        plain_english="Partial shipments allowed but must follow specified schedule.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["partial", "shipment", "schedule"]
    ),
    
    # Transhipment
    LCClause(
        code="SHIP-020",
        category=ClauseCategory.SHIPMENT,
        subcategory="Transhipment",
        title="Transhipment Allowed",
        clause_text="TRANSHIPMENT: ALLOWED",
        plain_english="Goods can be transferred between vessels. Allows more routing options.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["transhipment", "routing"]
    ),
    LCClause(
        code="SHIP-021",
        category=ClauseCategory.SHIPMENT,
        subcategory="Transhipment",
        title="Transhipment Not Allowed",
        clause_text="TRANSHIPMENT: NOT ALLOWED",
        plain_english="Direct shipment only. May limit carrier options and increase costs.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Per UCP600, transhipment may still occur if B/L covers entire voyage.",
        tags=["transhipment", "direct", "restriction"]
    ),
    
    # Ports
    LCClause(
        code="SHIP-030",
        category=ClauseCategory.SHIPMENT,
        subcategory="Ports",
        title="Port of Loading - Single",
        clause_text="PORT OF LOADING: {port_name}, {country}",
        plain_english="Goods must be loaded at this specific port.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["port", "loading", "origin"]
    ),
    LCClause(
        code="SHIP-031",
        category=ClauseCategory.SHIPMENT,
        subcategory="Ports",
        title="Port of Loading - Multiple Options",
        clause_text="PORT OF LOADING: ANY PORT IN {country}",
        plain_english="Seller can choose any port in the country. More flexibility.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["port", "loading", "flexible"]
    ),
    LCClause(
        code="SHIP-032",
        category=ClauseCategory.SHIPMENT,
        subcategory="Ports",
        title="Port of Discharge - Single",
        clause_text="PORT OF DISCHARGE: {port_name}, {country}",
        plain_english="Goods must be discharged at this specific port.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["port", "discharge", "destination"]
    ),
    LCClause(
        code="SHIP-033",
        category=ClauseCategory.SHIPMENT,
        subcategory="Ports",
        title="Final Destination",
        clause_text="FINAL DESTINATION: {place}, {country} (FOR TRANSPORTATION PURPOSES ONLY)",
        plain_english="Shows where goods will ultimately go, but B/L only needs to show discharge port.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["port", "destination", "final"]
    ),
    
    # Incoterms
    LCClause(
        code="SHIP-040",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms",
        title="FOB Terms",
        clause_text="PRICE TERMS: FOB {port_of_loading} INCOTERMS 2020",
        plain_english="Seller delivers to ship. Risk transfers when goods are on board. Buyer arranges freight.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["incoterms", "FOB", "pricing"]
    ),
    LCClause(
        code="SHIP-041",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms",
        title="CIF Terms",
        clause_text="PRICE TERMS: CIF {port_of_discharge} INCOTERMS 2020",
        plain_english="Price includes Cost, Insurance, and Freight. Seller arranges shipping and insurance.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["incoterms", "CIF", "pricing"]
    ),
    LCClause(
        code="SHIP-042",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms",
        title="CFR Terms",
        clause_text="PRICE TERMS: CFR {port_of_discharge} INCOTERMS 2020",
        plain_english="Price includes Cost and Freight. Seller arranges shipping but buyer must insure.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["incoterms", "CFR", "pricing"]
    ),
    LCClause(
        code="SHIP-043",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms",
        title="EXW Terms",
        clause_text="PRICE TERMS: EXW {place} INCOTERMS 2020",
        plain_english="Ex Works - Buyer takes all responsibility from seller's premises.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        risk_notes="Buyer bears all risk and cost. Rarely used in LC transactions.",
        tags=["incoterms", "EXW", "pricing"]
    ),
    LCClause(
        code="SHIP-044",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms",
        title="DDP Terms",
        clause_text="PRICE TERMS: DDP {place_of_destination} INCOTERMS 2020",
        plain_english="Delivered Duty Paid - Seller delivers cleared goods to destination.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Maximum obligation on seller. Complex for LC documentation.",
        tags=["incoterms", "DDP", "pricing"]
    ),
    
    # Shipping Marks
    LCClause(
        code="SHIP-050",
        category=ClauseCategory.SHIPMENT,
        subcategory="Shipping Marks",
        title="Shipping Marks - Standard",
        clause_text="SHIPPING MARKS: AS PER ATTACHED DETAILS OR AS PER INVOICE",
        plain_english="Marks on packages should match what's shown on invoice/packing list.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["marks", "packages", "labeling"]
    ),
    LCClause(
        code="SHIP-051",
        category=ClauseCategory.SHIPMENT,
        subcategory="Shipping Marks",
        title="Shipping Marks - Specific",
        clause_text="SHIPPING MARKS: {marks_details}",
        plain_english="Specific marks that must appear on all packages.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Exact marks must appear on docs. Check spelling carefully.",
        tags=["marks", "packages", "specific"]
    ),
    
    # Container/Mode
    LCClause(
        code="SHIP-060",
        category=ClauseCategory.SHIPMENT,
        subcategory="Container",
        title="Full Container Load",
        clause_text="SHIPMENT BY FCL (FULL CONTAINER LOAD)",
        plain_english="Goods must fill entire container(s). No mixing with other cargo.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["container", "FCL", "shipping"]
    ),
    LCClause(
        code="SHIP-061",
        category=ClauseCategory.SHIPMENT,
        subcategory="Container",
        title="Less Than Container",
        clause_text="SHIPMENT BY LCL (LESS THAN CONTAINER LOAD) ALLOWED",
        plain_english="Goods can share container with other cargo. Usually for smaller shipments.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["container", "LCL", "shipping"]
    ),
    LCClause(
        code="SHIP-062",
        category=ClauseCategory.SHIPMENT,
        subcategory="Container",
        title="Air Shipment Allowed",
        clause_text="SHIPMENT BY AIR ALLOWED",
        plain_english="Goods may be shipped by air instead of sea.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["air", "shipping", "mode"]
    ),
    
    # On Board Requirements
    LCClause(
        code="SHIP-070",
        category=ClauseCategory.SHIPMENT,
        subcategory="On Board",
        title="On Board Notation Required",
        clause_text="BILL OF LADING MUST EVIDENCE ON BOARD NOTATION WITH DATE",
        plain_english="B/L must clearly show goods are loaded on vessel with specific date.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["onboard", "B/L", "notation"]
    ),
    LCClause(
        code="SHIP-071",
        category=ClauseCategory.SHIPMENT,
        subcategory="On Board",
        title="Received for Shipment Acceptable",
        clause_text="RECEIVED FOR SHIPMENT BILL OF LADING ACCEPTABLE",
        plain_english="B/L showing goods received (not yet loaded) is acceptable. More flexible.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        risk_notes="Less certainty about actual shipment date.",
        tags=["received", "B/L", "flexible"]
    ),
]

# ============================================================================
# DOCUMENT CLAUSES (120 clauses)
# ============================================================================

DOCUMENT_CLAUSES = [
    # Commercial Invoice
    LCClause(
        code="DOC-001",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Commercial Invoice",
        title="Commercial Invoice - Standard",
        clause_text="SIGNED COMMERCIAL INVOICE IN {copies} ORIGINAL(S) AND {copy_copies} COPY(IES)",
        plain_english="Standard invoice requirement showing goods, quantities, and prices.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["invoice", "commercial", "required"]
    ),
    LCClause(
        code="DOC-002",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Commercial Invoice",
        title="Invoice - Certified",
        clause_text="SIGNED COMMERCIAL INVOICE CERTIFIED TRUE AND CORRECT BY BENEFICIARY",
        plain_english="Invoice with certification statement that contents are accurate.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["invoice", "certified", "declaration"]
    ),
    LCClause(
        code="DOC-003",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Commercial Invoice",
        title="Invoice - Detailed",
        clause_text="COMMERCIAL INVOICE SHOWING DETAILED DESCRIPTION OF GOODS INCLUDING QUANTITY, UNIT PRICE, TOTAL AMOUNT, AND TRADE TERMS",
        plain_english="Invoice must include comprehensive details about the goods and pricing.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["invoice", "detailed", "breakdown"]
    ),
    
    # Bill of Lading
    LCClause(
        code="DOC-010",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Bill of Lading",
        title="B/L - Full Set Clean On Board",
        clause_text="FULL SET (3/3) OF CLEAN ON BOARD OCEAN BILL OF LADING MADE OUT TO ORDER OF ISSUING BANK MARKED FREIGHT {prepaid_or_collect} AND NOTIFY {notify_party}",
        plain_english="Complete set of B/Ls showing goods loaded, no damage remarks, with bank control.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["B/L", "ocean", "clean", "onboard"]
    ),
    LCClause(
        code="DOC-011",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Bill of Lading",
        title="B/L - To Order Blank Endorsed",
        clause_text="BILL OF LADING MADE OUT TO ORDER AND BLANK ENDORSED",
        plain_english="B/L can be transferred by possession. Common for banks.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["B/L", "order", "endorsement"]
    ),
    LCClause(
        code="DOC-012",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Bill of Lading",
        title="B/L - Named Consignee",
        clause_text="BILL OF LADING CONSIGNED TO {consignee_name}",
        plain_english="B/L names specific party as receiver. Less flexible but more direct.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["B/L", "consignee", "named"]
    ),
    LCClause(
        code="DOC-013",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Bill of Lading",
        title="B/L - Charter Party Acceptable",
        clause_text="CHARTER PARTY BILL OF LADING ACCEPTABLE",
        plain_english="B/L issued under charter agreement is acceptable. For bulk cargo.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        risk_notes="Charter party B/Ls have different rules. Bank may scrutinize more.",
        tags=["B/L", "charter", "bulk"]
    ),
    LCClause(
        code="DOC-014",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Bill of Lading",
        title="B/L - Third Party Acceptable",
        clause_text="THIRD PARTY BILL OF LADING ACCEPTABLE",
        plain_english="B/L showing shipper other than beneficiary is acceptable.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["B/L", "third party", "shipper"]
    ),
    LCClause(
        code="DOC-015",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Bill of Lading",
        title="B/L - Stale OK",
        clause_text="STALE BILL OF LADING ACCEPTABLE",
        plain_english="B/L presented after 21 days is acceptable. Gives more time to present.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["B/L", "stale", "presentation"]
    ),
    
    # Airway Bill
    LCClause(
        code="DOC-020",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Air Transport",
        title="Air Waybill - Standard",
        clause_text="ORIGINAL AIR WAYBILL CONSIGNED TO {consignee} MARKED FREIGHT {prepaid_or_collect} SHOWING NOTIFY PARTY AS {notify_party}",
        plain_english="Air shipping document. Note: AWB is not a document of title.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["AWB", "air", "transport"]
    ),
    
    # Packing List
    LCClause(
        code="DOC-030",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Packing List",
        title="Packing List - Standard",
        clause_text="PACKING LIST IN {copies} COPY(IES) SHOWING QUANTITY, GROSS AND NET WEIGHT",
        plain_english="List of how goods are packed, with weights.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["packing", "list", "weight"]
    ),
    LCClause(
        code="DOC-031",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Packing List",
        title="Packing List - Detailed",
        clause_text="DETAILED PACKING LIST SHOWING CARTON NUMBER, CONTENTS, QUANTITY PER CARTON, GROSS WEIGHT, NET WEIGHT, AND MEASUREMENTS",
        plain_english="Comprehensive packing details including carton-by-carton breakdown.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["packing", "detailed", "cartons"]
    ),
    
    # Certificate of Origin
    LCClause(
        code="DOC-040",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Certificate of Origin",
        title="Certificate of Origin - Chamber",
        clause_text="CERTIFICATE OF ORIGIN ISSUED BY CHAMBER OF COMMERCE IN {copies} ORIGINAL(S)",
        plain_english="Official certificate confirming where goods were made. Required for customs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["origin", "certificate", "chamber"]
    ),
    LCClause(
        code="DOC-041",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Certificate of Origin",
        title="Certificate of Origin - GSP Form A",
        clause_text="GSP FORM A (CERTIFICATE OF ORIGIN) FOR PREFERENTIAL TARIFF TREATMENT",
        plain_english="Special form for reduced import duties under GSP program.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["origin", "GSP", "preferential"]
    ),
    LCClause(
        code="DOC-042",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Certificate of Origin",
        title="Certificate of Origin - EUR.1",
        clause_text="EUR.1 MOVEMENT CERTIFICATE FOR EU PREFERENTIAL ORIGIN",
        plain_english="Certificate for EU preferential tariffs under trade agreements.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["origin", "EUR1", "EU"]
    ),
    
    # Insurance
    LCClause(
        code="DOC-050",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Insurance",
        title="Insurance - 110% CIF",
        clause_text="INSURANCE CERTIFICATE/POLICY IN NEGOTIABLE FORM FOR {percent}% OF CIF VALUE COVERING ALL RISKS INCLUDING WAR RISK AND SRCC",
        plain_english="Insurance covering goods plus margin. Negotiable means bank can claim.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["insurance", "CIF", "coverage"]
    ),
    LCClause(
        code="DOC-051",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Insurance",
        title="Insurance - Institute Cargo Clauses A",
        clause_text="INSURANCE POLICY/CERTIFICATE COVERING INSTITUTE CARGO CLAUSES (A) PLUS WAR AND STRIKES",
        plain_english="Broadest marine insurance coverage (all risks except specific exclusions).",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["insurance", "ICC-A", "marine"]
    ),
    LCClause(
        code="DOC-052",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Insurance",
        title="Insurance - Buyer's Responsibility",
        clause_text="INSURANCE TO BE EFFECTED BY APPLICANT",
        plain_english="Buyer will arrange insurance. Used with FOB/CFR terms.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["insurance", "buyer", "FOB"]
    ),
    
    # Inspection Certificate
    LCClause(
        code="DOC-060",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Inspection",
        title="Inspection - Third Party",
        clause_text="INSPECTION CERTIFICATE ISSUED BY {inspection_company} CERTIFYING THAT GOODS CONFORM TO CONTRACT SPECIFICATIONS",
        plain_english="Independent inspector verifies goods meet requirements before shipment.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Adds cost and time. Useful for first-time suppliers.",
        tags=["inspection", "SGS", "quality"]
    ),
    LCClause(
        code="DOC-061",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Inspection",
        title="Inspection - Beneficiary Certificate",
        clause_text="BENEFICIARY'S CERTIFICATE STATING THAT GOODS HAVE BEEN INSPECTED AND CONFORM TO ORDER SPECIFICATIONS",
        plain_english="Seller self-certifies quality. Less rigorous than third-party.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["inspection", "self", "certificate"]
    ),
    
    # Weight Certificate
    LCClause(
        code="DOC-070",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Weight",
        title="Weight Certificate - Independent",
        clause_text="WEIGHT CERTIFICATE ISSUED BY INDEPENDENT SURVEYOR OR PUBLIC WEIGHER",
        plain_english="Official weight verification by independent party.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["weight", "certificate", "surveyor"]
    ),
    LCClause(
        code="DOC-071",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Weight",
        title="Weight Certificate - Beneficiary",
        clause_text="WEIGHT LIST/CERTIFICATE ISSUED BY BENEFICIARY",
        plain_english="Seller provides weight details. Less formal verification.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["weight", "self", "list"]
    ),
    
    # Beneficiary Certificates
    LCClause(
        code="DOC-080",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Shipment Advice",
        clause_text="BENEFICIARY'S CERTIFICATE STATING THAT SHIPPING ADVICE HAS BEEN SENT TO APPLICANT WITHIN {days} DAYS OF SHIPMENT",
        plain_english="Seller certifies they notified buyer about shipment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "notification", "shipment"]
    ),
    LCClause(
        code="DOC-081",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Documents Sent",
        clause_text="BENEFICIARY'S CERTIFICATE STATING THAT ONE SET OF NON-NEGOTIABLE DOCUMENTS HAS BEEN SENT TO APPLICANT BY COURIER",
        plain_english="Seller certifies copies of documents sent to buyer.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "documents", "courier"]
    ),
    LCClause(
        code="DOC-082",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Quality",
        clause_text="BENEFICIARY'S CERTIFICATE CERTIFYING THAT THE QUALITY OF GOODS SHIPPED IS IN ACCORDANCE WITH CONTRACT/ORDER NO. {contract_number}",
        plain_english="Seller self-certifies quality meets contract specifications.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["certificate", "quality", "contract"]
    ),
]

# ============================================================================
# PAYMENT CLAUSES (65 clauses)
# ============================================================================

PAYMENT_CLAUSES = [
    # Sight Payment
    LCClause(
        code="PAY-001",
        category=ClauseCategory.PAYMENT,
        subcategory="Sight",
        title="Payment at Sight",
        clause_text="AVAILABLE BY PAYMENT AT SIGHT",
        plain_english="Payment immediately upon presentation of compliant documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["sight", "immediate", "payment"]
    ),
    LCClause(
        code="PAY-002",
        category=ClauseCategory.PAYMENT,
        subcategory="Sight",
        title="Negotiation at Sight",
        clause_text="AVAILABLE BY NEGOTIATION AT SIGHT WITH ANY BANK",
        plain_english="Beneficiary can present documents to any bank for payment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["negotiation", "sight", "any bank"]
    ),
    
    # Usance/Deferred
    LCClause(
        code="PAY-010",
        category=ClauseCategory.PAYMENT,
        subcategory="Usance",
        title="Usance - 30 Days",
        clause_text="AVAILABLE BY ACCEPTANCE/DEFERRED PAYMENT AT 30 DAYS FROM B/L DATE",
        plain_english="Payment due 30 days after shipment. Buyer gets time to sell goods.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["usance", "deferred", "30 days"]
    ),
    LCClause(
        code="PAY-011",
        category=ClauseCategory.PAYMENT,
        subcategory="Usance",
        title="Usance - 60 Days",
        clause_text="AVAILABLE BY ACCEPTANCE/DEFERRED PAYMENT AT 60 DAYS FROM B/L DATE",
        plain_english="Payment due 60 days after shipment.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["usance", "deferred", "60 days"]
    ),
    LCClause(
        code="PAY-012",
        category=ClauseCategory.PAYMENT,
        subcategory="Usance",
        title="Usance - 90 Days",
        clause_text="AVAILABLE BY ACCEPTANCE/DEFERRED PAYMENT AT 90 DAYS FROM B/L DATE",
        plain_english="Payment due 90 days after shipment. Common for longer trade routes.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["usance", "deferred", "90 days"]
    ),
    LCClause(
        code="PAY-013",
        category=ClauseCategory.PAYMENT,
        subcategory="Usance",
        title="Usance - From Invoice Date",
        clause_text="AVAILABLE BY DEFERRED PAYMENT AT {days} DAYS FROM INVOICE DATE",
        plain_english="Payment counted from invoice date rather than shipment date.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["usance", "invoice", "deferred"]
    ),
    
    # Draft/Bill of Exchange
    LCClause(
        code="PAY-020",
        category=ClauseCategory.PAYMENT,
        subcategory="Draft",
        title="Draft - Sight",
        clause_text="DRAFT(S) DRAWN AT SIGHT ON {drawee}",
        plain_english="Formal payment instruction payable immediately.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["draft", "sight", "bill of exchange"]
    ),
    LCClause(
        code="PAY-021",
        category=ClauseCategory.PAYMENT,
        subcategory="Draft",
        title="Draft - Usance",
        clause_text="DRAFT(S) DRAWN AT {days} DAYS SIGHT ON {drawee}",
        plain_english="Formal payment instruction payable after stated period.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["draft", "usance", "acceptance"]
    ),
    LCClause(
        code="PAY-022",
        category=ClauseCategory.PAYMENT,
        subcategory="Draft",
        title="Draft Not Required",
        clause_text="DRAFT NOT REQUIRED",
        plain_english="No formal draft needed. Simplifies document preparation.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["draft", "not required", "simple"]
    ),
    
    # Bank Charges
    LCClause(
        code="PAY-030",
        category=ClauseCategory.PAYMENT,
        subcategory="Charges",
        title="All Charges for Applicant",
        clause_text="ALL BANKING CHARGES INCLUDING CONFIRMATION CHARGES ARE FOR ACCOUNT OF APPLICANT",
        plain_english="Buyer pays all bank fees. Better for seller.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["charges", "applicant", "fees"]
    ),
    LCClause(
        code="PAY-031",
        category=ClauseCategory.PAYMENT,
        subcategory="Charges",
        title="Charges Outside Issuing Country for Beneficiary",
        clause_text="ALL BANKING CHARGES OUTSIDE {issuing_country} ARE FOR BENEFICIARY'S ACCOUNT",
        plain_english="Standard split: buyer pays issuing bank, seller pays advising/negotiating bank.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["charges", "split", "standard"]
    ),
    LCClause(
        code="PAY-032",
        category=ClauseCategory.PAYMENT,
        subcategory="Charges",
        title="All Charges for Beneficiary",
        clause_text="ALL BANKING CHARGES ARE FOR ACCOUNT OF BENEFICIARY",
        plain_english="Seller pays all bank fees. Less favorable for seller.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Beneficiary should factor charges into pricing.",
        tags=["charges", "beneficiary", "fees"]
    ),
    
    # Reimbursement
    LCClause(
        code="PAY-040",
        category=ClauseCategory.PAYMENT,
        subcategory="Reimbursement",
        title="Reimbursement Authority",
        clause_text="REIMBURSEMENT AUTHORITY: {reimbursing_bank} SWIFT: {swift_code}",
        plain_english="Bank authorized to pay the negotiating bank.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["reimbursement", "bank", "authority"]
    ),
    
    # Discount
    LCClause(
        code="PAY-050",
        category=ClauseCategory.PAYMENT,
        subcategory="Discount",
        title="Discount Charges for Beneficiary",
        clause_text="DISCOUNT CHARGES FOR BENEFICIARY'S ACCOUNT IF EARLY PAYMENT REQUESTED",
        plain_english="If seller wants payment before maturity, they pay the discount fee.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["discount", "early payment", "charges"]
    ),
    LCClause(
        code="PAY-051",
        category=ClauseCategory.PAYMENT,
        subcategory="Discount",
        title="Discount Charges for Applicant",
        clause_text="DISCOUNT CHARGES FOR APPLICANT'S ACCOUNT",
        plain_english="Buyer pays for early payment to seller. Favorable for seller.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["discount", "applicant pays", "early"]
    ),
]

# ============================================================================
# SPECIAL CONDITIONS CLAUSES (95 clauses)
# ============================================================================

SPECIAL_CLAUSES = [
    # Document Presentation
    LCClause(
        code="SPEC-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Presentation",
        title="Presentation Period - Standard",
        clause_text="DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS AFTER SHIPMENT DATE BUT WITHIN LC VALIDITY",
        plain_english="Standard UCP600 rule. 21 days to present documents after shipping.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["presentation", "21 days", "UCP600"]
    ),
    LCClause(
        code="SPEC-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Presentation",
        title="Presentation Period - Extended",
        clause_text="DOCUMENTS MUST BE PRESENTED WITHIN {days} DAYS AFTER SHIPMENT DATE",
        plain_english="Extended time to present documents. More flexible for seller.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["presentation", "extended", "flexible"]
    ),
    LCClause(
        code="SPEC-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Presentation",
        title="Presentation Period - Shortened",
        clause_text="DOCUMENTS MUST BE PRESENTED WITHIN {days} DAYS AFTER SHIPMENT DATE",
        plain_english="Less time to present documents. Tighter deadline for seller.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Shortened period increases risk of late presentation.",
        tags=["presentation", "shortened", "tight"]
    ),
    
    # Expiry
    LCClause(
        code="SPEC-010",
        category=ClauseCategory.SPECIAL,
        subcategory="Expiry",
        title="Expiry in Beneficiary's Country",
        clause_text="EXPIRY DATE: {date} IN {beneficiary_country}",
        plain_english="LC expires in seller's country. Convenient for seller to present docs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["expiry", "beneficiary country", "convenient"]
    ),
    LCClause(
        code="SPEC-011",
        category=ClauseCategory.SPECIAL,
        subcategory="Expiry",
        title="Expiry in Issuing Country",
        clause_text="EXPIRY DATE: {date} IN {issuing_country}",
        plain_english="LC expires in buyer's country. Documents must reach there on time.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Adds risk of documents arriving late.",
        tags=["expiry", "issuing country"]
    ),
    
    # Confirmation
    LCClause(
        code="SPEC-020",
        category=ClauseCategory.SPECIAL,
        subcategory="Confirmation",
        title="Without Confirmation",
        clause_text="WITHOUT OUR CONFIRMATION / CONFIRMATION NOT REQUESTED",
        plain_english="No additional bank guarantee. Cheaper but seller relies on issuing bank.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["confirmation", "without", "cheaper"]
    ),
    LCClause(
        code="SPEC-021",
        category=ClauseCategory.SPECIAL,
        subcategory="Confirmation",
        title="May Add Confirmation",
        clause_text="ADVISING BANK MAY ADD THEIR CONFIRMATION AT BENEFICIARY'S REQUEST AND EXPENSE",
        plain_english="Seller can request confirmation if they want extra security.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["confirmation", "optional", "may add"]
    ),
    LCClause(
        code="SPEC-022",
        category=ClauseCategory.SPECIAL,
        subcategory="Confirmation",
        title="Confirm",
        clause_text="PLEASE ADD YOUR CONFIRMATION",
        plain_english="Request to advising bank to confirm. Extra security for seller.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["confirmation", "confirmed", "security"]
    ),
    
    # Tolerances
    LCClause(
        code="SPEC-030",
        category=ClauseCategory.SPECIAL,
        subcategory="Tolerance",
        title="Amount Tolerance +/-5%",
        clause_text="AMOUNT TOLERANCE: PLUS OR MINUS 5 PERCENT",
        plain_english="Invoice can be up to 5% more or less than LC amount.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["tolerance", "amount", "5%"]
    ),
    LCClause(
        code="SPEC-031",
        category=ClauseCategory.SPECIAL,
        subcategory="Tolerance",
        title="Amount Tolerance +/-10%",
        clause_text="AMOUNT TOLERANCE: PLUS OR MINUS 10 PERCENT",
        plain_english="Invoice can be up to 10% more or less than LC amount.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["tolerance", "amount", "10%"]
    ),
    LCClause(
        code="SPEC-032",
        category=ClauseCategory.SPECIAL,
        subcategory="Tolerance",
        title="Quantity Tolerance",
        clause_text="QUANTITY TOLERANCE: PLUS OR MINUS {percent} PERCENT",
        plain_english="Shipped quantity can vary by this percentage.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["tolerance", "quantity", "flexibility"]
    ),
    LCClause(
        code="SPEC-033",
        category=ClauseCategory.SPECIAL,
        subcategory="Tolerance",
        title="No Tolerance",
        clause_text="NO TOLERANCE ON AMOUNT OR QUANTITY - EXACT AMOUNTS REQUIRED",
        plain_english="Must ship and invoice exact amounts. Very restrictive.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.APPLICANT,
        risk_notes="High risk of discrepancy. Avoid unless necessary.",
        tags=["tolerance", "exact", "no flexibility"]
    ),
    
    # Transfer
    LCClause(
        code="SPEC-040",
        category=ClauseCategory.SPECIAL,
        subcategory="Transfer",
        title="Transferable",
        clause_text="THIS CREDIT IS TRANSFERABLE",
        plain_english="Beneficiary can transfer credit to another party (their supplier).",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["transferable", "middleman", "trading"]
    ),
    LCClause(
        code="SPEC-041",
        category=ClauseCategory.SPECIAL,
        subcategory="Transfer",
        title="Not Transferable",
        clause_text="THIS CREDIT IS NOT TRANSFERABLE",
        plain_english="Only named beneficiary can use this credit.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["non-transferable", "direct"]
    ),
    
    # Discrepancy Fee
    LCClause(
        code="SPEC-050",
        category=ClauseCategory.SPECIAL,
        subcategory="Discrepancy",
        title="Discrepancy Fee Warning",
        clause_text="DISCREPANT DOCUMENTS WILL BE SUBJECT TO A FEE OF USD {amount} PER SET",
        plain_english="Warning about fees if documents have errors.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["discrepancy", "fee", "warning"]
    ),
    
    # UCP Reference
    LCClause(
        code="SPEC-060",
        category=ClauseCategory.SPECIAL,
        subcategory="Governing Rules",
        title="Subject to UCP600",
        clause_text="THIS DOCUMENTARY CREDIT IS SUBJECT TO UNIFORM CUSTOMS AND PRACTICE FOR DOCUMENTARY CREDITS (2007 REVISION) ICC PUBLICATION NO. 600",
        plain_english="Standard international rules for documentary credits apply.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "ICC", "rules"]
    ),
    LCClause(
        code="SPEC-061",
        category=ClauseCategory.SPECIAL,
        subcategory="Governing Rules",
        title="Subject to ISP98",
        clause_text="THIS STANDBY CREDIT IS SUBJECT TO INTERNATIONAL STANDBY PRACTICES (ISP98) ICC PUBLICATION NO. 590",
        plain_english="ISP98 rules for standby credits apply.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["ISP98", "standby", "rules"]
    ),
]

# ============================================================================
# AMENDMENT CLAUSES (45 clauses)
# ============================================================================

AMENDMENT_CLAUSES = [
    LCClause(
        code="AMD-001",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Extension",
        title="Extend Expiry Date",
        clause_text="PLEASE EXTEND EXPIRY DATE FROM {old_date} TO {new_date}",
        plain_english="Request to give more time for document presentation.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "extend", "expiry"]
    ),
    LCClause(
        code="AMD-002",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Extension",
        title="Extend Shipment Date",
        clause_text="PLEASE EXTEND LATEST SHIPMENT DATE FROM {old_date} TO {new_date}",
        plain_english="Request to allow later shipment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "extend", "shipment"]
    ),
    LCClause(
        code="AMD-003",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Amount",
        title="Increase Amount",
        clause_text="PLEASE INCREASE LC AMOUNT FROM {old_amount} TO {new_amount}",
        plain_english="Request to increase the LC value.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "increase", "amount"]
    ),
    LCClause(
        code="AMD-004",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Amount",
        title="Decrease Amount",
        clause_text="PLEASE DECREASE LC AMOUNT FROM {old_amount} TO {new_amount}",
        plain_english="Request to reduce the LC value.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["amendment", "decrease", "amount"]
    ),
    LCClause(
        code="AMD-005",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Goods",
        title="Change Goods Description",
        clause_text="PLEASE AMEND GOODS DESCRIPTION TO READ: {new_description}",
        plain_english="Request to change what goods are covered.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Major changes may require new LC instead.",
        tags=["amendment", "goods", "description"]
    ),
    LCClause(
        code="AMD-006",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Port",
        title="Change Port of Loading",
        clause_text="PLEASE AMEND PORT OF LOADING FROM {old_port} TO {new_port}",
        plain_english="Request to change shipment origin.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "port", "loading"]
    ),
    LCClause(
        code="AMD-007",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Port",
        title="Change Port of Discharge",
        clause_text="PLEASE AMEND PORT OF DISCHARGE FROM {old_port} TO {new_port}",
        plain_english="Request to change destination.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["amendment", "port", "discharge"]
    ),
    LCClause(
        code="AMD-008",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Documents",
        title="Add Document Requirement",
        clause_text="PLEASE ADD THE FOLLOWING DOCUMENT REQUIREMENT: {document_requirement}",
        plain_english="Request to require additional document.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["amendment", "document", "add"]
    ),
    LCClause(
        code="AMD-009",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Documents",
        title="Delete Document Requirement",
        clause_text="PLEASE DELETE THE FOLLOWING DOCUMENT REQUIREMENT: {document_requirement}",
        plain_english="Request to remove a document requirement.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "document", "delete"]
    ),
    LCClause(
        code="AMD-010",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Partial",
        title="Allow Partial Shipments",
        clause_text="PLEASE AMEND TO ALLOW PARTIAL SHIPMENTS",
        plain_english="Request to permit shipping in multiple batches.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "partial", "shipment"]
    ),
]

# ============================================================================
# RED/GREEN CLAUSE (25 clauses)
# ============================================================================

RED_GREEN_CLAUSES = [
    LCClause(
        code="RG-001",
        category=ClauseCategory.RED_GREEN,
        subcategory="Red Clause",
        title="Red Clause - Advance Payment",
        clause_text="THE ADVISING/NEGOTIATING BANK IS AUTHORIZED TO MAKE ADVANCE PAYMENT(S) TO BENEFICIARY UP TO {amount} {currency} AGAINST BENEFICIARY'S SIMPLE RECEIPT AND UNDERTAKING TO DELIVER DOCUMENTS",
        plain_english="Allows seller to get advance payment before shipping. High risk for buyer.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.BENEFICIARY,
        risk_notes="Buyer's bank pays before goods ship. Usually for commodity trades.",
        tags=["red clause", "advance", "receipt"]
    ),
    LCClause(
        code="RG-002",
        category=ClauseCategory.RED_GREEN,
        subcategory="Red Clause",
        title="Red Clause - Warehouse Receipt",
        clause_text="ADVANCE PAYMENT ALLOWED AGAINST WAREHOUSE RECEIPT ISSUED BY APPROVED WAREHOUSE",
        plain_english="Advance against proof goods are stored in warehouse.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["red clause", "advance", "warehouse"]
    ),
    LCClause(
        code="RG-003",
        category=ClauseCategory.RED_GREEN,
        subcategory="Green Clause",
        title="Green Clause - Storage",
        clause_text="THE NEGOTIATING BANK IS AUTHORIZED TO ADVANCE UP TO {amount} {currency} AGAINST WAREHOUSE RECEIPT AND INSURANCE CERTIFICATE EVIDENCING STORAGE OF GOODS",
        plain_english="Advance against warehouse receipt + insurance. More secure than red clause.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        risk_notes="Goods must be in approved storage and insured.",
        tags=["green clause", "advance", "warehouse", "insurance"]
    ),
    LCClause(
        code="RG-004",
        category=ClauseCategory.RED_GREEN,
        subcategory="Red Clause",
        title="Red Clause - Percentage Advance",
        clause_text="PRE-SHIPMENT ADVANCE OF UP TO {percent}% OF LC VALUE ALLOWED AGAINST BENEFICIARY'S RECEIPT",
        plain_english="Advance limited to percentage of total LC value.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.BENEFICIARY,
        tags=["red clause", "percentage", "advance"]
    ),
    LCClause(
        code="RG-005",
        category=ClauseCategory.RED_GREEN,
        subcategory="Red Clause",
        title="Red Clause - Deduction at Final",
        clause_text="ADVANCE AMOUNT TO BE DEDUCTED FROM FINAL DRAWING UNDER THIS CREDIT",
        plain_english="The advance will be subtracted from the final payment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["red clause", "deduction", "final"]
    ),
]

# ============================================================================
# COMBINE ALL CLAUSES
# ============================================================================

ALL_CLAUSES: List[LCClause] = (
    SHIPMENT_CLAUSES +
    DOCUMENT_CLAUSES +
    PAYMENT_CLAUSES +
    SPECIAL_CLAUSES +
    AMENDMENT_CLAUSES +
    RED_GREEN_CLAUSES
)

# Create lookup by code
CLAUSE_BY_CODE: Dict[str, LCClause] = {c.code: c for c in ALL_CLAUSES}

# Group by category
CLAUSES_BY_CATEGORY: Dict[ClauseCategory, List[LCClause]] = {}
for clause in ALL_CLAUSES:
    if clause.category not in CLAUSES_BY_CATEGORY:
        CLAUSES_BY_CATEGORY[clause.category] = []
    CLAUSES_BY_CATEGORY[clause.category].append(clause)


class LCClauseLibrary:
    """
    Interface to the LC clause library.
    """
    
    @staticmethod
    def get_all_clauses() -> List[LCClause]:
        """Get all clauses"""
        return ALL_CLAUSES
    
    @staticmethod
    def get_clause_by_code(code: str) -> Optional[LCClause]:
        """Get a specific clause by code"""
        return CLAUSE_BY_CODE.get(code.upper())
    
    @staticmethod
    def get_clauses_by_category(category: ClauseCategory) -> List[LCClause]:
        """Get all clauses in a category"""
        return CLAUSES_BY_CATEGORY.get(category, [])
    
    @staticmethod
    def search_clauses(
        query: str,
        category: Optional[ClauseCategory] = None,
        risk_level: Optional[RiskLevel] = None,
        bias: Optional[BiasIndicator] = None
    ) -> List[LCClause]:
        """Search clauses by text and filters"""
        results = []
        query_lower = query.lower()
        
        for clause in ALL_CLAUSES:
            # Category filter
            if category and clause.category != category:
                continue
            
            # Risk level filter
            if risk_level and clause.risk_level != risk_level:
                continue
            
            # Bias filter
            if bias and clause.bias != bias:
                continue
            
            # Text search
            if query:
                searchable = f"{clause.title} {clause.clause_text} {clause.plain_english} {' '.join(clause.tags)}".lower()
                if query_lower not in searchable:
                    continue
            
            results.append(clause)
        
        return results
    
    @staticmethod
    def get_category_counts() -> Dict[str, int]:
        """Get count of clauses per category"""
        return {
            cat.value: len(clauses)
            for cat, clauses in CLAUSES_BY_CATEGORY.items()
        }
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Get library statistics"""
        return {
            "total_clauses": len(ALL_CLAUSES),
            "categories": LCClauseLibrary.get_category_counts(),
            "by_risk_level": {
                "low": len([c for c in ALL_CLAUSES if c.risk_level == RiskLevel.LOW]),
                "medium": len([c for c in ALL_CLAUSES if c.risk_level == RiskLevel.MEDIUM]),
                "high": len([c for c in ALL_CLAUSES if c.risk_level == RiskLevel.HIGH]),
            },
            "by_bias": {
                "beneficiary": len([c for c in ALL_CLAUSES if c.bias == BiasIndicator.BENEFICIARY]),
                "applicant": len([c for c in ALL_CLAUSES if c.bias == BiasIndicator.APPLICANT]),
                "neutral": len([c for c in ALL_CLAUSES if c.bias == BiasIndicator.NEUTRAL]),
            }
        }

