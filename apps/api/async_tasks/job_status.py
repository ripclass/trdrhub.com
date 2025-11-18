#!/usr/bin/env python3
"""
LCopilot Trust Platform - Job Status Manager
Phase 4: Async Processing Pipeline

Manages job status tracking and polling for async document processing.
"""

import json
import time
import redis
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from enum import Enum
from dataclasses import dataclass, asdict

class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""
    pass

class JobStatus(Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class JobUpdate:
    """Job status update"""
    status: str
    message: Optional[str] = None
    progress: Optional[int] = None  # 0-100
    data: Optional[Dict[str, Any]] = None
    updated_at: Optional[str] = None

class JobStatusManager:
    """Manages job status tracking and polling"""

    def __init__(self, config_path: str = "trust_config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)

        # Validate Redis password is configured
        redis_password = os.environ.get('REDIS_PASSWORD')
        if not redis_password:
            raise ConfigError("REDIS_PASSWORD not found in environment variables. "
                            "Redis authentication is required for security")

        # Redis connection for job status storage with security
        redis_config = self.config.get('redis', {})
        self.redis_client = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 1),  # Use different DB for job status
            password=redis_password,
            ssl=redis_config.get('ssl', True),
            ssl_cert_reqs='required' if redis_config.get('ssl', True) else None,
            decode_responses=True
        )

        # Job configuration
        job_config = self.config.get('async_processing', {}).get('job_status', {})
        self.default_ttl = job_config.get('default_ttl', 604800)  # 7 days
        self.polling_interval = job_config.get('polling_interval', 2000)  # 2 seconds
        self.max_poll_duration = job_config.get('max_poll_duration', 300000)  # 5 minutes

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load trust platform configuration"""
        import yaml

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return {}

    def create_job(self, job_id: str, initial_data: Dict[str, Any]) -> bool:
        """
        Create a new job status entry

        Args:
            job_id: Unique job identifier
            initial_data: Initial job data

        Returns:
            bool: True if job created successfully
        """
        try:
            job_data = {
                'job_id': job_id,
                'status': JobStatus.QUEUED.value,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'progress': 0,
                'updates': [],
                **initial_data
            }

            # Store job data
            key = f"job:{job_id}"
            self.redis_client.setex(
                key,
                self.default_ttl,
                json.dumps(job_data)
            )

            # Add to user's job list
            user_id = initial_data.get('user_id')
            if user_id:
                user_jobs_key = f"user_jobs:{user_id}"
                self.redis_client.lpush(user_jobs_key, job_id)
                self.redis_client.expire(user_jobs_key, self.default_ttl)

            # Add to global job index
            self.redis_client.setex(
                f"job_index:{job_id}",
                self.default_ttl,
                user_id or 'anonymous'
            )

            self.logger.info(f"Created job status for {job_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create job {job_id}: {e}")
            return False

    def update_job_status(
        self,
        job_id: str,
        update_data: Dict[str, Any],
        add_to_history: bool = True
    ) -> bool:
        """
        Update job status

        Args:
            job_id: Job identifier
            update_data: Update data
            add_to_history: Whether to add update to history

        Returns:
            bool: True if update successful
        """
        try:
            key = f"job:{job_id}"
            job_data_str = self.redis_client.get(key)

            if not job_data_str:
                self.logger.warning(f"Job {job_id} not found for update")
                return False

            job_data = json.loads(job_data_str)

            # Update fields
            for field, value in update_data.items():
                job_data[field] = value

            job_data['updated_at'] = datetime.utcnow().isoformat()

            # Add to update history if requested
            if add_to_history:
                update_entry = {
                    'timestamp': job_data['updated_at'],
                    'status': update_data.get('status', job_data.get('status')),
                    'message': update_data.get('message'),
                    'progress': update_data.get('progress'),
                }

                if 'updates' not in job_data:
                    job_data['updates'] = []

                job_data['updates'].append(update_entry)

                # Keep only last 50 updates
                if len(job_data['updates']) > 50:
                    job_data['updates'] = job_data['updates'][-50:]

            # Save updated data
            self.redis_client.setex(
                key,
                self.default_ttl,
                json.dumps(job_data)
            )

            self.logger.debug(f"Updated job {job_id}: {update_data}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update job {job_id}: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status

        Args:
            job_id: Job identifier

        Returns:
            Job data or None if not found
        """
        try:
            key = f"job:{job_id}"
            job_data_str = self.redis_client.get(key)

            if not job_data_str:
                return None

            return json.loads(job_data_str)

        except Exception as e:
            self.logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    def get_user_jobs(
        self,
        user_id: str,
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get jobs for a specific user

        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return
            status_filter: Optional status filter

        Returns:
            List of job data
        """
        try:
            user_jobs_key = f"user_jobs:{user_id}"
            job_ids = self.redis_client.lrange(user_jobs_key, 0, limit - 1)

            jobs = []
            for job_id in job_ids:
                job_data = self.get_job_status(job_id)
                if job_data:
                    # Apply status filter if specified
                    if status_filter and job_data.get('status') != status_filter:
                        continue

                    # Remove sensitive data for user response
                    filtered_data = {
                        'job_id': job_data['job_id'],
                        'status': job_data['status'],
                        'progress': job_data.get('progress', 0),
                        'created_at': job_data['created_at'],
                        'updated_at': job_data['updated_at'],
                        'tier': job_data.get('tier'),
                        'processing_time': job_data.get('processing_time'),
                        'document_name': job_data.get('document_name')
                    }

                    # Include error message if failed
                    if job_data.get('status') == JobStatus.FAILED.value:
                        filtered_data['error'] = job_data.get('error')

                    # Include results if completed
                    if job_data.get('status') == JobStatus.COMPLETED.value:
                        filtered_data['results'] = job_data.get('results')

                    jobs.append(filtered_data)

            return jobs

        except Exception as e:
            self.logger.error(f"Failed to get user jobs for {user_id}: {e}")
            return []

    def poll_job_status(
        self,
        job_id: str,
        timeout_seconds: int = 300,
        poll_interval_ms: int = None
    ) -> Dict[str, Any]:
        """
        Poll job status until completion or timeout

        Args:
            job_id: Job identifier
            timeout_seconds: Maximum time to poll
            poll_interval_ms: Polling interval in milliseconds

        Returns:
            Final job status
        """
        if poll_interval_ms is None:
            poll_interval_ms = self.polling_interval

        start_time = time.time()
        timeout = min(timeout_seconds, self.max_poll_duration / 1000)

        while time.time() - start_time < timeout:
            job_data = self.get_job_status(job_id)

            if not job_data:
                return {'error': 'Job not found'}

            status = job_data.get('status')

            # Check if job is in terminal state
            if status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value,
                         JobStatus.TIMEOUT.value, JobStatus.CANCELLED.value]:
                return job_data

            # Wait before next poll
            time.sleep(poll_interval_ms / 1000.0)

        # Timeout reached
        self.update_job_status(job_id, {
            'status': JobStatus.TIMEOUT.value,
            'message': f'Polling timeout after {timeout} seconds'
        })

        return self.get_job_status(job_id) or {'error': 'Job timeout'}

    def cancel_job(self, job_id: str, reason: str = "User cancelled") -> bool:
        """
        Cancel a job

        Args:
            job_id: Job identifier
            reason: Cancellation reason

        Returns:
            bool: True if cancellation successful
        """
        try:
            job_data = self.get_job_status(job_id)

            if not job_data:
                return False

            current_status = job_data.get('status')

            # Can only cancel queued or processing jobs
            if current_status not in [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]:
                self.logger.warning(f"Cannot cancel job {job_id} in status {current_status}")
                return False

            # Update status to cancelled
            update_result = self.update_job_status(job_id, {
                'status': JobStatus.CANCELLED.value,
                'message': reason,
                'cancelled_at': datetime.utcnow().isoformat()
            })

            if update_result:
                self.logger.info(f"Cancelled job {job_id}: {reason}")

            return update_result

        except Exception as e:
            self.logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """
        Clean up old completed jobs

        Args:
            days_old: Remove jobs older than this many days

        Returns:
            Number of jobs cleaned up
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_old)
            cutoff_timestamp = cutoff_time.isoformat()

            # Find all job keys
            job_keys = self.redis_client.keys("job:*")
            cleaned_count = 0

            for key in job_keys:
                try:
                    job_data_str = self.redis_client.get(key)
                    if job_data_str:
                        job_data = json.loads(job_data_str)

                        # Check if job is old and completed/failed
                        created_at = job_data.get('created_at', '')
                        status = job_data.get('status')

                        if (created_at < cutoff_timestamp and
                            status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value,
                                      JobStatus.TIMEOUT.value, JobStatus.CANCELLED.value]):

                            # Delete job data
                            job_id = job_data.get('job_id')
                            self.redis_client.delete(key)
                            self.redis_client.delete(f"job_index:{job_id}")

                            # Remove from user job list
                            user_id = job_data.get('user_id')
                            if user_id:
                                user_jobs_key = f"user_jobs:{user_id}"
                                self.redis_client.lrem(user_jobs_key, 0, job_id)

                            cleaned_count += 1

                except Exception as e:
                    self.logger.warning(f"Failed to process job key {key}: {e}")
                    continue

            self.logger.info(f"Cleaned up {cleaned_count} old jobs")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old jobs: {e}")
            return 0

    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job processing statistics"""
        try:
            # Count jobs by status
            job_keys = self.redis_client.keys("job:*")
            status_counts = {}
            total_jobs = 0
            processing_times = []

            for key in job_keys:
                try:
                    job_data_str = self.redis_client.get(key)
                    if job_data_str:
                        job_data = json.loads(job_data_str)
                        status = job_data.get('status', 'unknown')

                        status_counts[status] = status_counts.get(status, 0) + 1
                        total_jobs += 1

                        # Collect processing times for completed jobs
                        if (status == JobStatus.COMPLETED.value and
                            'processing_time' in job_data):
                            processing_times.append(job_data['processing_time'])

                except Exception:
                    continue

            # Calculate processing time statistics
            processing_stats = {}
            if processing_times:
                processing_stats = {
                    'average_processing_time': sum(processing_times) / len(processing_times),
                    'min_processing_time': min(processing_times),
                    'max_processing_time': max(processing_times),
                    'total_completed': len(processing_times)
                }

            return {
                'total_jobs': total_jobs,
                'status_counts': status_counts,
                'processing_statistics': processing_stats,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get job statistics: {e}")
            return {'error': str(e)}

    def extend_job_ttl(self, job_id: str, additional_seconds: int = 86400) -> bool:
        """
        Extend job TTL for long-running processes

        Args:
            job_id: Job identifier
            additional_seconds: Additional seconds to extend TTL

        Returns:
            bool: True if extension successful
        """
        try:
            key = f"job:{job_id}"
            current_ttl = self.redis_client.ttl(key)

            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                self.redis_client.expire(key, new_ttl)

                # Also extend job index
                self.redis_client.expire(f"job_index:{job_id}", new_ttl)

                self.logger.info(f"Extended TTL for job {job_id} by {additional_seconds} seconds")
                return True
            else:
                self.logger.warning(f"Job {job_id} not found or already expired")
                return False

        except Exception as e:
            self.logger.error(f"Failed to extend TTL for job {job_id}: {e}")
            return False