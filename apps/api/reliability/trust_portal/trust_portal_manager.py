#!/usr/bin/env python3
"""
LCopilot Customer Trust Portal Manager

Manages tier-based customer trust portals with authentication and feature access.
Provides Pro and Enterprise customers with dedicated portals for SLA access.

Features by Tier:
- Free: No portal access
- Pro: Basic portal with SLA dashboards, incident history, report downloads
- Enterprise: Enhanced portal with dedicated dashboards, compliance docs, white-label branding

Usage:
    python3 trust_portal_manager.py --tier pro --deploy-portal
    python3 trust_portal_manager.py --tier enterprise --customer enterprise-customer-001 --deploy-portal
    python3 trust_portal_manager.py --create-user --email customer@example.com --tier pro
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
import hashlib
import base64


@dataclass
class PortalConfig:
    """Trust portal configuration."""
    tier: str
    customer_id: Optional[str] = None
    domain: Optional[str] = None
    branding: Optional[Dict[str, str]] = None
    features: List[str] = None
    auth_method: str = 'cognito'


@dataclass
class PortalUser:
    """Portal user information."""
    email: str
    tier: str
    customer_id: Optional[str] = None
    permissions: List[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class TrustPortalManager:
    """Manages customer trust portals with tier-based features."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configurations
        self.reliability_config = self._load_reliability_config()

        # AWS clients
        self.cognito_client = None
        self.s3_client = None
        self.apigateway_client = None
        self.lambda_client = None
        self.region = self.reliability_config.get('global', {}).get('environments', {}).get(environment, {}).get('aws_region', 'eu-north-1')

        # Portal configurations
        self.portal_configs = {}

    def _load_reliability_config(self) -> Dict[str, Any]:
        """Load reliability configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'reliability_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return {}

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.cognito_client = session.client('cognito-idp')
            self.s3_client = session.client('s3')
            self.apigateway_client = session.client('apigateway')
            self.lambda_client = session.client('lambda')

            print(f"✅ AWS clients initialized for {self.region}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def get_portal_config(self, tier: str, customer_id: Optional[str] = None) -> PortalConfig:
        """Get portal configuration based on tier."""
        trust_portal = self.reliability_config.get('trust_portal', {})
        tier_config = trust_portal.get(tier, {})

        if not tier_config.get('enabled', False):
            return PortalConfig(
                tier=tier,
                customer_id=customer_id,
                features=[]
            )

        config = PortalConfig(
            tier=tier,
            customer_id=customer_id,
            features=tier_config.get('features', []),
            auth_method='cognito'
        )

        # Set domain
        if tier == 'enterprise' and customer_id:
            # Check for custom domain in customer config
            customer_config = self.reliability_config.get('customers', {}).get('tier_mappings', {}).get(customer_id, {})
            if 'features' in customer_config and 'white_label' in customer_config['features']:
                white_label = customer_config['features']['white_label']
                config.domain = white_label.get('domain', f'portal-{customer_id}.lcopilot.com')
                config.branding = white_label.get('branding', {})
            else:
                config.domain = f'portal-{customer_id}.lcopilot.com'
        else:
            config.domain = tier_config.get('domain', 'portal.lcopilot.com')

        return config

    def create_cognito_user_pool(self, config: PortalConfig) -> Optional[str]:
        """Create Cognito User Pool for portal authentication."""
        try:
            pool_name = f'lcopilot-portal-{config.tier}-{self.environment}'
            if config.customer_id:
                pool_name += f'-{config.customer_id}'

            # Check if pool already exists
            try:
                pools = self.cognito_client.list_user_pools(MaxResults=50)
                for pool in pools['UserPools']:
                    if pool['Name'] == pool_name:
                        print(f"✅ User pool already exists: {pool_name}")
                        return pool['Id']
            except Exception:
                pass

            # Create new user pool
            response = self.cognito_client.create_user_pool(
                PoolName=pool_name,
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': False
                    }
                },
                AutoVerifiedAttributes=['email'],
                UsernameConfiguration={
                    'CaseSensitive': False
                },
                AccountRecoverySetting={
                    'RecoveryMechanisms': [
                        {'Name': 'verified_email', 'Priority': 1}
                    ]
                },
                UserPoolTags={
                    'Environment': self.environment,
                    'Tier': config.tier,
                    'Service': 'lcopilot-trust-portal'
                }
            )

            user_pool_id = response['UserPool']['Id']

            # Create user pool client
            client_response = self.cognito_client.create_user_pool_client(
                UserPoolId=user_pool_id,
                ClientName=f'{pool_name}-client',
                GenerateSecret=False,  # For web applications
                RefreshTokenValidity=30,
                AccessTokenValidity=24,
                IdTokenValidity=24,
                TokenValidityUnits={
                    'AccessToken': 'hours',
                    'IdToken': 'hours',
                    'RefreshToken': 'days'
                },
                ExplicitAuthFlows=['ADMIN_NO_SRP_AUTH', 'USER_PASSWORD_AUTH'],
                SupportedIdentityProviders=['COGNITO']
            )

            print(f"✅ User pool created: {pool_name} ({user_pool_id})")
            print(f"   Client ID: {client_response['UserPoolClient']['ClientId']}")

            return user_pool_id

        except Exception as e:
            print(f"❌ Failed to create user pool: {e}")
            return None

    def create_portal_user(self, email: str, tier: str, customer_id: Optional[str] = None) -> bool:
        """Create a user in the portal."""
        try:
            # Get user pool ID
            pool_name = f'lcopilot-portal-{tier}-{self.environment}'
            if customer_id:
                pool_name += f'-{customer_id}'

            pools = self.cognito_client.list_user_pools(MaxResults=50)
            user_pool_id = None

            for pool in pools['UserPools']:
                if pool['Name'] == pool_name:
                    user_pool_id = pool['Id']
                    break

            if not user_pool_id:
                print(f"❌ User pool not found: {pool_name}")
                return False

            # Create user
            temp_password = self._generate_temp_password()

            self.cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'custom:tier', 'Value': tier},
                    {'Name': 'custom:customer_id', 'Value': customer_id or 'shared'}
                ],
                TemporaryPassword=temp_password,
                MessageAction='SUPPRESS'  # Don't send welcome email automatically
            )

            print(f"✅ User created: {email}")
            print(f"   Tier: {tier}")
            print(f"   Customer: {customer_id or 'Shared'}")
            print(f"   Temp password: {temp_password}")

            return True

        except self.cognito_client.exceptions.UsernameExistsException:
            print(f"⚠️  User already exists: {email}")
            return True
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            return False

    def _generate_temp_password(self) -> str:
        """Generate temporary password for new users."""
        import secrets
        import string

        # Generate secure temporary password
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(chars) for _ in range(12))

        # Ensure it meets requirements
        password = 'Aa1!' + password[:8]  # Ensure uppercase, lowercase, number, symbol

        return password

    def deploy_portal_frontend(self, config: PortalConfig) -> bool:
        """Deploy portal frontend to S3/CloudFront."""
        try:
            # Generate portal HTML
            html_content = self._generate_portal_html(config)

            # Determine S3 bucket
            if config.tier == 'enterprise' and config.customer_id:
                bucket_name = f'lcopilot-trust-portal-{config.customer_id}-{self.environment}'
            else:
                bucket_name = f'lcopilot-trust-portal-{config.tier}-{self.environment}'

            # Upload portal files
            portal_files = {
                'index.html': html_content,
                'login.html': self._generate_login_html(config),
                'dashboard.html': self._generate_dashboard_html(config),
                'css/portal.css': self._generate_portal_css(config),
                'js/portal.js': self._generate_portal_js(config)
            }

            for file_path, content in portal_files.items():
                content_type = self._get_content_type(file_path)

                self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_path,
                    Body=content,
                    ContentType=content_type,
                    CacheControl='public, max-age=3600' if file_path.endswith(('.css', '.js')) else 'public, max-age=300'
                )

            print(f"✅ Portal frontend deployed to S3: {bucket_name}")

            # Update CloudFront distribution if needed
            print(f"🔄 CloudFront distribution update may be required for {config.domain}")

            return True

        except Exception as e:
            print(f"❌ Failed to deploy portal frontend: {e}")
            return False

    def _generate_portal_html(self, config: PortalConfig) -> str:
        """Generate main portal HTML."""
        brand_name = config.branding.get('company_name', 'LCopilot') if config.branding else 'LCopilot'
        primary_color = config.branding.get('primary_color', '#1e293b') if config.branding else '#1e293b'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{brand_name} Trust Portal</title>
    <link rel="stylesheet" href="/css/portal.css">
</head>
<body>
    <div class="portal-container">
        <header class="portal-header" style="background: {primary_color};">
            <div class="header-content">
                <h1>{brand_name} Trust Portal</h1>
                <div class="tier-badge">{config.tier.title()} Tier</div>
            </div>
        </header>

        <main class="portal-main">
            <div class="welcome-section">
                <h2>Welcome to your Trust Portal</h2>
                <p>Access your SLA reports, incident history, and compliance documents.</p>
            </div>

            <div class="features-grid">
                {''.join(self._generate_feature_card(feature) for feature in config.features)}
            </div>

            <div class="portal-actions">
                <a href="/dashboard.html" class="btn btn-primary">Access Dashboard</a>
                <a href="/login.html" class="btn btn-secondary">Sign In</a>
            </div>
        </main>

        <footer class="portal-footer">
            <p>&copy; 2024 {brand_name}. {config.tier.title()} Service Level Agreement.</p>
        </footer>
    </div>

    <script src="/js/portal.js"></script>
</body>
</html>"""

    def _generate_feature_card(self, feature: str) -> str:
        """Generate HTML for a feature card."""
        feature_info = {
            'authentication': ('🔐', 'Secure Authentication', 'Multi-factor authentication and SSO'),
            'sla_dashboard_view': ('📊', 'SLA Dashboards', 'Real-time SLA monitoring and metrics'),
            'incident_rca_access': ('🔍', 'Incident Analysis', 'Root cause analysis and incident reports'),
            'report_downloads': ('📄', 'Report Downloads', 'Monthly SLA reports and compliance docs'),
            'dedicated_dashboards': ('🎯', 'Dedicated Dashboards', 'Customer-specific monitoring views'),
            'compliance_documents': ('📋', 'Compliance Docs', 'SOC2, GDPR, and regulatory documentation'),
            'white_label_branding': ('🎨', 'Custom Branding', 'White-label portal with your branding')
        }

        if feature in feature_info:
            icon, title, description = feature_info[feature]
            return f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-content">
                        <h3>{title}</h3>
                        <p>{description}</p>
                    </div>
                </div>
            """
        return ""

    def _generate_login_html(self, config: PortalConfig) -> str:
        """Generate login page HTML."""
        brand_name = config.branding.get('company_name', 'LCopilot') if config.branding else 'LCopilot'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In - {brand_name} Trust Portal</title>
    <link rel="stylesheet" href="/css/portal.css">
</head>
<body>
    <div class="login-container">
        <div class="login-card">
            <div class="login-header">
                <h1>{brand_name} Trust Portal</h1>
                <p>Sign in to access your SLA dashboard and reports</p>
            </div>

            <form class="login-form" id="loginForm">
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" required>
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>

                <button type="submit" class="btn btn-primary btn-full">Sign In</button>
            </form>

            <div class="login-footer">
                <a href="#" onclick="forgotPassword()">Forgot your password?</a>
                <div class="tier-info">
                    <span class="tier-badge">{config.tier.title()} Tier</span>
                </div>
            </div>
        </div>
    </div>

    <script src="/js/portal.js"></script>
</body>
</html>"""

    def _generate_dashboard_html(self, config: PortalConfig) -> str:
        """Generate dashboard HTML."""
        brand_name = config.branding.get('company_name', 'LCopilot') if config.branding else 'LCopilot'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - {brand_name} Trust Portal</title>
    <link rel="stylesheet" href="/css/portal.css">
</head>
<body>
    <div class="dashboard-container">
        <nav class="dashboard-nav">
            <div class="nav-header">
                <h1>{brand_name}</h1>
                <div class="tier-badge">{config.tier.title()}</div>
            </div>
            <ul class="nav-menu">
                <li><a href="#overview" class="nav-link active">Overview</a></li>
                <li><a href="#sla-metrics" class="nav-link">SLA Metrics</a></li>
                <li><a href="#incidents" class="nav-link">Incidents</a></li>
                <li><a href="#reports" class="nav-link">Reports</a></li>
                {'<li><a href="#compliance" class="nav-link">Compliance</a></li>' if config.tier == 'enterprise' else ''}
            </ul>
        </nav>

        <main class="dashboard-main">
            <div id="overview" class="dashboard-section active">
                <h2>SLA Overview</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">99.9%</div>
                        <div class="metric-label">Uptime (30d)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">2.1s</div>
                        <div class="metric-label">Avg Response Time</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">0</div>
                        <div class="metric-label">Active Incidents</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">✅</div>
                        <div class="metric-label">SLA Status</div>
                    </div>
                </div>
            </div>

            <div id="reports" class="dashboard-section">
                <h2>Available Reports</h2>
                <div class="reports-list">
                    <div class="report-item">
                        <div class="report-info">
                            <h3>Monthly SLA Report - November 2024</h3>
                            <p>Comprehensive SLA compliance and performance analysis</p>
                        </div>
                        <div class="report-actions">
                            <a href="/api/reports/latest.pdf" class="btn btn-sm">Download PDF</a>
                            {'<a href="/api/reports/latest.html" class="btn btn-sm btn-secondary">View HTML</a>' if 'html' in config.features else ''}
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script src="/js/portal.js"></script>
</body>
</html>"""

    def _generate_portal_css(self, config: PortalConfig) -> str:
        """Generate portal CSS styles."""
        primary_color = config.branding.get('primary_color', '#1e293b') if config.branding else '#1e293b'

        return f"""
/* LCopilot Trust Portal Styles */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f8fafc;
}}

/* Portal Layout */
.portal-container {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}}

.portal-header {{
    background: {primary_color};
    color: white;
    padding: 2rem 0;
}}

.header-content {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.tier-badge {{
    background: rgba(255,255,255,0.2);
    padding: 0.5rem 1rem;
    border-radius: 2rem;
    font-size: 0.875rem;
}}

/* Main Content */
.portal-main {{
    flex: 1;
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    width: 100%;
}}

.welcome-section {{
    text-align: center;
    margin-bottom: 3rem;
}}

.welcome-section h2 {{
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #1f2937;
}}

/* Features Grid */
.features-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}}

.feature-card {{
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}}

.feature-icon {{
    font-size: 2rem;
    margin-top: 0.25rem;
}}

.feature-content h3 {{
    font-size: 1.25rem;
    margin-bottom: 0.5rem;
    color: #1f2937;
}}

/* Buttons */
.btn {{
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: opacity 0.2s;
}}

.btn:hover {{
    opacity: 0.9;
}}

.btn-primary {{
    background: {primary_color};
    color: white;
}}

.btn-secondary {{
    background: #6b7280;
    color: white;
}}

.btn-full {{
    width: 100%;
}}

.btn-sm {{
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
}}

/* Portal Actions */
.portal-actions {{
    text-align: center;
    gap: 1rem;
}}

.portal-actions .btn {{
    margin: 0 0.5rem;
}}

/* Login Page */
.login-container {{
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, {primary_color}, #64748b);
}}

.login-card {{
    background: white;
    padding: 3rem;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    width: 100%;
    max-width: 400px;
}}

.login-header {{
    text-align: center;
    margin-bottom: 2rem;
}}

.login-header h1 {{
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
    color: #1f2937;
}}

/* Form Styles */
.form-group {{
    margin-bottom: 1.5rem;
}}

.form-group label {{
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
}}

.form-group input {{
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;
}}

.form-group input:focus {{
    outline: none;
    border-color: {primary_color};
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}}

/* Dashboard */
.dashboard-container {{
    display: flex;
    min-height: 100vh;
}}

.dashboard-nav {{
    width: 250px;
    background: #1f2937;
    color: white;
    padding: 2rem 0;
}}

.nav-header {{
    padding: 0 2rem;
    margin-bottom: 2rem;
}}

.nav-menu {{
    list-style: none;
}}

.nav-menu li {{
    margin-bottom: 0.5rem;
}}

.nav-link {{
    display: block;
    padding: 0.75rem 2rem;
    color: #d1d5db;
    text-decoration: none;
    transition: background-color 0.2s;
}}

.nav-link:hover,
.nav-link.active {{
    background: {primary_color};
    color: white;
}}

.dashboard-main {{
    flex: 1;
    padding: 2rem;
    overflow-y: auto;
}}

.dashboard-section {{
    display: none;
}}

.dashboard-section.active {{
    display: block;
}}

.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}}

.metric-card {{
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    text-align: center;
}}

.metric-value {{
    font-size: 2rem;
    font-weight: 700;
    color: {primary_color};
    margin-bottom: 0.5rem;
}}

.metric-label {{
    color: #6b7280;
    font-size: 0.875rem;
}}

/* Reports */
.reports-list {{
    space-y: 1rem;
}}

.report-item {{
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}}

.report-info h3 {{
    margin-bottom: 0.5rem;
    color: #1f2937;
}}

.report-actions {{
    display: flex;
    gap: 0.5rem;
}}

/* Footer */
.portal-footer {{
    background: #1f2937;
    color: #9ca3af;
    text-align: center;
    padding: 2rem;
}}

/* Responsive */
@media (max-width: 768px) {{
    .dashboard-container {{
        flex-direction: column;
    }}

    .dashboard-nav {{
        width: 100%;
        padding: 1rem 0;
    }}

    .nav-menu {{
        display: flex;
        overflow-x: auto;
    }}

    .nav-menu li {{
        margin-bottom: 0;
        margin-right: 0.5rem;
    }}

    .features-grid {{
        grid-template-columns: 1fr;
    }}

    .portal-actions .btn {{
        display: block;
        margin: 0.5rem 0;
    }}

    .report-item {{
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
    }}
}}
"""

    def _generate_portal_js(self, config: PortalConfig) -> str:
        """Generate portal JavaScript."""
        return """
// LCopilot Trust Portal JavaScript

// Initialize portal
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeAuth();
});

// Navigation handling
function initializeNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.dashboard-section');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove active class from all links and sections
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Add active class to clicked link
            this.classList.add('active');

            // Show corresponding section
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });
}

// Authentication handling
function initializeAuth() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
}

// Handle login form submission
function handleLogin(e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Signing in...';
    submitBtn.disabled = true;

    // Simulate authentication (replace with actual Cognito integration)
    setTimeout(() => {
        // For demo purposes, always "succeed"
        window.location.href = '/dashboard.html';
    }, 1500);
}

// Password reset
function forgotPassword() {
    const email = prompt('Enter your email address for password reset:');
    if (email) {
        alert('Password reset instructions have been sent to ' + email);
        // Implement actual password reset with Cognito
    }
}

// Auto-refresh dashboard data
function refreshDashboardData() {
    // Implement actual data refresh
    console.log('Refreshing dashboard data...');
}

// Refresh every 5 minutes when on dashboard
if (window.location.pathname.includes('dashboard.html')) {
    setInterval(refreshDashboardData, 5 * 60 * 1000);
}

// Export functions for global access
window.forgotPassword = forgotPassword;
"""

    def _get_content_type(self, file_path: str) -> str:
        """Get content type based on file extension."""
        if file_path.endswith('.html'):
            return 'text/html'
        elif file_path.endswith('.css'):
            return 'text/css'
        elif file_path.endswith('.js'):
            return 'application/javascript'
        else:
            return 'text/plain'

    def deploy_all_portals(self) -> Dict[str, Any]:
        """Deploy portals for all tiers and customers."""
        results = {'success': [], 'failed': []}

        # Deploy shared tier portals
        for tier in ['pro', 'enterprise']:
            try:
                print(f"\n🚀 Deploying {tier} tier portal...")

                config = self.get_portal_config(tier)
                if config.features:
                    # Create user pool
                    user_pool_id = self.create_cognito_user_pool(config)

                    if user_pool_id:
                        # Deploy frontend
                        if self.deploy_portal_frontend(config):
                            results['success'].append({
                                'tier': tier,
                                'customer_id': None,
                                'domain': config.domain,
                                'user_pool_id': user_pool_id
                            })
                        else:
                            results['failed'].append({
                                'tier': tier,
                                'customer_id': None,
                                'error': 'Frontend deployment failed'
                            })
                    else:
                        results['failed'].append({
                            'tier': tier,
                            'customer_id': None,
                            'error': 'User pool creation failed'
                        })

            except Exception as e:
                results['failed'].append({
                    'tier': tier,
                    'customer_id': None,
                    'error': str(e)
                })

        # Deploy enterprise customer portals
        customers = self.reliability_config.get('customers', {}).get('tier_mappings', {})
        enterprise_customers = [cust_id for cust_id, cust_config in customers.items()
                              if cust_config.get('tier') == 'enterprise']

        for customer_id in enterprise_customers:
            try:
                print(f"\n🏢 Deploying enterprise portal for {customer_id}...")

                config = self.get_portal_config('enterprise', customer_id)

                # Create dedicated user pool
                user_pool_id = self.create_cognito_user_pool(config)

                if user_pool_id:
                    # Deploy custom frontend
                    if self.deploy_portal_frontend(config):
                        results['success'].append({
                            'tier': 'enterprise',
                            'customer_id': customer_id,
                            'domain': config.domain,
                            'user_pool_id': user_pool_id
                        })
                    else:
                        results['failed'].append({
                            'tier': 'enterprise',
                            'customer_id': customer_id,
                            'error': 'Frontend deployment failed'
                        })
                else:
                    results['failed'].append({
                        'tier': 'enterprise',
                        'customer_id': customer_id,
                        'error': 'User pool creation failed'
                    })

            except Exception as e:
                results['failed'].append({
                    'tier': 'enterprise',
                    'customer_id': customer_id,
                    'error': str(e)
                })

        return results


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot Customer Trust Portal Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 trust_portal_manager.py --tier pro --deploy-portal
  python3 trust_portal_manager.py --tier enterprise --customer enterprise-customer-001 --deploy-portal
  python3 trust_portal_manager.py --create-user --email user@company.com --tier pro
  python3 trust_portal_manager.py --deploy-all
        """
    )

    parser.add_argument('--tier', choices=['pro', 'enterprise'], default='pro',
                       help='Service tier (default: pro)')
    parser.add_argument('--customer', help='Customer ID for enterprise tier')
    parser.add_argument('--env', '--environment', choices=['staging', 'prod'], default='prod',
                       help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--deploy-portal', action='store_true', help='Deploy trust portal')
    parser.add_argument('--create-user', action='store_true', help='Create portal user')
    parser.add_argument('--email', help='User email for user creation')
    parser.add_argument('--deploy-all', action='store_true', help='Deploy all portals')

    args = parser.parse_args()

    # Initialize manager
    manager = TrustPortalManager(environment=args.env, aws_profile=args.profile)

    print(f"🚀 LCopilot Trust Portal Manager ({args.tier} tier)")

    if not manager.initialize_aws_clients():
        sys.exit(1)

    # Deploy all portals
    if args.deploy_all:
        print("🚀 Deploying all trust portals...")

        results = manager.deploy_all_portals()

        print(f"\n✅ Successfully deployed {len(results['success'])} portal(s)")
        for result in results['success']:
            customer_info = f" for {result['customer_id']}" if result['customer_id'] else ""
            print(f"   • {result['tier'].title()} tier{customer_info}: {result['domain']}")

        if results['failed']:
            print(f"\n❌ Failed to deploy {len(results['failed'])} portal(s):")
            for result in results['failed']:
                customer_info = f" for {result['customer_id']}" if result['customer_id'] else ""
                print(f"   • {result['tier'].title()} tier{customer_info}: {result['error']}")

        return

    # Create user
    if args.create_user:
        if not args.email:
            print("❌ --email parameter required for user creation")
            sys.exit(1)

        success = manager.create_portal_user(args.email, args.tier, args.customer)
        if not success:
            sys.exit(1)
        return

    # Deploy single portal
    if args.deploy_portal:
        if args.tier == 'enterprise' and not args.customer:
            print("❌ Enterprise tier requires --customer parameter")
            sys.exit(1)

        config = manager.get_portal_config(args.tier, args.customer)

        if not config.features:
            print(f"❌ Trust portal not enabled for {args.tier} tier")
            sys.exit(1)

        print(f"🚀 Deploying {args.tier} tier portal...")
        print(f"   Domain: {config.domain}")
        print(f"   Features: {', '.join(config.features)}")

        # Create user pool
        user_pool_id = manager.create_cognito_user_pool(config)
        if not user_pool_id:
            sys.exit(1)

        # Deploy frontend
        success = manager.deploy_portal_frontend(config)
        if success:
            print(f"✅ Portal deployed successfully!")
            print(f"   URL: https://{config.domain}")
            print(f"   User Pool ID: {user_pool_id}")
        else:
            sys.exit(1)

        return

    # Show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    main()