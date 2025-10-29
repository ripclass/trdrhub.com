#!/usr/bin/env python3
"""
AWS CDK App for LCopilot Reliability-as-a-Service

This app creates reliability infrastructure stacks for different tiers:
- Free tier: Basic status page and SLA reporting
- Pro tier: Enhanced features with customer portal
- Enterprise tier: Full featured with white-label, ML, and custom domains

Usage:
    # Deploy free tier
    cdk deploy LCopilotReliabilityFree

    # Deploy pro tier
    cdk deploy LCopilotReliabilityPro

    # Deploy enterprise tier with custom domain
    cdk deploy LCopilotReliabilityEnterprise
"""

import aws_cdk as cdk
from reliability_stack import LCopilotReliabilityStack, ReliabilityTier
import os

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
)

# Common configuration
environment = app.node.try_get_context("environment") or "production"
alert_email = app.node.try_get_context("alert_email")

# Free Tier Stack
free_stack = LCopilotReliabilityStack(
    app, "LCopilotReliabilityFree",
    tier=ReliabilityTier.FREE,
    alert_email=alert_email,
    env=env,
    description="LCopilot Reliability-as-a-Service Free Tier Infrastructure",
    tags={
        "Project": "LCopilot",
        "Tier": "Free",
        "Environment": environment,
        "CostCenter": "Reliability",
        "Owner": "Platform Team"
    }
)

# Pro Tier Stack
pro_stack = LCopilotReliabilityStack(
    app, "LCopilotReliabilityPro",
    tier=ReliabilityTier.PRO,
    alert_email=alert_email,
    env=env,
    description="LCopilot Reliability-as-a-Service Pro Tier Infrastructure",
    tags={
        "Project": "LCopilot",
        "Tier": "Pro",
        "Environment": environment,
        "CostCenter": "Reliability",
        "Owner": "Platform Team"
    }
)

# Enterprise Tier Stack (Base)
enterprise_stack = LCopilotReliabilityStack(
    app, "LCopilotReliabilityEnterprise",
    tier=ReliabilityTier.ENTERPRISE,
    alert_email=alert_email,
    env=env,
    description="LCopilot Reliability-as-a-Service Enterprise Tier Infrastructure",
    tags={
        "Project": "LCopilot",
        "Tier": "Enterprise",
        "Environment": environment,
        "CostCenter": "Reliability",
        "Owner": "Platform Team"
    }
)

# Enterprise Customer-Specific Stacks
enterprise_customers = app.node.try_get_context("enterprise_customers") or []

for customer_config in enterprise_customers:
    customer_id = customer_config.get("customer_id")
    white_label_domain = customer_config.get("white_label_domain")
    customer_alert_email = customer_config.get("alert_email")

    if customer_id:
        customer_stack = LCopilotReliabilityStack(
            app, f"LCopilotReliabilityEnterprise{customer_id.title()}",
            tier=ReliabilityTier.ENTERPRISE,
            customer_id=customer_id,
            white_label_domain=white_label_domain,
            alert_email=customer_alert_email or alert_email,
            env=env,
            description=f"LCopilot Reliability-as-a-Service for Enterprise Customer {customer_id}",
            tags={
                "Project": "LCopilot",
                "Tier": "Enterprise",
                "Environment": environment,
                "CustomerID": customer_id,
                "CostCenter": "Reliability",
                "Owner": "Platform Team",
                "CustomerName": customer_config.get("name", customer_id)
            }
        )

# Development Environment Stacks (if in dev mode)
if environment == "dev":
    dev_stack = LCopilotReliabilityStack(
        app, "LCopilotReliabilityDev",
        tier=ReliabilityTier.ENTERPRISE,
        customer_id="dev-test",
        alert_email=alert_email,
        env=env,
        description="LCopilot Reliability-as-a-Service Development Environment",
        tags={
            "Project": "LCopilot",
            "Tier": "Enterprise",
            "Environment": "development",
            "CostCenter": "Development",
            "Owner": "Platform Team",
            "Purpose": "Testing"
        }
    )

app.synth()