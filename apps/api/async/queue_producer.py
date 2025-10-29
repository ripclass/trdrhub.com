#!/usr/bin/env python3
"""
LCopilot Trust Platform - SQS Queue Producer
Phase 4: Async Processing Pipeline

Handles document upload and job queuing for async processing.
Integrates with rate limiting and tier management.
"""

import json
import boto3
import uuid
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import hashlib
from pathlib import Path

from .rate_limiter import RateLimiter
from .job_status import JobStatusManager

@dataclass
class QueueJob:
    """Represents a job in the async processing queue"""
    job_id: str
    user_id: str
    tier: str  # free, pro, enterprise
    document_path: str
    document_hash: str
    lc_document: Dict[str, Any]
    bank_mode: Optional[str]
    options: Dict[str, Any]
    created_at: str
    priority: int = 0  # Higher number = higher priority
    retry_count: int = 0
    max_retries: int = 3

class QueueProducer:
    """Handles document upload and job queuing for async processing"""

    def __init__(self, config_path: str = "trust_config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)

        # Validate AWS credentials are available
        if not os.environ.get('AWS_ACCESS_KEY_ID') or not os.environ.get('AWS_SECRET_ACCESS_KEY'):
            raise ConfigError("AWS credentials not found in environment variables. "
                            "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

        # Initialize AWS clients with explicit credentials
        aws_region = self.config.get('async_processing', {}).get('sqs', {}).get('aws_region', 'us-east-1')

        # Create session with explicit credentials
        session = boto3.Session(
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', aws_region)
        )

        self.sqs = session.client('sqs')
        self.s3 = session.client('s3')

        # Initialize components
        self.rate_limiter = RateLimiter(config_path)
        self.job_status = JobStatusManager(config_path)

        # Queue configuration
        sqs_config = self.config.get('async_processing', {}).get('sqs', {})
        self.queue_name = sqs_config.get('queue_name', 'lcopilot-processing-queue')
        self.dead_letter_queue = sqs_config.get('dead_letter_queue', 'lcopilot-dlq')
        self.visibility_timeout = sqs_config.get('visibility_timeout', 300)

        # S3 configuration for document storage
        self.s3_bucket = self.config.get('storage', {}).get('s3_bucket', 'lcopilot-documents')

        self._setup_queues()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load trust platform configuration"""
        import yaml

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return {}

    def _setup_queues(self):
        """Set up SQS queues if they don't exist"""
        try:
            # Check if main queue exists
            self.queue_url = self._get_or_create_queue(self.queue_name, {
                'VisibilityTimeoutSeconds': str(self.visibility_timeout),
                'MessageRetentionPeriod': '1209600',  # 14 days
                'MaxReceiveCount': '3'
            })

            # Check if DLQ exists
            self.dlq_url = self._get_or_create_queue(self.dead_letter_queue, {
                'MessageRetentionPeriod': '1209600'  # 14 days
            })

            self.logger.info(f"Queue setup complete: {self.queue_name}")

        except Exception as e:
            self.logger.error(f"Failed to setup queues: {e}")
            raise

    def _get_or_create_queue(self, queue_name: str, attributes: Dict[str, str]) -> str:
        """Get existing queue URL or create new queue"""
        try:
            # Try to get existing queue
            response = self.sqs.get_queue_url(QueueName=queue_name)
            return response['QueueUrl']
        except self.sqs.exceptions.QueueDoesNotExist:
            # Create new queue
            response = self.sqs.create_queue(
                QueueName=queue_name,
                Attributes=attributes
            )
            return response['QueueUrl']

    def enqueue_job(
        self,
        user_id: str,
        tier: str,
        document_path: str,
        lc_document: Dict[str, Any],
        bank_mode: Optional[str] = None,
        options: Dict[str, Any] = None
    ) -> str:
        """
        Enqueue a document processing job

        Args:
            user_id: User identifier
            tier: User tier (free, pro, enterprise)
            document_path: Path to uploaded document
            lc_document: LC document data
            bank_mode: Optional bank enforcement mode
            options: Additional processing options

        Returns:
            job_id: Unique job identifier

        Raises:
            RateLimitExceeded: If user has exceeded their tier limits
            QueueError: If job cannot be queued
        """
        job_id = str(uuid.uuid4())

        self.logger.info(f"Enqueuing job {job_id} for user {user_id} (tier: {tier})")

        try:
            # Check rate limits
            if not self.rate_limiter.check_rate_limit(user_id, tier):
                raise RateLimitExceeded(f"Rate limit exceeded for tier {tier}")

            # Upload document to S3 for processing
            s3_key = self._upload_document_to_s3(document_path, job_id)

            # Calculate document hash for deduplication
            document_hash = self._calculate_file_hash(document_path)

            # Create job object
            job = QueueJob(
                job_id=job_id,
                user_id=user_id,
                tier=tier,
                document_path=s3_key,
                document_hash=document_hash,
                lc_document=lc_document,
                bank_mode=bank_mode,
                options=options or {},
                created_at=datetime.utcnow().isoformat(),
                priority=self._calculate_priority(tier)
            )

            # Initialize job status
            self.job_status.create_job(job_id, {
                'status': 'queued',
                'user_id': user_id,
                'tier': tier,
                'created_at': job.created_at,
                'document_hash': document_hash
            })

            # Send to SQS
            message_body = json.dumps(asdict(job))
            message_attributes = {
                'tier': {
                    'StringValue': tier,
                    'DataType': 'String'
                },
                'priority': {
                    'StringValue': str(job.priority),
                    'DataType': 'Number'
                },
                'user_id': {
                    'StringValue': user_id,
                    'DataType': 'String'
                }
            }

            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                MessageAttributes=message_attributes,
                DelaySeconds=0
            )

            # Record successful enqueue
            self.rate_limiter.record_request(user_id, tier)

            self.logger.info(f"Job {job_id} queued successfully (MessageId: {response['MessageId']})")

            return job_id

        except Exception as e:
            self.logger.error(f"Failed to enqueue job {job_id}: {e}")

            # Update job status to failed
            try:
                self.job_status.update_job_status(job_id, {
                    'status': 'failed',
                    'error': str(e),
                    'updated_at': datetime.utcnow().isoformat()
                })
            except:
                pass  # Don't fail if status update fails

            raise QueueError(f"Failed to enqueue job: {e}")

    def _upload_document_to_s3(self, document_path: str, job_id: str) -> str:
        """Upload document to S3 for processing by Lambda"""
        try:
            # Create S3 key with job ID and timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_extension = Path(document_path).suffix
            s3_key = f"documents/{timestamp}_{job_id}{file_extension}"

            # Validate KMS key is configured
            kms_key_id = os.environ.get('KMS_KEY_ID')
            if not kms_key_id:
                raise ConfigError("KMS_KEY_ID not found in environment variables. "
                                "Required for encrypted S3 uploads")

            # Upload file with KMS encryption
            with open(document_path, 'rb') as f:
                self.s3.upload_fileobj(
                    f,
                    self.s3_bucket,
                    s3_key,
                    ExtraArgs={
                        'ServerSideEncryption': 'aws:kms',
                        'SSEKMSKeyId': kms_key_id,
                        'StorageClass': 'INTELLIGENT_TIERING',
                        'Metadata': {
                            'job_id': job_id,
                            'uploaded_at': datetime.utcnow().isoformat()
                        }
                    }
                )

            self.logger.info(f"Document uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key

        except Exception as e:
            self.logger.error(f"Failed to upload document to S3: {e}")
            raise

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for deduplication"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _calculate_priority(self, tier: str) -> int:
        """Calculate job priority based on tier"""
        priority_map = {
            'enterprise': 10,
            'pro': 5,
            'free': 1
        }
        return priority_map.get(tier, 1)

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        try:
            # Get queue attributes
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['All']
            )

            attributes = response['Attributes']

            return {
                'queue_name': self.queue_name,
                'approximate_messages': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                'last_modified': attributes.get('LastModifiedTimestamp'),
                'visibility_timeout': int(attributes.get('VisibilityTimeout', 0)),
                'message_retention_period': int(attributes.get('MessageRetentionPeriod', 0))
            }

        except Exception as e:
            self.logger.error(f"Failed to get queue stats: {e}")
            return {'error': str(e)}

    def purge_queue(self) -> bool:
        """Purge all messages from queue (use with caution)"""
        try:
            self.sqs.purge_queue(QueueUrl=self.queue_url)
            self.logger.warning(f"Queue {self.queue_name} purged")
            return True
        except Exception as e:
            self.logger.error(f"Failed to purge queue: {e}")
            return False

    def requeue_failed_job(self, job_id: str) -> bool:
        """Requeue a failed job with increased retry count"""
        try:
            # Get job status
            job_status = self.job_status.get_job_status(job_id)

            if not job_status or job_status.get('status') != 'failed':
                self.logger.warning(f"Job {job_id} is not in failed state")
                return False

            # Check if we have the original job data
            original_job_data = job_status.get('original_job_data')
            if not original_job_data:
                self.logger.error(f"No original job data found for {job_id}")
                return False

            # Recreate job with incremented retry count
            job = QueueJob(**original_job_data)
            job.retry_count += 1

            if job.retry_count > job.max_retries:
                self.logger.warning(f"Job {job_id} has exceeded max retries ({job.max_retries})")
                return False

            # Send back to queue
            message_body = json.dumps(asdict(job))

            self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    'tier': {
                        'StringValue': job.tier,
                        'DataType': 'String'
                    },
                    'retry_count': {
                        'StringValue': str(job.retry_count),
                        'DataType': 'Number'
                    }
                }
            )

            # Update job status
            self.job_status.update_job_status(job_id, {
                'status': 'queued',
                'retry_count': job.retry_count,
                'requeued_at': datetime.utcnow().isoformat()
            })

            self.logger.info(f"Job {job_id} requeued (retry {job.retry_count})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to requeue job {job_id}: {e}")
            return False

class QueueError(Exception):
    """Raised when queue operations fail"""
    pass

class RateLimitExceeded(Exception):
    """Raised when user exceeds tier rate limits"""
    pass

class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""
    pass