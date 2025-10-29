"""
LCopilot Reliability CI/CD Automation Manager

Provides automated deployment, testing, and verification for reliability-as-a-service components.
Supports blue-green deployments, canary releases, automated rollback, and reliability validation.

Features:
- Automated deployment pipeline for reliability components
- Reliability testing and validation
- Blue-green and canary deployment strategies
- Automated rollback on reliability violations
- Infrastructure drift detection
- Performance regression testing
- SLA compliance validation
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import yaml
import subprocess
import hashlib
import time

logger = logging.getLogger(__name__)

class DeploymentStrategy(Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    IMMEDIATE = "immediate"

class ValidationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

class DeploymentStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class ReliabilityTest:
    test_id: str
    test_name: str
    test_type: str
    target_service: str
    expected_sla: float
    timeout_seconds: int
    validation_criteria: Dict[str, Any]
    tier_applicable: List[str]

@dataclass
class DeploymentConfig:
    deployment_id: str
    environment: str
    strategy: DeploymentStrategy
    services: List[str]
    health_check_url: str
    rollback_threshold: float
    validation_timeout: int
    canary_percentage: Optional[float] = None
    blue_green_swap_delay: Optional[int] = None

@dataclass
class ValidationResult:
    test_id: str
    status: ValidationStatus
    score: float
    message: str
    duration_seconds: float
    details: Dict[str, Any]
    timestamp: datetime

@dataclass
class DeploymentReport:
    deployment_id: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime]
    strategy_used: DeploymentStrategy
    services_deployed: List[str]
    validation_results: List[ValidationResult]
    rollback_triggered: bool
    performance_impact: Dict[str, float]
    cost_impact: float

class ReliabilityCICDManager:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.s3 = boto3.client('s3')
        self.cloudformation = boto3.client('cloudformation')
        self.codedeploy = boto3.client('codedeploy')
        self.cloudwatch = boto3.client('cloudwatch')
        self.lambda_client = boto3.client('lambda')

        self.config_path = Path(__file__).parent.parent / "config" / "reliability_config.yaml"
        self.reliability_config = self._load_reliability_config()

        self.artifacts_bucket = f"lcopilot-cicd-artifacts-{environment}"
        self.reports_bucket = f"lcopilot-deployment-reports-{environment}"

        # Initialize reliability tests
        self.reliability_tests = self._initialize_reliability_tests()

    def _load_reliability_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Reliability config not found at {self.config_path}")
            return {}

    def _initialize_reliability_tests(self) -> List[ReliabilityTest]:
        """Initialize standard reliability validation tests"""
        return [
            ReliabilityTest(
                test_id="availability_check",
                test_name="Service Availability Validation",
                test_type="health_check",
                target_service="api_gateway",
                expected_sla=99.9,
                timeout_seconds=30,
                validation_criteria={
                    "success_rate_threshold": 0.999,
                    "response_time_p95": 500,
                    "consecutive_success_count": 5
                },
                tier_applicable=["free", "pro", "enterprise"]
            ),
            ReliabilityTest(
                test_id="performance_regression",
                test_name="Performance Regression Test",
                test_type="load_test",
                target_service="lambda_functions",
                expected_sla=99.5,
                timeout_seconds=300,
                validation_criteria={
                    "latency_p95_threshold": 1000,
                    "throughput_degradation_max": 0.1,
                    "error_rate_threshold": 0.005
                },
                tier_applicable=["pro", "enterprise"]
            ),
            ReliabilityTest(
                test_id="sla_compliance_check",
                test_name="SLA Compliance Validation",
                test_type="sla_validation",
                target_service="reliability_stack",
                expected_sla=99.95,
                timeout_seconds=120,
                validation_criteria={
                    "uptime_threshold": 0.9995,
                    "mttr_threshold": 5,  # minutes
                    "incident_count_threshold": 0
                },
                tier_applicable=["enterprise"]
            ),
            ReliabilityTest(
                test_id="infrastructure_drift",
                test_name="Infrastructure Drift Detection",
                test_type="infrastructure",
                target_service="cloudformation_stacks",
                expected_sla=100.0,
                timeout_seconds=180,
                validation_criteria={
                    "drift_detection_threshold": 0,
                    "configuration_compliance": 1.0,
                    "security_group_changes": 0
                },
                tier_applicable=["pro", "enterprise"]
            ),
            ReliabilityTest(
                test_id="data_integrity_check",
                test_name="Data Integrity Validation",
                test_type="data_validation",
                target_service="data_stores",
                expected_sla=100.0,
                timeout_seconds=60,
                validation_criteria={
                    "data_consistency_check": True,
                    "backup_validation": True,
                    "encryption_validation": True
                },
                tier_applicable=["enterprise"]
            )
        ]

    def create_deployment_config(self, services: List[str], strategy: DeploymentStrategy,
                               tier: str = "enterprise") -> DeploymentConfig:
        """Create deployment configuration based on tier and strategy"""
        deployment_id = f"deploy_{int(datetime.utcnow().timestamp())}_{tier}_{self.environment}"

        # Tier-specific configuration
        if tier == "free":
            rollback_threshold = 0.9  # More tolerant
            validation_timeout = 300   # 5 minutes
        elif tier == "pro":
            rollback_threshold = 0.95
            validation_timeout = 600   # 10 minutes
        else:  # enterprise
            rollback_threshold = 0.99
            validation_timeout = 900   # 15 minutes

        # Strategy-specific configuration
        canary_percentage = None
        blue_green_swap_delay = None

        if strategy == DeploymentStrategy.CANARY:
            canary_percentage = 10.0 if tier == "enterprise" else 20.0
        elif strategy == DeploymentStrategy.BLUE_GREEN:
            blue_green_swap_delay = 300 if tier == "enterprise" else 180

        config = DeploymentConfig(
            deployment_id=deployment_id,
            environment=self.environment,
            strategy=strategy,
            services=services,
            health_check_url=f"https://api-{tier}-{self.environment}.lcopilot.com/health",
            rollback_threshold=rollback_threshold,
            validation_timeout=validation_timeout,
            canary_percentage=canary_percentage,
            blue_green_swap_delay=blue_green_swap_delay
        )

        logger.info(f"Created deployment config: {deployment_id} using {strategy.value} strategy")
        return config

    def execute_deployment(self, config: DeploymentConfig, tier: str = "enterprise") -> DeploymentReport:
        """Execute deployment using specified strategy and configuration"""
        logger.info(f"Starting deployment: {config.deployment_id}")

        report = DeploymentReport(
            deployment_id=config.deployment_id,
            status=DeploymentStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            completed_at=None,
            strategy_used=config.strategy,
            services_deployed=config.services,
            validation_results=[],
            rollback_triggered=False,
            performance_impact={},
            cost_impact=0.0
        )

        try:
            # Pre-deployment validation
            pre_validation_results = self._run_pre_deployment_validation(config, tier)
            report.validation_results.extend(pre_validation_results)

            # Check if pre-deployment validation passed
            if any(r.status == ValidationStatus.FAILED for r in pre_validation_results):
                raise Exception("Pre-deployment validation failed")

            # Execute deployment based on strategy
            if config.strategy == DeploymentStrategy.BLUE_GREEN:
                success = self._execute_blue_green_deployment(config, tier)
            elif config.strategy == DeploymentStrategy.CANARY:
                success = self._execute_canary_deployment(config, tier)
            elif config.strategy == DeploymentStrategy.ROLLING:
                success = self._execute_rolling_deployment(config, tier)
            else:  # IMMEDIATE
                success = self._execute_immediate_deployment(config, tier)

            if not success:
                raise Exception("Deployment execution failed")

            # Post-deployment validation
            post_validation_results = self._run_post_deployment_validation(config, tier)
            report.validation_results.extend(post_validation_results)

            # Check if post-deployment validation passed
            failed_validations = [r for r in post_validation_results if r.status == ValidationStatus.FAILED]

            if failed_validations:
                # Calculate failure rate
                failure_rate = len(failed_validations) / len(post_validation_results)

                if failure_rate > (1 - config.rollback_threshold):
                    logger.warning(f"Validation failure rate {failure_rate:.3f} exceeds threshold, triggering rollback")
                    self._execute_rollback(config, tier)
                    report.rollback_triggered = True
                    report.status = DeploymentStatus.ROLLED_BACK
                else:
                    logger.info(f"Validation failures within acceptable threshold: {failure_rate:.3f}")
                    report.status = DeploymentStatus.COMPLETED

            else:
                report.status = DeploymentStatus.COMPLETED

            # Calculate performance and cost impact
            report.performance_impact = self._calculate_performance_impact(config, tier)
            report.cost_impact = self._calculate_cost_impact(config, tier)

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            report.status = DeploymentStatus.FAILED

            # Attempt rollback
            try:
                self._execute_rollback(config, tier)
                report.rollback_triggered = True
                report.status = DeploymentStatus.ROLLED_BACK
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {str(rollback_error)}")

        finally:
            report.completed_at = datetime.utcnow()
            self._save_deployment_report(report)

        logger.info(f"Deployment completed: {config.deployment_id} with status {report.status.value}")
        return report

    def _run_pre_deployment_validation(self, config: DeploymentConfig, tier: str) -> List[ValidationResult]:
        """Run validation tests before deployment"""
        results = []

        # Filter tests applicable to tier
        applicable_tests = [t for t in self.reliability_tests if tier in t.tier_applicable]

        # Run infrastructure and preparation tests
        infrastructure_tests = [t for t in applicable_tests if t.test_type in ["infrastructure", "data_validation"]]

        for test in infrastructure_tests:
            result = self._execute_reliability_test(test, config, "pre_deployment")
            results.append(result)

        return results

    def _run_post_deployment_validation(self, config: DeploymentConfig, tier: str) -> List[ValidationResult]:
        """Run validation tests after deployment"""
        results = []

        # Filter tests applicable to tier
        applicable_tests = [t for t in self.reliability_tests if tier in t.tier_applicable]

        # Run all tests for comprehensive validation
        for test in applicable_tests:
            result = self._execute_reliability_test(test, config, "post_deployment")
            results.append(result)

        return results

    def _execute_reliability_test(self, test: ReliabilityTest, config: DeploymentConfig,
                                phase: str) -> ValidationResult:
        """Execute a single reliability test"""
        logger.info(f"Running {phase} test: {test.test_name}")

        start_time = datetime.utcnow()
        status = ValidationStatus.RUNNING

        try:
            if test.test_type == "health_check":
                score, details = self._run_health_check_test(test, config)
            elif test.test_type == "load_test":
                score, details = self._run_load_test(test, config)
            elif test.test_type == "sla_validation":
                score, details = self._run_sla_validation_test(test, config)
            elif test.test_type == "infrastructure":
                score, details = self._run_infrastructure_test(test, config)
            elif test.test_type == "data_validation":
                score, details = self._run_data_validation_test(test, config)
            else:
                raise ValueError(f"Unknown test type: {test.test_type}")

            # Determine pass/fail based on score vs expected SLA
            if score >= test.expected_sla:
                status = ValidationStatus.PASSED
                message = f"Test passed with score {score:.2f}"
            else:
                status = ValidationStatus.FAILED
                message = f"Test failed with score {score:.2f} (expected {test.expected_sla})"

        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            score = 0.0
            status = ValidationStatus.FAILED
            message = f"Test execution failed: {str(e)}"
            details = {"error": str(e)}

        duration = (datetime.utcnow() - start_time).total_seconds()

        return ValidationResult(
            test_id=test.test_id,
            status=status,
            score=score,
            message=message,
            duration_seconds=duration,
            details=details,
            timestamp=start_time
        )

    def _run_health_check_test(self, test: ReliabilityTest, config: DeploymentConfig) -> Tuple[float, Dict]:
        """Execute health check test"""
        success_count = 0
        total_attempts = test.validation_criteria.get("consecutive_success_count", 5)
        response_times = []

        for attempt in range(total_attempts):
            try:
                start_time = time.time()

                # Simulate health check (would make actual HTTP request)
                import random
                success = random.random() > 0.01  # 99% success rate simulation
                response_time = random.uniform(100, 300)  # Simulated response time

                if success:
                    success_count += 1
                    response_times.append(response_time)

                time.sleep(1)  # Wait between attempts

            except Exception as e:
                logger.error(f"Health check attempt {attempt + 1} failed: {str(e)}")

        success_rate = success_count / total_attempts
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Calculate score based on success rate and response time
        score = success_rate * 100
        if avg_response_time > test.validation_criteria.get("response_time_p95", 500):
            score *= 0.9  # Penalty for slow response times

        details = {
            "success_rate": success_rate,
            "successful_attempts": success_count,
            "total_attempts": total_attempts,
            "average_response_time": avg_response_time,
            "response_times": response_times
        }

        return score, details

    def _run_load_test(self, test: ReliabilityTest, config: DeploymentConfig) -> Tuple[float, Dict]:
        """Execute load test"""
        # Simulate load test execution
        import random

        # Simulated metrics
        latency_p95 = random.uniform(200, 800)
        throughput_rps = random.uniform(80, 120)
        error_rate = random.uniform(0.001, 0.01)

        # Score calculation based on validation criteria
        latency_score = min(100, (test.validation_criteria["latency_p95_threshold"] / latency_p95) * 100)
        error_score = max(0, 100 - (error_rate / test.validation_criteria["error_rate_threshold"]) * 100)

        overall_score = (latency_score + error_score) / 2

        details = {
            "latency_p95_ms": latency_p95,
            "throughput_rps": throughput_rps,
            "error_rate": error_rate,
            "latency_score": latency_score,
            "error_score": error_score,
            "duration_seconds": 60
        }

        return overall_score, details

    def _run_sla_validation_test(self, test: ReliabilityTest, config: DeploymentConfig) -> Tuple[float, Dict]:
        """Execute SLA validation test"""
        # Query recent reliability metrics
        try:
            # Simulate SLA metrics collection
            uptime_percentage = 99.98
            mttr_minutes = 3.5
            incident_count = 0

            # Calculate SLA compliance score
            uptime_score = min(100, (uptime_percentage / test.validation_criteria["uptime_threshold"]) * 100)
            mttr_score = max(0, 100 - (mttr_minutes / test.validation_criteria["mttr_threshold"]) * 10)
            incident_score = 100 if incident_count <= test.validation_criteria["incident_count_threshold"] else 50

            overall_score = (uptime_score + mttr_score + incident_score) / 3

            details = {
                "uptime_percentage": uptime_percentage,
                "mttr_minutes": mttr_minutes,
                "incident_count": incident_count,
                "uptime_score": uptime_score,
                "mttr_score": mttr_score,
                "incident_score": incident_score
            }

            return overall_score, details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _run_infrastructure_test(self, test: ReliabilityTest, config: DeploymentConfig) -> Tuple[float, Dict]:
        """Execute infrastructure validation test"""
        try:
            # Check CloudFormation stack drift
            stack_name = f"lcopilot-reliability-{self.environment}"

            try:
                # Simulate drift detection
                drift_status = "IN_SYNC"  # Would actually call detect_stack_drift
                drifted_resources = []

                if drift_status == "IN_SYNC":
                    drift_score = 100
                else:
                    drift_score = max(0, 100 - len(drifted_resources) * 10)

            except Exception:
                drift_score = 50  # Partial score if drift detection fails

            # Check security group compliance
            security_compliance = 95  # Simulated compliance score

            overall_score = (drift_score + security_compliance) / 2

            details = {
                "stack_name": stack_name,
                "drift_status": drift_status,
                "drifted_resources": drifted_resources,
                "security_compliance_score": security_compliance,
                "drift_score": drift_score
            }

            return overall_score, details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _run_data_validation_test(self, test: ReliabilityTest, config: DeploymentConfig) -> Tuple[float, Dict]:
        """Execute data validation test"""
        try:
            # Check data consistency
            consistency_score = 100  # Simulated

            # Check backup validation
            backup_score = 100  # Simulated

            # Check encryption
            encryption_score = 100  # Simulated

            overall_score = (consistency_score + backup_score + encryption_score) / 3

            details = {
                "data_consistency_score": consistency_score,
                "backup_validation_score": backup_score,
                "encryption_validation_score": encryption_score,
                "validation_timestamp": datetime.utcnow().isoformat()
            }

            return overall_score, details

        except Exception as e:
            return 0.0, {"error": str(e)}

    def _execute_blue_green_deployment(self, config: DeploymentConfig, tier: str) -> bool:
        """Execute blue-green deployment strategy"""
        logger.info(f"Executing blue-green deployment for {config.deployment_id}")

        try:
            # Step 1: Deploy to green environment
            green_stack = f"lcopilot-reliability-green-{tier}-{self.environment}"
            self._deploy_stack(green_stack, config.services)

            # Step 2: Wait for green environment to be healthy
            if config.blue_green_swap_delay:
                logger.info(f"Waiting {config.blue_green_swap_delay} seconds before traffic swap")
                time.sleep(config.blue_green_swap_delay)

            # Step 3: Swap traffic
            self._swap_traffic(tier, "green")

            # Step 4: Monitor for issues
            time.sleep(60)  # Monitor for 1 minute

            # Step 5: Remove blue environment if successful
            blue_stack = f"lcopilot-reliability-blue-{tier}-{self.environment}"
            # self._cleanup_stack(blue_stack)  # Would clean up old version

            return True

        except Exception as e:
            logger.error(f"Blue-green deployment failed: {str(e)}")
            return False

    def _execute_canary_deployment(self, config: DeploymentConfig, tier: str) -> bool:
        """Execute canary deployment strategy"""
        logger.info(f"Executing canary deployment for {config.deployment_id}")

        try:
            # Step 1: Deploy canary version
            canary_stack = f"lcopilot-reliability-canary-{tier}-{self.environment}"
            self._deploy_stack(canary_stack, config.services)

            # Step 2: Route small percentage of traffic to canary
            self._route_traffic_percentage(tier, "canary", config.canary_percentage or 10.0)

            # Step 3: Monitor canary performance
            time.sleep(300)  # Monitor for 5 minutes

            # Step 4: Gradually increase traffic if healthy
            self._route_traffic_percentage(tier, "canary", 50.0)
            time.sleep(300)

            # Step 5: Complete rollout
            self._route_traffic_percentage(tier, "canary", 100.0)

            return True

        except Exception as e:
            logger.error(f"Canary deployment failed: {str(e)}")
            return False

    def _execute_rolling_deployment(self, config: DeploymentConfig, tier: str) -> bool:
        """Execute rolling deployment strategy"""
        logger.info(f"Executing rolling deployment for {config.deployment_id}")

        try:
            # Update services one by one
            for service in config.services:
                logger.info(f"Updating service: {service}")

                # Deploy new version of service
                service_stack = f"lcopilot-{service}-{tier}-{self.environment}"
                self._deploy_stack(service_stack, [service])

                # Wait for health check
                time.sleep(60)

            return True

        except Exception as e:
            logger.error(f"Rolling deployment failed: {str(e)}")
            return False

    def _execute_immediate_deployment(self, config: DeploymentConfig, tier: str) -> bool:
        """Execute immediate deployment strategy"""
        logger.info(f"Executing immediate deployment for {config.deployment_id}")

        try:
            # Deploy all services at once
            stack_name = f"lcopilot-reliability-{tier}-{self.environment}"
            self._deploy_stack(stack_name, config.services)

            return True

        except Exception as e:
            logger.error(f"Immediate deployment failed: {str(e)}")
            return False

    def _deploy_stack(self, stack_name: str, services: List[str]) -> bool:
        """Deploy CloudFormation stack"""
        logger.info(f"Deploying stack: {stack_name} with services: {services}")

        try:
            # Simulate CloudFormation deployment
            # In real implementation, would call cloudformation.create_stack or update_stack
            time.sleep(30)  # Simulate deployment time

            logger.info(f"Stack deployed successfully: {stack_name}")
            return True

        except Exception as e:
            logger.error(f"Stack deployment failed: {str(e)}")
            return False

    def _swap_traffic(self, tier: str, target_environment: str) -> bool:
        """Swap traffic between blue/green environments"""
        logger.info(f"Swapping traffic to {target_environment} environment for {tier} tier")

        try:
            # Update Route 53 records or load balancer configuration
            # Simulate traffic swap
            time.sleep(10)

            logger.info(f"Traffic swapped to {target_environment}")
            return True

        except Exception as e:
            logger.error(f"Traffic swap failed: {str(e)}")
            return False

    def _route_traffic_percentage(self, tier: str, target: str, percentage: float) -> bool:
        """Route percentage of traffic to target environment"""
        logger.info(f"Routing {percentage}% of traffic to {target} for {tier} tier")

        try:
            # Update weighted routing or ALB target groups
            # Simulate traffic routing
            time.sleep(5)

            logger.info(f"Traffic routing updated: {percentage}% to {target}")
            return True

        except Exception as e:
            logger.error(f"Traffic routing failed: {str(e)}")
            return False

    def _execute_rollback(self, config: DeploymentConfig, tier: str) -> bool:
        """Execute deployment rollback"""
        logger.warning(f"Executing rollback for deployment: {config.deployment_id}")

        try:
            # Revert to previous known-good version
            if config.strategy == DeploymentStrategy.BLUE_GREEN:
                self._swap_traffic(tier, "blue")
            elif config.strategy == DeploymentStrategy.CANARY:
                self._route_traffic_percentage(tier, "production", 100.0)
            else:
                # Rolling rollback
                previous_stack = f"lcopilot-reliability-previous-{tier}-{self.environment}"
                self._deploy_stack(previous_stack, config.services)

            logger.info(f"Rollback completed for deployment: {config.deployment_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

    def _calculate_performance_impact(self, config: DeploymentConfig, tier: str) -> Dict[str, float]:
        """Calculate performance impact of deployment"""
        # Simulate performance impact calculation
        return {
            "response_time_change_percent": -2.5,  # 2.5% improvement
            "throughput_change_percent": 1.2,      # 1.2% improvement
            "error_rate_change_percent": -15.0,    # 15% reduction in errors
            "availability_change_percent": 0.1     # 0.1% improvement
        }

    def _calculate_cost_impact(self, config: DeploymentConfig, tier: str) -> float:
        """Calculate cost impact of deployment"""
        # Simulate cost impact calculation
        base_cost_per_hour = {"free": 0, "pro": 5.0, "enterprise": 15.0}
        deployment_overhead = 25.0  # Fixed overhead cost

        tier_cost = base_cost_per_hour.get(tier, 0)
        total_impact = deployment_overhead + (tier_cost * 0.1)  # 10% of hourly cost

        return total_impact

    def _save_deployment_report(self, report: DeploymentReport):
        """Save deployment report to S3"""
        try:
            report_key = f"deployment-reports/{report.deployment_id}.json"
            report_data = asdict(report)

            # Convert datetime objects to strings
            report_json = json.dumps(report_data, default=str, indent=2)

            self.s3.put_object(
                Bucket=self.reports_bucket,
                Key=report_key,
                Body=report_json,
                ContentType='application/json'
            )

            logger.info(f"Deployment report saved: {report_key}")

        except Exception as e:
            logger.error(f"Failed to save deployment report: {str(e)}")

def main():
    """Demo CI/CD automation functionality"""
    manager = ReliabilityCICDManager()

    print("=== LCopilot Reliability CI/CD Automation Demo ===")

    # Create deployment configuration for enterprise tier
    services = ["status_page", "sla_reporting", "trust_portal", "integration_apis"]

    print("\n1. Creating deployment configuration...")
    config = manager.create_deployment_config(
        services=services,
        strategy=DeploymentStrategy.CANARY,
        tier="enterprise"
    )

    print(f"Deployment ID: {config.deployment_id}")
    print(f"Strategy: {config.strategy.value}")
    print(f"Services: {config.services}")
    print(f"Rollback threshold: {config.rollback_threshold}")

    # Execute deployment
    print("\n2. Executing deployment...")
    report = manager.execute_deployment(config, tier="enterprise")

    print(f"Deployment Status: {report.status.value}")
    print(f"Rollback Triggered: {report.rollback_triggered}")
    print(f"Validation Results: {len(report.validation_results)} tests")

    # Show validation results
    print("\n3. Validation Results:")
    for result in report.validation_results:
        status_emoji = "✅" if result.status == ValidationStatus.PASSED else "❌"
        print(f"  {status_emoji} {result.test_id}: {result.message} (Score: {result.score:.1f})")

    # Show performance impact
    print(f"\n4. Performance Impact:")
    for metric, value in report.performance_impact.items():
        print(f"  {metric}: {value:+.1f}%")

    print(f"\n5. Cost Impact: ${report.cost_impact:.2f}")

    if report.completed_at:
        duration = (report.completed_at - report.started_at).total_seconds()
        print(f"6. Deployment Duration: {duration:.0f} seconds")

if __name__ == "__main__":
    main()