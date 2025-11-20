"""
Supabase Storage service for rules file management.
"""
import hashlib
import json
import logging
import os
from typing import Dict, Any

from supabase import create_client, Client

from app.config import settings

logger = logging.getLogger(__name__)


class RulesStorageService:
    """Service for managing rules files in Supabase Storage."""

    def __init__(self):
        """Initialize Supabase client with service role key for admin operations."""
        # Read from settings (which loads from environment variables)
        supabase_url = settings.SUPABASE_URL or os.getenv("SUPABASE_URL")
        service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.bucket_name = getattr(settings, "RULES_STORAGE_BUCKET", None) or "rules"
        
        if not supabase_url:
            logger.error("SUPABASE_URL is not set in environment variables")
            raise ValueError(
                "Supabase Storage is not configured. Set SUPABASE_URL "
                "in the backend environment variables."
            )
        
        if not service_role_key:
            logger.error("SUPABASE_SERVICE_ROLE_KEY is not set in environment variables")
            raise ValueError(
                "Supabase Storage is not configured. Set SUPABASE_SERVICE_ROLE_KEY "
                "in the backend environment variables."
            )
        
        logger.info(f"Initializing Supabase client with URL: {supabase_url[:30]}...")
        
        try:
            self.client: Client = create_client(supabase_url, service_role_key)
            logger.info("Supabase client initialized successfully")
        except Exception as exc:
            logger.exception(f"Failed to initialize Supabase client. URL: {supabase_url[:30]}..., Error: {exc}")
            raise ValueError(
                f"Unable to initialize Supabase client: {str(exc)}. "
                f"Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are correct."
            ) from exc
    
    def upload_ruleset(
        self,
        rules_json: list[Dict[str, Any]],
        domain: str,
        jurisdiction: str,
        ruleset_version: str,
        rulebook_version: str
    ) -> Dict[str, Any]:
        """
        Upload a ruleset JSON file to Supabase Storage.
        
        Args:
            rules_json: List of rule objects
            domain: Rule domain (e.g., 'icc')
            jurisdiction: Jurisdiction (e.g., 'global')
            ruleset_version: Semantic version (e.g., '1.0.0')
            rulebook_version: Rulebook version (e.g., 'UCP600:2007')
        
        Returns:
            Dict with file_path, checksum_md5, rule_count
        """
        # Normalize JSON (sort keys, remove whitespace)
        normalized_json = json.dumps(rules_json, sort_keys=True, separators=(',', ':'))
        
        # Compute checksum
        checksum_md5 = hashlib.md5(normalized_json.encode('utf-8')).hexdigest()
        
        # Generate file path
        # Format: rules/{domain}/{domain}-{rulebook_version}-v{ruleset_version}.json
        # Example: rules/icc/icc-ucp600-v1.0.0.json
        safe_domain = domain.lower().replace(' ', '-')
        safe_rulebook = rulebook_version.lower().replace(':', '-').replace(' ', '-')
        filename = f"{safe_domain}-{safe_rulebook}-v{ruleset_version}.json"
        file_path = f"{domain}/{filename}"
        
        # Upload to Supabase Storage
        try:
            response = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=normalized_json.encode('utf-8'),
                file_options={
                    "content-type": "application/json",
                    "upsert": "false"  # Don't overwrite existing files
                }
            )
            
            return {
                "file_path": file_path,
                "checksum_md5": checksum_md5,
                "rule_count": len(rules_json),
                "file_size": len(normalized_json.encode('utf-8'))
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to upload ruleset to Supabase Storage: {error_msg}", exc_info=True)
            
            # If bucket doesn't exist, provide helpful error
            if "Bucket not found" in error_msg or "does not exist" in error_msg:
                raise ValueError(
                    f"Supabase Storage bucket '{self.bucket_name}' does not exist. "
                    f"Please create it in the Supabase dashboard or via API."
                ) from e
            
            # If permission denied
            if "permission" in error_msg.lower() or "forbidden" in error_msg.lower() or "unauthorized" in error_msg.lower():
                raise ValueError(
                    f"Permission denied accessing Supabase Storage bucket '{self.bucket_name}'. "
                    f"Verify that SUPABASE_SERVICE_ROLE_KEY has storage access permissions."
                ) from e
            
            # Generic error with more context
            raise ValueError(
                f"Failed to upload to Supabase Storage: {error_msg}. "
                f"Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are correct."
            ) from e
    
    def get_ruleset_file(self, file_path: str) -> Dict[str, Any]:
        """
        Download a ruleset file from Supabase Storage.
        
        Args:
            file_path: Path to the file in storage (e.g., 'icc/icc-ucp600-v1.0.0.json')
        
        Returns:
            Dict with content (parsed JSON), checksum_md5, file_size
        """
        try:
            response = self.client.storage.from_(self.bucket_name).download(file_path)
            content = response.decode('utf-8')
            rules_json = json.loads(content)
            
            # Compute checksum for verification
            normalized = json.dumps(rules_json, sort_keys=True, separators=(',', ':'))
            checksum_md5 = hashlib.md5(normalized.encode('utf-8')).hexdigest()
            
            return {
                "content": rules_json,
                "checksum_md5": checksum_md5,
                "file_size": len(content.encode('utf-8'))
            }
        except Exception as e:
            raise FileNotFoundError(f"Ruleset file not found: {file_path}") from e
    
    def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Generate a signed URL for downloading a ruleset file.
        
        Args:
            file_path: Path to the file in storage
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed URL string
        """
        try:
            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return response.get("signedURL", "")
        except Exception as e:
            raise ValueError(f"Failed to generate signed URL for {file_path}") from e
    
    def delete_ruleset_file(self, file_path: str) -> bool:
        """
        Delete a ruleset file from Supabase Storage.
        
        Args:
            file_path: Path to the file in storage
        
        Returns:
            True if successful
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            raise ValueError(f"Failed to delete file {file_path}") from e

