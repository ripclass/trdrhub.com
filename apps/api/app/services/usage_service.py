"""
Hub Usage Tracking Service

Core service for tracking all billable operations across TRDR Hub tools.
Handles:
- Recording usage events (LC validations, price checks, etc.)
- Checking plan limits before operations
- Calculating overage charges
- Providing usage statistics

Usage:
    from app.services.usage_service import UsageService
    
    # Check if user can perform operation
    can_proceed, message = await usage_service.check_limit(company_id, "lc_validation")
    
    # Record usage after operation completes
    await usage_service.record_usage(company_id, user_id, "lc_validation", quantity=1)
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple, List
from uuid import UUID

from sqlalchemy import select, func, and_, extract
from sqlalchemy.orm import Session

from app.models.hub import (
    HubPlan, HubSubscription, HubUsage, HubUsageLog,
    Tool, ToolOperation, OPERATION_TO_FIELD
)
from app.models import Company

logger = logging.getLogger(__name__)


class UsageService:
    """Service for tracking and managing usage across all tools."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # USAGE RECORDING
    # =========================================================================
    
    async def record_usage(
        self,
        company_id: UUID,
        user_id: Optional[UUID],
        operation: str,
        tool: str,
        quantity: int = 1,
        log_data: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Decimal]]:
        """
        Record a usage event and update monthly counters.
        
        Args:
            company_id: The company performing the operation
            user_id: The user performing the operation (optional)
            operation: Type of operation (lc_validation, price_check, etc.)
            tool: Tool being used (lcopilot, price_verify, etc.)
            quantity: Number of operations (default 1)
            log_data: Additional context for audit trail
            description: Human-readable description
            
        Returns:
            Tuple of (success, message, overage_cost)
        """
        try:
            # Get current subscription and plan
            subscription = await self._get_active_subscription(company_id)
            if not subscription:
                # No subscription = pay-as-you-go
                plan = await self._get_plan("payg")
            else:
                plan = subscription.plan
            
            # Get or create monthly usage record
            usage = await self._get_or_create_monthly_usage(company_id, subscription)
            
            # Check if this is overage
            is_overage, overage_cost = await self._calculate_overage(
                usage, plan, operation, quantity
            )
            
            # Update usage counters
            field_name = OPERATION_TO_FIELD.get(operation)
            if field_name:
                # Update main counter
                current = getattr(usage, field_name, 0) or 0
                setattr(usage, field_name, current + quantity)
                
                # Update overage counter if applicable
                if is_overage:
                    overage_field = f"{field_name.replace('_used', '')}_overage"
                    if hasattr(usage, overage_field):
                        current_overage = getattr(usage, overage_field, 0) or 0
                        setattr(usage, overage_field, current_overage + quantity)
                    usage.overage_charges = (usage.overage_charges or Decimal("0")) + overage_cost
            
            # Create audit log entry
            log_entry = HubUsageLog(
                company_id=company_id,
                user_id=user_id,
                operation=operation,
                tool=tool,
                quantity=quantity,
                unit_cost=overage_cost / quantity if is_overage and quantity > 0 else None,
                is_overage=is_overage,
                log_data=log_data,
                description=description or f"{operation} x{quantity}"
            )
            self.db.add(log_entry)
            
            self.db.commit()
            
            message = f"Recorded {quantity} {operation}(s)"
            if is_overage:
                message += f" (overage: ${overage_cost:.2f})"
            
            logger.info(f"Usage recorded: company={company_id}, op={operation}, qty={quantity}, overage={is_overage}")
            return True, message, overage_cost if is_overage else None
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record usage: {e}")
            return False, str(e), None
    
    # =========================================================================
    # LIMIT CHECKING
    # =========================================================================
    
    async def check_limit(
        self,
        company_id: UUID,
        operation: str,
        quantity: int = 1
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if company can perform an operation (within limits or pay overage).
        
        For subscription plans: Check against monthly limits
        For PAYG: Always allowed (will be charged per-use)
        
        Returns:
            Tuple of (can_proceed, message, usage_info)
        """
        try:
            subscription = await self._get_active_subscription(company_id)
            
            if not subscription:
                # Pay-as-you-go - always allowed, will be charged
                plan = await self._get_plan("payg")
                return True, "Pay-as-you-go: Operation will be charged", {
                    "plan": "payg",
                    "cost_per_unit": self._get_operation_cost(plan, operation),
                    "is_overage": True
                }
            
            plan = subscription.plan
            usage = await self._get_or_create_monthly_usage(company_id, subscription)
            
            # Get limit and current usage
            limit = self._get_operation_limit(plan, operation)
            current = self._get_current_usage(usage, operation)
            remaining = max(0, limit - current) if limit else float('inf')
            
            # Check if within limit
            if limit == 0:
                # Unlimited
                return True, "Unlimited operations on your plan", {
                    "plan": plan.slug,
                    "limit": "unlimited",
                    "used": current,
                    "remaining": "unlimited"
                }
            elif remaining >= quantity:
                # Within limit
                return True, f"{remaining} remaining this month", {
                    "plan": plan.slug,
                    "limit": limit,
                    "used": current,
                    "remaining": remaining
                }
            else:
                # Will incur overage
                overage_rate = self._get_operation_cost(plan, operation)
                overage_qty = quantity - remaining
                overage_cost = overage_qty * overage_rate
                
                return True, f"Overage: {overage_qty} operations @ ${overage_rate}/each = ${overage_cost:.2f}", {
                    "plan": plan.slug,
                    "limit": limit,
                    "used": current,
                    "remaining": remaining,
                    "overage_quantity": overage_qty,
                    "overage_cost": float(overage_cost)
                }
                
        except Exception as e:
            logger.error(f"Failed to check limit: {e}")
            return False, str(e), {}
    
    async def get_remaining_limits(self, company_id: UUID) -> Dict[str, Any]:
        """Get remaining limits for all operations."""
        try:
            subscription = await self._get_active_subscription(company_id)
            
            if not subscription:
                plan = await self._get_plan("payg")
                return {
                    "plan": "payg",
                    "plan_name": "Pay-as-you-go",
                    "limits": {
                        "lc_validations": {"limit": "pay-per-use", "used": 0, "remaining": "unlimited"},
                        "price_checks": {"limit": "pay-per-use", "used": 0, "remaining": "unlimited"},
                        "hs_lookups": {"limit": "pay-per-use", "used": 0, "remaining": "unlimited"},
                        "sanctions_screens": {"limit": "pay-per-use", "used": 0, "remaining": "unlimited"},
                        "container_tracks": {"limit": "pay-per-use", "used": 0, "remaining": "unlimited"},
                    }
                }
            
            plan = subscription.plan
            usage = await self._get_or_create_monthly_usage(company_id, subscription)
            limits = plan.limits or {}
            
            result = {
                "plan": plan.slug,
                "plan_name": plan.name,
                "period_start": usage.period_start.isoformat() if usage.period_start else None,
                "period_end": usage.period_end.isoformat() if usage.period_end else None,
                "limits": {}
            }
            
            for op_type in ["lc_validations", "price_checks", "hs_lookups", "sanctions_screens", "container_tracks"]:
                limit = limits.get(op_type, 0)
                field = f"{op_type}_used"
                used = getattr(usage, field, 0) or 0
                
                if limit == 0:
                    result["limits"][op_type] = {
                        "limit": "unlimited",
                        "used": used,
                        "remaining": "unlimited"
                    }
                else:
                    result["limits"][op_type] = {
                        "limit": limit,
                        "used": used,
                        "remaining": max(0, limit - used)
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get remaining limits: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # USAGE STATISTICS
    # =========================================================================
    
    async def get_current_usage(self, company_id: UUID) -> Dict[str, Any]:
        """Get current month's usage summary."""
        try:
            subscription = await self._get_active_subscription(company_id)
            usage = await self._get_or_create_monthly_usage(
                company_id, subscription
            )
            
            return {
                "period": {
                    "start": usage.period_start.isoformat() if usage.period_start else None,
                    "end": usage.period_end.isoformat() if usage.period_end else None,
                },
                "usage": {
                    "lc_validations": usage.lc_validations_used or 0,
                    "price_checks": usage.price_checks_used or 0,
                    "hs_lookups": usage.hs_lookups_used or 0,
                    "sanctions_screens": usage.sanctions_screens_used or 0,
                    "container_tracks": usage.container_tracks_used or 0,
                },
                "overage": {
                    "lc_validations": usage.lc_validations_overage or 0,
                    "price_checks": usage.price_checks_overage or 0,
                    "hs_lookups": usage.hs_lookups_overage or 0,
                    "sanctions_screens": usage.sanctions_screens_overage or 0,
                    "container_tracks": usage.container_tracks_overage or 0,
                    "total_charges": float(usage.overage_charges or 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return {"error": str(e)}
    
    async def get_usage_history(
        self,
        company_id: UUID,
        months: int = 6
    ) -> List[Dict[str, Any]]:
        """Get usage history for past N months."""
        try:
            query = select(HubUsage).where(
                HubUsage.company_id == company_id
            ).order_by(HubUsage.period_start.desc()).limit(months)
            
            result = self.db.execute(query)
            records = result.scalars().all()
            
            return [
                {
                    "period_start": r.period_start.isoformat() if r.period_start else None,
                    "period_end": r.period_end.isoformat() if r.period_end else None,
                    "usage": {
                        "lc_validations": r.lc_validations_used or 0,
                        "price_checks": r.price_checks_used or 0,
                        "hs_lookups": r.hs_lookups_used or 0,
                        "sanctions_screens": r.sanctions_screens_used or 0,
                        "container_tracks": r.container_tracks_used or 0,
                    },
                    "overage_charges": float(r.overage_charges or 0)
                }
                for r in records
            ]
            
        except Exception as e:
            logger.error(f"Failed to get usage history: {e}")
            return []
    
    async def get_usage_logs(
        self,
        company_id: UUID,
        limit: int = 50,
        offset: int = 0,
        tool: Optional[str] = None,
        operation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed usage log entries."""
        try:
            query = select(HubUsageLog).where(
                HubUsageLog.company_id == company_id
            )
            
            if tool:
                query = query.where(HubUsageLog.tool == tool)
            if operation:
                query = query.where(HubUsageLog.operation == operation)
            
            query = query.order_by(HubUsageLog.created_at.desc()).offset(offset).limit(limit)
            
            result = self.db.execute(query)
            logs = result.scalars().all()
            
            return [
                {
                    "id": str(log.id),
                    "operation": log.operation,
                    "tool": log.tool,
                    "quantity": log.quantity,
                    "is_overage": log.is_overage,
                    "unit_cost": float(log.unit_cost) if log.unit_cost else None,
                    "description": log.description,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get usage logs: {e}")
            return []
    
    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    
    async def _get_active_subscription(self, company_id: UUID) -> Optional[HubSubscription]:
        """Get company's active subscription."""
        query = select(HubSubscription).where(
            and_(
                HubSubscription.company_id == company_id,
                HubSubscription.status == "active"
            )
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_plan(self, slug: str) -> Optional[HubPlan]:
        """Get plan by slug."""
        query = select(HubPlan).where(HubPlan.slug == slug)
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_or_create_monthly_usage(
        self,
        company_id: UUID,
        subscription: Optional[HubSubscription]
    ) -> HubUsage:
        """Get or create usage record for current month."""
        today = date.today()
        period_start = today.replace(day=1)
        
        # Calculate period end (last day of month)
        if today.month == 12:
            period_end = date(today.year + 1, 1, 1)
        else:
            period_end = date(today.year, today.month + 1, 1)
        period_end = period_end.replace(day=1) - timedelta(days=1) if hasattr(period_end, 'day') else period_end
        
        # Try to find existing
        query = select(HubUsage).where(
            and_(
                HubUsage.company_id == company_id,
                HubUsage.period_start == period_start
            )
        )
        result = self.db.execute(query)
        usage = result.scalar_one_or_none()
        
        if not usage:
            usage = HubUsage(
                company_id=company_id,
                subscription_id=subscription.id if subscription else None,
                period_start=period_start,
                period_end=period_end
            )
            self.db.add(usage)
            self.db.flush()
        
        return usage
    
    async def _calculate_overage(
        self,
        usage: HubUsage,
        plan: HubPlan,
        operation: str,
        quantity: int
    ) -> Tuple[bool, Decimal]:
        """Calculate if operation will incur overage and the cost."""
        limit = self._get_operation_limit(plan, operation)
        current = self._get_current_usage(usage, operation)
        
        if limit == 0:
            # Unlimited - no overage
            return False, Decimal("0")
        
        remaining = max(0, limit - current)
        
        if remaining >= quantity:
            # Within limit
            return False, Decimal("0")
        
        # Calculate overage
        overage_qty = quantity - remaining
        overage_rate = self._get_operation_cost(plan, operation)
        overage_cost = Decimal(str(overage_qty)) * Decimal(str(overage_rate))
        
        return True, overage_cost
    
    def _get_operation_limit(self, plan: HubPlan, operation: str) -> int:
        """Get the limit for an operation from plan."""
        if not plan or not plan.limits:
            return 0
        
        # Map operation to limit key
        limit_map = {
            "lc_validation": "lc_validations",
            "price_check": "price_checks",
            "hs_lookup": "hs_lookups",
            "sanctions_screen": "sanctions_screens",
            "container_track": "container_tracks"
        }
        key = limit_map.get(operation, operation)
        return plan.limits.get(key, 0)
    
    def _get_current_usage(self, usage: HubUsage, operation: str) -> int:
        """Get current usage count for an operation."""
        field_map = {
            "lc_validation": "lc_validations_used",
            "price_check": "price_checks_used",
            "hs_lookup": "hs_lookups_used",
            "sanctions_screen": "sanctions_screens_used",
            "container_track": "container_tracks_used"
        }
        field = field_map.get(operation)
        if field:
            return getattr(usage, field, 0) or 0
        return 0
    
    def _get_operation_cost(self, plan: HubPlan, operation: str) -> Decimal:
        """Get the per-unit cost for an operation (overage rate)."""
        if not plan or not plan.overage_rates:
            # Default PAYG rates
            defaults = {
                "lc_validation": 5.00,
                "price_check": 0.50,
                "hs_lookup": 0.25,
                "sanctions_screen": 0.50,
                "container_track": 1.00
            }
            return Decimal(str(defaults.get(operation, 1.00)))
        
        rate_map = {
            "lc_validation": "lc_validation",
            "price_check": "price_check",
            "hs_lookup": "hs_lookup",
            "sanctions_screen": "sanctions_screen",
            "container_track": "container_track"
        }
        key = rate_map.get(operation, operation)
        rate = plan.overage_rates.get(key, 1.00)
        return Decimal(str(rate))


# Add missing import
from datetime import timedelta


def get_usage_service(db: Session) -> UsageService:
    """Factory function to get UsageService instance."""
    return UsageService(db)

