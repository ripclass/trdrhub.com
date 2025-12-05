"""
Document Storage Service

Handles PDF storage to S3 with versioning and retrieval.
"""

import os
import io
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Environment variables
S3_BUCKET = os.getenv("AWS_S3_BUCKET_DOCUMENTS", "trdr-documents")
S3_REGION = os.getenv("AWS_S3_REGION", "us-east-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# S3 client configuration
S3_CONFIG = Config(
    region_name=S3_REGION,
    signature_version='s3v4',
    retries={'max_attempts': 3, 'mode': 'standard'}
)


class DocumentStorageService:
    """
    Service for storing generated documents in S3.
    
    Features:
    - Upload PDFs with versioning
    - Generate signed URLs for downloads
    - Track document versions
    - Calculate checksums for integrity
    """
    
    def __init__(self):
        self._client = None
        self._bucket = S3_BUCKET
        self._region = S3_REGION
    
    @property
    def client(self):
        """Lazy-load S3 client"""
        if self._client is None:
            if AWS_ACCESS_KEY and AWS_SECRET_KEY:
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY,
                    aws_secret_access_key=AWS_SECRET_KEY,
                    config=S3_CONFIG
                )
            else:
                # Use default credentials (IAM role, env vars, etc.)
                self._client = boto3.client('s3', config=S3_CONFIG)
        return self._client
    
    def _generate_s3_key(
        self,
        company_id: str,
        document_set_id: str,
        document_type: str,
        version: int = 1
    ) -> str:
        """
        Generate S3 key with organized folder structure.
        
        Format: doc-generator/{company_id}/{document_set_id}/{doc_type}_v{version}_{timestamp}.pdf
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"doc-generator/{company_id}/{document_set_id}/{document_type}_v{version}_{timestamp}.pdf"
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum of document"""
        return hashlib.sha256(data).hexdigest()
    
    async def upload_document(
        self,
        pdf_bytes: bytes,
        company_id: str,
        document_set_id: str,
        document_type: str,
        file_name: str,
        version: int = 1,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload a PDF document to S3.
        
        Returns:
            {
                "s3_key": str,
                "s3_bucket": str,
                "s3_region": str,
                "file_size": int,
                "checksum": str,
                "version": int,
            }
        """
        try:
            s3_key = self._generate_s3_key(company_id, document_set_id, document_type, version)
            checksum = self._calculate_checksum(pdf_bytes)
            
            # Prepare metadata
            s3_metadata = {
                "document-type": document_type,
                "document-set-id": document_set_id,
                "company-id": company_id,
                "version": str(version),
                "checksum": checksum,
            }
            if metadata:
                s3_metadata.update(metadata)
            
            # Upload to S3
            self.client.put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
                ContentDisposition=f'attachment; filename="{file_name}"',
                Metadata=s3_metadata,
            )
            
            logger.info(f"Uploaded document to S3: {s3_key} ({len(pdf_bytes)} bytes)")
            
            return {
                "s3_key": s3_key,
                "s3_bucket": self._bucket,
                "s3_region": self._region,
                "file_size": len(pdf_bytes),
                "checksum": checksum,
                "version": version,
            }
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise Exception(f"Failed to store document: {str(e)}")
    
    async def get_document(self, s3_key: str) -> Tuple[bytes, Dict[str, str]]:
        """
        Retrieve a document from S3.
        
        Returns: (pdf_bytes, metadata)
        """
        try:
            response = self.client.get_object(Bucket=self._bucket, Key=s3_key)
            pdf_bytes = response['Body'].read()
            metadata = response.get('Metadata', {})
            
            logger.info(f"Retrieved document from S3: {s3_key}")
            
            return pdf_bytes, metadata
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Document not found: {s3_key}")
            logger.error(f"S3 retrieval error: {e}")
            raise Exception(f"Failed to retrieve document: {str(e)}")
    
    async def get_signed_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
        response_content_disposition: Optional[str] = None
    ) -> str:
        """
        Generate a pre-signed URL for document download.
        
        Args:
            s3_key: S3 object key
            expires_in: URL expiry in seconds (default 1 hour)
            response_content_disposition: Optional Content-Disposition header
        
        Returns:
            Pre-signed URL
        """
        try:
            params = {
                'Bucket': self._bucket,
                'Key': s3_key,
            }
            
            if response_content_disposition:
                params['ResponseContentDisposition'] = response_content_disposition
            
            url = self.client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"Error generating signed URL: {e}")
            raise Exception(f"Failed to generate download URL: {str(e)}")
    
    async def delete_document(self, s3_key: str) -> bool:
        """Delete a document from S3."""
        try:
            self.client.delete_object(Bucket=self._bucket, Key=s3_key)
            logger.info(f"Deleted document from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"S3 deletion error: {e}")
            return False
    
    async def list_versions(
        self,
        company_id: str,
        document_set_id: str,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all versions of documents for a document set.
        
        Returns list of document info with versions.
        """
        try:
            prefix = f"doc-generator/{company_id}/{document_set_id}/"
            if document_type:
                prefix = f"{prefix}{document_type}_"
            
            response = self.client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix
            )
            
            documents = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                documents.append({
                    "s3_key": key,
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "document_type": self._extract_doc_type(key),
                })
            
            return sorted(documents, key=lambda x: x['last_modified'], reverse=True)
            
        except ClientError as e:
            logger.error(f"S3 list error: {e}")
            return []
    
    def _extract_doc_type(self, s3_key: str) -> str:
        """Extract document type from S3 key"""
        # Key format: doc-generator/{company}/{doc_set}/{type}_v{ver}_{timestamp}.pdf
        try:
            filename = s3_key.split('/')[-1]  # Get filename
            doc_type = filename.split('_v')[0]  # Get part before _v
            return doc_type
        except Exception:
            return "unknown"
    
    def is_configured(self) -> bool:
        """Check if S3 storage is properly configured"""
        return bool(self._bucket)


# Singleton instance
_storage_service: Optional[DocumentStorageService] = None


def get_document_storage() -> DocumentStorageService:
    """Get or create document storage service"""
    global _storage_service
    if _storage_service is None:
        _storage_service = DocumentStorageService()
    return _storage_service

