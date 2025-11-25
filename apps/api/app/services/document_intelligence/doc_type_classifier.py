"""
Document Type Classifier - Phase 0.1

Content-based document classification using pattern matching and text analysis.
Identifies document types from OCR text before validation begins.

Detection Strategy:
1. SWIFT MT700 patterns → Letter of Credit
2. Invoice structure patterns → Commercial Invoice
3. B/L patterns → Bill of Lading
4. Origin certification patterns → Certificate of Origin
5. Insurance/coverage patterns → Insurance Certificate
6. Item list + weight patterns → Packing List
7. Inspection/analysis patterns → Inspection Certificate
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from app.models import DocumentType


logger = logging.getLogger(__name__)


class ClassificationConfidence(str, Enum):
    """Confidence level of document classification."""
    HIGH = "high"        # >= 0.85 - Strong pattern match
    MEDIUM = "medium"    # >= 0.60 - Moderate pattern match  
    LOW = "low"          # >= 0.40 - Weak pattern match
    UNKNOWN = "unknown"  # < 0.40 - Insufficient patterns


@dataclass
class ClassificationResult:
    """Result of document type classification."""
    document_type: DocumentType
    confidence: float  # 0.0 to 1.0
    confidence_level: ClassificationConfidence
    matched_patterns: List[str]
    reasoning: str
    alternative_types: List[Tuple[DocumentType, float]]  # Other possible types
    is_reliable: bool  # True if confidence >= 0.60


# ---------------------------------------------------------------------------
# Pattern Definitions for Each Document Type
# ---------------------------------------------------------------------------

# SWIFT MT700 Letter of Credit patterns (very distinctive)
LC_PATTERNS = {
    # SWIFT field tags (highly distinctive)
    "swift_field_27": r":27:[\s\S]{0,30}SEQUENCE",
    "swift_field_40A": r":40[A-E]:",
    "swift_field_20": r":20:[A-Z0-9/-]+",
    "swift_field_31C": r":31C:\d{6}",
    "swift_field_31D": r":31D:\d{6}",
    "swift_field_32B": r":32B:[A-Z]{3}[\d,\.]+",
    "swift_field_39A": r":39[A-C]:",
    "swift_field_41A": r":41[A-D]:",
    "swift_field_42C": r":42[A-M]:",
    "swift_field_43P": r":43[A-T]:",
    "swift_field_44": r":44[A-Z]:",
    "swift_field_45A": r":45A:",
    "swift_field_46A": r":46A:",
    "swift_field_47A": r":47A:",
    "swift_field_48": r":48:",
    "swift_field_49": r":49:",
    "swift_field_50": r":50:",
    "swift_field_59": r":59:",
    "swift_field_71": r":71[A-D]:",
    "swift_field_72": r":72:",
    "swift_field_78": r":78:",
    
    # LC terminology
    "irrevocable": r"\bIRREVOCABLE\b",
    "documentary_credit": r"DOCUMENTARY\s*CREDIT",
    "letter_of_credit": r"LETTER\s*OF\s*CREDIT",
    "beneficiary": r"\bBENEFICIARY\b",
    "applicant": r"\bAPPLICANT\b",
    "issuing_bank": r"ISSUING\s*BANK",
    "advising_bank": r"ADVISING\s*BANK",
    "confirming_bank": r"CONFIRMING\s*BANK",
    "available_with": r"AVAILABLE\s*WITH",
    "available_by": r"AVAILABLE\s*BY",
    "draft_at": r"DRAFT[S]?\s*(AT|DRAWN)",
    "expiry_date": r"EXPIR[YE]\s*DATE",
    "latest_shipment": r"LATEST\s*(DATE\s*OF\s*)?SHIPMENT",
    "partial_shipments": r"PARTIAL\s*SHIPMENTS",
    "transshipment": r"TRANS[\-\s]?SHIPMENT",
    "documents_required": r"DOCUMENTS?\s*REQUIRED",
    "presentation_period": r"PRESENTATION\s*PERIOD",
    "ucp600": r"UCP\s*6?00",
    "ucp_latest": r"UCP\s*LATEST\s*VERSION",
    "isbp": r"ISBP\s*7?45",
    
    # SWIFT message type indicators
    "mt700": r"MT\s*700",
    "mt710": r"MT\s*710",
    "mt720": r"MT\s*720",
    "mt707": r"MT\s*707",
}

# Commercial Invoice patterns
INVOICE_PATTERNS = {
    "invoice_header": r"\bINVOICE\b",
    "commercial_invoice": r"COMMERCIAL\s*INVOICE",
    "proforma_invoice": r"PRO[\-\s]?FORMA\s*INVOICE",
    "invoice_number": r"INVOICE\s*(NO\.?|NUMBER|#)\s*:?\s*[\w\-/]+",
    "invoice_date": r"INVOICE\s*DATE\s*:?",
    "unit_price": r"UNIT\s*PRICE",
    "total_amount": r"TOTAL\s*(AMOUNT|VALUE)",
    "subtotal": r"SUB[\-\s]?TOTAL",
    "grand_total": r"GRAND\s*TOTAL",
    "payment_terms": r"PAYMENT\s*TERMS?",
    "bill_to": r"BILL\s*TO",
    "ship_to": r"SHIP\s*TO",
    "sold_to": r"SOLD\s*TO",
    "hs_code": r"\bH\.?S\.?\s*(CODE|TARIFF)",
    "line_items": r"(QTY|QUANTITY|DESCRIPTION|AMOUNT)\s*\n",
    "currency_amount": r"(USD|EUR|GBP|CNY|JPY)\s*[\d,\.]+",
    "fob_cif": r"\b(FOB|CIF|CFR|CIP|DAP|DDP|EXW)\b",
}

# Bill of Lading patterns
BL_PATTERNS = {
    "bill_of_lading": r"BILL\s*OF\s*LADING",
    "bl_header": r"\bB/L\b|\bBL\b(?!\s*NUMBER)",
    "ocean_bl": r"OCEAN\s*BILL\s*OF\s*LADING",
    "sea_waybill": r"SEA\s*WAY[\-\s]?BILL",
    "multimodal": r"MULTI[\-\s]?MODAL",
    "shipper": r"\bSHIPPER\b",
    "consignee": r"\bCONSIGNEE\b",
    "notify_party": r"NOTIFY\s*PARTY",
    "vessel": r"\bVESSEL\b",
    "voyage": r"\bVOYAGE\b",
    "port_of_loading": r"PORT\s*OF\s*LOADING",
    "port_of_discharge": r"PORT\s*OF\s*DISCHARGE",
    "place_of_receipt": r"PLACE\s*OF\s*RECEIPT",
    "place_of_delivery": r"PLACE\s*OF\s*DELIVERY",
    "container_no": r"CONTAINER\s*(NO\.?|NUMBER)",
    "seal_no": r"SEAL\s*(NO\.?|NUMBER)",
    "freight_prepaid": r"FREIGHT\s*(PRE[\-]?PAID|COLLECT)",
    "on_board": r"ON[\-\s]?BOARD",
    "shipped_on_board": r"SHIPPED\s*ON\s*BOARD",
    "clean_bl": r"CLEAN\s*(ON\s*BOARD)?",
    "gross_weight": r"GROSS\s*WEIGHT",
    "measurement": r"MEASUREMENT",
    "marks_numbers": r"MARKS\s*(AND|&)\s*NUMBERS?",
    "number_of_originals": r"(THREE|3)\s*ORIGINALS?",
    "carrier": r"\bCARRIER\b",
    "master": r"MASTER\s*(SIGNATURE)?",
}

# Packing List patterns
PACKING_LIST_PATTERNS = {
    "packing_list": r"PACKING\s*LIST",
    "pack_list": r"PACK[\-\s]?LIST",
    "item_list": r"ITEM\s*LIST",
    "carton_no": r"CARTON\s*(NO\.?|NUMBER)",
    "box_no": r"BOX\s*(NO\.?|NUMBER)",
    "net_weight": r"NET\s*WEIGHT",
    "gross_weight_pl": r"GROSS\s*WEIGHT",
    "dimensions": r"DIMENSIONS?|L\s*[xX×]\s*W\s*[xX×]\s*H",
    "cbm": r"\bCBM\b|CUBIC\s*METER",
    "pieces": r"\bPCS\b|\bPIECES?\b",
    "total_cartons": r"TOTAL\s*CARTONS?",
    "total_packages": r"TOTAL\s*PACKAGES?",
    "packed_by": r"PACKED\s*BY",
}

# Certificate of Origin patterns
CO_PATTERNS = {
    "certificate_of_origin": r"CERTIFICATE\s*OF\s*ORIGIN",
    "origin_cert": r"ORIGIN\s*CERTIFICATE",
    "country_of_origin": r"COUNTRY\s*OF\s*ORIGIN",
    "manufactured_in": r"MANUFACTURED\s*IN",
    "produced_in": r"PRODUCED\s*IN",
    "made_in": r"MADE\s*IN",
    "chamber_of_commerce": r"CHAMBER\s*OF\s*COMMERCE",
    "trade_association": r"TRADE\s*ASSOCIATION",
    "gsp": r"\bGSP\b|GENERALIZED\s*SYSTEM",
    "form_a": r"FORM\s*A",
    "preference": r"PREFERENCE\s*CERTIFICATE",
    "eur1": r"\bEUR[\.\s]?1\b",
    "origin_declaration": r"ORIGIN\s*DECLARATION",
    "attested": r"ATTESTED|CERTIFIED|LEGALIZED",
}

# Insurance Certificate patterns
INSURANCE_PATTERNS = {
    "insurance_certificate": r"INSURANCE\s*CERTIFICATE",
    "insurance_policy": r"INSURANCE\s*POLICY",
    "certificate_of_insurance": r"CERTIFICATE\s*OF\s*INSURANCE",
    "marine_insurance": r"MARINE\s*(CARGO\s*)?INSURANCE",
    "cargo_insurance": r"CARGO\s*INSURANCE",
    "insured_value": r"INSURED\s*(VALUE|AMOUNT)",
    "sum_insured": r"SUM\s*INSURED",
    "coverage": r"\bCOVERAGE\b",
    "all_risks": r"ALL\s*RISKS?",
    "icc_a": r"ICC\s*[\(\[]?A[\)\]]?",
    "icc_b": r"ICC\s*[\(\[]?B[\)\]]?",
    "icc_c": r"ICC\s*[\(\[]?C[\)\]]?",
    "institute_cargo_clauses": r"INSTITUTE\s*CARGO\s*CLAUSES?",
    "war_risk": r"WAR\s*(RISK|CLAUSE)",
    "strikes_clause": r"STRIKES?\s*(RISK|CLAUSE)",
    "premium": r"\bPREMIUM\b",
    "deductible": r"DEDUCTIBLE|EXCESS",
    "claims_payable": r"CLAIMS?\s*PAYABLE",
    "underwriter": r"UNDERWRITER",
    "policy_number": r"POLICY\s*(NO\.?|NUMBER)",
    "cif_110": r"CIF\s*\+?\s*10\s*%?|110\s*%?\s*OF\s*(CIF|INVOICE)",
}

# Inspection Certificate patterns
INSPECTION_PATTERNS = {
    "inspection_certificate": r"INSPECTION\s*CERTIFICATE",
    "certificate_of_inspection": r"CERTIFICATE\s*OF\s*INSPECTION",
    "quality_certificate": r"QUALITY\s*CERTIFICATE",
    "analysis_certificate": r"(CERTIFICATE\s*OF\s*)?ANALYSIS",
    "test_report": r"TEST\s*REPORT",
    "survey_report": r"SURVEY\s*REPORT",
    "inspection_report": r"INSPECTION\s*REPORT",
    "sgs": r"\bSGS\b",
    "bureau_veritas": r"BUREAU\s*VERITAS",
    "intertek": r"INTERTEK",
    "cotecna": r"COTECNA",
    "pre_shipment": r"PRE[\-\s]?SHIPMENT\s*INSPECTION",
    "psi": r"\bPSI\b",
    "findings": r"FINDINGS?|RESULTS?",
    "conforms": r"CONFORM[S]?\s*TO",
    "complies": r"COMPL(Y|IES)\s*WITH",
    "specifications": r"SPECIFICATIONS?",
    "sample": r"\bSAMPLE[S]?\b",
    "tested": r"\bTESTED\b",
    "inspected": r"\bINSPECTED\b",
    "inspector": r"\bINSPECTOR\b",
}


class DocumentTypeClassifier:
    """
    Content-based document type classifier.
    
    Uses pattern matching against OCR text to identify document types
    before validation begins. This prevents silent misclassification
    when documents are uploaded in wrong slots or with wrong filenames.
    """
    
    # Pattern weights: higher = more distinctive for that document type
    PATTERN_WEIGHTS = {
        DocumentType.LETTER_OF_CREDIT: {
            "swift_field_*": 3.0,      # SWIFT tags are highly distinctive
            "mt700": 3.0,
            "documentary_credit": 2.5,
            "letter_of_credit": 2.5,
            "irrevocable": 2.0,
            "ucp600": 2.0,
            "beneficiary": 1.5,
            "applicant": 1.5,
            "available_with": 1.5,
            "default": 1.0,
        },
        DocumentType.COMMERCIAL_INVOICE: {
            "invoice_number": 2.5,
            "commercial_invoice": 2.5,
            "unit_price": 2.0,
            "total_amount": 2.0,
            "bill_to": 1.5,
            "line_items": 1.5,
            "default": 1.0,
        },
        DocumentType.BILL_OF_LADING: {
            "bill_of_lading": 3.0,
            "ocean_bl": 3.0,
            "shipped_on_board": 2.5,
            "consignee": 2.0,
            "notify_party": 2.0,
            "vessel": 1.5,
            "voyage": 1.5,
            "port_of_loading": 1.5,
            "port_of_discharge": 1.5,
            "default": 1.0,
        },
        DocumentType.PACKING_LIST: {
            "packing_list": 3.0,
            "carton_no": 2.0,
            "total_cartons": 2.0,
            "cbm": 1.5,
            "dimensions": 1.5,
            "default": 1.0,
        },
        DocumentType.CERTIFICATE_OF_ORIGIN: {
            "certificate_of_origin": 3.0,
            "country_of_origin": 2.5,
            "chamber_of_commerce": 2.0,
            "gsp": 2.0,
            "form_a": 2.0,
            "default": 1.0,
        },
        DocumentType.INSURANCE_CERTIFICATE: {
            "insurance_certificate": 3.0,
            "marine_insurance": 2.5,
            "all_risks": 2.0,
            "icc_a": 2.0,
            "sum_insured": 2.0,
            "claims_payable": 1.5,
            "default": 1.0,
        },
        DocumentType.INSPECTION_CERTIFICATE: {
            "inspection_certificate": 3.0,
            "quality_certificate": 2.5,
            "sgs": 2.0,
            "bureau_veritas": 2.0,
            "pre_shipment": 2.0,
            "test_report": 1.5,
            "default": 1.0,
        },
    }
    
    # Minimum score thresholds for each document type
    MIN_SCORE_THRESHOLDS = {
        DocumentType.LETTER_OF_CREDIT: 8.0,
        DocumentType.COMMERCIAL_INVOICE: 5.0,
        DocumentType.BILL_OF_LADING: 6.0,
        DocumentType.PACKING_LIST: 4.0,
        DocumentType.CERTIFICATE_OF_ORIGIN: 5.0,
        DocumentType.INSURANCE_CERTIFICATE: 5.0,
        DocumentType.INSPECTION_CERTIFICATE: 5.0,
    }
    
    def __init__(self):
        """Initialize the classifier with pattern definitions."""
        self.pattern_sets = {
            DocumentType.LETTER_OF_CREDIT: LC_PATTERNS,
            DocumentType.COMMERCIAL_INVOICE: INVOICE_PATTERNS,
            DocumentType.BILL_OF_LADING: BL_PATTERNS,
            DocumentType.PACKING_LIST: PACKING_LIST_PATTERNS,
            DocumentType.CERTIFICATE_OF_ORIGIN: CO_PATTERNS,
            DocumentType.INSURANCE_CERTIFICATE: INSURANCE_PATTERNS,
            DocumentType.INSPECTION_CERTIFICATE: INSPECTION_PATTERNS,
        }
    
    def classify(
        self,
        text: str,
        filename: Optional[str] = None,
        fallback_type: Optional[DocumentType] = None,
    ) -> ClassificationResult:
        """
        Classify document type based on OCR text content.
        
        Args:
            text: OCR extracted text from document
            filename: Optional filename for secondary hints
            fallback_type: Type to use if classification confidence is too low
            
        Returns:
            ClassificationResult with detected type and confidence
        """
        if not text or len(text.strip()) < 50:
            logger.warning("Insufficient text for classification (len=%d)", len(text or ""))
            return self._create_unknown_result(fallback_type)
        
        # Normalize text for pattern matching
        normalized_text = self._normalize_text(text)
        
        # Score each document type
        scores: Dict[DocumentType, Tuple[float, List[str]]] = {}
        
        for doc_type, patterns in self.pattern_sets.items():
            score, matched = self._score_patterns(
                normalized_text, patterns, doc_type
            )
            scores[doc_type] = (score, matched)
        
        # Find best match
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: x[1][0],
            reverse=True
        )
        
        best_type, (best_score, best_patterns) = sorted_scores[0]
        
        # Calculate confidence
        confidence = self._calculate_confidence(best_score, best_type, sorted_scores)
        confidence_level = self._get_confidence_level(confidence)
        
        # Build alternatives list
        alternatives = [
            (doc_type, self._calculate_confidence(score, doc_type, sorted_scores))
            for doc_type, (score, _) in sorted_scores[1:4]
            if score > 0
        ]
        
        # Determine if classification is reliable
        is_reliable = confidence >= 0.60
        
        # Build reasoning
        reasoning = self._build_reasoning(
            best_type, best_score, best_patterns, confidence, sorted_scores
        )
        
        # Use fallback if confidence too low
        if not is_reliable and fallback_type:
            logger.warning(
                "Low confidence classification (%.2f). "
                "Using fallback type: %s (detected: %s)",
                confidence, fallback_type.value, best_type.value
            )
            return ClassificationResult(
                document_type=fallback_type,
                confidence=confidence,
                confidence_level=ClassificationConfidence.LOW,
                matched_patterns=best_patterns,
                reasoning=f"Fallback used due to low confidence. {reasoning}",
                alternative_types=[(best_type, confidence)] + alternatives,
                is_reliable=False,
            )
        
        logger.info(
            "Classified document as %s (confidence: %.2f, patterns: %d)",
            best_type.value, confidence, len(best_patterns)
        )
        
        return ClassificationResult(
            document_type=best_type,
            confidence=confidence,
            confidence_level=confidence_level,
            matched_patterns=best_patterns,
            reasoning=reasoning,
            alternative_types=alternatives,
            is_reliable=is_reliable,
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching."""
        # Convert to uppercase for pattern matching
        normalized = text.upper()
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def _score_patterns(
        self,
        text: str,
        patterns: Dict[str, str],
        doc_type: DocumentType,
    ) -> Tuple[float, List[str]]:
        """
        Score how well text matches patterns for a document type.
        
        Returns:
            Tuple of (total_score, list of matched pattern names)
        """
        total_score = 0.0
        matched_patterns = []
        weights = self.PATTERN_WEIGHTS.get(doc_type, {})
        
        for pattern_name, pattern_regex in patterns.items():
            try:
                matches = re.findall(pattern_regex, text, re.IGNORECASE)
                if matches:
                    # Get weight for this pattern
                    weight = weights.get(pattern_name, weights.get("default", 1.0))
                    
                    # Handle wildcard weights (e.g., "swift_field_*")
                    if weight == 1.0:
                        for key in weights:
                            if key.endswith("*") and pattern_name.startswith(key[:-1]):
                                weight = weights[key]
                                break
                    
                    # Score based on number of matches (diminishing returns)
                    match_score = weight * min(len(matches), 3)
                    total_score += match_score
                    matched_patterns.append(pattern_name)
            except re.error as e:
                logger.error("Regex error for pattern %s: %s", pattern_name, e)
        
        return total_score, matched_patterns
    
    def _calculate_confidence(
        self,
        score: float,
        doc_type: DocumentType,
        all_scores: List[Tuple[DocumentType, Tuple[float, List[str]]]],
    ) -> float:
        """
        Calculate confidence based on score and relative performance.
        
        Confidence factors:
        1. Absolute score vs threshold
        2. Score ratio vs second best
        3. Pattern coverage
        """
        threshold = self.MIN_SCORE_THRESHOLDS.get(doc_type, 5.0)
        
        # Factor 1: Score vs threshold (0.0 to 0.5)
        threshold_factor = min(score / (threshold * 2), 0.5)
        
        # Factor 2: Margin over second best (0.0 to 0.3)
        second_score = all_scores[1][1][0] if len(all_scores) > 1 else 0
        if score > 0:
            margin_ratio = (score - second_score) / score
            margin_factor = min(margin_ratio, 1.0) * 0.3
        else:
            margin_factor = 0.0
        
        # Factor 3: Pattern diversity (0.0 to 0.2)
        matched_count = len(all_scores[0][1][1]) if all_scores else 0
        total_patterns = len(self.pattern_sets.get(doc_type, {}))
        if total_patterns > 0:
            diversity_factor = min(matched_count / total_patterns, 1.0) * 0.2
        else:
            diversity_factor = 0.0
        
        confidence = threshold_factor + margin_factor + diversity_factor
        return min(max(confidence, 0.0), 1.0)
    
    def _get_confidence_level(self, confidence: float) -> ClassificationConfidence:
        """Map confidence score to confidence level."""
        if confidence >= 0.85:
            return ClassificationConfidence.HIGH
        elif confidence >= 0.60:
            return ClassificationConfidence.MEDIUM
        elif confidence >= 0.40:
            return ClassificationConfidence.LOW
        else:
            return ClassificationConfidence.UNKNOWN
    
    def _build_reasoning(
        self,
        doc_type: DocumentType,
        score: float,
        matched_patterns: List[str],
        confidence: float,
        all_scores: List[Tuple[DocumentType, Tuple[float, List[str]]]],
    ) -> str:
        """Build human-readable reasoning for classification."""
        pattern_summary = ", ".join(matched_patterns[:5])
        if len(matched_patterns) > 5:
            pattern_summary += f" (+{len(matched_patterns) - 5} more)"
        
        second_type = all_scores[1][0] if len(all_scores) > 1 else None
        second_score = all_scores[1][1][0] if len(all_scores) > 1 else 0
        
        reasoning = (
            f"Detected as {doc_type.value} with {confidence:.0%} confidence. "
            f"Score: {score:.1f}. Matched patterns: {pattern_summary}."
        )
        
        if second_type and second_score > 0:
            reasoning += (
                f" Second best: {second_type.value} (score: {second_score:.1f})."
            )
        
        return reasoning
    
    def _create_unknown_result(
        self,
        fallback_type: Optional[DocumentType],
    ) -> ClassificationResult:
        """Create a result for unclassifiable documents."""
        doc_type = fallback_type or DocumentType.SUPPORTING_DOCUMENT
        return ClassificationResult(
            document_type=doc_type,
            confidence=0.0,
            confidence_level=ClassificationConfidence.UNKNOWN,
            matched_patterns=[],
            reasoning="Insufficient text content for classification.",
            alternative_types=[],
            is_reliable=False,
        )
    
    def classify_batch(
        self,
        documents: List[Tuple[str, Optional[str]]],
    ) -> List[ClassificationResult]:
        """
        Classify multiple documents.
        
        Args:
            documents: List of (text, filename) tuples
            
        Returns:
            List of ClassificationResults in same order
        """
        return [
            self.classify(text, filename)
            for text, filename in documents
        ]
    
    def is_lc_document(self, text: str) -> bool:
        """
        Quick check if document is likely a Letter of Credit.
        
        This is a fast pre-check for validation gating.
        """
        result = self.classify(text)
        return (
            result.document_type == DocumentType.LETTER_OF_CREDIT
            and result.is_reliable
        )


# Module-level instance for convenience
_classifier: Optional[DocumentTypeClassifier] = None


def get_doc_type_classifier() -> DocumentTypeClassifier:
    """Get the global document type classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = DocumentTypeClassifier()
    return _classifier

