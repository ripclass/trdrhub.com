"""
Pricing configuration and cost calculation logic for LCopilot billing system.

This module defines pricing constants, subscription plans, and cost calculation
functions for different billing actions.
"""

from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, date


class BillingAction(str, Enum):
    """Billable action types with their corresponding pricing rules."""
    VALIDATE = "validate"               # Standard LC validation
    RECHECK = "recheck"                 # Re-validation of existing LC
    EXPORT = "export"                   # Export/download results
    BULK_UPLOAD = "bulk_upload"         # Bulk document processing
    DRAFT_IMPORT = "draft_import"       # Import draft LC
    IMPORT_BUNDLE = "import_bundle"     # Import document bundle


# Pricing constants in BDT (Bangladesh Taka)
class PricingConstants:
    """Base pricing for pay-per-check actions."""

    # Primary validation services
    PER_CHECK = Decimal("1200.00")          # Standard LC validation
    IMPORT_DRAFT = Decimal("1000.00")       # Draft LC import and validation
    IMPORT_BUNDLE = Decimal("1800.00")      # Full document bundle import

    # Additional services
    EXPORT_BASIC = Decimal("50.00")         # Basic export (PDF/CSV)
    EXPORT_DETAILED = Decimal("100.00")     # Detailed analytics export
    BULK_PROCESSING = Decimal("50.00")      # Per document in bulk upload

    # Re-check policy
    FIRST_RECHECK_FREE = True               # First re-check is free
    RECHECK_DISCOUNT = Decimal("0.50")      # 50% discount on additional rechecks


@dataclass
class SubscriptionPlan:
    """Subscription plan definition with quotas and pricing."""
    name: str
    monthly_price_bdt: Decimal
    quota_limit: Optional[int]              # None = unlimited
    included_actions: Dict[str, int]        # Action type -> included quantity
    overage_rates: Dict[str, Decimal]       # Action type -> overage price per unit
    features: list                          # List of included features
    is_enterprise: bool = False


# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    "free": SubscriptionPlan(
        name="Free Plan",
        monthly_price_bdt=Decimal("0.00"),
        quota_limit=5,                      # 5 validations per month
        included_actions={
            BillingAction.VALIDATE: 5,
            BillingAction.EXPORT: 5,
            BillingAction.RECHECK: 2,
        },
        overage_rates={
            BillingAction.VALIDATE: PricingConstants.PER_CHECK,
            BillingAction.EXPORT: PricingConstants.EXPORT_BASIC,
        },
        features=["Basic validation", "Standard support", "PDF export"]
    ),

    "monthly_basic": SubscriptionPlan(
        name="Monthly Basic",
        monthly_price_bdt=Decimal("25000.00"),  # 25k BDT for 30 checks
        quota_limit=30,
        included_actions={
            BillingAction.VALIDATE: 30,
            BillingAction.EXPORT: 50,
            BillingAction.RECHECK: 10,
            BillingAction.DRAFT_IMPORT: 5,
        },
        overage_rates={
            BillingAction.VALIDATE: Decimal("800.00"),     # Discounted overage
            BillingAction.DRAFT_IMPORT: Decimal("800.00"),
            BillingAction.EXPORT: PricingConstants.EXPORT_BASIC,
        },
        features=[
            "30 validations/month", "Priority support", "Advanced exports",
            "Draft import", "Analytics dashboard"
        ]
    ),

    "monthly_pro": SubscriptionPlan(
        name="Monthly Pro",
        monthly_price_bdt=Decimal("70000.00"),  # 70k BDT for 100 checks
        quota_limit=100,
        included_actions={
            BillingAction.VALIDATE: 100,
            BillingAction.EXPORT: 200,
            BillingAction.RECHECK: 50,
            BillingAction.DRAFT_IMPORT: 20,
            BillingAction.IMPORT_BUNDLE: 10,
            BillingAction.BULK_UPLOAD: 50,  # 50 documents in bulk
        },
        overage_rates={
            BillingAction.VALIDATE: Decimal("600.00"),     # Better overage rate
            BillingAction.DRAFT_IMPORT: Decimal("600.00"),
            BillingAction.IMPORT_BUNDLE: Decimal("1200.00"),
            BillingAction.BULK_UPLOAD: Decimal("30.00"),
        },
        features=[
            "100 validations/month", "Premium support", "All export formats",
            "Bulk processing", "Advanced analytics", "API access", "Team collaboration"
        ]
    ),

    "enterprise": SubscriptionPlan(
        name="Enterprise",
        monthly_price_bdt=Decimal("0.00"),      # Custom pricing
        quota_limit=None,                       # Unlimited
        included_actions={},                    # Custom allocation
        overage_rates={},                       # Custom rates
        features=[
            "Unlimited validations", "24/7 dedicated support", "Custom integrations",
            "On-premise deployment", "SLA guarantees", "Custom workflows"
        ],
        is_enterprise=True
    ),
}


def calculate_cost(
    action: str,
    company_plan: str = "pay_per_check",
    job_metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    session_history: Optional[Dict] = None
) -> Decimal:
    """
    Calculate the cost for a specific billing action.

    Args:
        action: The billing action type (validate, recheck, etc.)
        company_plan: The company's billing plan
        job_metadata: Additional context about the job
        user_id: User performing the action (for recheck logic)
        session_history: Previous actions in this session (for recheck logic)

    Returns:
        Cost in BDT as Decimal
    """

    if company_plan == "pay_per_check":
        return _calculate_pay_per_check_cost(action, job_metadata, user_id, session_history)

    # For subscription plans, cost is typically 0 (covered by subscription)
    # unless it's an overage charge
    plan = SUBSCRIPTION_PLANS.get(company_plan)
    if not plan:
        raise ValueError(f"Unknown billing plan: {company_plan}")

    # Subscription users typically don't pay per action
    # Cost calculation for overages is handled in the billing service
    return Decimal("0.00")


def _calculate_pay_per_check_cost(
    action: str,
    job_metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    session_history: Optional[Dict] = None
) -> Decimal:
    """Calculate cost for pay-per-check billing."""

    job_metadata = job_metadata or {}

    if action == BillingAction.VALIDATE:
        return PricingConstants.PER_CHECK

    elif action == BillingAction.RECHECK:
        # Recheck policy: first recheck is free, subsequent are full price
        if PricingConstants.FIRST_RECHECK_FREE:
            recheck_count = 0
            if session_history:
                recheck_count = session_history.get("recheck_count", 0)

            if recheck_count == 0:
                return Decimal("0.00")  # First recheck free
            else:
                # Apply discount for additional rechecks
                base_cost = PricingConstants.PER_CHECK
                return base_cost * PricingConstants.RECHECK_DISCOUNT

        return PricingConstants.PER_CHECK

    elif action == BillingAction.DRAFT_IMPORT:
        return PricingConstants.IMPORT_DRAFT

    elif action == BillingAction.IMPORT_BUNDLE:
        return PricingConstants.IMPORT_BUNDLE

    elif action == BillingAction.EXPORT:
        export_type = job_metadata.get("export_type", "basic")
        if export_type == "detailed":
            return PricingConstants.EXPORT_DETAILED
        return PricingConstants.EXPORT_BASIC

    elif action == BillingAction.BULK_UPLOAD:
        document_count = job_metadata.get("document_count", 1)
        return PricingConstants.BULK_PROCESSING * Decimal(str(document_count))

    else:
        raise ValueError(f"Unknown billing action: {action}")


def get_plan_quotas(plan_name: str) -> Dict[str, int]:
    """Get quota limits for a subscription plan."""
    plan = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        return {}
    return plan.included_actions


def calculate_subscription_cost(
    plan_name: str,
    billing_period: str = "monthly"
) -> Decimal:
    """Calculate subscription cost for a billing period."""
    plan = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_name}")

    if billing_period == "monthly":
        return plan.monthly_price_bdt
    elif billing_period == "annual":
        # 10% discount for annual billing
        return plan.monthly_price_bdt * 12 * Decimal("0.90")
    else:
        raise ValueError(f"Unknown billing period: {billing_period}")


def calculate_overage_cost(
    plan_name: str,
    action: str,
    overage_units: int
) -> Decimal:
    """Calculate cost for overage usage beyond subscription limits."""
    plan = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_name}")

    overage_rate = plan.overage_rates.get(action, Decimal("0.00"))
    return overage_rate * Decimal(str(overage_units))


def format_price_bdt(amount: Decimal) -> str:
    """Format price in BDT with proper currency symbol."""
    return f"৳{amount:,.2f}"


def convert_bdt_to_usd(bdt_amount: Decimal, exchange_rate: Optional[Decimal] = None) -> Decimal:
    """Convert BDT to USD using current exchange rate."""
    if exchange_rate is None:
        # Default exchange rate - in production this should come from a live API
        exchange_rate = Decimal("0.0085")  # 1 BDT ≈ 0.0085 USD (approximate)

    return bdt_amount * exchange_rate


def get_billing_period_dates(
    plan: str,
    cycle_start: Optional[date] = None
) -> tuple[date, date]:
    """Get billing period start and end dates for a plan."""
    if cycle_start is None:
        cycle_start = date.today().replace(day=1)  # First of current month

    if plan == "annual":
        # Annual billing: same date next year
        try:
            period_end = cycle_start.replace(year=cycle_start.year + 1)
        except ValueError:
            # Handle leap year edge case (Feb 29)
            period_end = cycle_start.replace(year=cycle_start.year + 1, month=2, day=28)
        return cycle_start, period_end

    else:
        # Monthly billing: same date next month
        if cycle_start.month == 12:
            period_end = cycle_start.replace(year=cycle_start.year + 1, month=1)
        else:
            try:
                period_end = cycle_start.replace(month=cycle_start.month + 1)
            except ValueError:
                # Handle month-end edge cases (Jan 31 -> Feb 28/29)
                if cycle_start.month + 1 == 2:
                    # February has fewer days
                    period_end = cycle_start.replace(month=2, day=28)
                    if cycle_start.year % 4 == 0 and (cycle_start.year % 100 != 0 or cycle_start.year % 400 == 0):
                        period_end = period_end.replace(day=29)  # Leap year
                else:
                    period_end = cycle_start.replace(month=cycle_start.month + 1, day=30)

        return cycle_start, period_end


def is_action_billable(action: str, plan: str) -> bool:
    """Check if an action is billable for a given plan."""
    if plan == "free":
        # Free plan has very limited actions
        return action in [BillingAction.VALIDATE, BillingAction.RECHECK]

    # All actions are potentially billable for paid plans
    return True


def get_plan_features(plan_name: str) -> list:
    """Get list of features included in a plan."""
    plan = SUBSCRIPTION_PLANS.get(plan_name, SUBSCRIPTION_PLANS["free"])
    return plan.features


def estimate_monthly_cost(
    expected_usage: Dict[str, int],
    plan_name: str = "pay_per_check"
) -> Dict[str, Decimal]:
    """
    Estimate monthly cost based on expected usage patterns.

    Args:
        expected_usage: Dict mapping action types to expected monthly quantity
        plan_name: Billing plan to evaluate

    Returns:
        Dict with cost breakdown
    """

    if plan_name == "pay_per_check":
        total_cost = Decimal("0.00")
        breakdown = {}

        for action, quantity in expected_usage.items():
            unit_cost = calculate_cost(action, plan_name)
            action_cost = unit_cost * Decimal(str(quantity))
            breakdown[action] = {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_cost": action_cost
            }
            total_cost += action_cost

        return {
            "plan": plan_name,
            "base_cost": Decimal("0.00"),
            "usage_cost": total_cost,
            "total_cost": total_cost,
            "breakdown": breakdown
        }

    else:
        # Subscription plan calculation
        plan = SUBSCRIPTION_PLANS.get(plan_name)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_name}")

        base_cost = plan.monthly_price_bdt
        overage_cost = Decimal("0.00")
        breakdown = {}

        for action, quantity in expected_usage.items():
            included = plan.included_actions.get(action, 0)
            overage = max(0, quantity - included)

            if overage > 0:
                overage_rate = plan.overage_rates.get(action, Decimal("0.00"))
                action_overage_cost = overage_rate * Decimal(str(overage))
                overage_cost += action_overage_cost

                breakdown[action] = {
                    "quantity": quantity,
                    "included": included,
                    "overage": overage,
                    "overage_rate": overage_rate,
                    "overage_cost": action_overage_cost
                }
            else:
                breakdown[action] = {
                    "quantity": quantity,
                    "included": included,
                    "overage": 0,
                    "overage_cost": Decimal("0.00")
                }

        return {
            "plan": plan_name,
            "base_cost": base_cost,
            "usage_cost": overage_cost,
            "total_cost": base_cost + overage_cost,
            "breakdown": breakdown
        }


# Export commonly used functions and constants
__all__ = [
    "BillingAction",
    "PricingConstants",
    "SUBSCRIPTION_PLANS",
    "calculate_cost",
    "get_plan_quotas",
    "calculate_subscription_cost",
    "calculate_overage_cost",
    "format_price_bdt",
    "convert_bdt_to_usd",
    "get_billing_period_dates",
    "is_action_billable",
    "get_plan_features",
    "estimate_monthly_cost"
]