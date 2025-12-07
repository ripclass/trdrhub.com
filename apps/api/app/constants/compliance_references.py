"""
Centralized UCP600 and ISBP745 reference descriptions.

This module provides human-readable descriptions for compliance rules,
eliminating the need for frontend hardcoded lookups.

Usage:
    from app.constants.compliance_references import get_ucp_description, get_isbp_description
    
    desc = get_ucp_description("14")  # Returns article description
    desc = get_isbp_description("A14")  # Returns paragraph description
"""

from typing import Optional, Dict, Tuple
import re


# =============================================================================
# UCP600 Article Descriptions
# ICC Uniform Customs and Practice for Documentary Credits (2007 Revision)
# =============================================================================

UCP600_ARTICLES: Dict[str, str] = {
    # General Provisions
    "1": "Application of UCP",
    "2": "Definitions",
    "3": "Interpretations",
    "4": "Credits v. Contracts",
    "5": "Documents v. Goods, Services or Performance",
    
    # Availability and Expiry
    "6": "Availability, Expiry Date and Place for Presentation",
    "6(a)": "Credit must state bank with which it is available",
    "6(b)": "Credit available with nominated bank is also available with issuing bank",
    "6(c)": "Credit must state whether available by sight, deferred, acceptance or negotiation",
    "6(d)": "Documents must be presented within expiry date",
    "6(d)(i)": "Place for presentation is the place of the issuing bank",
    "6(d)(ii)": "Expiry date is deadline for presentation",
    "6(e)": "Except as provided in Article 29(a), presentation must be made on or before expiry date",
    
    # Issuing Bank Undertaking
    "7": "Issuing Bank Undertaking",
    "7(a)": "Issuing bank must honour if presentation is complying",
    "7(b)": "Issuing bank is irrevocably bound to honour from time of issuance",
    "7(c)": "Issuing bank undertakes to reimburse nominated bank",
    
    # Confirming Bank Undertaking
    "8": "Confirming Bank Undertaking",
    "8(a)": "Confirming bank must honour if presentation is complying",
    "8(b)": "Confirming bank is irrevocably bound from time of adding confirmation",
    
    # Advising
    "9": "Advising of Credits and Amendments",
    "10": "Amendments",
    
    # Nominations
    "11": "Teletransmitted and Pre-Advised Credits and Amendments",
    "12": "Nomination",
    
    # Reimbursement
    "13": "Bank-to-Bank Reimbursement Arrangements",
    
    # Examination of Documents
    "14": "Standard for Examination of Documents",
    "14(a)": "Banks must examine presentation to determine compliance on face of documents",
    "14(b)": "Bank has maximum 5 banking days following presentation for examination",
    "14(c)": "Data in documents must not conflict with each other",
    "14(d)": "Data in documents need not be identical but must not conflict with LC or other documents",
    "14(e)": "Documents not required by LC will be disregarded",
    "14(f)": "Document not required by LC but presented must be returned to presenter",
    "14(g)": "Document with same title as required may be accepted",
    "14(h)": "LC requiring multiple documents may be satisfied by any combination",
    "14(i)": "Original of transport document may bear date prior to LC issuance",
    "14(j)": "Addresses need not be same; contact details will be disregarded",
    "14(k)": "Shipper/consignor need not be beneficiary",
    "14(l)": "Transport document may be issued by party other than carrier",
    
    # Complying Presentation
    "15": "Complying Presentation",
    "15(a)": "When issuing bank determines presentation is complying, it must honour",
    "15(b)": "When confirming bank determines presentation is complying, it must honour",
    "15(c)": "When nominated bank determines presentation is complying, it must forward documents",
    
    # Discrepant Documents
    "16": "Discrepant Documents, Waiver and Notice",
    "16(a)": "Bank may refuse to honour if presentation does not comply",
    "16(b)": "Bank may approach applicant for waiver of discrepancies",
    "16(c)": "Bank must give single notice of refusal stating each discrepancy",
    "16(d)": "Notice must state disposition of documents",
    "16(e)": "Failure to act in accordance with 16(c) precludes claim of non-compliance",
    "16(f)": "If applicant waives discrepancies, issuing bank may honour",
    
    # Original Documents
    "17": "Original Documents and Copies",
    "17(a)": "At least one original of each required document must be presented",
    "17(b)": "Bank treats as original any document with original signature or stamp",
    "17(c)": "Unless document states otherwise, bank may accept as original",
    "17(d)": "If LC permits copy, original or copy may be presented",
    "17(e)": "If multiple originals required, number stated must be presented",
    
    # Commercial Invoice
    "18": "Commercial Invoice",
    "18(a)": "Invoice must appear to be issued by beneficiary",
    "18(a)(i)": "Invoice must be made out in name of applicant",
    "18(a)(ii)": "Invoice must be same currency as credit",
    "18(a)(iii)": "Invoice need not be signed",
    "18(b)": "Nominated bank may accept invoice for amount exceeding credit",
    "18(c)": "Description of goods must correspond with description in credit",
    
    # Transport Documents
    "19": "Transport Document Covering at Least Two Different Modes of Transport",
    "20": "Bill of Lading",
    "20(a)": "B/L must indicate name of carrier, be signed, indicate shipment and port details",
    "20(a)(i)": "B/L must indicate name of carrier",
    "20(a)(ii)": "B/L must be signed by carrier, master or agent",
    "20(a)(iii)": "B/L must indicate shipment from port of loading to port of discharge",
    "20(a)(iv)": "B/L must be sole original or full set if more than one issued",
    "20(a)(v)": "B/L must contain terms and conditions of carriage",
    "20(a)(vi)": "B/L must not indicate subject to charter party",
    "20(b)": "Transhipment means unloading and reloading during carriage",
    "20(c)": "B/L may indicate transhipment will or may take place",
    "20(d)": "Clauses in B/L not expressly declaring defective condition are acceptable",
    "20(e)": "Requirements when B/L states goods loaded on deck",
    
    # Other Transport Documents
    "21": "Non-Negotiable Sea Waybill",
    "22": "Charter Party Bill of Lading",
    "23": "Air Transport Document",
    "24": "Road, Rail or Inland Waterway Transport Documents",
    "25": "Courier Receipt, Post Receipt or Certificate of Posting",
    "26": "On Deck, Shipper's Load and Count, Said to Contain, and Charges Additional to Freight",
    
    # Clean Transport Document
    "27": "Clean Transport Document",
    
    # Insurance
    "28": "Insurance Document and Coverage",
    "28(a)": "Insurance document must appear to be issued by insurer",
    "28(b)": "Insurance coverage must be at least 110% of CIF/CIP value",
    "28(c)": "Insurance must be effective no later than date of shipment",
    "28(d)": "Insurance must cover at least from place of taking in charge to place of discharge",
    "28(e)": "Insurance must be in same currency as credit",
    "28(f)": "LC should state type of insurance and risks to be covered",
    "28(g)": "Insurance document may refer to exclusion clauses",
    "28(h)": "Cover note will not be accepted unless specifically authorized",
    "28(i)": "Insurance policy is acceptable in lieu of certificate or declaration",
    
    # Extension and Force Majeure
    "29": "Extension of Expiry Date or Last Day for Presentation",
    "29(a)": "If expiry or last presentation day falls on non-banking day, extended to next banking day",
    "29(b)": "Latest shipment date is not extended",
    "29(c)": "Bank must provide statement regarding extension",
    
    # Tolerances
    "30": "Tolerance in Credit Amount, Quantity and Unit Prices",
    "30(a)": "Words 'about' or 'approximately' allow 10% tolerance",
    "30(b)": "5% tolerance in quantity unless LC prohibits or specifies exact quantity",
    "30(c)": "If quantity fully drawn, 5% less in amount is acceptable",
    
    # Partial Drawings and Shipments
    "31": "Partial Drawings or Shipments",
    "32": "Instalment Drawings or Shipments",
    
    # Presentation Period
    "33": "Hours of Presentation",
    
    # Transferable Credits
    "38": "Transferable Credits",
    "38(a)": "Credit may be transferred if designated as transferable",
    "38(b)": "Transferring bank has no obligation to effect transfer",
    "38(c)": "If transfer charge is payable, first beneficiary must pay",
    "38(d)": "Credit may be transferred to more than one second beneficiary",
    "38(e)": "Request must specify if transfer to be made available at another place",
    "38(f)": "First beneficiary may request amendment be advised to second beneficiary",
    "38(g)": "Transferred credit may include specific changes",
    "38(h)": "First beneficiary may substitute invoices and drafts",
    "38(i)": "If first beneficiary fails to substitute, transferring bank may present documents",
    "38(j)": "First beneficiary may not transfer to more than one second beneficiary",
    "38(k)": "Presentation by second beneficiary must be made to transferring bank",
    
    # Assignment
    "39": "Assignment of Proceeds",
}


# =============================================================================
# ISBP745 Paragraph Descriptions
# ICC International Standard Banking Practice (2013 Revision)
# =============================================================================

ISBP745_PARAGRAPHS: Dict[str, str] = {
    # General Principles
    "A1": "General principles for examination of documents",
    "A2": "Documents must be presented within time limits",
    "A3": "Data in documents need not be mirror images",
    "A4": "Abbreviations generally acceptable",
    "A5": "Certification, declaration and statement requirements",
    "A6": "Address requirements",
    "A7": "Corrections and alterations must appear authenticated",
    "A8": "Dates can be in different formats",
    "A9": "Signature requirements",
    "A10": "Use of slash and comma",
    "A11": "Language of documents",
    "A12": "Mathematical calculations",
    "A13": "Documents not required by LC may be ignored",
    "A14": "Documents must be presented within LC validity period",
    "A15": "Original documents requirements",
    "A16": "Documents issued prior to LC date are acceptable",
    "A17": "Issuer identification requirements",
    "A18": "Titles of documents",
    "A19": "Multiple documents requirements",
    "A20": "Document issuance time requirements",
    "A21": "Signing of documents",
    "A22": "Stamps on documents",
    "A23": "Copy document requirements",
    "A24": "Data not appearing in documents",
    "A25": "Extraneous/irrelevant information",
    "A26": "Non-documentary conditions",
    "A27": "Expiry date and latest presentation considerations",
    "A28": "Stale documents",
    "A29": "Applicant name and address",
    "A30": "Beneficiary name and address",
    "A31": "Shipping marks",
    "A32": "Quantity, weight and measurements",
    "A33": "Goods description",
    "A34": "Unit price/amount variations",
    "A35": "Trade terms (Incoterms)",
    
    # Drafts and Commercial Documents
    "B1": "Draft requirements",
    "B2": "Draft tenor",
    "B3": "Draft amount",
    "B4": "Draft on applicant",
    "B5": "Draft maturity date",
    "B6": "Draft endorsement",
    "B7": "Amounts in words and figures",
    "B8": "Alterations on drafts",
    "B9": "Correction of draft amount",
    
    # Commercial Invoice
    "C1": "Commercial invoice data requirements",
    "C2": "Invoice must be issued by beneficiary",
    "C3": "Invoice amount and currency must match LC",
    "C4": "Invoice applicant requirements",
    "C5": "Goods description must match LC",
    "C6": "Quantity and weight requirements",
    "C7": "Trade terms on invoice",
    "C8": "Charges on invoice",
    "C9": "Additional data on invoice",
    "C10": "Invoice copies",
    "C11": "Invoice corrections",
    "C12": "Pro forma invoice",
    "C13": "Provisional invoice",
    
    # Transport Documents General
    "D1": "General requirements for transport documents",
    "D2": "Full set of originals",
    "D3": "Carrier identification",
    "D4": "Signing of transport documents",
    "D5": "Onboard notation",
    "D6": "Date of shipment",
    "D7": "Port to port/place to place",
    "D8": "Consignee and notify party",
    "D9": "Shipper requirements",
    "D10": "Freight and charges",
    "D11": "Good order and condition",
    "D12": "Deck cargo",
    "D13": "Clean transport document",
    "D14": "Pre-carriage and place of receipt",
    "D15": "Transhipment",
    "D16": "Short form transport documents",
    
    # Bill of Lading
    "E1": "Application of B/L articles",
    "E2": "Full set of B/L originals required",
    "E3": "B/L must indicate name of carrier",
    "E4": "B/L signing requirements",
    "E5": "On board notation requirements",
    "E6": "Port of loading and discharge",
    "E7": "Consignee requirements on B/L",
    "E8": "Notify party on B/L",
    "E9": "Shipper on B/L",
    "E10": "Order B/L endorsement",
    "E11": "B/L freight indication",
    "E12": "B/L requirements and clauses",
    "E13": "Clean B/L requirements",
    "E14": "Goods and marks on B/L",
    "E15": "Corrections on B/L",
    "E16": "Received for shipment B/L",
    "E17": "Transhipment on B/L",
    "E18": "On deck cargo on B/L",
    "E19": "Charter party B/L",
    "E20": "Combined transport B/L",
    
    # Other Transport Documents
    "F1": "Non-negotiable sea waybill",
    "G1": "Charter party bill of lading",
    "H1": "Air transport document",
    "J1": "Road transport document",
    "K1": "Rail transport document",
    "L1": "Inland waterway transport document",
    "M1": "Courier/post receipt",
    
    # Insurance
    "N1": "Insurance document requirements",
    "N2": "Insurance coverage amount",
    "N3": "Insurance effective date",
    "N4": "Risks covered",
    "N5": "Insurance claims payable location",
    "N6": "Insurance certificate vs policy",
    "N7": "Insurance cover note",
    "N8": "Endorsement of insurance",
    "N9": "Insurance broker/agent",
    "N10": "Exclusion clauses",
    
    # Certificate of Origin
    "O1": "Certificate of origin requirements",
    "O2": "Origin certification",
    "O3": "GSP Form A",
    
    # Packing and Weight
    "P1": "Packing list requirements",
    "P2": "Weight list/certificate",
    "P3": "Inspection certificate",
    
    # Miscellaneous
    "Q1": "Analysis/inspection certificates",
    "Q2": "Health/phytosanitary certificate",
    "Q3": "Beneficiary certificate",
    "Q4": "Shipping company certificate",
}


def get_ucp_description(reference: str) -> Optional[str]:
    """
    Get human-readable description for a UCP600 article reference.
    
    Args:
        reference: UCP600 reference string, e.g., "14", "14(a)", "UCP600 Article 14"
        
    Returns:
        Description string or None if not found
    """
    if not reference:
        return None
    
    # Extract article number from various formats
    # "UCP600 Article 14(a)" -> "14(a)"
    # "Article 14" -> "14"
    # "14(a)" -> "14(a)"
    match = re.search(r"(?:Article\s*)?(\d+(?:\([a-z]\))?(?:\([ivx]+\))?)", reference, re.IGNORECASE)
    if match:
        article = match.group(1)
        return UCP600_ARTICLES.get(article)
    
    return UCP600_ARTICLES.get(reference)


def get_isbp_description(reference: str) -> Optional[str]:
    """
    Get human-readable description for an ISBP745 paragraph reference.
    
    Args:
        reference: ISBP745 reference string, e.g., "A14", "ISBP745 A14", "¶A14"
        
    Returns:
        Description string or None if not found
    """
    if not reference:
        return None
    
    # Extract paragraph from various formats
    # "ISBP745 A14" -> "A14"
    # "¶A14" -> "A14"
    # "Paragraph A14" -> "A14"
    match = re.search(r"(?:¶|Paragraph\s*)?([A-Z]\d+)", reference, re.IGNORECASE)
    if match:
        paragraph = match.group(1).upper()
        return ISBP745_PARAGRAPHS.get(paragraph)
    
    return ISBP745_PARAGRAPHS.get(reference.upper() if reference else "")


def enrich_issue_with_descriptions(
    ucp_reference: Optional[str],
    isbp_reference: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get both UCP600 and ISBP745 descriptions for an issue.
    
    Args:
        ucp_reference: UCP600 reference string
        isbp_reference: ISBP745 reference string
        
    Returns:
        Tuple of (ucp_description, isbp_description)
    """
    return (
        get_ucp_description(ucp_reference),
        get_isbp_description(isbp_reference)
    )
