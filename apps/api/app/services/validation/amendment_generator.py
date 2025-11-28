"""
LC Amendment Draft Generator

Generates SWIFT MT707 amendment drafts for common discrepancies.

Usage:
    When a discrepancy is detected that can be fixed via LC amendment,
    this module generates bank-ready SWIFT text.

Supported Discrepancies:
- Late shipment (Field 44C)
- Amount changes (Field 32B)
- Expiry date extension (Field 31D)
- Port changes (Field 44E, 44F)
- Quantity changes (Field 45A)
- Goods description changes (Field 45A)
- Document requirement changes (Field 46A)
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import re


@dataclass
class AmendmentDraft:
    """A SWIFT MT707 amendment draft."""
    discrepancy_type: str
    field_tag: str
    field_name: str
    current_value: str
    proposed_value: str
    swift_text: str
    narrative: str
    estimated_fee_usd: float = 75.0
    bank_processing_days: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "discrepancy_type": self.discrepancy_type,
            "field": {
                "tag": self.field_tag,
                "name": self.field_name,
                "current": self.current_value,
                "proposed": self.proposed_value,
            },
            "swift_mt707_text": self.swift_text,
            "narrative": self.narrative,
            "estimated_fee_usd": self.estimated_fee_usd,
            "bank_processing_days": self.bank_processing_days,
        }


def _format_swift_date(d: date) -> str:
    """Format date as YYMMDD for SWIFT."""
    return d.strftime("%y%m%d")


def _format_swift_amount(amount: float, currency: str = "USD") -> str:
    """Format amount for SWIFT field 32B."""
    # SWIFT format: Currency + Amount with comma as decimal separator
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "")
    return f"{currency}{formatted}"


def generate_late_shipment_amendment(
    current_date: str,
    proposed_date: str,
    lc_number: str,
) -> AmendmentDraft:
    """
    Generate amendment for late shipment date.
    
    Field 44C: Latest Date of Shipment
    """
    # Parse dates
    try:
        if len(current_date) == 6:  # YYMMDD
            current_dt = datetime.strptime(current_date, "%y%m%d").date()
        else:
            current_dt = datetime.strptime(current_date, "%Y-%m-%d").date()
    except:
        current_dt = date.today()
    
    try:
        if len(proposed_date) == 6:
            proposed_dt = datetime.strptime(proposed_date, "%y%m%d").date()
        else:
            proposed_dt = datetime.strptime(proposed_date, "%Y-%m-%d").date()
    except:
        proposed_dt = date.today()
    
    current_swift = _format_swift_date(current_dt)
    proposed_swift = _format_swift_date(proposed_dt)
    
    swift_text = f"""MT707 AMENDMENT TO DOCUMENTARY CREDIT

:20: {lc_number}
:21: AMENDMENT TO LC

:79: PLS AMEND FLD 44C
     FROM: {current_swift}
     TO:   {proposed_swift}
     
     LATEST DATE OF SHIPMENT EXTENDED FROM 
     {current_dt.strftime('%d %b %Y').upper()} TO 
     {proposed_dt.strftime('%d %b %Y').upper()}
     
     ALL OTHER TERMS AND CONDITIONS REMAIN UNCHANGED."""
    
    return AmendmentDraft(
        discrepancy_type="late_shipment",
        field_tag="44C",
        field_name="Latest Date of Shipment",
        current_value=current_swift,
        proposed_value=proposed_swift,
        swift_text=swift_text,
        narrative=f"Extend latest shipment date from {current_dt.strftime('%d %b %Y')} to {proposed_dt.strftime('%d %b %Y')}",
        estimated_fee_usd=75.0,
    )


def generate_amount_amendment(
    current_amount: float,
    proposed_amount: float,
    currency: str,
    lc_number: str,
) -> AmendmentDraft:
    """
    Generate amendment for LC amount change.
    
    Field 32B: Amount
    """
    current_swift = _format_swift_amount(current_amount, currency)
    proposed_swift = _format_swift_amount(proposed_amount, currency)
    
    change = proposed_amount - current_amount
    change_pct = (change / current_amount) * 100 if current_amount else 0
    
    swift_text = f"""MT707 AMENDMENT TO DOCUMENTARY CREDIT

:20: {lc_number}
:21: AMENDMENT TO LC

:32B: {proposed_swift}

:79: PLS AMEND FLD 32B
     FROM: {current_swift}
     TO:   {proposed_swift}
     
     LC AMOUNT {'INCREASED' if change > 0 else 'DECREASED'} BY {currency} {abs(change):,.2f}
     ({'+' if change > 0 else ''}{change_pct:.1f}%)
     
     ALL OTHER TERMS AND CONDITIONS REMAIN UNCHANGED."""
    
    return AmendmentDraft(
        discrepancy_type="amount_change",
        field_tag="32B",
        field_name="Amount",
        current_value=current_swift,
        proposed_value=proposed_swift,
        swift_text=swift_text,
        narrative=f"{'Increase' if change > 0 else 'Decrease'} LC amount by {currency} {abs(change):,.2f} ({change_pct:+.1f}%)",
        estimated_fee_usd=100.0,  # Amount amendments typically cost more
    )


def generate_expiry_amendment(
    current_date: str,
    proposed_date: str,
    lc_number: str,
) -> AmendmentDraft:
    """
    Generate amendment for expiry date extension.
    
    Field 31D: Date and Place of Expiry
    """
    try:
        if len(current_date) == 6:
            current_dt = datetime.strptime(current_date, "%y%m%d").date()
        else:
            current_dt = datetime.strptime(current_date, "%Y-%m-%d").date()
    except:
        current_dt = date.today()
    
    try:
        if len(proposed_date) == 6:
            proposed_dt = datetime.strptime(proposed_date, "%y%m%d").date()
        else:
            proposed_dt = datetime.strptime(proposed_date, "%Y-%m-%d").date()
    except:
        proposed_dt = date.today()
    
    current_swift = _format_swift_date(current_dt)
    proposed_swift = _format_swift_date(proposed_dt)
    
    swift_text = f"""MT707 AMENDMENT TO DOCUMENTARY CREDIT

:20: {lc_number}
:21: AMENDMENT TO LC

:31D: {proposed_swift}

:79: PLS AMEND FLD 31D
     FROM: {current_swift}
     TO:   {proposed_swift}
     
     EXPIRY DATE EXTENDED FROM
     {current_dt.strftime('%d %b %Y').upper()} TO
     {proposed_dt.strftime('%d %b %Y').upper()}
     
     ALL OTHER TERMS AND CONDITIONS REMAIN UNCHANGED."""
    
    return AmendmentDraft(
        discrepancy_type="expiry_extension",
        field_tag="31D",
        field_name="Date and Place of Expiry",
        current_value=current_swift,
        proposed_value=proposed_swift,
        swift_text=swift_text,
        narrative=f"Extend LC expiry from {current_dt.strftime('%d %b %Y')} to {proposed_dt.strftime('%d %b %Y')}",
        estimated_fee_usd=75.0,
    )


def generate_port_amendment(
    port_type: str,  # "loading" or "discharge"
    current_port: str,
    proposed_port: str,
    lc_number: str,
) -> AmendmentDraft:
    """
    Generate amendment for port change.
    
    Field 44E: Port of Loading
    Field 44F: Port of Discharge
    """
    field_tag = "44E" if port_type == "loading" else "44F"
    field_name = "Port of Loading" if port_type == "loading" else "Port of Discharge"
    
    swift_text = f"""MT707 AMENDMENT TO DOCUMENTARY CREDIT

:20: {lc_number}
:21: AMENDMENT TO LC

:{field_tag}: {proposed_port.upper()}

:79: PLS AMEND FLD {field_tag}
     FROM: {current_port.upper()}
     TO:   {proposed_port.upper()}
     
     {field_name.upper()} CHANGED
     
     ALL OTHER TERMS AND CONDITIONS REMAIN UNCHANGED."""
    
    return AmendmentDraft(
        discrepancy_type=f"port_{port_type}_change",
        field_tag=field_tag,
        field_name=field_name,
        current_value=current_port.upper(),
        proposed_value=proposed_port.upper(),
        swift_text=swift_text,
        narrative=f"Change {field_name.lower()} from {current_port} to {proposed_port}",
        estimated_fee_usd=75.0,
    )


def generate_document_requirement_amendment(
    action: str,  # "add" or "remove"
    document_description: str,
    lc_number: str,
) -> AmendmentDraft:
    """
    Generate amendment to add/remove document requirement.
    
    Field 46A: Documents Required
    """
    if action == "add":
        swift_text = f"""MT707 AMENDMENT TO DOCUMENTARY CREDIT

:20: {lc_number}
:21: AMENDMENT TO LC

:79: PLS AMEND FLD 46A
     ADD THE FOLLOWING DOCUMENT:
     
     {document_description.upper()}
     
     ALL OTHER TERMS AND CONDITIONS REMAIN UNCHANGED."""
        narrative = f"Add document requirement: {document_description}"
    else:
        swift_text = f"""MT707 AMENDMENT TO DOCUMENTARY CREDIT

:20: {lc_number}
:21: AMENDMENT TO LC

:79: PLS AMEND FLD 46A
     DELETE THE FOLLOWING DOCUMENT REQUIREMENT:
     
     {document_description.upper()}
     
     ALL OTHER TERMS AND CONDITIONS REMAIN UNCHANGED."""
        narrative = f"Remove document requirement: {document_description}"
    
    return AmendmentDraft(
        discrepancy_type=f"document_requirement_{action}",
        field_tag="46A",
        field_name="Documents Required",
        current_value="(see LC)" if action == "add" else document_description,
        proposed_value=document_description if action == "add" else "(removed)",
        swift_text=swift_text,
        narrative=narrative,
        estimated_fee_usd=75.0,
    )


def generate_amendment_for_discrepancy(
    discrepancy: Dict[str, Any],
    lc_data: Dict[str, Any],
) -> Optional[AmendmentDraft]:
    """
    Generate appropriate amendment draft based on discrepancy type.
    
    Args:
        discrepancy: Discrepancy details from validator
        lc_data: LC information including lc_number
        
    Returns:
        AmendmentDraft if applicable, None if amendment not possible
    """
    rule_id = discrepancy.get("rule", "")
    title = discrepancy.get("title", "").lower()
    lc_number = lc_data.get("lc_number", "UNKNOWN")
    
    # Late shipment
    if "late" in title and "shipment" in title:
        # Extract dates from discrepancy
        found = discrepancy.get("found", "")
        expected = discrepancy.get("expected", "")
        
        # Parse dates from strings
        current_date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{6})', expected)
        proposed_date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{6})', found)
        
        if current_date_match and proposed_date_match:
            return generate_late_shipment_amendment(
                current_date=current_date_match.group(1),
                proposed_date=proposed_date_match.group(1),
                lc_number=lc_number,
            )
    
    # Amount exceeds LC
    if "amount" in title and ("exceed" in title or "mismatch" in title):
        current_amount = lc_data.get("amount", 0)
        currency = lc_data.get("currency", "USD")
        
        # Try to extract proposed amount from found field
        found = discrepancy.get("found", "")
        amount_match = re.search(r'[\d,]+\.?\d*', found.replace(",", ""))
        if amount_match:
            proposed_amount = float(amount_match.group().replace(",", ""))
            return generate_amount_amendment(
                current_amount=current_amount,
                proposed_amount=proposed_amount,
                currency=currency,
                lc_number=lc_number,
            )
    
    # Port mismatch
    if "port" in title:
        current_port = discrepancy.get("expected", "").split(":")[-1].strip()
        proposed_port = discrepancy.get("found", "").split(":")[-1].strip()
        port_type = "loading" if "loading" in title.lower() else "discharge"
        
        if current_port and proposed_port:
            return generate_port_amendment(
                port_type=port_type,
                current_port=current_port,
                proposed_port=proposed_port,
                lc_number=lc_number,
            )
    
    # Missing document (can't be amended, but we can suggest adding to LC)
    if "missing" in title and "document" in title:
        doc_name = discrepancy.get("documents", ["Unknown"])[0]
        # This is informational only - beneficiary needs to obtain the document
        # Amendment would be to REMOVE the requirement (requires applicant consent)
        return None
    
    return None


# =============================================================================
# BULK AMENDMENT GENERATOR
# =============================================================================

def generate_amendments_for_issues(
    issues: List[Dict[str, Any]],
    lc_data: Dict[str, Any],
) -> List[AmendmentDraft]:
    """
    Generate all possible amendments for a list of issues.
    
    Args:
        issues: List of validation issues
        lc_data: LC information
        
    Returns:
        List of AmendmentDraft objects for issues that can be fixed via amendment
    """
    amendments = []
    
    for issue in issues:
        amendment = generate_amendment_for_discrepancy(issue, lc_data)
        if amendment:
            amendments.append(amendment)
    
    return amendments


def calculate_total_amendment_cost(amendments: List[AmendmentDraft]) -> Dict[str, Any]:
    """Calculate total estimated cost of amendments."""
    total_fee = sum(a.estimated_fee_usd for a in amendments)
    max_processing_days = max((a.bank_processing_days for a in amendments), default=0)
    
    return {
        "total_amendments": len(amendments),
        "total_estimated_fee_usd": total_fee,
        "max_processing_days": max_processing_days,
        "amendments_by_field": {a.field_tag: a.to_dict() for a in amendments},
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AmendmentDraft",
    "generate_late_shipment_amendment",
    "generate_amount_amendment",
    "generate_expiry_amendment",
    "generate_port_amendment",
    "generate_document_requirement_amendment",
    "generate_amendment_for_discrepancy",
    "generate_amendments_for_issues",
    "calculate_total_amendment_cost",
]

