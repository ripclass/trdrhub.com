#!/usr/bin/env python3
"""
Free Tier Gating System for LCopilot Trust Platform
Manages tier-based access control, quotas, and upsell mechanisms.
"""

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

class TierType(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

@dataclass
class TierLimits:
    """Tier limits and features"""
    name: str
    max_checks_per_month: int  # -1 for unlimited
    max_checks_per_day: int    # -1 for unlimited
    max_lc_size_mb: float      # Maximum LC document size
    features: List[str]        # Available features
    priority_support: bool
    api_access: bool
    batch_processing: bool
    evidence_packs: bool
    digital_signatures: bool
    custom_rules: bool

@dataclass
class CustomerUsage:
    """Customer usage tracking"""
    customer_id: str
    tier: TierType
    current_month: str  # YYYY-MM format
    current_day: str    # YYYY-MM-DD format
    checks_this_month: int
    checks_today: int
    total_lifetime_checks: int
    last_check_timestamp: str
    registration_date: str
    upgrade_date: Optional[str] = None

@dataclass
class UsageResult:
    """Result of usage check"""
    allowed: bool
    checks_remaining_today: int
    checks_remaining_month: int
    tier_limits: TierLimits
    upsell_triggered: bool
    upsell_message: str
    current_usage: CustomerUsage

class TierManager:
    """Manages tier-based access control and usage tracking"""

    # Tier definitions
    TIER_DEFINITIONS = {
        TierType.FREE: TierLimits(
            name="Free",
            max_checks_per_month=10,
            max_checks_per_day=3,
            max_lc_size_mb=2.0,
            features=["Basic compliance check", "Simple report"],
            priority_support=False,
            api_access=False,
            batch_processing=False,
            evidence_packs=False,
            digital_signatures=False,
            custom_rules=False
        ),
        TierType.PRO: TierLimits(
            name="Professional",
            max_checks_per_month=500,
            max_checks_per_day=50,
            max_lc_size_mb=10.0,
            features=[
                "Full compliance analysis",
                "Detailed reports",
                "Evidence packs",
                "API access",
                "Batch processing",
                "Priority support"
            ],
            priority_support=True,
            api_access=True,
            batch_processing=True,
            evidence_packs=True,
            digital_signatures=False,
            custom_rules=False
        ),
        TierType.ENTERPRISE: TierLimits(
            name="Enterprise",
            max_checks_per_month=-1,  # Unlimited
            max_checks_per_day=-1,    # Unlimited
            max_lc_size_mb=100.0,
            features=[
                "Unlimited compliance checks",
                "Advanced analytics",
                "Digital signatures",
                "Custom rules",
                "Dedicated support",
                "SSO integration",
                "Advanced API",
                "Custom integrations"
            ],
            priority_support=True,
            api_access=True,
            batch_processing=True,
            evidence_packs=True,
            digital_signatures=True,
            custom_rules=True
        )
    }

    def __init__(self, storage_path: str = "/Users/user/Desktop/Enso Intelligence/trdrhub.com/apps/api/data/usage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def check_usage_allowance(self, customer_id: str, tier: str, lc_size_mb: float = 0.0) -> UsageResult:
        """
        Check if customer can perform a compliance check based on their tier and usage
        """
        try:
            tier_enum = TierType(tier.lower())
        except ValueError:
            tier_enum = TierType.FREE

        tier_limits = self.TIER_DEFINITIONS[tier_enum]

        # Load current usage
        current_usage = self._load_customer_usage(customer_id, tier_enum)

        # Check file size limits
        if lc_size_mb > tier_limits.max_lc_size_mb:
            return UsageResult(
                allowed=False,
                checks_remaining_today=0,
                checks_remaining_month=0,
                tier_limits=tier_limits,
                upsell_triggered=True,
                upsell_message=f"LC document size ({lc_size_mb:.1f}MB) exceeds {tier_limits.name} tier limit ({tier_limits.max_lc_size_mb}MB). Upgrade to access larger documents.",
                current_usage=current_usage
            )

        # Check daily limits
        if tier_limits.max_checks_per_day > 0:  # Not unlimited
            if current_usage.checks_today >= tier_limits.max_checks_per_day:
                return UsageResult(
                    allowed=False,
                    checks_remaining_today=0,
                    checks_remaining_month=max(0, tier_limits.max_checks_per_month - current_usage.checks_this_month),
                    tier_limits=tier_limits,
                    upsell_triggered=True,
                    upsell_message=f"Daily limit of {tier_limits.max_checks_per_day} checks reached. Upgrade to Pro for 50 checks/day or Enterprise for unlimited.",
                    current_usage=current_usage
                )

        # Check monthly limits
        if tier_limits.max_checks_per_month > 0:  # Not unlimited
            if current_usage.checks_this_month >= tier_limits.max_checks_per_month:
                return UsageResult(
                    allowed=False,
                    checks_remaining_today=0,
                    checks_remaining_month=0,
                    tier_limits=tier_limits,
                    upsell_triggered=True,
                    upsell_message=f"Monthly limit of {tier_limits.max_checks_per_month} checks reached. Upgrade for more checks.",
                    current_usage=current_usage
                )

        # Calculate remaining checks
        remaining_today = -1 if tier_limits.max_checks_per_day < 0 else (tier_limits.max_checks_per_day - current_usage.checks_today)
        remaining_month = -1 if tier_limits.max_checks_per_month < 0 else (tier_limits.max_checks_per_month - current_usage.checks_this_month)

        # Determine if upsell should be triggered (approaching limits)
        upsell_triggered = False
        upsell_message = ""

        if tier_enum == TierType.FREE:
            if remaining_month <= 3 and remaining_month > 0:
                upsell_triggered = True
                upsell_message = f"Only {remaining_month} checks remaining this month. Upgrade to Pro for 500 monthly checks."
            elif remaining_today <= 1 and remaining_today > 0:
                upsell_triggered = True
                upsell_message = f"Only {remaining_today} checks remaining today. Upgrade for more daily checks."

        return UsageResult(
            allowed=True,
            checks_remaining_today=remaining_today,
            checks_remaining_month=remaining_month,
            tier_limits=tier_limits,
            upsell_triggered=upsell_triggered,
            upsell_message=upsell_message,
            current_usage=current_usage
        )

    def record_usage(self, customer_id: str, tier: str, success: bool = True) -> CustomerUsage:
        """
        Record a compliance check usage
        """
        try:
            tier_enum = TierType(tier.lower())
        except ValueError:
            tier_enum = TierType.FREE

        current_usage = self._load_customer_usage(customer_id, tier_enum)

        if success:
            # Update counters
            current_usage.checks_today += 1
            current_usage.checks_this_month += 1
            current_usage.total_lifetime_checks += 1
            current_usage.last_check_timestamp = datetime.now(timezone.utc).isoformat()

        # Save updated usage
        self._save_customer_usage(current_usage)

        return current_usage

    def get_tier_info(self, tier: str) -> TierLimits:
        """Get information about a tier"""
        try:
            tier_enum = TierType(tier.lower())
        except ValueError:
            tier_enum = TierType.FREE

        return self.TIER_DEFINITIONS[tier_enum]

    def get_customer_summary(self, customer_id: str, tier: str) -> Dict[str, Any]:
        """Get comprehensive customer usage summary"""
        try:
            tier_enum = TierType(tier.lower())
        except ValueError:
            tier_enum = TierType.FREE

        tier_limits = self.TIER_DEFINITIONS[tier_enum]
        current_usage = self._load_customer_usage(customer_id, tier_enum)

        # Calculate usage percentages
        daily_usage_pct = 0.0 if tier_limits.max_checks_per_day < 0 else (current_usage.checks_today / tier_limits.max_checks_per_day * 100)
        monthly_usage_pct = 0.0 if tier_limits.max_checks_per_month < 0 else (current_usage.checks_this_month / tier_limits.max_checks_per_month * 100)

        # Calculate days until reset
        today = datetime.now(timezone.utc)
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        days_until_reset = (next_month - today).days

        return {
            "customer_id": customer_id,
            "tier": tier_limits.name,
            "tier_features": tier_limits.features,
            "usage": {
                "checks_today": current_usage.checks_today,
                "checks_this_month": current_usage.checks_this_month,
                "total_lifetime": current_usage.total_lifetime_checks,
                "daily_usage_percent": round(daily_usage_pct, 1),
                "monthly_usage_percent": round(monthly_usage_pct, 1)
            },
            "limits": {
                "daily_limit": tier_limits.max_checks_per_day if tier_limits.max_checks_per_day > 0 else "Unlimited",
                "monthly_limit": tier_limits.max_checks_per_month if tier_limits.max_checks_per_month > 0 else "Unlimited",
                "max_file_size_mb": tier_limits.max_lc_size_mb
            },
            "remaining": {
                "today": -1 if tier_limits.max_checks_per_day < 0 else max(0, tier_limits.max_checks_per_day - current_usage.checks_today),
                "this_month": -1 if tier_limits.max_checks_per_month < 0 else max(0, tier_limits.max_checks_per_month - current_usage.checks_this_month),
                "days_until_monthly_reset": days_until_reset
            },
            "last_check": current_usage.last_check_timestamp,
            "member_since": current_usage.registration_date
        }

    def upgrade_customer_tier(self, customer_id: str, new_tier: str) -> Dict[str, Any]:
        """Upgrade a customer's tier"""
        try:
            new_tier_enum = TierType(new_tier.lower())
        except ValueError:
            return {"success": False, "error": f"Invalid tier: {new_tier}"}

        # Load current usage with old tier
        current_usage = self._load_customer_usage(customer_id, TierType.FREE)  # Load with current tier

        # Update to new tier
        current_usage.tier = new_tier_enum
        current_usage.upgrade_date = datetime.now(timezone.utc).isoformat()

        # Save updated usage
        self._save_customer_usage(current_usage)

        new_limits = self.TIER_DEFINITIONS[new_tier_enum]

        return {
            "success": True,
            "customer_id": customer_id,
            "new_tier": new_limits.name,
            "upgrade_date": current_usage.upgrade_date,
            "new_features": new_limits.features,
            "new_limits": {
                "daily": new_limits.max_checks_per_day if new_limits.max_checks_per_day > 0 else "Unlimited",
                "monthly": new_limits.max_checks_per_month if new_limits.max_checks_per_month > 0 else "Unlimited"
            }
        }

    def _load_customer_usage(self, customer_id: str, tier: TierType) -> CustomerUsage:
        """Load customer usage data or create new record"""
        usage_file = self.storage_path / f"{self._hash_customer_id(customer_id)}.json"

        now = datetime.now(timezone.utc)
        current_month = now.strftime("%Y-%m")
        current_day = now.strftime("%Y-%m-%d")

        if usage_file.exists():
            try:
                with open(usage_file, 'r') as f:
                    data = json.load(f)

                usage = CustomerUsage(**data)

                # Reset counters if month/day has changed
                if usage.current_month != current_month:
                    usage.checks_this_month = 0
                    usage.current_month = current_month

                if usage.current_day != current_day:
                    usage.checks_today = 0
                    usage.current_day = current_day

                # Update tier if changed
                usage.tier = tier

                return usage
            except Exception:
                # If file is corrupted, create new record
                pass

        # Create new usage record
        return CustomerUsage(
            customer_id=customer_id,
            tier=tier,
            current_month=current_month,
            current_day=current_day,
            checks_this_month=0,
            checks_today=0,
            total_lifetime_checks=0,
            last_check_timestamp="",
            registration_date=now.isoformat()
        )

    def _save_customer_usage(self, usage: CustomerUsage) -> None:
        """Save customer usage data"""
        usage_file = self.storage_path / f"{self._hash_customer_id(usage.customer_id)}.json"

        with open(usage_file, 'w') as f:
            json.dump(asdict(usage), f, indent=2, default=str)

    def _hash_customer_id(self, customer_id: str) -> str:
        """Hash customer ID for privacy"""
        return hashlib.sha256(customer_id.encode()).hexdigest()[:16]

    def get_upsell_pricing(self) -> Dict[str, Any]:
        """Get pricing information for upsell display"""
        return {
            "tiers": {
                "free": {
                    "name": "Free",
                    "price": "$0/month",
                    "limits": "10 checks/month, 3/day",
                    "features": ["Basic compliance check", "Simple report"]
                },
                "pro": {
                    "name": "Professional",
                    "price": "$99/month",
                    "limits": "500 checks/month, 50/day",
                    "features": [
                        "Full compliance analysis",
                        "Evidence packs",
                        "API access",
                        "Priority support"
                    ],
                    "upgrade_url": "https://lcopilot.com/upgrade/pro"
                },
                "enterprise": {
                    "name": "Enterprise",
                    "price": "Custom pricing",
                    "limits": "Unlimited",
                    "features": [
                        "Everything in Pro",
                        "Digital signatures",
                        "Custom rules",
                        "SSO integration",
                        "Dedicated support"
                    ],
                    "contact_url": "https://lcopilot.com/contact/enterprise"
                }
            },
            "upgrade_benefits": {
                "pro": [
                    "50x more daily checks",
                    "Advanced compliance analysis",
                    "Tamper-proof evidence packages",
                    "API integration",
                    "Priority customer support"
                ],
                "enterprise": [
                    "Unlimited compliance checks",
                    "Digital signatures for legal compliance",
                    "Custom rule creation",
                    "Advanced analytics dashboard",
                    "Dedicated account manager"
                ]
            }
        }

    def cleanup_old_usage_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old usage data files"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cleaned_files = 0
        kept_files = 0

        for usage_file in self.storage_path.glob("*.json"):
            try:
                # Check file modification time
                file_modified = datetime.fromtimestamp(usage_file.stat().st_mtime, timezone.utc)

                if file_modified < cutoff_date:
                    # Load to check if customer is still active
                    with open(usage_file, 'r') as f:
                        data = json.load(f)

                    last_check = data.get("last_check_timestamp", "")
                    if last_check:
                        last_check_date = datetime.fromisoformat(last_check.replace('Z', '+00:00'))

                        # If no activity for cleanup period, remove file
                        if last_check_date < cutoff_date:
                            usage_file.unlink()
                            cleaned_files += 1
                        else:
                            kept_files += 1
                    else:
                        # No recent activity, clean up
                        usage_file.unlink()
                        cleaned_files += 1
                else:
                    kept_files += 1

            except Exception:
                # If we can't process the file, keep it
                kept_files += 1

        return {
            "cleaned_files": cleaned_files,
            "kept_files": kept_files,
            "cleanup_date": cutoff_date.isoformat()
        }