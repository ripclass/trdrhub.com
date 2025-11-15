"""
Billing service layer for LCopilot billing and quota management.

This service handles:
- Usage tracking and cost calculation
- Quota enforcement
- Invoice generation and management
- Subscription management
- Usage analytics
"""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError

from ..models import (
    Company, User, ValidationSession, UsageRecord, Invoice,
    PlanType, CompanyStatus, InvoiceStatus, Currency
)
from ..core.pricing import (
    calculate_cost, get_plan_quotas, calculate_subscription_cost,
    calculate_overage_cost, get_billing_period_dates, BillingAction,
    SUBSCRIPTION_PLANS
)
from ..database import get_db
from ..models.audit_log import AuditLog, AuditAction, AuditResult


class QuotaExceededException(Exception):
    """Raised when a company exceeds its usage quota."""
    def __init__(self, message: str, current_usage: int, quota_limit: int):
        super().__init__(message)
        self.current_usage = current_usage
        self.quota_limit = quota_limit


class BillingServiceError(Exception):
    """Base exception for billing service errors."""
    pass


class BillingService:
    """Core billing service for usage tracking, quota enforcement, and invoicing."""

    def __init__(self, db: Session):
        self.db = db

    def record_usage(
        self,
        company_id: uuid.UUID,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        units: int = 1,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """
        Record a billable usage event and calculate cost.

        Args:
            company_id: Company performing the action
            action: Type of action (validate, recheck, etc.)
            user_id: User performing the action
            session_id: Validation session ID (if applicable)
            units: Number of units consumed (default 1)
            description: Human-readable description
            metadata: Additional context data

        Returns:
            Created UsageRecord

        Raises:
            BillingServiceError: If cost calculation fails
        """
        try:
            # Get company for cost calculation
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise BillingServiceError(f"Company {company_id} not found")

            # Calculate session history for recheck logic
            session_history = {}
            if action == BillingAction.RECHECK and session_id:
                recheck_count = self.db.query(UsageRecord).filter(
                    and_(
                        UsageRecord.session_id == session_id,
                        UsageRecord.action == BillingAction.RECHECK
                    )
                ).count()
                session_history["recheck_count"] = recheck_count

            # Calculate cost for this action
            cost = calculate_cost(
                action=action,
                company_plan=company.plan.value,
                job_metadata=metadata,
                user_id=str(user_id) if user_id else None,
                session_history=session_history
            )

            # Create usage record
            usage_record = UsageRecord(
                company_id=company_id,
                session_id=session_id,
                action=action,
                units=units,
                cost=cost * Decimal(str(units)),
                user_id=user_id,
                description=description,
                metadata=metadata
            )

            self.db.add(usage_record)
            self.db.commit()
            self.db.refresh(usage_record)

            # Create audit log entry
            self._create_audit_log(
                action=AuditAction.CREATE_USER,  # We need a BILLING_RECORD action
                user_id=user_id,
                resource_type="usage_record",
                resource_id=str(usage_record.id),
                details={
                    "company_id": str(company_id),
                    "billing_action": action,
                    "cost": float(cost),
                    "units": units
                }
            )

            return usage_record

        except Exception as e:
            self.db.rollback()
            raise BillingServiceError(f"Failed to record usage: {str(e)}")

    def get_usage(
        self,
        company_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        action: Optional[str] = None,
        billed: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a company within a date range.

        Args:
            company_id: Company ID
            start_date: Start of date range (default: current month start)
            end_date: End of date range (default: current month end)
            action: Filter by specific action type
            billed: Filter by billing status

        Returns:
            Dict with usage statistics and breakdown
        """
        if start_date is None:
            start_date = date.today().replace(day=1)
        if end_date is None:
            # Last day of current month
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)

        # Build query filters
        filters = [
            UsageRecord.company_id == company_id,
            func.date(UsageRecord.timestamp) >= start_date,
            func.date(UsageRecord.timestamp) <= end_date
        ]

        if action:
            filters.append(UsageRecord.action == action)
        if billed is not None:
            filters.append(UsageRecord.billed == billed)

        # Get usage records
        usage_records = self.db.query(UsageRecord).filter(and_(*filters)).all()

        # Calculate totals
        total_cost = sum(record.cost for record in usage_records)
        total_units = sum(record.units for record in usage_records)

        # Group by action
        action_breakdown = {}
        for record in usage_records:
            if record.action not in action_breakdown:
                action_breakdown[record.action] = {
                    "count": 0,
                    "units": 0,
                    "cost": Decimal("0.00"),
                    "records": []
                }

            action_breakdown[record.action]["count"] += 1
            action_breakdown[record.action]["units"] += record.units
            action_breakdown[record.action]["cost"] += record.cost
            action_breakdown[record.action]["records"].append({
                "id": str(record.id),
                "timestamp": record.timestamp.isoformat(),
                "units": record.units,
                "cost": float(record.cost),
                "description": record.description
            })

        return {
            "company_id": str(company_id),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "totals": {
                "records_count": len(usage_records),
                "total_units": total_units,
                "total_cost": float(total_cost),
                "average_cost_per_unit": float(total_cost / total_units) if total_units > 0 else 0.0
            },
            "breakdown_by_action": {
                action: {
                    "count": data["count"],
                    "units": data["units"],
                    "cost": float(data["cost"]),
                    "average_cost": float(data["cost"] / data["units"]) if data["units"] > 0 else 0.0
                }
                for action, data in action_breakdown.items()
            },
            "records": [
                {
                    "id": str(record.id),
                    "action": record.action,
                    "timestamp": record.timestamp.isoformat(),
                    "units": record.units,
                    "cost": float(record.cost),
                    "description": record.description,
                    "billed": record.billed
                }
                for record in usage_records
            ]
        }

    def enforce_quota(self, company_id: uuid.UUID, action: str) -> bool:
        """
        Check if company can perform an action without exceeding quota.

        Args:
            company_id: Company ID
            action: Action to check

        Returns:
            True if action is allowed

        Raises:
            QuotaExceededException: If quota would be exceeded
        """
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise BillingServiceError(f"Company {company_id} not found")

        # Companies with unlimited quota (enterprise) always pass
        if not company.has_quota_limit:
            return True

        # Pay-per-check companies have no enforced quotas (they pay per use)
        if company.is_pay_per_check:
            return True

        # Get current billing period
        if company.billing_cycle_start:
            period_start, period_end = get_billing_period_dates(
                "monthly", company.billing_cycle_start
            )
        else:
            # Default to current month
            period_start = date.today().replace(day=1)
            period_end = date.today()

        # Count current usage in this billing cycle
        current_usage = self.db.query(func.count(UsageRecord.id)).filter(
            and_(
                UsageRecord.company_id == company_id,
                UsageRecord.action == action,
                func.date(UsageRecord.timestamp) >= period_start,
                func.date(UsageRecord.timestamp) <= period_end
            )
        ).scalar() or 0

        # Get plan quotas
        plan_quotas = get_plan_quotas(company.plan.value)
        action_quota = plan_quotas.get(action, 0)

        # Check if adding this action would exceed quota
        if current_usage >= action_quota:
            raise QuotaExceededException(
                f"Company {company.name} has exceeded {action} quota ({current_usage}/{action_quota})",
                current_usage=current_usage,
                quota_limit=action_quota
            )

        return True

    def get_quota_status(self, company_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get current quota usage status for a company.

        Returns:
            Dict with quota status for all actions
        """
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise BillingServiceError(f"Company {company_id} not found")

        if not company.has_quota_limit:
            return {
                "company_id": str(company_id),
                "plan": company.plan.value,
                "has_quota_limit": False,
                "quotas": {},
                "message": "Unlimited usage"
            }

        # Get current billing period
        if company.billing_cycle_start:
            period_start, period_end = get_billing_period_dates(
                "monthly", company.billing_cycle_start
            )
        else:
            period_start = date.today().replace(day=1)
            period_end = date.today()

        # Get plan quotas
        plan_quotas = get_plan_quotas(company.plan.value)
        quota_status = {}

        for action, quota_limit in plan_quotas.items():
            current_usage = self.db.query(func.count(UsageRecord.id)).filter(
                and_(
                    UsageRecord.company_id == company_id,
                    UsageRecord.action == action,
                    func.date(UsageRecord.timestamp) >= period_start,
                    func.date(UsageRecord.timestamp) <= period_end
                )
            ).scalar() or 0

            quota_status[action] = {
                "used": current_usage,
                "limit": quota_limit,
                "remaining": max(0, quota_limit - current_usage),
                "percentage_used": (current_usage / quota_limit * 100) if quota_limit > 0 else 0,
                "is_exceeded": current_usage >= quota_limit
            }

        return {
            "company_id": str(company_id),
            "plan": company.plan.value,
            "has_quota_limit": True,
            "billing_period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "quotas": quota_status
        }

    def generate_invoice(
        self,
        company_id: uuid.UUID,
        period_start: date,
        period_end: date,
        description: Optional[str] = None
    ) -> Invoice:
        """
        Generate an invoice for a company's usage in a billing period.

        Args:
            company_id: Company ID
            period_start: Start of billing period
            period_end: End of billing period
            description: Optional invoice description

        Returns:
            Created Invoice

        Raises:
            BillingServiceError: If invoice generation fails
        """
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise BillingServiceError(f"Company {company_id} not found")

            # Get unbilled usage records for this period
            unbilled_records = self.db.query(UsageRecord).filter(
                and_(
                    UsageRecord.company_id == company_id,
                    UsageRecord.billed == False,
                    func.date(UsageRecord.timestamp) >= period_start,
                    func.date(UsageRecord.timestamp) <= period_end
                )
            ).all()

            if not unbilled_records and not company.is_subscription_plan:
                raise BillingServiceError("No unbilled usage found for period")

            # Calculate invoice amount
            usage_amount = sum(record.cost for record in unbilled_records)
            subscription_amount = Decimal("0.00")

            if company.is_subscription_plan:
                subscription_amount = calculate_subscription_cost(company.plan.value)

            total_amount = usage_amount + subscription_amount

            # Generate invoice number
            invoice_number = Invoice.generate_invoice_number(str(company_id))

            # Create invoice
            invoice = Invoice(
                company_id=company_id,
                invoice_number=invoice_number,
                amount=total_amount,
                currency=Currency.BDT,
                period_start=period_start,
                period_end=period_end,
                description=description or f"Billing for {period_start.strftime('%B %Y')}",
                due_date=date.today() + timedelta(days=30)  # 30 days to pay
            )

            # Add line items to metadata
            if company.is_subscription_plan and subscription_amount > 0:
                invoice.add_line_item(
                    description=f"{company.get_plan_display()} Subscription",
                    quantity=1,
                    unit_price=subscription_amount,
                    total=subscription_amount
                )

            # Group usage by action type for line items
            usage_by_action = {}
            for record in unbilled_records:
                if record.action not in usage_by_action:
                    usage_by_action[record.action] = {
                        "units": 0,
                        "cost": Decimal("0.00")
                    }
                usage_by_action[record.action]["units"] += record.units
                usage_by_action[record.action]["cost"] += record.cost

            for action, data in usage_by_action.items():
                if data["cost"] > 0:
                    unit_price = data["cost"] / data["units"] if data["units"] > 0 else Decimal("0.00")
                    invoice.add_line_item(
                        description=f"{action.replace('_', ' ').title()} ({data['units']} units)",
                        quantity=data["units"],
                        unit_price=unit_price,
                        total=data["cost"]
                    )

            self.db.add(invoice)
            self.db.flush()  # Get invoice ID

            # Mark usage records as billed
            for record in unbilled_records:
                record.mark_as_billed(invoice.id)

            self.db.commit()
            self.db.refresh(invoice)

            # Create audit log
            self._create_audit_log(
                action=AuditAction.CREATE_USER,  # Need INVOICE_GENERATED action
                user_id=None,
                resource_type="invoice",
                resource_id=str(invoice.id),
                details={
                    "company_id": str(company_id),
                    "amount": float(total_amount),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "usage_records_count": len(unbilled_records)
                }
            )

            return invoice

        except Exception as e:
            self.db.rollback()
            raise BillingServiceError(f"Failed to generate invoice: {str(e)}")

    def mark_invoice_paid(
        self,
        invoice_id: uuid.UUID,
        transaction_id: str,
        payment_method: Optional[str] = None
    ) -> Invoice:
        """
        Mark an invoice as paid and update payment details.

        Args:
            invoice_id: Invoice ID
            transaction_id: External payment provider transaction ID
            payment_method: Payment method used

        Returns:
            Updated Invoice

        Raises:
            BillingServiceError: If invoice not found or already paid
        """
        try:
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                raise BillingServiceError(f"Invoice {invoice_id} not found")

            if invoice.is_paid:
                raise BillingServiceError(f"Invoice {invoice_id} is already paid")

            invoice.mark_as_paid(transaction_id, payment_method)
            self.db.commit()
            self.db.refresh(invoice)

            # Create audit log
            self._create_audit_log(
                action=AuditAction.CREATE_USER,  # Need INVOICE_PAID action
                user_id=None,
                resource_type="invoice",
                resource_id=str(invoice_id),
                details={
                    "transaction_id": transaction_id,
                    "payment_method": payment_method,
                    "amount": float(invoice.amount)
                }
            )

            return invoice

        except Exception as e:
            self.db.rollback()
            raise BillingServiceError(f"Failed to mark invoice as paid: {str(e)}")

    def get_company_invoices(
        self,
        company_id: uuid.UUID,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Invoice]:
        """Get invoices for a company with optional filtering."""
        query = self.db.query(Invoice).filter(Invoice.company_id == company_id)

        if status:
            query = query.filter(Invoice.status == status)

        return query.order_by(desc(Invoice.created_at)).limit(limit).offset(offset).all()

    def change_company_plan(
        self,
        company_id: uuid.UUID,
        new_plan: str,
        effective_date: Optional[date] = None,
        admin_user_id: Optional[uuid.UUID] = None
    ) -> Company:
        """
        Change a company's billing plan.

        Args:
            company_id: Company ID
            new_plan: New plan name
            effective_date: When the change takes effect (default: today)
            admin_user_id: Admin user making the change

        Returns:
            Updated Company

        Raises:
            BillingServiceError: If plan change fails
        """
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise BillingServiceError(f"Company {company_id} not found")

            if new_plan not in [plan.value for plan in PlanType]:
                raise BillingServiceError(f"Invalid plan: {new_plan}")

            old_plan = company.plan.value
            effective_date = effective_date or date.today()

            # Update company plan
            company.plan = PlanType(new_plan)

            # Set quota limit based on new plan
            if new_plan in SUBSCRIPTION_PLANS:
                plan_config = SUBSCRIPTION_PLANS[new_plan]
                company.quota_limit = plan_config.quota_limit

            # Update billing cycle start for subscription plans
            if company.is_subscription_plan and not company.billing_cycle_start:
                company.billing_cycle_start = effective_date

            self.db.commit()
            self.db.refresh(company)

            # Create audit log
            self._create_audit_log(
                action=AuditAction.ROLE_CHANGE,  # Could be PLAN_CHANGE
                user_id=admin_user_id,
                resource_type="company",
                resource_id=str(company_id),
                details={
                    "old_plan": old_plan,
                    "new_plan": new_plan,
                    "effective_date": effective_date.isoformat(),
                    "quota_limit": company.quota_limit
                }
            )

            return company

        except Exception as e:
            self.db.rollback()
            raise BillingServiceError(f"Failed to change company plan: {str(e)}")

    def get_billing_analytics(
        self,
        company_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get billing analytics for a company or system-wide.

        Args:
            company_id: Specific company (None for system-wide)
            start_date: Analysis start date
            end_date: Analysis end date

        Returns:
            Dict with billing analytics
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()

        # Build base query
        usage_query = self.db.query(UsageRecord)
        invoice_query = self.db.query(Invoice)

        if company_id:
            usage_query = usage_query.filter(UsageRecord.company_id == company_id)
            invoice_query = invoice_query.filter(Invoice.company_id == company_id)

        # Filter by date range
        usage_query = usage_query.filter(
            func.date(UsageRecord.timestamp).between(start_date, end_date)
        )
        invoice_query = invoice_query.filter(
            func.date(Invoice.created_at).between(start_date, end_date)
        )

        # Calculate usage metrics
        usage_records = usage_query.all()
        total_usage_cost = sum(record.cost for record in usage_records)
        total_usage_units = sum(record.units for record in usage_records)

        # Calculate invoice metrics
        invoices = invoice_query.all()
        total_invoiced = sum(invoice.amount for invoice in invoices)
        paid_invoices = [inv for inv in invoices if inv.is_paid]
        total_paid = sum(invoice.amount for invoice in paid_invoices)

        # Usage by action
        usage_by_action = {}
        for record in usage_records:
            if record.action not in usage_by_action:
                usage_by_action[record.action] = {"units": 0, "cost": Decimal("0.00")}
            usage_by_action[record.action]["units"] += record.units
            usage_by_action[record.action]["cost"] += record.cost

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "company_id": str(company_id) if company_id else None,
            "usage_metrics": {
                "total_records": len(usage_records),
                "total_units": total_usage_units,
                "total_cost": float(total_usage_cost),
                "by_action": {
                    action: {
                        "units": data["units"],
                        "cost": float(data["cost"])
                    }
                    for action, data in usage_by_action.items()
                }
            },
            "invoice_metrics": {
                "total_invoices": len(invoices),
                "total_invoiced": float(total_invoiced),
                "paid_invoices": len(paid_invoices),
                "total_paid": float(total_paid),
                "collection_rate": float(total_paid / total_invoiced * 100) if total_invoiced > 0 else 0.0
            }
        }

    def _create_audit_log(
        self,
        action: AuditAction,
        user_id: Optional[uuid.UUID],
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Create an audit log entry for billing actions."""
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=AuditResult.SUCCESS,
            details=details or {},
            ip_address="internal",  # Internal system action
            user_agent="billing_service"
        )
        self.db.add(audit_entry)


    def get_company_billing_info(self, company_id: uuid.UUID) -> Dict[str, Any]:
        """Get company billing information for API response."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise BillingServiceError(f"Company {company_id} not found")

        quota_status = self.get_quota_status(company_id)
        total_usage = sum(q["used"] for q in quota_status.get("quotas", {}).values())

        return {
            "id": company.id,
            "name": company.name,
            "plan": company.plan,
            "quota_limit": company.quota_limit,
            "quota_used": total_usage,
            "quota_remaining": company.quota_limit - total_usage if company.quota_limit else None,
            "billing_email": company.billing_email,
            "payment_customer_id": company.payment_customer_id
        }

    def update_company_billing(self, company_id: uuid.UUID, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update company billing settings."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise BillingServiceError(f"Company {company_id} not found")

        for key, value in update_data.items():
            if hasattr(company, key):
                setattr(company, key, value)

        self.db.commit()
        self.db.refresh(company)

        return self.get_company_billing_info(company_id)

    def get_usage_stats(self, company_id: uuid.UUID) -> Dict[str, Any]:
        """Get usage statistics for company."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise BillingServiceError(f"Company {company_id} not found")

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Get current usage
        today_usage = self.db.query(func.count(UsageRecord.id)).filter(
            and_(
                UsageRecord.company_id == company_id,
                func.date(UsageRecord.timestamp) == today
            )
        ).scalar() or 0

        week_usage = self.db.query(func.count(UsageRecord.id)).filter(
            and_(
                UsageRecord.company_id == company_id,
                func.date(UsageRecord.timestamp) >= week_start
            )
        ).scalar() or 0

        month_usage = self.db.query(func.count(UsageRecord.id)).filter(
            and_(
                UsageRecord.company_id == company_id,
                func.date(UsageRecord.timestamp) >= month_start
            )
        ).scalar() or 0

        total_usage = self.db.query(func.count(UsageRecord.id)).filter(
            UsageRecord.company_id == company_id
        ).scalar() or 0

        total_cost = self.db.query(func.sum(UsageRecord.cost)).filter(
            UsageRecord.company_id == company_id
        ).scalar() or Decimal("0.00")

        return {
            "company_id": company_id,
            "current_month": month_usage,
            "current_week": week_usage,
            "today": today_usage,
            "total_usage": total_usage,
            "total_cost": total_cost,
            "quota_limit": company.quota_limit,
            "quota_used": month_usage,  # Using monthly usage for quota
            "quota_remaining": company.quota_limit - month_usage if company.quota_limit else None
        }

    def get_usage_records(
        self,
        company_id: uuid.UUID,
        page: int = 1,
        per_page: int = 50,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        action: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated usage records."""
        query = self.db.query(UsageRecord).filter(UsageRecord.company_id == company_id)

        if start_date:
            query = query.filter(func.date(UsageRecord.timestamp) >= start_date)
        if end_date:
            query = query.filter(func.date(UsageRecord.timestamp) <= end_date)
        if action:
            query = query.filter(UsageRecord.action == action)

        total = query.count()
        records = query.order_by(desc(UsageRecord.timestamp)).offset((page - 1) * per_page).limit(per_page).all()

        return {
            "records": records,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }

    def get_invoices(
        self,
        company_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated invoices."""
        query = self.db.query(Invoice).filter(Invoice.company_id == company_id)

        if status:
            try:
                status_enum = InvoiceStatus(status.lower())
            except ValueError:
                raise BillingServiceError(f"Unsupported invoice status: {status}")
            query = query.filter(Invoice.status == status_enum)

        total = query.count()
        invoices = query.order_by(desc(Invoice.created_at)).offset((page - 1) * per_page).limit(per_page).all()

        return {
            "invoices": invoices,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }

    def get_invoice(self, invoice_id: uuid.UUID, company_id: uuid.UUID) -> Optional[Invoice]:
        """Get specific invoice."""
        return self.db.query(Invoice).filter(
            and_(Invoice.id == invoice_id, Invoice.company_id == company_id)
        ).first()

    def update_invoice_payment_intent(self, invoice_id: uuid.UUID, payment_intent_id: str):
        """Update invoice with payment intent ID."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.payment_intent_id = payment_intent_id
            self.db.commit()

    def process_payment_webhook(self, webhook_event):
        """Process payment webhook event."""
        # Find invoice by payment intent ID
        if webhook_event.payment_id:
            invoice = self.db.query(Invoice).filter(
                Invoice.payment_intent_id == webhook_event.payment_id
            ).first()

            if invoice and webhook_event.status and webhook_event.status.value == "SUCCESS":
                self.mark_invoice_paid(
                    invoice.id,
                    webhook_event.transaction_id or webhook_event.payment_id,
                    "online_payment"
                )

    def get_admin_company_stats(self, page: int = 1, per_page: int = 50) -> List[Dict[str, Any]]:
        """Get company statistics for admin users."""
        companies = self.db.query(Company).offset((page - 1) * per_page).limit(per_page).all()

        stats = []
        for company in companies:
            usage_stats = self.get_usage_stats(company.id)

            # Get last activity
            last_record = self.db.query(UsageRecord).filter(
                UsageRecord.company_id == company.id
            ).order_by(desc(UsageRecord.timestamp)).first()

            stats.append({
                "company_id": company.id,
                "company_name": company.name,
                "plan": company.plan,
                "total_usage": usage_stats["total_usage"],
                "total_cost": usage_stats["total_cost"],
                "quota_limit": company.quota_limit,
                "quota_used": usage_stats["quota_used"],
                "last_activity": last_record.timestamp if last_record else None,
                "status": company.status.value if company.status else "active"
            })

        return stats

    def get_admin_usage_report(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get usage report for admin users."""
        # Get all companies with usage in period
        companies_query = self.db.query(Company).join(UsageRecord).filter(
            func.date(UsageRecord.timestamp).between(start_date, end_date)
        ).distinct()

        companies = companies_query.all()
        total_usage = 0
        total_revenue = Decimal("0.00")
        company_stats = []

        for company in companies:
            usage_count = self.db.query(func.count(UsageRecord.id)).filter(
                and_(
                    UsageRecord.company_id == company.id,
                    func.date(UsageRecord.timestamp).between(start_date, end_date)
                )
            ).scalar() or 0

            usage_cost = self.db.query(func.sum(UsageRecord.cost)).filter(
                and_(
                    UsageRecord.company_id == company.id,
                    func.date(UsageRecord.timestamp).between(start_date, end_date)
                )
            ).scalar() or Decimal("0.00")

            total_usage += usage_count
            total_revenue += usage_cost

            last_record = self.db.query(UsageRecord).filter(
                and_(
                    UsageRecord.company_id == company.id,
                    func.date(UsageRecord.timestamp).between(start_date, end_date)
                )
            ).order_by(desc(UsageRecord.timestamp)).first()

            company_stats.append({
                "company_id": company.id,
                "company_name": company.name,
                "plan": company.plan,
                "total_usage": usage_count,
                "total_cost": usage_cost,
                "quota_limit": company.quota_limit,
                "quota_used": usage_count,
                "last_activity": last_record.timestamp if last_record else None,
                "status": company.status.value if company.status else "active"
            })

        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_companies": len(companies),
            "total_usage": total_usage,
            "total_revenue": total_revenue,
            "companies": company_stats
        }


def get_billing_service(db: Session = None) -> BillingService:
    """Factory function to get a BillingService instance."""
    if db is None:
        db = next(get_db())
    return BillingService(db)