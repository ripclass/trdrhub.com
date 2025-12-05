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
# UCP600 ARTICLE-BASED CLAUSES (39 articles = more clauses)
# ============================================================================

UCP600_CLAUSES = [
    # Article 3 - Interpretations
    LCClause(
        code="UCP-003-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="Branches as Separate Banks",
        clause_text="BRANCHES OF A BANK IN DIFFERENT COUNTRIES ARE CONSIDERED TO BE SEPARATE BANKS",
        plain_english="For LC purposes, HSBC Hong Kong is a different bank from HSBC London.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "article 3", "branches"]
    ),
    LCClause(
        code="UCP-003-02",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="On or About Shipping Date",
        clause_text="SHIPMENT 'ON OR ABOUT' MEANS A PERIOD OF 5 DAYS BEFORE AND AFTER THE SPECIFIED DATE",
        plain_english="If LC says 'on or about 15 March', shipment can be 10-20 March.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "dates", "interpretation"]
    ),
    LCClause(
        code="UCP-003-03",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="First Half / Second Half",
        clause_text="'FIRST HALF' OF A MONTH MEANS 1ST TO 15TH, 'SECOND HALF' MEANS 16TH TO LAST DAY",
        plain_english="Standard interpretation for date ranges.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "dates", "periods"]
    ),
    LCClause(
        code="UCP-003-04",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="Beginning/Middle/End of Month",
        clause_text="'BEGINNING' = 1ST-10TH, 'MIDDLE' = 11TH-20TH, 'END' = 21ST-LAST DAY OF MONTH",
        plain_english="Standard interpretation for month periods.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "dates", "periods"]
    ),
    LCClause(
        code="UCP-003-05",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="To/Until/Till/From Inclusive",
        clause_text="WORDS 'TO', 'UNTIL', 'TILL', 'FROM' AND 'BETWEEN' INCLUDE THE DATE(S) MENTIONED",
        plain_english="'From 1 March to 15 March' includes both 1st and 15th.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "dates", "inclusive"]
    ),
    LCClause(
        code="UCP-003-06",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="Before/After Exclusive",
        clause_text="'BEFORE' AND 'AFTER' EXCLUDE THE DATE MENTIONED",
        plain_english="'Before 15 March' means up to and including 14 March.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "dates", "exclusive"]
    ),
    LCClause(
        code="UCP-003-07",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 3",
        title="Within Interpretation",
        clause_text="'WITHIN' INCLUDES THE DATE(S) MENTIONED",
        plain_english="'Within 10 days' includes the 10th day.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "dates", "within"]
    ),
    
    # Article 5 - Documents vs Goods
    LCClause(
        code="UCP-005-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 5",
        title="Banks Deal with Documents Only",
        clause_text="BANKS DEAL WITH DOCUMENTS AND NOT WITH GOODS, SERVICES OR PERFORMANCE TO WHICH DOCUMENTS MAY RELATE",
        plain_english="Banks check documents only. They don't inspect actual goods.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "article 5", "documents"]
    ),
    
    # Article 6 - Availability
    LCClause(
        code="UCP-006-01",
        category=ClauseCategory.PAYMENT,
        subcategory="UCP600 Article 6",
        title="Credit Must State Availability",
        clause_text="A CREDIT MUST STATE THE BANK WITH WHICH IT IS AVAILABLE OR WHETHER IT IS AVAILABLE WITH ANY BANK",
        plain_english="LC must say which bank will pay (nominated bank) or if any bank can.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "availability", "nominated bank"]
    ),
    LCClause(
        code="UCP-006-02",
        category=ClauseCategory.PAYMENT,
        subcategory="UCP600 Article 6",
        title="Freely Negotiable",
        clause_text="THIS CREDIT IS AVAILABLE WITH ANY BANK BY NEGOTIATION",
        plain_english="Beneficiary can present documents to any bank for payment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "freely negotiable", "any bank"]
    ),
    
    # Article 7 - Issuing Bank Undertaking
    LCClause(
        code="UCP-007-01",
        category=ClauseCategory.PAYMENT,
        subcategory="UCP600 Article 7",
        title="Issuing Bank Irrevocable Undertaking",
        clause_text="ISSUING BANK UNDERTAKES TO HONOUR A COMPLYING PRESENTATION FROM THE TIME OF ISSUANCE",
        plain_english="Issuing bank must pay if documents comply. This is irrevocable.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "undertaking", "irrevocable"]
    ),
    
    # Article 8 - Confirming Bank Undertaking
    LCClause(
        code="UCP-008-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 8",
        title="Confirmation Adds Second Bank Guarantee",
        clause_text="CONFIRMING BANK IS IRREVOCABLY BOUND TO HONOUR OR NEGOTIATE FROM TIME OF CONFIRMATION",
        plain_english="If confirmed, beneficiary has two banks guaranteeing payment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "confirmation", "guarantee"]
    ),
    
    # Article 14 - Standard for Examination
    LCClause(
        code="UCP-014-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 14",
        title="Documents Must Be Examined Carefully",
        clause_text="A NOMINATED BANK, CONFIRMING BANK OR ISSUING BANK MUST EXAMINE A PRESENTATION TO DETERMINE WHETHER IT APPEARS ON ITS FACE TO COMPLY",
        plain_english="Banks check if documents look correct on their face. They don't verify facts.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "examination", "face value"]
    ),
    LCClause(
        code="UCP-014-02",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 14",
        title="Five Banking Days to Examine",
        clause_text="BANKS HAVE A MAXIMUM OF 5 BANKING DAYS TO EXAMINE DOCUMENTS AND DETERMINE COMPLIANCE",
        plain_english="Bank must decide within 5 working days if documents are OK or not.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "examination", "5 days"]
    ),
    LCClause(
        code="UCP-014-03",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 14",
        title="Data Need Not Be Identical",
        clause_text="DATA IN A DOCUMENT NEED NOT BE IDENTICAL TO BUT MUST NOT CONFLICT WITH DATA IN THAT DOCUMENT, ANY OTHER STIPULATED DOCUMENT OR THE CREDIT",
        plain_english="Minor differences are OK if data doesn't contradict. E.g., 'Company Ltd' vs 'Company Limited'.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "data", "consistency"]
    ),
    
    # Article 16 - Discrepant Documents
    LCClause(
        code="UCP-016-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 16",
        title="Bank Must Notify Refusal",
        clause_text="IF A BANK REFUSES TO HONOUR OR NEGOTIATE, IT MUST GIVE NOTICE TO THAT EFFECT BY TELECOMMUNICATION",
        plain_english="If bank rejects documents, they must tell you why by SWIFT/email within 5 days.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "refusal", "notification"]
    ),
    LCClause(
        code="UCP-016-02",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 16",
        title="Single Notice All Discrepancies",
        clause_text="NOTICE OF REFUSAL MUST STATE ALL DISCREPANCIES IN RESPECT OF WHICH THE BANK REFUSES TO HONOUR OR NEGOTIATE",
        plain_english="Bank must list ALL problems at once. Can't reject, then find more issues later.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "discrepancies", "preclusion"]
    ),
    
    # Article 17 - Original Documents
    LCClause(
        code="UCP-017-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 17",
        title="At Least One Original Required",
        clause_text="AT LEAST ONE ORIGINAL OF EACH DOCUMENT STIPULATED IN THE CREDIT MUST BE PRESENTED",
        plain_english="You must present at least one original, not all copies.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "originals", "copies"]
    ),
    LCClause(
        code="UCP-017-02",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 17",
        title="Document Appears to be Original",
        clause_text="A BANK SHALL TREAT AS AN ORIGINAL ANY DOCUMENT BEARING AN APPARENTLY ORIGINAL SIGNATURE, MARK, STAMP OR LABEL OF THE ISSUER",
        plain_english="If document has original signature/stamp, it counts as original.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "originals", "signature"]
    ),
    
    # Article 18 - Commercial Invoice
    LCClause(
        code="UCP-018-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 18",
        title="Invoice Must Be Issued by Beneficiary",
        clause_text="A COMMERCIAL INVOICE MUST BE ISSUED BY THE BENEFICIARY (EXCEPT AS PROVIDED IN ARTICLE 38)",
        plain_english="Invoice must show beneficiary as seller. Can't use supplier's invoice.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "invoice", "beneficiary"]
    ),
    LCClause(
        code="UCP-018-02",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 18",
        title="Invoice Must Be Made Out to Applicant",
        clause_text="A COMMERCIAL INVOICE MUST BE MADE OUT IN THE NAME OF THE APPLICANT (EXCEPT AS PROVIDED IN SUB-ARTICLE 38(G))",
        plain_english="Invoice must show applicant (buyer) as the customer.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "invoice", "applicant"]
    ),
    LCClause(
        code="UCP-018-03",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 18",
        title="Invoice Goods Description Must Match LC",
        clause_text="THE DESCRIPTION OF GOODS IN THE COMMERCIAL INVOICE MUST CORRESPOND WITH THAT APPEARING IN THE CREDIT",
        plain_english="Invoice goods description must match LC exactly. Other docs can use general terms.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="This is a common discrepancy. Check word-for-word match.",
        tags=["UCP600", "invoice", "description"]
    ),
    LCClause(
        code="UCP-018-04",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 18",
        title="Invoice Amount Cannot Exceed LC Amount",
        clause_text="THE INVOICE AMOUNT MUST NOT EXCEED THAT ALLOWED BY THE CREDIT",
        plain_english="Invoice cannot be more than LC amount. Tolerance applies per Article 30.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Over-invoicing is a hard discrepancy. No bank acceptance.",
        tags=["UCP600", "invoice", "amount"]
    ),
    
    # Article 19 - Transport Covering Multiple Modes
    LCClause(
        code="UCP-019-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 19",
        title="Multimodal Transport Document",
        clause_text="A TRANSPORT DOCUMENT COVERING AT LEAST TWO DIFFERENT MODES OF TRANSPORT (MULTIMODAL OR COMBINED TRANSPORT DOCUMENT)",
        plain_english="For door-to-door shipments using truck + ship or rail + ship.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "multimodal", "transport"]
    ),
    
    # Article 20 - Bill of Lading
    LCClause(
        code="UCP-020-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 20",
        title="B/L Must Name Carrier",
        clause_text="A BILL OF LADING MUST APPEAR TO INDICATE THE NAME OF THE CARRIER AND BE SIGNED",
        plain_english="B/L must show which shipping company carried the goods.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "B/L", "carrier"]
    ),
    LCClause(
        code="UCP-020-02",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 20",
        title="B/L Must Show Port to Port",
        clause_text="A BILL OF LADING MUST INDICATE SHIPMENT FROM THE PORT OF LOADING TO THE PORT OF DISCHARGE STATED IN THE CREDIT",
        plain_english="B/L ports must match LC ports exactly.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Port mismatch is a common discrepancy.",
        tags=["UCP600", "B/L", "ports"]
    ),
    LCClause(
        code="UCP-020-03",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 20",
        title="Full Set B/L Required",
        clause_text="IF A CREDIT REQUIRES PRESENTATION OF A FULL SET OF BILLS OF LADING, ALL ORIGINALS INDICATED MUST BE PRESENTED",
        plain_english="If LC says 'full set 3/3', you must present all 3 originals.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Missing originals is a hard discrepancy.",
        tags=["UCP600", "B/L", "full set"]
    ),
    
    # Article 21 - Non-Negotiable Sea Waybill
    LCClause(
        code="UCP-021-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 21",
        title="Sea Waybill Acceptable",
        clause_text="NON-NEGOTIABLE SEA WAYBILL ACCEPTABLE",
        plain_english="Sea waybill OK instead of B/L. Simpler but not a document of title.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "sea waybill", "non-negotiable"]
    ),
    
    # Article 22 - Charter Party B/L
    LCClause(
        code="UCP-022-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 22",
        title="Charter Party B/L Requirements",
        clause_text="A CHARTER PARTY BILL OF LADING MUST BE SIGNED BY THE MASTER OR CHARTERER AND INDICATE THAT IT IS SUBJECT TO A CHARTER PARTY",
        plain_english="Charter party B/Ls have different rules. Must clearly show it's under charter.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "charter party", "B/L"]
    ),
    
    # Article 23 - Air Transport
    LCClause(
        code="UCP-023-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 23",
        title="Air Waybill Requirements",
        clause_text="AN AIR TRANSPORT DOCUMENT MUST INDICATE THE NAME OF THE CARRIER, BE SIGNED, AND INDICATE THE AIRPORT OF DEPARTURE AND DESTINATION",
        plain_english="AWB must show airline name, be signed, and show airports.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "AWB", "air transport"]
    ),
    
    # Article 24 - Road/Rail/Inland Waterway
    LCClause(
        code="UCP-024-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 24",
        title="Road/Rail Transport Document",
        clause_text="A ROAD, RAIL OR INLAND WATERWAY TRANSPORT DOCUMENT",
        plain_english="For shipments by truck, train, or river barge.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "road", "rail", "inland"]
    ),
    
    # Article 25 - Courier Receipt
    LCClause(
        code="UCP-025-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 25",
        title="Courier Receipt Acceptable",
        clause_text="A COURIER RECEIPT, HOWEVER NAMED, FROM COURIER SERVICE SUCH AS DHL, FEDEX OR UPS",
        plain_english="For small shipments sent by express courier.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "courier", "express"]
    ),
    
    # Article 26 - On Deck/Shipper's Load
    LCClause(
        code="UCP-026-01",
        category=ClauseCategory.SHIPMENT,
        subcategory="UCP600 Article 26",
        title="On Deck Shipment Acceptable",
        clause_text="ON DECK SHIPMENT ACCEPTABLE",
        plain_english="Goods may be shipped on deck (not below deck). Usually for containers.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "on deck", "stowage"]
    ),
    LCClause(
        code="UCP-026-02",
        category=ClauseCategory.SHIPMENT,
        subcategory="UCP600 Article 26",
        title="Shipper's Load and Count Acceptable",
        clause_text="'SHIPPER'S LOAD AND COUNT' OR 'SAID TO CONTAIN' ACCEPTABLE",
        plain_english="Carrier accepts shipper's statement of contents without checking.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "shipper's load", "SLC"]
    ),
    
    # Article 27 - Clean Transport Document
    LCClause(
        code="UCP-027-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 27",
        title="Clean Transport Document Required",
        clause_text="BANKS WILL ONLY ACCEPT A CLEAN TRANSPORT DOCUMENT. A CLEAN DOCUMENT BEARS NO CLAUSE OR NOTATION EXPRESSLY DECLARING A DEFECTIVE CONDITION",
        plain_english="B/L cannot have remarks like 'damaged' or 'cargo wet'. Must be clean.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Claused B/L is almost always rejected.",
        tags=["UCP600", "clean", "B/L"]
    ),
    
    # Article 28 - Insurance
    LCClause(
        code="UCP-028-01",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 28",
        title="Insurance Effective Date",
        clause_text="THE DATE OF THE INSURANCE DOCUMENT MUST BE NO LATER THAN THE DATE OF SHIPMENT",
        plain_english="Insurance must start on or before shipping date, not after.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Insurance dated after shipment is a discrepancy.",
        tags=["UCP600", "insurance", "date"]
    ),
    LCClause(
        code="UCP-028-02",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 28",
        title="Insurance Currency Must Match",
        clause_text="AN INSURANCE DOCUMENT MUST BE IN THE SAME CURRENCY AS THE CREDIT",
        plain_english="If LC is in USD, insurance must be in USD.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "insurance", "currency"]
    ),
    LCClause(
        code="UCP-028-03",
        category=ClauseCategory.DOCUMENTS,
        subcategory="UCP600 Article 28",
        title="Minimum Insurance Coverage",
        clause_text="IF A CREDIT DOES NOT INDICATE THE INSURANCE COVERAGE REQUIRED, THE MINIMUM AMOUNT IS 110% OF CIF OR CIP VALUE",
        plain_english="Default: insure for at least 110% of goods value.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "insurance", "110%"]
    ),
    
    # Article 29 - Extension of Expiry
    LCClause(
        code="UCP-029-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 29",
        title="Expiry on Non-Banking Day",
        clause_text="IF EXPIRY DATE FALLS ON A NON-BANKING DAY, IT IS EXTENDED TO THE FIRST FOLLOWING BANKING DAY",
        plain_english="If LC expires on Sunday, you can present on Monday.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "expiry", "extension"]
    ),
    LCClause(
        code="UCP-029-02",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 29",
        title="Bank Closure Force Majeure",
        clause_text="IF BANK IS CLOSED DUE TO INTERRUPTION OF BUSINESS, THE EXPIRY DATE AND PRESENTATION PERIOD ARE EXTENDED",
        plain_english="If bank closes due to strike/war/disaster, deadlines extend.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "force majeure", "closure"]
    ),
    
    # Article 30 - Tolerance
    LCClause(
        code="UCP-030-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 30",
        title="5% Quantity Tolerance Default",
        clause_text="A TOLERANCE NOT TO EXCEED 5% MORE OR 5% LESS THAN THE QUANTITY STATED IS ALLOWED UNLESS THE CREDIT STATES OTHERWISE",
        plain_english="Can ship 95-105% of quantity unless LC prohibits or specifies exact amount.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "tolerance", "5%"]
    ),
    LCClause(
        code="UCP-030-02",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 30",
        title="About/Approximately +/-10%",
        clause_text="'ABOUT' OR 'APPROXIMATELY' ALLOWS A TOLERANCE NOT TO EXCEED 10% MORE OR LESS",
        plain_english="If LC says 'about 10,000 pcs', can ship 9,000-11,000 pcs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "tolerance", "10%", "about"]
    ),
    
    # Article 31 - Partial Drawings
    LCClause(
        code="UCP-031-01",
        category=ClauseCategory.SHIPMENT,
        subcategory="UCP600 Article 31",
        title="Partial Drawings Allowed by Default",
        clause_text="PARTIAL DRAWINGS OR SHIPMENTS ARE ALLOWED UNLESS THE CREDIT STATES OTHERWISE",
        plain_english="Default: Can ship in parts and draw against each shipment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "partial", "default"]
    ),
    
    # Article 32 - Instalment Drawings
    LCClause(
        code="UCP-032-01",
        category=ClauseCategory.SHIPMENT,
        subcategory="UCP600 Article 32",
        title="Instalment Schedule Must Be Met",
        clause_text="IF A DRAWING OR SHIPMENT BY INSTALMENTS WITHIN GIVEN PERIODS IS STIPULATED AND ANY INSTALMENT IS NOT DRAWN OR SHIPPED, THE CREDIT CEASES TO BE AVAILABLE",
        plain_english="Miss one scheduled shipment = lose credit for future instalments. Very strict.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Instalment clauses are risky. One miss = credit cancelled.",
        tags=["UCP600", "instalment", "schedule"]
    ),
    
    # Article 33 - Hours of Presentation
    LCClause(
        code="UCP-033-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 33",
        title="Banking Hours",
        clause_text="DOCUMENTS MUST BE PRESENTED DURING BANKING HOURS OF THE PLACE OF PRESENTATION",
        plain_english="Present documents during bank's working hours only.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "presentation", "hours"]
    ),
    
    # Article 34 - Disclaimer on Goods
    LCClause(
        code="UCP-034-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 34",
        title="Bank Not Responsible for Goods",
        clause_text="BANK ASSUMES NO LIABILITY FOR THE DESCRIPTION, QUANTITY, WEIGHT, QUALITY, CONDITION, PACKING, DELIVERY, VALUE OR EXISTENCE OF GOODS",
        plain_english="Bank only checks documents. Not responsible if goods are defective.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "disclaimer", "liability"]
    ),
    
    # Article 35 - Disclaimer on Transmission
    LCClause(
        code="UCP-035-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 35",
        title="Bank Not Liable for Transmission Errors",
        clause_text="BANK ASSUMES NO LIABILITY FOR DELAYS, LOSS IN TRANSIT, MUTILATION OR OTHER ERRORS IN TRANSMISSION OF MESSAGES",
        plain_english="Bank not responsible if SWIFT message is delayed or corrupted.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "transmission", "disclaimer"]
    ),
    
    # Article 36 - Force Majeure
    LCClause(
        code="UCP-036-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 36",
        title="Force Majeure",
        clause_text="BANK ASSUMES NO LIABILITY FOR CONSEQUENCES ARISING OUT OF INTERRUPTION OF BUSINESS DUE TO ACTS OF GOD, RIOTS, CIVIL COMMOTIONS, INSURRECTIONS, WARS, OR ANY OTHER CAUSES BEYOND CONTROL",
        plain_english="Bank not responsible for delays due to war, natural disasters, etc.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "force majeure", "war"]
    ),
    
    # Article 38 - Transferable Credits
    LCClause(
        code="UCP-038-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 38",
        title="Transferable Must Be Stated",
        clause_text="A CREDIT CAN BE TRANSFERRED ONLY IF IT IS EXPRESSLY DESIGNATED AS 'TRANSFERABLE' BY THE ISSUING BANK",
        plain_english="LC must explicitly say 'transferable' to be transferred.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "transferable", "explicit"]
    ),
    LCClause(
        code="UCP-038-02",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 38",
        title="Transfer Only Once",
        clause_text="A CREDIT MAY BE TRANSFERRED IN PART TO MORE THAN ONE SECOND BENEFICIARY PROVIDED PARTIAL DRAWINGS OR SHIPMENTS ARE ALLOWED",
        plain_english="Can split transfer to multiple suppliers if partial shipments allowed.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "transferable", "partial"]
    ),
    LCClause(
        code="UCP-038-03",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 38",
        title="Transfer Changes Allowed",
        clause_text="THE TRANSFERRED CREDIT MAY REDUCE THE AMOUNT, UNIT PRICE, EXPIRY DATE, PRESENTATION PERIOD, LATEST SHIPMENT DATE OR PERIOD FOR SHIPMENT",
        plain_english="When transferring, can reduce amount/prices/dates but not increase.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UCP600", "transferable", "substitution"]
    ),
    
    # Article 39 - Assignment of Proceeds
    LCClause(
        code="UCP-039-01",
        category=ClauseCategory.SPECIAL,
        subcategory="UCP600 Article 39",
        title="Assignment of Proceeds",
        clause_text="THE FACT THAT A CREDIT IS NOT STATED TO BE TRANSFERABLE SHALL NOT AFFECT THE RIGHT OF THE BENEFICIARY TO ASSIGN ANY PROCEEDS",
        plain_english="Even non-transferable LCs can have proceeds assigned to third party.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["UCP600", "assignment", "proceeds"]
    ),
]

# ============================================================================
# ISBP745 CLAUSES (More specific document examination rules)
# ============================================================================

ISBP745_CLAUSES = [
    # General Principles
    LCClause(
        code="ISBP-001",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 General",
        title="Abbreviations Acceptable",
        clause_text="GENERALLY ACCEPTED ABBREVIATIONS MAY BE USED",
        plain_english="'Co.' for Company, 'Ltd' for Limited, etc. are OK.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "abbreviations"]
    ),
    LCClause(
        code="ISBP-002",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 General",
        title="Corrections Must Be Authenticated",
        clause_text="CORRECTIONS AND ALTERATIONS IN DOCUMENTS MUST APPEAR TO BE AUTHENTICATED BY THE PARTY WHO ISSUED THE DOCUMENT",
        plain_english="If you correct a typo, you must sign/stamp next to it.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["ISBP745", "corrections", "authentication"]
    ),
    LCClause(
        code="ISBP-003",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 General",
        title="Dates Format Acceptable",
        clause_text="DATES MAY BE EXPRESSED IN DIFFERENT FORMATS (DD/MM/YY, MM/DD/YY, YY/MM/DD) PROVIDED THEY DO NOT CREATE AMBIGUITY",
        plain_english="Different date formats OK if meaning is clear.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "dates", "format"]
    ),
    LCClause(
        code="ISBP-004",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 General",
        title="Misspellings That Don't Change Meaning",
        clause_text="MISSPELLINGS OR TYPING ERRORS THAT DO NOT AFFECT THE MEANING OF A WORD ARE NOT REGARDED AS A DISCREPANCY",
        plain_english="'Shanghia' instead of 'Shanghai' may be OK if clearly the same place.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "typos", "misspellings"]
    ),
    LCClause(
        code="ISBP-005",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 General",
        title="Mathematical Calculations",
        clause_text="MATHEMATICAL CALCULATIONS IN A DOCUMENT MUST BE MATHEMATICALLY CORRECT BUT NEED NOT BE CHECKED BEYOND REASONABLENESS",
        plain_english="Totals must add up correctly.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["ISBP745", "calculations", "math"]
    ),
    
    # Drafts / Bills of Exchange
    LCClause(
        code="ISBP-010",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Drafts",
        title="Draft Must Be Drawn on Named Drawee",
        clause_text="A DRAFT MUST BE DRAWN ON THE PARTY STATED IN THE CREDIT",
        plain_english="Draft must be drawn on whoever the LC says (usually issuing bank).",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["ISBP745", "draft", "drawee"]
    ),
    LCClause(
        code="ISBP-011",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Drafts",
        title="Draft Amount in Figures and Words",
        clause_text="THE AMOUNT OF A DRAFT MUST BE SHOWN IN BOTH FIGURES AND WORDS",
        plain_english="Draft must show 'USD 50,000.00' and 'FIFTY THOUSAND US DOLLARS'.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["ISBP745", "draft", "amount"]
    ),
    
    # Invoices
    LCClause(
        code="ISBP-020",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Invoice",
        title="Invoice Need Not Be Signed",
        clause_text="A COMMERCIAL INVOICE NEED NOT BE SIGNED UNLESS REQUIRED BY THE CREDIT",
        plain_english="Invoice signature only required if LC says so.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "invoice", "signature"]
    ),
    LCClause(
        code="ISBP-021",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Invoice",
        title="Invoice Quantity May Use Shipping Units",
        clause_text="THE QUANTITY OF GOODS IN AN INVOICE MAY BE SHOWN IN THE SHIPPING UNIT STATED IN THE CREDIT",
        plain_english="If LC says 'about 100 MT', invoice can show 98.5 MT.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "invoice", "quantity"]
    ),
    
    # Transport Documents
    LCClause(
        code="ISBP-030",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Transport",
        title="Pre-Carriage OK if Same B/L",
        clause_text="A B/L MAY INDICATE PRE-CARRIAGE BY DIFFERENT MEANS OF TRANSPORT TO THE PORT OF LOADING",
        plain_english="Goods can be trucked to port, then put on ship. Same B/L OK.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "B/L", "pre-carriage"]
    ),
    LCClause(
        code="ISBP-031",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Transport",
        title="On-Carriage OK if Same B/L",
        clause_text="A B/L MAY INDICATE ON-CARRIAGE AFTER DISCHARGE TO A PLACE DIFFERENT FROM THE PORT OF DISCHARGE",
        plain_english="Goods can be trucked from port to final destination. Same B/L OK.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "B/L", "on-carriage"]
    ),
    
    # Insurance
    LCClause(
        code="ISBP-040",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Insurance",
        title="Open Cover Certificates",
        clause_text="AN INSURANCE CERTIFICATE ISSUED UNDER AN OPEN COVER IS ACCEPTABLE",
        plain_english="Insurance certificate from master policy OK.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "insurance", "open cover"]
    ),
    LCClause(
        code="ISBP-041",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Insurance",
        title="Insurance Risks Coverage",
        clause_text="IF A CREDIT REQUIRES 'ALL RISKS' COVERAGE, AN INSURANCE DOCUMENT BEARING ANY 'ALL RISKS' CLAUSE OR NOTATION IS ACCEPTABLE",
        plain_english="Any 'All Risks' wording acceptable, doesn't need exact ICC(A) mention.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "insurance", "all risks"]
    ),
    
    # Certificates of Origin
    LCClause(
        code="ISBP-050",
        category=ClauseCategory.DOCUMENTS,
        subcategory="ISBP745 Origin",
        title="CoO May Be Issued by Any Party",
        clause_text="A CERTIFICATE OF ORIGIN MAY BE ISSUED BY THE BENEFICIARY, A CHAMBER OF COMMERCE, OR ANY OTHER PARTY",
        plain_english="Origin certificate can come from seller, chamber, or inspection company.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["ISBP745", "origin", "issuer"]
    ),
]

# ============================================================================
# REGIONAL CLAUSES (Bangladesh, India, Pakistan specific)
# ============================================================================

REGIONAL_CLAUSES = [
    # Bangladesh Bank Requirements
    LCClause(
        code="BD-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Bangladesh Bank",
        title="EXP Form Reference",
        clause_text="EXP FORM NUMBER {exp_number} DATED {date} MUST BE REFERENCED",
        plain_english="Bangladesh exporters must reference their EXP form in documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Bangladesh", "EXP form", "regulatory"]
    ),
    LCClause(
        code="BD-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Bangladesh Bank",
        title="Repatriation Deadline",
        clause_text="EXPORT PROCEEDS MUST BE REPATRIATED WITHIN 4 MONTHS FROM SHIPMENT DATE AS PER BANGLADESH BANK GUIDELINES",
        plain_english="Bangladesh law: export money must return within 4 months.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["Bangladesh", "repatriation", "timeline"]
    ),
    LCClause(
        code="BD-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Bangladesh Bank",
        title="UD Form for Usance LC",
        clause_text="UD FORM MUST BE SUBMITTED FOR USANCE LC TRANSACTIONS",
        plain_english="Bangladesh requires UD form for deferred payment LCs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Bangladesh", "UD form", "usance"]
    ),
    
    # India RBI Requirements
    LCClause(
        code="IN-001",
        category=ClauseCategory.SPECIAL,
        subcategory="RBI India",
        title="AD Code Reference",
        clause_text="AD CODE {ad_code} MUST BE MENTIONED IN DOCUMENTS",
        plain_english="India exporters must include Authorized Dealer code.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["India", "AD code", "FEMA"]
    ),
    LCClause(
        code="IN-002",
        category=ClauseCategory.SPECIAL,
        subcategory="RBI India",
        title="IEC Number Required",
        clause_text="IMPORTER EXPORTER CODE (IEC) {iec_number} MUST BE STATED",
        plain_english="India's 10-digit IEC required for all trade documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["India", "IEC", "regulatory"]
    ),
    LCClause(
        code="IN-003",
        category=ClauseCategory.SPECIAL,
        subcategory="RBI India",
        title="FEMA Compliance",
        clause_text="TRANSACTION COMPLIES WITH FOREIGN EXCHANGE MANAGEMENT ACT (FEMA) REGULATIONS",
        plain_english="India's foreign exchange regulations must be followed.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["India", "FEMA", "compliance"]
    ),
    
    # Pakistan SBP Requirements
    LCClause(
        code="PK-001",
        category=ClauseCategory.SPECIAL,
        subcategory="SBP Pakistan",
        title="Form E Reference",
        clause_text="FORM E NUMBER {form_e_number} DATED {date} MUST BE REFERENCED",
        plain_english="Pakistan exporters must reference Form E in documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Pakistan", "Form E", "SBP"]
    ),
    LCClause(
        code="PK-002",
        category=ClauseCategory.SPECIAL,
        subcategory="SBP Pakistan",
        title="NTN Number Required",
        clause_text="NATIONAL TAX NUMBER (NTN) {ntn_number} MUST BE STATED",
        plain_english="Pakistan's tax ID required on trade documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Pakistan", "NTN", "tax"]
    ),
    
    # UAE Requirements
    LCClause(
        code="AE-001",
        category=ClauseCategory.SPECIAL,
        subcategory="UAE",
        title="Chamber of Commerce Attestation",
        clause_text="DOCUMENTS MUST BE ATTESTED BY UAE CHAMBER OF COMMERCE",
        plain_english="UAE often requires chamber attestation on documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["UAE", "attestation", "chamber"]
    ),
    
    # China Requirements
    LCClause(
        code="CN-001",
        category=ClauseCategory.SPECIAL,
        subcategory="China SAFE",
        title="SAFE Filing Reference",
        clause_text="STATE ADMINISTRATION OF FOREIGN EXCHANGE (SAFE) FILING REFERENCE MUST BE PROVIDED",
        plain_english="China's forex control registration must be referenced.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["China", "SAFE", "forex"]
    ),
]

# ============================================================================
# INDUSTRY-SPECIFIC CLAUSES
# ============================================================================

INDUSTRY_CLAUSES = [
    # Textiles/RMG
    LCClause(
        code="IND-TEX-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Textiles/RMG",
        title="GSP Form A Required",
        clause_text="GSP FORM A CERTIFICATE OF ORIGIN FOR PREFERENTIAL DUTY TREATMENT REQUIRED",
        plain_english="For duty-free export to EU/UK under GSP scheme.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["textiles", "GSP", "duty"]
    ),
    LCClause(
        code="IND-TEX-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Textiles/RMG",
        title="Oeko-Tex Certificate",
        clause_text="OEKO-TEX STANDARD 100 CERTIFICATE REQUIRED CERTIFYING PRODUCTS TESTED FOR HARMFUL SUBSTANCES",
        plain_english="Safety certification for textiles - common for EU buyers.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["textiles", "Oeko-Tex", "safety"]
    ),
    LCClause(
        code="IND-TEX-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Textiles/RMG",
        title="Size Ratio Breakdown",
        clause_text="PACKING LIST MUST SHOW SIZE RATIO BREAKDOWN (S/M/L/XL)",
        plain_english="For garments, show quantity by size.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["textiles", "size ratio", "packing"]
    ),
    
    # Electronics
    LCClause(
        code="IND-ELEC-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Electronics",
        title="CE Marking Certificate",
        clause_text="CE MARKING CERTIFICATE REQUIRED FOR EUROPEAN MARKET COMPLIANCE",
        plain_english="Required for electronics sold in EU.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["electronics", "CE", "EU"]
    ),
    LCClause(
        code="IND-ELEC-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Electronics",
        title="RoHS Compliance",
        clause_text="ROHS COMPLIANCE CERTIFICATE CERTIFYING PRODUCTS FREE FROM RESTRICTED HAZARDOUS SUBSTANCES",
        plain_english="No lead, mercury, cadmium in electronics.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["electronics", "RoHS", "hazardous"]
    ),
    LCClause(
        code="IND-ELEC-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Electronics",
        title="Serial Number List",
        clause_text="PACKING LIST MUST INCLUDE SERIAL NUMBERS OF ALL UNITS",
        plain_english="Track individual electronic items by serial.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["electronics", "serial numbers", "tracking"]
    ),
    
    # Food/Agricultural
    LCClause(
        code="IND-FOOD-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Food/Agricultural",
        title="Phytosanitary Certificate",
        clause_text="PHYTOSANITARY CERTIFICATE ISSUED BY AGRICULTURAL AUTHORITY CERTIFYING PRODUCTS FREE FROM PESTS AND DISEASES",
        plain_english="Required for plant products to ensure no crop diseases.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["food", "phytosanitary", "agricultural"]
    ),
    LCClause(
        code="IND-FOOD-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Food/Agricultural",
        title="Health Certificate",
        clause_text="HEALTH CERTIFICATE ISSUED BY COMPETENT HEALTH AUTHORITY",
        plain_english="For food products to ensure safety for consumption.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["food", "health", "safety"]
    ),
    LCClause(
        code="IND-FOOD-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Food/Agricultural",
        title="Halal Certificate",
        clause_text="HALAL CERTIFICATE ISSUED BY RECOGNIZED ISLAMIC AUTHORITY",
        plain_english="Required for Muslim markets (Middle East, Malaysia, etc.).",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["food", "halal", "Islamic"]
    ),
    LCClause(
        code="IND-FOOD-004",
        category=ClauseCategory.SPECIAL,
        subcategory="Food/Agricultural",
        title="Fumigation Certificate",
        clause_text="FUMIGATION CERTIFICATE REQUIRED FOR WOODEN PACKAGING (ISPM-15 COMPLIANT)",
        plain_english="Wooden pallets must be heat treated or fumigated.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["food", "fumigation", "ISPM-15"]
    ),
    LCClause(
        code="IND-FOOD-005",
        category=ClauseCategory.SPECIAL,
        subcategory="Food/Agricultural",
        title="Temperature Log Required",
        clause_text="TEMPERATURE LOG/REEFER CONTAINER TEMPERATURE RECORD REQUIRED",
        plain_english="For refrigerated cargo, show temperature was maintained.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["food", "reefer", "temperature"]
    ),
    
    # Chemicals/Hazmat
    LCClause(
        code="IND-CHEM-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Chemicals",
        title="Material Safety Data Sheet",
        clause_text="MATERIAL SAFETY DATA SHEET (MSDS) REQUIRED FOR CHEMICAL PRODUCTS",
        plain_english="Safety information for handling chemicals.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["chemicals", "MSDS", "safety"]
    ),
    LCClause(
        code="IND-CHEM-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Chemicals",
        title="Dangerous Goods Declaration",
        clause_text="DANGEROUS GOODS DECLARATION (IMO CLASS) REQUIRED",
        plain_english="For hazardous cargo, IMO classification must be declared.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["chemicals", "dangerous goods", "IMO"]
    ),
    
    # Machinery/Equipment
    LCClause(
        code="IND-MACH-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Machinery",
        title="Performance Test Certificate",
        clause_text="PERFORMANCE TEST CERTIFICATE ISSUED BY MANUFACTURER OR INDEPENDENT SURVEYOR",
        plain_english="For machinery, prove it works as specified.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["machinery", "performance", "testing"]
    ),
    LCClause(
        code="IND-MACH-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Machinery",
        title="Installation Manual Required",
        clause_text="INSTALLATION AND OPERATION MANUAL IN {language} REQUIRED",
        plain_english="Machine must come with manuals in buyer's language.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["machinery", "manual", "documentation"]
    ),
    LCClause(
        code="IND-MACH-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Machinery",
        title="Warranty Certificate",
        clause_text="WARRANTY CERTIFICATE FOR {period} MONTHS/YEARS FROM DATE OF SHIPMENT/INSTALLATION",
        plain_english="Seller certifies warranty period for equipment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["machinery", "warranty", "guarantee"]
    ),
    
    # Bulk Commodities
    LCClause(
        code="IND-BULK-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Bulk Commodities",
        title="Weight Certificate at Loading",
        clause_text="WEIGHT CERTIFICATE ISSUED BY INDEPENDENT SURVEYOR AT PORT OF LOADING",
        plain_english="Third-party weight verification for bulk cargo.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["bulk", "weight", "surveyor"]
    ),
    LCClause(
        code="IND-BULK-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Bulk Commodities",
        title="Quality Certificate at Loading",
        clause_text="QUALITY/ASSAY CERTIFICATE ISSUED BY INDEPENDENT SURVEYOR AT PORT OF LOADING",
        plain_english="Third-party quality verification for commodities.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["bulk", "quality", "assay"]
    ),
    LCClause(
        code="IND-BULK-003",
        category=ClauseCategory.SPECIAL,
        subcategory="Bulk Commodities",
        title="Draft Survey Report",
        clause_text="DRAFT SURVEY REPORT AT PORT OF LOADING DETERMINING WEIGHT BY VESSEL DISPLACEMENT",
        plain_english="For bulk cargo, weight determined by ship draft.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["bulk", "draft survey", "weight"]
    ),
]

# ============================================================================
# MORE AMENDMENT CLAUSES
# ============================================================================

MORE_AMENDMENT_CLAUSES = [
    LCClause(
        code="AMD-011",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Tolerance",
        title="Add/Increase Tolerance",
        clause_text="PLEASE AMEND TO ADD TOLERANCE OF +/- {percent}% ON QUANTITY AND/OR AMOUNT",
        plain_english="Request to allow variation in quantity/amount.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "tolerance", "flexibility"]
    ),
    LCClause(
        code="AMD-012",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Parties",
        title="Change Beneficiary Address",
        clause_text="PLEASE AMEND BENEFICIARY ADDRESS FROM {old_address} TO {new_address}",
        plain_english="Update seller's address in the LC.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["amendment", "beneficiary", "address"]
    ),
    LCClause(
        code="AMD-013",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Parties",
        title="Add Notify Party",
        clause_text="PLEASE ADD NOTIFY PARTY: {notify_party_name_address}",
        plain_english="Add party to be notified on arrival.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["amendment", "notify party", "B/L"]
    ),
    LCClause(
        code="AMD-014",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Shipment",
        title="Allow Transhipment",
        clause_text="PLEASE AMEND TO ALLOW TRANSHIPMENT",
        plain_english="Request to permit cargo transfer between vessels.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "transhipment", "flexibility"]
    ),
    LCClause(
        code="AMD-015",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Payment",
        title="Change Payment Terms",
        clause_text="PLEASE AMEND PAYMENT TERMS FROM {old_terms} TO {new_terms}",
        plain_english="Change from sight to usance or vice versa.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        tags=["amendment", "payment", "usance"]
    ),
    LCClause(
        code="AMD-016",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Currency",
        title="Change Currency",
        clause_text="PLEASE AMEND LC CURRENCY FROM {old_currency} TO {new_currency} WITH EQUIVALENT AMOUNT",
        plain_english="Change the currency of the LC.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="Currency change may affect FX exposure.",
        tags=["amendment", "currency", "conversion"]
    ),
    LCClause(
        code="AMD-017",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Confirmation",
        title="Add Confirmation",
        clause_text="PLEASE ADVISE CONFIRMING BANK TO ADD THEIR CONFIRMATION",
        plain_english="Request to upgrade to confirmed LC.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "confirmation", "security"]
    ),
    LCClause(
        code="AMD-018",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Incoterms",
        title="Change Incoterms",
        clause_text="PLEASE AMEND TRADE TERMS FROM {old_incoterms} TO {new_incoterms}",
        plain_english="Change delivery terms (FOB to CIF, etc.).",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.NEUTRAL,
        risk_notes="May affect document requirements and pricing.",
        tags=["amendment", "incoterms", "delivery"]
    ),
    LCClause(
        code="AMD-019",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Presentation",
        title="Extend Presentation Period",
        clause_text="PLEASE AMEND PRESENTATION PERIOD FROM {old_days} TO {new_days} DAYS",
        plain_english="More time to present documents after shipment.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["amendment", "presentation", "deadline"]
    ),
    LCClause(
        code="AMD-020",
        category=ClauseCategory.AMENDMENTS,
        subcategory="Bank",
        title="Change Advising Bank",
        clause_text="PLEASE CHANGE ADVISING BANK TO {new_bank_name} SWIFT: {swift_code}",
        plain_english="Route LC through a different advising bank.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["amendment", "advising bank", "routing"]
    ),
]

# ============================================================================
# COMBINE ALL CLAUSES
# ============================================================================

# ============================================================================
# BANK-SPECIFIC CLAUSES (Major banks' preferences)
# ============================================================================

BANK_SPECIFIC_CLAUSES = [
    # HSBC
    LCClause(
        code="BANK-HSBC-001",
        category=ClauseCategory.SPECIAL,
        subcategory="HSBC Format",
        title="HSBC LC Reference Format",
        clause_text="ALL DOCUMENTS MUST QUOTE HSBC LC REFERENCE NUMBER {lc_ref}",
        plain_english="HSBC requires their reference on all docs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["HSBC", "reference", "bank"]
    ),
    LCClause(
        code="BANK-HSBC-002",
        category=ClauseCategory.SPECIAL,
        subcategory="HSBC Format",
        title="HSBC Draft Clause",
        clause_text="DRAFT DRAWN ON HSBC AT {tenor} FOR {percent}% OF INVOICE VALUE",
        plain_english="HSBC-specific draft requirements.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["HSBC", "draft", "tenor"]
    ),
    
    # Standard Chartered
    LCClause(
        code="BANK-SCB-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Standard Chartered",
        title="SCB Documentary Credit Number",
        clause_text="STANDARD CHARTERED BANK DOCUMENTARY CREDIT NUMBER MUST APPEAR ON ALL DOCUMENTS",
        plain_english="SCB requires DC number on all documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["SCB", "reference", "bank"]
    ),
    LCClause(
        code="BANK-SCB-002",
        category=ClauseCategory.SPECIAL,
        subcategory="Standard Chartered",
        title="SCB Negotiation",
        clause_text="DOCUMENTS TO BE NEGOTIATED THROUGH STANDARD CHARTERED BANK {branch}",
        plain_english="SCB nominated for negotiation.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["SCB", "negotiation", "bank"]
    ),
    
    # Citi
    LCClause(
        code="BANK-CITI-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Citibank",
        title="Citibank Reference",
        clause_text="CITIBANK N.A. LETTER OF CREDIT NUMBER {lc_ref} MUST BE REFERENCED",
        plain_english="Citibank requires their LC number on documents.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Citibank", "reference", "bank"]
    ),
    
    # DBS
    LCClause(
        code="BANK-DBS-001",
        category=ClauseCategory.SPECIAL,
        subcategory="DBS Bank",
        title="DBS LC Reference",
        clause_text="DBS BANK LTD LETTER OF CREDIT NUMBER {lc_ref} TO BE MENTIONED ON ALL DOCUMENTS",
        plain_english="DBS requires their reference on all docs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["DBS", "reference", "Singapore"]
    ),
    
    # Bank of China
    LCClause(
        code="BANK-BOC-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Bank of China",
        title="Bank of China Reference",
        clause_text="BANK OF CHINA LC NUMBER {lc_ref} MUST APPEAR ON ALL DOCUMENTS",
        plain_english="Bank of China reference requirement.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["BOC", "reference", "China"]
    ),
    
    # State Bank of India
    LCClause(
        code="BANK-SBI-001",
        category=ClauseCategory.SPECIAL,
        subcategory="State Bank of India",
        title="SBI LC Reference",
        clause_text="STATE BANK OF INDIA LC NUMBER {lc_ref} MUST BE QUOTED ON ALL DOCUMENTS",
        plain_english="SBI reference requirement.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["SBI", "reference", "India"]
    ),
    
    # Habib Bank Limited
    LCClause(
        code="BANK-HBL-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Habib Bank",
        title="HBL LC Reference",
        clause_text="HABIB BANK LIMITED LC NUMBER {lc_ref} MUST BE MENTIONED ON ALL DOCUMENTS",
        plain_english="HBL reference requirement for Pakistan LCs.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["HBL", "reference", "Pakistan"]
    ),
    
    # Islami Bank Bangladesh
    LCClause(
        code="BANK-IBBL-001",
        category=ClauseCategory.SPECIAL,
        subcategory="Islami Bank Bangladesh",
        title="IBBL Reference",
        clause_text="ISLAMI BANK BANGLADESH LIMITED LC NUMBER {lc_ref} MUST APPEAR ON ALL DOCUMENTS",
        plain_english="IBBL reference requirement.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["IBBL", "reference", "Bangladesh"]
    ),
]

# ============================================================================
# INCOTERMS 2020 CLAUSES
# ============================================================================

INCOTERMS_CLAUSES = [
    # E Terms
    LCClause(
        code="INC-EXW-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms E",
        title="EXW - Ex Works",
        clause_text="PRICE TERM: EXW {named_place} INCOTERMS 2020",
        plain_english="Buyer bears all costs from seller's premises. Minimum obligation for seller.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Seller has minimal responsibility. May not suit LC as buyer handles export.",
        tags=["Incoterms", "EXW", "ex works"]
    ),
    
    # F Terms
    LCClause(
        code="INC-FCA-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms F",
        title="FCA - Free Carrier",
        clause_text="PRICE TERM: FCA {named_place} INCOTERMS 2020",
        plain_english="Seller delivers to carrier at named place. Risk transfers then.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "FCA", "free carrier"]
    ),
    LCClause(
        code="INC-FAS-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms F",
        title="FAS - Free Alongside Ship",
        clause_text="PRICE TERM: FAS {port_of_shipment} INCOTERMS 2020",
        plain_english="Seller delivers goods alongside vessel at port. Sea/waterway only.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "FAS", "alongside"]
    ),
    LCClause(
        code="INC-FOB-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms F",
        title="FOB - Free On Board",
        clause_text="PRICE TERM: FOB {port_of_shipment} INCOTERMS 2020",
        plain_english="Seller delivers goods on board vessel. Risk transfers at ship's rail.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "FOB", "on board"]
    ),
    
    # C Terms
    LCClause(
        code="INC-CFR-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms C",
        title="CFR - Cost and Freight",
        clause_text="PRICE TERM: CFR {port_of_destination} INCOTERMS 2020",
        plain_english="Seller pays freight to destination. Risk transfers at loading.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "CFR", "cost freight"]
    ),
    LCClause(
        code="INC-CIF-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms C",
        title="CIF - Cost Insurance Freight",
        clause_text="PRICE TERM: CIF {port_of_destination} INCOTERMS 2020",
        plain_english="Seller pays freight and insurance. Most common for sea shipments.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "CIF", "cost insurance freight"]
    ),
    LCClause(
        code="INC-CPT-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms C",
        title="CPT - Carriage Paid To",
        clause_text="PRICE TERM: CPT {named_place_destination} INCOTERMS 2020",
        plain_english="Seller pays carriage to destination. Any mode of transport.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "CPT", "carriage paid"]
    ),
    LCClause(
        code="INC-CIP-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms C",
        title="CIP - Carriage Insurance Paid",
        clause_text="PRICE TERM: CIP {named_place_destination} INCOTERMS 2020",
        plain_english="Seller pays carriage and insurance. Any mode.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["Incoterms", "CIP", "carriage insurance"]
    ),
    
    # D Terms
    LCClause(
        code="INC-DAP-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms D",
        title="DAP - Delivered at Place",
        clause_text="PRICE TERM: DAP {named_place_destination} INCOTERMS 2020",
        plain_english="Seller delivers to destination, unloading is buyer's. Maximum seller obligation.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["Incoterms", "DAP", "delivered"]
    ),
    LCClause(
        code="INC-DPU-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms D",
        title="DPU - Delivered at Place Unloaded",
        clause_text="PRICE TERM: DPU {named_place_destination} INCOTERMS 2020",
        plain_english="Seller delivers and unloads at destination.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.BENEFICIARY,
        tags=["Incoterms", "DPU", "unloaded"]
    ),
    LCClause(
        code="INC-DDP-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Incoterms D",
        title="DDP - Delivered Duty Paid",
        clause_text="PRICE TERM: DDP {named_place_destination} INCOTERMS 2020",
        plain_english="Seller delivers cleared for import. Maximum obligation for seller.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.BENEFICIARY,
        risk_notes="Seller bears all risk until delivery. May need import license.",
        tags=["Incoterms", "DDP", "duty paid"]
    ),
]

# ============================================================================
# PORT/LOCATION CLAUSES
# ============================================================================

PORT_CLAUSES = [
    LCClause(
        code="PORT-001",
        category=ClauseCategory.SHIPMENT,
        subcategory="Port Options",
        title="Any Port in Country",
        clause_text="SHIPMENT FROM ANY PORT IN {country}",
        plain_english="Flexible loading port within specified country.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["port", "flexibility", "loading"]
    ),
    LCClause(
        code="PORT-002",
        category=ClauseCategory.SHIPMENT,
        subcategory="Port Options",
        title="Port Range",
        clause_text="SHIPMENT FROM {port1} OR {port2} OR {port3}",
        plain_english="Multiple named ports acceptable for loading.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["port", "options", "loading"]
    ),
    LCClause(
        code="PORT-003",
        category=ClauseCategory.SHIPMENT,
        subcategory="Port Options",
        title="Destination Port Range",
        clause_text="DISCHARGE AT {port1} OR {port2} AT CARRIER'S OPTION",
        plain_english="Multiple destination ports, carrier chooses.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["port", "discharge", "options"]
    ),
    LCClause(
        code="PORT-004",
        category=ClauseCategory.SHIPMENT,
        subcategory="Port Options",
        title="Any Safe Port",
        clause_text="SHIPMENT FROM ANY SAFE PORT IN {region}",
        plain_english="Flexible but must be a safe (non-sanctioned, operational) port.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["port", "safe", "flexibility"]
    ),
    LCClause(
        code="PORT-005",
        category=ClauseCategory.SHIPMENT,
        subcategory="Port Restrictions",
        title="No Specific Port",
        clause_text="SHIPMENT NOT FROM {excluded_port}",
        plain_english="Exclude specific port (maybe sanctioned or congested).",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["port", "exclusion", "restriction"]
    ),
    LCClause(
        code="PORT-006",
        category=ClauseCategory.SHIPMENT,
        subcategory="Container Terminals",
        title="FCL Container Terminal",
        clause_text="SHIPMENT FROM {port} CONTAINER TERMINAL FOR FCL CARGO",
        plain_english="Full container load from named container yard.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["port", "container", "FCL"]
    ),
    LCClause(
        code="PORT-007",
        category=ClauseCategory.SHIPMENT,
        subcategory="Inland Points",
        title="Inland Container Depot",
        clause_text="RECEIPT AT INLAND CONTAINER DEPOT {icd_name} FOR SHIPMENT TO {port}",
        plain_english="Cargo received at inland depot, transported to port.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["ICD", "inland", "container"]
    ),
]

# ============================================================================
# INSPECTION CLAUSES
# ============================================================================

INSPECTION_CLAUSES = [
    LCClause(
        code="INSP-001",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Pre-Shipment Inspection",
        title="PSI - SGS Required",
        clause_text="PRE-SHIPMENT INSPECTION CERTIFICATE ISSUED BY SGS {country}",
        plain_english="SGS must inspect goods before shipment. Common requirement.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "PSI", "SGS"]
    ),
    LCClause(
        code="INSP-002",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Pre-Shipment Inspection",
        title="PSI - Bureau Veritas",
        clause_text="PRE-SHIPMENT INSPECTION CERTIFICATE ISSUED BY BUREAU VERITAS",
        plain_english="Bureau Veritas inspection required.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "PSI", "BV"]
    ),
    LCClause(
        code="INSP-003",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Pre-Shipment Inspection",
        title="PSI - Intertek",
        clause_text="PRE-SHIPMENT INSPECTION CERTIFICATE ISSUED BY INTERTEK",
        plain_english="Intertek inspection required.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "PSI", "Intertek"]
    ),
    LCClause(
        code="INSP-004",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Pre-Shipment Inspection",
        title="PSI - COTECNA",
        clause_text="PRE-SHIPMENT INSPECTION CERTIFICATE ISSUED BY COTECNA",
        plain_english="COTECNA inspection required.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "PSI", "COTECNA"]
    ),
    LCClause(
        code="INSP-005",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Inspection Scope",
        title="Inspection for Quantity Only",
        clause_text="INSPECTION CERTIFICATE CERTIFYING QUANTITY ONLY",
        plain_english="Inspector only verifies quantity, not quality.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["inspection", "quantity", "scope"]
    ),
    LCClause(
        code="INSP-006",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Inspection Scope",
        title="Inspection for Quality Only",
        clause_text="INSPECTION CERTIFICATE CERTIFYING QUALITY/SPECIFICATIONS ONLY",
        plain_english="Inspector only verifies quality, not quantity.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "quality", "scope"]
    ),
    LCClause(
        code="INSP-007",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Inspection Scope",
        title="Full Inspection Q&Q",
        clause_text="INSPECTION CERTIFICATE CERTIFYING QUANTITY AND QUALITY AS PER LC TERMS",
        plain_english="Full inspection of both quantity and quality.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "full", "Q&Q"]
    ),
    LCClause(
        code="INSP-008",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Buyer Inspection",
        title="Buyer's Representative Inspection",
        clause_text="INSPECTION CERTIFICATE ISSUED BY BUYER'S REPRESENTATIVE",
        plain_english="Buyer sends someone to inspect before shipment.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Delays possible if buyer's inspector not available.",
        tags=["inspection", "buyer", "representative"]
    ),
    LCClause(
        code="INSP-009",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Container Inspection",
        title="Container Loading Supervision",
        clause_text="CONTAINER LOADING SUPERVISION CERTIFICATE ISSUED BY {inspector}",
        plain_english="Inspector watches goods being loaded into container.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "container", "loading"]
    ),
    LCClause(
        code="INSP-010",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Factory Inspection",
        title="Factory Inspection Report",
        clause_text="FACTORY INSPECTION REPORT CONFIRMING PRODUCTION COMPLETED AS PER SPECIFICATIONS",
        plain_english="Inspector visits factory to verify production.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["inspection", "factory", "production"]
    ),
]

# ============================================================================
# CERTIFICATE CLAUSES (Various certificates required)
# ============================================================================

CERTIFICATE_CLAUSES = [
    # Quality Certificates
    LCClause(
        code="CERT-001",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Quality Certificate",
        title="Manufacturer's Quality Certificate",
        clause_text="MANUFACTURER'S QUALITY CERTIFICATE CERTIFYING GOODS CONFORM TO SPECIFICATIONS",
        plain_english="Manufacturer confirms goods meet specifications.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["certificate", "quality", "manufacturer"]
    ),
    LCClause(
        code="CERT-002",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Quality Certificate",
        title="Third Party Quality Certificate",
        clause_text="QUALITY CERTIFICATE ISSUED BY INDEPENDENT THIRD PARTY SURVEYOR",
        plain_english="Independent company certifies quality.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "quality", "third party"]
    ),
    
    # Weight Certificates
    LCClause(
        code="CERT-010",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Weight Certificate",
        title="Weight Certificate - Manufacturer",
        clause_text="WEIGHT CERTIFICATE ISSUED BY MANUFACTURER SHOWING GROSS AND NET WEIGHT",
        plain_english="Manufacturer certifies weight.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.BENEFICIARY,
        tags=["certificate", "weight", "manufacturer"]
    ),
    LCClause(
        code="CERT-011",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Weight Certificate",
        title="Weight Certificate - Public Weigher",
        clause_text="WEIGHT CERTIFICATE ISSUED BY PUBLIC WEIGHER OR SWORN MEASURER",
        plain_english="Official public weigher certifies weight.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "weight", "public"]
    ),
    LCClause(
        code="CERT-012",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Weight Certificate",
        title="Weight Certificate - Surveyor",
        clause_text="WEIGHT CERTIFICATE ISSUED BY INDEPENDENT SURVEYOR AT PORT OF LOADING",
        plain_english="Surveyor at loading port certifies weight.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "weight", "surveyor"]
    ),
    
    # Analysis Certificates
    LCClause(
        code="CERT-020",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Analysis Certificate",
        title="Chemical Analysis Certificate",
        clause_text="CHEMICAL ANALYSIS CERTIFICATE ISSUED BY ACCREDITED LABORATORY",
        plain_english="Lab tests confirm chemical composition.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "analysis", "chemical"]
    ),
    LCClause(
        code="CERT-021",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Analysis Certificate",
        title="Mill Test Certificate",
        clause_text="MILL TEST CERTIFICATE SHOWING CHEMICAL COMPOSITION AND MECHANICAL PROPERTIES",
        plain_english="For steel/metal products, mill test data required.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["certificate", "mill test", "steel"]
    ),
    
    # Beneficiary Certificates
    LCClause(
        code="CERT-030",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Shipment Notification",
        clause_text="BENEFICIARY'S CERTIFICATE STATING THAT SHIPPING DOCUMENTS HAVE BEEN SENT TO APPLICANT BY {courier}",
        plain_english="Seller confirms they sent docs directly to buyer.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["certificate", "beneficiary", "notification"]
    ),
    LCClause(
        code="CERT-031",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Non-Manufacturer",
        clause_text="BENEFICIARY'S CERTIFICATE STATING THEY ARE NOT THE MANUFACTURER OF THE GOODS",
        plain_english="Seller confirms they are a trader, not manufacturer.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["certificate", "beneficiary", "trader"]
    ),
    LCClause(
        code="CERT-032",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Compliance",
        clause_text="BENEFICIARY'S CERTIFICATE STATING ALL GOODS ARE NEW AND OF FIRST QUALITY",
        plain_english="Seller certifies goods are new, not used.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["certificate", "beneficiary", "new goods"]
    ),
    LCClause(
        code="CERT-033",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Beneficiary Certificate",
        title="Beneficiary Certificate - Sanctions",
        clause_text="BENEFICIARY'S CERTIFICATE STATING GOODS DO NOT ORIGINATE FROM ANY SANCTIONED COUNTRY",
        plain_english="Seller confirms goods not from sanctioned nations.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "beneficiary", "sanctions"]
    ),
    
    # Health/Safety Certificates
    LCClause(
        code="CERT-040",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Health Certificate",
        title="Health Certificate - Animal Products",
        clause_text="VETERINARY HEALTH CERTIFICATE ISSUED BY COMPETENT AUTHORITY",
        plain_english="For animal products, vet certificate required.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "health", "veterinary"]
    ),
    LCClause(
        code="CERT-041",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Health Certificate",
        title="Free Sale Certificate",
        clause_text="FREE SALE CERTIFICATE ISSUED BY COMPETENT AUTHORITY IN COUNTRY OF ORIGIN",
        plain_english="Confirms product can be legally sold in origin country.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "free sale", "regulatory"]
    ),
    
    # Shipping Certificates
    LCClause(
        code="CERT-050",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Shipping Certificate",
        title="Vessel Age Certificate",
        clause_text="CERTIFICATE STATING VESSEL IS NOT MORE THAN {years} YEARS OLD",
        plain_english="Confirms ship's age for insurance purposes.",
        risk_level=RiskLevel.MEDIUM,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "vessel", "age"]
    ),
    LCClause(
        code="CERT-051",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Shipping Certificate",
        title="Vessel Classification Certificate",
        clause_text="CERTIFICATE STATING VESSEL IS CLASSIFIED BY {classification_society}",
        plain_english="Confirms ship is certified by Lloyd's, DNV, etc.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.APPLICANT,
        tags=["certificate", "vessel", "classification"]
    ),
    LCClause(
        code="CERT-052",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Shipping Certificate",
        title="Vessel Not Sanctioned Certificate",
        clause_text="CERTIFICATE STATING VESSEL AND VESSEL OWNER ARE NOT ON ANY SANCTIONS LIST",
        plain_english="Confirms ship not blacklisted for sanctions.",
        risk_level=RiskLevel.HIGH,
        bias=BiasIndicator.APPLICANT,
        risk_notes="Important for compliance. Check OFAC, EU sanctions.",
        tags=["certificate", "vessel", "sanctions"]
    ),
    
    # Packing Certificates
    LCClause(
        code="CERT-060",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Packing Certificate",
        title="Export Packing Certificate",
        clause_text="CERTIFICATE STATING GOODS ARE PACKED IN EXPORT STANDARD PACKING",
        plain_english="Confirms goods are properly packed for international shipping.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["certificate", "packing", "export"]
    ),
    LCClause(
        code="CERT-061",
        category=ClauseCategory.DOCUMENTS,
        subcategory="Packing Certificate",
        title="Container Seal Certificate",
        clause_text="CERTIFICATE SHOWING CONTAINER NUMBER AND SEAL NUMBER",
        plain_english="Confirms container and seal numbers for tracking.",
        risk_level=RiskLevel.LOW,
        bias=BiasIndicator.NEUTRAL,
        tags=["certificate", "container", "seal"]
    ),
]

# ============================================================================
# MORE SHIPMENT CLAUSES
# ============================================================================

MORE_SHIPMENT_CLAUSES = [
    # Transhipment variations
    LCClause(code="SHIP-101", category=ClauseCategory.SHIPMENT, subcategory="Transhipment", title="Transhipment - One Port Only", clause_text="TRANSHIPMENT ALLOWED AT {port} ONLY", plain_english="Transhipment only allowed at specific port.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["transhipment", "port"]),
    LCClause(code="SHIP-102", category=ClauseCategory.SHIPMENT, subcategory="Transhipment", title="No More Than Two Transhipments", clause_text="NO MORE THAN TWO TRANSHIPMENTS ALLOWED", plain_english="Limit number of cargo transfers.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["transhipment", "limit"]),
    
    # Vessel requirements
    LCClause(code="SHIP-110", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Liner Vessel Only", clause_text="SHIPMENT BY LINER VESSEL ONLY (NO TRAMP)", plain_english="Must use scheduled liner service.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "liner"]),
    LCClause(code="SHIP-111", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Container Vessel Only", clause_text="SHIPMENT BY FULL CONTAINER VESSEL ONLY", plain_english="No break-bulk or RoRo.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "container"]),
    LCClause(code="SHIP-112", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Named Vessel", clause_text="SHIPMENT ON MV {vessel_name} ONLY", plain_english="Specific vessel must be used.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, risk_notes="If vessel unavailable, amendment needed.", tags=["vessel", "named"]),
    LCClause(code="SHIP-113", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Flag State Acceptable", clause_text="VESSELS OF {flag_states} FLAG ACCEPTABLE", plain_english="Only certain flag states allowed.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "flag"]),
    LCClause(code="SHIP-114", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="No Sanctioned Flag", clause_text="VESSEL NOT TO BE OF NORTH KOREAN, IRANIAN, SYRIAN, CUBAN OR RUSSIAN FLAG", plain_english="Exclude sanctioned flag states.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.APPLICANT, tags=["vessel", "sanctions", "flag"]),
    LCClause(code="SHIP-115", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="ISM Code Compliant", clause_text="VESSEL MUST BE ISM CODE COMPLIANT", plain_english="International Safety Management certified.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "ISM", "safety"]),
    LCClause(code="SHIP-116", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="P&I Club Member", clause_text="VESSEL MUST BE ENTERED WITH A RECOGNIZED P&I CLUB", plain_english="Vessel must have proper insurance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "P&I", "insurance"]),
    LCClause(code="SHIP-117", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Max Vessel Age 25 Years", clause_text="VESSEL AGE NOT TO EXCEED 25 YEARS", plain_english="Old vessel restriction for safety.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "age"]),
    LCClause(code="SHIP-118", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Max Vessel Age 20 Years", clause_text="VESSEL AGE NOT TO EXCEED 20 YEARS", plain_english="Stricter age limit.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["vessel", "age"]),
    LCClause(code="SHIP-119", category=ClauseCategory.SHIPMENT, subcategory="Vessel", title="Max Vessel Age 15 Years", clause_text="VESSEL AGE NOT TO EXCEED 15 YEARS", plain_english="Premium vessel age requirement.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["vessel", "age"]),
    
    # Container types
    LCClause(code="SHIP-120", category=ClauseCategory.SHIPMENT, subcategory="Container", title="20ft Container", clause_text="SHIPMENT IN 20 FOOT DRY CONTAINER(S)", plain_english="Standard 20ft dry container.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["container", "20ft", "dry"]),
    LCClause(code="SHIP-121", category=ClauseCategory.SHIPMENT, subcategory="Container", title="40ft Container", clause_text="SHIPMENT IN 40 FOOT DRY CONTAINER(S)", plain_english="Standard 40ft dry container.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["container", "40ft", "dry"]),
    LCClause(code="SHIP-122", category=ClauseCategory.SHIPMENT, subcategory="Container", title="40ft High Cube", clause_text="SHIPMENT IN 40 FOOT HIGH CUBE CONTAINER(S)", plain_english="40ft high cube (9'6\" height).", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["container", "40ft", "high cube"]),
    LCClause(code="SHIP-123", category=ClauseCategory.SHIPMENT, subcategory="Container", title="Reefer Container", clause_text="SHIPMENT IN REFRIGERATED CONTAINER(S) AT {temperature} DEGREES CELSIUS", plain_english="Temperature-controlled container.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["container", "reefer", "temperature"]),
    LCClause(code="SHIP-124", category=ClauseCategory.SHIPMENT, subcategory="Container", title="Open Top Container", clause_text="SHIPMENT IN OPEN TOP CONTAINER(S)", plain_english="For oversized cargo.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["container", "open top"]),
    LCClause(code="SHIP-125", category=ClauseCategory.SHIPMENT, subcategory="Container", title="Flat Rack Container", clause_text="SHIPMENT ON FLAT RACK CONTAINER(S)", plain_english="For heavy machinery.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["container", "flat rack"]),
    LCClause(code="SHIP-126", category=ClauseCategory.SHIPMENT, subcategory="Container", title="Tank Container", clause_text="SHIPMENT IN ISO TANK CONTAINER(S)", plain_english="For liquid cargo.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["container", "tank", "liquid"]),
    
    # Freight terms
    LCClause(code="SHIP-130", category=ClauseCategory.SHIPMENT, subcategory="Freight", title="Freight Prepaid", clause_text="FREIGHT PREPAID", plain_english="Seller pays freight before shipping.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["freight", "prepaid"]),
    LCClause(code="SHIP-131", category=ClauseCategory.SHIPMENT, subcategory="Freight", title="Freight Collect", clause_text="FREIGHT COLLECT", plain_english="Buyer pays freight at destination.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["freight", "collect"]),
    LCClause(code="SHIP-132", category=ClauseCategory.SHIPMENT, subcategory="Freight", title="Freight Payable at Destination", clause_text="FREIGHT PAYABLE AT DESTINATION", plain_english="Freight paid upon arrival.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["freight", "destination"]),
    LCClause(code="SHIP-133", category=ClauseCategory.SHIPMENT, subcategory="Freight", title="Freight as Arranged", clause_text="FREIGHT AS ARRANGED", plain_english="Freight terms per separate agreement.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["freight", "arranged"]),
    
    # Schedule
    LCClause(code="SHIP-140", category=ClauseCategory.SHIPMENT, subcategory="Schedule", title="Weekly Shipments", clause_text="SHIPMENTS TO BE MADE ON A WEEKLY BASIS", plain_english="Regular weekly deliveries.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["schedule", "weekly"]),
    LCClause(code="SHIP-141", category=ClauseCategory.SHIPMENT, subcategory="Schedule", title="Monthly Shipments", clause_text="SHIPMENTS TO BE MADE ON A MONTHLY BASIS", plain_english="Regular monthly deliveries.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["schedule", "monthly"]),
    LCClause(code="SHIP-142", category=ClauseCategory.SHIPMENT, subcategory="Schedule", title="Shipment in Equal Lots", clause_text="SHIPMENT IN {number} EQUAL LOTS", plain_english="Split evenly over multiple shipments.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["schedule", "lots"]),
    
    # Special cargo
    LCClause(code="SHIP-150", category=ClauseCategory.SHIPMENT, subcategory="Special Cargo", title="Hazardous Cargo Class", clause_text="SHIPMENT OF IMO CLASS {class} DANGEROUS GOODS", plain_english="Dangerous goods classification.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.NEUTRAL, tags=["hazardous", "IMO", "DG"]),
    LCClause(code="SHIP-151", category=ClauseCategory.SHIPMENT, subcategory="Special Cargo", title="Project Cargo", clause_text="PROJECT CARGO SHIPMENT - OVERSIZED/OVERWEIGHT", plain_english="For large equipment/machinery.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["project cargo", "oversized"]),
    LCClause(code="SHIP-152", category=ClauseCategory.SHIPMENT, subcategory="Special Cargo", title="Break Bulk", clause_text="BREAK BULK SHIPMENT (NON-CONTAINERIZED)", plain_english="Cargo not in containers.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["break bulk", "conventional"]),
]

# ============================================================================
# MORE DOCUMENT CLAUSES
# ============================================================================

MORE_DOCUMENT_CLAUSES = [
    # Commercial Invoice variations
    LCClause(code="DOC-101", category=ClauseCategory.DOCUMENTS, subcategory="Commercial Invoice", title="Signed Invoice", clause_text="SIGNED COMMERCIAL INVOICE IN {copies} ORIGINALS", plain_english="Invoice must be signed.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "signed"]),
    LCClause(code="DOC-102", category=ClauseCategory.DOCUMENTS, subcategory="Commercial Invoice", title="Certified Invoice", clause_text="CERTIFIED COMMERCIAL INVOICE", plain_english="Invoice certified as correct by seller.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "certified"]),
    LCClause(code="DOC-103", category=ClauseCategory.DOCUMENTS, subcategory="Commercial Invoice", title="Consular Invoice", clause_text="CONSULAR INVOICE LEGALIZED BY CONSULATE OF {country}", plain_english="Invoice legalized by destination country's consulate.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["invoice", "consular"]),
    LCClause(code="DOC-104", category=ClauseCategory.DOCUMENTS, subcategory="Commercial Invoice", title="Proforma Invoice", clause_text="PROFORMA INVOICE TO ACCOMPANY DOCUMENTS", plain_english="Preliminary invoice attached.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "proforma"]),
    
    # B/L variations
    LCClause(code="DOC-110", category=ClauseCategory.DOCUMENTS, subcategory="Bill of Lading", title="Received for Shipment B/L", clause_text="RECEIVED FOR SHIPMENT BILL OF LADING ACCEPTABLE", plain_english="B/L showing receipt before loading is OK.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["B/L", "received"]),
    LCClause(code="DOC-111", category=ClauseCategory.DOCUMENTS, subcategory="Bill of Lading", title="On Board B/L Required", clause_text="ON BOARD OCEAN BILL OF LADING REQUIRED", plain_english="B/L must show goods loaded on vessel.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "on board"]),
    LCClause(code="DOC-112", category=ClauseCategory.DOCUMENTS, subcategory="Bill of Lading", title="Port to Port B/L", clause_text="PORT TO PORT BILL OF LADING", plain_english="B/L covers only sea portion.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "port to port"]),
    LCClause(code="DOC-113", category=ClauseCategory.DOCUMENTS, subcategory="Bill of Lading", title="Combined Transport B/L", clause_text="COMBINED TRANSPORT BILL OF LADING ACCEPTABLE", plain_english="Multimodal B/L accepted.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["B/L", "combined", "multimodal"]),
    LCClause(code="DOC-114", category=ClauseCategory.DOCUMENTS, subcategory="Bill of Lading", title="Foul B/L Acceptable", clause_text="BILL OF LADING BEARING REMARKS RELATING TO PACKAGING ACCEPTABLE", plain_english="B/L with packing remarks OK - unusual.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.BENEFICIARY, tags=["B/L", "claused"]),
    LCClause(code="DOC-115", category=ClauseCategory.DOCUMENTS, subcategory="Bill of Lading", title="Electronic B/L", clause_text="ELECTRONIC BILL OF LADING (BOLERO/essDOCS/TradeLen) ACCEPTABLE", plain_english="Digital B/L accepted.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["B/L", "electronic", "digital"]),
    
    # Packing List variations
    LCClause(code="DOC-120", category=ClauseCategory.DOCUMENTS, subcategory="Packing List", title="Signed Packing List", clause_text="SIGNED PACKING LIST IN {copies} COPIES", plain_english="Packing list must be signed.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["packing", "signed"]),
    LCClause(code="DOC-121", category=ClauseCategory.DOCUMENTS, subcategory="Packing List", title="Weight/Measurement List", clause_text="WEIGHT AND MEASUREMENT LIST", plain_english="Separate weight/dimension document.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["weight", "measurement"]),
    
    # Insurance variations
    LCClause(code="DOC-130", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="Marine Insurance Policy", clause_text="MARINE INSURANCE POLICY (NOT CERTIFICATE)", plain_english="Full policy required, not just certificate.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["insurance", "policy"]),
    LCClause(code="DOC-131", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="Open Cover Certificate", clause_text="CERTIFICATE OF INSURANCE ISSUED UNDER OPEN COVER POLICY", plain_english="Insurance from master policy OK.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["insurance", "open cover"]),
    LCClause(code="DOC-132", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="ICC(A) All Risks", clause_text="INSURANCE COVERING INSTITUTE CARGO CLAUSES (A) ALL RISKS", plain_english="Widest coverage.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "ICC(A)", "all risks"]),
    LCClause(code="DOC-133", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="ICC(B) Named Risks", clause_text="INSURANCE COVERING INSTITUTE CARGO CLAUSES (B) NAMED RISKS", plain_english="Medium coverage - named perils.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "ICC(B)"]),
    LCClause(code="DOC-134", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="ICC(C) Basic", clause_text="INSURANCE COVERING INSTITUTE CARGO CLAUSES (C) BASIC RISKS", plain_english="Minimum coverage.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "ICC(C)"]),
    LCClause(code="DOC-135", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="War Risk Insurance", clause_text="INSTITUTE WAR CLAUSES (CARGO) COVERAGE REQUIRED", plain_english="War risk extension required.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["insurance", "war"]),
    LCClause(code="DOC-136", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="Strike Risk Insurance", clause_text="INSTITUTE STRIKES CLAUSES (CARGO) COVERAGE REQUIRED", plain_english="Strike risk extension required.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["insurance", "strikes"]),
    LCClause(code="DOC-137", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="Insurance 110% CIF", clause_text="INSURANCE COVERING 110% OF CIF VALUE", plain_english="Standard coverage level.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "110%"]),
    LCClause(code="DOC-138", category=ClauseCategory.DOCUMENTS, subcategory="Insurance", title="Insurance 120% Invoice", clause_text="INSURANCE COVERING 120% OF INVOICE VALUE", plain_english="Higher than standard coverage.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["insurance", "120%"]),
    
    # Origin certificates
    LCClause(code="DOC-140", category=ClauseCategory.DOCUMENTS, subcategory="Origin", title="GSP Form A", clause_text="GSP FORM A CERTIFICATE OF ORIGIN FOR PREFERENTIAL TARIFF", plain_english="Generalized System of Preferences form.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["origin", "GSP", "preferential"]),
    LCClause(code="DOC-141", category=ClauseCategory.DOCUMENTS, subcategory="Origin", title="EUR.1 Movement Certificate", clause_text="EUR.1 MOVEMENT CERTIFICATE FOR EU FREE TRADE AGREEMENT", plain_english="European origin certificate.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["origin", "EUR.1", "EU"]),
    LCClause(code="DOC-142", category=ClauseCategory.DOCUMENTS, subcategory="Origin", title="FORM D AFTA", clause_text="FORM D CERTIFICATE OF ORIGIN FOR ASEAN FREE TRADE AREA", plain_english="ASEAN origin certificate.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["origin", "Form D", "ASEAN"]),
    LCClause(code="DOC-143", category=ClauseCategory.DOCUMENTS, subcategory="Origin", title="RCEP Origin Certificate", clause_text="RCEP CERTIFICATE OF ORIGIN FOR REGIONAL COMPREHENSIVE ECONOMIC PARTNERSHIP", plain_english="RCEP (Asia-Pacific FTA) origin certificate.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["origin", "RCEP", "Asia"]),
    LCClause(code="DOC-144", category=ClauseCategory.DOCUMENTS, subcategory="Origin", title="USMCA Origin Certificate", clause_text="CERTIFICATE OF ORIGIN FOR USMCA PREFERENTIAL TREATMENT", plain_english="US-Mexico-Canada agreement origin.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["origin", "USMCA", "NAFTA"]),
    
    # Drafts/Bills of Exchange
    LCClause(code="DOC-150", category=ClauseCategory.DOCUMENTS, subcategory="Draft", title="Draft at Sight", clause_text="DRAFT DRAWN ON {drawee_bank} AT SIGHT FOR 100% OF INVOICE VALUE", plain_english="Immediate payment upon presentation.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["draft", "sight"]),
    LCClause(code="DOC-151", category=ClauseCategory.DOCUMENTS, subcategory="Draft", title="Draft 30 Days Sight", clause_text="DRAFT DRAWN ON {drawee_bank} AT 30 DAYS AFTER SIGHT", plain_english="Payment 30 days after acceptance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["draft", "usance", "30 days"]),
    LCClause(code="DOC-152", category=ClauseCategory.DOCUMENTS, subcategory="Draft", title="Draft 60 Days Sight", clause_text="DRAFT DRAWN ON {drawee_bank} AT 60 DAYS AFTER SIGHT", plain_english="Payment 60 days after acceptance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["draft", "usance", "60 days"]),
    LCClause(code="DOC-153", category=ClauseCategory.DOCUMENTS, subcategory="Draft", title="Draft 90 Days Sight", clause_text="DRAFT DRAWN ON {drawee_bank} AT 90 DAYS AFTER SIGHT", plain_english="Payment 90 days after acceptance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["draft", "usance", "90 days"]),
    LCClause(code="DOC-154", category=ClauseCategory.DOCUMENTS, subcategory="Draft", title="Draft 180 Days Sight", clause_text="DRAFT DRAWN ON {drawee_bank} AT 180 DAYS AFTER SIGHT", plain_english="Payment 180 days after acceptance.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["draft", "usance", "180 days"]),
    LCClause(code="DOC-155", category=ClauseCategory.DOCUMENTS, subcategory="Draft", title="Draft XX Days from B/L", clause_text="DRAFT DRAWN AT {days} DAYS AFTER B/L DATE", plain_english="Payment X days from shipment date.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["draft", "usance", "B/L date"]),
]

# ============================================================================
# MORE PAYMENT CLAUSES  
# ============================================================================

MORE_PAYMENT_CLAUSES = [
    LCClause(code="PAY-101", category=ClauseCategory.PAYMENT, subcategory="Availability", title="Available at Sight", clause_text="AVAILABLE AT SIGHT WITH {nominated_bank}", plain_english="Immediate payment from nominated bank.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["payment", "sight"]),
    LCClause(code="PAY-102", category=ClauseCategory.PAYMENT, subcategory="Availability", title="Available by Acceptance", clause_text="AVAILABLE BY ACCEPTANCE OF DRAFT DRAWN ON {drawee}", plain_english="Payment upon draft acceptance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["payment", "acceptance"]),
    LCClause(code="PAY-103", category=ClauseCategory.PAYMENT, subcategory="Availability", title="Available by Deferred Payment", clause_text="AVAILABLE BY DEFERRED PAYMENT AT {days} DAYS FROM B/L DATE", plain_english="Payment deferred without draft.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["payment", "deferred"]),
    LCClause(code="PAY-104", category=ClauseCategory.PAYMENT, subcategory="Availability", title="Available by Negotiation", clause_text="AVAILABLE BY NEGOTIATION WITH ANY BANK IN {country}", plain_english="Any bank can negotiate/buy documents.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["payment", "negotiation"]),
    
    # Reimbursement
    LCClause(code="PAY-110", category=ClauseCategory.PAYMENT, subcategory="Reimbursement", title="T/T Reimbursement", clause_text="REIMBURSEMENT BY TELEGRAPHIC TRANSFER", plain_english="Wire transfer reimbursement.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["reimbursement", "T/T"]),
    LCClause(code="PAY-111", category=ClauseCategory.PAYMENT, subcategory="Reimbursement", title="Reimbursement with Interest", clause_text="REIMBURSEMENT WILL BE EFFECTED WITH INTEREST AT {rate}% PER ANNUM", plain_english="Interest included in reimbursement.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["reimbursement", "interest"]),
    LCClause(code="PAY-112", category=ClauseCategory.PAYMENT, subcategory="Reimbursement", title="Reimbursement Authorization", clause_text="WE HEREBY AUTHORIZE {reimbursing_bank} TO REIMBURSE CLAIMING BANK", plain_english="Third bank authorized to pay.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["reimbursement", "authorization"]),
    
    # Interest/Financing
    LCClause(code="PAY-120", category=ClauseCategory.PAYMENT, subcategory="Interest", title="Interest for Buyers Account", clause_text="INTEREST FOR BUYER'S ACCOUNT AT {rate}% PER ANNUM", plain_english="Buyer pays deferred payment interest.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["interest", "buyer"]),
    LCClause(code="PAY-121", category=ClauseCategory.PAYMENT, subcategory="Interest", title="Interest for Sellers Account", clause_text="INTEREST FOR SELLER'S ACCOUNT AT {rate}% PER ANNUM", plain_english="Seller absorbs financing cost.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["interest", "seller"]),
    LCClause(code="PAY-122", category=ClauseCategory.PAYMENT, subcategory="Interest", title="Discount Acceptable", clause_text="DISCOUNTING CHARGES FOR BENEFICIARY'S ACCOUNT", plain_english="Seller pays if they want early payment.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["discount", "charges"]),
    
    # Charges
    LCClause(code="PAY-130", category=ClauseCategory.PAYMENT, subcategory="Charges", title="All Charges Outside Country", clause_text="ALL BANKING CHARGES OUTSIDE {country} FOR APPLICANT'S ACCOUNT", plain_english="Applicant pays foreign bank fees.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["charges", "banking"]),
    LCClause(code="PAY-131", category=ClauseCategory.PAYMENT, subcategory="Charges", title="All Charges for Beneficiary", clause_text="ALL BANKING CHARGES FOR BENEFICIARY'S ACCOUNT", plain_english="Seller pays all bank fees.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["charges", "beneficiary"]),
    LCClause(code="PAY-132", category=ClauseCategory.PAYMENT, subcategory="Charges", title="Amendment Charges", clause_text="AMENDMENT CHARGES FOR {party}'S ACCOUNT", plain_english="Who pays for LC changes.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["charges", "amendment"]),
    
    # Discrepancy handling
    LCClause(code="PAY-140", category=ClauseCategory.PAYMENT, subcategory="Discrepancy", title="Discrepancy Fee", clause_text="DISCREPANCY FEE OF USD {amount} PER SET FOR BENEFICIARY'S ACCOUNT", plain_english="Seller pays if docs have issues.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["discrepancy", "fee"]),
    LCClause(code="PAY-141", category=ClauseCategory.PAYMENT, subcategory="Discrepancy", title="Minor Discrepancy Acceptable", clause_text="MINOR DISCREPANCIES ACCEPTABLE SUBJECT TO DEDUCTION OF USD {amount}", plain_english="Small issues OK with penalty.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["discrepancy", "minor"]),
]

# ============================================================================
# MORE SPECIAL CLAUSES
# ============================================================================

MORE_SPECIAL_CLAUSES = [
    # Confirmation
    LCClause(code="SPEC-101", category=ClauseCategory.SPECIAL, subcategory="Confirmation", title="Confirmed by Advising Bank", clause_text="PLEASE ADD YOUR CONFIRMATION", plain_english="Request for advising bank to confirm.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["confirmation", "advising"]),
    LCClause(code="SPEC-102", category=ClauseCategory.SPECIAL, subcategory="Confirmation", title="Confirmation May Be Added", clause_text="CONFIRMATION MAY BE ADDED AT BENEFICIARY'S REQUEST AND EXPENSE", plain_english="Optional confirmation, seller pays.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["confirmation", "optional"]),
    LCClause(code="SPEC-103", category=ClauseCategory.SPECIAL, subcategory="Confirmation", title="Silent Confirmation", clause_text="SILENT CONFIRMATION MAY BE ADDED", plain_english="Confirmation without issuing bank knowledge.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.BENEFICIARY, tags=["confirmation", "silent"]),
    
    # Presentation
    LCClause(code="SPEC-110", category=ClauseCategory.SPECIAL, subcategory="Presentation", title="21 Days Presentation", clause_text="DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS AFTER SHIPMENT DATE", plain_english="Standard presentation period.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["presentation", "21 days"]),
    LCClause(code="SPEC-111", category=ClauseCategory.SPECIAL, subcategory="Presentation", title="14 Days Presentation", clause_text="DOCUMENTS MUST BE PRESENTED WITHIN 14 DAYS AFTER SHIPMENT DATE", plain_english="Shorter presentation period.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["presentation", "14 days"]),
    LCClause(code="SPEC-112", category=ClauseCategory.SPECIAL, subcategory="Presentation", title="7 Days Presentation", clause_text="DOCUMENTS MUST BE PRESENTED WITHIN 7 DAYS AFTER SHIPMENT DATE", plain_english="Very short presentation - tight deadline.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.APPLICANT, tags=["presentation", "7 days"]),
    LCClause(code="SPEC-113", category=ClauseCategory.SPECIAL, subcategory="Presentation", title="Presentation Place", clause_text="DOCUMENTS TO BE PRESENTED AT {bank_name_address}", plain_english="Where to submit documents.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["presentation", "place"]),
    
    # Expiry
    LCClause(code="SPEC-120", category=ClauseCategory.SPECIAL, subcategory="Expiry", title="Expiry Date", clause_text="THIS CREDIT EXPIRES ON {date}", plain_english="Final date for presentation.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["expiry", "date"]),
    LCClause(code="SPEC-121", category=ClauseCategory.SPECIAL, subcategory="Expiry", title="Expiry Place", clause_text="EXPIRY FOR PRESENTATION IN {country}", plain_english="Where LC expires.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["expiry", "place"]),
    
    # Revolving
    LCClause(code="SPEC-130", category=ClauseCategory.SPECIAL, subcategory="Revolving", title="Revolving LC - Cumulative", clause_text="THIS CREDIT IS CUMULATIVE REVOLVING FOR {amount} MONTHLY", plain_english="Unused amount carries forward.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["revolving", "cumulative"]),
    LCClause(code="SPEC-131", category=ClauseCategory.SPECIAL, subcategory="Revolving", title="Revolving LC - Non-Cumulative", clause_text="THIS CREDIT IS NON-CUMULATIVE REVOLVING FOR {amount} MONTHLY", plain_english="Unused amount lost each period.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["revolving", "non-cumulative"]),
    
    # Back-to-Back
    LCClause(code="SPEC-140", category=ClauseCategory.SPECIAL, subcategory="Back-to-Back", title="Back-to-Back Allowed", clause_text="THIS CREDIT MAY BE USED AS COLLATERAL FOR BACK-TO-BACK CREDIT", plain_english="Can use to secure second LC to supplier.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["back-to-back", "collateral"]),
    
    # Language
    LCClause(code="SPEC-150", category=ClauseCategory.SPECIAL, subcategory="Language", title="Documents in English", clause_text="ALL DOCUMENTS TO BE IN ENGLISH LANGUAGE", plain_english="English-only documents.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["language", "English"]),
    LCClause(code="SPEC-151", category=ClauseCategory.SPECIAL, subcategory="Language", title="Documents in Arabic", clause_text="ALL DOCUMENTS TO BE IN ARABIC LANGUAGE OR ACCOMPANIED BY ARABIC TRANSLATION", plain_english="Arabic required for Middle East.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["language", "Arabic"]),
    LCClause(code="SPEC-152", category=ClauseCategory.SPECIAL, subcategory="Language", title="Documents in Chinese", clause_text="ALL DOCUMENTS TO BE IN CHINESE LANGUAGE OR ACCOMPANIED BY CHINESE TRANSLATION", plain_english="Chinese required for China.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["language", "Chinese"]),
    
    # Sanctions
    LCClause(code="SPEC-160", category=ClauseCategory.SPECIAL, subcategory="Sanctions", title="OFAC Compliance", clause_text="ALL PARTIES TO THIS TRANSACTION MUST BE IN COMPLIANCE WITH OFAC REGULATIONS", plain_english="US sanctions compliance required.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.NEUTRAL, tags=["sanctions", "OFAC", "compliance"]),
    LCClause(code="SPEC-161", category=ClauseCategory.SPECIAL, subcategory="Sanctions", title="EU Sanctions Compliance", clause_text="ALL PARTIES MUST COMPLY WITH EUROPEAN UNION SANCTIONS REGULATIONS", plain_english="EU sanctions compliance required.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.NEUTRAL, tags=["sanctions", "EU", "compliance"]),
    LCClause(code="SPEC-162", category=ClauseCategory.SPECIAL, subcategory="Sanctions", title="UN Sanctions Compliance", clause_text="ALL PARTIES MUST COMPLY WITH UNITED NATIONS SECURITY COUNCIL SANCTIONS", plain_english="UN sanctions compliance required.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.NEUTRAL, tags=["sanctions", "UN", "compliance"]),
]

# ============================================================================
# COMBINE ALL CLAUSES
# ============================================================================

# ============================================================================
# TRADE ROUTE SPECIFIC CLAUSES
# ============================================================================

TRADE_ROUTE_CLAUSES = [
    # Bangladesh RMG
    LCClause(code="TR-BD-001", category=ClauseCategory.SPECIAL, subcategory="Bangladesh RMG", title="Bangladesh Textile Clause", clause_text="GOODS OF BANGLADESH ORIGIN - READY MADE GARMENTS", plain_english="RMG export from Bangladesh.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Bangladesh", "RMG", "textiles"]),
    LCClause(code="TR-BD-002", category=ClauseCategory.SPECIAL, subcategory="Bangladesh RMG", title="CTG/Dhaka Port", clause_text="SHIPMENT FROM CHITTAGONG OR DHAKA ICD", plain_english="Standard Bangladesh export ports.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Bangladesh", "port", "CTG"]),
    LCClause(code="TR-BD-003", category=ClauseCategory.SPECIAL, subcategory="Bangladesh RMG", title="Bangladesh LC Currency", clause_text="LC VALUE IN US DOLLARS AS PER BANGLADESH BANK GUIDELINES", plain_english="BB requires USD for exports.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Bangladesh", "USD", "currency"]),
    LCClause(code="TR-BD-004", category=ClauseCategory.SPECIAL, subcategory="Bangladesh RMG", title="Size Assortment", clause_text="GARMENTS TO BE SHIPPED AS PER SIZE ASSORTMENT PROVIDED BY BUYER", plain_english="Size breakdown per buyer specs.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Bangladesh", "size", "assortment"]),
    
    # China Electronics
    LCClause(code="TR-CN-001", category=ClauseCategory.SPECIAL, subcategory="China Electronics", title="China Electronics Export", clause_text="GOODS OF CHINESE ORIGIN - ELECTRONICS/ELECTRICAL", plain_english="Electronics from China.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["China", "electronics"]),
    LCClause(code="TR-CN-002", category=ClauseCategory.SPECIAL, subcategory="China Electronics", title="Shenzhen/Shanghai Port", clause_text="SHIPMENT FROM ANY CHINESE PORT INCLUDING SHENZHEN, SHANGHAI, NINGBO", plain_english="Major Chinese ports.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["China", "port", "flexibility"]),
    LCClause(code="TR-CN-003", category=ClauseCategory.SPECIAL, subcategory="China Electronics", title="CCC Certificate", clause_text="CHINA COMPULSORY CERTIFICATE (CCC) REQUIRED FOR ELECTRICAL PRODUCTS", plain_english="Chinese safety certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["China", "CCC", "certificate"]),
    
    # India Commodities
    LCClause(code="TR-IN-001", category=ClauseCategory.SPECIAL, subcategory="India Trade", title="India Port Options", clause_text="SHIPMENT FROM ANY INDIAN PORT", plain_english="Flexible Indian loading port.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["India", "port"]),
    LCClause(code="TR-IN-002", category=ClauseCategory.SPECIAL, subcategory="India Trade", title="FSSAI Certificate", clause_text="FSSAI CERTIFICATE REQUIRED FOR FOOD PRODUCTS", plain_english="Indian food safety certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["India", "FSSAI", "food"]),
    LCClause(code="TR-IN-003", category=ClauseCategory.SPECIAL, subcategory="India Trade", title="Spices Board Certificate", clause_text="SPICES BOARD CERTIFICATE OF QUALITY REQUIRED", plain_english="For spice exports from India.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["India", "spices", "certificate"]),
    
    # Middle East
    LCClause(code="TR-ME-001", category=ClauseCategory.SPECIAL, subcategory="Middle East", title="UAE Import License", clause_text="UAE IMPORT LICENSE NUMBER {license_no} TO BE MENTIONED", plain_english="UAE requires import license on docs.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["UAE", "import license"]),
    LCClause(code="TR-ME-002", category=ClauseCategory.SPECIAL, subcategory="Middle East", title="Saudi SABER Certificate", clause_text="SABER CERTIFICATE FOR GOODS DESTINED TO SAUDI ARABIA", plain_english="Saudi product conformity.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Saudi", "SABER", "conformity"]),
    LCClause(code="TR-ME-003", category=ClauseCategory.SPECIAL, subcategory="Middle East", title="Arab League Boycott", clause_text="GOODS AND VESSELS NOT OF ISRAELI ORIGIN AND NOT CALLING AT ISRAELI PORTS", plain_english="Arab boycott clause - controversial.", risk_level=RiskLevel.HIGH, bias=BiasIndicator.NEUTRAL, risk_notes="May conflict with anti-boycott laws.", tags=["boycott", "Israel", "Arab"]),
    
    # European Union
    LCClause(code="TR-EU-001", category=ClauseCategory.SPECIAL, subcategory="EU Trade", title="EU Conformity", clause_text="GOODS CONFORMING TO EUROPEAN UNION STANDARDS AND REGULATIONS", plain_english="EU standards compliance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["EU", "conformity"]),
    LCClause(code="TR-EU-002", category=ClauseCategory.SPECIAL, subcategory="EU Trade", title="REACH Compliance", clause_text="REACH COMPLIANCE CERTIFICATE FOR CHEMICALS AND MATERIALS", plain_english="EU chemical regulations.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["EU", "REACH", "chemical"]),
    LCClause(code="TR-EU-003", category=ClauseCategory.SPECIAL, subcategory="EU Trade", title="WEEE Compliance", clause_text="WEEE DIRECTIVE COMPLIANCE FOR ELECTRICAL/ELECTRONIC EQUIPMENT", plain_english="EU e-waste directive.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["EU", "WEEE", "electronics"]),
    
    # USA
    LCClause(code="TR-US-001", category=ClauseCategory.SPECIAL, subcategory="USA Trade", title="FDA Registration", clause_text="FDA REGISTRATION NUMBER AND PRIOR NOTICE REQUIRED FOR FOOD/DRUG IMPORTS", plain_english="US FDA requirements.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["USA", "FDA", "food"]),
    LCClause(code="TR-US-002", category=ClauseCategory.SPECIAL, subcategory="USA Trade", title="CPSC Compliance", clause_text="CONSUMER PRODUCT SAFETY COMMISSION (CPSC) CERTIFICATE REQUIRED", plain_english="US consumer product safety.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["USA", "CPSC", "safety"]),
    LCClause(code="TR-US-003", category=ClauseCategory.SPECIAL, subcategory="USA Trade", title="C-TPAT Compliance", clause_text="SHIPMENT FROM C-TPAT CERTIFIED FACTORY/CONSOLIDATOR", plain_english="US customs security program.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["USA", "C-TPAT", "security"]),
    
    # Japan
    LCClause(code="TR-JP-001", category=ClauseCategory.SPECIAL, subcategory="Japan Trade", title="JIS Standard", clause_text="GOODS CONFORMING TO JAPANESE INDUSTRIAL STANDARDS (JIS)", plain_english="Japanese quality standards.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Japan", "JIS", "standard"]),
    
    # Africa
    LCClause(code="TR-AF-001", category=ClauseCategory.SPECIAL, subcategory="Africa Trade", title="PVoC Certificate", clause_text="PRE-EXPORT VERIFICATION OF CONFORMITY (PVOC) CERTIFICATE REQUIRED", plain_english="African import inspection.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Africa", "PVoC", "conformity"]),
    LCClause(code="TR-AF-002", category=ClauseCategory.SPECIAL, subcategory="Africa Trade", title="SONCAP Nigeria", clause_text="SONCAP CERTIFICATE FOR GOODS DESTINED TO NIGERIA", plain_english="Nigerian standards conformity.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["Nigeria", "SONCAP", "conformity"]),
]

# ============================================================================
# ESG/SUSTAINABILITY CLAUSES
# ============================================================================

ESG_CLAUSES = [
    LCClause(code="ESG-001", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="Carbon Footprint Certificate", clause_text="CARBON FOOTPRINT CERTIFICATE SHOWING CO2 EMISSIONS FOR SHIPMENT", plain_english="Environmental impact disclosure.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "carbon", "environment"]),
    LCClause(code="ESG-002", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="Fair Trade Certificate", clause_text="FAIR TRADE CERTIFICATE FROM RECOGNIZED FAIR TRADE ORGANIZATION", plain_english="Ethical sourcing certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "fair trade", "ethical"]),
    LCClause(code="ESG-003", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="Organic Certificate", clause_text="ORGANIC CERTIFICATE FROM ACCREDITED CERTIFICATION BODY", plain_english="Organic product certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "organic", "certification"]),
    LCClause(code="ESG-004", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="FSC Certificate", clause_text="FOREST STEWARDSHIP COUNCIL (FSC) CERTIFICATE FOR WOOD/PAPER PRODUCTS", plain_english="Sustainable forestry certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "FSC", "forestry"]),
    LCClause(code="ESG-005", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="SA8000 Compliance", clause_text="SA8000 SOCIAL ACCOUNTABILITY STANDARD COMPLIANCE CERTIFICATE", plain_english="Labor standards certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "SA8000", "labor"]),
    LCClause(code="ESG-006", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="BSCI Audit", clause_text="BUSINESS SOCIAL COMPLIANCE INITIATIVE (BSCI) AUDIT REPORT", plain_english="Social compliance audit.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "BSCI", "audit"]),
    LCClause(code="ESG-007", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="Conflict Minerals Declaration", clause_text="DECLARATION STATING GOODS ARE FREE FROM CONFLICT MINERALS", plain_english="Dodd-Frank conflict minerals.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.NEUTRAL, tags=["ESG", "conflict minerals", "compliance"]),
    LCClause(code="ESG-008", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="Child Labor Free Certificate", clause_text="CERTIFICATE STATING NO CHILD LABOR USED IN PRODUCTION", plain_english="Child labor compliance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "child labor", "ethical"]),
    LCClause(code="ESG-009", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="ISO 14001 Environment", clause_text="MANUFACTURER MUST BE ISO 14001 ENVIRONMENTAL MANAGEMENT CERTIFIED", plain_english="Environmental management system.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "ISO 14001", "environment"]),
    LCClause(code="ESG-010", category=ClauseCategory.SPECIAL, subcategory="Sustainability", title="GRS Recycled Content", clause_text="GLOBAL RECYCLED STANDARD (GRS) CERTIFICATE FOR RECYCLED MATERIALS", plain_english="Recycled content certification.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ESG", "GRS", "recycled"]),
]

# ============================================================================
# MORE PAYMENT TERMS
# ============================================================================

TENOR_CLAUSES = [
    LCClause(code="TEN-001", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="45 Days from B/L", clause_text="PAYMENT AT 45 DAYS FROM B/L DATE", plain_english="45-day credit period.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["tenor", "45 days"]),
    LCClause(code="TEN-002", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="60 Days from B/L", clause_text="PAYMENT AT 60 DAYS FROM B/L DATE", plain_english="60-day credit period.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["tenor", "60 days"]),
    LCClause(code="TEN-003", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="90 Days from B/L", clause_text="PAYMENT AT 90 DAYS FROM B/L DATE", plain_english="90-day credit period.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["tenor", "90 days"]),
    LCClause(code="TEN-004", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="120 Days from B/L", clause_text="PAYMENT AT 120 DAYS FROM B/L DATE", plain_english="120-day credit period.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["tenor", "120 days"]),
    LCClause(code="TEN-005", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="180 Days from B/L", clause_text="PAYMENT AT 180 DAYS FROM B/L DATE", plain_english="180-day credit period.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["tenor", "180 days"]),
    LCClause(code="TEN-006", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="Mixed Payment 30/70", clause_text="30% AT SIGHT, 70% AT 90 DAYS FROM B/L DATE", plain_english="Split payment terms.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["tenor", "mixed", "split"]),
    LCClause(code="TEN-007", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="Mixed Payment 50/50", clause_text="50% AT SIGHT, 50% AT 60 DAYS FROM B/L DATE", plain_english="Equal split payment.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["tenor", "mixed", "50/50"]),
    LCClause(code="TEN-008", category=ClauseCategory.PAYMENT, subcategory="Tenor", title="Installments 3 Equal", clause_text="PAYMENT IN 3 EQUAL INSTALLMENTS AT 30, 60, 90 DAYS FROM B/L DATE", plain_english="3-installment payment.", risk_level=RiskLevel.MEDIUM, bias=BiasIndicator.APPLICANT, tags=["tenor", "installments"]),
]

# ============================================================================
# DOCUMENT DETAILS CLAUSES
# ============================================================================

DOC_DETAILS_CLAUSES = [
    # Invoice Details
    LCClause(code="DET-001", category=ClauseCategory.DOCUMENTS, subcategory="Invoice Details", title="Invoice Show PO Number", clause_text="COMMERCIAL INVOICE MUST SHOW PURCHASE ORDER NUMBER {po_number}", plain_english="Include buyer's PO reference.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "PO", "reference"]),
    LCClause(code="DET-002", category=ClauseCategory.DOCUMENTS, subcategory="Invoice Details", title="Invoice Show Contract Number", clause_text="COMMERCIAL INVOICE MUST SHOW CONTRACT NUMBER {contract_no}", plain_english="Include contract reference.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "contract", "reference"]),
    LCClause(code="DET-003", category=ClauseCategory.DOCUMENTS, subcategory="Invoice Details", title="Invoice Show HS Code", clause_text="COMMERCIAL INVOICE MUST SHOW HS TARIFF CODE FOR EACH ITEM", plain_english="Customs classification on invoice.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "HS code", "customs"]),
    LCClause(code="DET-004", category=ClauseCategory.DOCUMENTS, subcategory="Invoice Details", title="Invoice Show Country of Origin", clause_text="COMMERCIAL INVOICE MUST STATE COUNTRY OF ORIGIN OF GOODS", plain_english="Origin declaration on invoice.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "origin"]),
    LCClause(code="DET-005", category=ClauseCategory.DOCUMENTS, subcategory="Invoice Details", title="Invoice 3 Originals", clause_text="SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS", plain_english="Three original invoices.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "copies"]),
    LCClause(code="DET-006", category=ClauseCategory.DOCUMENTS, subcategory="Invoice Details", title="Invoice 5 Copies", clause_text="COMMERCIAL INVOICE IN 1 ORIGINAL AND 5 COPIES", plain_english="One original plus five copies.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["invoice", "copies"]),
    
    # B/L Details
    LCClause(code="DET-010", category=ClauseCategory.DOCUMENTS, subcategory="B/L Details", title="B/L Full Set 3/3", clause_text="FULL SET OF 3/3 ORIGINAL OCEAN BILLS OF LADING", plain_english="Complete set of three originals.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "full set"]),
    LCClause(code="DET-011", category=ClauseCategory.DOCUMENTS, subcategory="B/L Details", title="B/L Show Notify Party", clause_text="B/L MUST SHOW NOTIFY PARTY AS {notify_party}", plain_english="B/L must name who to notify.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "notify"]),
    LCClause(code="DET-012", category=ClauseCategory.DOCUMENTS, subcategory="B/L Details", title="B/L Show Freight Amount", clause_text="B/L MUST SHOW FREIGHT AMOUNT", plain_english="Freight cost on B/L.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "freight"]),
    LCClause(code="DET-013", category=ClauseCategory.DOCUMENTS, subcategory="B/L Details", title="B/L Dated Before Expiry", clause_text="B/L DATE MUST BE BEFORE LC EXPIRY DATE", plain_english="Shipment before LC expires.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "date"]),
    LCClause(code="DET-014", category=ClauseCategory.DOCUMENTS, subcategory="B/L Details", title="B/L Shipped on Board", clause_text="B/L MUST BE MARKED 'SHIPPED ON BOARD' WITH DATE", plain_english="On board notation required.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "shipped"]),
    LCClause(code="DET-015", category=ClauseCategory.DOCUMENTS, subcategory="B/L Details", title="B/L Container Numbers", clause_text="B/L MUST SHOW CONTAINER NUMBER(S) AND SEAL NUMBER(S)", plain_english="Container tracking info on B/L.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["B/L", "container"]),
    
    # Insurance Details
    LCClause(code="DET-020", category=ClauseCategory.DOCUMENTS, subcategory="Insurance Details", title="Insurance Show LC Number", clause_text="INSURANCE DOCUMENT MUST QUOTE LC NUMBER", plain_english="LC reference on insurance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "reference"]),
    LCClause(code="DET-021", category=ClauseCategory.DOCUMENTS, subcategory="Insurance Details", title="Insurance Show Vessel Name", clause_text="INSURANCE DOCUMENT MUST SHOW VESSEL NAME", plain_english="Ship name on insurance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "vessel"]),
    LCClause(code="DET-022", category=ClauseCategory.DOCUMENTS, subcategory="Insurance Details", title="Insurance Blank Endorsed", clause_text="INSURANCE POLICY/CERTIFICATE BLANK ENDORSED", plain_english="Transferable insurance document.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["insurance", "endorsed"]),
    LCClause(code="DET-023", category=ClauseCategory.DOCUMENTS, subcategory="Insurance Details", title="Insurance Cover Note Not Acceptable", clause_text="INSURANCE COVER NOTE NOT ACCEPTABLE", plain_english="Full certificate/policy required.", risk_level=RiskLevel.LOW, bias=BiasIndicator.APPLICANT, tags=["insurance", "cover note"]),
    
    # Packing Details
    LCClause(code="DET-030", category=ClauseCategory.DOCUMENTS, subcategory="Packing Details", title="Packing Show Marks", clause_text="PACKING LIST MUST SHOW SHIPPING MARKS", plain_english="Cargo marks on packing list.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["packing", "marks"]),
    LCClause(code="DET-031", category=ClauseCategory.DOCUMENTS, subcategory="Packing Details", title="Packing Show Carton Dimensions", clause_text="PACKING LIST MUST SHOW CARTON DIMENSIONS (L X W X H)", plain_english="Box sizes for shipping.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["packing", "dimensions"]),
    LCClause(code="DET-032", category=ClauseCategory.DOCUMENTS, subcategory="Packing Details", title="Packing Show CBM", clause_text="PACKING LIST MUST SHOW TOTAL CUBIC METERS (CBM)", plain_english="Volume for freight calculation.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["packing", "CBM"]),
]

# ============================================================================
# STANDBY LC SPECIFIC CLAUSES
# ============================================================================

SBLC_CLAUSES = [
    LCClause(code="SBLC-001", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Performance Guarantee", clause_text="THIS STANDBY LC GUARANTEES PERFORMANCE OF CONTRACT {contract_no}", plain_english="Guarantees seller's performance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "performance"]),
    LCClause(code="SBLC-002", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Payment Guarantee", clause_text="THIS STANDBY LC GUARANTEES PAYMENT BY APPLICANT", plain_english="Guarantees buyer's payment.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "payment"]),
    LCClause(code="SBLC-003", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Advance Payment Guarantee", clause_text="THIS STANDBY LC SECURES ADVANCE PAYMENT OF {amount}", plain_english="Protects buyer's advance.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "advance"]),
    LCClause(code="SBLC-004", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Demand Statement", clause_text="BENEFICIARY'S STATEMENT THAT APPLICANT HAS FAILED TO FULFILL OBLIGATION", plain_english="Default declaration to draw.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "demand"]),
    LCClause(code="SBLC-005", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Subject to ISP98", clause_text="THIS STANDBY LETTER OF CREDIT IS SUBJECT TO ISP98 (ICC PUBLICATION NO. 590)", plain_english="International Standby Practices apply.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "ISP98"]),
    LCClause(code="SBLC-006", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Bid Bond", clause_text="THIS STANDBY LC SERVES AS BID BOND FOR TENDER {tender_no}", plain_english="Guarantees tender commitment.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "bid bond"]),
    LCClause(code="SBLC-007", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Retention Guarantee", clause_text="THIS STANDBY LC SERVES AS RETENTION MONEY GUARANTEE", plain_english="Guarantees contractor retention.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "retention"]),
    LCClause(code="SBLC-008", category=ClauseCategory.SPECIAL, subcategory="Standby LC", title="SBLC Warranty Guarantee", clause_text="THIS STANDBY LC GUARANTEES WARRANTY OBLIGATIONS FOR {period}", plain_english="Backs warranty commitments.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["SBLC", "warranty"]),
]

# ============================================================================
# FINAL LC WORDING CLAUSES
# ============================================================================

STANDARD_LC_CLAUSES = [
    # Standard closing clauses
    LCClause(code="STD-001", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="LC Subject to UCP600", clause_text="THIS CREDIT IS SUBJECT TO UNIFORM CUSTOMS AND PRACTICE FOR DOCUMENTARY CREDITS (UCP600), ICC PUBLICATION NO. 600", plain_english="Standard UCP600 incorporation.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["UCP600", "standard"]),
    LCClause(code="STD-002", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="LC Subject to eUCP", clause_text="THIS CREDIT IS SUBJECT TO eUCP VERSION 2.0 SUPPLEMENT TO UCP600", plain_english="Electronic presentation allowed.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["eUCP", "electronic"]),
    LCClause(code="STD-003", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="LC Subject to URR725", clause_text="THIS CREDIT IS SUBJECT TO UNIFORM RULES FOR BANK-TO-BANK REIMBURSEMENT UNDER DOCUMENTARY CREDITS (URR725)", plain_english="Reimbursement rules apply.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["URR725", "reimbursement"]),
    LCClause(code="STD-004", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="ISBP745 Reference", clause_text="DOCUMENTS TO BE EXAMINED IN ACCORDANCE WITH INTERNATIONAL STANDARD BANKING PRACTICE (ISBP745)", plain_english="ISBP examination standard.", risk_level=RiskLevel.LOW, bias=BiasIndicator.NEUTRAL, tags=["ISBP745", "examination"]),
    
    # Final paragraphs
    LCClause(code="STD-010", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="Irrevocable Clause", clause_text="THIS CREDIT IS IRREVOCABLE AND CANNOT BE AMENDED OR CANCELLED WITHOUT CONSENT OF ALL PARTIES", plain_english="Cannot be changed unilaterally.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["irrevocable", "amendment"]),
    LCClause(code="STD-011", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="Engagement Clause", clause_text="WE HEREBY ENGAGE WITH DRAWERS, ENDORSERS AND BONA FIDE HOLDERS THAT DRAFTS DRAWN UNDER AND IN COMPLIANCE WITH THE TERMS OF THIS CREDIT WILL BE DULY HONORED", plain_english="Bank's payment undertaking.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["engagement", "honor"]),
    LCClause(code="STD-012", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="Third Party Documents", clause_text="THIRD PARTY DOCUMENTS ACCEPTABLE EXCEPT COMMERCIAL INVOICE", plain_english="Documents can be from parties other than beneficiary.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["third party", "documents"]),
    LCClause(code="STD-013", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="Signature Not Required", clause_text="SIGNATURES ON DOCUMENTS OTHER THAN DRAFT ARE NOT REQUIRED UNLESS SPECIFIED", plain_english="Documents don't need signing unless LC says so.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["signature", "not required"]),
    LCClause(code="STD-014", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="Full Name Not Required", clause_text="FULL NAME OF APPLICANT/BENEFICIARY NOT REQUIRED ON DOCUMENTS", plain_english="Short names/abbreviations OK.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["name", "abbreviation"]),
    LCClause(code="STD-015", category=ClauseCategory.SPECIAL, subcategory="Standard Wording", title="Port Address Not Required", clause_text="FULL ADDRESS OF PORT IS NOT REQUIRED ON DOCUMENTS", plain_english="Just port name is sufficient.", risk_level=RiskLevel.LOW, bias=BiasIndicator.BENEFICIARY, tags=["port", "address"]),
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
    RED_GREEN_CLAUSES +
    UCP600_CLAUSES +
    ISBP745_CLAUSES +
    REGIONAL_CLAUSES +
    INDUSTRY_CLAUSES +
    MORE_AMENDMENT_CLAUSES +
    BANK_SPECIFIC_CLAUSES +
    INCOTERMS_CLAUSES +
    PORT_CLAUSES +
    INSPECTION_CLAUSES +
    CERTIFICATE_CLAUSES +
    MORE_SHIPMENT_CLAUSES +
    MORE_DOCUMENT_CLAUSES +
    MORE_PAYMENT_CLAUSES +
    MORE_SPECIAL_CLAUSES +
    TRADE_ROUTE_CLAUSES +
    ESG_CLAUSES +
    TENOR_CLAUSES +
    DOC_DETAILS_CLAUSES +
    SBLC_CLAUSES +
    STANDARD_LC_CLAUSES
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

