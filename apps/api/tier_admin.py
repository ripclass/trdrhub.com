#!/usr/bin/env python3
"""
Tier Administration CLI for LCopilot Trust Platform
Manage customer tiers, usage, and quotas.

Usage:
    python tier_admin.py --customer-id customer123 --check-usage
    python tier_admin.py --customer-id customer123 --upgrade-tier pro
    python tier_admin.py --customer-id customer123 --record-usage --tier free
    python tier_admin.py --list-pricing
"""

import argparse
import json
import sys
from pathlib import Path

# Add trust platform to path
sys.path.append(str(Path(__file__).parent))

from trust_platform.tiers.tier_manager import TierManager

def check_usage(args):
    """Check customer usage allowance"""
    print(f"🔍 Checking usage allowance for customer: {args.customer_id}")

    tier_manager = TierManager()

    # Check current allowance
    usage_result = tier_manager.check_usage_allowance(args.customer_id, args.tier, args.lc_size)

    print(f"📊 Tier: {usage_result.tier_limits.name}")
    print(f"✅ Allowed: {'Yes' if usage_result.allowed else 'No'}")

    if usage_result.allowed:
        print(f"📈 Remaining today: {'Unlimited' if usage_result.checks_remaining_today == -1 else usage_result.checks_remaining_today}")
        print(f"📅 Remaining this month: {'Unlimited' if usage_result.checks_remaining_month == -1 else usage_result.checks_remaining_month}")
    else:
        print(f"❌ Usage blocked")

    if usage_result.upsell_triggered:
        print(f"💡 Upsell: {usage_result.upsell_message}")

    # Show detailed usage summary
    summary = tier_manager.get_customer_summary(args.customer_id, args.tier)
    print(f"\n📋 Detailed Usage Summary:")
    print(f"   Today: {summary['usage']['checks_today']} checks ({summary['usage']['daily_usage_percent']}%)")
    print(f"   This month: {summary['usage']['checks_this_month']} checks ({summary['usage']['monthly_usage_percent']}%)")
    print(f"   Lifetime: {summary['usage']['total_lifetime']} checks")
    print(f"   Member since: {summary['member_since']}")

    return usage_result.allowed

def record_usage(args):
    """Record a usage event"""
    print(f"📝 Recording usage for customer: {args.customer_id}")

    tier_manager = TierManager()

    # Record the usage
    updated_usage = tier_manager.record_usage(args.customer_id, args.tier, success=not args.failed)

    print(f"✅ Usage recorded successfully")
    print(f"📈 New counts - Today: {updated_usage.checks_today}, Month: {updated_usage.checks_this_month}")
    print(f"🏆 Lifetime total: {updated_usage.total_lifetime_checks}")

    return True

def upgrade_tier(args):
    """Upgrade customer tier"""
    print(f"⬆️  Upgrading customer {args.customer_id} to {args.new_tier}")

    tier_manager = TierManager()

    # Perform upgrade
    result = tier_manager.upgrade_customer_tier(args.customer_id, args.new_tier)

    if result["success"]:
        print(f"✅ Upgrade successful!")
        print(f"🎉 New tier: {result['new_tier']}")
        print(f"📅 Upgrade date: {result['upgrade_date']}")
        print(f"🚀 New features: {', '.join(result['new_features'])}")
        print(f"📊 New limits: {result['new_limits']['daily']} daily, {result['new_limits']['monthly']} monthly")
    else:
        print(f"❌ Upgrade failed: {result['error']}")

    return result["success"]

def list_pricing(args):
    """List pricing and tier information"""
    print("💰 LCopilot Pricing & Tiers")
    print("=" * 50)

    tier_manager = TierManager()

    pricing = tier_manager.get_upsell_pricing()

    for tier_key, tier_info in pricing["tiers"].items():
        print(f"\n🏷️  {tier_info['name']} - {tier_info['price']}")
        print(f"   Limits: {tier_info['limits']}")
        print(f"   Features:")
        for feature in tier_info['features']:
            print(f"     • {feature}")

        if 'upgrade_url' in tier_info:
            print(f"   🔗 Upgrade: {tier_info['upgrade_url']}")
        elif 'contact_url' in tier_info:
            print(f"   📞 Contact: {tier_info['contact_url']}")

    return True

def show_tier_features(args):
    """Show detailed tier feature comparison"""
    print("🔍 Tier Feature Comparison")
    print("=" * 50)

    tier_manager = TierManager()

    for tier_type in ["free", "pro", "enterprise"]:
        tier_info = tier_manager.get_tier_info(tier_type)
        print(f"\n{tier_info.name.upper()} TIER:")
        print(f"  Daily limit: {'Unlimited' if tier_info.max_checks_per_day == -1 else tier_info.max_checks_per_day}")
        print(f"  Monthly limit: {'Unlimited' if tier_info.max_checks_per_month == -1 else tier_info.max_checks_per_month}")
        print(f"  Max file size: {tier_info.max_lc_size_mb}MB")
        print(f"  Priority support: {'Yes' if tier_info.priority_support else 'No'}")
        print(f"  API access: {'Yes' if tier_info.api_access else 'No'}")
        print(f"  Evidence packs: {'Yes' if tier_info.evidence_packs else 'No'}")
        print(f"  Digital signatures: {'Yes' if tier_info.digital_signatures else 'No'}")

    return True

def cleanup_usage_data(args):
    """Clean up old usage data"""
    print(f"🧹 Cleaning up usage data older than {args.days} days")

    tier_manager = TierManager()
    result = tier_manager.cleanup_old_usage_data(args.days)

    print(f"✅ Cleanup completed")
    print(f"🗑️  Files removed: {result['cleaned_files']}")
    print(f"📁 Files kept: {result['kept_files']}")
    print(f"📅 Cutoff date: {result['cleanup_date']}")

    return True

def main():
    parser = argparse.ArgumentParser(
        description="Tier Administration CLI for LCopilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Check usage allowance
    python tier_admin.py --customer-id user123 --check-usage --tier free

    # Record successful usage
    python tier_admin.py --customer-id user123 --record-usage --tier pro

    # Upgrade customer
    python tier_admin.py --customer-id user123 --upgrade-tier enterprise

    # List pricing
    python tier_admin.py --list-pricing

    # Show tier features
    python tier_admin.py --show-features

    # Clean old data
    python tier_admin.py --cleanup --days 90
        """
    )

    # Common arguments
    parser.add_argument("--customer-id", help="Customer ID")
    parser.add_argument("--tier", default="free", choices=["free", "pro", "enterprise"], help="Customer tier")

    # Commands
    parser.add_argument("--check-usage", action="store_true", help="Check usage allowance")
    parser.add_argument("--lc-size", type=float, default=0.0, help="LC document size in MB")

    parser.add_argument("--record-usage", action="store_true", help="Record usage")
    parser.add_argument("--failed", action="store_true", help="Mark usage as failed")

    parser.add_argument("--upgrade-tier", choices=["pro", "enterprise"], help="Upgrade to tier")

    parser.add_argument("--list-pricing", action="store_true", help="List pricing information")
    parser.add_argument("--show-features", action="store_true", help="Show tier features")

    parser.add_argument("--cleanup", action="store_true", help="Clean up old usage data")
    parser.add_argument("--days", type=int, default=90, help="Days of data to keep")

    args = parser.parse_args()

    # Execute commands
    success = False

    if args.check_usage:
        if not args.customer_id:
            print("❌ --customer-id required for usage check")
            return 1
        success = check_usage(args)

    elif args.record_usage:
        if not args.customer_id:
            print("❌ --customer-id required for recording usage")
            return 1
        success = record_usage(args)

    elif args.upgrade_tier:
        if not args.customer_id:
            print("❌ --customer-id required for tier upgrade")
            return 1
        args.new_tier = args.upgrade_tier
        success = upgrade_tier(args)

    elif args.list_pricing:
        success = list_pricing(args)

    elif args.show_features:
        success = show_tier_features(args)

    elif args.cleanup:
        success = cleanup_usage_data(args)

    else:
        parser.print_help()
        print("\n❌ No valid command provided")
        return 1

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())