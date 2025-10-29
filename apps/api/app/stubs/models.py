"""
Pydantic models for stub scenario configuration.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, validator
from datetime import datetime
import re


class StubExtractedField(BaseModel):
    """Stub representation of an extracted field."""
    field_name: str
    field_type: str  # date, amount, party, port, text
    value: Optional[str] = None
    confidence: float = 0.95
    raw_text: Optional[str] = None
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        return max(0.0, min(1.0, v))
    
    @validator('field_type')
    def validate_field_type(cls, v):
        """Validate field type is one of expected values."""
        allowed = {'date', 'amount', 'party', 'port', 'text', 'number'}
        if v not in allowed:
            raise ValueError(f'field_type must be one of {allowed}')
        return v
    
    @validator('value')
    def validate_field_value(cls, v, values):
        """Validate field value based on field type."""
        if v is None:
            return v
            
        field_type = values.get('field_type', '')
        
        if field_type == 'date':
            # Validate date format (YYYY-MM-DD or MM/DD/YYYY or DD/MM/YYYY)
            date_patterns = [
                r'^\d{4}-\d{2}-\d{2}$',  # 2024-01-15
                r'^\d{2}/\d{2}/\d{4}$',  # 01/15/2024
                r'^\d{1,2}/\d{1,2}/\d{4}$',  # 1/15/2024
                r'^\d{2}-\d{2}-\d{4}$',  # 01-15-2024
            ]
            if not any(re.match(pattern, v) for pattern in date_patterns):
                raise ValueError(f'Date value "{v}" must be in format YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY')
        
        elif field_type == 'amount':
            # Validate amount format (with or without currency symbol)
            amount_pattern = r'^(\$|USD|€|EUR)?\s*\d{1,3}(,\d{3})*(\.\d{2})?$'
            if not re.match(amount_pattern, v.replace(' ', '')):
                raise ValueError(f'Amount value "{v}" must be in currency format (e.g., $1,000.00)')
        
        elif field_type == 'number':
            # Validate numeric value
            try:
                float(v.replace(',', ''))
            except ValueError:
                raise ValueError(f'Number value "{v}" must be numeric')
        
        return v


class StubDocumentData(BaseModel):
    """Stub data for a specific document type."""
    document_type: str  # letter_of_credit, commercial_invoice, bill_of_lading
    ocr_confidence: float = 0.92
    processing_time_ms: int = 1500
    extracted_fields: List[StubExtractedField] = []
    full_text: str = ""
    
    @validator('document_type')
    def validate_document_type(cls, v):
        """Validate document type."""
        allowed = {'letter_of_credit', 'commercial_invoice', 'bill_of_lading'}
        if v not in allowed:
            raise ValueError(f'document_type must be one of {allowed}')
        return v


class StubScenarioModel(BaseModel):
    """
    Complete stub scenario configuration.
    
    This model defines all the data needed to simulate a realistic
    OCR and validation scenario for testing purposes.
    """
    scenario_name: str
    description: str
    created_at: datetime = datetime.now()
    
    # OCR simulation data
    documents: List[StubDocumentData] = []
    
    # Expected validation outcomes
    expected_discrepancies: int = 0
    expected_critical_issues: int = 0
    expected_major_issues: int = 0
    expected_minor_issues: int = 0
    
    # Error simulation flags (overridden by env vars if set)
    simulate_ocr_failure: bool = False
    simulate_storage_failure: bool = False
    
    # Metadata
    tags: List[str] = []
    notes: Optional[str] = None
    
    def get_document_data(self, document_type: str) -> Optional[StubDocumentData]:
        """Get stub data for a specific document type."""
        for doc in self.documents:
            if doc.document_type == document_type:
                return doc
        return None
    
    def has_document(self, document_type: str) -> bool:
        """Check if scenario has data for a document type."""
        return self.get_document_data(document_type) is not None