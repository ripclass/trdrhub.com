"""
Bulk Processing Service
Handles batch LC processing with async queue workers and retry logic
"""

import asyncio
import json
import zipfile
import csv
import io
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import boto3
from botocore.exceptions import ClientError

from app.models.bulk_jobs import (
    BulkJob, BulkItem, BulkFailure, JobEvent, BulkTemplate,
    JobStatus, ItemStatus, JobEventType
)
from app.config import settings
from app.core.queue import get_queue, Queue
from app.core.events import EventSeverity
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service
from app.core.exceptions import ValidationError, ProcessingError
from app.metrics.workflow_metrics import bulk_metrics

import logging

logger = logging.getLogger(__name__)


class BulkProcessor:
    """Service for managing bulk LC processing jobs"""

    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.queue = get_queue('bulk_processing')
        self.max_batch_size = 200
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.supported_formats = ['zip', 'csv', 'json']

    async def create_job(
        self,
        db: Session,
        tenant_id: str,
        name: str,
        job_type: str,
        config: Dict[str, Any],
        created_by: UUID,
        bank_alias: Optional[str] = None,
        priority: int = 0,
        manifest_data: Optional[Dict[str, Any]] = None,
        s3_manifest_key: Optional[str] = None
    ) -> BulkJob:
        """Create a new bulk processing job"""

        # Validate job configuration
        self._validate_job_config(job_type, config)

        # Create job record
        job = BulkJob(
            tenant_id=tenant_id,
            bank_alias=bank_alias,
            name=name,
            description=config.get('description'),
            job_type=job_type,
            config=config,
            created_by=created_by,
            priority=priority,
            status=JobStatus.PENDING,
            s3_manifest_bucket=settings.S3_BUCKET if s3_manifest_key else None,
            s3_manifest_key=s3_manifest_key
        )

        db.add(job)
        db.flush()

        # Create job event
        await self._create_job_event(
            db, job.id, JobEventType.CREATED, {
                "job_type": job_type,
                "config": config,
                "manifest_provided": manifest_data is not None or s3_manifest_key is not None
            }, created_by
        )

        # Process manifest if provided
        if manifest_data:
            items = await self._process_manifest_data(db, job.id, manifest_data)
            job.total_items = len(items)
        elif s3_manifest_key:
            items = await self._process_s3_manifest(db, job.id, s3_manifest_key)
            job.total_items = len(items)

        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=tenant_id,
            event_type="bulk.job.created",
            actor_id=created_by,
            resource_type="bulk_job",
            resource_id=str(job.id),
            details={
                "name": name,
                "job_type": job_type,
                "total_items": job.total_items,
                "priority": priority
            }
        )

        # Queue job for processing
        await self._queue_job(job.id)

        bulk_metrics.jobs_created_total.labels(
            tenant=tenant_id,
            job_type=job_type
        ).inc()

        return job

    async def start_job(self, db: Session, job_id: UUID, worker_id: str) -> bool:
        """Start processing a bulk job"""

        job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
        if not job:
            return False

        if job.status != JobStatus.PENDING:
            logger.warning(f"Job {job_id} is not in pending status: {job.status}")
            return False

        # Update job status
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()

        # Create start event
        await self._create_job_event(
            db, job_id, JobEventType.STARTED, {
                "worker_id": worker_id,
                "total_items": job.total_items
            }
        )

        db.commit()

        # Start processing items
        await self._process_job_items(db, job_id, worker_id)

        return True

    async def _process_job_items(self, db: Session, job_id: UUID, worker_id: str):
        """Process all items in a job"""

        job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
        if not job:
            return

        try:
            # Get pending items
            items = db.query(BulkItem).filter(
                and_(
                    BulkItem.job_id == job_id,
                    BulkItem.status == ItemStatus.PENDING
                )
            ).order_by(BulkItem.created_at).all()

            logger.info(f"Processing {len(items)} items for job {job_id}")

            start_time = datetime.utcnow()
            processed_count = 0
            failed_count = 0

            # Process items in batches
            batch_size = min(10, len(items))
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]

                # Process batch concurrently
                tasks = [
                    self._process_single_item(db, item, worker_id)
                    for item in batch
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Update counts
                for result in results:
                    if isinstance(result, Exception):
                        failed_count += 1
                    else:
                        processed_count += 1

                # Update job progress
                await self._update_job_progress(db, job_id, processed_count + failed_count)

                # Refresh session to avoid stale data
                db.refresh(job)

            # Calculate final stats
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Update job completion
            job.finished_at = end_time
            job.duration_seconds = int(duration)
            job.processed_items = processed_count + failed_count
            job.succeeded_items = processed_count
            job.failed_items = failed_count

            if duration > 0:
                job.throughput_items_per_sec = round(processed_count / duration, 2)

            # Determine final status
            if failed_count == 0:
                job.status = JobStatus.SUCCEEDED
            elif processed_count == 0:
                job.status = JobStatus.FAILED
            else:
                job.status = JobStatus.PARTIAL

            # Create completion event
            await self._create_job_event(
                db, job_id, JobEventType.COMPLETED, {
                    "worker_id": worker_id,
                    "duration_seconds": duration,
                    "processed_items": processed_count,
                    "failed_items": failed_count,
                    "throughput_items_per_sec": job.throughput_items_per_sec
                }
            )

            db.commit()

            # Send completion notification
            await notification_service.emit_event_simple(
                tenant_id=job.tenant_id,
                event_key="bulk.job.completed",
                event_data={
                    "job_id": str(job_id),
                    "name": job.name,
                    "status": job.status,
                    "processed_items": processed_count,
                    "failed_items": failed_count,
                    "duration_seconds": duration
                },
                db=db
            )

            # Update metrics
            bulk_metrics.job_duration_seconds.labels(
                tenant=job.tenant_id,
                job_type=job.job_type,
                status=job.status
            ).observe(duration)

            bulk_metrics.items_processed_total.labels(
                tenant=job.tenant_id,
                job_type=job.job_type,
                status="succeeded"
            ).inc(processed_count)

            bulk_metrics.items_processed_total.labels(
                tenant=job.tenant_id,
                job_type=job.job_type,
                status="failed"
            ).inc(failed_count)

        except Exception as e:
            logger.error(f"Job {job_id} processing failed: {str(e)}")

            # Mark job as failed
            job.status = JobStatus.FAILED
            job.finished_at = datetime.utcnow()
            job.last_error = str(e)

            await self._create_job_event(
                db, job_id, JobEventType.FAILED, {
                    "worker_id": worker_id,
                    "error": str(e)
                }
            )

            db.commit()

            # Send failure notification
            await notification_service.emit_event_simple(
                tenant_id=job.tenant_id,
                event_key="bulk.job.failed",
                event_data={
                    "job_id": str(job_id),
                    "name": job.name,
                    "error": str(e)
                },
                db=db,
                severity=EventSeverity.ERROR
            )

    async def _process_single_item(
        self,
        db: Session,
        item: BulkItem,
        worker_id: str
    ) -> bool:
        """Process a single bulk item"""

        start_time = datetime.utcnow()

        try:
            # Update item status
            item.status = ItemStatus.PROCESSING
            item.started_at = start_time
            item.attempts += 1

            # Generate idempotency key if not exists
            if not item.idempotency_key:
                item.idempotency_key = self._generate_idempotency_key(
                    item.job_id, item.lc_identifier
                )

            db.commit()

            # Process based on job type
            job = item.job
            result = await self._execute_item_processing(job, item)

            # Update item with results
            item.status = ItemStatus.SUCCEEDED
            item.finished_at = datetime.utcnow()
            item.duration_ms = int((item.finished_at - start_time).total_seconds() * 1000)
            item.result_data = result

            db.commit()

            # Create success event
            await self._create_job_event(
                db, item.job_id, JobEventType.ITEM_COMPLETED, {
                    "item_id": str(item.id),
                    "lc_identifier": item.lc_identifier,
                    "duration_ms": item.duration_ms,
                    "worker_id": worker_id
                }
            )

            return True

        except Exception as e:
            logger.error(f"Item {item.id} processing failed: {str(e)}")

            # Update item with failure
            item.status = ItemStatus.FAILED
            item.finished_at = datetime.utcnow()
            item.duration_ms = int((item.finished_at - start_time).total_seconds() * 1000)
            item.last_error = str(e)
            item.retriable = self._is_retriable_error(e)

            # Create failure record
            failure = BulkFailure(
                item_id=item.id,
                attempt_number=item.attempts,
                error_code=getattr(e, 'code', 'UNKNOWN'),
                error_message=str(e),
                error_category=self._categorize_error(e),
                error_severity="high",
                retriable=item.retriable,
                worker_id=worker_id,
                failed_at=datetime.utcnow()
            )

            db.add(failure)

            # Schedule retry if retriable and under max attempts
            if item.retriable and item.attempts < item.max_attempts:
                retry_delay = self._calculate_retry_delay(item.attempts)
                failure.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                item.status = ItemStatus.RETRIED

                # Queue retry
                await self._queue_item_retry(item.id, retry_delay)

            db.commit()

            # Create failure event
            await self._create_job_event(
                db, item.job_id, JobEventType.ITEM_FAILED, {
                    "item_id": str(item.id),
                    "lc_identifier": item.lc_identifier,
                    "error": str(e),
                    "attempt_number": item.attempts,
                    "retriable": item.retriable,
                    "worker_id": worker_id
                }
            )

            return False

    async def _execute_item_processing(self, job: BulkJob, item: BulkItem) -> Dict[str, Any]:
        """Execute the actual processing logic for an item"""

        if job.job_type == "lc_validation":
            return await self._process_lc_validation(job, item)
        elif job.job_type == "doc_verification":
            return await self._process_doc_verification(job, item)
        elif job.job_type == "risk_analysis":
            return await self._process_risk_analysis(job, item)
        else:
            raise ProcessingError(f"Unknown job type: {job.job_type}")

    async def _process_lc_validation(self, job: BulkJob, item: BulkItem) -> Dict[str, Any]:
        """Process LC validation for a single item"""

        lc_data = item.item_data

        # Simulate LC validation logic
        await asyncio.sleep(0.1)  # Simulate processing time

        # Mock validation results
        validation_result = {
            "lc_number": item.lc_identifier,
            "validation_status": "passed",
            "discrepancies_found": 0,
            "compliance_score": 95.5,
            "processing_time_ms": 100,
            "validated_fields": ["amount", "expiry_date", "beneficiary", "applicant"],
            "warnings": [],
            "errors": []
        }

        return validation_result

    async def _process_doc_verification(self, job: BulkJob, item: BulkItem) -> Dict[str, Any]:
        """Process document verification for a single item"""

        # Simulate document verification
        await asyncio.sleep(0.2)

        verification_result = {
            "document_id": item.lc_identifier,
            "verification_status": "verified",
            "document_type": "commercial_invoice",
            "authenticity_score": 98.2,
            "extracted_data": {
                "amount": "100000.00",
                "currency": "USD",
                "date": "2024-01-15"
            }
        }

        return verification_result

    async def _process_risk_analysis(self, job: BulkJob, item: BulkItem) -> Dict[str, Any]:
        """Process risk analysis for a single item"""

        # Simulate risk analysis
        await asyncio.sleep(0.3)

        risk_result = {
            "lc_number": item.lc_identifier,
            "risk_score": 25.5,
            "risk_level": "low",
            "risk_factors": [
                {"factor": "country_risk", "score": 15.0},
                {"factor": "bank_rating", "score": 10.5}
            ],
            "recommendations": ["Monitor for updates", "Standard processing"]
        }

        return risk_result

    async def retry_failed_items(self, db: Session, job_id: UUID, user_id: UUID) -> int:
        """Retry all failed items in a job"""

        # Get failed items
        failed_items = db.query(BulkItem).filter(
            and_(
                BulkItem.job_id == job_id,
                BulkItem.status == ItemStatus.FAILED,
                BulkItem.retriable == True,
                BulkItem.attempts < BulkItem.max_attempts
            )
        ).all()

        if not failed_items:
            return 0

        # Reset items for retry
        retry_count = 0
        for item in failed_items:
            item.status = ItemStatus.PENDING
            item.last_error = None
            retry_count += 1

        # Create retry event
        job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
        if job:
            await self._create_job_event(
                db, job_id, JobEventType.RETRY_REQUESTED, {
                    "items_to_retry": retry_count,
                    "requested_by": str(user_id)
                }, user_id
            )

            # Update job status if needed
            if job.status in [JobStatus.FAILED, JobStatus.PARTIAL]:
                job.status = JobStatus.RUNNING

        db.commit()

        # Queue job for reprocessing
        await self._queue_job(job_id)

        return retry_count

    def _validate_job_config(self, job_type: str, config: Dict[str, Any]):
        """Validate job configuration"""

        allowed_types = ["lc_validation", "doc_verification", "risk_analysis"]
        if job_type not in allowed_types:
            raise ValidationError(f"Invalid job type: {job_type}")

        # Validate specific config requirements
        if job_type == "lc_validation":
            required_fields = ["validation_rules", "compliance_standards"]
            for field in required_fields:
                if field not in config:
                    raise ValidationError(f"Missing required config field: {field}")

    async def _process_manifest_data(
        self,
        db: Session,
        job_id: UUID,
        manifest_data: Dict[str, Any]
    ) -> List[BulkItem]:
        """Process manifest data and create bulk items"""

        items = []

        # Extract items from manifest
        lc_items = manifest_data.get('items', [])

        for idx, lc_data in enumerate(lc_items):
            if idx >= self.max_batch_size:
                logger.warning(f"Truncating batch at {self.max_batch_size} items")
                break

            # Validate required fields
            if 'lc_number' not in lc_data:
                raise ValidationError(f"Item {idx}: missing lc_number")

            # Create bulk item
            item = BulkItem(
                job_id=job_id,
                lc_identifier=lc_data['lc_number'],
                source_ref=f"manifest_item_{idx}",
                item_data=lc_data,
                status=ItemStatus.PENDING
            )

            db.add(item)
            items.append(item)

        return items

    async def _process_s3_manifest(
        self,
        db: Session,
        job_id: UUID,
        s3_key: str
    ) -> List[BulkItem]:
        """Process manifest file from S3"""

        try:
            # Download manifest from S3
            response = self.s3_client.get_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key
            )

            content = response['Body'].read()

            # Determine file type and parse
            if s3_key.endswith('.json'):
                manifest_data = json.loads(content)
                return await self._process_manifest_data(db, job_id, manifest_data)
            elif s3_key.endswith('.csv'):
                return await self._process_csv_manifest(db, job_id, content)
            elif s3_key.endswith('.zip'):
                return await self._process_zip_manifest(db, job_id, content)
            else:
                raise ValidationError(f"Unsupported manifest format: {s3_key}")

        except ClientError as e:
            raise ProcessingError(f"Failed to download manifest: {str(e)}")

    async def _process_csv_manifest(
        self,
        db: Session,
        job_id: UUID,
        csv_content: bytes
    ) -> List[BulkItem]:
        """Process CSV manifest"""

        items = []
        csv_data = csv_content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_data))

        for idx, row in enumerate(reader):
            if idx >= self.max_batch_size:
                break

            if 'lc_number' not in row:
                raise ValidationError(f"CSV row {idx}: missing lc_number column")

            item = BulkItem(
                job_id=job_id,
                lc_identifier=row['lc_number'],
                source_ref=f"csv_row_{idx}",
                item_data=dict(row),
                status=ItemStatus.PENDING
            )

            db.add(item)
            items.append(item)

        return items

    async def _process_zip_manifest(
        self,
        db: Session,
        job_id: UUID,
        zip_content: bytes
    ) -> List[BulkItem]:
        """Process ZIP manifest containing multiple files"""

        items = []

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            file_count = 0

            for file_info in zf.filelist:
                if file_count >= self.max_batch_size:
                    break

                if file_info.filename.endswith('/'):
                    continue  # Skip directories

                # Read file content
                with zf.open(file_info) as f:
                    file_content = f.read()

                # Create item for file
                item = BulkItem(
                    job_id=job_id,
                    lc_identifier=file_info.filename,
                    source_ref=f"zip_file_{file_count}",
                    item_data={
                        "filename": file_info.filename,
                        "file_size": file_info.file_size,
                        "content_preview": file_content[:1000].decode('utf-8', errors='ignore')
                    },
                    status=ItemStatus.PENDING
                )

                db.add(item)
                items.append(item)
                file_count += 1

        return items

    async def _update_job_progress(self, db: Session, job_id: UUID, processed_count: int):
        """Update job progress"""

        job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
        if job and job.total_items > 0:
            job.processed_items = processed_count
            job.progress_percent = round((processed_count / job.total_items) * 100, 2)

            # Estimate completion time
            if processed_count > 0 and job.started_at:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                estimated_total = (elapsed / processed_count) * job.total_items
                job.estimated_completion = job.started_at + timedelta(seconds=estimated_total)

            db.commit()

    async def _create_job_event(
        self,
        db: Session,
        job_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ):
        """Create a job event"""

        event = JobEvent(
            job_id=job_id,
            event_type=event_type,
            event_data=event_data,
            user_id=user_id
        )

        db.add(event)

    def _generate_idempotency_key(self, job_id: UUID, lc_identifier: str) -> str:
        """Generate idempotency key for item processing"""

        content = f"{job_id}:{lc_identifier}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _is_retriable_error(self, error: Exception) -> bool:
        """Determine if an error is retriable"""

        # Network errors, timeouts, temporary failures are retriable
        retriable_types = [
            "ConnectionError", "TimeoutError", "TemporaryFailure"
        ]

        return type(error).__name__ in retriable_types

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for reporting"""

        error_type = type(error).__name__

        if "Connection" in error_type or "Network" in error_type:
            return "network"
        elif "Validation" in error_type:
            return "validation"
        elif "Processing" in error_type:
            return "processing"
        else:
            return "system"

    def _calculate_retry_delay(self, attempt: int) -> int:
        """Calculate exponential backoff delay"""

        base_delay = 60  # 1 minute
        max_delay = 3600  # 1 hour

        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        return delay

    async def _queue_job(self, job_id: UUID):
        """Queue job for processing"""

        await self.queue.enqueue(
            "process_bulk_job",
            job_id=str(job_id),
            timeout=3600  # 1 hour timeout
        )

    async def _queue_item_retry(self, item_id: UUID, delay_seconds: int):
        """Queue item for retry after delay"""

        await self.queue.enqueue(
            "retry_bulk_item",
            item_id=str(item_id),
            delay=delay_seconds
        )


# Global service instance
bulk_processor = BulkProcessor()