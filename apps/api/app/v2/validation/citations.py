"""
Citation Library

Maps rule IDs and issue types to UCP600/ISBP745 citations.
THIS IS THE KEY DIFFERENTIATOR - every issue MUST have citations.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from ..core.types import Citations


# ============================================================================
# UCP600 ARTICLE DEFINITIONS
# ============================================================================

UCP600_ARTICLES = {
    # Article 14 - Standard for Examination of Documents
    "14": "Standard for Examination of Documents",
    "14(a)": "Banks must examine on face, to determine compliance",
    "14(b)": "5 banking days for examination",
    "14(c)": "Data not conflicting with data in other documents",
    "14(d)": "Data need not be identical but must not conflict",
    "14(e)": "In documents other than commercial invoice...",
    "14(f)": "Documents not called for will be disregarded",
    "14(g)": "Non-documentary conditions deemed not stated",
    "14(h)": "When credit requires presentation of document other than transport",
    "14(i)": "Banks will accept document dated prior to issuance date",
    "14(j)": "Addresses of parties need not match those in credit",
    "14(k)": "Contact details of shipper/consignee not examined",
    "14(l)": "Transport document may indicate goods loaded in containers",
    
    # Article 18 - Commercial Invoice
    "18": "Commercial Invoice",
    "18(a)": "Invoice must appear to be issued by beneficiary",
    "18(b)": "Invoice must be made out in name of applicant",
    "18(c)": "Invoice need not be signed",
    "18(d)": "Description must correspond with credit description",
    
    # Article 19 - Transport Document Covering at least Two Modes
    "19": "Multimodal Transport Document",
    "19(a)": "Must indicate name of carrier",
    "19(b)": "Signed by carrier/agent/master",
    "19(c)": "Indicate goods received/dispatched/shipped",
    
    # Article 20 - Bill of Lading
    "20": "Bill of Lading",
    "20(a)": "B/L must name carrier and be signed",
    "20(b)": "If master signs, indicate name of master",
    "20(c)": "Indicate goods shipped on board",
    "20(d)": "Indicate port of loading and discharge",
    "20(e)": "Be sole original or full set",
    "20(f)": "Contain terms and conditions",
    "20(g)": "Deck cargo if stated",
    
    # Article 21 - Non-Negotiable Sea Waybill
    "21": "Non-Negotiable Sea Waybill",
    
    # Article 22 - Charter Party Bill of Lading
    "22": "Charter Party Bill of Lading",
    
    # Article 23 - Air Transport Document
    "23": "Air Transport Document",
    
    # Article 24 - Road, Rail or Inland Waterway Transport
    "24": "Road, Rail or Inland Waterway Transport",
    
    # Article 25 - Courier Receipt, Post Receipt
    "25": "Courier Receipt, Post Receipt",
    
    # Article 26 - "On Deck", "Shipper's Load and Count"
    "26": "On Deck, Shipper's Load and Count, Name of Consignor",
    
    # Article 27 - Clean Transport Document
    "27": "Clean Transport Document",
    
    # Article 28 - Insurance Document
    "28": "Insurance Document and Coverage",
    "28(a)": "Insurance document must name insured",
    "28(b)": "Insurance must be dated",
    "28(c)": "Insurance amount (min 110%)",
    "28(d)": "Insurance coverage",
    "28(e)": "Insured value",
    "28(f)": "Insurance must cover credit goods",
    "28(g)": "Insurance coverage types",
    "28(h)": "Insurance exclusions",
    "28(i)": "Insurance endorsement",
    
    # Article 29 - Extension of Expiry Date/Period for Presentation
    "29": "Extension of Expiry Date",
    
    # Article 30 - Tolerance in Credit Amount, Quantity and Unit Prices
    "30": "Tolerance in Credit Amount, Quantity and Unit Prices",
    "30(a)": "+/- 10% tolerance on quantity",
    "30(b)": "+/- 5% tolerance on unit price",
    
    # Article 31 - Partial Drawings
    "31": "Partial Drawings or Shipments",
    
    # Article 32 - Instalment Drawings
    "32": "Instalment Drawings or Shipments",
    
    # Article 33 - Hours of Presentation
    "33": "Hours of Presentation",
    
    # Article 34 - Disclaimer on Effectiveness of Documents
    "34": "Disclaimer on Effectiveness of Documents",
    
    # Article 35 - Disclaimer on Transmission and Translation
    "35": "Disclaimer on Transmission and Translation",
    
    # Article 36 - Force Majeure
    "36": "Force Majeure",
    
    # Article 37 - Disclaimer for Acts of Instructed Party
    "37": "Disclaimer for Acts of an Instructed Party",
    
    # Article 38 - Transferable Credits
    "38": "Transferable Credits",
    
    # Article 39 - Assignment of Proceeds
    "39": "Assignment of Proceeds",
}

# ============================================================================
# ISBP745 PARAGRAPHS
# ============================================================================

ISBP745_PARAGRAPHS = {
    # General Principles
    "1": "Abbreviations - generally acceptable",
    "2": "Addresses",
    "3": "Applicant",
    "4": "Beneficiary",
    "5": "Branches",
    "6": "Certificates and declarations",
    "7": "Clauses to be stamped or otherwise authenticated",
    "8": "Combined invoices",
    "9": "Compliance with L/C terms",
    "10": "Consistency between data in required documents",
    "11": "Consular attestation",
    "12": "Contact details",
    "13": "Copies of documents",
    "14": "Copy of transport document",
    "15": "Correction of documents",
    "16": "Courier and post receipts",
    "17": "Dating of documents",
    "18": "Default in L/C conditions",
    "19": "Description of goods, services or performance",
    "20": "Documents completed in more than one language",
    "21": "Documents for which L/C is silent",
    "22": "Drawing amount and tolerance",
    "23": "Earliest dates",
    "24": "Email address and URL",
    "25": "Examination of documents",
    "26": "Expressions not defined",
    "27": "Extension of expiry date",
    "28": "Insurance",
    "29": "Instalment drawings",
    "30": "Language of documents",
    
    # Commercial Invoice
    "72": "Commercial invoice - issued by beneficiary",
    "73": "Commercial invoice - description",
    "73(a)": "Description must correspond to LC",
    "74": "Commercial invoice - quantity and price",
    "75": "Commercial invoice - amendments",
    
    # Transport Documents
    "95": "Transport document - shipper",
    "96": "Transport document - consignee",
    "97": "Transport document - notify party",
    "98": "Transport document - on board notation",
    
    # Bill of Lading
    "107": "B/L - carrier identification",
    "108": "B/L - signing",
    "109": "B/L - on board date",
    "110": "B/L - port of loading",
    "111": "B/L - port of discharge",
    "112": "B/L - full set",
    
    # Insurance
    "165": "Insurance - amount",
    "166": "Insurance - risks covered",
    "167": "Insurance - currency",
    "168": "Insurance - parties",
    
    # Certificate of Origin
    "185": "Origin - issuing party",
    "186": "Origin - goods description",
    "187": "Origin - country statement",
}


# ============================================================================
# RULE TO CITATION MAPPING
# ============================================================================

@dataclass
class CitationMapping:
    """Mapping from issue type to citations."""
    ucp600: List[str]
    isbp745: List[str]
    description: str


# Master mapping of rule patterns to citations
CITATION_MAPPINGS: Dict[str, CitationMapping] = {
    # Amount/Value Issues
    "amount_mismatch": CitationMapping(
        ucp600=["18(d)", "30"],
        isbp745=["74", "22"],
        description="Invoice amount vs LC amount discrepancy"
    ),
    "amount_exceeds": CitationMapping(
        ucp600=["18(d)", "30(a)"],
        isbp745=["22"],
        description="Invoice amount exceeds LC amount"
    ),
    "tolerance_exceeded": CitationMapping(
        ucp600=["30", "30(a)", "30(b)"],
        isbp745=["22"],
        description="Amount or quantity tolerance exceeded"
    ),
    
    # Description Issues
    "description_mismatch": CitationMapping(
        ucp600=["18(c)", "14(d)"],
        isbp745=["19", "73", "73(a)"],
        description="Goods description does not match LC"
    ),
    "goods_description": CitationMapping(
        ucp600=["18(c)", "14(d)"],
        isbp745=["19", "73"],
        description="Goods description discrepancy"
    ),
    
    # Party Issues
    "beneficiary_mismatch": CitationMapping(
        ucp600=["18(a)", "14(j)"],
        isbp745=["4", "72"],
        description="Beneficiary name discrepancy"
    ),
    "applicant_mismatch": CitationMapping(
        ucp600=["18(b)", "14(j)"],
        isbp745=["3"],
        description="Applicant name discrepancy"
    ),
    "consignee_mismatch": CitationMapping(
        ucp600=["20(d)", "14(d)"],
        isbp745=["96"],
        description="Consignee discrepancy"
    ),
    "shipper_mismatch": CitationMapping(
        ucp600=["20(a)", "14(d)"],
        isbp745=["95"],
        description="Shipper discrepancy"
    ),
    "notify_party": CitationMapping(
        ucp600=["14(d)"],
        isbp745=["97"],
        description="Notify party discrepancy"
    ),
    
    # Date Issues
    "late_shipment": CitationMapping(
        ucp600=["14(c)", "29"],
        isbp745=["109"],
        description="Shipment after latest shipment date"
    ),
    "late_presentation": CitationMapping(
        ucp600=["14(b)", "29"],
        isbp745=["27"],
        description="Late presentation of documents"
    ),
    "expired_lc": CitationMapping(
        ucp600=["29"],
        isbp745=["27"],
        description="LC expired"
    ),
    "date_mismatch": CitationMapping(
        ucp600=["14(c)", "14(i)"],
        isbp745=["17", "23"],
        description="Date inconsistency"
    ),
    "invoice_date": CitationMapping(
        ucp600=["14(i)"],
        isbp745=["17"],
        description="Invoice date issue"
    ),
    
    # Transport Document Issues
    "bl_not_clean": CitationMapping(
        ucp600=["27"],
        isbp745=["112"],
        description="Bill of lading not clean"
    ),
    "on_board_date": CitationMapping(
        ucp600=["20(a)(ii)"],
        isbp745=["98", "109"],
        description="On board date discrepancy"
    ),
    "port_loading": CitationMapping(
        ucp600=["20(a)(iii)"],
        isbp745=["110"],
        description="Port of loading discrepancy"
    ),
    "port_discharge": CitationMapping(
        ucp600=["20(a)(iii)"],
        isbp745=["111"],
        description="Port of discharge discrepancy"
    ),
    "carrier_signature": CitationMapping(
        ucp600=["20(a)(i)"],
        isbp745=["107", "108"],
        description="Carrier/master signature issue"
    ),
    "full_set_bl": CitationMapping(
        ucp600=["20(a)(iv)"],
        isbp745=["112"],
        description="Full set of B/L not presented"
    ),
    
    # Insurance Issues
    "insurance_amount": CitationMapping(
        ucp600=["28(b)", "28(f)(ii)"],
        isbp745=["165"],
        description="Insurance amount insufficient (min 110%)"
    ),
    "insurance_coverage": CitationMapping(
        ucp600=["28(g)", "28(h)"],
        isbp745=["166"],
        description="Insurance coverage discrepancy"
    ),
    "insurance_currency": CitationMapping(
        ucp600=["28(f)(i)"],
        isbp745=["167"],
        description="Insurance currency mismatch"
    ),
    "insurance_date": CitationMapping(
        ucp600=["28(e)"],
        isbp745=["168"],
        description="Insurance date issue"
    ),
    
    # Origin Certificate Issues
    "origin_country": CitationMapping(
        ucp600=["14(d)"],
        isbp745=["185", "187"],
        description="Country of origin discrepancy"
    ),
    "origin_description": CitationMapping(
        ucp600=["14(d)"],
        isbp745=["186"],
        description="Origin certificate goods description"
    ),
    
    # Document Issues
    "missing_document": CitationMapping(
        ucp600=["14(a)"],
        isbp745=["21"],
        description="Required document missing"
    ),
    "document_inconsistency": CitationMapping(
        ucp600=["14(c)", "14(d)"],
        isbp745=["10"],
        description="Documents contain conflicting data"
    ),
    "unsigned_document": CitationMapping(
        ucp600=["14(a)"],
        isbp745=["6"],
        description="Required signature missing"
    ),
    "document_language": CitationMapping(
        ucp600=["14(a)"],
        isbp745=["30"],
        description="Document language issue"
    ),
    
    # Quantity Issues
    "quantity_mismatch": CitationMapping(
        ucp600=["30(a)"],
        isbp745=["74"],
        description="Quantity discrepancy"
    ),
    
    # General
    "data_conflict": CitationMapping(
        ucp600=["14(d)"],
        isbp745=["10"],
        description="Data conflict between documents"
    ),
}


class CitationLibrary:
    """
    Citation library for looking up UCP600/ISBP745 references.
    
    EVERY issue in V2 MUST have citations. No exceptions.
    """
    
    @staticmethod
    def get_citations(issue_type: str) -> Citations:
        """
        Get citations for an issue type.
        
        Args:
            issue_type: Type of issue (e.g., 'amount_mismatch', 'late_shipment')
            
        Returns:
            Citations with UCP600 and ISBP745 references
        """
        # Try exact match first
        mapping = CITATION_MAPPINGS.get(issue_type.lower())
        
        if mapping:
            return Citations(
                ucp600=mapping.ucp600,
                isbp745=mapping.isbp745,
            )
        
        # Try partial match
        for key, mapping in CITATION_MAPPINGS.items():
            if key in issue_type.lower() or issue_type.lower() in key:
                return Citations(
                    ucp600=mapping.ucp600,
                    isbp745=mapping.isbp745,
                )
        
        # Default fallback - at minimum cite Article 14
        return Citations(
            ucp600=["14(a)"],
            isbp745=[],
        )
    
    @staticmethod
    def get_citations_for_field(field_name: str) -> Citations:
        """Get citations based on field name."""
        field_mappings = {
            "amount": ["18(d)", "30"],
            "currency": ["18(d)"],
            "description": ["18(c)", "14(d)"],
            "goods": ["18(c)", "14(d)"],
            "beneficiary": ["18(a)"],
            "applicant": ["18(b)"],
            "consignee": ["20(d)"],
            "shipper": ["20(a)"],
            "port": ["20(a)(iii)"],
            "date": ["14(c)"],
            "expiry": ["29"],
            "shipment": ["29"],
            "insurance": ["28"],
            "bl": ["20"],
            "origin": ["14(d)"],
        }
        
        field_lower = field_name.lower()
        for key, articles in field_mappings.items():
            if key in field_lower:
                return Citations(ucp600=articles, isbp745=[])
        
        return Citations(ucp600=["14(a)"], isbp745=[])
    
    @staticmethod
    def format_bank_message(title: str, citations: Citations) -> str:
        """Format message for bank examiner."""
        citation_str = citations.format()
        if citation_str:
            return f"{title}. Per {citation_str}."
        return title
    
    @staticmethod
    def get_article_description(article: str) -> str:
        """Get description of UCP600 article."""
        return UCP600_ARTICLES.get(article, f"Article {article}")
    
    @staticmethod
    def get_paragraph_description(paragraph: str) -> str:
        """Get description of ISBP745 paragraph."""
        return ISBP745_PARAGRAPHS.get(paragraph, f"Paragraph {paragraph}")
    
    @staticmethod
    def enrich_citations(citations: Citations) -> Dict[str, str]:
        """Enrich citations with descriptions."""
        enriched = {}
        
        for art in citations.ucp600:
            desc = UCP600_ARTICLES.get(art, "")
            enriched[f"UCP600 Article {art}"] = desc
        
        for para in citations.isbp745:
            desc = ISBP745_PARAGRAPHS.get(para, "")
            enriched[f"ISBP745 Paragraph {para}"] = desc
        
        return enriched

