"""
Stub OCR adapter for testing and development without real OCR services.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional
from uuid import UUID
from pathlib import Path

try:
    from google.cloud.exceptions import GoogleCloudError
except ImportError:
    class GoogleCloudError(Exception):
        pass

try:
    from botocore.exceptions import ClientError
except ImportError:
    class ClientError(Exception):
        pass

from ..ocr.base import OCRAdapter, OCRResult, OCRTextElement, BoundingBox
from ..config import settings
from .models import StubScenarioModel, StubDocumentData

logger = logging.getLogger(__name__)


class StubOCRAdapter(OCRAdapter):
    """
    Stub OCR adapter that returns realistic test data.
    
    This adapter simulates OCR processing by loading predefined scenarios
    from JSON files. It can simulate both successful processing and various
    error conditions for comprehensive testing.
    """
    
    def __init__(self):
        self.scenario_cache: Dict[str, StubScenarioModel] = {}
        self._load_scenario_cache()
    
    @property
    def provider_name(self) -> str:
        return "stub_ocr"
    
    def _load_scenario_cache(self):
        """Load and cache all available scenarios."""
        stub_dir = Path(settings.STUB_DATA_DIR)
        if not stub_dir.exists():
            logger.warning(f"Stub data directory {stub_dir} does not exist")
            return
        
        for scenario_file in stub_dir.glob("*.json"):
            try:
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                scenario = StubScenarioModel.parse_obj(data)
                self.scenario_cache[scenario_file.name] = scenario
                logger.info(f"Loaded stub scenario: {scenario_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to load scenario {scenario_file}: {e}")
    
    def _get_scenario(self, scenario_name: str) -> Optional[StubScenarioModel]:
        """Get scenario by name, with fallback to default."""
        if scenario_name in self.scenario_cache:
            return self.scenario_cache[scenario_name]
        
        # Fallback to lc_happy.json if requested scenario not found
        fallback = "lc_happy.json"
        if fallback in self.scenario_cache:
            logger.warning(f"Scenario {scenario_name} not found, using {fallback}")
            return self.scenario_cache[fallback]
        
        logger.error(f"No scenarios available, including fallback {fallback}")
        return None
    
    def _determine_document_type(self, s3_key: str) -> str:
        """Determine document type from S3 key path."""
        # Expected format: uploads/{session_id}/{document_type}/{file_id}
        parts = s3_key.split('/')
        if len(parts) >= 3:
            return parts[2]  # document_type part
        
        # Fallback based on filename patterns
        filename = parts[-1].lower()
        if 'lc' in filename or 'letter' in filename or 'credit' in filename:
            return 'letter_of_credit'
        elif 'invoice' in filename or 'inv' in filename:
            return 'commercial_invoice'
        elif 'bill' in filename or 'lading' in filename or 'bl' in filename:
            return 'bill_of_lading'
        
        # Default fallback
        return 'letter_of_credit'
    
    async def process_document(
        self, 
        s3_bucket: str, 
        s3_key: str,
        document_id: UUID
    ) -> OCRResult:
        """Process document using stub data."""
        start_time = time.time()
        
        # Check for error simulation
        if settings.STUB_FAIL_OCR:
            processing_time = int((time.time() - start_time) * 1000)
            # Simulate different types of OCR failures
            import random
            error_type = random.choice(['google_api_error', 'textract_timeout', 'processing_error'])
            
            if error_type == 'google_api_error':
                raise GoogleCloudError("Document processing failed: Invalid document format")
            elif error_type == 'textract_timeout':
                raise Exception("Textract processing timeout after 30 seconds")
            else:
                raise Exception("OCR processing failed: Unable to extract text")
        
        # Get current scenario
        scenario = self._get_scenario(settings.STUB_SCENARIO)
        if not scenario:
            # Emergency fallback with minimal data
            return self._create_emergency_fallback_result(document_id, start_time)
        
        # Determine document type
        document_type = self._determine_document_type(s3_key)
        
        # Get document data from scenario
        doc_data = scenario.get_document_data(document_type)
        if not doc_data:
            logger.warning(f"No stub data for document type {document_type} in scenario {settings.STUB_SCENARIO}")
            return self._create_empty_result(document_id, start_time, document_type)
        
        # Build OCR elements from stub data
        elements = []
        for field in doc_data.extracted_fields:
            if field.value:
                # Create realistic bounding box
                bbox = BoundingBox(
                    x1=0.1 + hash(field.field_name) % 100 / 1000,  # Pseudo-random but consistent
                    y1=0.1 + hash(field.value or '') % 100 / 1000,
                    x2=0.5 + hash(field.field_name) % 50 / 1000,
                    y2=0.2 + hash(field.value or '') % 50 / 1000,
                    page=1
                )
                
                elements.append(OCRTextElement(
                    text=field.value,
                    confidence=field.confidence,
                    bounding_box=bbox,
                    element_type="field"
                ))
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Add realistic processing delay
        if processing_time < doc_data.processing_time_ms:
            await self._simulate_processing_delay(doc_data.processing_time_ms - processing_time)
            processing_time = doc_data.processing_time_ms
        
        return OCRResult(
            document_id=document_id,
            full_text=doc_data.full_text or self._generate_full_text(doc_data.extracted_fields),
            overall_confidence=doc_data.ocr_confidence,
            elements=elements,
            metadata={
                "stub_scenario": settings.STUB_SCENARIO,
                "document_type": document_type,
                "processing_mode": "stub",
                "fields_extracted": len(doc_data.extracted_fields)
            },
            processing_time_ms=processing_time,
            provider=self.provider_name
        )
    
    async def _simulate_processing_delay(self, delay_ms: int):
        """Simulate realistic processing delay."""
        if delay_ms > 0:
            import asyncio
            await asyncio.sleep(delay_ms / 1000.0)
    
    def _generate_full_text(self, fields: List) -> str:
        """Generate full text from extracted fields."""
        lines = []
        for field in fields:
            if field.value:
                lines.append(f"{field.field_name.replace('_', ' ').title()}: {field.value}")
        return "\n".join(lines)
    
    def _create_emergency_fallback_result(self, document_id: UUID, start_time: float) -> OCRResult:
        """Create minimal fallback result when no scenarios are available."""
        processing_time = int((time.time() - start_time) * 1000)
        
        return OCRResult(
            document_id=document_id,
            full_text="EMERGENCY FALLBACK: No stub scenarios available",
            overall_confidence=0.1,
            elements=[],
            metadata={
                "error": "No stub scenarios loaded",
                "processing_mode": "emergency_fallback"
            },
            processing_time_ms=processing_time,
            provider=self.provider_name
        )
    
    def _create_empty_result(self, document_id: UUID, start_time: float, document_type: str) -> OCRResult:
        """Create empty result when document type not found in scenario."""
        processing_time = int((time.time() - start_time) * 1000)
        
        return OCRResult(
            document_id=document_id,
            full_text=f"No stub data available for document type: {document_type}",
            overall_confidence=0.0,
            elements=[],
            metadata={
                "document_type": document_type,
                "processing_mode": "stub_empty",
                "scenario": settings.STUB_SCENARIO
            },
            processing_time_ms=processing_time,
            provider=self.provider_name
        )
    
    async def health_check(self) -> bool:
        """Stub OCR is always healthy unless explicitly configured to fail."""
        # Check if we have any scenarios loaded
        if not self.scenario_cache:
            logger.warning("No stub scenarios loaded for OCR")
            return False
        
        # Check if current scenario exists
        current_scenario = self._get_scenario(settings.STUB_SCENARIO)
        return current_scenario is not None
    
    def get_available_scenarios(self) -> List[str]:
        """Get list of available scenario names."""
        return list(self.scenario_cache.keys())
    
    def get_scenario_info(self, scenario_name: str) -> Optional[Dict]:
        """Get information about a specific scenario."""
        scenario = self._get_scenario(scenario_name)
        if not scenario:
            return None
        
        return {
            "name": scenario.scenario_name,
            "description": scenario.description,
            "documents": [doc.document_type for doc in scenario.documents],
            "expected_discrepancies": scenario.expected_discrepancies,
            "tags": scenario.tags
        }