#!/usr/bin/env python3
"""
LCopilot Security Monitoring System

Implements real-time security monitoring with anomaly detection and alerting.
Monitors authentication events, suspicious activities, and security metrics.

Features:
- Authentication failure monitoring and alerting
- IP-based anomaly detection
- Geographic anomaly detection
- Brute force attack detection
- Security metrics publishing
- Integration with escalation routing

Usage:
    python3 security_monitor.py --env prod --monitor auth-failures
    python3 security_monitor.py --env staging --analyze-logs --hours 24
    python3 security_monitor.py --env prod --create-alarms
    python3 security_monitor.py --env staging --test-alert
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import re
import ipaddress


@dataclass
class SecurityEvent:
    """Security event data structure."""
    timestamp: datetime
    event_type: str
    severity: str
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    country_code: Optional[str] = None
    risk_score: int = 0


@dataclass
class SecurityAnomaly:
    """Security anomaly detection result."""
    anomaly_type: str
    severity: str
    confidence: float
    description: str
    affected_ips: List[str]
    event_count: int
    time_window: str


class SecurityMonitor:
    """Security monitoring and anomaly detection system."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})
        self.security_config = self.config.get('security', {})

        # Security monitoring configuration
        self.auth_config = self.security_config.get('auth_monitoring', {})
        self.waf_config = self.security_config.get('waf_monitoring', {})

        # Thresholds
        self.failure_threshold = self.auth_config.get('failure_threshold', {}).get(environment, 20)

        # AWS clients
        self.cloudwatch_client = None
        self.logs_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Security patterns
        self.log_patterns = self.auth_config.get('log_patterns', {})

        # Known suspicious countries (configurable)
        self.suspicious_countries = ['CN', 'RU', 'KP', 'IR']

        # IP reputation cache
        self.ip_reputation_cache = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load enterprise configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'enterprise_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'environments': {
                'staging': {'aws_region': 'eu-north-1'},
                'prod': {'aws_region': 'eu-north-1'}
            },
            'security': {
                'enable_auth_alarms': True,
                'auth_monitoring': {
                    'failure_threshold': {
                        'staging': 20,
                        'prod': 50
                    },
                    'metrics': {
                        'auth_failure_count': 'AuthFailureCount-{env}',
                        'suspicious_ip_count': 'SuspiciousIPCount-{env}'
                    },
                    'log_patterns': {
                        'auth_failed': '{ $.event = "auth_failed" }',
                        'brute_force': '{ $.event = "auth_failed" && $.attempts > 5 }',
                        'suspicious_countries': '{ $.country_code = "CN" || $.country_code = "RU" || $.country_code = "KP" }'
                    }
                }
            }
        }

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.cloudwatch_client = session.client('cloudwatch')
            self.logs_client = session.client('logs')

            # Test connections
            self.cloudwatch_client.describe_alarms(MaxRecords=1)
            self.logs_client.describe_log_groups(limit=1)

            print(f"✅ AWS clients initialized for {self.region}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def parse_security_logs(self, log_group_name: str, hours_back: int = 1) -> List[SecurityEvent]:
        """Parse security-related events from CloudWatch logs."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        security_events = []

        try:
            # Query for authentication failures
            auth_query = """
            fields @timestamp, @message, level, event, ip_address, user_agent, country_code, attempts
            | filter event like /auth_failed|login_failed|authentication_error/
            | sort @timestamp desc
            | limit 1000
            """

            response = self.logs_client.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=auth_query
            )

            query_id = response['queryId']

            # Poll for results
            import time
            while True:
                result = self.logs_client.get_query_results(queryId=query_id)
                status = result['status']

                if status == 'Complete':
                    break
                elif status in ['Failed', 'Cancelled']:
                    print(f"❌ Security log query {status.lower()}")
                    return security_events
                else:
                    time.sleep(2)

            # Parse results into SecurityEvent objects
            for result_row in result.get('results', []):
                event_data = {field['field']: field['value'] for field in result_row}

                try:
                    timestamp = datetime.fromisoformat(event_data.get('@timestamp', '').replace('Z', '+00:00'))
                    ip_address = event_data.get('ip_address', 'unknown')
                    country_code = event_data.get('country_code')
                    attempts = int(event_data.get('attempts', '1'))

                    # Calculate risk score
                    risk_score = self._calculate_risk_score(ip_address, country_code, attempts)

                    security_events.append(SecurityEvent(
                        timestamp=timestamp,
                        event_type='auth_failure',
                        severity='high' if risk_score > 80 else ('medium' if risk_score > 50 else 'low'),
                        ip_address=ip_address,
                        user_agent=event_data.get('user_agent', ''),
                        country_code=country_code,
                        risk_score=risk_score,
                        details={
                            'attempts': attempts,
                            'message': event_data.get('@message', ''),
                            'level': event_data.get('level', 'INFO')
                        }
                    ))

                except (ValueError, TypeError) as e:
                    print(f"⚠️  Failed to parse security event: {e}")
                    continue

            print(f"📋 Parsed {len(security_events)} security events from logs")
            return security_events

        except Exception as e:
            print(f"❌ Failed to parse security logs: {e}")
            return security_events

    def _calculate_risk_score(self, ip_address: str, country_code: Optional[str], attempts: int) -> int:
        """Calculate risk score for a security event."""
        risk_score = 0

        # Base score for authentication failure
        risk_score += 20

        # Multiple attempts increase risk
        if attempts > 5:
            risk_score += min(30, attempts * 3)

        # Suspicious countries
        if country_code in self.suspicious_countries:
            risk_score += 25

        # Private IP addresses are less risky
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.is_private:
                risk_score -= 10
        except ValueError:
            pass

        # Known malicious IP patterns (simplified)
        if self._is_suspicious_ip(ip_address):
            risk_score += 30

        return max(0, min(100, risk_score))

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address matches suspicious patterns."""
        # Simplified suspicious IP detection
        suspicious_patterns = [
            r'^192\.168\.1\.1$',  # Common router IP (could be compromised)
            r'^10\.0\.0\.1$',     # Common router IP
            # Add more patterns as needed
        ]

        for pattern in suspicious_patterns:
            if re.match(pattern, ip_address):
                return True

        return False

    def detect_anomalies(self, security_events: List[SecurityEvent]) -> List[SecurityAnomaly]:
        """Detect security anomalies from events."""
        anomalies = []

        if not security_events:
            return anomalies

        # Group events by IP address
        events_by_ip = defaultdict(list)
        for event in security_events:
            events_by_ip[event.ip_address].append(event)

        # Detect brute force attacks
        brute_force_anomalies = self._detect_brute_force(events_by_ip)
        anomalies.extend(brute_force_anomalies)

        # Detect geographic anomalies
        geo_anomalies = self._detect_geographic_anomalies(security_events)
        anomalies.extend(geo_anomalies)

        # Detect volume anomalies
        volume_anomalies = self._detect_volume_anomalies(security_events)
        anomalies.extend(volume_anomalies)

        return anomalies

    def _detect_brute_force(self, events_by_ip: Dict[str, List[SecurityEvent]]) -> List[SecurityAnomaly]:
        """Detect brute force attacks."""
        anomalies = []

        for ip_address, events in events_by_ip.items():
            # Check for high frequency of failures from same IP
            if len(events) >= 10:  # 10+ failures
                # Check if events are within a short time window
                time_span = (max(e.timestamp for e in events) - min(e.timestamp for e in events)).total_seconds()

                if time_span <= 300:  # Within 5 minutes
                    anomalies.append(SecurityAnomaly(
                        anomaly_type='brute_force',
                        severity='high',
                        confidence=0.9,
                        description=f'Brute force attack detected from {ip_address}',
                        affected_ips=[ip_address],
                        event_count=len(events),
                        time_window=f'{int(time_span)}s'
                    ))

        return anomalies

    def _detect_geographic_anomalies(self, events: List[SecurityEvent]) -> List[SecurityAnomaly]:
        """Detect geographic anomalies."""
        anomalies = []

        # Count events by country
        country_counts = Counter(event.country_code for event in events if event.country_code)

        # Check for high activity from suspicious countries
        for country, count in country_counts.items():
            if country in self.suspicious_countries and count >= 5:
                affected_ips = list(set(e.ip_address for e in events if e.country_code == country))

                anomalies.append(SecurityAnomaly(
                    anomaly_type='geographic_anomaly',
                    severity='medium',
                    confidence=0.7,
                    description=f'High authentication failure activity from {country}',
                    affected_ips=affected_ips,
                    event_count=count,
                    time_window='1h'
                ))

        return anomalies

    def _detect_volume_anomalies(self, events: List[SecurityEvent]) -> List[SecurityAnomaly]:
        """Detect volume-based anomalies."""
        anomalies = []

        # Check overall volume
        if len(events) > self.failure_threshold * 2:  # More than 2x normal threshold
            unique_ips = len(set(event.ip_address for event in events))

            anomalies.append(SecurityAnomaly(
                anomaly_type='volume_anomaly',
                severity='high',
                confidence=0.8,
                description=f'Unusually high authentication failure volume: {len(events)} events from {unique_ips} IPs',
                affected_ips=list(set(event.ip_address for event in events[:10])),  # Top 10 IPs
                event_count=len(events),
                time_window='1h'
            ))

        return anomalies

    def publish_security_metrics(self, events: List[SecurityEvent], anomalies: List[SecurityAnomaly]):
        """Publish security metrics to CloudWatch."""
        try:
            metric_data = []
            timestamp = datetime.now()

            # Authentication failure count
            auth_failure_count = len([e for e in events if e.event_type == 'auth_failure'])
            metric_data.append({
                'MetricName': f'AuthFailureCount-{self.environment}',
                'Value': auth_failure_count,
                'Unit': 'Count',
                'Timestamp': timestamp
            })

            # Suspicious IP count
            suspicious_ips = set()
            for event in events:
                if event.country_code in self.suspicious_countries or event.risk_score > 70:
                    suspicious_ips.add(event.ip_address)

            metric_data.append({
                'MetricName': f'SuspiciousIPCount-{self.environment}',
                'Value': len(suspicious_ips),
                'Unit': 'Count',
                'Timestamp': timestamp
            })

            # Anomaly metrics
            for anomaly_type in ['brute_force', 'geographic_anomaly', 'volume_anomaly']:
                count = len([a for a in anomalies if a.anomaly_type == anomaly_type])
                metric_data.append({
                    'MetricName': f'SecurityAnomaly-{anomaly_type}-{self.environment}',
                    'Value': count,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                })

            # High risk event count
            high_risk_events = len([e for e in events if e.risk_score > 80])
            metric_data.append({
                'MetricName': f'HighRiskSecurityEvents-{self.environment}',
                'Value': high_risk_events,
                'Unit': 'Count',
                'Timestamp': timestamp
            })

            # Publish metrics
            for i in range(0, len(metric_data), 20):  # CloudWatch limit is 20 per request
                batch = metric_data[i:i + 20]
                self.cloudwatch_client.put_metric_data(
                    Namespace='LCopilot/Security',
                    MetricData=batch
                )

            print(f"✅ Published {len(metric_data)} security metrics to CloudWatch")

        except Exception as e:
            print(f"❌ Failed to publish security metrics: {e}")

    def create_security_alarms(self) -> bool:
        """Create CloudWatch alarms for security monitoring."""
        try:
            # Authentication failure alarm
            auth_alarm_name = f'lcopilot-auth-failures-{self.environment}'

            self.cloudwatch_client.put_metric_alarm(
                AlarmName=auth_alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName=f'AuthFailureCount-{self.environment}',
                Namespace='LCopilot/Security',
                Period=300,  # 5 minutes
                Statistic='Sum',
                Threshold=self.failure_threshold,
                ActionsEnabled=True,
                AlarmActions=[],  # Would be populated with SNS topics
                AlarmDescription=f'Authentication failures exceeded threshold in {self.environment}',
                Unit='Count',
                TreatMissingData='notBreaching'
            )

            # Suspicious IP alarm
            suspicious_ip_alarm_name = f'lcopilot-suspicious-ips-{self.environment}'

            self.cloudwatch_client.put_metric_alarm(
                AlarmName=suspicious_ip_alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName=f'SuspiciousIPCount-{self.environment}',
                Namespace='LCopilot/Security',
                Period=300,
                Statistic='Maximum',
                Threshold=5,  # More than 5 suspicious IPs
                ActionsEnabled=True,
                AlarmActions=[],
                AlarmDescription=f'Suspicious IP activity detected in {self.environment}',
                Unit='Count',
                TreatMissingData='notBreaching'
            )

            # High risk events alarm
            high_risk_alarm_name = f'lcopilot-high-risk-security-{self.environment}'

            self.cloudwatch_client.put_metric_alarm(
                AlarmName=high_risk_alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName=f'HighRiskSecurityEvents-{self.environment}',
                Namespace='LCopilot/Security',
                Period=300,
                Statistic='Sum',
                Threshold=10,  # More than 10 high-risk events
                ActionsEnabled=True,
                AlarmActions=[],
                AlarmDescription=f'High-risk security events detected in {self.environment}',
                Unit='Count',
                TreatMissingData='notBreaching'
            )

            print(f"✅ Security alarms created:")
            print(f"   • {auth_alarm_name}")
            print(f"   • {suspicious_ip_alarm_name}")
            print(f"   • {high_risk_alarm_name}")

            return True

        except Exception as e:
            print(f"❌ Failed to create security alarms: {e}")
            return False

    def generate_security_report(self, events: List[SecurityEvent], anomalies: List[SecurityAnomaly]) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment,
            'summary': {
                'total_security_events': len(events),
                'total_anomalies': len(anomalies),
                'high_risk_events': len([e for e in events if e.risk_score > 80]),
                'unique_source_ips': len(set(e.ip_address for e in events)),
                'countries_involved': len(set(e.country_code for e in events if e.country_code))
            },
            'events_by_severity': {
                'high': len([e for e in events if e.severity == 'high']),
                'medium': len([e for e in events if e.severity == 'medium']),
                'low': len([e for e in events if e.severity == 'low'])
            },
            'top_source_ips': [],
            'anomalies': [],
            'recommendations': []
        }

        # Top source IPs
        ip_counts = Counter(event.ip_address for event in events)
        for ip, count in ip_counts.most_common(10):
            ip_events = [e for e in events if e.ip_address == ip]
            avg_risk = sum(e.risk_score for e in ip_events) / len(ip_events)

            report['top_source_ips'].append({
                'ip_address': ip,
                'event_count': count,
                'average_risk_score': avg_risk,
                'countries': list(set(e.country_code for e in ip_events if e.country_code))
            })

        # Anomalies
        for anomaly in anomalies:
            report['anomalies'].append({
                'type': anomaly.anomaly_type,
                'severity': anomaly.severity,
                'confidence': anomaly.confidence,
                'description': anomaly.description,
                'affected_ips_count': len(anomaly.affected_ips),
                'event_count': anomaly.event_count
            })

        # Generate recommendations
        if len(events) > self.failure_threshold:
            report['recommendations'].append({
                'priority': 'high',
                'category': 'authentication',
                'recommendation': 'Consider implementing additional authentication controls (MFA, IP whitelisting)',
                'rationale': f'Authentication failure count ({len(events)}) exceeds threshold ({self.failure_threshold})'
            })

        if any(a.anomaly_type == 'brute_force' for a in anomalies):
            report['recommendations'].append({
                'priority': 'high',
                'category': 'security',
                'recommendation': 'Implement rate limiting and IP blocking for repeated failures',
                'rationale': 'Brute force attacks detected'
            })

        return report

    def test_security_alert(self) -> bool:
        """Test security alerting system."""
        print(f"🧪 Testing security alert system for {self.environment}")

        try:
            # Publish test metrics that should trigger alarms
            test_metrics = [
                {
                    'MetricName': f'AuthFailureCount-{self.environment}',
                    'Value': self.failure_threshold + 5,  # Above threshold
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                },
                {
                    'MetricName': f'SuspiciousIPCount-{self.environment}',
                    'Value': 8,  # Above threshold
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                }
            ]

            self.cloudwatch_client.put_metric_data(
                Namespace='LCopilot/Security',
                MetricData=test_metrics
            )

            print(f"✅ Test metrics published - alarms should trigger within 5 minutes")
            print(f"   Monitor CloudWatch console for alarm state changes")

            return True

        except Exception as e:
            print(f"❌ Failed to test security alerts: {e}")
            return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot Security Monitoring System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 security_monitor.py --env prod --analyze-logs --hours 24
  python3 security_monitor.py --env staging --create-alarms
  python3 security_monitor.py --env prod --monitor auth-failures
  python3 security_monitor.py --env staging --test-alert
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod'],
                       default='prod', help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--analyze-logs', action='store_true', help='Analyze security logs')
    parser.add_argument('--hours', type=int, default=24, help='Hours back to analyze (default: 24)')
    parser.add_argument('--create-alarms', action='store_true', help='Create security alarms')
    parser.add_argument('--monitor', choices=['auth-failures'], help='Monitor specific security events')
    parser.add_argument('--test-alert', action='store_true', help='Test security alerting')
    parser.add_argument('--output', help='Save report to JSON file')

    args = parser.parse_args()

    # Initialize monitor
    monitor = SecurityMonitor(environment=args.env, aws_profile=args.profile)

    print(f"🔒 LCopilot Security Monitor")
    print(f"   Environment: {args.env}")
    print(f"   Region: {monitor.region}")

    if not monitor.initialize_aws_clients():
        sys.exit(1)

    # Create security alarms
    if args.create_alarms:
        success = monitor.create_security_alarms()
        if not success:
            sys.exit(1)
        return

    # Test security alerts
    if args.test_alert:
        success = monitor.test_security_alert()
        if not success:
            sys.exit(1)
        return

    # Analyze security logs
    if args.analyze_logs:
        log_group_name = f"/aws/lambda/lcopilot-{args.env}"

        print(f"📋 Analyzing security logs from {log_group_name}")
        print(f"   Time window: {args.hours} hours")

        # Parse security events
        events = monitor.parse_security_logs(log_group_name, args.hours)

        if events:
            print(f"✅ Found {len(events)} security events")

            # Detect anomalies
            anomalies = monitor.detect_anomalies(events)
            print(f"🚨 Detected {len(anomalies)} security anomalies")

            # Publish metrics
            monitor.publish_security_metrics(events, anomalies)

            # Generate report
            report = monitor.generate_security_report(events, anomalies)

            # Display summary
            print(f"\n📊 Security Analysis Summary:")
            print(f"   Total events: {report['summary']['total_security_events']}")
            print(f"   High-risk events: {report['summary']['high_risk_events']}")
            print(f"   Unique source IPs: {report['summary']['unique_source_ips']}")
            print(f"   Anomalies detected: {report['summary']['total_anomalies']}")

            if report['anomalies']:
                print(f"\n🚨 Security Anomalies:")
                for anomaly in report['anomalies']:
                    print(f"   • {anomaly['type']} ({anomaly['severity']}) - {anomaly['description']}")

            if report['recommendations']:
                print(f"\n💡 Security Recommendations:")
                for rec in report['recommendations']:
                    print(f"   • [{rec['priority'].upper()}] {rec['recommendation']}")

            # Save report if requested
            if args.output:
                try:
                    with open(args.output, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                    print(f"✅ Security report saved to {args.output}")
                except Exception as e:
                    print(f"❌ Failed to save report: {e}")

        else:
            print(f"ℹ️  No security events found in the specified time window")

        return

    # Show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    main()