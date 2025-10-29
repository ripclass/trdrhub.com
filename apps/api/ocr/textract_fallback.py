#!/usr/bin/env python3
"""
AWS Textract Fallback OCR System
Provides resilient document processing when primary OCR fails.
"""

import boto3
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import yaml
import os

@dataclass
class TextractResult:
    """Result from Textract processing"""
    text: str
    confidence: float
    tables: List[Dict[str, Any]]
    forms: List[Dict[str, Any]]
    pages: int
    cost_estimate: float
    processing_time: float
    job_id: str

@dataclass
class TextractConfig:
    """Textract configuration parameters"""
    aws_region: str
    max_pages_per_day: int
    max_pages_per_document: int
    timeout_seconds: int
    retry_attempts: int
    features: List[str]

class TextractFallbackError(Exception):
    """Custom exception for Textract fallback errors"""
    pass

class CostGuardrailError(Exception):
    """Raised when cost guardrails are exceeded"""
    pass

class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""
    pass

class TextractFallback:
    """
    AWS Textract fallback OCR processor.
    Handles document processing when primary OCR fails.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Textract fallback processor"""
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.textract_client = self._initialize_client()
        # Initialize S3 with same session credentials
        if not os.environ.get('AWS_ACCESS_KEY_ID') or not os.environ.get('AWS_SECRET_ACCESS_KEY'):
            raise ConfigError("AWS credentials not found in environment variables")

        session = boto3.Session(
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', self.config.aws_region)
        )
        self.s3_client = session.client('s3')
        self.usage_tracker = TextractUsageTracker()

    def _load_config(self, config_path: Optional[str] = None) -> TextractConfig:
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "trust_config.yaml"

        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            textract_config = config_data['ocr']['textract_fallback']
            return TextractConfig(
                aws_region=textract_config.get('aws_region', 'us-east-1'),
                max_pages_per_day=textract_config.get('max_pages_per_day', 1000),
                max_pages_per_document=textract_config.get('max_pages_per_document', 50),
                timeout_seconds=textract_config.get('timeout_seconds', 30),
                retry_attempts=textract_config.get('retry_attempts', 3),
                features=textract_config.get('features', ['TABLES', 'FORMS'])
            )
        except Exception as e:
            self.logger.warning(f"Could not load config from {config_path}: {e}")
            # Return default configuration
            return TextractConfig(
                aws_region='us-east-1',
                max_pages_per_day=1000,
                max_pages_per_document=50,
                timeout_seconds=30,
                retry_attempts=3,
                features=['TABLES', 'FORMS']
            )

    def _initialize_client(self) -> boto3.client:
        """Initialize AWS Textract client with explicit credentials"""
        try:
            # Validate AWS credentials are available
            if not os.environ.get('AWS_ACCESS_KEY_ID') or not os.environ.get('AWS_SECRET_ACCESS_KEY'):
                raise ConfigError("AWS credentials not found in environment variables. "
                                "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

            # Create session with explicit credentials
            session = boto3.Session(
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('AWS_REGION', self.config.aws_region)
            )
            return session.client('textract')
        except ConfigError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Textract client: {e}")
            raise TextractFallbackError(f"AWS Textract client initialization failed: {e}")

    def process_document(self, document_path: str, job_id: Optional[str] = None) -> TextractResult:
        """
        Process document using AWS Textract fallback

        Args:
            document_path: Path to document file
            job_id: Optional job ID for tracking

        Returns:
            TextractResult with extracted content
        """
        start_time = time.time()
        job_id = job_id or str(uuid.uuid4())

        self.logger.info(f"Starting Textract fallback processing for job {job_id}")

        try:
            # Pre-processing checks
            self._validate_document(document_path)
            self._check_cost_guardrails()

            # Process document
            if self._is_large_document(document_path):
                result = self._process_async(document_path, job_id)
            else:
                result = self._process_sync(document_path, job_id)

            # Track usage
            self.usage_tracker.record_usage(result.pages, result.cost_estimate)

            processing_time = time.time() - start_time
            result.processing_time = processing_time

            self.logger.info(f"Textract fallback completed for job {job_id} in {processing_time:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Textract fallback failed for job {job_id}: {str(e)}")
            self._log_structured_error(job_id, str(e))
            raise TextractFallbackError(f"Document processing failed: {e}")

    def _validate_document(self, document_path: str) -> None:
        """Validate document before processing"""
        if not Path(document_path).exists():
            raise TextractFallbackError(f"Document not found: {document_path}")

        # Check file size (Textract limit is 512MB)
        file_size = Path(document_path).stat().st_size
        if file_size > 512 * 1024 * 1024:  # 512MB
            raise TextractFallbackError(f"Document too large: {file_size / (1024*1024):.1f}MB (max 512MB)")

        # Check supported format
        supported_formats = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        file_ext = Path(document_path).suffix.lower()
        if file_ext not in supported_formats:
            raise TextractFallbackError(f"Unsupported format: {file_ext}")

    def _check_cost_guardrails(self) -> None:
        """Check if cost guardrails allow processing"""
        daily_usage = self.usage_tracker.get_daily_usage()

        if daily_usage['pages'] >= self.config.max_pages_per_day:
            raise CostGuardrailError(
                f"Daily page limit exceeded: {daily_usage['pages']}/{self.config.max_pages_per_day}"
            )

        if daily_usage['cost'] >= 100.0:  # $100 daily limit
            raise CostGuardrailError(
                f"Daily cost limit exceeded: ${daily_usage['cost']:.2f}"
            )

    def _is_large_document(self, document_path: str) -> bool:
        """Determine if document requires async processing"""
        # Simple heuristic: files > 50MB or PDFs with likely many pages
        file_size = Path(document_path).stat().st_size

        if file_size > 50 * 1024 * 1024:  # 50MB
            return True

        # For PDFs, estimate pages based on file size
        if document_path.lower().endswith('.pdf'):
            estimated_pages = file_size / (100 * 1024)  # Rough estimate: 100KB per page
            return estimated_pages > 20

        return False

    def _process_sync(self, document_path: str, job_id: str) -> TextractResult:
        """Process document synchronously"""
        self.logger.info(f"Processing {document_path} synchronously for job {job_id}")

        with open(document_path, 'rb') as document_file:
            document_bytes = document_file.read()

        try:
            # Analyze document
            response = self.textract_client.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=self.config.features
            )

            return self._parse_textract_response(response, job_id)

        except Exception as e:
            self.logger.error(f"Synchronous Textract processing failed: {e}")
            raise TextractFallbackError(f"Sync processing failed: {e}")

    def _process_async(self, document_path: str, job_id: str) -> TextractResult:
        """Process document asynchronously (for large documents)"""
        self.logger.info(f"Processing {document_path} asynchronously for job {job_id}")

        # Upload to S3 first
        bucket_name = f"lcopilot-textract-{self.config.aws_region}"
        s3_key = f"documents/{job_id}/{Path(document_path).name}"

        try:
            self.s3_client.upload_file(document_path, bucket_name, s3_key)

            # Start async analysis
            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': s3_key
                    }
                },
                FeatureTypes=self.config.features,
                JobTag=job_id
            )

            textract_job_id = response['JobId']
            self.logger.info(f"Started async Textract job {textract_job_id} for {job_id}")

            # Poll for completion
            return self._wait_for_async_job(textract_job_id, job_id)

        except Exception as e:
            self.logger.error(f"Async Textract processing failed: {e}")
            raise TextractFallbackError(f"Async processing failed: {e}")

    def _wait_for_async_job(self, textract_job_id: str, job_id: str) -> TextractResult:
        """Wait for async Textract job to complete"""
        timeout = time.time() + self.config.timeout_seconds
        poll_interval = 2  # seconds

        while time.time() < timeout:
            try:
                response = self.textract_client.get_document_analysis(JobId=textract_job_id)
                status = response['JobStatus']

                if status == 'SUCCEEDED':
                    self.logger.info(f"Async Textract job {textract_job_id} completed successfully")
                    return self._parse_textract_response(response, job_id)
                elif status == 'FAILED':
                    error_msg = response.get('StatusMessage', 'Unknown error')
                    raise TextractFallbackError(f"Async job failed: {error_msg}")
                elif status == 'IN_PROGRESS':
                    self.logger.debug(f"Textract job {textract_job_id} still in progress...")
                    time.sleep(poll_interval)
                else:
                    self.logger.warning(f"Unexpected status: {status}")
                    time.sleep(poll_interval)

            except Exception as e:
                self.logger.error(f"Error checking async job status: {e}")
                time.sleep(poll_interval)

        raise TextractFallbackError(f"Async job timeout after {self.config.timeout_seconds}s")

    def _parse_textract_response(self, response: Dict[str, Any], job_id: str) -> TextractResult:
        """Parse Textract API response into standardized format"""
        blocks = response.get('Blocks', [])

        # Extract text
        text_blocks = [block for block in blocks if block['BlockType'] == 'LINE']
        extracted_text = '\n'.join([block['Text'] for block in text_blocks if 'Text' in block])

        # Calculate average confidence
        confidences = [block.get('Confidence', 0) for block in blocks if 'Confidence' in block]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Extract tables
        tables = self._extract_tables(blocks)

        # Extract forms
        forms = self._extract_forms(blocks)

        # Estimate pages
        pages = len([block for block in blocks if block['BlockType'] == 'PAGE'])

        # Estimate cost (AWS Textract pricing: ~$0.0015 per page)
        cost_estimate = pages * 0.0015

        return TextractResult(
            text=extracted_text,
            confidence=avg_confidence,
            tables=tables,
            forms=forms,
            pages=pages,
            cost_estimate=cost_estimate,
            processing_time=0.0,  # Will be set by caller
            job_id=job_id
        )

    def _extract_tables(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract table data from Textract blocks"""
        tables = []
        table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']

        for table_block in table_blocks:
            table = {
                'id': table_block['Id'],
                'confidence': table_block.get('Confidence', 0),
                'rows': [],
                'bbox': table_block.get('Geometry', {}).get('BoundingBox', {})
            }

            # Extract table cells (simplified implementation)
            cell_blocks = [block for block in blocks
                          if block['BlockType'] == 'CELL' and
                          self._is_child_of_table(block, table_block)]

            # Group cells by row
            rows = {}
            for cell in cell_blocks:
                row_index = cell.get('RowIndex', 0)
                col_index = cell.get('ColumnIndex', 0)

                if row_index not in rows:
                    rows[row_index] = {}

                rows[row_index][col_index] = {
                    'text': self._get_cell_text(cell, blocks),
                    'confidence': cell.get('Confidence', 0)
                }

            table['rows'] = [rows.get(i, {}) for i in sorted(rows.keys())]
            tables.append(table)

        return tables

    def _extract_forms(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract form data from Textract blocks"""
        forms = []
        key_value_blocks = [block for block in blocks if block['BlockType'] == 'KEY_VALUE_SET']

        key_blocks = [block for block in key_value_blocks
                     if block.get('EntityTypes', []) == ['KEY']]

        for key_block in key_blocks:
            form_field = {
                'key': self._get_block_text(key_block, blocks),
                'value': '',
                'confidence': key_block.get('Confidence', 0)
            }

            # Find corresponding value block
            relationships = key_block.get('Relationships', [])
            for relationship in relationships:
                if relationship['Type'] == 'VALUE':
                    value_ids = relationship.get('Ids', [])
                    for value_id in value_ids:
                        value_block = next((b for b in blocks if b['Id'] == value_id), None)
                        if value_block:
                            form_field['value'] = self._get_block_text(value_block, blocks)
                            break

            forms.append(form_field)

        return forms

    def _is_child_of_table(self, cell_block: Dict[str, Any], table_block: Dict[str, Any]) -> bool:
        """Check if cell belongs to table"""
        relationships = table_block.get('Relationships', [])
        for relationship in relationships:
            if relationship['Type'] == 'CHILD' and cell_block['Id'] in relationship.get('Ids', []):
                return True
        return False

    def _get_cell_text(self, cell_block: Dict[str, Any], all_blocks: List[Dict[str, Any]]) -> str:
        """Get text content of a table cell"""
        return self._get_block_text(cell_block, all_blocks)

    def _get_block_text(self, block: Dict[str, Any], all_blocks: List[Dict[str, Any]]) -> str:
        """Get text content of a block by following relationships"""
        if 'Text' in block:
            return block['Text']

        text_parts = []
        relationships = block.get('Relationships', [])

        for relationship in relationships:
            if relationship['Type'] == 'CHILD':
                child_ids = relationship.get('Ids', [])
                for child_id in child_ids:
                    child_block = next((b for b in all_blocks if b['Id'] == child_id), None)
                    if child_block and 'Text' in child_block:
                        text_parts.append(child_block['Text'])

        return ' '.join(text_parts)

    def _log_structured_error(self, job_id: str, error_message: str) -> None:
        """Log structured error for monitoring"""
        structured_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'job_id': job_id,
            'service': 'textract_fallback',
            'error_type': 'processing_failure',
            'error_message': error_message,
            'aws_region': self.config.aws_region
        }

        self.logger.error(json.dumps(structured_log))

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return {
            'daily_usage': self.usage_tracker.get_daily_usage(),
            'monthly_usage': self.usage_tracker.get_monthly_usage(),
            'cost_limits': {
                'daily_page_limit': self.config.max_pages_per_day,
                'document_page_limit': self.config.max_pages_per_document
            }
        }

class TextractUsageTracker:
    """Track Textract usage for cost management"""

    def __init__(self):
        self.usage_file = Path(__file__).parent / "textract_usage.json"

    def record_usage(self, pages: int, cost: float) -> None:
        """Record usage for cost tracking"""
        usage_data = self._load_usage_data()
        today = datetime.now().date().isoformat()

        if today not in usage_data:
            usage_data[today] = {'pages': 0, 'cost': 0.0}

        usage_data[today]['pages'] += pages
        usage_data[today]['cost'] += cost

        # Clean old data (keep only last 30 days)
        cutoff_date = (datetime.now() - timedelta(days=30)).date()
        usage_data = {date: data for date, data in usage_data.items()
                     if datetime.fromisoformat(date).date() >= cutoff_date}

        self._save_usage_data(usage_data)

    def get_daily_usage(self) -> Dict[str, Any]:
        """Get today's usage"""
        usage_data = self._load_usage_data()
        today = datetime.now().date().isoformat()
        return usage_data.get(today, {'pages': 0, 'cost': 0.0})

    def get_monthly_usage(self) -> Dict[str, Any]:
        """Get current month's usage"""
        usage_data = self._load_usage_data()
        current_month = datetime.now().strftime('%Y-%m')

        monthly_pages = 0
        monthly_cost = 0.0

        for date, data in usage_data.items():
            if date.startswith(current_month):
                monthly_pages += data['pages']
                monthly_cost += data['cost']

        return {'pages': monthly_pages, 'cost': monthly_cost}

    def _load_usage_data(self) -> Dict[str, Any]:
        """Load usage data from file"""
        if not self.usage_file.exists():
            return {}

        try:
            with open(self.usage_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_usage_data(self, data: Dict[str, Any]) -> None:
        """Save usage data to file"""
        try:
            self.usage_file.parent.mkdir(exist_ok=True)
            with open(self.usage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not save usage data: {e}")

def normalize_textract_output(textract_result: TextractResult) -> Dict[str, Any]:
    """
    Normalize Textract output to standard LC document format
    Compatible with existing validation pipeline
    """
    return {
        'extracted_text': textract_result.text,
        'confidence_score': textract_result.confidence / 100.0,  # Convert to 0-1 range
        'pages_processed': textract_result.pages,
        'tables': textract_result.tables,
        'forms': textract_result.forms,
        'metadata': {
            'processing_method': 'aws_textract',
            'job_id': textract_result.job_id,
            'processing_time': textract_result.processing_time,
            'cost_estimate': textract_result.cost_estimate
        }
    }

# Integration function for existing pipeline
def process_with_fallback(document_path: str, primary_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process document with Textract fallback if primary OCR fails

    Args:
        document_path: Path to document
        primary_result: Result from primary OCR (if available)

    Returns:
        Processed document data
    """
    logger = logging.getLogger(__name__)

    # Check if fallback is needed
    if primary_result and primary_result.get('confidence_score', 0) > 0.7:
        logger.info("Primary OCR succeeded, skipping fallback")
        return primary_result

    # Initialize Textract fallback
    try:
        textract = TextractFallback()
        result = textract.process_document(document_path)

        logger.info(f"Textract fallback successful: {result.pages} pages, {result.confidence:.1f}% confidence")
        return normalize_textract_output(result)

    except Exception as e:
        logger.error(f"Textract fallback failed: {e}")

        # Return primary result even if it's poor quality, rather than failing completely
        if primary_result:
            logger.warning("Returning low-quality primary OCR result due to fallback failure")
            return primary_result
        else:
            raise TextractFallbackError(f"Both primary OCR and Textract fallback failed: {e}")

def main():
    """Demo the Textract fallback system"""
    print("🔍 LCopilot AWS Textract Fallback Demo")
    print("=" * 50)

    # Initialize fallback processor
    try:
        textract = TextractFallback()
        stats = textract.get_usage_stats()

        print(f"📊 Usage Stats:")
        print(f"  • Daily: {stats['daily_usage']['pages']} pages, ${stats['daily_usage']['cost']:.2f}")
        print(f"  • Limits: {stats['cost_limits']['daily_page_limit']} pages/day")
        print(f"✅ Textract fallback initialized successfully")

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    print(f"\n💡 Ready to process documents with AWS Textract fallback")
    print(f"   Use process_with_fallback(document_path) in your code")

if __name__ == "__main__":
    main()