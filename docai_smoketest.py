#!/usr/bin/env python3
"""
Google Cloud Document AI Smoke Test
===================================

This script tests the Document AI processor setup to verify:
1. Service account credentials are properly configured
2. Processor is accessible and functional
3. Document processing pipeline works end-to-end

Usage: python3 docai_smoketest.py [path_to_test_document]
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from google.cloud import documentai
    from google.api_core import exceptions as gcp_exceptions
    from decouple import config, Config, RepositoryEnv
except ImportError as e:
    logger.error(f"Missing required dependencies: {e}")
    logger.error("Please install: pip install google-cloud-documentai python-decouple")
    sys.exit(1)


class DocumentAISmokeTest:
    """Google Cloud Document AI smoke test runner."""

    def __init__(self):
        self.client: Optional[documentai.DocumentProcessorServiceClient] = None
        self.project_id: Optional[str] = None
        self.location: Optional[str] = None
        self.processor_id: Optional[str] = None
        self.processor_name: Optional[str] = None

    def load_environment(self) -> bool:
        """Load environment variables with fallback logic."""
        logger.info("Loading environment configuration...")

        # Try to load from .env.production first, then .env
        env_files = ['.env.production', 'apps/api/.env.production', '.env', 'apps/api/.env']
        config_obj = None

        for env_file in env_files:
            env_path = Path(env_file)
            if env_path.exists():
                logger.info(f"Loading environment from: {env_path}")
                config_obj = Config(RepositoryEnv(str(env_path)))
                break

        if not config_obj:
            logger.warning("No .env files found, using system environment variables")
            config_obj = config

        try:
            # Load Document AI configuration
            self.project_id = config_obj('GOOGLE_CLOUD_PROJECT', default=None)
            self.location = config_obj('GOOGLE_DOCUMENTAI_LOCATION', default='eu')
            self.processor_id = config_obj('GOOGLE_DOCUMENTAI_PROCESSOR_ID', default=None)

            # Load credentials path
            credentials_path = config_obj('GOOGLE_APPLICATION_CREDENTIALS', default=None)

            logger.info(f"Project ID: {self.project_id}")
            logger.info(f"Location: {self.location}")
            logger.info(f"Processor ID: {self.processor_id}")
            logger.info(f"Credentials path: {credentials_path}")

            # Validate required settings
            if not self.project_id:
                logger.error("GOOGLE_CLOUD_PROJECT is not set")
                return False

            if not self.processor_id:
                logger.error("GOOGLE_DOCUMENTAI_PROCESSOR_ID is not set")
                return False

            # Validate credentials file
            if credentials_path and not Path(credentials_path).exists():
                logger.error(f"Credentials file not found: {credentials_path}")
                return False
            elif credentials_path:
                # Set the environment variable for the Google client library
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                logger.info("✓ Credentials file found and set")

            # Build processor name
            self.processor_name = (
                f"projects/{self.project_id}/locations/{self.location}/"
                f"processors/{self.processor_id}"
            )
            logger.info(f"Processor name: {self.processor_name}")

            return True

        except Exception as e:
            logger.error(f"Error loading environment: {e}")
            return False

    def initialize_client(self) -> bool:
        """Initialize the Document AI client."""
        logger.info("Initializing Document AI client...")

        try:
            # Create client with regional endpoint
            if self.location and self.location != 'us':
                client_options = {"api_endpoint": f"{self.location}-documentai.googleapis.com"}
                self.client = documentai.DocumentProcessorServiceClient(
                    client_options=client_options
                )
                logger.info(f"✓ Client initialized with regional endpoint: {self.location}")
            else:
                self.client = documentai.DocumentProcessorServiceClient()
                logger.info("✓ Client initialized with default endpoint")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            return False

    def validate_processor(self) -> bool:
        """Validate that the processor exists and is accessible."""
        logger.info("Validating processor access...")

        try:
            # Try to get processor details
            processor = self.client.get_processor(name=self.processor_name)
            logger.info(f"✓ Processor found: {processor.display_name}")
            logger.info(f"  Type: {processor.type_}")
            logger.info(f"  State: {processor.state}")

            if processor.state != documentai.Processor.State.ENABLED:
                logger.warning(f"Processor state is: {processor.state}")

            return True

        except gcp_exceptions.NotFound:
            logger.error(f"Processor not found: {self.processor_name}")
            return False
        except gcp_exceptions.PermissionDenied:
            logger.error("Permission denied - check service account permissions")
            return False
        except Exception as e:
            logger.error(f"Error validating processor: {e}")
            return False

    def process_document(self, document_path: str) -> bool:
        """Process a test document."""
        logger.info(f"Processing document: {document_path}")

        doc_path = Path(document_path)
        if not doc_path.exists():
            logger.error(f"Document file not found: {document_path}")
            return False

        try:
            # Read document content
            with open(doc_path, 'rb') as file:
                document_content = file.read()

            # Determine MIME type based on file extension
            mime_type = "application/pdf"  # Default to PDF
            if doc_path.suffix.lower() in ['.jpg', '.jpeg']:
                mime_type = "image/jpeg"
            elif doc_path.suffix.lower() == '.png':
                mime_type = "image/png"
            elif doc_path.suffix.lower() == '.tiff':
                mime_type = "image/tiff"

            logger.info(f"Document MIME type: {mime_type}")
            logger.info(f"Document size: {len(document_content)} bytes")

            # Create the document request
            raw_document = documentai.RawDocument(
                content=document_content,
                mime_type=mime_type
            )

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )

            # Process the document
            logger.info("Sending document to Document AI...")
            result = self.client.process_document(request=request)

            # Extract and display results
            document = result.document
            logger.info("✓ Document processed successfully!")

            # Print extracted text
            if document.text:
                text_preview = document.text[:200].replace('\n', ' ')
                logger.info(f"Extracted text preview: {text_preview}...")
                logger.info(f"Total text length: {len(document.text)} characters")
            else:
                logger.warning("No text extracted from document")

            # Print form fields if any
            if document.entities:
                logger.info(f"Found {len(document.entities)} form fields:")
                for i, entity in enumerate(document.entities[:5]):  # Show first 5
                    confidence = getattr(entity, 'confidence', 0)
                    logger.info(f"  {i+1}. {entity.type_}: {entity.mention_text} "
                              f"(confidence: {confidence:.2f})")
                if len(document.entities) > 5:
                    logger.info(f"  ... and {len(document.entities) - 5} more fields")
            else:
                logger.info("No form fields extracted")

            # Print page count
            page_count = len(document.pages) if document.pages else 0
            logger.info(f"Document pages processed: {page_count}")

            return True

        except gcp_exceptions.InvalidArgument as e:
            logger.error(f"Invalid document or request: {e}")
            return False
        except gcp_exceptions.PermissionDenied as e:
            logger.error(f"Permission denied during processing: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return False

    def run_smoke_test(self, test_document: Optional[str] = None) -> bool:
        """Run the complete smoke test."""
        logger.info("=== Starting Document AI Smoke Test ===")

        # Step 1: Load environment
        if not self.load_environment():
            logger.error("❌ Environment configuration failed")
            return False

        # Step 2: Initialize client
        if not self.initialize_client():
            logger.error("❌ Client initialization failed")
            return False

        # Step 3: Validate processor
        if not self.validate_processor():
            logger.error("❌ Processor validation failed")
            return False

        # Step 4: Process test document
        if test_document:
            if not self.process_document(test_document):
                logger.error("❌ Document processing failed")
                return False
        else:
            logger.info("⚠️  No test document provided - skipping document processing")
            logger.info("To test document processing, run: python3 docai_smoketest.py path/to/sample.pdf")

        logger.info("✅ All smoke tests passed!")
        return True


def main():
    """Main entry point."""
    test_document = sys.argv[1] if len(sys.argv) > 1 else None

    if test_document:
        logger.info(f"Test document: {test_document}")
    else:
        logger.info("No test document provided - will test configuration only")

    smoke_test = DocumentAISmokeTest()
    success = smoke_test.run_smoke_test(test_document)

    if success:
        logger.info("🎉 Document AI setup is working correctly!")
        sys.exit(0)
    else:
        logger.error("💥 Document AI setup has issues")
        sys.exit(1)


if __name__ == "__main__":
    main()