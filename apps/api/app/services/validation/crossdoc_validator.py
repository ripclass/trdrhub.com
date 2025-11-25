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


logger = logging.getLogger(__name__)


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
    
    # Amount tolerance (5% per UCP600 Article 30)
    DEFAULT_AMOUNT_TOLERANCE = 0.05
    
    # Quantity tolerance (5% per UCP600 Article 30)
    DEFAULT_QUANTITY_TOLERANCE = 0.05
    
    def __init__(
        self,
        amount_tolerance: float = DEFAULT_AMOUNT_TOLERANCE,
        quantity_tolerance: float = DEFAULT_QUANTITY_TOLERANCE,
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
        """Check invoice goods description matches LC."""
        inv_goods = self._normalize_text(
            invoice.get("goods_description") or invoice.get("description")
        )
        lc_goods = self._normalize_text(lc_data.get("goods_description"))
        
        if not inv_goods or not lc_goods:
            return None
        
        # Use fuzzy matching for goods description
        similarity = self._text_similarity(inv_goods, lc_goods)
        
        # Invoice goods must not conflict with LC (but can be more specific)
        if similarity < 0.5:  # Very different descriptions
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
        
        if ins_amount < min_coverage:
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
        
        if similarity < 0.4:
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
        
        # Jaccard similarity > 0.5
        return len(intersection) / len(union) > 0.5
    
    def _ports_match(self, port1: str, port2: str) -> bool:
        """Check if two port names match."""
        p1 = self._normalize_port(port1)
        p2 = self._normalize_port(port2)
        
        if p1 == p2:
            return True
        
        # Check if one contains the other
        if p1 in p2 or p2 in p1:
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

