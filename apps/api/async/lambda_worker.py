#!/usr/bin/env python3
"""
LCopilot Trust Platform - Lambda Worker
Phase 4: Async Processing Pipeline

AWS Lambda function for processing documents asynchronously.
Integrates with SQS, OCR fallback, and job status tracking.
"""

import json
import os
import time
import boto3
from typing import Dict, Any, Optional
import logging
import tempfile
from datetime import datetime

# Import local modules (these would be packaged with the Lambda)
from async.job_status import JobStatusManager, JobStatus
from async.rate_limiter import RateLimiter
from ocr.textract_fallback import TextractFallback
from trust_platform.compliance.validator import ComplianceValidator
from trust_platform.compliance.bank_profile_engine import BankProfileEngine

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda handler for processing document validation jobs

    Args:
        event: SQS event containing job messages
        context: Lambda context

    Returns:
        Processing results
    """
    processor = DocumentProcessor()

    try:
        return processor.process_sqs_event(event, context)
    except Exception as e:
        logger.error(f"Lambda handler failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

class DocumentProcessor:
    """Processes document validation jobs in Lambda environment"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Load configuration from environment variables
        config_bucket = os.environ.get('CONFIG_BUCKET', 'lcopilot-config')
        config_key = os.environ.get('CONFIG_KEY', 'trust_config.yaml')

        # Download config from S3 if in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            self.config = self._load_config_from_s3(config_bucket, config_key)
        else:
            self.config = self._load_local_config()

        # Initialize AWS clients
        self.s3 = boto3.client('s3')
        self.sqs = boto3.client('sqs')

        # Initialize components
        self.job_status = JobStatusManager()
        self.rate_limiter = RateLimiter()
        self.textract_fallback = TextractFallback()
        self.validator = ComplianceValidator()
        self.bank_engine = BankProfileEngine()

        # S3 configuration
        self.s3_bucket = self.config.get('storage', {}).get('s3_bucket', 'lcopilot-documents')

    def _load_config_from_s3(self, bucket: str, key: str) -> Dict[str, Any]:
        """Load configuration from S3"""
        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            config_content = response['Body'].read().decode('utf-8')

            import yaml
            return yaml.safe_load(config_content)

        except Exception as e:
            self.logger.error(f"Failed to load config from S3: {e}")
            return {}

    def _load_local_config(self) -> Dict[str, Any]:
        """Load local configuration file"""
        import yaml

        try:
            with open('trust_config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning("Config file not found, using defaults")
            return {}

    def process_sqs_event(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """Process SQS event with multiple messages"""

        results = []

        for record in event.get('Records', []):
            try:
                # Parse SQS message
                message_body = json.loads(record['body'])
                receipt_handle = record['receiptHandle']

                # Process the job
                result = self.process_job(message_body, context)
                result['receiptHandle'] = receipt_handle

                results.append(result)

            except Exception as e:
                self.logger.error(f"Failed to process SQS record: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'receiptHandle': record.get('receiptHandle')
                })

        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'results': results
            })
        }

    def process_job(self, job_data: Dict[str, Any], context) -> Dict[str, Any]:
        """
        Process a single document validation job

        Args:
            job_data: Job data from SQS message
            context: Lambda context

        Returns:
            Processing result
        """
        job_id = job_data.get('job_id')
        start_time = time.time()

        self.logger.info(f"Processing job {job_id}")

        try:
            # Update job status to processing
            self.job_status.update_job_status(job_id, {
                'status': JobStatus.PROCESSING.value,
                'message': 'Started processing document',
                'progress': 10,
                'lambda_request_id': context.aws_request_id,
                'processing_started_at': datetime.utcnow().isoformat()
            })

            # Download document from S3
            document_path = self._download_document(
                job_data['document_path'],
                job_id
            )

            # Update progress
            self.job_status.update_job_status(job_id, {
                'progress': 30,
                'message': 'Document downloaded, starting OCR processing'
            })

            # Extract document data
            extracted_data = self._extract_document_data(document_path, job_id)

            # Update progress
            self.job_status.update_job_status(job_id, {
                'progress': 60,
                'message': 'OCR completed, validating LC compliance'
            })

            # Validate LC compliance
            validation_result = self._validate_lc_compliance(
                job_data['lc_document'],
                extracted_data,
                job_data.get('bank_mode'),
                job_data.get('options', {})
            )

            # Calculate processing time
            processing_time = time.time() - start_time

            # Update job status to completed
            final_result = {
                'status': JobStatus.COMPLETED.value,
                'message': 'Document processing completed successfully',
                'progress': 100,
                'processing_time': processing_time,
                'completed_at': datetime.utcnow().isoformat(),
                'results': validation_result
            }

            self.job_status.update_job_status(job_id, final_result)

            # Remove from concurrent job tracking
            user_id = job_data.get('user_id')
            tier = job_data.get('tier')
            if user_id and tier:
                self.rate_limiter.remove_concurrent_job(user_id, job_id)

            # Clean up temporary files
            self._cleanup_temp_files(document_path)

            self.logger.info(f"Job {job_id} completed in {processing_time:.2f}s")

            return {
                'success': True,
                'job_id': job_id,
                'processing_time': processing_time,
                'compliance_score': validation_result.get('compliance_score', 0)
            }

        except Exception as e:
            self.logger.error(f"Job {job_id} failed: {e}")

            # Calculate processing time for failed job
            processing_time = time.time() - start_time

            # Update job status to failed
            self.job_status.update_job_status(job_id, {
                'status': JobStatus.FAILED.value,
                'message': f'Processing failed: {str(e)}',
                'error': str(e),
                'processing_time': processing_time,
                'failed_at': datetime.utcnow().isoformat()
            })

            # Remove from concurrent tracking
            user_id = job_data.get('user_id')
            if user_id:
                self.rate_limiter.remove_concurrent_job(user_id, job_id)

            return {
                'success': False,
                'job_id': job_id,
                'error': str(e),
                'processing_time': processing_time
            }

    def _download_document(self, s3_key: str, job_id: str) -> str:
        """Download document from S3 to local temp file"""

        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(s3_key)[1]
            )

            # Download from S3
            self.s3.download_fileobj(
                self.s3_bucket,
                s3_key,
                temp_file
            )

            temp_file.close()

            self.logger.info(f"Downloaded document for job {job_id} to {temp_file.name}")

            return temp_file.name

        except Exception as e:
            self.logger.error(f"Failed to download document for job {job_id}: {e}")
            raise

    def _extract_document_data(self, document_path: str, job_id: str) -> Dict[str, Any]:
        """Extract data from document using OCR"""

        try:
            # First try primary OCR (will fall back to Textract if needed)
            extracted_data = self._run_primary_ocr(document_path)

            # Check if we need Textract fallback
            if self._should_use_textract_fallback(extracted_data):
                self.logger.info(f"Using Textract fallback for job {job_id}")

                # Update progress
                self.job_status.update_job_status(job_id, {
                    'progress': 45,
                    'message': 'Using enhanced OCR processing for better accuracy'
                })

                # Use Textract fallback
                textract_result = self.textract_fallback.process_document(
                    document_path,
                    job_id
                )

                extracted_data = textract_result.extracted_text

                # Log Textract usage
                self.logger.info(f"Textract fallback completed for job {job_id}: "
                              f"{textract_result.pages} pages, "
                              f"${textract_result.cost_estimate:.4f} cost")

            return extracted_data

        except Exception as e:
            self.logger.error(f"OCR extraction failed for job {job_id}: {e}")
            raise

    def _run_primary_ocr(self, document_path: str) -> Dict[str, Any]:
        """Run primary OCR engine (pypdf/pdfplumber)"""

        # This would integrate with existing OCR pipeline
        # For now, return mock data to demonstrate flow
        return {
            'text': 'Mock extracted text from primary OCR',
            'confidence': 0.85,
            'pages': 1
        }

    def _should_use_textract_fallback(self, extracted_data: Dict[str, Any]) -> bool:
        """Determine if Textract fallback should be used"""

        # Use Textract if:
        # 1. Primary OCR confidence is low
        # 2. No text extracted
        # 3. Document appears to be image-based

        confidence = extracted_data.get('confidence', 1.0)
        text_length = len(extracted_data.get('text', ''))

        return (
            confidence < 0.8 or  # Low confidence
            text_length < 50 or  # Very little text extracted
            not extracted_data.get('text', '').strip()  # No meaningful text
        )

    def _validate_lc_compliance(
        self,
        lc_document: Dict[str, Any],
        extracted_data: Dict[str, Any],
        bank_mode: Optional[str],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate LC compliance using extracted document data"""

        try:
            # Merge LC document with extracted data
            combined_data = {
                **lc_document,
                'extracted_text': extracted_data.get('text', ''),
                'ocr_confidence': extracted_data.get('confidence', 0),
                'document_pages': extracted_data.get('pages', 1)
            }

            # Get bank profile if specified
            bank_profile = None
            if bank_mode:
                bank_profile = self.bank_engine.get_profile(bank_mode)

            # Run validation
            validation_result = self.validator.validate_lc(
                combined_data,
                bank_profile=bank_profile,
                **options
            )

            # Add processing metadata
            validation_result['processing_metadata'] = {
                'ocr_method': 'textract_fallback' if extracted_data.get('textract_used') else 'primary_ocr',
                'ocr_confidence': extracted_data.get('confidence'),
                'document_pages': extracted_data.get('pages'),
                'bank_profile': bank_profile.get('bank_name') if bank_profile else None,
                'processed_at': datetime.utcnow().isoformat(),
                'lambda_environment': True
            }

            return validation_result

        except Exception as e:
            self.logger.error(f"LC validation failed: {e}")
            raise

    def _cleanup_temp_files(self, *file_paths):
        """Clean up temporary files"""

        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}")

# For local testing
if __name__ == "__main__":
    # Mock SQS event for local testing
    mock_event = {
        'Records': [{
            'body': json.dumps({
                'job_id': 'test-job-123',
                'user_id': 'test-user',
                'tier': 'pro',
                'document_path': 'test-documents/sample-lc.pdf',
                'document_hash': 'abc123',
                'lc_document': {
                    'lc_number': 'TEST-LC-001',
                    'amount': {'value': 100000, 'currency': 'USD'},
                    'issue_date': '2024-01-15'
                },
                'bank_mode': 'BRAC_BANK',
                'options': {}
            }),
            'receiptHandle': 'mock-receipt-handle'
        }]
    }

    class MockContext:
        aws_request_id = 'mock-request-id'

    processor = DocumentProcessor()
    result = processor.process_sqs_event(mock_event, MockContext())
    print(json.dumps(result, indent=2))