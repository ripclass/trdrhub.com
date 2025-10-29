"""
Analytics service for computing dashboard metrics.
"""

import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import UUID
from collections import defaultdict, Counter

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_, extract, case
from sqlalchemy.sql import text

from ..models import (
    ValidationSession, Document, Discrepancy, User, UserRole
)
from ..models.audit_log import AuditLog, AuditAction, AuditResult
from ..schemas.analytics import (
    SummaryStats, DiscrepancyStats, TrendStats, TrendPoint,
    UserStats, SystemMetrics, ProcessingTimeBreakdown,
    DiscrepancyDetail, ComplianceReport, DateRange,
    AnomalyAlert, TimeRange
)


class AnalyticsService:
    """Service for computing analytics and dashboard metrics."""

    def __init__(self, db: Session):
        self.db = db

    def _parse_time_range(self, time_range: TimeRange, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """Parse time range into start and end datetime objects."""
        now = datetime.utcnow()

        if time_range == "custom":
            if not start_date or not end_date:
                raise ValueError("start_date and end_date required for custom time range")
            return start_date, end_date

        days_mapping = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "180d": 180,
            "365d": 365
        }

        days = days_mapping.get(time_range, 30)
        start = now - timedelta(days=days)
        return start, now

    def get_summary_stats(self, user: User, time_range: TimeRange = "30d",
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> SummaryStats:
        """Get summary statistics for jobs and processing."""

        start, end = self._parse_time_range(time_range, start_date, end_date)

        # Base query filtered by user role
        base_query = self.db.query(ValidationSession).filter(
            ValidationSession.created_at.between(start, end)
        )

        # Apply role-based filtering
        if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
            base_query = base_query.filter(ValidationSession.user_id == user.id)

        # Get job counts by status
        status_counts = base_query.with_entities(
            ValidationSession.status,
            func.count(ValidationSession.id).label('count')
        ).group_by(ValidationSession.status).all()

        # Convert to dict
        status_dict = {status: count for status, count in status_counts}

        total_jobs = sum(status_dict.values())
        success_count = status_dict.get('completed', 0)
        rejection_count = status_dict.get('failed', 0)
        pending_count = status_dict.get('processing', 0) + status_dict.get('created', 0)

        rejection_rate = (rejection_count / max(total_jobs, 1)) * 100

        # Calculate average processing time
        processing_times = base_query.filter(
            and_(
                ValidationSession.processing_started_at.isnot(None),
                ValidationSession.processing_completed_at.isnot(None)
            )
        ).with_entities(
            ValidationSession.processing_started_at,
            ValidationSession.processing_completed_at
        ).all()

        avg_processing_time = None
        if processing_times:
            total_minutes = 0
            for start_time, end_time in processing_times:
                if start_time and end_time:
                    delta = end_time - start_time
                    total_minutes += delta.total_seconds() / 60
            avg_processing_time = total_minutes / len(processing_times)

        # Document distribution
        doc_query = self.db.query(
            Document.document_type,
            func.count(Document.id).label('count')
        ).join(ValidationSession).filter(
            ValidationSession.created_at.between(start, end)
        )

        # Apply same role filtering for documents
        if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
            doc_query = doc_query.filter(ValidationSession.user_id == user.id)

        doc_distribution = doc_query.group_by(Document.document_type).all()
        doc_dist_dict = {doc_type: count for doc_type, count in doc_distribution}

        return SummaryStats(
            total_jobs=total_jobs,
            success_count=success_count,
            rejection_count=rejection_count,
            pending_count=pending_count,
            rejection_rate=round(rejection_rate, 2),
            avg_processing_time_minutes=round(avg_processing_time, 2) if avg_processing_time else None,
            doc_distribution=doc_dist_dict,
            time_range=time_range,
            start_date=start,
            end_date=end
        )

    def get_discrepancy_stats(self, user: User, time_range: TimeRange = "30d",
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> DiscrepancyStats:
        """Get discrepancy analysis statistics."""

        start, end = self._parse_time_range(time_range, start_date, end_date)

        # Base discrepancy query with role filtering
        base_query = self.db.query(Discrepancy).join(ValidationSession).filter(
            Discrepancy.created_at.between(start, end)
        )

        if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
            base_query = base_query.filter(ValidationSession.user_id == user.id)

        # Top discrepancy types
        top_discrepancies_query = base_query.with_entities(
            Discrepancy.discrepancy_type,
            Discrepancy.rule_name,
            func.count(Discrepancy.id).label('count')
        ).group_by(
            Discrepancy.discrepancy_type,
            Discrepancy.rule_name
        ).order_by(desc('count')).limit(10)

        top_discrepancies = [
            {
                "type": disc_type,
                "rule": rule_name,
                "count": count,
                "percentage": round((count / max(base_query.count(), 1)) * 100, 2)
            }
            for disc_type, rule_name, count in top_discrepancies_query.all()
        ]

        # Fatal four frequency (common critical discrepancies)
        fatal_four_patterns = [
            'currency_mismatch',
            'missing_bill_of_lading',
            'amount_discrepancy',
            'date_inconsistency'
        ]

        fatal_four_frequency = {}
        for pattern in fatal_four_patterns:
            count = base_query.filter(
                or_(
                    Discrepancy.discrepancy_type.ilike(f'%{pattern}%'),
                    Discrepancy.rule_name.ilike(f'%{pattern}%')
                )
            ).count()
            fatal_four_frequency[pattern] = count

        # Severity distribution
        severity_counts = base_query.with_entities(
            Discrepancy.severity,
            func.count(Discrepancy.id).label('count')
        ).group_by(Discrepancy.severity).all()

        severity_distribution = {severity: count for severity, count in severity_counts}

        # Discrepancy trends (daily)
        trend_query = base_query.with_entities(
            func.date(Discrepancy.created_at).label('date'),
            func.count(Discrepancy.id).label('count')
        ).group_by(func.date(Discrepancy.created_at)).order_by(asc('date'))

        discrepancy_trends = [
            {
                "date": trend_date.isoformat(),
                "count": count
            }
            for trend_date, count in trend_query.all()
        ]

        total_discrepancies = base_query.count()

        # Calculate jobs with discrepancies for average
        jobs_with_discrepancies = base_query.with_entities(
            func.count(func.distinct(Discrepancy.validation_session_id))
        ).scalar()

        avg_discrepancies_per_job = (
            total_discrepancies / max(jobs_with_discrepancies, 1)
        ) if jobs_with_discrepancies else 0

        return DiscrepancyStats(
            top_discrepancies=top_discrepancies,
            fatal_four_frequency=fatal_four_frequency,
            severity_distribution=severity_distribution,
            discrepancy_trends=discrepancy_trends,
            total_discrepancies=total_discrepancies,
            avg_discrepancies_per_job=round(avg_discrepancies_per_job, 2),
            time_range=time_range,
            start_date=start,
            end_date=end
        )

    def get_trend_stats(self, user: User, time_range: TimeRange = "30d",
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> TrendStats:
        """Get trend analysis over time."""

        start, end = self._parse_time_range(time_range, start_date, end_date)

        # Generate daily timeline
        timeline = []
        current_date = start.date()
        end_date_only = end.date()

        while current_date <= end_date_only:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # Jobs query for this day
            day_jobs_query = self.db.query(ValidationSession).filter(
                ValidationSession.created_at.between(day_start, day_end)
            )

            # Apply role filtering
            if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
                day_jobs_query = day_jobs_query.filter(ValidationSession.user_id == user.id)

            # Get daily metrics
            jobs_submitted = day_jobs_query.count()
            jobs_completed = day_jobs_query.filter(ValidationSession.status == 'completed').count()
            jobs_rejected = day_jobs_query.filter(ValidationSession.status == 'failed').count()

            # Processing time for completed jobs
            processing_times = day_jobs_query.filter(
                and_(
                    ValidationSession.status == 'completed',
                    ValidationSession.processing_started_at.isnot(None),
                    ValidationSession.processing_completed_at.isnot(None)
                )
            ).with_entities(
                ValidationSession.processing_started_at,
                ValidationSession.processing_completed_at
            ).all()

            avg_processing_time = None
            if processing_times:
                total_minutes = sum(
                    (end_time - start_time).total_seconds() / 60
                    for start_time, end_time in processing_times
                    if start_time and end_time
                )
                avg_processing_time = total_minutes / len(processing_times)

            # Discrepancy count for this day
            discrepancy_query = self.db.query(Discrepancy).join(ValidationSession).filter(
                Discrepancy.created_at.between(day_start, day_end)
            )

            if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
                discrepancy_query = discrepancy_query.filter(ValidationSession.user_id == user.id)

            discrepancy_count = discrepancy_query.count()

            success_rate = (jobs_completed / max(jobs_submitted, 1)) * 100

            timeline.append(TrendPoint(
                date=current_date,
                jobs_submitted=jobs_submitted,
                jobs_completed=jobs_completed,
                jobs_rejected=jobs_rejected,
                avg_processing_time=round(avg_processing_time, 2) if avg_processing_time else None,
                discrepancy_count=discrepancy_count,
                success_rate=round(success_rate, 2)
            ))

            current_date += timedelta(days=1)

        # Calculate trend slopes (simple linear trend)
        def calculate_trend(values: List[float]) -> float:
            if len(values) < 2:
                return 0.0

            n = len(values)
            x_sum = sum(range(n))
            y_sum = sum(values)
            xy_sum = sum(i * y for i, y in enumerate(values))
            x_squared_sum = sum(i * i for i in range(n))

            denominator = n * x_squared_sum - x_sum * x_sum
            if denominator == 0:
                return 0.0

            slope = (n * xy_sum - x_sum * y_sum) / denominator
            return slope

        # Extract values for trend calculations
        job_volumes = [point.jobs_submitted for point in timeline]
        rejection_rates = [
            (point.jobs_rejected / max(point.jobs_submitted, 1)) * 100
            for point in timeline
        ]
        processing_times = [
            point.avg_processing_time for point in timeline
            if point.avg_processing_time is not None
        ]

        job_volume_trend = calculate_trend(job_volumes)
        rejection_rate_trend = calculate_trend(rejection_rates)
        processing_time_trend = calculate_trend(processing_times) if processing_times else 0.0

        return TrendStats(
            timeline=timeline,
            job_volume_trend=round(job_volume_trend, 4),
            rejection_rate_trend=round(rejection_rate_trend, 4),
            processing_time_trend=round(processing_time_trend, 4),
            time_range=time_range,
            start_date=start,
            end_date=end
        )

    def get_user_stats(self, target_user: User, requesting_user: User,
                      time_range: TimeRange = "30d",
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> UserStats:
        """Get statistics for a specific user."""

        # Verify requesting user has permission to view target user's stats
        if requesting_user.role not in [UserRole.ADMIN, UserRole.BANK]:
            if requesting_user.id != target_user.id:
                raise PermissionError("Cannot view other user's statistics")

        start, end = self._parse_time_range(time_range, start_date, end_date)

        # Job metrics
        user_jobs = self.db.query(ValidationSession).filter(
            and_(
                ValidationSession.user_id == target_user.id,
                ValidationSession.created_at.between(start, end)
            )
        )

        total_jobs = user_jobs.count()
        successful_jobs = user_jobs.filter(ValidationSession.status == 'completed').count()
        rejected_jobs = user_jobs.filter(ValidationSession.status == 'failed').count()
        pending_jobs = user_jobs.filter(
            ValidationSession.status.in_(['created', 'processing'])
        ).count()

        rejection_rate = (rejected_jobs / max(total_jobs, 1)) * 100

        # Processing time
        processing_query = user_jobs.filter(
            and_(
                ValidationSession.processing_started_at.isnot(None),
                ValidationSession.processing_completed_at.isnot(None)
            )
        )

        avg_processing_time = None
        if processing_query.count() > 0:
            processing_times = processing_query.with_entities(
                ValidationSession.processing_started_at,
                ValidationSession.processing_completed_at
            ).all()

            total_minutes = sum(
                (end_time - start_time).total_seconds() / 60
                for start_time, end_time in processing_times
                if start_time and end_time
            )
            avg_processing_time = total_minutes / len(processing_times)

        # Time to correction (from rejection to resubmission)
        # This is complex - simplified version
        avg_time_to_correction = None  # TODO: Implement based on audit logs

        # Activity patterns
        activity_by_hour = self.db.query(
            extract('hour', ValidationSession.created_at).label('hour'),
            func.count(ValidationSession.id).label('count')
        ).filter(
            and_(
                ValidationSession.user_id == target_user.id,
                ValidationSession.created_at.between(start, end)
            )
        ).group_by('hour').order_by(desc('count')).first()

        most_active_hour = int(activity_by_hour[0]) if activity_by_hour else None

        activity_by_day = self.db.query(
            extract('dow', ValidationSession.created_at).label('dow'),
            func.count(ValidationSession.id).label('count')
        ).filter(
            and_(
                ValidationSession.user_id == target_user.id,
                ValidationSession.created_at.between(start, end)
            )
        ).group_by('dow').order_by(desc('count')).first()

        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        most_active_day = day_names[int(activity_by_day[0])] if activity_by_day else None

        # Document count
        documents_uploaded = self.db.query(func.count(Document.id)).join(ValidationSession).filter(
            and_(
                ValidationSession.user_id == target_user.id,
                Document.created_at.between(start, end)
            )
        ).scalar() or 0

        # Recent activity
        last_job = user_jobs.order_by(desc(ValidationSession.created_at)).first()
        last_job_date = last_job.created_at if last_job else None

        # Jobs in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        jobs_last_30_days = self.db.query(ValidationSession).filter(
            and_(
                ValidationSession.user_id == target_user.id,
                ValidationSession.created_at >= thirty_days_ago
            )
        ).count()

        return UserStats(
            user_id=target_user.id,
            user_email=target_user.email,
            user_role=target_user.role,
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            rejected_jobs=rejected_jobs,
            pending_jobs=pending_jobs,
            rejection_rate=round(rejection_rate, 2),
            avg_processing_time_minutes=round(avg_processing_time, 2) if avg_processing_time else None,
            avg_time_to_correction_hours=avg_time_to_correction,
            most_active_day=most_active_day,
            most_active_hour=most_active_hour,
            documents_uploaded=documents_uploaded,
            last_job_date=last_job_date,
            jobs_last_30_days=jobs_last_30_days,
            time_range=time_range,
            start_date=start,
            end_date=end
        )

    def get_system_metrics(self, user: User, time_range: TimeRange = "30d",
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> SystemMetrics:
        """Get system-wide metrics (Bank/Admin only)."""

        if user.role not in [UserRole.BANK, UserRole.ADMIN]:
            raise PermissionError("System metrics require bank or admin role")

        start, end = self._parse_time_range(time_range, start_date, end_date)

        # Total system jobs
        total_system_jobs = self.db.query(ValidationSession).filter(
            ValidationSession.created_at.between(start, end)
        ).count()

        # Active users (users with jobs in the period)
        total_active_users = self.db.query(
            func.count(func.distinct(ValidationSession.user_id))
        ).filter(
            ValidationSession.created_at.between(start, end)
        ).scalar() or 0

        jobs_per_user_avg = total_system_jobs / max(total_active_users, 1)

        # System rejection rate
        rejected_jobs = self.db.query(ValidationSession).filter(
            and_(
                ValidationSession.created_at.between(start, end),
                ValidationSession.status == 'failed'
            )
        ).count()

        system_rejection_rate = (rejected_jobs / max(total_system_jobs, 1)) * 100

        # Average system processing time
        system_processing_query = self.db.query(ValidationSession).filter(
            and_(
                ValidationSession.created_at.between(start, end),
                ValidationSession.processing_started_at.isnot(None),
                ValidationSession.processing_completed_at.isnot(None)
            )
        )

        avg_system_processing_time = None
        if system_processing_query.count() > 0:
            processing_times = system_processing_query.with_entities(
                ValidationSession.processing_started_at,
                ValidationSession.processing_completed_at
            ).all()

            total_minutes = sum(
                (end_time - start_time).total_seconds() / 60
                for start_time, end_time in processing_times
                if start_time and end_time
            )
            avg_system_processing_time = total_minutes / len(processing_times)

        # Usage by role
        usage_by_role_query = self.db.query(
            User.role,
            func.count(ValidationSession.id).label('job_count')
        ).join(ValidationSession).filter(
            ValidationSession.created_at.between(start, end)
        ).group_by(User.role).all()

        usage_by_role = {role: count for role, count in usage_by_role_query}

        # Peak hours
        peak_hours_query = self.db.query(
            extract('hour', ValidationSession.created_at).label('hour'),
            func.count(ValidationSession.id).label('count')
        ).filter(
            ValidationSession.created_at.between(start, end)
        ).group_by('hour').order_by(desc('count')).limit(5).all()

        peak_hours = [
            {"hour": int(hour), "job_count": count}
            for hour, count in peak_hours_query
        ]

        # Peak days
        peak_days_query = self.db.query(
            extract('dow', ValidationSession.created_at).label('dow'),
            func.count(ValidationSession.id).label('count')
        ).filter(
            ValidationSession.created_at.between(start, end)
        ).group_by('dow').order_by(desc('count')).all()

        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        peak_days = [
            {"day": day_names[int(dow)], "job_count": count}
            for dow, count in peak_days_query
        ]

        # Document type analytics
        doc_type_query = self.db.query(
            Document.document_type,
            func.count(Document.id).label('count')
        ).join(ValidationSession).filter(
            ValidationSession.created_at.between(start, end)
        ).group_by(Document.document_type).order_by(desc('count')).all()

        most_common_document_types = [
            {"document_type": doc_type, "count": count}
            for doc_type, count in doc_type_query
        ]

        # Success rates by document type
        doc_success_rates = {}
        for doc_type, _ in doc_type_query:
            total_jobs_for_type = self.db.query(ValidationSession).join(Document).filter(
                and_(
                    Document.document_type == doc_type,
                    ValidationSession.created_at.between(start, end)
                )
            ).count()

            successful_jobs_for_type = self.db.query(ValidationSession).join(Document).filter(
                and_(
                    Document.document_type == doc_type,
                    ValidationSession.created_at.between(start, end),
                    ValidationSession.status == 'completed'
                )
            ).count()

            success_rate = (successful_jobs_for_type / max(total_jobs_for_type, 1)) * 100
            doc_success_rates[doc_type] = round(success_rate, 2)

        return SystemMetrics(
            total_system_jobs=total_system_jobs,
            total_active_users=total_active_users,
            jobs_per_user_avg=round(jobs_per_user_avg, 2),
            system_rejection_rate=round(system_rejection_rate, 2),
            avg_system_processing_time=round(avg_system_processing_time, 2) if avg_system_processing_time else None,
            usage_by_role=usage_by_role,
            peak_hours=peak_hours,
            peak_days=peak_days,
            most_common_document_types=most_common_document_types,
            document_processing_success_rates=doc_success_rates,
            time_range=time_range,
            start_date=start,
            end_date=end
        )

    def get_processing_time_breakdown(self, user: User, time_range: TimeRange = "30d",
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> ProcessingTimeBreakdown:
        """Get detailed processing time breakdown."""

        start, end = self._parse_time_range(time_range, start_date, end_date)

        # Base query with role filtering
        base_query = self.db.query(ValidationSession).filter(
            and_(
                ValidationSession.created_at.between(start, end),
                ValidationSession.processing_started_at.isnot(None),
                ValidationSession.processing_completed_at.isnot(None)
            )
        )

        if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
            base_query = base_query.filter(ValidationSession.user_id == user.id)

        # Get processing times
        sessions = base_query.all()

        if not sessions:
            return ProcessingTimeBreakdown(
                time_percentiles={"p50": 0, "p90": 0, "p95": 0, "p99": 0},
                by_document_type={}
            )

        # Calculate total processing times
        processing_times = []
        for session in sessions:
            if session.processing_started_at and session.processing_completed_at:
                delta = session.processing_completed_at - session.processing_started_at
                processing_times.append(delta.total_seconds())

        # Calculate percentiles
        processing_times.sort()
        n = len(processing_times)

        def percentile(p: float) -> float:
            if n == 0:
                return 0
            index = int(p * n)
            if index >= n:
                index = n - 1
            return processing_times[index]

        time_percentiles = {
            "p50": round(percentile(0.5), 2),
            "p90": round(percentile(0.9), 2),
            "p95": round(percentile(0.95), 2),
            "p99": round(percentile(0.99), 2)
        }

        # Average total time
        avg_total_time = sum(processing_times) / len(processing_times) if processing_times else 0

        # Processing time by document type
        by_document_type = {}

        for session in sessions:
            # Get documents for this session
            session_docs = self.db.query(Document).filter(
                Document.validation_session_id == session.id
            ).all()

            for doc in session_docs:
                if session.processing_started_at and session.processing_completed_at:
                    processing_time = (session.processing_completed_at - session.processing_started_at).total_seconds()

                    if doc.document_type not in by_document_type:
                        by_document_type[doc.document_type] = []
                    by_document_type[doc.document_type].append(processing_time)

        # Average by document type
        for doc_type in by_document_type:
            times = by_document_type[doc_type]
            by_document_type[doc_type] = round(sum(times) / len(times), 2) if times else 0

        return ProcessingTimeBreakdown(
            avg_total_time_seconds=round(avg_total_time, 2),
            time_percentiles=time_percentiles,
            by_document_type=by_document_type
        )

    def detect_anomalies(self, user: User, time_range: TimeRange = "7d") -> List[AnomalyAlert]:
        """Detect anomalies in user or system metrics."""

        if user.role not in [UserRole.BANK, UserRole.ADMIN]:
            return []  # Only bank/admin get anomaly alerts

        alerts = []
        start, end = self._parse_time_range(time_range)

        # Check rejection rate spike
        recent_rejection_rate = self._calculate_rejection_rate(start, end)
        historical_rejection_rate = self._calculate_rejection_rate(
            start - timedelta(days=30), start
        )

        if recent_rejection_rate > historical_rejection_rate * 1.5:  # 50% increase
            alerts.append(AnomalyAlert(
                alert_type="rejection_spike",
                severity="high" if recent_rejection_rate > historical_rejection_rate * 2 else "medium",
                message=f"Rejection rate increased by {((recent_rejection_rate / historical_rejection_rate) - 1) * 100:.1f}%",
                details={
                    "recent_rate": recent_rejection_rate,
                    "historical_rate": historical_rejection_rate
                },
                current_value=recent_rejection_rate,
                expected_value=historical_rejection_rate,
                threshold=historical_rejection_rate * 1.5,
                confidence=0.85,
                time_window=DateRange(start_date=start, end_date=end)
            ))

        return alerts

    def _calculate_rejection_rate(self, start: datetime, end: datetime) -> float:
        """Calculate rejection rate for a time period."""
        total_jobs = self.db.query(ValidationSession).filter(
            ValidationSession.created_at.between(start, end)
        ).count()

        rejected_jobs = self.db.query(ValidationSession).filter(
            and_(
                ValidationSession.created_at.between(start, end),
                ValidationSession.status == 'failed'
            )
        ).count()

        return (rejected_jobs / max(total_jobs, 1)) * 100