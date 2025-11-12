"""
DeepSeek OCR adapter implementation using Hugging Face transformers.
"""

import os
import time
import io
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from uuid import UUID

try:
    import torch
    from transformers import pipeline
    from PIL import Image
    import boto3
except ImportError:
    torch = None
    pipeline = None
    Image = None

# For type hints when Image might not be available
if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
else:
    PILImage = Any

from .base import OCRAdapter, OCRResult, OCRTextElement, BoundingBox


class DeepSeekOCRAdapter(OCRAdapter):
    """DeepSeek OCR adapter using Hugging Face transformers."""
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize DeepSeek OCR adapter.
        
        Args:
            model_name: Hugging Face model identifier (default: deepseek-ai/deepseek-ocr)
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        if torch is None or pipeline is None or Image is None:
            raise ImportError(
                "DeepSeek OCR dependencies not installed. "
                "Install with: pip install torch transformers pillow"
            )
        
        self.model_name = model_name or os.getenv(
            "DEEPSEEK_OCR_MODEL_NAME", 
            "deepseek-ai/deepseek-ocr"
        )
        
        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Lazy loading - pipeline will be loaded on first use
        self._ocr_pipeline = None
        self._model_loaded = False
    
    def _load_model(self):
        """Lazy load the OCR pipeline."""
        if self._model_loaded:
            return
        
        try:
            print(f"Loading DeepSeek OCR model: {self.model_name} on {self.device}")
            
            # Use transformers pipeline for OCR
            # Note: Adjust task type based on actual DeepSeek OCR model capabilities
            # Common tasks: "image-to-text", "ocr", "document-question-answering"
            self._ocr_pipeline = pipeline(
                "image-to-text",  # or "ocr" if available
                model=self.model_name,
                device=0 if self.device == "cuda" else -1,  # 0 for GPU, -1 for CPU
                trust_remote_code=True
            )
            
            self._model_loaded = True
            print(f"✓ DeepSeek OCR model loaded successfully on {self.device}")
            
        except Exception as e:
            # Fallback: try alternative pipeline task types
            try:
                print(f"Trying alternative OCR pipeline configuration...")
                self._ocr_pipeline = pipeline(
                    "ocr",
                    model=self.model_name,
                    device=0 if self.device == "cuda" else -1,
                    trust_remote_code=True
                )
                self._model_loaded = True
                print(f"✓ DeepSeek OCR model loaded with OCR pipeline")
            except Exception as e2:
                raise RuntimeError(
                    f"Failed to load DeepSeek OCR model: {e}. "
                    f"Alternative pipeline also failed: {e2}. "
                    f"Please verify the model name and that it supports OCR tasks."
                )
    
    @property
    def provider_name(self) -> str:
        return "deepseek_ocr"
    
    def _download_from_s3(self, s3_bucket: str, s3_key: str) -> bytes:
        """Download document from S3."""
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        return response['Body'].read()
    
    def _convert_pdf_to_image(self, pdf_content: bytes) -> List[Any]:
        """
        Convert PDF to images for OCR processing.
        
        Note: This requires pdf2image library. Install with:
        pip install pdf2image
        And install poppler: https://github.com/oschwartz10612/poppler-windows/releases
        """
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_content)
            return images
        except ImportError:
            raise ImportError(
                "pdf2image not installed. Install with: pip install pdf2image"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF to images: {e}")
    
    def _process_image(self, image: Any) -> Dict[str, Any]:
        """
        Process a single image through DeepSeek OCR.
        
        Returns:
            Dictionary with 'text' and 'confidence' keys
        """
        if not self._model_loaded:
            self._load_model()
        
        try:
            # Prepare image for the model
            # Convert PIL Image to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Process image through OCR pipeline
            result = self._ocr_pipeline(image)
            
            # Extract text from pipeline result
            # Pipeline output format varies, handle common cases
            if isinstance(result, list):
                # Multiple results (e.g., multiple text regions)
                text_parts = []
                for item in result:
                    if isinstance(item, dict):
                        text_parts.append(item.get('generated_text', item.get('text', '')))
                    elif isinstance(item, str):
                        text_parts.append(item)
                text = '\n'.join(text_parts)
            elif isinstance(result, dict):
                # Single result dictionary
                text = result.get('generated_text', result.get('text', ''))
            else:
                # String result
                text = str(result)
            
            # Extract confidence if available
            confidence = 0.95  # Default confidence
            if isinstance(result, dict) and 'score' in result:
                confidence = float(result['score'])
            elif isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and 'score' in result[0]:
                    # Average confidence across multiple results
                    scores = [float(r.get('score', 0.95)) for r in result if isinstance(r, dict)]
                    confidence = sum(scores) / len(scores) if scores else 0.95
            
            return {
                "text": text.strip(),
                "confidence": confidence
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to process image with DeepSeek OCR: {e}")
    
    async def process_document(
        self, 
        s3_bucket: str, 
        s3_key: str,
        document_id: UUID
    ) -> OCRResult:
        """Process document using DeepSeek OCR."""
        start_time = time.time()
        
        try:
            # Download document from S3
            document_content = self._download_from_s3(s3_bucket, s3_key)
            
            # Determine file type
            file_ext = s3_key.lower().split('.')[-1]
            is_pdf = file_ext == 'pdf'
            is_image = file_ext in ['jpg', 'jpeg', 'png', 'tiff', 'tif']
            
            if not (is_pdf or is_image):
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Process document
            full_text_parts = []
            elements = []
            confidence_sum = 0.0
            confidence_count = 0
            
            if is_pdf:
                # Convert PDF to images
                images = self._convert_pdf_to_image(document_content)
                
                # Process each page
                for page_idx, image in enumerate(images):
                    result = self._process_image(image)
                    
                    page_text = result["text"]
                    page_confidence = result["confidence"]
                    
                    full_text_parts.append(page_text)
                    
                    if page_confidence > 0:
                        confidence_sum += page_confidence
                        confidence_count += 1
                    
                    # Create text element for the page
                    elements.append(OCRTextElement(
                        text=page_text,
                        confidence=page_confidence,
                        bounding_box=None,  # DeepSeek OCR may not provide bounding boxes
                        element_type="page"
                    ))
            else:
                # Process single image
                image = Image.open(io.BytesIO(document_content))
                result = self._process_image(image)
                
                full_text_parts.append(result["text"])
                confidence_sum += result["confidence"]
                confidence_count += 1
                
                elements.append(OCRTextElement(
                    text=result["text"],
                    confidence=result["confidence"],
                    bounding_box=None,
                    element_type="image"
                ))
            
            # Combine all text
            full_text = "\n\n".join(full_text_parts)
            
            # Calculate overall confidence
            overall_confidence = (
                confidence_sum / confidence_count 
                if confidence_count > 0 
                else 0.0
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return OCRResult(
                document_id=document_id,
                full_text=full_text,
                overall_confidence=overall_confidence,
                elements=elements,
                metadata={
                    "page_count": len(elements),
                    "file_type": file_ext,
                    "model": self.model_name,
                    "device": self.device
                },
                processing_time_ms=processing_time,
                provider=self.provider_name
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
        """Check if DeepSeek OCR is available."""
        try:
            # Try to load model if not already loaded
            if not self._model_loaded:
                self._load_model()
            return self._model_loaded
        except Exception:
            return False

