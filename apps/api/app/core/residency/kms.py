"""
KMS Encryption Service

Abstraction layer for Key Management Service operations supporting both AWS KMS and Vault Transit.
Provides encrypt/decrypt operations with comprehensive audit logging.
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError
import hvac
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.compliance import EncryptionEvent, ComplianceAuditEvent
from ...core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class EncryptionResult:
    """Result of an encryption operation"""
    encrypted_data: bytes
    key_id: str
    checksum_before: str
    checksum_after: str
    metadata: Dict[str, Any]

@dataclass
class DecryptionResult:
    """Result of a decryption operation"""
    decrypted_data: bytes
    key_id: str
    checksum_before: str
    checksum_after: str
    metadata: Dict[str, Any]

class KMSProvider(ABC):
    """Abstract base class for KMS providers"""

    @abstractmethod
    async def encrypt(self, data: bytes, key_id: str, context: Dict[str, str] = None) -> EncryptionResult:
        """Encrypt data using the specified key"""
        pass

    @abstractmethod
    async def decrypt(self, encrypted_data: bytes, context: Dict[str, str] = None) -> DecryptionResult:
        """Decrypt data"""
        pass

    @abstractmethod
    async def generate_data_key(self, key_id: str, key_spec: str = "AES_256") -> Tuple[bytes, bytes]:
        """Generate a data encryption key"""
        pass

    @abstractmethod
    async def describe_key(self, key_id: str) -> Dict[str, Any]:
        """Get key metadata"""
        pass

class AWSKMSProvider(KMSProvider):
    """AWS KMS implementation"""

    def __init__(self, region_name: str = None):
        self.region_name = region_name or settings.AWS_DEFAULT_REGION
        self.client = boto3.client('kms', region_name=self.region_name)

    async def encrypt(self, data: bytes, key_id: str, context: Dict[str, str] = None) -> EncryptionResult:
        """Encrypt data using AWS KMS"""
        checksum_before = hashlib.sha256(data).hexdigest()

        try:
            kwargs = {
                'KeyId': key_id,
                'Plaintext': data
            }
            if context:
                kwargs['EncryptionContext'] = context

            response = self.client.encrypt(**kwargs)

            encrypted_data = response['CiphertextBlob']
            checksum_after = hashlib.sha256(encrypted_data).hexdigest()

            return EncryptionResult(
                encrypted_data=encrypted_data,
                key_id=response['KeyId'],
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                metadata={
                    'encryption_algorithm': response.get('EncryptionAlgorithm', 'SYMMETRIC_DEFAULT'),
                    'aws_region': self.region_name,
                    'context': context
                }
            )
        except ClientError as e:
            logger.error(f"AWS KMS encryption failed: {e}")
            raise

    async def decrypt(self, encrypted_data: bytes, context: Dict[str, str] = None) -> DecryptionResult:
        """Decrypt data using AWS KMS"""
        checksum_before = hashlib.sha256(encrypted_data).hexdigest()

        try:
            kwargs = {
                'CiphertextBlob': encrypted_data
            }
            if context:
                kwargs['EncryptionContext'] = context

            response = self.client.decrypt(**kwargs)

            decrypted_data = response['Plaintext']
            checksum_after = hashlib.sha256(decrypted_data).hexdigest()

            return DecryptionResult(
                decrypted_data=decrypted_data,
                key_id=response['KeyId'],
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                metadata={
                    'encryption_algorithm': response.get('EncryptionAlgorithm', 'SYMMETRIC_DEFAULT'),
                    'aws_region': self.region_name,
                    'context': context
                }
            )
        except ClientError as e:
            logger.error(f"AWS KMS decryption failed: {e}")
            raise

    async def generate_data_key(self, key_id: str, key_spec: str = "AES_256") -> Tuple[bytes, bytes]:
        """Generate a data encryption key"""
        try:
            response = self.client.generate_data_key(
                KeyId=key_id,
                KeySpec=key_spec
            )
            return response['Plaintext'], response['CiphertextBlob']
        except ClientError as e:
            logger.error(f"AWS KMS data key generation failed: {e}")
            raise

    async def describe_key(self, key_id: str) -> Dict[str, Any]:
        """Get key metadata"""
        try:
            response = self.client.describe_key(KeyId=key_id)
            return response['KeyMetadata']
        except ClientError as e:
            logger.error(f"AWS KMS describe key failed: {e}")
            raise

class VaultKMSProvider(KMSProvider):
    """HashiCorp Vault Transit implementation"""

    def __init__(self, vault_url: str = None, vault_token: str = None, mount_point: str = "transit"):
        self.vault_url = vault_url or settings.VAULT_URL
        self.vault_token = vault_token or settings.VAULT_TOKEN
        self.mount_point = mount_point
        self.client = hvac.Client(url=self.vault_url, token=self.vault_token)

    async def encrypt(self, data: bytes, key_id: str, context: Dict[str, str] = None) -> EncryptionResult:
        """Encrypt data using Vault Transit"""
        checksum_before = hashlib.sha256(data).hexdigest()

        try:
            # Encode data as base64 for Vault
            import base64
            encoded_data = base64.b64encode(data).decode('utf-8')

            kwargs = {
                'name': key_id,
                'plaintext': encoded_data
            }
            if context:
                kwargs['context'] = base64.b64encode(json.dumps(context).encode()).decode()

            response = self.client.secrets.transit.encrypt_data(**kwargs)

            encrypted_data = response['data']['ciphertext'].encode('utf-8')
            checksum_after = hashlib.sha256(encrypted_data).hexdigest()

            return EncryptionResult(
                encrypted_data=encrypted_data,
                key_id=key_id,
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                metadata={
                    'vault_mount': self.mount_point,
                    'key_version': response['data'].get('key_version'),
                    'context': context
                }
            )
        except Exception as e:
            logger.error(f"Vault encryption failed: {e}")
            raise

    async def decrypt(self, encrypted_data: bytes, context: Dict[str, str] = None) -> DecryptionResult:
        """Decrypt data using Vault Transit"""
        checksum_before = hashlib.sha256(encrypted_data).hexdigest()

        try:
            import base64

            kwargs = {
                'ciphertext': encrypted_data.decode('utf-8')
            }
            if context:
                kwargs['context'] = base64.b64encode(json.dumps(context).encode()).decode()

            response = self.client.secrets.transit.decrypt_data(**kwargs)

            # Decode from base64
            decrypted_data = base64.b64decode(response['data']['plaintext'])
            checksum_after = hashlib.sha256(decrypted_data).hexdigest()

            return DecryptionResult(
                decrypted_data=decrypted_data,
                key_id="vault-transit",  # Vault doesn't return key ID in decrypt
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                metadata={
                    'vault_mount': self.mount_point,
                    'context': context
                }
            )
        except Exception as e:
            logger.error(f"Vault decryption failed: {e}")
            raise

    async def generate_data_key(self, key_id: str, key_spec: str = "AES_256") -> Tuple[bytes, bytes]:
        """Generate a data encryption key (Vault doesn't have direct equivalent)"""
        # For Vault, we can generate random bytes and encrypt them
        import os
        import base64

        key_size = 32 if key_spec == "AES_256" else 16  # 256 bits or 128 bits
        plaintext_key = os.urandom(key_size)

        result = await self.encrypt(plaintext_key, key_id)
        return plaintext_key, result.encrypted_data

    async def describe_key(self, key_id: str) -> Dict[str, Any]:
        """Get key metadata"""
        try:
            response = self.client.secrets.transit.read_key(name=key_id)
            return response['data']
        except Exception as e:
            logger.error(f"Vault describe key failed: {e}")
            raise

class KMSService:
    """High-level KMS service with audit logging"""

    def __init__(self, provider: KMSProvider, db: Session):
        self.provider = provider
        self.db = db

    async def encrypt_object(
        self,
        data: bytes,
        object_key: str,
        tenant_id: str,
        bucket: str,
        actor: str,
        key_id: str = None,
        context: Dict[str, str] = None
    ) -> EncryptionResult:
        """Encrypt object data with audit logging"""

        # Use default key if not specified
        if not key_id:
            key_id = settings.DEFAULT_KMS_KEY_ID

        # Add tenant context
        encryption_context = context or {}
        encryption_context.update({
            'tenant_id': tenant_id,
            'object_key': object_key,
            'bucket': bucket
        })

        try:
            result = await self.provider.encrypt(data, key_id, encryption_context)

            # Log successful encryption
            self._log_encryption_event(
                tenant_id=tenant_id,
                object_key=object_key,
                bucket=bucket,
                kms_key_id=result.key_id,
                checksum_before=result.checksum_before,
                checksum_after=result.checksum_after,
                actor=actor,
                action='encrypt',
                status='success'
            )

            return result

        except Exception as e:
            # Log failed encryption
            self._log_encryption_event(
                tenant_id=tenant_id,
                object_key=object_key,
                bucket=bucket,
                kms_key_id=key_id,
                checksum_before=hashlib.sha256(data).hexdigest(),
                checksum_after="",
                actor=actor,
                action='encrypt',
                status='failure',
                error_message=str(e)
            )
            raise

    async def decrypt_object(
        self,
        encrypted_data: bytes,
        object_key: str,
        tenant_id: str,
        bucket: str,
        actor: str,
        context: Dict[str, str] = None
    ) -> DecryptionResult:
        """Decrypt object data with audit logging"""

        # Add tenant context
        encryption_context = context or {}
        encryption_context.update({
            'tenant_id': tenant_id,
            'object_key': object_key,
            'bucket': bucket
        })

        try:
            result = await self.provider.decrypt(encrypted_data, encryption_context)

            # Log successful decryption
            self._log_encryption_event(
                tenant_id=tenant_id,
                object_key=object_key,
                bucket=bucket,
                kms_key_id=result.key_id,
                checksum_before=result.checksum_before,
                checksum_after=result.checksum_after,
                actor=actor,
                action='decrypt',
                status='success'
            )

            return result

        except Exception as e:
            # Log failed decryption
            self._log_encryption_event(
                tenant_id=tenant_id,
                object_key=object_key,
                bucket=bucket,
                kms_key_id="unknown",
                checksum_before=hashlib.sha256(encrypted_data).hexdigest(),
                checksum_after="",
                actor=actor,
                action='decrypt',
                status='failure',
                error_message=str(e)
            )
            raise

    def _log_encryption_event(
        self,
        tenant_id: str,
        object_key: str,
        bucket: str,
        kms_key_id: str,
        checksum_before: str,
        checksum_after: str,
        actor: str,
        action: str,
        status: str,
        error_message: str = None
    ):
        """Log encryption event to database"""
        try:
            event = EncryptionEvent(
                tenant_id=tenant_id,
                object_key=object_key,
                bucket=bucket,
                kms_key_id=kms_key_id,
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                actor=actor,
                action=action,
                status=status,
                error_message=error_message
            )
            self.db.add(event)
            self.db.commit()

            # Also log to compliance audit trail
            audit_event = ComplianceAuditEvent(
                event_type='encryption_operation',
                actor_id=actor,
                actor_type='user',
                tenant_id=tenant_id,
                resource_type='object',
                resource_id=object_key,
                action=f"{action}_object",
                outcome='success' if status == 'success' else 'failure',
                reason=error_message,
                metadata={
                    'bucket': bucket,
                    'kms_key_id': kms_key_id,
                    'checksum_before': checksum_before,
                    'checksum_after': checksum_after
                }
            )
            self.db.add(audit_event)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to log encryption event: {e}")
            self.db.rollback()

def get_kms_service(db: Session = None) -> KMSService:
    """Factory function to get KMS service instance"""
    if db is None:
        db = next(get_db())

    # Choose provider based on configuration
    if settings.KMS_PROVIDER == "aws":
        provider = AWSKMSProvider(region_name=settings.AWS_DEFAULT_REGION)
    elif settings.KMS_PROVIDER == "vault":
        provider = VaultKMSProvider(
            vault_url=settings.VAULT_URL,
            vault_token=settings.VAULT_TOKEN
        )
    else:
        raise ValueError(f"Unsupported KMS provider: {settings.KMS_PROVIDER}")

    return KMSService(provider, db)