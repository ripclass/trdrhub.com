"""
MT700 SWIFT Message Generator

Generates MT700 format messages for LC applications.
MT700 is the SWIFT message type for Documentary Credit Issuance.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class MT700Field:
    """A single field in MT700 format"""
    tag: str
    name: str
    value: str
    is_mandatory: bool = True
    max_length: Optional[int] = None
    
    def validate(self) -> Optional[str]:
        """Returns error message if invalid, None if valid"""
        if self.is_mandatory and not self.value:
            return f"Field {self.tag} ({self.name}) is mandatory"
        if self.max_length and len(self.value) > self.max_length:
            return f"Field {self.tag} ({self.name}) exceeds max length {self.max_length}"
        return None


class MT700Generator:
    """
    Generates MT700 SWIFT messages for Documentary Credit Issuance.
    
    MT700 Structure:
    - Sequence A: General Information
    - Sequence B: Details of Credit
    """
    
    # Field definitions with max lengths per SWIFT standards
    FIELD_SPECS = {
        "27": {"name": "Sequence of Total", "max": 6},
        "40A": {"name": "Form of Documentary Credit", "max": 24},
        "20": {"name": "Documentary Credit Number", "max": 16},
        "23": {"name": "Reference to Pre-Advice", "max": 16},
        "31C": {"name": "Date of Issue", "max": 8},
        "40E": {"name": "Applicable Rules", "max": 35},
        "31D": {"name": "Date and Place of Expiry", "max": 35},
        "51a": {"name": "Applicant Bank", "max": 35},
        "50": {"name": "Applicant", "max": 140},
        "59": {"name": "Beneficiary", "max": 140},
        "32B": {"name": "Currency Code, Amount", "max": 18},
        "39A": {"name": "Percentage Credit Amount Tolerance", "max": 5},
        "39B": {"name": "Maximum Credit Amount", "max": 13},
        "39C": {"name": "Additional Amounts Covered", "max": 100},
        "41a": {"name": "Available With ... By ...", "max": 35},
        "42C": {"name": "Drafts at ...", "max": 105},
        "42a": {"name": "Drawee", "max": 35},
        "42M": {"name": "Mixed Payment Details", "max": 210},
        "42P": {"name": "Deferred Payment Details", "max": 210},
        "43P": {"name": "Partial Shipments", "max": 11},
        "43T": {"name": "Transhipment", "max": 11},
        "44A": {"name": "Place of Taking in Charge/Dispatch from", "max": 65},
        "44E": {"name": "Port of Loading/Airport of Departure", "max": 65},
        "44F": {"name": "Port of Discharge/Airport of Destination", "max": 65},
        "44B": {"name": "Place of Final Destination", "max": 65},
        "44C": {"name": "Latest Date of Shipment", "max": 8},
        "44D": {"name": "Shipment Period", "max": 65},
        "45A": {"name": "Description of Goods and/or Services", "max": 10000},
        "46A": {"name": "Documents Required", "max": 10000},
        "47A": {"name": "Additional Conditions", "max": 10000},
        "71D": {"name": "Charges", "max": 210},
        "48": {"name": "Period for Presentation", "max": 35},
        "49": {"name": "Confirmation Instructions", "max": 7},
        "53a": {"name": "Reimbursing Bank", "max": 35},
        "78": {"name": "Instructions to Paying/Accepting/Negotiating Bank", "max": 1000},
        "57a": {"name": "Advise Through Bank", "max": 35},
        "72Z": {"name": "Sender to Receiver Information", "max": 420},
    }
    
    def __init__(self, lc_data: Dict[str, Any]):
        """
        Initialize with LC application data.
        
        Args:
            lc_data: Dictionary containing LC application fields
        """
        self.lc_data = lc_data
        self.fields: List[MT700Field] = []
        self.validation_errors: List[str] = []
    
    def _format_date(self, date_val) -> str:
        """Format date to YYMMDD for SWIFT"""
        if not date_val:
            return ""
        if isinstance(date_val, str):
            try:
                date_val = datetime.fromisoformat(date_val.replace("Z", ""))
            except:
                return date_val
        return date_val.strftime("%y%m%d")
    
    def _format_amount(self, currency: str, amount: float) -> str:
        """Format currency and amount for field 32B"""
        # Format: CUR + amount with comma as decimal
        amount_str = f"{amount:,.2f}".replace(",", "")
        return f"{currency}{amount_str}"
    
    def _format_tolerance(self, plus: float, minus: float) -> str:
        """Format tolerance for field 39A"""
        if plus == minus:
            return f"{int(plus)}/{int(minus)}"
        return f"{int(plus)}/{int(minus)}"
    
    def _format_multiline(self, text: str, line_length: int = 65) -> str:
        """Split text into SWIFT-compliant lines"""
        if not text:
            return ""
        
        lines = []
        current_line = ""
        
        for word in text.split():
            if len(current_line) + len(word) + 1 <= line_length:
                current_line = f"{current_line} {word}".strip()
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return "\n".join(lines)
    
    def _format_party(self, name: str, address: str, country: str) -> str:
        """Format party (applicant/beneficiary) for SWIFT"""
        lines = [name]
        if address:
            # Split address into lines of max 35 chars
            for line in address.split("\n"):
                if len(line) > 35:
                    # Word wrap
                    words = line.split()
                    current = ""
                    for word in words:
                        if len(current) + len(word) + 1 <= 35:
                            current = f"{current} {word}".strip()
                        else:
                            if current:
                                lines.append(current)
                            current = word
                    if current:
                        lines.append(current)
                else:
                    lines.append(line)
        if country:
            lines.append(country)
        return "\n".join(lines[:4])  # Max 4 lines
    
    def _add_field(self, tag: str, value: str, is_mandatory: bool = True):
        """Add a field to the message"""
        spec = self.FIELD_SPECS.get(tag, {})
        field = MT700Field(
            tag=tag,
            name=spec.get("name", "Unknown"),
            value=value,
            is_mandatory=is_mandatory,
            max_length=spec.get("max")
        )
        
        error = field.validate()
        if error:
            self.validation_errors.append(error)
        
        self.fields.append(field)
    
    def build(self) -> Dict[str, Any]:
        """
        Build the MT700 message.
        
        Returns:
            Dictionary with 'message', 'fields', 'validation_errors', 'character_count'
        """
        self.fields = []
        self.validation_errors = []
        
        data = self.lc_data
        
        # Sequence of Total
        self._add_field("27", "1/1")
        
        # Form of Documentary Credit
        lc_type_map = {
            "documentary": "IRREVOCABLE",
            "standby": "IRREVOCABLE STANDBY",
            "transferable": "IRREVOCABLE TRANSFERABLE",
            "revolving": "IRREVOCABLE REVOLVING",
        }
        form = lc_type_map.get(data.get("lc_type", "documentary"), "IRREVOCABLE")
        self._add_field("40A", form)
        
        # Documentary Credit Number
        self._add_field("20", data.get("reference_number", "")[:16])
        
        # Date of Issue
        self._add_field("31C", self._format_date(datetime.now()))
        
        # Applicable Rules
        self._add_field("40E", "UCP LATEST VERSION")
        
        # Date and Place of Expiry
        expiry = f"{self._format_date(data.get('expiry_date'))} {data.get('expiry_place', '')}"
        self._add_field("31D", expiry.strip())
        
        # Applicant
        applicant = data.get("applicant", {})
        if isinstance(applicant, dict):
            applicant_text = self._format_party(
                applicant.get("name", ""),
                applicant.get("address", ""),
                applicant.get("country", "")
            )
        else:
            applicant_text = data.get("applicant_name", "")
        self._add_field("50", applicant_text)
        
        # Beneficiary
        beneficiary = data.get("beneficiary", {})
        if isinstance(beneficiary, dict):
            beneficiary_text = self._format_party(
                beneficiary.get("name", ""),
                beneficiary.get("address", ""),
                beneficiary.get("country", "")
            )
        else:
            beneficiary_text = data.get("beneficiary_name", "")
        self._add_field("59", beneficiary_text)
        
        # Currency and Amount
        currency = data.get("currency", "USD")
        amount = data.get("amount", 0)
        self._add_field("32B", self._format_amount(currency, amount))
        
        # Tolerance
        tol_plus = data.get("tolerance_plus", 0)
        tol_minus = data.get("tolerance_minus", 0)
        if tol_plus or tol_minus:
            self._add_field("39A", self._format_tolerance(tol_plus, tol_minus), is_mandatory=False)
        
        # Available With ... By ...
        payment_terms = data.get("payment_terms", "sight")
        if payment_terms == "sight":
            self._add_field("41a", "ANY BANK BY NEGOTIATION")
        else:
            self._add_field("41a", "ISSUING BANK BY DEF PAYMENT")
        
        # Drafts at
        if payment_terms == "sight":
            self._add_field("42C", "AT SIGHT", is_mandatory=False)
        elif payment_terms == "usance":
            days = data.get("usance_days", 30)
            from_date = data.get("usance_from", "B/L DATE")
            self._add_field("42C", f"AT {days} DAYS FROM {from_date.upper()}", is_mandatory=False)
        
        # Partial Shipments
        partial = "ALLOWED" if data.get("partial_shipments", True) else "NOT ALLOWED"
        self._add_field("43P", partial)
        
        # Transhipment
        tranship = "ALLOWED" if data.get("transhipment", True) else "NOT ALLOWED"
        self._add_field("43T", tranship)
        
        # Port of Loading
        if data.get("port_of_loading"):
            self._add_field("44E", data["port_of_loading"], is_mandatory=False)
        
        # Port of Discharge
        if data.get("port_of_discharge"):
            self._add_field("44F", data["port_of_discharge"], is_mandatory=False)
        
        # Place of Final Destination
        if data.get("place_of_delivery"):
            self._add_field("44B", data["place_of_delivery"], is_mandatory=False)
        
        # Latest Date of Shipment
        if data.get("latest_shipment_date"):
            self._add_field("44C", self._format_date(data["latest_shipment_date"]))
        
        # Description of Goods
        goods_desc = data.get("goods_description", "")
        incoterms = data.get("incoterms", "")
        incoterms_place = data.get("incoterms_place", "")
        
        full_goods = goods_desc
        if incoterms:
            full_goods += f"\n{incoterms} {incoterms_place} INCOTERMS 2020"
        
        self._add_field("45A", self._format_multiline(full_goods))
        
        # Documents Required
        docs = data.get("documents_required", [])
        if docs:
            doc_lines = []
            for i, doc in enumerate(docs, 1):
                if isinstance(doc, dict):
                    doc_type = doc.get("document_type", "")
                    copies_orig = doc.get("copies_original", 1)
                    copies_copy = doc.get("copies_copy", 0)
                    specific = doc.get("specific_requirements", "")
                    
                    line = f"+{doc_type.upper()}"
                    if copies_orig:
                        line += f" IN {copies_orig} ORIGINAL(S)"
                    if copies_copy:
                        line += f" AND {copies_copy} COPY(IES)"
                    if specific:
                        line += f" - {specific}"
                    doc_lines.append(line)
                else:
                    doc_lines.append(f"+{doc}")
            
            self._add_field("46A", "\n".join(doc_lines))
        
        # Additional Conditions
        conditions = data.get("additional_conditions", [])
        if conditions:
            cond_text = "\n".join([f"+{c}" for c in conditions])
            self._add_field("47A", cond_text, is_mandatory=False)
        
        # Charges
        self._add_field("71D", "ALL BANKING CHARGES OUTSIDE ISSUING COUNTRY FOR BENEFICIARY'S ACCOUNT", is_mandatory=False)
        
        # Period for Presentation
        pres_period = data.get("presentation_period", 21)
        self._add_field("48", f"DOCUMENTS MUST BE PRESENTED WITHIN {pres_period} DAYS AFTER SHIPMENT BUT WITHIN CREDIT VALIDITY")
        
        # Confirmation Instructions
        confirm_map = {
            "without": "WITHOUT",
            "may_add": "MAY ADD",
            "confirm": "CONFIRM",
        }
        confirm = confirm_map.get(data.get("confirmation_instructions", "without"), "WITHOUT")
        self._add_field("49", confirm)
        
        # Build the message
        message_lines = [
            "{1:F01BANKDEFAXXXX0000000000}",
            "{2:O7001200210315BANKDEFAXXXX00000000002103150000N}",
            "{4:",
        ]
        
        for field in self.fields:
            if field.value:
                # Handle multiline values
                if "\n" in field.value:
                    message_lines.append(f":{field.tag}:")
                    for line in field.value.split("\n"):
                        message_lines.append(line)
                else:
                    message_lines.append(f":{field.tag}:{field.value}")
        
        message_lines.append("-}")
        
        full_message = "\n".join(message_lines)
        
        return {
            "message": full_message,
            "fields": [
                {
                    "tag": f.tag,
                    "name": f.name,
                    "value": f.value,
                    "is_mandatory": f.is_mandatory,
                    "length": len(f.value) if f.value else 0,
                    "max_length": f.max_length,
                }
                for f in self.fields
            ],
            "validation_errors": self.validation_errors,
            "character_count": len(full_message),
            "is_valid": len(self.validation_errors) == 0,
        }
    
    @staticmethod
    def field_reference() -> List[Dict[str, Any]]:
        """Get MT700 field reference for UI"""
        return [
            {"tag": tag, **spec}
            for tag, spec in MT700Generator.FIELD_SPECS.items()
        ]

