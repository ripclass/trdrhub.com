"""
Shared Document Types - Single Source of Truth (Python)

This file mirrors document-types.ts and provides the same types for the backend.
KEEP IN SYNC with the TypeScript version!

RULES:
1. NEVER change existing values (breaks backward compatibility)
2. Always add new types to the appropriate category
3. Keep in sync with document-types.ts
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


# =============================================================================
# DOCUMENT CATEGORIES
# =============================================================================

class DocumentCategory(str, Enum):
    """Document type categories for grouping in UI"""
    CORE = "core"
    TRANSPORT = "transport"
    INSPECTION = "inspection"
    HEALTH = "health"
    FINANCIAL = "financial"
    CUSTOMS = "customs"
    OTHER = "other"


# =============================================================================
# DOCUMENT TYPE ENUM
# =============================================================================

class DocumentType(str, Enum):
    """
    Canonical document type values.
    These are the values used in API payloads.
    """
    # =========================================================================
    # CORE DOCUMENTS (Required for most LCs)
    # =========================================================================
    LETTER_OF_CREDIT = "letter_of_credit"
    SWIFT_MESSAGE = "swift_message"
    LC_APPLICATION = "lc_application"
    COMMERCIAL_INVOICE = "commercial_invoice"
    PROFORMA_INVOICE = "proforma_invoice"
    BILL_OF_LADING = "bill_of_lading"
    PACKING_LIST = "packing_list"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    INSURANCE_POLICY = "insurance_policy"

    # =========================================================================
    # TRANSPORT DOCUMENTS
    # =========================================================================
    OCEAN_BILL_OF_LADING = "ocean_bill_of_lading"
    SEA_WAYBILL = "sea_waybill"
    AIR_WAYBILL = "air_waybill"
    MULTIMODAL_TRANSPORT_DOCUMENT = "multimodal_transport_document"
    RAILWAY_CONSIGNMENT_NOTE = "railway_consignment_note"
    ROAD_TRANSPORT_DOCUMENT = "road_transport_document"
    FORWARDER_CERTIFICATE_OF_RECEIPT = "forwarder_certificate_of_receipt"
    HOUSE_BILL_OF_LADING = "house_bill_of_lading"
    MASTER_BILL_OF_LADING = "master_bill_of_lading"
    SHIPPING_COMPANY_CERTIFICATE = "shipping_company_certificate"
    MATES_RECEIPT = "mates_receipt"
    DELIVERY_ORDER = "delivery_order"

    # =========================================================================
    # INSPECTION & QUALITY CERTIFICATES
    # =========================================================================
    INSPECTION_CERTIFICATE = "inspection_certificate"
    PRE_SHIPMENT_INSPECTION = "pre_shipment_inspection"
    QUALITY_CERTIFICATE = "quality_certificate"
    WEIGHT_CERTIFICATE = "weight_certificate"
    MEASUREMENT_CERTIFICATE = "measurement_certificate"
    ANALYSIS_CERTIFICATE = "analysis_certificate"
    LAB_TEST_REPORT = "lab_test_report"
    SGS_CERTIFICATE = "sgs_certificate"
    BUREAU_VERITAS_CERTIFICATE = "bureau_veritas_certificate"
    INTERTEK_CERTIFICATE = "intertek_certificate"

    # =========================================================================
    # HEALTH & AGRICULTURAL CERTIFICATES
    # =========================================================================
    PHYTOSANITARY_CERTIFICATE = "phytosanitary_certificate"
    FUMIGATION_CERTIFICATE = "fumigation_certificate"
    HEALTH_CERTIFICATE = "health_certificate"
    VETERINARY_CERTIFICATE = "veterinary_certificate"
    SANITARY_CERTIFICATE = "sanitary_certificate"
    CITES_PERMIT = "cites_permit"
    RADIATION_CERTIFICATE = "radiation_certificate"
    HALAL_CERTIFICATE = "halal_certificate"
    KOSHER_CERTIFICATE = "kosher_certificate"
    ORGANIC_CERTIFICATE = "organic_certificate"

    # =========================================================================
    # FINANCIAL DOCUMENTS
    # =========================================================================
    DRAFT_BILL_OF_EXCHANGE = "draft_bill_of_exchange"
    PROMISSORY_NOTE = "promissory_note"
    BANK_GUARANTEE = "bank_guarantee"
    STANDBY_LC = "standby_lc"
    PAYMENT_RECEIPT = "payment_receipt"
    DEBIT_NOTE = "debit_note"
    CREDIT_NOTE = "credit_note"

    # =========================================================================
    # BENEFICIARY & ATTESTATION
    # =========================================================================
    BENEFICIARY_CERTIFICATE = "beneficiary_certificate"
    MANUFACTURER_CERTIFICATE = "manufacturer_certificate"
    CONFORMITY_CERTIFICATE = "conformity_certificate"
    NON_MANIPULATION_CERTIFICATE = "non_manipulation_certificate"

    # =========================================================================
    # CUSTOMS & TRADE COMPLIANCE
    # =========================================================================
    CUSTOMS_DECLARATION = "customs_declaration"
    EXPORT_LICENSE = "export_license"
    IMPORT_LICENSE = "import_license"
    GSP_FORM_A = "gsp_form_a"
    EUR1_MOVEMENT_CERTIFICATE = "eur1_movement_certificate"
    WAREHOUSE_RECEIPT = "warehouse_receipt"
    CARGO_MANIFEST = "cargo_manifest"

    # =========================================================================
    # OTHER / SUPPORTING
    # =========================================================================
    SUPPORTING_DOCUMENT = "supporting_document"
    OTHER = "other"
    UNKNOWN = "unknown"


# =============================================================================
# DOCUMENT TYPE METADATA
# =============================================================================

@dataclass
class DocumentTypeInfo:
    """Metadata for a document type"""
    value: str
    label: str
    short_label: str
    category: DocumentCategory
    aliases: List[str]
    description: str = ""
    avg_pages: int = 2
    required: bool = False


# Complete document type registry with metadata
DOCUMENT_TYPE_INFO: Dict[str, DocumentTypeInfo] = {
    # =========================================================================
    # CORE DOCUMENTS
    # =========================================================================
    DocumentType.LETTER_OF_CREDIT.value: DocumentTypeInfo(
        value=DocumentType.LETTER_OF_CREDIT.value,
        label="Letter of Credit",
        short_label="LC",
        category=DocumentCategory.CORE,
        aliases=["lc", "l/c", "mt700", "mt760", "documentary_credit"],
        description="MT700/MT760 Letter of Credit document",
        avg_pages=6,
        required=True,
    ),
    DocumentType.SWIFT_MESSAGE.value: DocumentTypeInfo(
        value=DocumentType.SWIFT_MESSAGE.value,
        label="SWIFT Message",
        short_label="SWIFT",
        category=DocumentCategory.CORE,
        aliases=["swift", "mt", "message"],
        description="SWIFT banking message (MT series)",
        avg_pages=3,
    ),
    DocumentType.LC_APPLICATION.value: DocumentTypeInfo(
        value=DocumentType.LC_APPLICATION.value,
        label="LC Application",
        short_label="LC App",
        category=DocumentCategory.CORE,
        aliases=["lc_app", "application", "lc_request"],
        description="Application for opening Letter of Credit",
        avg_pages=4,
    ),
    DocumentType.COMMERCIAL_INVOICE.value: DocumentTypeInfo(
        value=DocumentType.COMMERCIAL_INVOICE.value,
        label="Commercial Invoice",
        short_label="Invoice",
        category=DocumentCategory.CORE,
        aliases=["invoice", "inv", "commercial_inv", "sales_invoice"],
        description="Seller's invoice for goods shipped",
        avg_pages=2,
        required=True,
    ),
    DocumentType.PROFORMA_INVOICE.value: DocumentTypeInfo(
        value=DocumentType.PROFORMA_INVOICE.value,
        label="Proforma Invoice",
        short_label="Proforma",
        category=DocumentCategory.CORE,
        aliases=["proforma", "pro_forma", "pi"],
        description="Preliminary invoice before shipment",
        avg_pages=2,
    ),
    DocumentType.BILL_OF_LADING.value: DocumentTypeInfo(
        value=DocumentType.BILL_OF_LADING.value,
        label="Bill of Lading",
        short_label="B/L",
        category=DocumentCategory.TRANSPORT,
        aliases=["bl", "b/l", "bol", "lading"],
        description="Transport document for ocean shipment",
        avg_pages=3,
        required=True,
    ),
    DocumentType.PACKING_LIST.value: DocumentTypeInfo(
        value=DocumentType.PACKING_LIST.value,
        label="Packing List",
        short_label="PL",
        category=DocumentCategory.CORE,
        aliases=["packing", "pack_list", "plist", "pl"],
        description="Detailed list of packed goods",
        avg_pages=3,
        required=True,
    ),
    DocumentType.CERTIFICATE_OF_ORIGIN.value: DocumentTypeInfo(
        value=DocumentType.CERTIFICATE_OF_ORIGIN.value,
        label="Certificate of Origin",
        short_label="COO",
        category=DocumentCategory.CORE,
        aliases=["coo", "origin", "origin_cert", "co"],
        description="Certifies country of origin of goods",
        avg_pages=2,
    ),
    DocumentType.INSURANCE_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.INSURANCE_CERTIFICATE.value,
        label="Insurance Certificate",
        short_label="Ins. Cert",
        category=DocumentCategory.CORE,
        aliases=["insurance", "ins_cert", "insurance_cert", "cargo_insurance", "marine_insurance"],
        description="Proof of cargo insurance coverage",
        avg_pages=2,
    ),
    DocumentType.INSURANCE_POLICY.value: DocumentTypeInfo(
        value=DocumentType.INSURANCE_POLICY.value,
        label="Insurance Policy",
        short_label="Policy",
        category=DocumentCategory.CORE,
        aliases=["policy", "ins_policy"],
        description="Full insurance policy document",
        avg_pages=8,
    ),

    # =========================================================================
    # TRANSPORT DOCUMENTS
    # =========================================================================
    DocumentType.OCEAN_BILL_OF_LADING.value: DocumentTypeInfo(
        value=DocumentType.OCEAN_BILL_OF_LADING.value,
        label="Ocean Bill of Lading",
        short_label="Ocean B/L",
        category=DocumentCategory.TRANSPORT,
        aliases=["ocean_bl", "marine_bl", "obl"],
        description="Bill of lading for ocean freight",
        avg_pages=3,
    ),
    DocumentType.SEA_WAYBILL.value: DocumentTypeInfo(
        value=DocumentType.SEA_WAYBILL.value,
        label="Sea Waybill",
        short_label="SWB",
        category=DocumentCategory.TRANSPORT,
        aliases=["sea_waybill", "swb", "seawaybill"],
        description="Non-negotiable sea transport document",
        avg_pages=2,
    ),
    DocumentType.AIR_WAYBILL.value: DocumentTypeInfo(
        value=DocumentType.AIR_WAYBILL.value,
        label="Air Waybill",
        short_label="AWB",
        category=DocumentCategory.TRANSPORT,
        aliases=["awb", "airwaybill", "air_waybill", "hawb", "mawb"],
        description="Transport document for air freight",
        avg_pages=2,
    ),
    DocumentType.MULTIMODAL_TRANSPORT_DOCUMENT.value: DocumentTypeInfo(
        value=DocumentType.MULTIMODAL_TRANSPORT_DOCUMENT.value,
        label="Multimodal Transport Document",
        short_label="MTD",
        category=DocumentCategory.TRANSPORT,
        aliases=["multimodal", "mtd", "combined_transport"],
        description="Document for multiple transport modes",
        avg_pages=3,
    ),
    DocumentType.RAILWAY_CONSIGNMENT_NOTE.value: DocumentTypeInfo(
        value=DocumentType.RAILWAY_CONSIGNMENT_NOTE.value,
        label="Railway Consignment Note",
        short_label="Rail CN",
        category=DocumentCategory.TRANSPORT,
        aliases=["rail", "railway", "cim", "smgs"],
        description="Transport document for rail freight",
        avg_pages=2,
    ),
    DocumentType.ROAD_TRANSPORT_DOCUMENT.value: DocumentTypeInfo(
        value=DocumentType.ROAD_TRANSPORT_DOCUMENT.value,
        label="Road Transport Document",
        short_label="CMR",
        category=DocumentCategory.TRANSPORT,
        aliases=["cmr", "road", "trucking"],
        description="Transport document for road freight (CMR)",
        avg_pages=2,
    ),
    DocumentType.FORWARDER_CERTIFICATE_OF_RECEIPT.value: DocumentTypeInfo(
        value=DocumentType.FORWARDER_CERTIFICATE_OF_RECEIPT.value,
        label="Forwarder's Certificate of Receipt",
        short_label="FCR",
        category=DocumentCategory.TRANSPORT,
        aliases=["fcr", "forwarder", "freight_receipt"],
        description="Freight forwarder receipt document",
        avg_pages=1,
    ),
    DocumentType.HOUSE_BILL_OF_LADING.value: DocumentTypeInfo(
        value=DocumentType.HOUSE_BILL_OF_LADING.value,
        label="House Bill of Lading",
        short_label="HBL",
        category=DocumentCategory.TRANSPORT,
        aliases=["hbl", "house_bl"],
        description="B/L issued by freight forwarder",
        avg_pages=3,
    ),
    DocumentType.MASTER_BILL_OF_LADING.value: DocumentTypeInfo(
        value=DocumentType.MASTER_BILL_OF_LADING.value,
        label="Master Bill of Lading",
        short_label="MBL",
        category=DocumentCategory.TRANSPORT,
        aliases=["mbl", "master_bl"],
        description="B/L issued by shipping line",
        avg_pages=3,
    ),
    DocumentType.SHIPPING_COMPANY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.SHIPPING_COMPANY_CERTIFICATE.value,
        label="Shipping Company Certificate",
        short_label="Ship Cert",
        category=DocumentCategory.TRANSPORT,
        aliases=["shipping_cert", "carrier_cert"],
        description="Certificate from shipping company",
        avg_pages=1,
    ),
    DocumentType.MATES_RECEIPT.value: DocumentTypeInfo(
        value=DocumentType.MATES_RECEIPT.value,
        label="Mate's Receipt",
        short_label="MR",
        category=DocumentCategory.TRANSPORT,
        aliases=["mates_receipt", "mr", "mate_receipt"],
        description="Receipt from ship's officer for cargo",
        avg_pages=1,
    ),
    DocumentType.DELIVERY_ORDER.value: DocumentTypeInfo(
        value=DocumentType.DELIVERY_ORDER.value,
        label="Delivery Order",
        short_label="DO",
        category=DocumentCategory.TRANSPORT,
        aliases=["do", "delivery", "release_order"],
        description="Order to release cargo",
        avg_pages=1,
    ),

    # =========================================================================
    # INSPECTION & QUALITY CERTIFICATES
    # =========================================================================
    DocumentType.INSPECTION_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.INSPECTION_CERTIFICATE.value,
        label="Inspection Certificate",
        short_label="Insp Cert",
        category=DocumentCategory.INSPECTION,
        aliases=["inspection", "insp_cert", "survey"],
        description="Third-party inspection certificate",
        avg_pages=3,
    ),
    DocumentType.PRE_SHIPMENT_INSPECTION.value: DocumentTypeInfo(
        value=DocumentType.PRE_SHIPMENT_INSPECTION.value,
        label="Pre-Shipment Inspection",
        short_label="PSI",
        category=DocumentCategory.INSPECTION,
        aliases=["psi", "pre_shipment"],
        description="Inspection before shipment",
        avg_pages=3,
    ),
    DocumentType.QUALITY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.QUALITY_CERTIFICATE.value,
        label="Quality Certificate",
        short_label="QC",
        category=DocumentCategory.INSPECTION,
        aliases=["quality", "qc", "quality_cert"],
        description="Certificate of quality",
        avg_pages=2,
    ),
    DocumentType.WEIGHT_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.WEIGHT_CERTIFICATE.value,
        label="Weight Certificate",
        short_label="Wt Cert",
        category=DocumentCategory.INSPECTION,
        aliases=["weight", "weighment", "weight_cert"],
        description="Certificate of weight",
        avg_pages=1,
    ),
    DocumentType.MEASUREMENT_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.MEASUREMENT_CERTIFICATE.value,
        label="Measurement Certificate",
        short_label="Meas Cert",
        category=DocumentCategory.INSPECTION,
        aliases=["measurement", "dimension"],
        description="Certificate of measurements/dimensions",
        avg_pages=1,
    ),
    DocumentType.ANALYSIS_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.ANALYSIS_CERTIFICATE.value,
        label="Analysis Certificate",
        short_label="Analysis",
        category=DocumentCategory.INSPECTION,
        aliases=["analysis", "chemical_analysis"],
        description="Chemical/composition analysis",
        avg_pages=2,
    ),
    DocumentType.LAB_TEST_REPORT.value: DocumentTypeInfo(
        value=DocumentType.LAB_TEST_REPORT.value,
        label="Lab Test Report",
        short_label="Lab Test",
        category=DocumentCategory.INSPECTION,
        aliases=["lab_test", "lab_report", "test_report"],
        description="Laboratory test results",
        avg_pages=3,
    ),
    DocumentType.SGS_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.SGS_CERTIFICATE.value,
        label="SGS Certificate",
        short_label="SGS",
        category=DocumentCategory.INSPECTION,
        aliases=["sgs"],
        description="Certificate from SGS inspection",
        avg_pages=3,
    ),
    DocumentType.BUREAU_VERITAS_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.BUREAU_VERITAS_CERTIFICATE.value,
        label="Bureau Veritas Certificate",
        short_label="BV",
        category=DocumentCategory.INSPECTION,
        aliases=["bureau_veritas", "bv"],
        description="Certificate from Bureau Veritas",
        avg_pages=3,
    ),
    DocumentType.INTERTEK_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.INTERTEK_CERTIFICATE.value,
        label="Intertek Certificate",
        short_label="Intertek",
        category=DocumentCategory.INSPECTION,
        aliases=["intertek"],
        description="Certificate from Intertek",
        avg_pages=3,
    ),

    # =========================================================================
    # HEALTH & AGRICULTURAL CERTIFICATES
    # =========================================================================
    DocumentType.PHYTOSANITARY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.PHYTOSANITARY_CERTIFICATE.value,
        label="Phytosanitary Certificate",
        short_label="Phyto",
        category=DocumentCategory.HEALTH,
        aliases=["phyto", "phytosanitary", "plant_health"],
        description="Plant health certificate",
        avg_pages=1,
    ),
    DocumentType.FUMIGATION_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.FUMIGATION_CERTIFICATE.value,
        label="Fumigation Certificate",
        short_label="Fumi",
        category=DocumentCategory.HEALTH,
        aliases=["fumigation", "fumi", "pest_control"],
        description="Proof of fumigation treatment",
        avg_pages=1,
    ),
    DocumentType.HEALTH_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.HEALTH_CERTIFICATE.value,
        label="Health Certificate",
        short_label="Health",
        category=DocumentCategory.HEALTH,
        aliases=["health", "health_cert"],
        description="General health certificate",
        avg_pages=1,
    ),
    DocumentType.VETERINARY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.VETERINARY_CERTIFICATE.value,
        label="Veterinary Certificate",
        short_label="Vet",
        category=DocumentCategory.HEALTH,
        aliases=["vet", "veterinary", "animal_health"],
        description="Animal health certificate",
        avg_pages=1,
    ),
    DocumentType.SANITARY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.SANITARY_CERTIFICATE.value,
        label="Sanitary Certificate",
        short_label="Sanitary",
        category=DocumentCategory.HEALTH,
        aliases=["sanitary", "sanit"],
        description="Sanitary/hygiene certificate",
        avg_pages=1,
    ),
    DocumentType.CITES_PERMIT.value: DocumentTypeInfo(
        value=DocumentType.CITES_PERMIT.value,
        label="CITES Permit",
        short_label="CITES",
        category=DocumentCategory.HEALTH,
        aliases=["cites"],
        description="Permit for endangered species trade",
        avg_pages=2,
    ),
    DocumentType.RADIATION_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.RADIATION_CERTIFICATE.value,
        label="Radiation Certificate",
        short_label="Radiation",
        category=DocumentCategory.HEALTH,
        aliases=["radiation", "non_radiation"],
        description="Radiation testing certificate",
        avg_pages=1,
    ),
    DocumentType.HALAL_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.HALAL_CERTIFICATE.value,
        label="Halal Certificate",
        short_label="Halal",
        category=DocumentCategory.HEALTH,
        aliases=["halal"],
        description="Halal certification",
        avg_pages=1,
    ),
    DocumentType.KOSHER_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.KOSHER_CERTIFICATE.value,
        label="Kosher Certificate",
        short_label="Kosher",
        category=DocumentCategory.HEALTH,
        aliases=["kosher"],
        description="Kosher certification",
        avg_pages=1,
    ),
    DocumentType.ORGANIC_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.ORGANIC_CERTIFICATE.value,
        label="Organic Certificate",
        short_label="Organic",
        category=DocumentCategory.HEALTH,
        aliases=["organic"],
        description="Organic certification",
        avg_pages=2,
    ),

    # =========================================================================
    # FINANCIAL DOCUMENTS
    # =========================================================================
    DocumentType.DRAFT_BILL_OF_EXCHANGE.value: DocumentTypeInfo(
        value=DocumentType.DRAFT_BILL_OF_EXCHANGE.value,
        label="Draft/Bill of Exchange",
        short_label="Draft",
        category=DocumentCategory.FINANCIAL,
        aliases=["draft", "boe", "bill_of_exchange"],
        description="Payment draft or bill of exchange",
        avg_pages=1,
    ),
    DocumentType.PROMISSORY_NOTE.value: DocumentTypeInfo(
        value=DocumentType.PROMISSORY_NOTE.value,
        label="Promissory Note",
        short_label="P/N",
        category=DocumentCategory.FINANCIAL,
        aliases=["promissory", "pn"],
        description="Promise to pay document",
        avg_pages=1,
    ),
    DocumentType.BANK_GUARANTEE.value: DocumentTypeInfo(
        value=DocumentType.BANK_GUARANTEE.value,
        label="Bank Guarantee",
        short_label="BG",
        category=DocumentCategory.FINANCIAL,
        aliases=["bg", "guarantee"],
        description="Bank guarantee document",
        avg_pages=2,
    ),
    DocumentType.STANDBY_LC.value: DocumentTypeInfo(
        value=DocumentType.STANDBY_LC.value,
        label="Standby Letter of Credit",
        short_label="SBLC",
        category=DocumentCategory.FINANCIAL,
        aliases=["sblc", "standby"],
        description="Standby LC document",
        avg_pages=4,
    ),
    DocumentType.PAYMENT_RECEIPT.value: DocumentTypeInfo(
        value=DocumentType.PAYMENT_RECEIPT.value,
        label="Payment Receipt",
        short_label="Receipt",
        category=DocumentCategory.FINANCIAL,
        aliases=["receipt", "payment"],
        description="Proof of payment",
        avg_pages=1,
    ),
    DocumentType.DEBIT_NOTE.value: DocumentTypeInfo(
        value=DocumentType.DEBIT_NOTE.value,
        label="Debit Note",
        short_label="DN",
        category=DocumentCategory.FINANCIAL,
        aliases=["debit", "dn"],
        description="Debit note document",
        avg_pages=1,
    ),
    DocumentType.CREDIT_NOTE.value: DocumentTypeInfo(
        value=DocumentType.CREDIT_NOTE.value,
        label="Credit Note",
        short_label="CN",
        category=DocumentCategory.FINANCIAL,
        aliases=["credit", "cn"],
        description="Credit note document",
        avg_pages=1,
    ),

    # =========================================================================
    # BENEFICIARY & ATTESTATION
    # =========================================================================
    DocumentType.BENEFICIARY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.BENEFICIARY_CERTIFICATE.value,
        label="Beneficiary Certificate",
        short_label="Benef Cert",
        category=DocumentCategory.OTHER,
        aliases=["beneficiary", "benef_cert", "attestation"],
        description="Certificate signed by beneficiary",
        avg_pages=1,
    ),
    DocumentType.MANUFACTURER_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.MANUFACTURER_CERTIFICATE.value,
        label="Manufacturer's Certificate",
        short_label="Mfr Cert",
        category=DocumentCategory.OTHER,
        aliases=["manufacturer", "mfr_cert"],
        description="Certificate from manufacturer",
        avg_pages=1,
    ),
    DocumentType.CONFORMITY_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.CONFORMITY_CERTIFICATE.value,
        label="Certificate of Conformity",
        short_label="COC",
        category=DocumentCategory.OTHER,
        aliases=["conformity", "coc", "compliance"],
        description="Certificate of compliance/conformity",
        avg_pages=1,
    ),
    DocumentType.NON_MANIPULATION_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.NON_MANIPULATION_CERTIFICATE.value,
        label="Non-Manipulation Certificate",
        short_label="Non-Manip",
        category=DocumentCategory.OTHER,
        aliases=["non_manipulation", "transhipment"],
        description="Certificate of non-manipulation",
        avg_pages=1,
    ),

    # =========================================================================
    # CUSTOMS & TRADE COMPLIANCE
    # =========================================================================
    DocumentType.CUSTOMS_DECLARATION.value: DocumentTypeInfo(
        value=DocumentType.CUSTOMS_DECLARATION.value,
        label="Customs Declaration",
        short_label="Customs",
        category=DocumentCategory.CUSTOMS,
        aliases=["customs", "declaration", "customs_form"],
        description="Customs clearance document",
        avg_pages=2,
    ),
    DocumentType.EXPORT_LICENSE.value: DocumentTypeInfo(
        value=DocumentType.EXPORT_LICENSE.value,
        label="Export License",
        short_label="Exp Lic",
        category=DocumentCategory.CUSTOMS,
        aliases=["export_license", "export_permit"],
        description="License to export goods",
        avg_pages=1,
    ),
    DocumentType.IMPORT_LICENSE.value: DocumentTypeInfo(
        value=DocumentType.IMPORT_LICENSE.value,
        label="Import License",
        short_label="Imp Lic",
        category=DocumentCategory.CUSTOMS,
        aliases=["import_license", "import_permit"],
        description="License to import goods",
        avg_pages=1,
    ),
    DocumentType.GSP_FORM_A.value: DocumentTypeInfo(
        value=DocumentType.GSP_FORM_A.value,
        label="GSP Form A",
        short_label="Form A",
        category=DocumentCategory.CUSTOMS,
        aliases=["gsp", "form_a", "preference"],
        description="Generalized System of Preferences form",
        avg_pages=1,
    ),
    DocumentType.EUR1_MOVEMENT_CERTIFICATE.value: DocumentTypeInfo(
        value=DocumentType.EUR1_MOVEMENT_CERTIFICATE.value,
        label="EUR.1 Movement Certificate",
        short_label="EUR.1",
        category=DocumentCategory.CUSTOMS,
        aliases=["eur1", "eur.1", "movement_cert"],
        description="EU preferential origin certificate",
        avg_pages=1,
    ),
    DocumentType.WAREHOUSE_RECEIPT.value: DocumentTypeInfo(
        value=DocumentType.WAREHOUSE_RECEIPT.value,
        label="Warehouse Receipt",
        short_label="WR",
        category=DocumentCategory.CUSTOMS,
        aliases=["warehouse", "wr", "storage"],
        description="Receipt for goods in warehouse",
        avg_pages=1,
    ),
    DocumentType.CARGO_MANIFEST.value: DocumentTypeInfo(
        value=DocumentType.CARGO_MANIFEST.value,
        label="Cargo Manifest",
        short_label="Manifest",
        category=DocumentCategory.CUSTOMS,
        aliases=["manifest", "cargo_list"],
        description="List of all cargo on vessel",
        avg_pages=3,
    ),

    # =========================================================================
    # OTHER / SUPPORTING
    # =========================================================================
    DocumentType.SUPPORTING_DOCUMENT.value: DocumentTypeInfo(
        value=DocumentType.SUPPORTING_DOCUMENT.value,
        label="Supporting Document",
        short_label="Support",
        category=DocumentCategory.OTHER,
        aliases=["supporting", "supplementary", "attachment"],
        description="Additional supporting document",
        avg_pages=2,
    ),
    DocumentType.OTHER.value: DocumentTypeInfo(
        value=DocumentType.OTHER.value,
        label="Other Document",
        short_label="Other",
        category=DocumentCategory.OTHER,
        aliases=["other", "misc", "miscellaneous"],
        description="Other document type",
        avg_pages=2,
    ),
    DocumentType.UNKNOWN.value: DocumentTypeInfo(
        value=DocumentType.UNKNOWN.value,
        label="Unknown",
        short_label="?",
        category=DocumentCategory.OTHER,
        aliases=["unknown"],
        description="Document type not identified",
        avg_pages=2,
    ),
}


# =============================================================================
# BUILD ALIAS LOOKUP (for fast normalization)
# =============================================================================

_ALIAS_TO_DOCTYPE: Dict[str, str] = {}
for doc_type, info in DOCUMENT_TYPE_INFO.items():
    _ALIAS_TO_DOCTYPE[doc_type] = doc_type  # Self-reference
    for alias in info.aliases:
        _ALIAS_TO_DOCTYPE[alias.lower()] = doc_type


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_document_type(input_value: str) -> str:
    """
    Normalize any document type value to the canonical form.
    Handles aliases, legacy values, case variations, and display labels.
    
    Args:
        input_value: Raw document type string (e.g., "lc", "invoice", "Letter of Credit")
        
    Returns:
        Canonical document type value (e.g., "letter_of_credit")
    """
    if not input_value:
        return DocumentType.UNKNOWN.value
    
    normalized = input_value.lower().strip()
    
    # Handle display labels by converting spaces to underscores
    # e.g., "Letter of Credit" -> "letter_of_credit"
    normalized_underscored = normalized.replace(" ", "_").replace("-", "_")
    
    # Direct match via alias lookup (original)
    if normalized in _ALIAS_TO_DOCTYPE:
        return _ALIAS_TO_DOCTYPE[normalized]
    
    # Direct match via alias lookup (underscored version)
    if normalized_underscored in _ALIAS_TO_DOCTYPE:
        return _ALIAS_TO_DOCTYPE[normalized_underscored]
    
    # Check if it's already a valid document type
    try:
        DocumentType(normalized_underscored)
        return normalized_underscored
    except ValueError:
        pass
    
    # Fuzzy match on common patterns
    if "letter" in normalized and "credit" in normalized:
        return DocumentType.LETTER_OF_CREDIT.value
    if "lc" in normalized or "credit" in normalized:
        return DocumentType.LETTER_OF_CREDIT.value
    if "invoice" in normalized or normalized == "inv":
        return DocumentType.COMMERCIAL_INVOICE.value
    if "lading" in normalized or normalized in ("bl", "bol", "b/l"):
        return DocumentType.BILL_OF_LADING.value
    if "packing" in normalized:
        return DocumentType.PACKING_LIST.value
    if "origin" in normalized or normalized == "coo":
        return DocumentType.CERTIFICATE_OF_ORIGIN.value
    if "insurance" in normalized:
        return DocumentType.INSURANCE_CERTIFICATE.value
    if "inspection" in normalized:
        return DocumentType.INSPECTION_CERTIFICATE.value
    if "weight" in normalized:
        return DocumentType.WEIGHT_CERTIFICATE.value
    if "quality" in normalized:
        return DocumentType.QUALITY_CERTIFICATE.value
    if "phyto" in normalized or "sanitary" in normalized:
        return DocumentType.PHYTOSANITARY_CERTIFICATE.value
    if "health" in normalized:
        return DocumentType.HEALTH_CERTIFICATE.value
    if "fumigat" in normalized:
        return DocumentType.FUMIGATION_CERTIFICATE.value
    if "draft" in normalized or "exchange" in normalized:
        return DocumentType.DRAFT_BILL_OF_EXCHANGE.value
    if "beneficiary" in normalized:
        return DocumentType.BENEFICIARY_CERTIFICATE.value
    if "air" in normalized and "waybill" in normalized:
        return DocumentType.AIR_WAYBILL.value
    if "awb" in normalized:
        return DocumentType.AIR_WAYBILL.value
    
    return DocumentType.UNKNOWN.value


def get_document_type_info(type_value: str) -> Optional[DocumentTypeInfo]:
    """Get document type info by value or alias."""
    normalized = normalize_document_type(type_value)
    return DOCUMENT_TYPE_INFO.get(normalized)


def get_documents_by_category() -> Dict[DocumentCategory, List[DocumentTypeInfo]]:
    """Get documents grouped by category for UI display."""
    grouped: Dict[DocumentCategory, List[DocumentTypeInfo]] = {
        DocumentCategory.CORE: [],
        DocumentCategory.TRANSPORT: [],
        DocumentCategory.INSPECTION: [],
        DocumentCategory.HEALTH: [],
        DocumentCategory.FINANCIAL: [],
        DocumentCategory.CUSTOMS: [],
        DocumentCategory.OTHER: [],
    }
    
    for info in DOCUMENT_TYPE_INFO.values():
        grouped[info.category].append(info)
    
    return grouped


def get_required_document_types() -> Set[str]:
    """Get document types that are typically required for LC."""
    return {
        doc_type
        for doc_type, info in DOCUMENT_TYPE_INFO.items()
        if info.required
    }


def is_transport_document(type_value: str) -> bool:
    """Check if a document type is a transport document."""
    info = get_document_type_info(type_value)
    return info.category == DocumentCategory.TRANSPORT if info else False


def is_lc_document(type_value: str) -> bool:
    """Check if a document type is LC-related."""
    normalized = normalize_document_type(type_value)
    return normalized in {
        DocumentType.LETTER_OF_CREDIT.value,
        DocumentType.SWIFT_MESSAGE.value,
        DocumentType.LC_APPLICATION.value,
        DocumentType.STANDBY_LC.value,
    }


# =============================================================================
# EXPORT ALL
# =============================================================================

__all__ = [
    # Enums
    "DocumentType",
    "DocumentCategory",
    # Data classes
    "DocumentTypeInfo",
    # Constants
    "DOCUMENT_TYPE_INFO",
    # Functions
    "normalize_document_type",
    "get_document_type_info",
    "get_documents_by_category",
    "get_required_document_types",
    "is_transport_document",
    "is_lc_document",
]
