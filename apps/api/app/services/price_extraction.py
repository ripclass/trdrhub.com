"""
Price Extraction Service

Extracts commodity prices from trade documents (invoices, LCs, contracts)
using OCR + AI extraction pipeline. Reuses LCopilot's existing infrastructure.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from app.services.llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

# =============================================================================
# PRICE EXTRACTION PROMPTS
# =============================================================================

PRICE_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in extracting commodity and price information.

Your task is to extract structured price data from trade documents including:
- Commercial Invoices
- Letters of Credit
- Purchase Contracts
- Proforma Invoices

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. If a field is not found, return null - do NOT guess
3. For amounts, include the full number without currency symbols
4. Be precise about units of measure (kg, mt, pieces, etc.)
5. Extract ALL line items if there are multiple commodities
6. Look for HS codes if present - they help identify commodities

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

PRICE_EXTRACTION_PROMPT = """Extract commodity and price information from this trade document.

For EACH commodity/line item found, extract:
- commodity_name: Name/description of the goods
- commodity_code: HS code if present (e.g., "5201.00")
- quantity: Amount being traded
- unit: Unit of measure (kg, mt, pcs, etc.)
- unit_price: Price per unit
- total_price: Total price for this line item
- currency: Currency code (USD, EUR, etc.)

Also extract document-level information:
- document_type: Type of document (invoice, lc, contract, proforma)
- document_number: Reference number
- document_date: Date of document
- seller_name: Seller/exporter
- buyer_name: Buyer/importer
- origin_country: Country of origin
- destination_country: Destination country

Return a JSON object with:
{{
    "document_info": {{
        "document_type": "...",
        "document_number": "...",
        "document_date": "...",
        "seller_name": "...",
        "buyer_name": "...",
        "origin_country": "...",
        "destination_country": "..."
    }},
    "line_items": [
        {{
            "commodity_name": "...",
            "commodity_code": "...",
            "quantity": 123.45,
            "unit": "kg",
            "unit_price": 2.50,
            "total_price": 308.63,
            "currency": "USD"
        }}
    ],
    "totals": {{
        "total_amount": 12345.67,
        "currency": "USD"
    }}
}}

---
DOCUMENT TEXT:
{document_text}
---
"""


@dataclass
class ExtractedLineItem:
    """Extracted line item from a trade document."""
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    currency: str = "USD"
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity_name": self.commodity_name,
            "commodity_code": self.commodity_code,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "currency": self.currency,
            "confidence": self.confidence,
        }


@dataclass
class PriceExtractionResult:
    """Result of price extraction from a document."""
    success: bool = False
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[str] = None
    seller_name: Optional[str] = None
    buyer_name: Optional[str] = None
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    line_items: List[ExtractedLineItem] = field(default_factory=list)
    total_amount: Optional[float] = None
    currency: str = "USD"
    extraction_method: str = "ai"
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    raw_text_preview: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "document_info": {
                "document_type": self.document_type,
                "document_number": self.document_number,
                "document_date": self.document_date,
                "seller_name": self.seller_name,
                "buyer_name": self.buyer_name,
                "origin_country": self.origin_country,
                "destination_country": self.destination_country,
            },
            "line_items": [item.to_dict() for item in self.line_items],
            "totals": {
                "total_amount": self.total_amount,
                "currency": self.currency,
            },
            "extraction_metadata": {
                "method": self.extraction_method,
                "confidence": self.confidence,
                "errors": self.errors,
            },
        }


class PriceExtractionService:
    """
    Extracts commodity prices from trade documents.
    Reuses LCopilot's OCR and AI infrastructure.
    """
    
    def __init__(self):
        self.llm_provider = LLMProviderFactory.create_provider()
    
    async def extract_prices_from_text(
        self,
        raw_text: str,
        filename: Optional[str] = None,
    ) -> PriceExtractionResult:
        """
        Extract prices from OCR/document text using AI.
        
        Args:
            raw_text: Text content from OCR or document
            filename: Optional filename for context
            
        Returns:
            PriceExtractionResult with extracted line items
        """
        result = PriceExtractionResult()
        result.raw_text_preview = raw_text[:500] if raw_text else None
        
        if not raw_text or not raw_text.strip():
            result.errors.append("Empty document text")
            return result
        
        # Step 1: Try AI extraction
        try:
            ai_result = await self._run_ai_extraction(raw_text)
            
            if ai_result:
                result = self._parse_ai_result(ai_result, result)
                result.extraction_method = "ai"
                result.success = len(result.line_items) > 0
                result.confidence = 0.85 if result.success else 0.0
                
        except Exception as e:
            logger.error(f"AI extraction error: {e}", exc_info=True)
            result.errors.append(f"AI extraction failed: {str(e)}")
        
        # Step 2: Fallback to regex if AI fails
        if not result.success:
            try:
                result = self._regex_fallback(raw_text, result)
                result.extraction_method = "regex_fallback"
                result.confidence = 0.6 if result.success else 0.0
            except Exception as e:
                logger.error(f"Regex fallback error: {e}", exc_info=True)
                result.errors.append(f"Regex fallback failed: {str(e)}")
        
        return result
    
    async def _run_ai_extraction(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Run AI extraction using LLM provider."""
        try:
            # Truncate text if too long
            max_chars = 15000
            text_for_ai = raw_text[:max_chars] if len(raw_text) > max_chars else raw_text
            
            prompt = PRICE_EXTRACTION_PROMPT.format(document_text=text_for_ai)
            
            response = await self.llm_provider.generate(
                prompt=prompt,
                system_prompt=PRICE_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000,
            )
            
            if response:
                return self._parse_json_response(response)
                
        except Exception as e:
            logger.error(f"LLM extraction error: {e}", exc_info=True)
            
        return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        import json
        
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _parse_ai_result(
        self,
        ai_result: Dict[str, Any],
        result: PriceExtractionResult,
    ) -> PriceExtractionResult:
        """Parse AI extraction result into structured format."""
        
        # Document info
        doc_info = ai_result.get("document_info", {})
        result.document_type = doc_info.get("document_type")
        result.document_number = doc_info.get("document_number")
        result.document_date = doc_info.get("document_date")
        result.seller_name = doc_info.get("seller_name")
        result.buyer_name = doc_info.get("buyer_name")
        result.origin_country = doc_info.get("origin_country")
        result.destination_country = doc_info.get("destination_country")
        
        # Line items
        line_items = ai_result.get("line_items", [])
        for item_data in line_items:
            if not item_data:
                continue
                
            item = ExtractedLineItem(
                commodity_name=item_data.get("commodity_name"),
                commodity_code=item_data.get("commodity_code"),
                quantity=self._safe_float(item_data.get("quantity")),
                unit=item_data.get("unit"),
                unit_price=self._safe_float(item_data.get("unit_price")),
                total_price=self._safe_float(item_data.get("total_price")),
                currency=item_data.get("currency", "USD"),
                confidence=0.85,
            )
            
            # Only add if we have meaningful data
            if item.commodity_name or item.unit_price:
                result.line_items.append(item)
        
        # Totals
        totals = ai_result.get("totals", {})
        result.total_amount = self._safe_float(totals.get("total_amount"))
        result.currency = totals.get("currency", "USD")
        
        return result
    
    def _regex_fallback(
        self,
        raw_text: str,
        result: PriceExtractionResult,
    ) -> PriceExtractionResult:
        """Fallback regex extraction for basic price data."""
        
        # Common patterns
        amount_pattern = r'(?:USD|EUR|GBP|\$|€|£)\s*([\d,]+\.?\d*)'
        quantity_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(kg|mt|pcs|pieces|units|tons?|bbl|barrels?)'
        unit_price_pattern = r'(?:unit price|price per|@)\s*(?:USD|EUR|\$)?\s*([\d,]+\.?\d*)'
        
        # Try to extract amounts
        amounts = re.findall(amount_pattern, raw_text, re.IGNORECASE)
        quantities = re.findall(quantity_pattern, raw_text, re.IGNORECASE)
        unit_prices = re.findall(unit_price_pattern, raw_text, re.IGNORECASE)
        
        # Build line item from regex matches
        if unit_prices:
            for i, price_str in enumerate(unit_prices[:5]):  # Max 5 items
                try:
                    unit_price = float(price_str.replace(",", ""))
                    quantity = None
                    unit = None
                    
                    if i < len(quantities):
                        quantity = float(quantities[i][0].replace(",", ""))
                        unit = quantities[i][1].lower()
                    
                    item = ExtractedLineItem(
                        commodity_name="Unknown Commodity",
                        unit_price=unit_price,
                        quantity=quantity,
                        unit=unit,
                        currency="USD",
                        confidence=0.5,
                    )
                    result.line_items.append(item)
                    
                except ValueError:
                    continue
        
        # Try to get total
        if amounts:
            try:
                # Take the largest amount as likely total
                max_amount = max(float(a.replace(",", "")) for a in amounts)
                result.total_amount = max_amount
            except ValueError:
                pass
        
        result.success = len(result.line_items) > 0
        return result
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.replace(",", "").strip()
            return float(value)
        except (ValueError, TypeError):
            return None


# Singleton instance
_service_instance: Optional[PriceExtractionService] = None


def get_price_extraction_service() -> PriceExtractionService:
    """Get or create the price extraction service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = PriceExtractionService()
    return _service_instance

