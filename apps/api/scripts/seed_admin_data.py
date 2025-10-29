#!/usr/bin/env python3
"""
Admin Console Seed Data Script

Creates demo data for the Admin Console including:
- Admin users and roles
- Sample organizations and tenants
- Mock billing data and disputes
- Partner integrations
- Job queue entries
- Feature flags
- Audit events
- LLM usage data

Usage:
    python scripts/seed_admin_data.py [--reset]
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timedelta, date
from decimal import Decimal
import random
import uuid
import hashlib
import json

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.admin import *
from app.models.user import User
from app.models.organization import Organization

# Faker for generating realistic test data
try:
    from faker import Faker
    fake = Faker()
except ImportError:
    print("Installing faker for realistic test data...")
    os.system("pip install faker")
    from faker import Faker
    fake = Faker()


class AdminDataSeeder:
    """Seed admin console with demo data"""

    def __init__(self, db: Session):
        self.db = db

    def seed_all(self, reset=False):
        """Seed all admin data"""
        print("🌱 Seeding Admin Console data...")

        if reset:
            self.reset_data()

        self.seed_admin_roles()
        self.seed_organizations()
        self.seed_users()
        self.seed_admin_users()
        self.seed_billing_data()
        self.seed_partner_data()
        self.seed_job_data()
        self.seed_feature_flags()
        self.seed_audit_events()
        self.seed_llm_data()
        self.seed_compliance_data()

        print("✅ Admin Console seeding complete!")

    def reset_data(self):
        """Reset all admin tables (careful!)"""
        print("🗑️  Resetting admin data...")

        # Drop all admin tables in reverse dependency order
        tables_to_reset = [
            'flag_evaluations', 'feature_flags', 'release_notes',
            'llm_budgets', 'llm_eval_runs', 'llm_prompts',
            'legal_holds', 'retention_policies', 'data_residency_policies',
            'user_sessions', 'ip_allowlists', 'service_accounts', 'api_keys',
            'webhook_dlq', 'webhook_deliveries', 'partner_connectors', 'partner_registry',
            'disputes', 'credits', 'billing_adjustments',
            'jobs_history', 'jobs_dlq', 'jobs_queue',
            'break_glass_events', 'approvals', 'audit_events',
            'admin_users', 'admin_roles'
        ]

        for table in tables_to_reset:
            try:
                self.db.execute(f"DELETE FROM {table}")
                print(f"  Cleared {table}")
            except Exception as e:
                print(f"  Warning: Could not clear {table}: {e}")

        self.db.commit()

    def seed_admin_roles(self):
        """Create admin roles with permissions"""
        print("👥 Creating admin roles...")

        roles_data = [
            {
                'name': 'super_admin',
                'description': 'Super administrator with all permissions',
                'permissions': ['*']
            },
            {
                'name': 'ops_admin',
                'description': 'Operations administrator',
                'permissions': [
                    'ops:read', 'ops:write', 'jobs:read', 'jobs:write',
                    'monitoring:read', 'feature_flags:read', 'feature_flags:write',
                    'users:read'
                ]
            },
            {
                'name': 'security_admin',
                'description': 'Security administrator',
                'permissions': [
                    'audit:read', 'audit:export', 'users:read', 'users:write',
                    'api_keys:read', 'api_keys:write', 'sessions:read', 'sessions:write',
                    'approvals:read', 'approvals:write', 'break_glass:read'
                ]
            },
            {
                'name': 'finance_admin',
                'description': 'Finance administrator',
                'permissions': [
                    'billing:read', 'billing:write', 'credits:read', 'credits:write',
                    'disputes:read', 'disputes:write', 'approvals:read', 'approvals:write'
                ]
            },
            {
                'name': 'partner_admin',
                'description': 'Partner integration administrator',
                'permissions': [
                    'partners:read', 'partners:write', 'webhooks:read', 'webhooks:write',
                    'integrations:read', 'integrations:write'
                ]
            },
            {
                'name': 'compliance_admin',
                'description': 'Compliance and data governance administrator',
                'permissions': [
                    'audit:read', 'audit:export', 'data_residency:read', 'data_residency:write',
                    'retention:read', 'retention:write', 'legal_holds:read', 'legal_holds:write'
                ]
            }
        ]

        for role_data in roles_data:
            role = AdminRole(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            self.db.add(role)

        self.db.commit()
        print(f"  Created {len(roles_data)} admin roles")

    def seed_organizations(self):
        """Create demo organizations"""
        print("🏢 Creating demo organizations...")

        orgs_data = [
            {
                'name': 'DemoCo Ltd',
                'type': 'sme',
                'country': 'BD',
                'email': 'admin@democorp.com'
            },
            {
                'name': 'Acme Logistics',
                'type': 'sme',
                'country': 'BD',
                'email': 'ops@acmelogistics.com'
            },
            {
                'name': 'BankOne',
                'type': 'bank',
                'country': 'BD',
                'email': 'tech@bankone.com'
            },
            {
                'name': 'GlobalTrade Inc',
                'type': 'sme',
                'country': 'SG',
                'email': 'trading@globaltrade.com'
            },
            {
                'name': 'EuroBank',
                'type': 'bank',
                'country': 'EU',
                'email': 'digital@eurobank.com'
            }
        ]

        for org_data in orgs_data:
            # Check if organization already exists
            existing = self.db.query(Organization).filter(
                Organization.name == org_data['name']
            ).first()

            if not existing:
                org = Organization(
                    name=org_data['name'],
                    type=org_data['type'],
                    country=org_data['country'],
                    email=org_data['email'],
                    is_active=True
                )
                self.db.add(org)

        self.db.commit()
        print(f"  Created {len(orgs_data)} organizations")

    def seed_users(self):
        """Create demo users"""
        print("👤 Creating demo users...")

        # Get organizations
        orgs = self.db.query(Organization).all()
        org_map = {org.name: org.id for org in orgs}

        users_data = [
            {
                'name': 'John Smith',
                'email': 'admin@lcopilot.com',
                'role': 'admin',
                'organization_id': None  # System admin
            },
            {
                'name': 'Sarah Johnson',
                'email': 'ops@lcopilot.com',
                'role': 'admin',
                'organization_id': None
            },
            {
                'name': 'Mike Chen',
                'email': 'security@lcopilot.com',
                'role': 'admin',
                'organization_id': None
            },
            {
                'name': 'Lisa Rodriguez',
                'email': 'finance@lcopilot.com',
                'role': 'admin',
                'organization_id': None
            },
            {
                'name': 'Ahmed Rahman',
                'email': 'ahmed@democorp.com',
                'role': 'manager',
                'organization_id': org_map.get('DemoCo Ltd')
            },
            {
                'name': 'Emma Wilson',
                'email': 'emma@acmelogistics.com',
                'role': 'user',
                'organization_id': org_map.get('Acme Logistics')
            },
            {
                'name': 'David Kumar',
                'email': 'david@bankone.com',
                'role': 'bank_admin',
                'organization_id': org_map.get('BankOne')
            }
        ]

        for user_data in users_data:
            # Check if user already exists
            existing = self.db.query(User).filter(
                User.email == user_data['email']
            ).first()

            if not existing:
                user = User(
                    name=user_data['name'],
                    email=user_data['email'],
                    role=user_data['role'],
                    organization_id=user_data['organization_id'],
                    is_active=True,
                    email_verified=True
                )
                self.db.add(user)

        self.db.commit()
        print(f"  Created {len(users_data)} users")

    def seed_admin_users(self):
        """Assign admin roles to users"""
        print("🔐 Creating admin user assignments...")

        # Get admin roles
        roles = self.db.query(AdminRole).all()
        role_map = {role.name: role.id for role in roles}

        # Get admin users
        admin_users = self.db.query(User).filter(
            User.email.in_([
                'admin@lcopilot.com',
                'ops@lcopilot.com',
                'security@lcopilot.com',
                'finance@lcopilot.com'
            ])
        ).all()

        admin_assignments = [
            ('admin@lcopilot.com', 'super_admin'),
            ('ops@lcopilot.com', 'ops_admin'),
            ('security@lcopilot.com', 'security_admin'),
            ('finance@lcopilot.com', 'finance_admin')
        ]

        for email, role_name in admin_assignments:
            user = next((u for u in admin_users if u.email == email), None)
            if user and role_name in role_map:
                admin_user = AdminUser(
                    user_id=user.id,
                    role_id=role_map[role_name],
                    granted_by=user.id,  # Self-granted for seed data
                    is_active=True
                )
                self.db.add(admin_user)

        self.db.commit()
        print(f"  Created {len(admin_assignments)} admin assignments")

    def seed_billing_data(self):
        """Create billing, credits, and disputes data"""
        print("💳 Creating billing data...")

        # Get organizations
        orgs = self.db.query(Organization).all()
        users = self.db.query(User).all()
        finance_admin = self.db.query(User).filter(
            User.email == 'finance@lcopilot.com'
        ).first()

        # Create credits/promotions
        credits_data = [
            {
                'code': 'WELCOME10',
                'type': CreditType.PERCENTAGE,
                'percentage': 10,
                'max_uses': 100,
                'valid_until': datetime.utcnow() + timedelta(days=90),
                'applicable_plans': ['starter', 'pro']
            },
            {
                'code': 'PARTNER25',
                'type': CreditType.PERCENTAGE,
                'percentage': 25,
                'max_uses': 50,
                'valid_until': datetime.utcnow() + timedelta(days=180),
                'applicable_plans': ['enterprise']
            },
            {
                'code': 'BLACKFRIDAY',
                'type': CreditType.FIXED_AMOUNT,
                'value_usd': Decimal('50.00'),
                'max_uses': 200,
                'valid_until': datetime.utcnow() + timedelta(days=30)
            }
        ]

        for credit_data in credits_data:
            credit = Credit(
                code=credit_data['code'],
                type=credit_data['type'],
                value_usd=credit_data.get('value_usd'),
                percentage=credit_data.get('percentage'),
                max_uses=credit_data['max_uses'],
                uses_count=random.randint(0, credit_data['max_uses'] // 2),
                valid_until=credit_data['valid_until'],
                applicable_plans=credit_data.get('applicable_plans', []),
                created_by=finance_admin.id if finance_admin else users[0].id,
                is_active=True
            )
            self.db.add(credit)

        # Create billing adjustments
        for i in range(5):
            org = random.choice(orgs)
            adjustment = BillingAdjustment(
                organization_id=org.id,
                type=random.choice(list(AdjustmentType)),
                amount_usd=Decimal(str(random.uniform(10.0, 500.0))),
                reason=fake.sentence(),
                applied_by=finance_admin.id if finance_admin else users[0].id,
                approved_by=finance_admin.id if finance_admin else users[0].id,
                status=random.choice(list(AdjustmentStatus)),
                approved_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            self.db.add(adjustment)

        # Create disputes
        for i in range(3):
            org = random.choice(orgs)
            dispute = Dispute(
                invoice_id=uuid.uuid4(),
                organization_id=org.id,
                type=random.choice(list(DisputeType)),
                amount_usd=Decimal(str(random.uniform(100.0, 2000.0))),
                reason=fake.paragraph(),
                status=random.choice(list(DisputeStatus)),
                assigned_to=finance_admin.id if finance_admin else None
            )
            self.db.add(dispute)

        self.db.commit()
        print(f"  Created {len(credits_data)} credits, 5 adjustments, 3 disputes")

    def seed_partner_data(self):
        """Create partner registry and webhook data"""
        print("🤝 Creating partner data...")

        # Create partners
        partners_data = [
            {
                'name': 'BankOne API',
                'type': PartnerType.BANK,
                'environment': EnvironmentType.PRODUCTION,
                'api_endpoint': 'https://api.bankone.com/v1',
                'contact_email': 'api@bankone.com'
            },
            {
                'name': 'CustomsBD Sandbox',
                'type': PartnerType.CUSTOMS,
                'environment': EnvironmentType.SANDBOX,
                'api_endpoint': 'https://sandbox.customs.gov.bd/api',
                'contact_email': 'tech@customs.gov.bd'
            },
            {
                'name': 'DHL Logistics',
                'type': PartnerType.LOGISTICS,
                'environment': EnvironmentType.PRODUCTION,
                'api_endpoint': 'https://api.dhl.com/shipping/v2',
                'contact_email': 'developers@dhl.com'
            },
            {
                'name': 'TestBank Staging',
                'type': PartnerType.BANK,
                'environment': EnvironmentType.STAGING,
                'api_endpoint': 'https://staging.testbank.com/api',
                'contact_email': 'staging@testbank.com'
            }
        ]

        partner_objects = []
        for partner_data in partners_data:
            partner = PartnerRegistry(
                name=partner_data['name'],
                type=partner_data['type'],
                environment=partner_data['environment'],
                status=PartnerStatus.ACTIVE,
                api_endpoint=partner_data['api_endpoint'],
                auth_config={
                    'type': 'oauth2',
                    'client_id': f"client_{uuid.uuid4().hex[:8]}",
                    'scopes': ['read', 'write']
                },
                rate_limits={
                    'requests_per_minute': 100,
                    'burst_limit': 200
                },
                contact_email=partner_data['contact_email'],
                health_status='healthy',
                last_health_check=datetime.utcnow(),
                metadata={'created_by': 'seed_script'}
            )
            self.db.add(partner)
            partner_objects.append(partner)

        self.db.flush()  # Get IDs

        # Create partner connectors
        for partner in partner_objects:
            connector = PartnerConnector(
                partner_id=partner.id,
                connector_type=f"{partner.type.value}_connector",
                version="v1.2.3",
                config={'timeout': 30, 'retries': 3},
                status=random.choice(list(ConnectorStatus)),
                success_count=random.randint(100, 1000),
                failure_count=random.randint(0, 50),
                avg_response_time_ms=random.randint(50, 300),
                uptime_percentage=Decimal(str(random.uniform(95.0, 99.9)))
            )
            self.db.add(connector)

        # Create webhook deliveries
        for partner in partner_objects:
            for i in range(random.randint(2, 8)):
                delivery = WebhookDelivery(
                    partner_id=partner.id,
                    webhook_url=f"https://{partner.name.lower().replace(' ', '')}.com/webhooks/lcopilot",
                    event_type=random.choice(['lc_created', 'payment_received', 'document_validated']),
                    payload={'event_id': str(uuid.uuid4()), 'data': {'lc_id': f'LC{random.randint(1000, 9999)}'}},
                    status=random.choice(list(DeliveryStatus)),
                    attempts=random.randint(1, 3),
                    http_status=random.choice([200, 201, 400, 500, None]),
                    delivery_time_ms=random.randint(100, 2000) if random.choice([True, False]) else None,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 7))
                )
                self.db.add(delivery)

        self.db.commit()
        print(f"  Created {len(partners_data)} partners with connectors and webhooks")

    def seed_job_data(self):
        """Create job queue and DLQ data"""
        print("⚙️ Creating job data...")

        # Get organizations and users
        orgs = self.db.query(Organization).all()
        users = self.db.query(User).all()

        job_types = [
            'lc_validation',
            'document_ocr',
            'discrepancy_analysis',
            'notification_send',
            'report_generation',
            'data_export',
            'partner_sync',
            'webhook_delivery'
        ]

        # Create jobs in various states
        for i in range(25):
            org = random.choice(orgs)
            user = random.choice([u for u in users if u.organization_id == org.id])

            job = JobQueue(
                job_type=random.choice(job_types),
                job_data={
                    'lc_id': f'LC{random.randint(1000, 9999)}',
                    'user_id': str(user.id) if user else None,
                    'parameters': {
                        'priority': random.choice(['high', 'normal', 'low']),
                        'timeout': random.randint(30, 300)
                    }
                },
                priority=random.randint(1, 10),
                status=random.choice(list(JobStatus)),
                attempts=random.randint(0, 3),
                max_attempts=3,
                scheduled_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 1440)),
                organization_id=org.id,
                user_id=user.id if user else None,
                lc_id=f'LC{random.randint(1000, 9999)}'
            )

            # Set timing based on status
            if job.status in [JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED]:
                job.started_at = job.scheduled_at + timedelta(seconds=random.randint(1, 300))

            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completed_at = job.started_at + timedelta(seconds=random.randint(10, 600))

            if job.status == JobStatus.FAILED:
                job.failed_at = job.completed_at
                job.error_message = fake.sentence()

            self.db.add(job)

        self.db.flush()

        # Create some DLQ entries
        failed_jobs = self.db.query(JobQueue).filter(
            JobQueue.status == JobStatus.FAILED
        ).limit(5).all()

        for job in failed_jobs:
            dlq_entry = JobDLQ(
                original_job_id=job.id,
                job_type=job.job_type,
                job_data=job.job_data,
                failure_reason=job.error_message or "Unknown error",
                failure_count=job.attempts,
                last_error=fake.sentence(),
                can_retry=random.choice([True, False])
            )
            self.db.add(dlq_entry)

        self.db.commit()
        print(f"  Created 25 jobs and {len(failed_jobs)} DLQ entries")

    def seed_feature_flags(self):
        """Create feature flags"""
        print("🚩 Creating feature flags...")

        # Get admin user
        admin_user = self.db.query(User).filter(
            User.email == 'admin@lcopilot.com'
        ).first()

        flags_data = [
            {
                'name': 'ai_discrepancy_analysis',
                'description': 'Enable AI-powered discrepancy analysis',
                'type': FlagType.BOOLEAN,
                'default_value': True,
                'rollout_percentage': 75
            },
            {
                'name': 'new_dashboard_ui',
                'description': 'Enable new dashboard UI design',
                'type': FlagType.BOOLEAN,
                'default_value': False,
                'rollout_percentage': 25
            },
            {
                'name': 'max_file_upload_size',
                'description': 'Maximum file upload size in MB',
                'type': FlagType.NUMBER,
                'default_value': 50,
                'rollout_percentage': 100
            },
            {
                'name': 'partner_api_version',
                'description': 'Default partner API version',
                'type': FlagType.STRING,
                'default_value': 'v2.1',
                'rollout_percentage': 100
            },
            {
                'name': 'advanced_analytics',
                'description': 'Enable advanced analytics features',
                'type': FlagType.BOOLEAN,
                'default_value': False,
                'rollout_percentage': 10
            }
        ]

        for flag_data in flags_data:
            flag = FeatureFlag(
                name=flag_data['name'],
                description=flag_data['description'],
                type=flag_data['type'],
                default_value=flag_data['default_value'],
                rollout_percentage=flag_data['rollout_percentage'],
                is_active=True,
                created_by=admin_user.id if admin_user else uuid.uuid4(),
                targeting_rules={
                    'user_types': ['sme', 'bank'],
                    'regions': ['BD', 'SG']
                }
            )
            self.db.add(flag)

        self.db.commit()
        print(f"  Created {len(flags_data)} feature flags")

    def seed_audit_events(self):
        """Create audit events"""
        print("📋 Creating audit events...")

        # Get users and organizations
        users = self.db.query(User).all()
        orgs = self.db.query(Organization).all()

        event_types = [
            'user_login', 'user_logout', 'lc_created', 'lc_updated',
            'payment_processed', 'document_uploaded', 'api_key_created',
            'role_changed', 'plan_upgraded', 'dispute_created'
        ]

        actions = [
            'create', 'update', 'delete', 'view', 'download',
            'approve', 'reject', 'process', 'validate', 'export'
        ]

        resource_types = [
            'user', 'organization', 'lc', 'document', 'payment',
            'api_key', 'webhook', 'report', 'audit_log', 'feature_flag'
        ]

        # Create audit events for the last 30 days
        for i in range(100):
            user = random.choice(users)
            org = random.choice(orgs) if random.choice([True, False]) else None

            event = AuditEvent(
                event_type=random.choice(event_types),
                actor_id=user.id,
                actor_type='user',
                resource_type=random.choice(resource_types),
                resource_id=f"{random.choice(resource_types)}_{random.randint(1000, 9999)}",
                organization_id=org.id if org else user.organization_id,
                action=random.choice(actions),
                changes={
                    'field_changed': fake.word(),
                    'old_value': fake.word(),
                    'new_value': fake.word()
                } if random.choice([True, False]) else None,
                metadata={
                    'session_id': f"session_{uuid.uuid4().hex[:8]}",
                    'request_id': f"req_{uuid.uuid4().hex[:8]}",
                    'duration_ms': random.randint(10, 1000)
                },
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent(),
                session_id=f"session_{uuid.uuid4().hex[:8]}",
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            self.db.add(event)

        self.db.commit()
        print("  Created 100 audit events")

    def seed_llm_data(self):
        """Create LLM prompts, budgets, and evaluation data"""
        print("🧠 Creating LLM data...")

        # Get admin user and organizations
        admin_user = self.db.query(User).filter(
            User.email == 'admin@lcopilot.com'
        ).first()
        orgs = self.db.query(Organization).all()

        # Create LLM prompts
        prompts_data = [
            {
                'name': 'discrepancy_analysis',
                'version': 'v1.0',
                'prompt_type': 'analysis',
                'system_prompt': 'You are an expert trade finance analyst...',
                'user_template': 'Analyze the following discrepancies: {discrepancies}',
                'language': PromptLanguage.EN
            },
            {
                'name': 'discrepancy_analysis',
                'version': 'v1.1',
                'prompt_type': 'analysis',
                'system_prompt': 'You are an expert trade finance analyst with improved context...',
                'user_template': 'Analyze the following discrepancies with context: {discrepancies}',
                'language': PromptLanguage.EN
            },
            {
                'name': 'bank_draft_generation',
                'version': 'v1.0',
                'prompt_type': 'generation',
                'system_prompt': 'You are a banking professional drafting formal correspondence...',
                'user_template': 'Draft a formal letter for: {purpose}',
                'language': PromptLanguage.EN
            }
        ]

        for prompt_data in prompts_data:
            prompt = LLMPrompt(
                name=prompt_data['name'],
                version=prompt_data['version'],
                prompt_type=prompt_data['prompt_type'],
                system_prompt=prompt_data['system_prompt'],
                user_template=prompt_data['user_template'],
                language=prompt_data['language'],
                model_constraints={'max_tokens': 2000, 'temperature': 0.7},
                safety_filters={'toxicity': True, 'pii': True},
                is_active=True,
                created_by=admin_user.id if admin_user else uuid.uuid4(),
                approved_by=admin_user.id if admin_user else uuid.uuid4(),
                performance_metrics={
                    'avg_latency_ms': random.randint(500, 2000),
                    'success_rate': random.uniform(0.9, 0.99)
                }
            )
            self.db.add(prompt)

        # Create LLM budgets for organizations
        for org in orgs[:3]:  # First 3 orgs
            budget = LLMBudget(
                organization_id=org.id,
                model_name=random.choice(['gpt-4', 'gpt-3.5-turbo', 'claude-3-sonnet']),
                budget_period=BudgetPeriod.MONTHLY,
                budget_usd=Decimal(str(random.uniform(100.0, 1000.0))),
                used_usd=Decimal(str(random.uniform(10.0, 500.0))),
                token_budget=random.randint(10000, 100000),
                tokens_used=random.randint(1000, 50000),
                alert_threshold_percent=80,
                hard_limit_enabled=random.choice([True, False]),
                period_start=date.today().replace(day=1),
                period_end=date.today().replace(day=28),
                created_by=admin_user.id if admin_user else uuid.uuid4()
            )
            self.db.add(budget)

        self.db.commit()
        print(f"  Created {len(prompts_data)} prompts and {len(orgs[:3])} budgets")

    def seed_compliance_data(self):
        """Create compliance and data governance data"""
        print("🛡️ Creating compliance data...")

        # Get admin user and organizations
        compliance_admin = self.db.query(User).filter(
            User.email == 'security@lcopilot.com'
        ).first()
        orgs = self.db.query(Organization).all()

        # Create data residency policies
        for org in orgs[:3]:
            policy = DataResidencyPolicy(
                organization_id=org.id,
                region=DataRegion.BD if org.country == 'BD' else DataRegion.EU,
                data_types=['user_data', 'transaction_data', 'documents'],
                storage_location=f"datacenter-{org.country.lower()}",
                encryption_key_id=f"key_{uuid.uuid4().hex[:8]}",
                compliance_frameworks=['GDPR', 'ISO27001'],
                is_active=True,
                created_by=compliance_admin.id if compliance_admin else uuid.uuid4(),
                approved_by=compliance_admin.id if compliance_admin else uuid.uuid4()
            )
            self.db.add(policy)

        # Create retention policies
        retention_policies_data = [
            {
                'name': 'Transaction Data Retention',
                'data_type': 'transaction_data',
                'retention_period_days': 2555,  # 7 years
                'legal_basis': 'Financial regulations'
            },
            {
                'name': 'User Activity Logs',
                'data_type': 'activity_logs',
                'retention_period_days': 365,  # 1 year
                'legal_basis': 'Security monitoring'
            },
            {
                'name': 'Document Storage',
                'data_type': 'documents',
                'retention_period_days': 1825,  # 5 years
                'legal_basis': 'Trade finance requirements'
            }
        ]

        for policy_data in retention_policies_data:
            policy = RetentionPolicy(
                name=policy_data['name'],
                data_type=policy_data['data_type'],
                retention_period_days=policy_data['retention_period_days'],
                archive_after_days=policy_data['retention_period_days'] // 2,
                delete_after_days=policy_data['retention_period_days'],
                legal_basis=policy_data['legal_basis'],
                applies_to_regions=[DataRegion.BD, DataRegion.EU, DataRegion.SG],
                is_active=True,
                created_by=compliance_admin.id if compliance_admin else uuid.uuid4(),
                approved_by=compliance_admin.id if compliance_admin else uuid.uuid4()
            )
            self.db.add(policy)

        # Create a legal hold
        legal_hold = LegalHold(
            case_number='CASE-2024-001',
            title='Regulatory Investigation - DemoCo Transaction',
            description='Legal hold for regulatory investigation into suspicious transactions',
            organization_id=orgs[0].id if orgs else None,
            data_types=['transaction_data', 'documents', 'communications'],
            date_range_start=date.today() - timedelta(days=180),
            date_range_end=date.today(),
            search_terms=['LC2024001', 'suspicious', 'investigation'],
            status=LegalHoldStatus.ACTIVE,
            created_by=compliance_admin.id if compliance_admin else uuid.uuid4(),
            legal_contact={
                'name': 'Jane Legal',
                'email': 'legal@lawfirm.com',
                'phone': '+1-555-0123'
            }
        )
        self.db.add(legal_hold)

        self.db.commit()
        print(f"  Created {len(orgs[:3])} residency policies, {len(retention_policies_data)} retention policies, 1 legal hold")


def create_makefile_targets():
    """Create Makefile targets for easy demo setup"""
    makefile_content = '''
# Admin Console Demo Setup Targets

.PHONY: db_migrate db_seed_admin admin_demo_login help

db_migrate:
	@echo "🔄 Running database migrations..."
	cd apps/api && alembic upgrade head

db_seed_admin:
	@echo "🌱 Seeding admin demo data..."
	cd apps/api && python scripts/seed_admin_data.py

admin_demo_login:
	@echo "🔑 Admin Demo Login Credentials:"
	@echo ""
	@echo "Super Admin:"
	@echo "  Email: admin@lcopilot.com"
	@echo "  Password: admin123"
	@echo ""
	@echo "Operations Admin:"
	@echo "  Email: ops@lcopilot.com"
	@echo "  Password: ops123"
	@echo ""
	@echo "Security Admin:"
	@echo "  Email: security@lcopilot.com"
	@echo "  Password: security123"
	@echo ""
	@echo "Finance Admin:"
	@echo "  Email: finance@lcopilot.com"
	@echo "  Password: finance123"
	@echo ""
	@echo "🌐 Admin Console URL: http://localhost:3000/admin"

admin_demo: db_migrate db_seed_admin admin_demo_login
	@echo "✅ Admin Console demo setup complete!"

help:
	@echo "Available admin targets:"
	@echo "  admin_demo      - Full admin demo setup (migrate + seed + show login)"
	@echo "  db_migrate      - Run database migrations"
	@echo "  db_seed_admin   - Seed admin demo data"
	@echo "  admin_demo_login - Show admin login credentials"
'''

    with open('../../Makefile', 'a') as f:
        f.write('\n# Admin Console Targets\n')
        f.write(makefile_content)

    print("📝 Added Makefile targets for admin demo")


def main():
    """Main seeding function"""
    parser = argparse.ArgumentParser(description='Seed admin console data')
    parser.add_argument('--reset', action='store_true',
                       help='Reset existing data before seeding')
    parser.add_argument('--makefile', action='store_true',
                       help='Create Makefile targets')

    args = parser.parse_args()

    print("🚀 LCopilot Admin Console Data Seeder")
    print("=====================================")

    if args.makefile:
        create_makefile_targets()
        return

    # Create database session
    db = SessionLocal()

    try:
        seeder = AdminDataSeeder(db)
        seeder.seed_all(reset=args.reset)

        print("\n🎉 Seeding completed successfully!")
        print("\n📋 Demo Login Credentials:")
        print("  Super Admin:    admin@lcopilot.com / admin123")
        print("  Ops Admin:      ops@lcopilot.com / ops123")
        print("  Security Admin: security@lcopilot.com / security123")
        print("  Finance Admin:  finance@lcopilot.com / finance123")
        print("\n🌐 Access Admin Console at: http://localhost:3000/admin")

    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()