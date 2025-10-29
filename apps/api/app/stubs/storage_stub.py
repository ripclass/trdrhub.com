"""
Stub S3 service for testing and development without real AWS credentials.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from urllib.parse import quote

from botocore.exceptions import ClientError

from ..config import settings
from ..schemas import DocumentUploadUrl
from ..models import DocumentType

logger = logging.getLogger(__name__)


class StubS3Service:
    """
    Stub S3 service that uses local filesystem storage.
    
    This service simulates S3 operations by storing files locally
    and providing fake pre-signed URLs that route through the FastAPI app.
    """
    
    def __init__(self):
        self.upload_dir = Path(settings.STUB_UPLOAD_DIR)
        self.base_url = "http://localhost:8000"  # Will be dynamically set by the app
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """Ensure the upload directory exists."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Stub upload directory: {self.upload_dir}")
    
    def set_base_url(self, base_url: str):
        """Set the base URL for generating fake pre-signed URLs."""
        self.base_url = base_url.rstrip('/')
    
    def generate_upload_urls(self, session_id: UUID) -> List[DocumentUploadUrl]:
        """Generate fake pre-signed URLs for document uploads."""
        
        # Check for error simulation
        if settings.STUB_FAIL_STORAGE:
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'AccessDenied',
                        'Message': 'Access Denied'
                    }
                },
                operation_name='GeneratePresignedUrl'
            )
        
        upload_urls = []
        
        # Generate URLs for all three document types
        document_types = [
            DocumentType.LETTER_OF_CREDIT,
            DocumentType.COMMERCIAL_INVOICE,
            DocumentType.BILL_OF_LADING
        ]
        
        for doc_type in document_types:
            file_id = uuid4()
            s3_key = f"uploads/{session_id}/{doc_type.value}/{file_id}"
            
            # Create directory for this upload
            upload_path = self.upload_dir / str(session_id) / doc_type.value
            upload_path.mkdir(parents=True, exist_ok=True)
            
            # Generate fake pre-signed URL
            presigned_url = f"{self.base_url}/fake-s3/{session_id}/{doc_type.value}/{file_id}"
            
            upload_urls.append(DocumentUploadUrl(
                document_type=doc_type,
                upload_url=presigned_url,
                s3_key=s3_key
            ))
        
        return upload_urls
    
    def store_uploaded_file(
        self, 
        session_id: str, 
        document_type: str, 
        file_id: str, 
        file_content: bytes,
        content_type: str = "application/pdf"
    ) -> Dict:
        """Store uploaded file content locally."""
        
        # Check for error simulation
        if settings.STUB_FAIL_STORAGE:
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'InternalError',
                        'Message': 'We encountered an internal error. Please try again.'
                    }
                },
                operation_name='PutObject'
            )
        
        # Determine file extension from content type
        ext_map = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg"
        }
        ext = ext_map.get(content_type, ".pdf")
        
        # Create file path
        file_path = self.upload_dir / session_id / document_type / f"{file_id}{ext}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file content
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Stored stub file: {file_path} ({len(file_content)} bytes)")
        
        return {
            "file_path": str(file_path),
            "file_size": len(file_content),
            "content_type": content_type,
            "stored_at": datetime.now().isoformat()
        }
    
    def get_file_path(self, s3_key: str) -> Path:
        """Get local file path from S3 key."""
        # Convert S3 key format to local path
        # uploads/{session_id}/{document_type}/{file_id} -> {upload_dir}/{session_id}/{document_type}/{file_id}*
        key_parts = s3_key.split('/')
        if len(key_parts) >= 4 and key_parts[0] == 'uploads':
            session_id, doc_type, file_id = key_parts[1], key_parts[2], key_parts[3]
            
            # Find file with any extension
            base_dir = self.upload_dir / session_id / doc_type
            if base_dir.exists():
                for ext in ['.pdf', '.png', '.jpg', '.jpeg']:
                    file_path = base_dir / f"{file_id}{ext}"
                    if file_path.exists():
                        return file_path
        
        # If not found, return expected path (will not exist)
        return self.upload_dir / s3_key
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in local storage."""
        return self.get_file_path(s3_key).exists()
    
    def get_file_info(self, s3_key: str) -> Dict:
        """Get file information."""
        file_path = self.get_file_path(s3_key)
        
        if not file_path.exists():
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'NoSuchKey',
                        'Message': 'The specified key does not exist.'
                    }
                },
                operation_name='GetObject'
            )
        
        stat = file_path.stat()
        return {
            "file_path": str(file_path),
            "file_size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_type": self._guess_content_type(file_path)
        }
    
    def _guess_content_type(self, file_path: Path) -> str:
        """Guess content type from file extension."""
        ext = file_path.suffix.lower()
        type_map = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        return type_map.get(ext, 'application/octet-stream')
    
    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate fake download URL."""
        
        # Check for error simulation
        if settings.STUB_FAIL_STORAGE:
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'AccessDenied',
                        'Message': 'Access Denied'
                    }
                },
                operation_name='GeneratePresignedUrl'
            )
        
        # Encode the S3 key for URL safety
        encoded_key = quote(s3_key, safe='/')
        return f"{self.base_url}/fake-s3-download/{encoded_key}"
    
    def cleanup_session_files(self, session_id: str):
        """Clean up files for a session (simulates S3 lifecycle policy)."""
        session_dir = self.upload_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.info(f"Cleaned up stub files for session {session_id}")
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics for monitoring."""
        total_size = 0
        total_files = 0
        sessions = set()
        
        for file_path in self.upload_dir.rglob('*'):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
                
                # Extract session ID from path
                try:
                    relative_path = file_path.relative_to(self.upload_dir)
                    session_id = relative_path.parts[0]
                    sessions.add(session_id)
                except (ValueError, IndexError):
                    pass
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_sessions": len(sessions),
            "storage_path": str(self.upload_dir)
        }

    async def upload_file(self, file, session_id: UUID, document_type: str) -> Dict:
        """Upload a file directly (stub implementation)."""
        from fastapi import UploadFile

        # Check for error simulation
        if settings.STUB_FAIL_STORAGE:
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'InternalError',
                        'Message': 'We encountered an internal error. Please try again.'
                    }
                },
                operation_name='PutObject'
            )

        # Generate file ID and extension
        file_id = uuid4()
        file_extension = os.path.splitext(file.filename or "")[1] or ".pdf"
        s3_key = f"uploads/{session_id}/{document_type}/{file_id}{file_extension}"

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Store file locally
        file_path = self.upload_dir / str(session_id) / document_type
        file_path.mkdir(parents=True, exist_ok=True)

        full_file_path = file_path / f"{file_id}{file_extension}"
        with open(full_file_path, 'wb') as f:
            f.write(file_content)

        logger.info(f"Stub uploaded file: {full_file_path} ({file_size} bytes)")

        # Generate fake S3 URL
        s3_url = f"{self.base_url}/fake-s3-download/{quote(s3_key, safe='/')}"

        return {
            's3_key': s3_key,
            's3_url': s3_url,
            'file_size': file_size,
            'content_type': file.content_type or 'application/octet-stream',
            'original_filename': file.filename or 'unknown'
        }