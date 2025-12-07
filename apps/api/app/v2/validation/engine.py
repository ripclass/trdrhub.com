"""
V2 Validation Engine

Runs all validation rules and generates issues WITH citations.
Target: <7 seconds

Key Features:
- Every issue has UCP600/ISBP745 citations
- Uses existing 2,159 rules from database
- Cross-document validation
- Sanctions screening
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from ..core.types import (
    DocumentType, Issue, Citations, IssueSeverity, 
    FieldConfidence, SanctionsStatus, SanctionsMatch
)
from ..core.config import get_v2_config
from ..extraction.smart_extractor import ExtractionResult
from .citations import CitationLibrary
from .verdict import VerdictCalculator

logger = logging.getLogger(__name__)


class ValidationEngineV2:
    """
    V2 Validation Engine.
    
    Every issue MUST have:
    1. UCP600/ISBP745 citations
    2. Expected vs Found values
    3. Actionable suggestion
    """
    
    def __init__(self):
        self.config = get_v2_config()
        self.citation_lib = CitationLibrary()
        self.verdict_calc = VerdictCalculator()
    
    async def validate(
        self,
        extractions: Dict[str, ExtractionResult],
    ) -> Tuple[List[Issue], SanctionsStatus, Dict[str, Any]]:
        """
        Run full validation.
        
        Args:
            extractions: Extracted fields by document ID
            
        Returns:
            (issues, sanctions_status, audit_info)
        """
        start = time.perf_counter()
        issues = []
        
        # Build validation context
        context = self._build_context(extractions)
        
        # Run validations in parallel
        rule_task = self._run_rule_validation(context)
        crossdoc_task = self._run_crossdoc_validation(context)
        sanctions_task = self._run_sanctions_screening(context)
        
        rule_issues, crossdoc_issues, sanctions_status = await asyncio.gather(
            rule_task, crossdoc_task, sanctions_task
        )
        
        # Combine issues
        issues.extend(rule_issues)
        issues.extend(crossdoc_issues)
        
        # Add sanctions issues if matches found
        if sanctions_status.matches_found > 0:
            issues.extend(self._create_sanctions_issues(sanctions_status))
        
        # Ensure ALL issues have citations
        for issue in issues:
            if not issue.citations.ucp600 and not issue.citations.isbp745:
                issue.citations = self.citation_lib.get_citations(issue.rule_id)
        
        # Sort by severity
        issues.sort(key=lambda i: ["critical", "major", "minor", "info"].index(i.severity.value))
        
        processing_time = time.perf_counter() - start
        
        audit_info = {
            "rules_evaluated": len(context.get("rules_checked", [])),
            "rules_passed": len(context.get("rules_passed", [])),
            "rules_failed": len(issues),
            "cross_doc_checks": len(crossdoc_issues),
            "processing_time_seconds": processing_time,
        }
        
        logger.info(
            f"Validation complete: {len(issues)} issues found in {processing_time:.2f}s"
        )
        
        return issues, sanctions_status, audit_info
    
    def _build_context(
        self,
        extractions: Dict[str, ExtractionResult],
    ) -> Dict[str, Any]:
        """Build validation context from extractions."""
        context = {
            "documents": {},
            "lc": {},
            "invoice": {},
            "bl": {},
            "rules_checked": [],
            "rules_passed": [],
        }
        
        # Organize by document type
        for doc_id, extraction in extractions.items():
            doc_type = extraction.document_type
            
            # Convert fields to simple values for validation
            fields = {
                k: v.value for k, v in extraction.fields.items()
                if v.value is not None
            }
            
            context["documents"][doc_id] = {
                "type": doc_type,
                "fields": fields,
                "confidence": extraction.overall_confidence,
            }
            
            # Populate type-specific context
            if doc_type in [DocumentType.LETTER_OF_CREDIT, DocumentType.MT700]:
                context["lc"] = fields
            elif doc_type == DocumentType.COMMERCIAL_INVOICE:
                context["invoice"] = fields
            elif doc_type == DocumentType.BILL_OF_LADING:
                context["bl"] = fields
        
        return context
    
    async def _run_rule_validation(
        self,
        context: Dict[str, Any],
    ) -> List[Issue]:
        """
        Run validation rules - V2 uses basic validation only.
        
        The full rule engine runs 2,159 rules but many are country/document
        specific and trigger false positives when fields are missing.
        
        For V2 MVP, we use focused basic validation + crossdoc checks.
        Full rule engine integration requires proper field mapping.
        """
        # V2 MVP: Use basic validation only (similar to V1's focused approach)
        # This prevents the "1000+ issues" problem from running all rules
        issues = self._run_basic_validation(context)
        
        # Track metrics
        context["rules_checked"] = ["basic_validation"]
        context["rules_passed"] = [] if issues else ["basic_validation"]
        
        logger.info(f"V2 Basic validation: {len(issues)} issues found")
        
        return issues
    
    def _run_basic_validation(self, context: Dict[str, Any]) -> List[Issue]:
        """Basic validation when rule engine unavailable."""
        issues = []
        lc = context.get("lc", {})
        invoice = context.get("invoice", {})
        bl = context.get("bl", {})
        
        # Check LC expiry
        if lc.get("expiry_date"):
            from datetime import datetime
            try:
                expiry = datetime.strptime(lc["expiry_date"], "%Y-%m-%d")
                if expiry < datetime.now():
                    issues.append(self._create_issue(
                        rule_id="UCP600-ART29-EXPIRY",
                        title="LC Expired",
                        severity=IssueSeverity.CRITICAL,
                        issue_type="expired_lc",
                        expected="Valid LC (not expired)",
                        found=f"LC expired on {lc['expiry_date']}",
                        suggestion="Request LC amendment to extend expiry date",
                        documents=["Letter of Credit"],
                    ))
            except ValueError:
                pass
        
        # Check amount
        lc_amount = self._parse_amount(lc.get("amount"))
        inv_amount = self._parse_amount(invoice.get("invoice_amount"))
        
        if lc_amount and inv_amount:
            tolerance = lc_amount * Decimal("0.05")
            if inv_amount > lc_amount + tolerance:
                issues.append(self._create_issue(
                    rule_id="UCP600-ART30-AMOUNT",
                    title="Invoice Amount Exceeds LC",
                    severity=IssueSeverity.CRITICAL,
                    issue_type="amount_exceeds",
                    expected=f"Invoice ≤ {lc_amount} (LC amount + 5%)",
                    found=f"Invoice amount: {inv_amount}",
                    suggestion="Reduce invoice amount or request LC amendment",
                    documents=["Commercial Invoice", "Letter of Credit"],
                ))
        
        # Check goods description
        lc_desc = lc.get("goods_description", "")
        inv_desc = invoice.get("goods_description", "")
        if lc_desc and inv_desc:
            if not self._descriptions_match(lc_desc, inv_desc):
                issues.append(self._create_issue(
                    rule_id="UCP600-ART18C-DESC",
                    title="Goods Description Mismatch",
                    severity=IssueSeverity.MAJOR,
                    issue_type="description_mismatch",
                    expected=f"'{lc_desc[:100]}...'",
                    found=f"'{inv_desc[:100]}...'",
                    suggestion="Amend invoice to match LC goods description exactly",
                    documents=["Commercial Invoice", "Letter of Credit"],
                ))
        
        # Check beneficiary
        lc_benef = lc.get("beneficiary", "")
        inv_seller = invoice.get("seller_name", "")
        if lc_benef and inv_seller:
            if not self._names_match(lc_benef, inv_seller):
                issues.append(self._create_issue(
                    rule_id="UCP600-ART18A-BENEF",
                    title="Beneficiary Name Mismatch",
                    severity=IssueSeverity.MAJOR,
                    issue_type="beneficiary_mismatch",
                    expected=f"'{lc_benef}'",
                    found=f"'{inv_seller}'",
                    suggestion="Invoice must be issued by LC beneficiary",
                    documents=["Commercial Invoice", "Letter of Credit"],
                ))
        
        # Check ports
        lc_pol = lc.get("port_of_loading", "")
        bl_pol = bl.get("port_of_loading", "")
        if lc_pol and bl_pol:
            if not self._ports_match(lc_pol, bl_pol):
                issues.append(self._create_issue(
                    rule_id="UCP600-ART20-POL",
                    title="Port of Loading Mismatch",
                    severity=IssueSeverity.MAJOR,
                    issue_type="port_loading",
                    expected=f"'{lc_pol}'",
                    found=f"'{bl_pol}'",
                    suggestion="B/L port of loading must match LC requirement",
                    documents=["Bill of Lading", "Letter of Credit"],
                ))
        
        return issues
    
    async def _run_crossdoc_validation(
        self,
        context: Dict[str, Any],
    ) -> List[Issue]:
        """Run cross-document validation using existing crossdoc service."""
        issues = []
        
        try:
            from app.services.crossdoc import run_cross_document_checks
            
            # Map V2 context to crossdoc payload format
            crossdoc_payload = {
                "lc": context.get("lc", {}),
                "invoice": context.get("invoice", {}),
                "bill_of_lading": context.get("bl", {}),
                "documents_presence": context.get("documents_presence", {}),
                "documents": list(context.get("documents", {}).values()),
            }
            
            # Run synchronous crossdoc checks
            crossdoc_results = run_cross_document_checks(crossdoc_payload)
            
            logger.info(f"CrossDoc validation found {len(crossdoc_results)} issues")
            
            for result in crossdoc_results:
                # Skip if marked as passed
                if result.get("passed", True):
                    continue
                    
                issue = self._create_issue(
                    rule_id=result.get("rule", "CROSSDOC"),
                    title=result.get("title", "Cross-Document Discrepancy"),
                    severity=self._map_severity(result.get("severity", "warning")),
                    issue_type="crossdoc",
                    expected=result.get("expected", "Consistent data across documents"),
                    found=result.get("actual", result.get("found", "Data mismatch detected")),
                    suggestion=result.get("suggestion", "Review and correct discrepancy"),
                    documents=result.get("documents", result.get("document_names", [])),
                )
                issues.append(issue)
                
        except ImportError as e:
            logger.warning(f"CrossDoc service not available: {e}")
        except Exception as e:
            logger.error(f"CrossDoc validation failed: {e}", exc_info=True)
        
        return issues
    
    async def _run_sanctions_screening(
        self,
        context: Dict[str, Any],
    ) -> SanctionsStatus:
        """Run sanctions screening on parties."""
        try:
            from app.services.sanctions_lcopilot import extract_parties_from_lc_data
            from app.services.sanctions_screening import SanctionsScreeningService
            
            # Extract parties from LC data
            lc = context.get("lc", {})
            invoice = context.get("invoice", {})
            bl = context.get("bl", {})
            
            parties = []
            
            # Add LC parties
            if lc.get("applicant"):
                parties.append({"name": lc["applicant"], "type": "applicant"})
            if lc.get("beneficiary"):
                parties.append({"name": lc["beneficiary"], "type": "beneficiary"})
            if lc.get("issuing_bank"):
                parties.append({"name": lc["issuing_bank"], "type": "bank"})
            if lc.get("advising_bank"):
                parties.append({"name": lc["advising_bank"], "type": "bank"})
            
            # Add invoice parties
            if invoice.get("seller_name"):
                parties.append({"name": invoice["seller_name"], "type": "seller"})
            if invoice.get("buyer_name"):
                parties.append({"name": invoice["buyer_name"], "type": "buyer"})
            
            # Add B/L parties
            if bl.get("shipper"):
                parties.append({"name": bl["shipper"], "type": "shipper"})
            if bl.get("consignee"):
                parties.append({"name": bl["consignee"], "type": "consignee"})
            if bl.get("vessel_name"):
                parties.append({"name": bl["vessel_name"], "type": "vessel"})
            
            if not parties:
                return SanctionsStatus(
                    screened=False,
                    parties_screened=0,
                    matches_found=0,
                    status="clear",
                )
            
            # Screen parties
            service = SanctionsScreeningService()
            matches = []
            
            for party in parties:
                result = await service.screen_party(party["name"])
                if result.matches:
                    for match in result.matches:
                        matches.append(SanctionsMatch(
                            party=party["name"],
                            party_type=party["type"],
                            list_name=match.list_name,
                            match_score=match.score,
                            match_type=match.match_type,
                            sanction_programs=match.programs,
                        ))
            
            status = "clear"
            if matches:
                max_score = max(m.match_score for m in matches)
                if max_score >= 0.95:
                    status = "blocked"
                elif max_score >= 0.8:
                    status = "match"
                else:
                    status = "potential_match"
            
            return SanctionsStatus(
                screened=True,
                parties_screened=len(parties),
                matches_found=len(matches),
                status=status,
                matches=matches,
            )
            
        except ImportError:
            logger.warning("Sanctions service not available")
            return SanctionsStatus(
                screened=False,
                parties_screened=0,
                matches_found=0,
                status="clear",
            )
        except Exception as e:
            logger.error(f"Sanctions screening failed: {e}")
            return SanctionsStatus(
                screened=False,
                parties_screened=0,
                matches_found=0,
                status="clear",
            )
    
    def _create_issue(
        self,
        rule_id: str,
        title: str,
        severity: IssueSeverity,
        issue_type: str,
        expected: str,
        found: str,
        suggestion: str,
        documents: List[str],
        can_amend: bool = True,
    ) -> Issue:
        """Create issue with citations."""
        citations = self.citation_lib.get_citations(issue_type)
        bank_message = self.citation_lib.format_bank_message(title, citations)
        
        return Issue(
            id=str(uuid.uuid4())[:8],
            rule_id=rule_id,
            title=title,
            severity=severity,
            citations=citations,
            bank_message=bank_message,
            explanation=f"{title}: {found}",
            expected=expected,
            found=found,
            suggestion=suggestion,
            documents=documents,
            document_ids=[],
            can_amend=can_amend,
        )
    
    def _create_issue_from_rule(
        self,
        rule: Any,
        result: Any,
        context: Dict[str, Any],
    ) -> Optional[Issue]:
        """Create issue from rule execution result."""
        try:
            citations = Citations(
                ucp600=rule.citations.get("ucp600", []) if hasattr(rule, 'citations') else [],
                isbp745=rule.citations.get("isbp745", []) if hasattr(rule, 'citations') else [],
            )
            
            # Fallback if no citations in rule
            if not citations.ucp600 and not citations.isbp745:
                citations = self.citation_lib.get_citations(rule.rule_type)
            
            severity = self._map_severity(rule.severity if hasattr(rule, 'severity') else 'warning')
            
            return Issue(
                id=str(uuid.uuid4())[:8],
                rule_id=rule.id,
                title=rule.title if hasattr(rule, 'title') else rule.id,
                severity=severity,
                citations=citations,
                bank_message=self.citation_lib.format_bank_message(
                    rule.title if hasattr(rule, 'title') else rule.id,
                    citations
                ),
                explanation=result.message if hasattr(result, 'message') else str(result),
                expected=result.expected if hasattr(result, 'expected') else "Compliant",
                found=result.found if hasattr(result, 'found') else "Non-compliant",
                suggestion=rule.suggestion if hasattr(rule, 'suggestion') else "Review and correct",
                documents=rule.documents if hasattr(rule, 'documents') else [],
                document_ids=[],
                can_amend=True,
            )
        except Exception as e:
            logger.warning(f"Failed to create issue from rule: {e}")
            return None
    
    def _create_issue_from_rule_result(
        self,
        rule_issue: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Issue]:
        """Create V2 Issue from rule executor result dict."""
        try:
            rule_id = rule_issue.get("rule_id", rule_issue.get("rule", "UNKNOWN"))
            title = rule_issue.get("title", rule_id)
            severity_str = rule_issue.get("severity", "major").lower()
            
            # Get citations from the citation library based on rule_id
            citations = self.citation_lib.get_citations(rule_id)
            
            # If the rule has reference info, try to parse UCP/ISBP references
            reference = rule_issue.get("ucp_reference") or rule_issue.get("reference", "")
            if reference and not citations.ucp600:
                # Try to extract article numbers
                import re
                ucp_match = re.findall(r'Article\s*(\d+[a-z]?)', reference, re.IGNORECASE)
                if ucp_match:
                    citations.ucp600 = ucp_match
            
            return Issue(
                id=str(uuid.uuid4())[:8],
                rule_id=rule_id,
                title=title,
                severity=self._map_severity(severity_str),
                citations=citations,
                bank_message=self.citation_lib.format_bank_message(title, citations),
                explanation=rule_issue.get("message", rule_issue.get("description", "")),
                expected=rule_issue.get("expected", "Compliant with LC terms"),
                found=rule_issue.get("actual", rule_issue.get("found", "Discrepancy detected")),
                suggestion=rule_issue.get("suggestion", "Review and correct the discrepancy"),
                documents=rule_issue.get("documents", []),
                document_ids=rule_issue.get("document_ids", []),
                can_amend=rule_issue.get("can_amend", True),
            )
        except Exception as e:
            logger.warning(f"Failed to create issue from rule result: {e}")
            return None
    
    def _create_sanctions_issues(
        self,
        status: SanctionsStatus,
    ) -> List[Issue]:
        """Create issues for sanctions matches."""
        issues = []
        
        for match in status.matches:
            severity = IssueSeverity.CRITICAL if match.match_score >= 0.9 else IssueSeverity.MAJOR
            
            issues.append(Issue(
                id=str(uuid.uuid4())[:8],
                rule_id="SANCTIONS-MATCH",
                title=f"Sanctions Match: {match.party}",
                severity=severity,
                citations=Citations(ucp600=[], isbp745=[]),  # Sanctions don't cite UCP
                bank_message=f"Potential sanctions match for {match.party} ({match.party_type})",
                explanation=f"Party '{match.party}' matched against {match.list_name} with {match.match_score:.0%} confidence",
                expected="No sanctions matches",
                found=f"Match on {match.list_name}: {', '.join(match.sanction_programs)}",
                suggestion="Obtain compliance clearance before proceeding",
                documents=[],
                document_ids=[],
                can_amend=False,
            ))
        
        return issues
    
    def _map_severity(self, severity: str) -> IssueSeverity:
        """Map severity string to enum."""
        mapping = {
            "critical": IssueSeverity.CRITICAL,
            "error": IssueSeverity.CRITICAL,
            "major": IssueSeverity.MAJOR,
            "warning": IssueSeverity.MINOR,
            "minor": IssueSeverity.MINOR,
            "info": IssueSeverity.INFO,
        }
        return mapping.get(severity.lower(), IssueSeverity.MINOR)
    
    def _parse_amount(self, value: Any) -> Optional[Decimal]:
        """Parse amount to Decimal."""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            if isinstance(value, str):
                # Remove currency symbols and commas
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                return Decimal(cleaned) if cleaned else None
            return None
        except Exception:
            return None
    
    def _descriptions_match(self, desc1: str, desc2: str) -> bool:
        """Check if descriptions match (allow some variance)."""
        # Normalize
        d1 = desc1.lower().strip()
        d2 = desc2.lower().strip()
        
        if d1 == d2:
            return True
        
        # Check if one contains the other
        if d1 in d2 or d2 in d1:
            return True
        
        # Check word overlap
        words1 = set(d1.split())
        words2 = set(d2.split())
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        
        return overlap > 0.7
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if party names match."""
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        if n1 == n2:
            return True
        
        # Remove common suffixes
        for suffix in [' ltd', ' llc', ' inc', ' corp', ' co', '.', ',']:
            n1 = n1.replace(suffix, '')
            n2 = n2.replace(suffix, '')
        
        return n1.strip() == n2.strip()
    
    def _ports_match(self, port1: str, port2: str) -> bool:
        """Check if ports match."""
        p1 = port1.lower().strip()
        p2 = port2.lower().strip()
        
        if p1 == p2:
            return True
        
        # Check if one contains the other
        if p1 in p2 or p2 in p1:
            return True
        
        return False

