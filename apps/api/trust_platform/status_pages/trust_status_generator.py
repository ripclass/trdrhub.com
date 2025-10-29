"""
LCopilot Trust Platform Status Page Generator

Builds status pages specifically for importers, exporters, and banks with:
- LC validation health monitoring
- Trade-specific incident categories
- Bank-auditable uptime metrics
- Tier-based feature display
"""

import boto3
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import requests
from jinja2 import Template
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class LCValidationHealth:
    endpoint_name: str
    status: str  # "operational", "degraded", "outage"
    response_time_ms: float
    accuracy_percentage: float
    last_check: datetime
    uptime_percentage_24h: float
    processing_volume_24h: int
    error_count_24h: int

@dataclass
class TradeIncident:
    incident_id: str
    title: str
    status: str  # "investigating", "identified", "monitoring", "resolved"
    severity: str  # "critical", "major", "minor", "maintenance"
    category: str  # "lc_validation_failure", "processing_delays", etc.
    trade_impact: str  # Impact description for importers/exporters
    bank_impact: str   # Impact description for banks
    started_at: datetime
    resolved_at: Optional[datetime]
    updates: List[Dict[str, Any]]
    affected_services: List[str]
    root_cause_summary: Optional[str]

@dataclass
class TrustStatusConfig:
    tier: str
    customer_id: str
    company_name: str
    business_type: str  # "importer", "exporter", "bank", "trading_company"
    white_label_config: Optional[Dict[str, str]]
    display_features: Dict[str, bool]
    uptime_history_days: int
    show_lc_metrics: bool
    show_bank_compliance: bool

class TrustStatusGenerator:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.s3 = boto3.client('s3')
        self.cloudwatch = boto3.client('cloudwatch')

        # Load trust platform configuration
        self.config_path = Path(__file__).parent.parent / "config" / "trust_config.yaml"
        self.trust_config = self._load_trust_config()

        # S3 buckets for status pages
        self.status_bucket = f"lcopilot-trust-status-{environment}"
        self.assets_bucket = f"lcopilot-trust-assets-{environment}"

        # CloudFront distribution (for Enterprise white-label)
        self.cloudfront = boto3.client('cloudfront')

    def _load_trust_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Trust config not found at {self.config_path}")
            return {}

    def get_customer_config(self, customer_id: str) -> TrustStatusConfig:
        """Get tier-based configuration for customer status page"""
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')
        tier_features = self.trust_config.get('tier_offerings', {}).get(tier, {}).get('features', {})
        compliance_config = self.trust_config.get('compliance', {}).get('tiers', {}).get(tier, {})

        config = TrustStatusConfig(
            tier=tier,
            customer_id=customer_id,
            company_name=customer_data.get('company_name', 'LCopilot Customer'),
            business_type=customer_data.get('business_type', 'trader'),
            white_label_config=customer_data.get('white_label'),
            display_features={
                'show_uptime_history': tier_features.get('uptime_history_days', 0) > 0,
                'show_incident_history': tier_features.get('incident_history', False),
                'show_lc_validation_health': tier_features.get('lc_validation_health', False),
                'show_processing_metrics': tier in ['pro', 'enterprise'],
                'show_compliance_status': compliance_config.get('enabled', False),
                'show_compliance_details': tier in ['pro', 'enterprise'],
                'show_compliance_violations': tier == 'enterprise',
                'show_api_status': tier_features.get('api_access', False),
                'show_webhook_status': tier_features.get('webhooks', False)
            },
            uptime_history_days=tier_features.get('uptime_history_days', 90),
            show_lc_metrics=tier_features.get('lc_validation_health', True),
            show_bank_compliance=tier == 'enterprise' and customer_data.get('business_type') == 'bank'
        )

        return config

    def check_lc_validation_health(self) -> List[LCValidationHealth]:
        """Check health of all LC validation endpoints"""
        health_checks = []
        endpoints = self.trust_config.get('lc_health_metrics', {}).get('validation_endpoints', [])

        for endpoint_config in endpoints:
            try:
                # Perform health check
                start_time = datetime.now()
                response = requests.get(
                    f"{endpoint_config['endpoint']}/health",
                    timeout=endpoint_config.get('timeout_seconds', 30)
                )
                response_time = (datetime.now() - start_time).total_seconds() * 1000

                # Get CloudWatch metrics for this endpoint
                endpoint_metrics = self._get_endpoint_metrics(endpoint_config['name'])

                # Determine status
                if response.status_code == 200:
                    if endpoint_metrics['accuracy'] >= 99.0:
                        status = "operational"
                    else:
                        status = "degraded"
                else:
                    status = "outage"

                health_check = LCValidationHealth(
                    endpoint_name=endpoint_config['name'],
                    status=status,
                    response_time_ms=response_time,
                    accuracy_percentage=endpoint_metrics['accuracy'],
                    last_check=datetime.now(timezone.utc),
                    uptime_percentage_24h=endpoint_metrics['uptime_24h'],
                    processing_volume_24h=endpoint_metrics['volume_24h'],
                    error_count_24h=endpoint_metrics['errors_24h']
                )

            except Exception as e:
                logger.error(f"Health check failed for {endpoint_config['name']}: {str(e)}")
                health_check = LCValidationHealth(
                    endpoint_name=endpoint_config['name'],
                    status="outage",
                    response_time_ms=0,
                    accuracy_percentage=0,
                    last_check=datetime.now(timezone.utc),
                    uptime_percentage_24h=0,
                    processing_volume_24h=0,
                    error_count_24h=0
                )

            health_checks.append(health_check)

        return health_checks

    def _get_endpoint_metrics(self, endpoint_name: str) -> Dict[str, float]:
        """Get CloudWatch metrics for LC validation endpoint"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        try:
            # Get accuracy metric
            accuracy_response = self.cloudwatch.get_metric_statistics(
                Namespace='LCopilot/Validation',
                MetricName='ValidationAccuracy',
                Dimensions=[{'Name': 'Endpoint', 'Value': endpoint_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )

            # Get uptime metric
            uptime_response = self.cloudwatch.get_metric_statistics(
                Namespace='LCopilot/Validation',
                MetricName='EndpointAvailability',
                Dimensions=[{'Name': 'Endpoint', 'Value': endpoint_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )

            # Get volume and error metrics
            volume_response = self.cloudwatch.get_metric_statistics(
                Namespace='LCopilot/Validation',
                MetricName='ProcessingVolume',
                Dimensions=[{'Name': 'Endpoint', 'Value': endpoint_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )

            error_response = self.cloudwatch.get_metric_statistics(
                Namespace='LCopilot/Validation',
                MetricName='ValidationErrors',
                Dimensions=[{'Name': 'Endpoint', 'Value': endpoint_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )

            # Calculate averages
            accuracy = sum(dp['Average'] for dp in accuracy_response['Datapoints']) / len(accuracy_response['Datapoints']) if accuracy_response['Datapoints'] else 99.0
            uptime = sum(dp['Average'] for dp in uptime_response['Datapoints']) / len(uptime_response['Datapoints']) if uptime_response['Datapoints'] else 100.0
            volume = sum(dp['Sum'] for dp in volume_response['Datapoints']) if volume_response['Datapoints'] else 0
            errors = sum(dp['Sum'] for dp in error_response['Datapoints']) if error_response['Datapoints'] else 0

            return {
                'accuracy': accuracy,
                'uptime_24h': uptime,
                'volume_24h': int(volume),
                'errors_24h': int(errors)
            }

        except Exception as e:
            logger.error(f"Failed to get metrics for {endpoint_name}: {str(e)}")
            return {
                'accuracy': 99.0,  # Default values
                'uptime_24h': 100.0,
                'volume_24h': 0,
                'errors_24h': 0
            }

    def get_recent_incidents(self, customer_config: TrustStatusConfig, days_back: int = 30) -> List[TradeIncident]:
        """Get recent incidents affecting trade operations"""
        incidents = []

        # Query incidents from the last specified days
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        # This would typically query from a database or incident management system
        # For now, we'll simulate with some example incidents
        sample_incidents = [
            {
                'incident_id': 'INC-2024-001',
                'title': 'LC Validation Engine Response Delays',
                'status': 'resolved',
                'severity': 'major',
                'category': 'processing_delays',
                'trade_impact': 'LC validation taking 60-90 seconds instead of usual 30 seconds, affecting shipment documentation timeline',
                'bank_impact': 'Extended processing times for LC compliance verification, potential impact on credit facility timelines',
                'started_at': datetime.now(timezone.utc) - timedelta(hours=48),
                'resolved_at': datetime.now(timezone.utc) - timedelta(hours=46),
                'affected_services': ['UCP600 Compliance Check', 'ISBP Review Engine'],
                'root_cause_summary': 'Database connection pool exhaustion during peak processing hours'
            },
            {
                'incident_id': 'INC-2024-002',
                'title': 'Temporary API Rate Limiting',
                'status': 'resolved',
                'severity': 'minor',
                'category': 'api_unavailable',
                'trade_impact': 'Enterprise trading platforms experienced occasional 429 rate limit errors',
                'bank_impact': 'Core banking system integrations temporarily throttled during high-volume periods',
                'started_at': datetime.now(timezone.utc) - timedelta(hours=12),
                'resolved_at': datetime.now(timezone.utc) - timedelta(hours=10),
                'affected_services': ['Integration APIs'],
                'root_cause_summary': 'Rate limiting configuration updated to handle holiday trade volume spike'
            }
        ]

        for incident_data in sample_incidents:
            # Only show incidents relevant to customer tier
            if customer_config.tier == 'free' and incident_data['category'] == 'api_unavailable':
                continue  # Free tier doesn't have API access

            incident = TradeIncident(
                incident_id=incident_data['incident_id'],
                title=incident_data['title'],
                status=incident_data['status'],
                severity=incident_data['severity'],
                category=incident_data['category'],
                trade_impact=incident_data['trade_impact'],
                bank_impact=incident_data['bank_impact'],
                started_at=incident_data['started_at'],
                resolved_at=incident_data.get('resolved_at'),
                updates=[],  # Would be populated from incident management system
                affected_services=incident_data['affected_services'],
                root_cause_summary=incident_data.get('root_cause_summary')
            )
            incidents.append(incident)

        return incidents

    def calculate_overall_status(self, health_checks: List[LCValidationHealth], incidents: List[TradeIncident]) -> str:
        """Calculate overall system status for status page"""

        # Check for active critical incidents
        active_critical = any(
            inc.status in ['investigating', 'identified'] and inc.severity == 'critical'
            for inc in incidents
        )
        if active_critical:
            return "major_outage"

        # Check for active major incidents
        active_major = any(
            inc.status in ['investigating', 'identified'] and inc.severity == 'major'
            for inc in incidents
        )
        if active_major:
            return "partial_outage"

        # Check LC validation health
        degraded_services = [hc for hc in health_checks if hc.status == "degraded"]
        failed_services = [hc for hc in health_checks if hc.status == "outage"]

        if failed_services:
            return "partial_outage"
        elif degraded_services:
            return "degraded_performance"
        elif any(inc.status in ['investigating', 'identified'] for inc in incidents):
            return "under_maintenance"
        else:
            return "operational"

    def get_compliance_metrics(self, customer_config: TrustStatusConfig) -> Dict[str, Any]:
        """Get UCP600/ISBP compliance metrics for status page"""
        compliance_config = self.trust_config.get('compliance', {}).get('tiers', {}).get(customer_config.tier, {})

        if not compliance_config.get('enabled', False):
            return None

        # Get compliance configuration
        checks_included = compliance_config.get('checks_included', 0)
        description = compliance_config.get('description', '')
        features = compliance_config.get('features', [])
        limitations = compliance_config.get('limitations', [])

        # Simulate compliance health metrics
        if customer_config.tier == 'free':
            # Free tier shows teaser information
            return {
                'tier': customer_config.tier,
                'checks_included': checks_included,
                'checks_remaining': 3,  # Would track actual usage
                'description': description,
                'features': features,
                'limitations': limitations,
                'ucp600_health': 'Available',
                'isbp_health': 'Available',
                'compliance_score': None,  # Not shown until used
                'upgrade_message': 'Try 3 UCP600/ISBP compliance checks — see how banks will view your LC'
            }

        elif customer_config.tier == 'pro':
            # Pro tier shows unlimited compliance
            return {
                'tier': customer_config.tier,
                'checks_included': 'unlimited',
                'description': description,
                'features': features,
                'limitations': limitations,
                'ucp600_health': 'Operational',
                'isbp_health': 'Operational',
                'compliance_score': 94.2,  # Simulated score
                'recent_validations': 1247,
                'compliance_message': 'Every LC validated against ICC rules to avoid rejections'
            }

        else:  # enterprise
            # Enterprise shows full bank-grade compliance
            return {
                'tier': customer_config.tier,
                'checks_included': 'unlimited',
                'description': description,
                'features': features,
                'limitations': limitations,
                'ucp600_health': 'Operational',
                'isbp_health': 'Operational',
                'compliance_score': 97.8,  # Higher enterprise score
                'recent_validations': 5420,
                'audit_trail_status': 'Enabled',
                'digital_signatures': 'Active',
                'retention_period': '7 years',
                'compliance_message': 'Audit-grade compliance with immutable logs + 7y retention'
            }

    def get_common_violations(self) -> List[Dict[str, Any]]:
        """Get most common UCP600/ISBP violations for dashboard"""
        return self.trust_config.get('common_violations', [])

    def generate_status_page_html(self, customer_config: TrustStatusConfig) -> str:
        """Generate HTML status page for trade partners"""

        # Get current health and incident data
        health_checks = self.check_lc_validation_health()
        recent_incidents = self.get_recent_incidents(customer_config)
        overall_status = self.calculate_overall_status(health_checks, recent_incidents)

        # Get compliance metrics
        compliance_metrics = self.get_compliance_metrics(customer_config)
        common_violations = self.get_common_violations() if customer_config.display_features.get('show_compliance_violations') else []

        # Load HTML template
        template_path = Path(__file__).parent / "templates" / "trust_status_page.html"
        with open(template_path, 'r') as f:
            template_content = f.read()

        template = Template(template_content)

        # Prepare template variables
        template_vars = {
            'config': customer_config,
            'overall_status': overall_status,
            'health_checks': health_checks,
            'incidents': recent_incidents[:10],  # Show last 10 incidents
            'compliance_metrics': compliance_metrics,
            'common_violations': common_violations,
            'generated_at': datetime.now(timezone.utc),
            'status_colors': {
                'operational': '#28a745',
                'degraded_performance': '#ffc107',
                'partial_outage': '#fd7e14',
                'major_outage': '#dc3545',
                'under_maintenance': '#6f42c1'
            },
            'tier_features': customer_config.display_features,
            'business_context': self._get_business_context(customer_config.business_type)
        }

        # Render HTML
        html_content = template.render(**template_vars)

        return html_content

    def _get_business_context(self, business_type: str) -> Dict[str, str]:
        """Get business-specific context for status page"""
        contexts = {
            'importer': {
                'primary_concern': 'LC validation delays affecting shipment clearance',
                'key_metric': 'Time to validate import LCs',
                'impact_description': 'Delays may affect customs clearance and delivery schedules'
            },
            'exporter': {
                'primary_concern': 'LC compliance verification for payment assurance',
                'key_metric': 'LC validation accuracy for export documents',
                'impact_description': 'Validation errors may delay payment from importing banks'
            },
            'bank': {
                'primary_concern': 'Regulatory compliance and audit trail integrity',
                'key_metric': 'Audit-grade validation accuracy and response times',
                'impact_description': 'Service issues may affect trade finance operations and compliance'
            },
            'trading_company': {
                'primary_concern': 'End-to-end trade facilitation efficiency',
                'key_metric': 'Overall LC processing pipeline performance',
                'impact_description': 'Delays impact both import and export operations'
            }
        }
        return contexts.get(business_type, contexts['trading_company'])

    def generate_status_json(self, customer_config: TrustStatusConfig) -> Dict[str, Any]:
        """Generate machine-readable JSON status feed"""

        health_checks = self.check_lc_validation_health()
        recent_incidents = self.get_recent_incidents(customer_config, days_back=7)
        overall_status = self.calculate_overall_status(health_checks, recent_incidents)

        status_data = {
            'page': {
                'id': f"lcopilot-trust-{customer_config.customer_id}",
                'name': f"{customer_config.company_name} - LC Platform Status",
                'url': self._get_status_page_url(customer_config),
                'updated_at': datetime.now(timezone.utc).isoformat()
            },
            'status': {
                'indicator': overall_status,
                'description': self._get_status_description(overall_status)
            },
            'components': [
                {
                    'id': hc.endpoint_name.lower().replace(' ', '_'),
                    'name': hc.endpoint_name,
                    'status': hc.status,
                    'response_time_ms': hc.response_time_ms,
                    'accuracy_percentage': hc.accuracy_percentage,
                    'uptime_24h': hc.uptime_percentage_24h,
                    'processing_volume_24h': hc.processing_volume_24h,
                    'last_updated': hc.last_check.isoformat()
                }
                for hc in health_checks
            ],
            'incidents': [
                {
                    'id': inc.incident_id,
                    'name': inc.title,
                    'status': inc.status,
                    'impact': inc.severity,
                    'created_at': inc.started_at.isoformat(),
                    'resolved_at': inc.resolved_at.isoformat() if inc.resolved_at else None,
                    'trade_impact': inc.trade_impact,
                    'bank_impact': inc.bank_impact if customer_config.show_bank_compliance else None
                }
                for inc in recent_incidents
            ]
        }

        return status_data

    def _get_status_description(self, status: str) -> str:
        """Get human-readable status description"""
        descriptions = {
            'operational': 'All LC validation services are operating normally',
            'degraded_performance': 'Some LC validation services are experiencing performance issues',
            'partial_outage': 'Some LC validation services are currently unavailable',
            'major_outage': 'LC validation services are experiencing major disruptions',
            'under_maintenance': 'Scheduled maintenance is in progress'
        }
        return descriptions.get(status, 'Status unknown')

    def _get_status_page_url(self, customer_config: TrustStatusConfig) -> str:
        """Get the URL for the customer's status page"""
        if customer_config.white_label_config:
            return f"https://{customer_config.white_label_config['domain']}"
        else:
            return f"https://trust-status.lcopilot.com/{customer_config.customer_id}"

    def deploy_status_page(self, customer_config: TrustStatusConfig) -> Dict[str, str]:
        """Deploy status page to S3 with CloudFront for Enterprise"""

        # Generate HTML and JSON
        html_content = self.generate_status_page_html(customer_config)
        json_content = self.generate_status_json(customer_config)

        # Determine deployment path
        if customer_config.tier == 'enterprise' and customer_config.white_label_config:
            # Enterprise white-label deployment
            deployment_prefix = f"enterprise/{customer_config.customer_id}"
        else:
            # Standard deployment
            deployment_prefix = f"{customer_config.tier}/{customer_config.customer_id}"

        try:
            # Upload HTML page
            html_key = f"{deployment_prefix}/index.html"
            self.s3.put_object(
                Bucket=self.status_bucket,
                Key=html_key,
                Body=html_content,
                ContentType='text/html',
                CacheControl='public, max-age=300'  # 5 minute cache
            )

            # Upload JSON feed
            json_key = f"{deployment_prefix}/status.json"
            self.s3.put_object(
                Bucket=self.status_bucket,
                Key=json_key,
                Body=json.dumps(json_content, indent=2),
                ContentType='application/json',
                CacheControl='public, max-age=60'  # 1 minute cache for JSON
            )

            # Generate URLs
            if customer_config.white_label_config:
                html_url = f"https://{customer_config.white_label_config['domain']}"
                json_url = f"https://{customer_config.white_label_config['domain']}/status.json"
            else:
                html_url = f"https://{self.status_bucket}.s3-website-{boto3.Session().region_name}.amazonaws.com/{html_key}"
                json_url = f"https://{self.status_bucket}.s3-website-{boto3.Session().region_name}.amazonaws.com/{json_key}"

            logger.info(f"Status page deployed for {customer_config.customer_id} ({customer_config.tier})")

            return {
                'html_url': html_url,
                'json_url': json_url,
                'deployment_path': deployment_prefix
            }

        except Exception as e:
            logger.error(f"Failed to deploy status page for {customer_config.customer_id}: {str(e)}")
            raise

    def create_cloudfront_distribution(self, customer_config: TrustStatusConfig) -> Optional[str]:
        """Create CloudFront distribution for Enterprise white-label"""

        if customer_config.tier != 'enterprise' or not customer_config.white_label_config:
            return None

        domain = customer_config.white_label_config['domain']

        try:
            # Create CloudFront distribution
            distribution_config = {
                'CallerReference': f"lcopilot-trust-{customer_config.customer_id}-{int(datetime.now().timestamp())}",
                'Comment': f"LCopilot Trust Status Page for {customer_config.company_name}",
                'DefaultCacheBehavior': {
                    'TargetOriginId': f"S3-{self.status_bucket}",
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'MinTTL': 0,
                    'DefaultTTL': 300,
                    'MaxTTL': 3600,
                    'ForwardedValues': {
                        'QueryString': False,
                        'Cookies': {'Forward': 'none'}
                    }
                },
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': f"S3-{self.status_bucket}",
                            'DomainName': f"{self.status_bucket}.s3.amazonaws.com",
                            'OriginPath': f"/enterprise/{customer_config.customer_id}",
                            'S3OriginConfig': {
                                'OriginAccessIdentity': ''
                            }
                        }
                    ]
                },
                'Aliases': {
                    'Quantity': 1,
                    'Items': [domain]
                },
                'Enabled': True,
                'PriceClass': 'PriceClass_100'
            }

            response = self.cloudfront.create_distribution(
                DistributionConfig=distribution_config
            )

            distribution_id = response['Distribution']['Id']
            distribution_domain = response['Distribution']['DomainName']

            logger.info(f"CloudFront distribution created: {distribution_id} for {domain}")

            return {
                'distribution_id': distribution_id,
                'domain_name': distribution_domain,
                'status': response['Distribution']['Status']
            }

        except Exception as e:
            logger.error(f"Failed to create CloudFront distribution for {domain}: {str(e)}")
            return None

def main():
    """Demo trust status page generation"""
    generator = TrustStatusGenerator()

    print("=== LCopilot Trust Platform Status Page Demo ===")

    # Test different customer tiers
    customers = ['sme-importer-001', 'pro-trader-001', 'enterprise-bank-001']

    for customer_id in customers:
        print(f"\n--- Generating status page for {customer_id} ---")

        try:
            config = generator.get_customer_config(customer_id)
            print(f"Customer: {config.company_name} ({config.tier} tier)")
            print(f"Business Type: {config.business_type}")
            print(f"Features: {list(k for k, v in config.display_features.items() if v)}")

            # Deploy status page
            deployment_result = generator.deploy_status_page(config)
            print(f"Deployed to: {deployment_result['html_url']}")

            # Show JSON status sample
            json_status = generator.generate_status_json(config)
            print(f"Status: {json_status['status']['indicator']} - {json_status['status']['description']}")
            print(f"Components monitored: {len(json_status['components'])}")
            print(f"Recent incidents: {len(json_status['incidents'])}")

        except Exception as e:
            print(f"Error generating status page for {customer_id}: {str(e)}")

if __name__ == "__main__":
    main()