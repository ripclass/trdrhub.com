"""
Cross-Document Validator - Phase 7: Rule-by-rule validation.

This module implements UCP600/ISBP745 compliant cross-document validation:
- Invoice vs LC (amount, goods, parties)
- Bill of Lading vs LC (ports, dates, goods)
- Insurance vs LC (coverage, amount)
- Certificate of Origin vs LC
- Packing List vs Invoice

Each rule produces structured Expected/Found/Suggestion output.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, date
from enum import Enum

from app.services.extraction.lc_baseline import LCBaseline
from app.services.validation.issue_engine import Issue, IssueSeverity, IssueSource
from app.reference_data.ports import get_port_registry, PortRegistry
from app.constants.thresholds import VALIDATION, CONFIDENCE


logger = logging.getLogger(__name__)

# Global port registry instance
_port_registry: Optional[PortRegistry] = None

def _get_port_registry() -> PortRegistry:
    """Get or create port registry singleton."""
    global _port_registry
    if _port_registry is None:
        _port_registry = get_port_registry()
    return _port_registry


class DocumentType(str, Enum):
    """Document types for cross-validation."""
    LC = "letter_of_credit"
    INVOICE = "commercial_invoice"
    BILL_OF_LADING = "bill_of_lading"
    INSURANCE = "insurance_certificate"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    PACKING_LIST = "packing_list"
    INSPECTION_CERT = "inspection_certificate"
    DRAFT = "draft"


@dataclass
class CrossDocIssue:
    """A cross-document validation issue."""
    rule_id: str
    title: str
    severity: IssueSeverity
    message: str
    expected: str
    found: str
    suggestion: str
    
    # Document references
    source_doc: DocumentType
    target_doc: DocumentType
    source_field: str
    target_field: str
    
    # Compliance references
    ucp_article: Optional[str] = None
    isbp_paragraph: Optional[str] = None
    
    # Values for debugging
    source_value: Any = None
    target_value: Any = None
    tolerance_applied: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule_id,
            "title": self.title,
            "severity": self.severity.value,
            "message": self.message,
            "expected": self.expected,
            "actual": self.found,
            "suggestion": self.suggestion,
            "passed": False,
            "documents": [self.source_doc.value, self.target_doc.value],
            "document_names": [
                self._doc_display_name(self.source_doc),
                self._doc_display_name(self.target_doc),
            ],
            "source_field": self.source_field,
            "target_field": self.target_field,
            "ucp_reference": self.ucp_article,
            "isbp_reference": self.isbp_paragraph,
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "display_card": True,
            "auto_generated": True,
        }
    
    def _doc_display_name(self, doc_type: DocumentType) -> str:
        names = {
            DocumentType.LC: "Letter of Credit",
            DocumentType.INVOICE: "Commercial Invoice",
            DocumentType.BILL_OF_LADING: "Bill of Lading",
            DocumentType.INSURANCE: "Insurance Certificate",
            DocumentType.CERTIFICATE_OF_ORIGIN: "Certificate of Origin",
            DocumentType.PACKING_LIST: "Packing List",
            DocumentType.INSPECTION_CERT: "Inspection Certificate",
            DocumentType.DRAFT: "Draft/Bill of Exchange",
        }
        return names.get(doc_type, doc_type.value)


@dataclass
class CrossDocResult:
    """Result of cross-document validation."""
    issues: List[CrossDocIssue]
    rules_executed: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    
    # By severity
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    
    # By document pair
    issues_by_pair: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules_executed": self.rules_executed,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "pass_rate": round(self.rules_passed / max(1, self.rules_executed) * 100, 1),
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "issues": [i.to_dict() for i in self.issues],
            "issues_by_pair": self.issues_by_pair,
        }


class CrossDocValidator:
    """
    UCP600/ISBP745 compliant cross-document validator.
    
    Validates consistency between:
    - LC terms and supporting documents
    - Document-to-document matching
    """
    
    def __init__(
        self,
        amount_tolerance: float = VALIDATION.AMOUNT_TOLERANCE,
        quantity_tolerance: float = VALIDATION.QUANTITY_TOLERANCE,
        strict_goods_matching: bool = False,
    ):
        self.amount_tolerance = amount_tolerance
        self.quantity_tolerance = quantity_tolerance
        self.strict_goods_matching = strict_goods_matching
    
    def validate_all(
        self,
        lc_baseline: LCBaseline,
        invoice: Optional[Dict[str, Any]] = None,
        bill_of_lading: Optional[Dict[str, Any]] = None,
        insurance: Optional[Dict[str, Any]] = None,
        certificate_of_origin: Optional[Dict[str, Any]] = None,
        packing_list: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CrossDocResult:
        """
        Run all cross-document validations.
        """
        all_issues: List[CrossDocIssue] = []
        rules_executed = 0
        rules_passed = 0
        
        # Convert baseline to dict for easier access
        lc_data = self._baseline_to_dict(lc_baseline)
        
        # =========================================================================
        # LC VALIDITY CHECK (FF001) - Must be checked FIRST
        # =========================================================================
        rules_executed += 1
        lc_expiry_issue = self._check_lc_expiry(lc_data)
        if lc_expiry_issue:
            all_issues.append(lc_expiry_issue)
        else:
            rules_passed += 1
        
        # =========================================================================
        # ARTICLE 16 TIMING CHECK - Presentation deadline
        # =========================================================================
        if bill_of_lading:
            rules_executed += 1
            timing_issue = self._check_article_16_timing(bill_of_lading, lc_data)
            if timing_issue:
                all_issues.append(timing_issue)
            else:
                rules_passed += 1
        
        # Invoice vs LC
        if invoice:
            inv_issues, inv_exec, inv_pass = self._validate_invoice_vs_lc(
                invoice, lc_data, lc_baseline
            )
            all_issues.extend(inv_issues)
            rules_executed += inv_exec
            rules_passed += inv_pass
        
        # B/L vs LC
        if bill_of_lading:
            bl_issues, bl_exec, bl_pass = self._validate_bl_vs_lc(
                bill_of_lading, lc_data, lc_baseline
            )
            all_issues.extend(bl_issues)
            rules_executed += bl_exec
            rules_passed += bl_pass
        
        # Insurance vs LC
        if insurance:
            ins_issues, ins_exec, ins_pass = self._validate_insurance_vs_lc(
                insurance, lc_data, lc_baseline
            )
            all_issues.extend(ins_issues)
            rules_executed += ins_exec
            rules_passed += ins_pass
        
        # Invoice vs B/L
        if invoice and bill_of_lading:
            inv_bl_issues, inv_bl_exec, inv_bl_pass = self._validate_invoice_vs_bl(
                invoice, bill_of_lading
            )
            all_issues.extend(inv_bl_issues)
            rules_executed += inv_bl_exec
            rules_passed += inv_bl_pass
        
        # Build result
        result = self._build_result(all_issues, rules_executed, rules_passed)
        
        logger.info(
            "Cross-doc validation: %d rules, %d passed, %d failed, %d issues",
            rules_executed, rules_passed, len(all_issues), len(all_issues)
        )
        
        return result
    
    # =========================================================================
    # INVOICE vs LC
    # =========================================================================
    
    def _validate_invoice_vs_lc(
        self,
        invoice: Dict[str, Any],
        lc_data: Dict[str, Any],
        baseline: LCBaseline,
    ) -> Tuple[List[CrossDocIssue], int, int]:
        """Validate commercial invoice against LC."""
        issues: List[CrossDocIssue] = []
        executed = 0
        passed = 0
        
        # CROSSDOC-INV-001: Invoice amount vs LC amount
        executed += 1
        issue = self._check_invoice_amount(invoice, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-INV-002: Invoice beneficiary vs LC beneficiary
        executed += 1
        issue = self._check_invoice_beneficiary(invoice, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-INV-003: Invoice goods description vs LC goods
        executed += 1
        issue = self._check_invoice_goods(invoice, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-INV-004: Invoice date vs LC expiry
        executed += 1
        issue = self._check_invoice_date(invoice, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-INV-005: Invoice LC reference
        executed += 1
        issue = self._check_invoice_lc_reference(invoice, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        return issues, executed, passed
    
    # =========================================================================
    # LC VALIDITY CHECKS
    # =========================================================================
    
    def _check_lc_expiry(
        self,
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """
        Check if LC has expired (FF001).
        
        Per UCP600 Article 6(d)(i), documents must be presented within
        the validity period of the LC. An expired LC cannot be used.
        """
        expiry_str = lc_data.get("expiry_date")
        if not expiry_str:
            # CRITICAL: Missing expiry date means we cannot verify LC validity
            logger.warning("LC expiry date not found in extracted data - cannot verify LC validity")
            return CrossDocIssue(
                rule_id="CROSSDOC-LC-001",
                title="LC Expiry Date Not Found",
                severity=IssueSeverity.MAJOR,
                message=(
                    "LC expiry date could not be extracted from the document. "
                    "Cannot verify if the LC is still valid for presentation. "
                    "This is a critical field required for UCP600 compliance."
                ),
                expected="LC expiry date (SWIFT field :31D:)",
                found="Not extracted / Not found in document",
                suggestion="Verify the LC document contains an expiry date. Re-upload if OCR failed to capture it, or manually verify LC validity.",
                source_doc=DocumentType.LC,
                target_doc=DocumentType.LC,
                source_field="expiry_date",
                target_field="expiry_date",
                ucp_article="UCP600 Article 6(d)",
                isbp_paragraph="ISBP745 A14",
            )
        
        expiry_date = self._parse_date(expiry_str)
        if expiry_date is None:
            # Could extract the string but couldn't parse it as a date
            logger.warning("LC expiry date found but could not be parsed: %s", expiry_str)
            return CrossDocIssue(
                rule_id="CROSSDOC-LC-001",
                title="LC Expiry Date Invalid Format",
                severity=IssueSeverity.MAJOR,
                message=(
                    f"LC expiry date '{expiry_str}' could not be parsed as a valid date. "
                    "Cannot verify if the LC is still valid for presentation."
                ),
                expected="Valid date format (YYYY-MM-DD or DD/MM/YYYY)",
                found=f"'{expiry_str}' (unparseable)",
                suggestion="Verify the expiry date format in the LC document. Expected format: YYYY-MM-DD or similar.",
                source_doc=DocumentType.LC,
                target_doc=DocumentType.LC,
                source_field="expiry_date",
                target_field="expiry_date",
                ucp_article="UCP600 Article 6(d)",
                isbp_paragraph="ISBP745 A14",
            )
        
        today = datetime.now().date()
        
        # Check if LC is expired
        if isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()
        
        if expiry_date < today:
            days_expired = (today - expiry_date).days
            return CrossDocIssue(
                rule_id="CROSSDOC-LC-001",
                title="LC Expired",
                severity=IssueSeverity.CRITICAL,
                message=(
                    f"Letter of Credit expired on {expiry_date.isoformat()}. "
                    f"Documents cannot be presented under an expired LC. "
                    f"LC has been expired for {days_expired} day(s)."
                ),
                expected="Valid LC (not expired)",
                found=f"LC expired on {expiry_date.isoformat()}",
                suggestion="Request LC amendment to extend expiry date before presenting documents.",
                source_doc=DocumentType.LC,
                target_doc=DocumentType.LC,
                source_field="expiry_date",
                target_field="expiry_date",
                ucp_article="UCP600 Article 6(d)(i)",
                isbp_paragraph="ISBP745 A14",
                source_value=expiry_date,
                target_value=today,
            )
        
        # Warn if expiring within 7 days
        days_until_expiry = (expiry_date - today).days
        if days_until_expiry <= 7:
            logger.warning(
                "LC expiring soon: %s (in %d days)",
                expiry_date.isoformat(), days_until_expiry
            )
            return CrossDocIssue(
                rule_id="CROSSDOC-LC-002",
                title="LC Expiring Soon",
                severity=IssueSeverity.MAJOR if days_until_expiry > 3 else IssueSeverity.CRITICAL,
                message=(
                    f"Letter of Credit expires on {expiry_date.isoformat()} "
                    f"({days_until_expiry} day(s) remaining). "
                    f"Documents must be presented before expiry per UCP600."
                ),
                expected="LC with sufficient validity period",
                found=f"LC expires in {days_until_expiry} day(s) on {expiry_date.isoformat()}",
                suggestion="Expedite document presentation or request LC amendment to extend expiry date.",
                source_doc=DocumentType.LC,
                target_doc=DocumentType.LC,
                source_field="expiry_date",
                target_field="expiry_date",
                ucp_article="UCP600 Article 6(d)(i)",
                isbp_paragraph="ISBP745 A14",
                source_value=expiry_date,
                target_value=today,
            )
        
        return None
    
    def _check_invoice_amount(
        self,
        invoice: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check invoice amount does not exceed LC amount (with tolerance)."""
        inv_amount = self._parse_amount(invoice.get("amount") or invoice.get("total_amount"))
        lc_amount = self._parse_amount(lc_data.get("amount"))
        
        if inv_amount is None or lc_amount is None:
            return None  # Can't check without values
        
        # Calculate maximum allowed (LC amount + tolerance)
        max_allowed = lc_amount * (1 + self.amount_tolerance)
        
        if inv_amount > max_allowed:
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-001",
                title="Invoice Amount Exceeds LC Amount",
                severity=IssueSeverity.CRITICAL,
                message=(
                    f"Invoice amount ({inv_amount:,.2f}) exceeds LC amount "
                    f"({lc_amount:,.2f}) plus {self.amount_tolerance*100:.0f}% tolerance "
                    f"(max: {max_allowed:,.2f})."
                ),
                expected=f"<= {max_allowed:,.2f} (LC amount + {self.amount_tolerance*100:.0f}% tolerance)",
                found=f"{inv_amount:,.2f}",
                suggestion="Reduce invoice amount to within LC tolerance or request LC amendment.",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.LC,
                source_field="amount",
                target_field="amount",
                ucp_article="UCP600 Article 18(b)",
                isbp_paragraph="ISBP745 C3",
                source_value=inv_amount,
                target_value=lc_amount,
                tolerance_applied=self.amount_tolerance,
            )
        
        return None
    
    def _check_invoice_beneficiary(
        self,
        invoice: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check invoice is issued by LC beneficiary."""
        inv_issuer = self._normalize_party(
            invoice.get("issuer") or invoice.get("seller") or invoice.get("beneficiary")
        )
        lc_beneficiary = self._normalize_party(lc_data.get("beneficiary"))
        
        if not inv_issuer or not lc_beneficiary:
            return None
        
        if not self._parties_match(inv_issuer, lc_beneficiary):
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-002",
                title="Invoice Issuer Does Not Match LC Beneficiary",
                severity=IssueSeverity.CRITICAL,
                message=(
                    "The invoice must be issued by the beneficiary named in the LC. "
                    "The issuer name does not match."
                ),
                expected=f"Invoice issued by: {lc_beneficiary}",
                found=f"Invoice issued by: {inv_issuer}",
                suggestion="Ensure invoice shows the exact beneficiary name as stated in LC.",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.LC,
                source_field="issuer",
                target_field="beneficiary",
                ucp_article="UCP600 Article 18(a)(i)",
                source_value=inv_issuer,
                target_value=lc_beneficiary,
            )
        
        return None
    
    def _check_invoice_goods(
        self,
        invoice: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check invoice goods description matches LC.
        
        Per UCP600 Article 18(c) and ISBP745: 
        - Invoice goods description must CORRESPOND with LC (not be identical)
        - Same HS codes with matching quantities = compliant
        - Case/formatting differences are acceptable
        """
        inv_goods = self._normalize_text(
            invoice.get("goods_description") or invoice.get("description")
        )
        lc_goods = self._normalize_text(lc_data.get("goods_description"))
        
        if not inv_goods or not lc_goods:
            return None
        
        # FIRST: Check HS codes - if they match, goods correspond
        inv_hs_codes = self._extract_hs_codes(inv_goods)
        lc_hs_codes = self._extract_hs_codes(lc_goods)
        
        if inv_hs_codes and lc_hs_codes:
            # HS codes present in both - check for match
            if inv_hs_codes == lc_hs_codes or inv_hs_codes.issubset(lc_hs_codes):
                logger.info(f"✓ Goods match by HS codes: {inv_hs_codes}")
                return None  # Compliant - same HS codes
        
        # SECOND: Check key product terms (cotton, t-shirt, garment, etc.)
        key_terms_match = self._check_key_product_terms(inv_goods, lc_goods)
        if key_terms_match:
            logger.info("✓ Goods match by key product terms")
            return None
        
        # THIRD: Fuzzy text similarity as fallback
        similarity = self._text_similarity(inv_goods, lc_goods)
        
        # Invoice goods must not conflict with LC (but can be more specific)
        # UCP600 Article 18(c) allows general terms - "correspond" not "identical"
        if similarity < VALIDATION.GOODS_DESCRIPTION_MIN_SIMILARITY:
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-003",
                title="Invoice Goods Description Mismatch",
                severity=IssueSeverity.MAJOR,
                message=(
                    "Invoice goods description does not correspond with LC terms. "
                    "Invoice may use general terms but must not conflict."
                ),
                expected=f"Goods matching: {lc_goods[:100]}...",
                found=f"Invoice states: {inv_goods[:100]}...",
                suggestion="Align invoice goods description with LC terms. May use general terms per UCP600 Article 18(c).",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.LC,
                source_field="goods_description",
                target_field="goods_description",
                ucp_article="UCP600 Article 18(c)",
                isbp_paragraph="ISBP745 C6",
                source_value=inv_goods,
                target_value=lc_goods,
            )
        
        return None
    
    def _extract_hs_codes(self, text: str) -> Set[str]:
        """Extract HS codes from text (6-10 digit numbers)."""
        if not text:
            return set()
        # HS codes are typically 6, 8, or 10 digits
        pattern = r'\b(\d{6,10})\b'
        matches = re.findall(pattern, text)
        # Filter to likely HS codes (starting with valid chapters 01-99)
        hs_codes = set()
        for m in matches:
            chapter = int(m[:2])
            if 1 <= chapter <= 99:
                hs_codes.add(m)
        return hs_codes
    
    def _check_key_product_terms(self, text1: str, text2: str) -> bool:
        """Check if key product terms match between two descriptions."""
        # Common product categories in trade
        product_keywords = [
            "cotton", "garment", "t-shirt", "tshirt", "shirt", "trouser", "pant",
            "dress", "denim", "knit", "woven", "textile", "apparel", "clothing",
            "fabric", "yarn", "shoes", "leather", "electronic", "machinery",
            "furniture", "plastic", "chemical", "food", "grain", "rice", "wheat"
        ]
        
        t1_words = set(text1.lower().split())
        t2_words = set(text2.lower().split())
        
        # Find product terms in each text
        t1_products = {w for w in t1_words if any(kw in w for kw in product_keywords)}
        t2_products = {w for w in t2_words if any(kw in w for kw in product_keywords)}
        
        if not t1_products or not t2_products:
            return False
        
        # Check for overlap
        overlap = t1_products & t2_products
        if overlap:
            return True
        
        # Check for related terms (e.g., "t-shirts" in one, "tshirt" in other)
        for t1_prod in t1_products:
            for t2_prod in t2_products:
                if t1_prod in t2_prod or t2_prod in t1_prod:
                    return True
        
        return False
    
    def _check_invoice_date(
        self,
        invoice: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check invoice date is not after LC expiry."""
        inv_date = self._parse_date(invoice.get("date") or invoice.get("invoice_date"))
        lc_expiry = self._parse_date(lc_data.get("expiry_date"))
        
        if inv_date is None or lc_expiry is None:
            return None
        
        if inv_date > lc_expiry:
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-004",
                title="Invoice Dated After LC Expiry",
                severity=IssueSeverity.CRITICAL,
                message="Invoice date is after the LC expiry date. Documents must be dated within LC validity.",
                expected=f"Invoice date on or before: {lc_expiry.isoformat()}",
                found=f"Invoice dated: {inv_date.isoformat()}",
                suggestion="Ensure invoice is dated within LC validity period.",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.LC,
                source_field="date",
                target_field="expiry_date",
                ucp_article="UCP600 Article 6(d)(i)",
                source_value=inv_date,
                target_value=lc_expiry,
            )
        
        return None
    
    def _check_invoice_lc_reference(
        self,
        invoice: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check invoice references the correct LC number."""
        inv_lc_ref = self._normalize_text(
            invoice.get("lc_number") or invoice.get("lc_reference")
        )
        lc_number = self._normalize_text(lc_data.get("lc_number"))
        
        if not lc_number:
            return None  # Can't check without LC number
        
        if not inv_lc_ref:
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-005",
                title="Invoice Missing LC Reference",
                severity=IssueSeverity.MINOR,
                message="Invoice does not reference the Letter of Credit number.",
                expected=f"LC reference: {lc_number}",
                found="No LC reference found on invoice",
                suggestion="Add LC reference number to invoice for documentary compliance.",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.LC,
                source_field="lc_reference",
                target_field="lc_number",
                isbp_paragraph="ISBP745 C1",
                target_value=lc_number,
            )
        
        if lc_number.lower() not in inv_lc_ref.lower():
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-005",
                title="Invoice LC Reference Mismatch",
                severity=IssueSeverity.MAJOR,
                message="Invoice references a different LC number than the credit being utilized.",
                expected=f"LC reference: {lc_number}",
                found=f"Invoice shows: {inv_lc_ref}",
                suggestion="Correct the LC reference on the invoice.",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.LC,
                source_field="lc_reference",
                target_field="lc_number",
                source_value=inv_lc_ref,
                target_value=lc_number,
            )
        
        return None
    
    # =========================================================================
    # BILL OF LADING vs LC
    # =========================================================================
    
    def _validate_bl_vs_lc(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
        baseline: LCBaseline,
    ) -> Tuple[List[CrossDocIssue], int, int]:
        """Validate Bill of Lading against LC."""
        issues: List[CrossDocIssue] = []
        executed = 0
        passed = 0
        
        # CROSSDOC-BL-001: Port of loading
        executed += 1
        issue = self._check_bl_port_of_loading(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-002: Port of discharge
        executed += 1
        issue = self._check_bl_port_of_discharge(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-003: Shipment date vs latest shipment
        executed += 1
        issue = self._check_bl_shipment_date(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-004: Shipper vs beneficiary
        executed += 1
        issue = self._check_bl_shipper(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-005: Consignee
        executed += 1
        issue = self._check_bl_consignee(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-006: On-board notation
        executed += 1
        issue = self._check_bl_onboard(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-007: Clean B/L
        executed += 1
        issue = self._check_bl_clean(bl)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-BL-008: Multimodal Transport validation (UCP600 Article 19)
        executed += 1
        issue = self._check_multimodal_transport(bl, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        return issues, executed, passed
    
    def _check_bl_port_of_loading(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L port of loading matches LC."""
        bl_pol = self._normalize_port(bl.get("port_of_loading") or bl.get("pol"))
        lc_pol = self._normalize_port(lc_data.get("port_of_loading"))
        
        if not bl_pol or not lc_pol:
            return None
        
        if not self._ports_match(bl_pol, lc_pol):
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-001",
                title="Port of Loading Mismatch",
                severity=IssueSeverity.CRITICAL,
                message="Bill of Lading port of loading does not match LC requirements.",
                expected=f"Port of Loading: {lc_pol}",
                found=f"B/L shows: {bl_pol}",
                suggestion="Ensure goods are shipped from the port specified in LC.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="port_of_loading",
                target_field="port_of_loading",
                ucp_article="UCP600 Article 20(a)(ii)",
                source_value=bl_pol,
                target_value=lc_pol,
            )
        
        return None
    
    def _check_bl_port_of_discharge(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L port of discharge matches LC."""
        bl_pod = self._normalize_port(bl.get("port_of_discharge") or bl.get("pod"))
        lc_pod = self._normalize_port(lc_data.get("port_of_discharge"))
        
        if not bl_pod or not lc_pod:
            return None
        
        if not self._ports_match(bl_pod, lc_pod):
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-002",
                title="Port of Discharge Mismatch",
                severity=IssueSeverity.CRITICAL,
                message="Bill of Lading port of discharge does not match LC requirements.",
                expected=f"Port of Discharge: {lc_pod}",
                found=f"B/L shows: {bl_pod}",
                suggestion="Ensure destination port matches LC specifications.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="port_of_discharge",
                target_field="port_of_discharge",
                ucp_article="UCP600 Article 20(a)(ii)",
                source_value=bl_pod,
                target_value=lc_pod,
            )
        
        return None
    
    def _check_bl_shipment_date(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L shipment date is within LC latest shipment."""
        bl_date = self._parse_date(
            bl.get("shipment_date") or bl.get("on_board_date") or bl.get("date")
        )
        lc_latest = self._parse_date(lc_data.get("latest_shipment"))
        
        if bl_date is None or lc_latest is None:
            return None
        
        if bl_date > lc_latest:
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-003",
                title="Late Shipment",
                severity=IssueSeverity.CRITICAL,
                message="Shipment date on B/L is after LC latest shipment date.",
                expected=f"Shipment on or before: {lc_latest.isoformat()}",
                found=f"B/L dated: {bl_date.isoformat()}",
                suggestion="Shipment must be made by latest date stipulated in LC. Request LC amendment if needed.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="shipment_date",
                target_field="latest_shipment",
                ucp_article="UCP600 Article 6(c)",
                source_value=bl_date,
                target_value=lc_latest,
            )
        
        return None
    
    def _check_bl_shipper(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L shipper is the LC beneficiary."""
        bl_shipper = self._normalize_party(bl.get("shipper"))
        lc_beneficiary = self._normalize_party(lc_data.get("beneficiary"))
        
        if not bl_shipper or not lc_beneficiary:
            return None
        
        if not self._parties_match(bl_shipper, lc_beneficiary):
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-004",
                title="Shipper Not LC Beneficiary",
                severity=IssueSeverity.MAJOR,
                message="B/L shipper name does not match LC beneficiary.",
                expected=f"Shipper: {lc_beneficiary}",
                found=f"B/L shows: {bl_shipper}",
                suggestion="B/L should show beneficiary as shipper unless LC permits otherwise.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="shipper",
                target_field="beneficiary",
                isbp_paragraph="ISBP745 E2",
                source_value=bl_shipper,
                target_value=lc_beneficiary,
            )
        
        return None
    
    def _check_bl_consignee(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L consignee matches LC requirements."""
        bl_consignee = self._normalize_party(bl.get("consignee"))
        lc_applicant = self._normalize_party(lc_data.get("applicant"))
        
        if not bl_consignee:
            return None
        
        # "To order" or "To order of [bank]" is acceptable
        if "to order" in bl_consignee.lower():
            return None
        
        # If consignee specified, should typically match applicant
        if lc_applicant and not self._parties_match(bl_consignee, lc_applicant):
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-005",
                title="Consignee Mismatch",
                severity=IssueSeverity.MINOR,
                message="B/L consignee does not match LC applicant. Verify LC consignee requirements.",
                expected=f"Consignee: {lc_applicant} or 'To Order'",
                found=f"B/L shows: {bl_consignee}",
                suggestion="Check LC for specific consignee requirements.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="consignee",
                target_field="applicant",
                source_value=bl_consignee,
                target_value=lc_applicant,
            )
        
        return None
    
    def _check_bl_onboard(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L has on-board notation."""
        is_onboard = bl.get("on_board", False)
        has_onboard_date = bl.get("on_board_date") is not None
        bl_type = (bl.get("type") or "").lower()
        
        # Shipped B/L is automatically on-board
        if "shipped" in bl_type:
            return None
        
        if not is_onboard and not has_onboard_date and "received" in bl_type:
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-006",
                title="Missing On-Board Notation",
                severity=IssueSeverity.CRITICAL,
                message="B/L appears to be 'Received for Shipment' without on-board notation.",
                expected="On-board notation with date and vessel name",
                found="No on-board notation found",
                suggestion="Obtain 'Shipped' B/L or add on-board notation per UCP600.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="on_board",
                target_field="transport_doc_type",
                ucp_article="UCP600 Article 20(a)(ii)",
            )
        
        return None
    
    def _check_bl_clean(
        self,
        bl: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check B/L is clean (no adverse clauses)."""
        is_clean = bl.get("clean", True)
        clauses = bl.get("clauses") or []
        
        adverse_terms = ["damaged", "wet", "stained", "torn", "inadequate"]
        
        for clause in clauses:
            clause_lower = str(clause).lower()
            if any(term in clause_lower for term in adverse_terms):
                return CrossDocIssue(
                    rule_id="CROSSDOC-BL-007",
                    title="Claused Bill of Lading",
                    severity=IssueSeverity.CRITICAL,
                    message="B/L contains clauses indicating defective condition of goods or packaging.",
                    expected="Clean B/L without adverse notations",
                    found=f"Clause found: {clause}",
                    suggestion="Obtain clean B/L. Banks will reject documents with adverse clauses.",
                    source_doc=DocumentType.BILL_OF_LADING,
                    target_doc=DocumentType.LC,
                    source_field="clauses",
                    target_field="clean_bl_required",
                    ucp_article="UCP600 Article 27",
                    source_value=clause,
                )
        
        return None
    
    def _check_multimodal_transport(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """
        Validate multimodal transport document per UCP600 Article 19.
        
        Per UCP600 Article 19, a multimodal transport document must:
        - Indicate the carrier/multimodal transport operator
        - Indicate shipment/dispatch/taking in charge at the place stated in LC
        - Indicate the place of final destination stated in LC
        - Be signed by the carrier/MTO or their agent
        - Indicate that goods are on board or have been dispatched
        """
        bl_type = (bl.get("type") or bl.get("document_type") or "").lower()
        
        # Only validate if this is a multimodal/combined transport document
        is_multimodal = any(term in bl_type for term in [
            "multimodal", "combined", "intermodal", "multi-modal"
        ])
        
        # Also check if LC specifies multimodal transport
        lc_transport = (lc_data.get("transport_mode") or "").lower()
        lc_requires_multimodal = "multimodal" in lc_transport or "combined" in lc_transport
        
        if not is_multimodal and not lc_requires_multimodal:
            return None  # Standard ocean B/L, no multimodal validation needed
        
        # For multimodal, check place of receipt (not just port of loading)
        place_of_receipt = bl.get("place_of_receipt") or bl.get("place_of_taking_in_charge")
        lc_place_of_receipt = lc_data.get("place_of_receipt") or lc_data.get("place_of_dispatch")
        
        # Check place of delivery (final destination)
        place_of_delivery = bl.get("place_of_delivery") or bl.get("final_destination")
        lc_place_of_delivery = lc_data.get("place_of_delivery") or lc_data.get("final_destination")
        
        # Validate place of receipt matches
        if lc_place_of_receipt and place_of_receipt:
            if not self._places_match(place_of_receipt, lc_place_of_receipt):
                return CrossDocIssue(
                    rule_id="CROSSDOC-BL-008",
                    title="Multimodal Place of Receipt Mismatch",
                    severity=IssueSeverity.MAJOR,
                    message="Multimodal transport document place of receipt does not match LC.",
                    expected=f"Place of Receipt: {lc_place_of_receipt}",
                    found=f"Document shows: {place_of_receipt}",
                    suggestion="Ensure place of taking in charge matches LC requirements.",
                    source_doc=DocumentType.BILL_OF_LADING,
                    target_doc=DocumentType.LC,
                    source_field="place_of_receipt",
                    target_field="place_of_receipt",
                    ucp_article="UCP600 Article 19(a)(ii)",
                    isbp_paragraph="ISBP745 D1-D3",
                    source_value=place_of_receipt,
                    target_value=lc_place_of_receipt,
                )
        
        # Validate place of delivery matches
        if lc_place_of_delivery and place_of_delivery:
            if not self._places_match(place_of_delivery, lc_place_of_delivery):
                return CrossDocIssue(
                    rule_id="CROSSDOC-BL-008",
                    title="Multimodal Final Destination Mismatch",
                    severity=IssueSeverity.MAJOR,
                    message="Multimodal transport document final destination does not match LC.",
                    expected=f"Final Destination: {lc_place_of_delivery}",
                    found=f"Document shows: {place_of_delivery}",
                    suggestion="Ensure final destination matches LC requirements.",
                    source_doc=DocumentType.BILL_OF_LADING,
                    target_doc=DocumentType.LC,
                    source_field="place_of_delivery",
                    target_field="place_of_delivery",
                    ucp_article="UCP600 Article 19(a)(ii)",
                    isbp_paragraph="ISBP745 D1-D3",
                    source_value=place_of_delivery,
                    target_value=lc_place_of_delivery,
                )
        
        # Check if document indicates dispatch/taking in charge
        dispatch_date = bl.get("dispatch_date") or bl.get("taking_in_charge_date")
        on_board_date = bl.get("on_board_date") or bl.get("shipped_date")
        
        if is_multimodal and not dispatch_date and not on_board_date:
            return CrossDocIssue(
                rule_id="CROSSDOC-BL-008",
                title="Missing Dispatch/On-Board Date on Multimodal Document",
                severity=IssueSeverity.CRITICAL,
                message="Multimodal transport document must indicate when goods were dispatched or taken in charge.",
                expected="Dispatch date or on-board notation",
                found="No dispatch/shipment date indicated",
                suggestion="Add dispatch date or on-board notation to the transport document.",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="dispatch_date",
                target_field="latest_shipment_date",
                ucp_article="UCP600 Article 19(a)(ii)",
                isbp_paragraph="ISBP745 D7",
            )
        
        return None
    
    def _places_match(self, place1: str, place2: str) -> bool:
        """Check if two place names match (flexible matching)."""
        if not place1 or not place2:
            return True  # Can't compare, assume OK
        
        p1 = place1.upper().strip()
        p2 = place2.upper().strip()
        
        # Direct match
        if p1 == p2:
            return True
        
        # One contains the other
        if p1 in p2 or p2 in p1:
            return True
        
        # Remove common suffixes and compare
        suffixes = [" PORT", " AIRPORT", " TERMINAL", " STATION", " DEPOT"]
        for suffix in suffixes:
            p1 = p1.replace(suffix, "")
            p2 = p2.replace(suffix, "")
        
        return p1 == p2
    
    def _check_article_16_timing(
        self,
        bl: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """
        Check presentation timing per UCP600 Article 14(c) and Article 16.
        
        Key rules:
        - Documents must be presented within 21 days of shipment (Art. 14(c))
        - Unless LC specifies a different period
        - Presentation must be within LC validity
        - Bank has 5 banking days to examine (Art. 14(b))
        """
        from datetime import datetime, timedelta
        
        # Get shipment date from B/L
        shipment_date_str = (
            bl.get("on_board_date") or 
            bl.get("shipped_date") or 
            bl.get("date_of_issue") or
            bl.get("dispatch_date")
        )
        
        if not shipment_date_str:
            return None  # Can't check without shipment date
        
        # Parse shipment date
        try:
            if isinstance(shipment_date_str, datetime):
                shipment_date = shipment_date_str
            else:
                # Try multiple date formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%B %d, %Y"]:
                    try:
                        shipment_date = datetime.strptime(str(shipment_date_str), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None  # Can't parse date
        except Exception:
            return None
        
        # Get presentation period from LC (default: 21 days per UCP600 Art. 14(c))
        presentation_period = lc_data.get("presentation_period")
        if presentation_period:
            try:
                days_allowed = int(presentation_period)
            except (ValueError, TypeError):
                days_allowed = 21
        else:
            days_allowed = 21
        
        # Calculate presentation deadline
        presentation_deadline = shipment_date + timedelta(days=days_allowed)
        today = datetime.now()
        
        # Get LC expiry date
        expiry_date_str = lc_data.get("expiry_date") or lc_data.get("date_of_expiry")
        expiry_date = None
        if expiry_date_str:
            try:
                if isinstance(expiry_date_str, datetime):
                    expiry_date = expiry_date_str
                else:
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
                        try:
                            expiry_date = datetime.strptime(str(expiry_date_str), fmt)
                            break
                        except ValueError:
                            continue
            except Exception:
                pass
        
        # The effective deadline is the EARLIER of:
        # 1. 21 days (or LC-specified period) after shipment
        # 2. LC expiry date
        effective_deadline = presentation_deadline
        if expiry_date and expiry_date < presentation_deadline:
            effective_deadline = expiry_date
        
        # Check if presentation deadline has passed
        if today > presentation_deadline:
            days_overdue = (today - presentation_deadline).days
            return CrossDocIssue(
                rule_id="CROSSDOC-TIMING-001",
                title="Presentation Period Exceeded",
                severity=IssueSeverity.CRITICAL,
                message=f"Documents presented {days_overdue} days after the {days_allowed}-day presentation deadline.",
                expected=f"Documents presented by {presentation_deadline.strftime('%Y-%m-%d')} ({days_allowed} days from shipment)",
                found=f"Today is {today.strftime('%Y-%m-%d')} ({days_overdue} days late)",
                suggestion="Present documents within the stipulated period. Bank will refuse documents presented late per UCP600 Article 14(c).",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="shipment_date",
                target_field="presentation_period",
                ucp_article="UCP600 Article 14(c)",
                isbp_paragraph="ISBP745 A20-A22",
                source_value=shipment_date.strftime("%Y-%m-%d"),
                target_value=f"{days_allowed} days",
            )
        
        # Warning if presentation is getting close to deadline (within 5 days)
        days_remaining = (effective_deadline - today).days
        if 0 < days_remaining <= 5:
            return CrossDocIssue(
                rule_id="CROSSDOC-TIMING-002",
                title="Presentation Deadline Approaching",
                severity=IssueSeverity.WARNING,
                message=f"Only {days_remaining} day(s) remaining to present documents.",
                expected=f"Present by {effective_deadline.strftime('%Y-%m-%d')}",
                found=f"Today is {today.strftime('%Y-%m-%d')} ({days_remaining} days remaining)",
                suggestion=f"Present documents immediately. Bank needs 5 banking days to examine (Art. 14(b)).",
                source_doc=DocumentType.BILL_OF_LADING,
                target_doc=DocumentType.LC,
                source_field="shipment_date",
                target_field="expiry_date",
                ucp_article="UCP600 Article 14(b)(c)",
                isbp_paragraph="ISBP745 A20",
                source_value=shipment_date.strftime("%Y-%m-%d"),
                target_value=effective_deadline.strftime("%Y-%m-%d"),
            )
        
        return None
    
    # =========================================================================
    # INSURANCE vs LC
    # =========================================================================
    
    def _validate_insurance_vs_lc(
        self,
        insurance: Dict[str, Any],
        lc_data: Dict[str, Any],
        baseline: LCBaseline,
    ) -> Tuple[List[CrossDocIssue], int, int]:
        """Validate insurance certificate against LC."""
        issues: List[CrossDocIssue] = []
        executed = 0
        passed = 0
        
        # CROSSDOC-INS-001: Insurance amount coverage
        executed += 1
        issue = self._check_insurance_amount(insurance, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-INS-002: Insurance date
        executed += 1
        issue = self._check_insurance_date(insurance, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        # CROSSDOC-INS-003: Currency match
        executed += 1
        issue = self._check_insurance_currency(insurance, lc_data)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        return issues, executed, passed
    
    def _check_insurance_amount(
        self,
        insurance: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check insurance covers at least 110% of CIF/CIP value."""
        ins_amount = self._parse_amount(insurance.get("amount") or insurance.get("sum_insured"))
        lc_amount = self._parse_amount(lc_data.get("amount"))
        
        if ins_amount is None or lc_amount is None:
            return None
        
        # Minimum 110% coverage per UCP600 Article 28(f)(ii)
        min_coverage = lc_amount * 1.10
        
        # Use small epsilon for floating-point comparison
        epsilon = VALIDATION.NUMERIC_EPSILON
        if ins_amount < (min_coverage - epsilon):
            return CrossDocIssue(
                rule_id="CROSSDOC-INS-001",
                title="Insufficient Insurance Coverage",
                severity=IssueSeverity.CRITICAL,
                message=(
                    f"Insurance coverage ({ins_amount:,.2f}) is less than "
                    f"110% of invoice/LC value ({min_coverage:,.2f})."
                ),
                expected=f">= {min_coverage:,.2f} (110% of LC amount)",
                found=f"{ins_amount:,.2f}",
                suggestion="Increase insurance coverage to minimum 110% of CIF value.",
                source_doc=DocumentType.INSURANCE,
                target_doc=DocumentType.LC,
                source_field="amount",
                target_field="amount",
                ucp_article="UCP600 Article 28(f)(ii)",
                source_value=ins_amount,
                target_value=lc_amount,
            )
        
        return None
    
    def _check_insurance_date(
        self,
        insurance: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check insurance is dated before or on shipment date."""
        ins_date = self._parse_date(insurance.get("date"))
        # Use latest_shipment as proxy for shipment date from LC
        shipment_date = self._parse_date(lc_data.get("latest_shipment"))
        
        if ins_date is None or shipment_date is None:
            return None
        
        # Insurance should be effective from shipment date
        # Being dated after shipment is a discrepancy
        if ins_date > shipment_date:
            return CrossDocIssue(
                rule_id="CROSSDOC-INS-002",
                title="Insurance Dated After Shipment",
                severity=IssueSeverity.MAJOR,
                message="Insurance certificate is dated after the shipment date.",
                expected=f"Insurance effective from: {shipment_date.isoformat()} or earlier",
                found=f"Insurance dated: {ins_date.isoformat()}",
                suggestion="Insurance must be dated on or before shipment date.",
                source_doc=DocumentType.INSURANCE,
                target_doc=DocumentType.LC,
                source_field="date",
                target_field="latest_shipment",
                ucp_article="UCP600 Article 28(e)",
                source_value=ins_date,
                target_value=shipment_date,
            )
        
        return None
    
    def _check_insurance_currency(
        self,
        insurance: Dict[str, Any],
        lc_data: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check insurance currency matches LC."""
        ins_currency = (insurance.get("currency") or "").upper()
        lc_currency = (lc_data.get("currency") or "").upper()
        
        if not ins_currency or not lc_currency:
            return None
        
        if ins_currency != lc_currency:
            return CrossDocIssue(
                rule_id="CROSSDOC-INS-003",
                title="Insurance Currency Mismatch",
                severity=IssueSeverity.MAJOR,
                message="Insurance certificate currency does not match LC currency.",
                expected=f"Currency: {lc_currency}",
                found=f"Insurance in: {ins_currency}",
                suggestion="Insurance must be in same currency as LC unless otherwise stipulated.",
                source_doc=DocumentType.INSURANCE,
                target_doc=DocumentType.LC,
                source_field="currency",
                target_field="currency",
                ucp_article="UCP600 Article 28(f)(i)",
                source_value=ins_currency,
                target_value=lc_currency,
            )
        
        return None
    
    # =========================================================================
    # INVOICE vs BILL OF LADING
    # =========================================================================
    
    def _validate_invoice_vs_bl(
        self,
        invoice: Dict[str, Any],
        bl: Dict[str, Any],
    ) -> Tuple[List[CrossDocIssue], int, int]:
        """Validate invoice against bill of lading."""
        issues: List[CrossDocIssue] = []
        executed = 0
        passed = 0
        
        # CROSSDOC-INV-BL-001: Goods description consistency
        executed += 1
        issue = self._check_invoice_bl_goods(invoice, bl)
        if issue:
            issues.append(issue)
        else:
            passed += 1
        
        return issues, executed, passed
    
    def _check_invoice_bl_goods(
        self,
        invoice: Dict[str, Any],
        bl: Dict[str, Any],
    ) -> Optional[CrossDocIssue]:
        """Check goods description is consistent between invoice and B/L."""
        inv_goods = self._normalize_text(
            invoice.get("goods_description") or invoice.get("description")
        )
        bl_goods = self._normalize_text(
            bl.get("goods_description") or bl.get("description")
        )
        
        if not inv_goods or not bl_goods:
            return None
        
        similarity = self._text_similarity(inv_goods, bl_goods)
        
        if similarity < VALIDATION.GOODS_DESCRIPTION_MIN_SIMILARITY:
            return CrossDocIssue(
                rule_id="CROSSDOC-INV-BL-001",
                title="Goods Description Inconsistency",
                severity=IssueSeverity.MAJOR,
                message="Goods description differs significantly between invoice and B/L.",
                expected=f"Consistent description: {inv_goods[:80]}...",
                found=f"B/L states: {bl_goods[:80]}...",
                suggestion="Align goods description across all documents.",
                source_doc=DocumentType.INVOICE,
                target_doc=DocumentType.BILL_OF_LADING,
                source_field="goods_description",
                target_field="goods_description",
                isbp_paragraph="ISBP745 A22",
                source_value=inv_goods,
                target_value=bl_goods,
            )
        
        return None
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _baseline_to_dict(self, baseline: LCBaseline) -> Dict[str, Any]:
        """Convert LCBaseline to dict for easier access."""
        return {
            "lc_number": baseline.lc_number.value,
            "lc_type": baseline.lc_type.value,
            "applicant": baseline.applicant.value,
            "beneficiary": baseline.beneficiary.value,
            "issuing_bank": baseline.issuing_bank.value,
            "advising_bank": baseline.advising_bank.value,
            "amount": baseline.amount.value,
            "currency": baseline.currency.value,
            "expiry_date": baseline.expiry_date.value,
            "issue_date": baseline.issue_date.value,
            "latest_shipment": baseline.latest_shipment.value,
            "port_of_loading": baseline.port_of_loading.value,
            "port_of_discharge": baseline.port_of_discharge.value,
            "goods_description": baseline.goods_description.value,
            "incoterm": baseline.incoterm.value,
        }
    
    def _parse_amount(self, value: Any) -> Optional[float]:
        """Parse amount from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.]', '', value)
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse date from various formats."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            # Try common formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None
    
    def _normalize_text(self, text: Any) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        text = str(text).lower()
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove punctuation except essential
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.strip()
    
    def _normalize_party(self, party: Any) -> str:
        """Normalize party name for comparison."""
        if not party:
            return ""
        text = str(party).upper()
        # Remove common suffixes
        for suffix in [" LTD", " LIMITED", " INC", " CORP", " CO", " LLC", " PLC"]:
            text = text.replace(suffix, "")
        return " ".join(text.split()).strip()
    
    def _normalize_port(self, port: Any) -> str:
        """Normalize port name for comparison."""
        if not port:
            return ""
        text = str(port).upper()
        # Remove common prefixes
        for prefix in ["PORT OF ", "PORT ", "PORTO DE "]:
            if text.startswith(prefix):
                text = text[len(prefix):]
        return text.strip()
    
    def _parties_match(self, party1: str, party2: str) -> bool:
        """Check if two party names match (fuzzy)."""
        if not party1 or not party2:
            return False
        
        p1 = self._normalize_party(party1)
        p2 = self._normalize_party(party2)
        
        # Exact match after normalization
        if p1 == p2:
            return True
        
        # Check if one contains the other
        if p1 in p2 or p2 in p1:
            return True
        
        # Token-based similarity
        tokens1 = set(p1.split())
        tokens2 = set(p2.split())
        
        if not tokens1 or not tokens2:
            return False
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        # Jaccard similarity threshold for set comparisons
        return len(intersection) / len(union) > VALIDATION.JACCARD_SIMILARITY_THRESHOLD
    
    # Port aliases for common spelling variations
    PORT_ALIASES = {
        "CHITTAGONG": ["CHATTOGRAM", "CHITAGONG", "CTGN", "CTG"],
        "CHATTOGRAM": ["CHITTAGONG", "CHITAGONG", "CTGN", "CTG"],
        "NEW YORK": ["NY", "NEWYORK", "NYC"],
        "LOS ANGELES": ["LA", "LOSANGELES"],
        "SHANGHAI": ["SH", "SHANG HAI"],
        "HONG KONG": ["HK", "HONGKONG"],
        "SINGAPORE": ["SG", "SINGAPURA"],
    }
    
    def _ports_match(self, port1: str, port2: str) -> bool:
        """Check if two port names match using UN/LOCODE registry."""
        if not port1 or not port2:
            return False
        
        # Quick normalized string match first
        p1 = self._normalize_port(port1)
        p2 = self._normalize_port(port2)
        
        if p1 == p2:
            return True
        
        # Check if one contains the other (e.g., "Port of New York" vs "New York")
        if p1 in p2 or p2 in p1:
            return True
        
        # Use UN/LOCODE registry for authoritative matching
        try:
            registry = _get_port_registry()
            if registry.same_port(port1, port2):
                return True
        except Exception as e:
            logger.warning(f"Port registry lookup failed: {e}")
        
        # Fallback: check hardcoded aliases
        for canonical, aliases in self.PORT_ALIASES.items():
            p1_matches = p1 == canonical or any(alias in p1 for alias in aliases) or canonical in p1
            p2_matches = p2 == canonical or any(alias in p2 for alias in aliases) or canonical in p2
            if p1_matches and p2_matches:
                return True
        
        return False
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using Jaccard."""
        t1 = set(self._normalize_text(text1).split())
        t2 = set(self._normalize_text(text2).split())
        
        if not t1 or not t2:
            return 0.0
        
        intersection = t1 & t2
        union = t1 | t2
        
        return len(intersection) / len(union)
    
    def _build_result(
        self,
        issues: List[CrossDocIssue],
        executed: int,
        passed: int,
    ) -> CrossDocResult:
        """Build CrossDocResult from issues."""
        critical = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        major = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        minor = sum(1 for i in issues if i.severity == IssueSeverity.MINOR)
        
        # Count by document pair
        pairs: Dict[str, int] = {}
        for issue in issues:
            pair = f"{issue.source_doc.value}-{issue.target_doc.value}"
            pairs[pair] = pairs.get(pair, 0) + 1
        
        return CrossDocResult(
            issues=issues,
            rules_executed=executed,
            rules_passed=passed,
            rules_failed=len(issues),
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            issues_by_pair=pairs,
        )


def validate_cross_documents(
    lc_baseline: LCBaseline,
    documents: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convenience function for cross-document validation.
    
    Args:
        lc_baseline: LCBaseline from extraction
        documents: Dict with keys 'invoice', 'bill_of_lading', 'insurance', etc.
        
    Returns:
        Dict ready for API response
    """
    validator = CrossDocValidator()
    
    result = validator.validate_all(
        lc_baseline=lc_baseline,
        invoice=documents.get("invoice"),
        bill_of_lading=documents.get("bill_of_lading"),
        insurance=documents.get("insurance"),
        certificate_of_origin=documents.get("certificate_of_origin"),
        packing_list=documents.get("packing_list"),
    )
    
    return result.to_dict()


# Module-level instance
_crossdoc_validator: Optional[CrossDocValidator] = None


def get_crossdoc_validator() -> CrossDocValidator:
    """Get the global cross-document validator."""
    global _crossdoc_validator
    if _crossdoc_validator is None:
        _crossdoc_validator = CrossDocValidator()
    return _crossdoc_validator


# =============================================================================
# DOCUMENT SET VALIDATOR
# Validates completeness and composition of document sets per UCP600/ISBP745
# =============================================================================

@dataclass
class DocumentSetComposition:
    """Analytics for document set composition."""
    total_documents: int
    total_pages: int
    document_types: Dict[str, int]  # type -> count
    missing_common: List[str]  # commonly expected but missing
    missing_required: List[str]  # required by LC terms but missing
    completeness_score: float  # 0-100
    lc_only_mode: bool  # True if only LC document present
    estimated_processing_time_sec: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_documents": self.total_documents,
            "total_pages": self.total_pages,
            "document_types": self.document_types,
            "missing_common": self.missing_common,
            "missing_required": self.missing_required,
            "completeness_score": self.completeness_score,
            "lc_only_mode": self.lc_only_mode,
            "estimated_processing_time_sec": self.estimated_processing_time_sec,
            "completeness_grade": _completeness_grade(self.completeness_score),
        }


def _completeness_grade(score: float) -> str:
    """Convert completeness score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 25:
        return "D"
    return "F"


class DocumentSetValidator:
    """
    Validates document set completeness per UCP600/ISBP745 norms.
    
    International norms for LC document sets:
    - Minimum: LC document (MT700/MT760)
    - Standard: LC + Invoice + B/L + Packing List (4 docs)
    - Full: LC + Invoice + B/L + Packing + Insurance + CoO (6 docs)
    - Complex: Above + Inspection + Certificates (8+ docs)
    """
    
    # Common documents expected in most LC transactions
    COMMON_DOCUMENTS = {
        "letter_of_credit": {"weight": 30, "required": True, "aliases": ["lc", "swift", "mt700", "mt760"]},
        "commercial_invoice": {"weight": 25, "required": True, "aliases": ["invoice", "proforma"]},
        "bill_of_lading": {"weight": 20, "required": False, "aliases": ["bl", "bol", "shipping"]},
        "packing_list": {"weight": 10, "required": False, "aliases": ["packing", "packlist"]},
        "insurance_certificate": {"weight": 10, "required": False, "aliases": ["insurance", "policy"]},
        "certificate_of_origin": {"weight": 5, "required": False, "aliases": ["coo", "origin", "gsp"]},
    }
    
    # Additional documents for complex trades
    OPTIONAL_DOCUMENTS = {
        "inspection_certificate": {"weight": 3, "aliases": ["inspection", "quality", "analysis"]},
        "weight_certificate": {"weight": 2, "aliases": ["weight", "weighment"]},
        "fumigation_certificate": {"weight": 2, "aliases": ["fumigation", "phyto"]},
        "health_certificate": {"weight": 2, "aliases": ["health", "sanitary"]},
        "beneficiary_certificate": {"weight": 2, "aliases": ["beneficiary", "attestation"]},
    }
    
    # Average pages per document type (based on international norms)
    AVG_PAGES_BY_TYPE = {
        "letter_of_credit": 6,  # MT700/MT760 typically 2-10 pages
        "commercial_invoice": 2,
        "bill_of_lading": 3,
        "packing_list": 3,
        "insurance_certificate": 2,
        "certificate_of_origin": 2,
        "inspection_certificate": 2,
        "supporting_document": 2,
    }
    
    # Processing time estimates (seconds per page)
    PROCESSING_TIME_PER_PAGE = 5.0  # Conservative estimate with OCR

    def __init__(self, lc_terms: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional LC terms for requirement detection.
        
        Args:
            lc_terms: Extracted LC fields to detect required documents
        """
        self.lc_terms = lc_terms or {}
        self._detect_required_documents()
    
    def _detect_required_documents(self):
        """Detect which documents are required based on LC terms."""
        self.required_docs: Set[str] = {"letter_of_credit"}  # Always required
        
        # Field 46A (Documents Required) parsing
        docs_required_field = self.lc_terms.get("documents_required", "") or ""
        docs_required_lower = docs_required_field.lower()
        
        # Add required docs based on LC terms
        if "invoice" in docs_required_lower or "commercial" in docs_required_lower:
            self.required_docs.add("commercial_invoice")
        
        if any(x in docs_required_lower for x in ["bill of lading", "b/l", "bol", "shipping"]):
            self.required_docs.add("bill_of_lading")
        
        if any(x in docs_required_lower for x in ["insurance", "policy", "coverage"]):
            self.required_docs.add("insurance_certificate")
        
        if any(x in docs_required_lower for x in ["packing", "weight list"]):
            self.required_docs.add("packing_list")
        
        if any(x in docs_required_lower for x in ["origin", "gsp", "certificate of origin"]):
            self.required_docs.add("certificate_of_origin")
        
        if any(x in docs_required_lower for x in ["inspection", "quality", "analysis"]):
            self.required_docs.add("inspection_certificate")
        
        # Incoterms-based requirements
        incoterms = (self.lc_terms.get("incoterms", "") or "").upper()
        if incoterms in ["CIF", "CIP"]:
            self.required_docs.add("insurance_certificate")
    
    def validate_document_set(
        self,
        documents: List[Dict[str, Any]],
        page_counts: Optional[Dict[str, int]] = None,
    ) -> Tuple[DocumentSetComposition, List[CrossDocIssue]]:
        """
        Validate a document set for completeness.
        
        Args:
            documents: List of document info dicts with 'document_type', 'filename', etc.
            page_counts: Optional dict mapping filename to page count
        
        Returns:
            Tuple of (composition analytics, list of issues/warnings)
        """
        page_counts = page_counts or {}
        issues: List[CrossDocIssue] = []
        
        # Count document types
        doc_type_counts: Dict[str, int] = {}
        total_pages = 0
        
        for doc in documents:
            doc_type = doc.get("document_type", "supporting_document")
            doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
            
            # Estimate pages if not provided
            filename = doc.get("filename", "")
            if filename in page_counts:
                total_pages += page_counts[filename]
            else:
                # Use average for document type
                total_pages += self.AVG_PAGES_BY_TYPE.get(doc_type, 2)
        
        # Determine missing documents
        present_types = set(doc_type_counts.keys())
        
        # Check for missing common documents
        missing_common = []
        for doc_type, info in self.COMMON_DOCUMENTS.items():
            if doc_type not in present_types:
                missing_common.append(doc_type)
        
        # Check for missing required documents (per LC terms)
        missing_required = []
        for doc_type in self.required_docs:
            if doc_type not in present_types:
                missing_required.append(doc_type)
                
                # Create issue for missing required document
                issues.append(CrossDocIssue(
                    rule_id=f"DOCSET-MISSING-{doc_type.upper().replace('_', '-')}",
                    title=f"Missing {doc_type.replace('_', ' ').title()}",
                    severity=IssueSeverity.MAJOR if doc_type != "letter_of_credit" else IssueSeverity.CRITICAL,
                    message=f"The {doc_type.replace('_', ' ')} is required by LC terms but was not provided.",
                    expected=f"{doc_type.replace('_', ' ').title()} document",
                    found="Not provided",
                    suggestion=f"Upload the {doc_type.replace('_', ' ')} to complete the document set.",
                    source_doc=DocumentType.LC,
                    target_doc=DocumentType.LC,
                    source_field="46A",
                    target_field="document_set",
                    ucp_article="14(a)",
                    isbp_paragraph="A14",
                ))
        
        # Calculate completeness score
        completeness_score = self._calculate_completeness_score(
            present_types, missing_common, missing_required
        )
        
        # Detect LC-only mode
        lc_only_mode = (
            len(documents) == 1 and 
            "letter_of_credit" in present_types
        )
        
        # Add info issue if LC-only
        if lc_only_mode and not missing_required:
            issues.append(CrossDocIssue(
                rule_id="DOCSET-LC-ONLY-MODE",
                title="LC Document Only",
                severity=IssueSeverity.INFO,
                message="Only the Letter of Credit was uploaded. Cross-document validation is limited.",
                expected="Full document set (LC + Invoice + B/L + supporting docs)",
                found="LC document only",
                suggestion="Upload supporting documents for comprehensive compliance checking.",
                source_doc=DocumentType.LC,
                target_doc=DocumentType.LC,
                source_field="document_set",
                target_field="document_set",
                ucp_article="14(d)",
                isbp_paragraph="A3",
            ))
        
        # Estimate processing time
        estimated_time = total_pages * self.PROCESSING_TIME_PER_PAGE
        
        composition = DocumentSetComposition(
            total_documents=len(documents),
            total_pages=total_pages,
            document_types=doc_type_counts,
            missing_common=missing_common,
            missing_required=missing_required,
            completeness_score=completeness_score,
            lc_only_mode=lc_only_mode,
            estimated_processing_time_sec=estimated_time,
        )
        
        return composition, issues
    
    def _calculate_completeness_score(
        self,
        present_types: Set[str],
        missing_common: List[str],
        missing_required: List[str],
    ) -> float:
        """Calculate document set completeness score (0-100)."""
        # Start with 100
        score = 100.0
        
        # Heavy penalty for missing required documents
        score -= len(missing_required) * 20
        
        # Lighter penalty for missing common documents
        for doc_type in missing_common:
            if doc_type not in self.required_docs:
                weight = self.COMMON_DOCUMENTS.get(doc_type, {}).get("weight", 5)
                score -= weight * 0.5  # Half weight since not required
        
        # Bonus for having more than minimum
        if len(present_types) >= 6:
            score = min(100, score + 5)
        
        return max(0, min(100, score))


def validate_document_set_completeness(
    documents: List[Dict[str, Any]],
    lc_terms: Optional[Dict[str, Any]] = None,
    page_counts: Optional[Dict[str, int]] = None,
    skip_lc_check: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to validate document set completeness.

    Args:
        documents: List of document info dicts with 'document_type', 'filename'
        lc_terms: Optional LC terms for requirement detection
        page_counts: Optional dict mapping filename to page count
        skip_lc_check: If True, skip "Missing Letter of Credit" check (useful when LC is already confirmed)

    Returns dict with composition analytics and any issues.
    """
    validator = DocumentSetValidator(lc_terms=lc_terms)
    composition, issues = validator.validate_document_set(
        documents=documents,
        page_counts=page_counts,
    )
    
    # Filter out "Missing Letter of Credit" if LC is already confirmed
    if skip_lc_check:
        issues = [
            issue for issue in issues
            if issue.rule_id != "DOCSET-MISSING-LETTER-OF-CREDIT"
        ]

    return {
        "composition": composition.to_dict(),
        "issues": [i.to_dict() for i in issues],
        "is_complete": len(issues) == 0 or all(
            i.severity in [IssueSeverity.INFO, IssueSeverity.MINOR]
            for i in issues
        ),
    }

