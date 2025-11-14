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
from supabase_config import SUPABASE_URL as LEGACY_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY as LEGACY_SERVICE_ROLE_KEY

logger = logging.getLogger(__name__)


class RulesStorageService:
    """Service for managing rules files in Supabase Storage."""
    
    BUCKET_NAME = "rules"
    
    def __init__(self):
        """Initialize Supabase client with service role key for admin operations."""
        supabase_url = LEGACY_SUPABASE_URL or getattr(settings, "SUPABASE_URL", None) or os.getenv("SUPABASE_URL")
        service_role_key = LEGACY_SERVICE_ROLE_KEY or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None) or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not service_role_key:
            raise ValueError(
                "Supabase Storage is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "in the backend environment variables."
            )
        
        try:
            self.client: Client = create_client(supabase_url, service_role_key)
        except Exception as exc:
            logger.exception("Failed to initialize Supabase client")
            raise ValueError("Unable to initialize Supabase client. Verify SUPABASE_URL and service role key.") from exc
    
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
            response = self.client.storage.from_(self.BUCKET_NAME).upload(
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
            # If bucket doesn't exist, provide helpful error
            if "Bucket not found" in str(e) or "does not exist" in str(e):
                raise ValueError(
                    f"Supabase Storage bucket '{self.BUCKET_NAME}' does not exist. "
                    f"Please create it in the Supabase dashboard or via API."
                ) from e
            raise
    
    def get_ruleset_file(self, file_path: str) -> Dict[str, Any]:
        """
        Download a ruleset file from Supabase Storage.
        
        Args:
            file_path: Path to the file in storage (e.g., 'icc/icc-ucp600-v1.0.0.json')
        
        Returns:
            Dict with content (parsed JSON), checksum_md5, file_size
        """
        try:
            response = self.client.storage.from_(self.BUCKET_NAME).download(file_path)
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
            response = self.client.storage.from_(self.BUCKET_NAME).create_signed_url(
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
            self.client.storage.from_(self.BUCKET_NAME).remove([file_path])
            return True
        except Exception as e:
            raise ValueError(f"Failed to delete file {file_path}") from e

