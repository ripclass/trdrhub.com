"""
Production Billing Checkpoint
Enforces billing requirements for bank recheck operations in production
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum
import logging
import asyncio

from app.core.bankpilot.tenant_config import get_tenant_config, Environment
from app.core.exceptions import BillingError, InsufficientCreditsError

logger = logging.getLogger(__name__)


class BillingEventType(str, Enum):
    BANK_RECHECK = "bank_recheck"
    DOCUMENT_VALIDATION = "document_validation"
    COMPLIANCE_CHECK = "compliance_check"
    RISK_ANALYSIS = "risk_analysis"
    REPORT_GENERATION = "report_generation"


class BillingEvent(BaseModel):
    """Immutable billing event record"""

    event_id: str
    tenant_alias: str
    event_type: BillingEventType
    amount: float
    currency: str = "USD"
    actor: str  # "bank" or "sme"
    context: Dict[str, Any]
    timestamp: datetime
    reference_id: Optional[str] = None
    reconciliation_ref: Optional[str] = None

    class Config:
        frozen = True  # Immutable


class CreditBalance(BaseModel):
    """Bank credit balance tracking"""

    tenant_alias: str
    total_credits: float
    used_credits: float
    available_credits: float
    last_updated: datetime
    expiry_date: Optional[datetime] = None


class BillingCheckpoint:
    """Production billing enforcement for bank pilot"""

    def __init__(self, tenant_alias: str):
        self.tenant_alias = tenant_alias
        self._billing_cache: Dict[str, Any] = {}

    async def enforce_billing_for_recheck(
        self,
        operation_type: str,
        cost: float,
        context: Dict[str, Any],
        user_id: str
    ) -> BillingEvent:
        """Enforce billing for bank recheck operations in production"""

        tenant_config = await get_tenant_config(self.tenant_alias)
        if not tenant_config:
            raise BillingError(f"Tenant configuration not found: {self.tenant_alias}")

        # Only enforce billing in production environment
        if tenant_config.environment != Environment.PRODUCTION:
            logger.info(f"Billing checkpoint skipped for {tenant_config.environment} environment")
            return await self._create_demo_billing_event(operation_type, cost, context, user_id)

        # Check if billing is enabled for this tenant
        if not tenant_config.billing_enabled:
            raise BillingError(f"Billing not enabled for tenant: {self.tenant_alias}")

        # Verify sufficient credits
        credit_balance = await self._get_credit_balance()
        if credit_balance.available_credits < cost:
            raise InsufficientCreditsError(
                f"Insufficient credits: required {cost}, available {credit_balance.available_credits}"
            )

        # Deduct credits and create billing event
        billing_event = await self._process_billing_transaction(
            operation_type, cost, context, user_id
        )

        logger.info(
            f"Billing enforced: {operation_type} for {self.tenant_alias}, "
            f"cost: {cost}, event_id: {billing_event.event_id}"
        )

        return billing_event

    async def _get_credit_balance(self) -> CreditBalance:
        """Get current credit balance for tenant"""

        # Check cache first
        cache_key = f"credits_{self.tenant_alias}"
        if cache_key in self._billing_cache:
            cached_data = self._billing_cache[cache_key]
            if (datetime.utcnow() - cached_data["timestamp"]).seconds < 60:  # 1 minute cache
                return cached_data["balance"]

        # Load from billing service/database
        balance = await self._load_credit_balance()

        # Update cache
        self._billing_cache[cache_key] = {
            "balance": balance,
            "timestamp": datetime.utcnow()
        }

        return balance

    async def _load_credit_balance(self) -> CreditBalance:
        """Load credit balance from billing service"""

        # In production, this would query the billing database
        # For now, simulate credit balance

        return CreditBalance(
            tenant_alias=self.tenant_alias,
            total_credits=10000.0,
            used_credits=2500.0,
            available_credits=7500.0,
            last_updated=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=30)
        )

    async def _process_billing_transaction(
        self,
        operation_type: str,
        cost: float,
        context: Dict[str, Any],
        user_id: str
    ) -> BillingEvent:
        """Process billing transaction and create immutable event"""

        try:
            # Generate unique event ID
            event_id = await self._generate_event_id()

            # Deduct credits atomically
            await self._deduct_credits(cost)

            # Create billing event
            billing_event = BillingEvent(
                event_id=event_id,
                tenant_alias=self.tenant_alias,
                event_type=BillingEventType.BANK_RECHECK,
                amount=cost,
                actor="bank",
                context={
                    "operation_type": operation_type,
                    "user_id": user_id,
                    **context
                },
                timestamp=datetime.utcnow(),
                reference_id=context.get("reference_id"),
                reconciliation_ref=await self._generate_reconciliation_ref()
            )

            # Persist billing event (immutable)
            await self._persist_billing_event(billing_event)

            # Invalidate cache
            self._invalidate_cache()

            return billing_event

        except Exception as e:
            logger.error(f"Billing transaction failed for {self.tenant_alias}: {str(e)}")
            raise BillingError(f"Billing transaction failed: {str(e)}")

    async def _create_demo_billing_event(
        self,
        operation_type: str,
        cost: float,
        context: Dict[str, Any],
        user_id: str
    ) -> BillingEvent:
        """Create demo billing event for non-production environments"""

        return BillingEvent(
            event_id=await self._generate_event_id(),
            tenant_alias=self.tenant_alias,
            event_type=BillingEventType.BANK_RECHECK,
            amount=0.0,  # No charge in demo
            actor="bank",
            context={
                "operation_type": operation_type,
                "user_id": user_id,
                "demo_mode": True,
                **context
            },
            timestamp=datetime.utcnow(),
            reconciliation_ref="DEMO"
        )

    async def enable_production_billing(self):
        """Enable billing enforcement for production environment"""

        tenant_config = await get_tenant_config(self.tenant_alias)
        if not tenant_config:
            raise BillingError(f"Tenant configuration not found: {self.tenant_alias}")

        # Update tenant configuration to enable billing
        await self._update_tenant_billing_config(True)

        logger.info(f"Production billing enabled for tenant: {self.tenant_alias}")

    async def get_billing_reconciliation(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate billing reconciliation report"""

        events = await self._get_billing_events(start_date, end_date)

        summary = {
            "tenant": self.tenant_alias,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_events": len(events),
            "total_amount": sum(event.amount for event in events),
            "events_by_type": {},
            "events_by_actor": {},
            "events": [event.dict() for event in events]
        }

        # Aggregate by event type
        for event in events:
            event_type = event.event_type
            if event_type not in summary["events_by_type"]:
                summary["events_by_type"][event_type] = {"count": 0, "amount": 0.0}
            summary["events_by_type"][event_type]["count"] += 1
            summary["events_by_type"][event_type]["amount"] += event.amount

        # Aggregate by actor
        for event in events:
            actor = event.actor
            if actor not in summary["events_by_actor"]:
                summary["events_by_actor"][actor] = {"count": 0, "amount": 0.0}
            summary["events_by_actor"][actor]["count"] += 1
            summary["events_by_actor"][actor]["amount"] += event.amount

        return summary

    async def _generate_event_id(self) -> str:
        """Generate unique billing event ID"""
        import uuid
        return f"bill_{self.tenant_alias}_{datetime.utcnow().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"

    async def _generate_reconciliation_ref(self) -> str:
        """Generate reconciliation reference"""
        return f"REC_{self.tenant_alias}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    async def _deduct_credits(self, amount: float):
        """Atomically deduct credits from tenant balance"""
        # In production, this would be an atomic database operation
        pass

    async def _persist_billing_event(self, event: BillingEvent):
        """Persist immutable billing event"""
        # In production, this would write to audit/billing database
        pass

    async def _get_billing_events(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[BillingEvent]:
        """Get billing events for date range"""
        # In production, this would query the billing database
        return []

    async def _update_tenant_billing_config(self, enabled: bool):
        """Update tenant billing configuration"""
        # In production, this would update the tenant config in database
        pass

    def _invalidate_cache(self):
        """Invalidate billing cache"""
        cache_key = f"credits_{self.tenant_alias}"
        if cache_key in self._billing_cache:
            del self._billing_cache[cache_key]


# Singleton billing service
class BillingService:
    """Global billing service for managing bank pilot billing"""

    def __init__(self):
        self._checkpoints: Dict[str, BillingCheckpoint] = {}

    def get_checkpoint(self, tenant_alias: str) -> BillingCheckpoint:
        """Get or create billing checkpoint for tenant"""

        if tenant_alias not in self._checkpoints:
            self._checkpoints[tenant_alias] = BillingCheckpoint(tenant_alias)

        return self._checkpoints[tenant_alias]

    async def enforce_bank_recheck_billing(
        self,
        tenant_alias: str,
        operation_type: str,
        cost: float,
        context: Dict[str, Any],
        user_id: str
    ) -> BillingEvent:
        """Convenience method for enforcing bank recheck billing"""

        checkpoint = self.get_checkpoint(tenant_alias)
        return await checkpoint.enforce_billing_for_recheck(
            operation_type, cost, context, user_id
        )


# Global billing service instance
billing_service = BillingService()