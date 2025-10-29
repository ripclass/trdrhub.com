#!/usr/bin/env python3
"""
LCopilot Chaos Engineering Controller

Implements controlled fault injection to test monitoring and alerting systems.
Provides safe, time-limited chaos experiments to validate system resilience.

Fault Types:
1. error_spike: Increase error rate by specified multiplier
2. latency_injection: Add artificial latency to responses
3. log_pipeline_drop: Simulate log pipeline failures (simulation only)

Safety Features:
- Time-limited experiments with auto-rollback
- Environment-based safety controls (prod requires --force)
- Change ticket requirements for production
- Feature flag based control system

Usage:
    python3 chaos_controller.py --env staging --fault error_spike --duration 120
    python3 chaos_controller.py --env prod --fault latency_injection --duration 300 --force
    python3 chaos_controller.py --list-active --env staging
    python3 chaos_controller.py --emergency-stop --env staging
"""

import os
import sys
import json
import time
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import threading
import signal


@dataclass
class ChaosExperiment:
    """Represents an active chaos experiment."""
    experiment_id: str
    fault_type: str
    environment: str
    start_time: datetime
    duration_seconds: int
    parameters: Dict[str, Any]
    auto_rollback: bool = True
    change_ticket: Optional[str] = None


class ChaosController:
    """Chaos engineering controller for LCopilot."""

    def __init__(self, environment: str = "staging", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})
        self.chaos_config = self.config.get('chaos', {})

        # Safety checks
        self.is_prod = environment == 'prod'
        self.allowed_in_env = self._check_environment_permissions()

        # AWS clients
        self.dynamodb_client = None
        self.cloudwatch_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Active experiments tracking
        self.active_experiments: List[ChaosExperiment] = []
        self.stop_event = threading.Event()

        # Fault type definitions
        self.fault_types = self._load_fault_definitions()

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
            'chaos': {
                'allowed_in_prod': False,
                'allowed_in_staging': True,
                'fault_types': {
                    'error_spike': {
                        'enabled': True,
                        'duration_seconds': 120,
                        'error_rate_multiplier': 10
                    },
                    'latency_injection': {
                        'enabled': True,
                        'duration_seconds': 300,
                        'latency_ms_range': [500, 2000]
                    }
                },
                'safety': {
                    'require_change_ticket_prod': True,
                    'max_duration_seconds': 600,
                    'auto_rollback': True
                }
            }
        }

    def _check_environment_permissions(self) -> bool:
        """Check if chaos testing is allowed in current environment."""
        if self.is_prod:
            return self.chaos_config.get('allowed_in_prod', False)
        else:
            return self.chaos_config.get('allowed_in_staging', True)

    def _load_fault_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load fault type definitions from configuration."""
        return self.chaos_config.get('fault_types', {
            'error_spike': {
                'enabled': True,
                'duration_seconds': 120,
                'error_rate_multiplier': 10
            },
            'latency_injection': {
                'enabled': True,
                'duration_seconds': 300,
                'latency_ms_range': [500, 2000]
            },
            'log_pipeline_drop': {
                'enabled': False,
                'duration_seconds': 60
            }
        })

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.dynamodb_client = session.client('dynamodb')
            self.cloudwatch_client = session.client('cloudwatch')

            # Test connections
            self.dynamodb_client.describe_limits()
            self.cloudwatch_client.describe_alarms(MaxRecords=1)

            print(f"✅ AWS clients initialized for {self.region}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def validate_experiment_request(self, fault_type: str, duration_seconds: int,
                                  force: bool = False, change_ticket: Optional[str] = None) -> Tuple[bool, str]:
        """Validate chaos experiment request against safety policies."""

        # Check environment permissions
        if not self.allowed_in_env and not force:
            return False, f"Chaos testing not allowed in {self.environment} environment. Use --force to override."

        # Check if fault type is enabled
        fault_config = self.fault_types.get(fault_type)
        if not fault_config:
            return False, f"Unknown fault type: {fault_type}"

        if not fault_config.get('enabled', False):
            return False, f"Fault type '{fault_type}' is disabled in configuration"

        # Check duration limits
        max_duration = self.chaos_config.get('safety', {}).get('max_duration_seconds', 600)
        if duration_seconds > max_duration:
            return False, f"Duration {duration_seconds}s exceeds maximum allowed {max_duration}s"

        # Production safety checks
        if self.is_prod:
            safety_config = self.chaos_config.get('safety', {})

            if not force:
                return False, "Production chaos testing requires --force flag"

            if safety_config.get('require_change_ticket_prod', True) and not change_ticket:
                return False, "Production chaos testing requires --change-ticket parameter"

        return True, "Validation passed"

    def set_feature_flag(self, flag_name: str, value: Any) -> bool:
        """Set chaos feature flag in DynamoDB."""
        table_name = self.chaos_config.get('feature_flags', {}).get('table_name', '').format(env=self.environment)
        if not table_name:
            print(f"⚠️  Feature flags table not configured for {self.environment}")
            return False

        try:
            self.dynamodb_client.put_item(
                TableName=table_name,
                Item={
                    'flag_name': {'S': flag_name},
                    'value': {'S': str(value)},
                    'environment': {'S': self.environment},
                    'updated_at': {'S': datetime.now().isoformat()},
                    'ttl': {'N': str(int((datetime.now() + timedelta(hours=2)).timestamp()))}
                }
            )

            print(f"✅ Feature flag set: {flag_name} = {value}")
            return True
        except Exception as e:
            print(f"❌ Failed to set feature flag {flag_name}: {e}")
            return False

    def clear_feature_flag(self, flag_name: str) -> bool:
        """Clear chaos feature flag."""
        table_name = self.chaos_config.get('feature_flags', {}).get('table_name', '').format(env=self.environment)
        if not table_name:
            return False

        try:
            self.dynamodb_client.delete_item(
                TableName=table_name,
                Key={
                    'flag_name': {'S': flag_name},
                    'environment': {'S': self.environment}
                }
            )

            print(f"✅ Feature flag cleared: {flag_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to clear feature flag {flag_name}: {e}")
            return False

    def start_error_spike(self, duration_seconds: int, error_rate_multiplier: int = 10) -> str:
        """Start error spike chaos experiment."""
        experiment_id = f"error-spike-{self.environment}-{int(time.time())}"

        print(f"🔥 Starting error spike experiment: {experiment_id}")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Error rate multiplier: {error_rate_multiplier}x")

        # Set feature flag to trigger errors
        if not self.set_feature_flag('CHAOS_ERROR_RATE', error_rate_multiplier):
            return ""

        # Publish metric to track experiment
        self.publish_chaos_metric('ChaosExperimentActive', 1,
                                {'ExperimentType': 'error_spike', 'ExperimentId': experiment_id})

        # Create experiment record
        experiment = ChaosExperiment(
            experiment_id=experiment_id,
            fault_type='error_spike',
            environment=self.environment,
            start_time=datetime.now(),
            duration_seconds=duration_seconds,
            parameters={'error_rate_multiplier': error_rate_multiplier}
        )

        self.active_experiments.append(experiment)

        # Schedule automatic rollback
        rollback_timer = threading.Timer(duration_seconds, self.rollback_error_spike, [experiment_id])
        rollback_timer.start()

        return experiment_id

    def start_latency_injection(self, duration_seconds: int, latency_ms_min: int = 500,
                               latency_ms_max: int = 2000) -> str:
        """Start latency injection chaos experiment."""
        experiment_id = f"latency-injection-{self.environment}-{int(time.time())}"

        print(f"🐌 Starting latency injection experiment: {experiment_id}")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Latency range: {latency_ms_min}-{latency_ms_max}ms")

        # Set feature flag to trigger latency
        latency_config = f"{latency_ms_min},{latency_ms_max}"
        if not self.set_feature_flag('CHAOS_LATENCY_MS', latency_config):
            return ""

        # Publish metric
        self.publish_chaos_metric('ChaosExperimentActive', 1,
                                {'ExperimentType': 'latency_injection', 'ExperimentId': experiment_id})

        # Create experiment record
        experiment = ChaosExperiment(
            experiment_id=experiment_id,
            fault_type='latency_injection',
            environment=self.environment,
            start_time=datetime.now(),
            duration_seconds=duration_seconds,
            parameters={'latency_ms_min': latency_ms_min, 'latency_ms_max': latency_ms_max}
        )

        self.active_experiments.append(experiment)

        # Schedule automatic rollback
        rollback_timer = threading.Timer(duration_seconds, self.rollback_latency_injection, [experiment_id])
        rollback_timer.start()

        return experiment_id

    def start_log_pipeline_drop(self, duration_seconds: int) -> str:
        """Start log pipeline drop simulation (does not actually drop logs)."""
        experiment_id = f"log-drop-sim-{self.environment}-{int(time.time())}"

        print(f"📋 Starting log pipeline drop SIMULATION: {experiment_id}")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   ⚠️  This is a SIMULATION - logs will not actually be dropped")

        # Set feature flag to simulate log drops (for monitoring purposes)
        if not self.set_feature_flag('CHAOS_DROP_LOGS', 'SIMULATION'):
            return ""

        # Publish metric
        self.publish_chaos_metric('ChaosExperimentActive', 1,
                                {'ExperimentType': 'log_drop_simulation', 'ExperimentId': experiment_id})

        # Create experiment record
        experiment = ChaosExperiment(
            experiment_id=experiment_id,
            fault_type='log_pipeline_drop',
            environment=self.environment,
            start_time=datetime.now(),
            duration_seconds=duration_seconds,
            parameters={'simulation_only': True}
        )

        self.active_experiments.append(experiment)

        # Schedule automatic rollback
        rollback_timer = threading.Timer(duration_seconds, self.rollback_log_pipeline_drop, [experiment_id])
        rollback_timer.start()

        return experiment_id

    def rollback_error_spike(self, experiment_id: str):
        """Rollback error spike experiment."""
        print(f"🔄 Rolling back error spike experiment: {experiment_id}")

        self.clear_feature_flag('CHAOS_ERROR_RATE')
        self.publish_chaos_metric('ChaosExperimentActive', 0, {'ExperimentType': 'error_spike'})

        # Remove from active experiments
        self.active_experiments = [e for e in self.active_experiments if e.experiment_id != experiment_id]

        print(f"✅ Error spike experiment rolled back: {experiment_id}")

    def rollback_latency_injection(self, experiment_id: str):
        """Rollback latency injection experiment."""
        print(f"🔄 Rolling back latency injection experiment: {experiment_id}")

        self.clear_feature_flag('CHAOS_LATENCY_MS')
        self.publish_chaos_metric('ChaosExperimentActive', 0, {'ExperimentType': 'latency_injection'})

        # Remove from active experiments
        self.active_experiments = [e for e in self.active_experiments if e.experiment_id != experiment_id]

        print(f"✅ Latency injection experiment rolled back: {experiment_id}")

    def rollback_log_pipeline_drop(self, experiment_id: str):
        """Rollback log pipeline drop simulation."""
        print(f"🔄 Rolling back log drop simulation: {experiment_id}")

        self.clear_feature_flag('CHAOS_DROP_LOGS')
        self.publish_chaos_metric('ChaosExperimentActive', 0, {'ExperimentType': 'log_drop_simulation'})

        # Remove from active experiments
        self.active_experiments = [e for e in self.active_experiments if e.experiment_id != experiment_id]

        print(f"✅ Log drop simulation rolled back: {experiment_id}")

    def emergency_stop_all(self) -> bool:
        """Emergency stop all active experiments."""
        print(f"🚨 EMERGENCY STOP: Stopping all active chaos experiments in {self.environment}")

        # Clear all chaos feature flags
        chaos_flags = self.chaos_config.get('feature_flags', {}).get('flags', [])
        for flag in chaos_flags:
            self.clear_feature_flag(flag)

        # Stop all active experiments
        for experiment in self.active_experiments[:]:
            if experiment.fault_type == 'error_spike':
                self.rollback_error_spike(experiment.experiment_id)
            elif experiment.fault_type == 'latency_injection':
                self.rollback_latency_injection(experiment.experiment_id)
            elif experiment.fault_type == 'log_pipeline_drop':
                self.rollback_log_pipeline_drop(experiment.experiment_id)

        self.active_experiments.clear()

        print(f"✅ All chaos experiments stopped in {self.environment}")
        return True

    def list_active_experiments(self) -> List[Dict[str, Any]]:
        """List all active chaos experiments."""
        active_list = []

        for experiment in self.active_experiments:
            elapsed_time = (datetime.now() - experiment.start_time).total_seconds()
            remaining_time = max(0, experiment.duration_seconds - elapsed_time)

            active_list.append({
                'experiment_id': experiment.experiment_id,
                'fault_type': experiment.fault_type,
                'environment': experiment.environment,
                'start_time': experiment.start_time.isoformat(),
                'duration_seconds': experiment.duration_seconds,
                'elapsed_seconds': int(elapsed_time),
                'remaining_seconds': int(remaining_time),
                'parameters': experiment.parameters,
                'status': 'active' if remaining_time > 0 else 'completing'
            })

        return active_list

    def publish_chaos_metric(self, metric_name: str, value: float, dimensions: Optional[Dict[str, str]] = None):
        """Publish chaos experiment metrics to CloudWatch."""
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.now()
            }

            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]

            self.cloudwatch_client.put_metric_data(
                Namespace='LCopilot/Chaos',
                MetricData=[metric_data]
            )
        except Exception as e:
            print(f"⚠️  Failed to publish chaos metric: {e}")


def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    print(f"\n🛑 Received signal {signum}, stopping chaos experiments...")
    sys.exit(0)


def main():
    """Main CLI interface."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(
        description='LCopilot Chaos Engineering Controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 chaos_controller.py --env staging --fault error_spike --duration 120
  python3 chaos_controller.py --env staging --fault latency_injection --duration 300 --latency-min 1000 --latency-max 3000
  python3 chaos_controller.py --env staging --list-active
  python3 chaos_controller.py --env staging --emergency-stop
  python3 chaos_controller.py --env prod --fault error_spike --duration 60 --force --change-ticket CHG-123456
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod'],
                       default='staging', help='Environment (default: staging)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--fault', choices=['error_spike', 'latency_injection', 'log_pipeline_drop'],
                       help='Fault type to inject')
    parser.add_argument('--duration', type=int, default=120,
                       help='Experiment duration in seconds (default: 120)')
    parser.add_argument('--error-multiplier', type=int, default=10,
                       help='Error rate multiplier for error_spike (default: 10)')
    parser.add_argument('--latency-min', type=int, default=500,
                       help='Minimum latency in ms for latency_injection (default: 500)')
    parser.add_argument('--latency-max', type=int, default=2000,
                       help='Maximum latency in ms for latency_injection (default: 2000)')
    parser.add_argument('--force', action='store_true',
                       help='Force execution (required for production)')
    parser.add_argument('--change-ticket', help='Change ticket number (required for production)')
    parser.add_argument('--list-active', action='store_true',
                       help='List active experiments')
    parser.add_argument('--emergency-stop', action='store_true',
                       help='Emergency stop all active experiments')

    args = parser.parse_args()

    # Initialize controller
    controller = ChaosController(environment=args.env, aws_profile=args.profile)

    print(f"🌪️  LCopilot Chaos Engineering Controller")
    print(f"   Environment: {args.env}")
    print(f"   Safety mode: {'PRODUCTION' if controller.is_prod else 'DEVELOPMENT'}")

    if not controller.initialize_aws_clients():
        sys.exit(1)

    # List active experiments
    if args.list_active:
        active = controller.list_active_experiments()
        if active:
            print(f"\n📊 Active Chaos Experiments ({len(active)}):")
            for exp in active:
                print(f"   • {exp['experiment_id']}")
                print(f"     Type: {exp['fault_type']}")
                print(f"     Remaining: {exp['remaining_seconds']}s")
                print(f"     Parameters: {exp['parameters']}")
        else:
            print(f"\nℹ️  No active chaos experiments in {args.env}")
        return

    # Emergency stop
    if args.emergency_stop:
        controller.emergency_stop_all()
        return

    # Start fault injection
    if args.fault:
        # Validate experiment
        valid, message = controller.validate_experiment_request(
            args.fault, args.duration, args.force, args.change_ticket
        )

        if not valid:
            print(f"❌ Experiment validation failed: {message}")
            sys.exit(1)

        print(f"✅ Experiment validation passed")

        # Start the appropriate fault type
        experiment_id = ""

        if args.fault == 'error_spike':
            experiment_id = controller.start_error_spike(args.duration, args.error_multiplier)
        elif args.fault == 'latency_injection':
            experiment_id = controller.start_latency_injection(
                args.duration, args.latency_min, args.latency_max
            )
        elif args.fault == 'log_pipeline_drop':
            experiment_id = controller.start_log_pipeline_drop(args.duration)

        if experiment_id:
            print(f"🎯 Chaos experiment started: {experiment_id}")
            print(f"   Duration: {args.duration} seconds")
            print(f"   Auto-rollback: ✅ Enabled")
            print(f"\n⚠️  Monitor your alerts and dashboards during this experiment!")
            print(f"   Emergency stop: python3 chaos_controller.py --env {args.env} --emergency-stop")
        else:
            print(f"❌ Failed to start chaos experiment")
            sys.exit(1)

        return

    # Show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    main()