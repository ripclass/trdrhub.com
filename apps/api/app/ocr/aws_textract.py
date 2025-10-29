"""
AWS Textract OCR adapter implementation.
"""

import os
import time
from typing import Dict, List, Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from .base import OCRAdapter, OCRResult, OCRTextElement, BoundingBox


class AWSTextractAdapter(OCRAdapter):
    """AWS Textract OCR adapter."""
    
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.textract_client = boto3.client('textract', region_name=self.region)
        self.s3_client = boto3.client('s3', region_name=self.region)
    
    @property
    def provider_name(self) -> str:
        return "aws_textract"
    
    async def process_document(
        self, 
        s3_bucket: str, 
        s3_key: str,
        document_id: UUID
    ) -> OCRResult:
        """Process document using AWS Textract."""
        start_time = time.time()
        
        try:
            # Use detect_document_text for simple text extraction
            # For production, you might want to use start_document_text_detection
            # for async processing of larger documents
            response = self.textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                }
            )
            
            # Extract text and build elements
            full_text = ""
            elements = []
            confidence_sum = 0.0
            confidence_count = 0
            
            # Process blocks from Textract response
            for block in response.get('Blocks', []):
                if block['BlockType'] in ['LINE', 'WORD']:
                    text = block.get('Text', '')
                    confidence = block.get('Confidence', 0.0) / 100.0  # Convert to 0-1 scale
                    
                    if text and confidence > 0:
                        confidence_sum += confidence
                        confidence_count += 1
                        
                        # Extract bounding box
                        bbox = None
                        if 'Geometry' in block and 'BoundingBox' in block['Geometry']:
                            bbox_data = block['Geometry']['BoundingBox']
                            page = block.get('Page', 1)
                            
                            bbox = BoundingBox(
                                x1=bbox_data['Left'],
                                y1=bbox_data['Top'],
                                x2=bbox_data['Left'] + bbox_data['Width'],
                                y2=bbox_data['Top'] + bbox_data['Height'],
                                page=page
                            )
                        
                        elements.append(OCRTextElement(
                            text=text,
                            confidence=confidence,
                            bounding_box=bbox,
                            element_type=block['BlockType'].lower()
                        ))
                        
                        # Add to full text (only for lines to avoid duplication)
                        if block['BlockType'] == 'LINE':
                            full_text += text + "\n"
            
            # Calculate overall confidence
            overall_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Get document metadata
            metadata = {
                "block_count": len(response.get('Blocks', [])),
                "document_metadata": response.get('DocumentMetadata', {}),
                "job_status": "SUCCEEDED"
            }
            
            return OCRResult(
                document_id=document_id,
                full_text=full_text.strip(),
                overall_confidence=overall_confidence,
                elements=elements,
                metadata=metadata,
                processing_time_ms=processing_time,
                provider=self.provider_name
            )
            
        except ClientError as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            return OCRResult(
                document_id=document_id,
                full_text="",
                overall_confidence=0.0,
                elements=[],
                metadata={"error_code": error_code},
                processing_time_ms=processing_time,
                provider=self.provider_name,
                error=f"AWS Textract error: {str(e)}"
            )
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return OCRResult(
                document_id=document_id,
                full_text="",
                overall_confidence=0.0,
                elements=[],
                metadata={"error_type": type(e).__name__},
                processing_time_ms=processing_time,
                provider=self.provider_name,
                error=str(e)
            )
    
    async def health_check(self) -> bool:
        """Check AWS Textract service health."""
        try:
            # Test service availability by checking describe_document_text_detection
            # This doesn't use any resources but validates credentials and service access
            self.textract_client.list_adapters()
            return True
        except Exception:
            return False