"""
Workflow Service
Custom per-bank workflows, rule overrides, and policy versioning
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.workflows import (
    BankWorkflow, RuleOverride, PolicyVersion, EscalationRule, WorkflowExecution,
    WorkflowStatus, RuleComparator, EscalationPriority
)
from app.config import settings
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service
from app.core.exceptions import ValidationError, ConfigurationError

import logging

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing bank-specific workflows and rule overrides"""

    def __init__(self):
        self.base_rules_cache: Dict[str, Dict[str, Any]] = {}
        self.effective_rules_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(minutes=15)

    async def create_bank_workflow(
        self,
        db: Session,
        bank_id: str,
        tenant_id: str,
        name: str,
        workflow_type: str,
        base_config: Dict[str, Any],
        created_by: UUID,
        description: Optional[str] = None
    ) -> BankWorkflow:
        """Create a new bank-specific workflow"""

        # Validate workflow type
        allowed_types = ["lc_validation", "doc_review", "risk_assessment", "compliance_check"]
        if workflow_type not in allowed_types:
            raise ValidationError(f"Invalid workflow type: {workflow_type}")

        # Validate base configuration
        await self._validate_workflow_config(workflow_type, base_config)

        # Create workflow
        workflow = BankWorkflow(
            bank_id=bank_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            workflow_type=workflow_type,
            base_config=base_config,
            status=WorkflowStatus.DRAFT,
            created_by=created_by
        )

        db.add(workflow)
        db.flush()

        # Create initial policy version
        await self._create_initial_policy_version(db, workflow.id, created_by)

        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=tenant_id,
            event_type="workflow.created",
            actor_id=created_by,
            resource_type="bank_workflow",
            resource_id=str(workflow.id),
            details={
                "bank_id": bank_id,
                "name": name,
                "workflow_type": workflow_type
            }
        )

        return workflow

    async def add_rule_override(
        self,
        db: Session,
        workflow_id: UUID,
        rule_key: str,
        comparator: str,
        value_data: Any,
        created_by: UUID,
        rule_category: str = "validation",
        condition_expr: Optional[str] = None,
        severity_override: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        requires_approval: bool = False
    ) -> RuleOverride:
        """Add a rule override to a workflow"""

        workflow = db.query(BankWorkflow).filter(BankWorkflow.id == workflow_id).first()
        if not workflow:
            raise ValidationError("Workflow not found")

        # Validate rule key format
        if not self._is_valid_rule_key(rule_key):
            raise ValidationError(f"Invalid rule key format: {rule_key}")

        # Validate comparator
        if comparator not in [c.value for c in RuleComparator]:
            raise ValidationError(f"Invalid comparator: {comparator}")

        # Check for existing override
        existing = db.query(RuleOverride).filter(
            and_(
                RuleOverride.workflow_id == workflow_id,
                RuleOverride.rule_key == rule_key,
                or_(
                    RuleOverride.effective_to.is_(None),
                    RuleOverride.effective_to > datetime.utcnow()
                )
            )
        ).first()

        if existing:
            # Expire existing override
            existing.effective_to = datetime.utcnow()

        # Create new override
        override = RuleOverride(
            workflow_id=workflow_id,
            rule_key=rule_key,
            rule_category=rule_category,
            comparator=comparator,
            value_data=value_data,
            condition_expr=condition_expr,
            override_severity=severity_override,
            effective_from=effective_from or datetime.utcnow(),
            effective_to=effective_to,
            requires_approval=requires_approval,
            created_by=created_by
        )

        db.add(override)
        db.commit()

        # Invalidate cache
        self._invalidate_cache(workflow.bank_id)

        # Emit audit event
        await audit_service.log_event(
            tenant_id=workflow.tenant_id,
            event_type="workflow.rule_override.added",
            actor_id=created_by,
            resource_type="rule_override",
            resource_id=str(override.id),
            details={
                "workflow_id": str(workflow_id),
                "rule_key": rule_key,
                "comparator": comparator,
                "requires_approval": requires_approval
            }
        )

        return override

    async def create_policy_version(
        self,
        db: Session,
        workflow_id: UUID,
        version: str,
        name: str,
        policy_config: Dict[str, Any],
        created_by: UUID,
        description: Optional[str] = None,
        changelog: Optional[Dict[str, Any]] = None
    ) -> PolicyVersion:
        """Create a new policy version"""

        workflow = db.query(BankWorkflow).filter(BankWorkflow.id == workflow_id).first()
        if not workflow:
            raise ValidationError("Workflow not found")

        # Check version uniqueness
        existing = db.query(PolicyVersion).filter(
            and_(
                PolicyVersion.workflow_id == workflow_id,
                PolicyVersion.version == version
            )
        ).first()

        if existing:
            raise ValidationError(f"Version {version} already exists")

        # Validate policy configuration
        validation_errors = await self._validate_policy_config(policy_config)
        if validation_errors:
            raise ValidationError(f"Policy configuration errors: {validation_errors}")

        # Calculate config hash
        config_hash = hashlib.sha256(
            json.dumps(policy_config, sort_keys=True).encode()
        ).hexdigest()

        # Create policy version
        policy_version = PolicyVersion(
            workflow_id=workflow_id,
            version=version,
            name=name,
            description=description,
            policy_config=policy_config,
            config_hash=config_hash,
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors if validation_errors else None,
            changelog=changelog,
            created_by=created_by
        )

        db.add(policy_version)
        db.commit()

        # Invalidate cache
        self._invalidate_cache(workflow.bank_id)

        # Emit audit event
        await audit_service.log_event(
            tenant_id=workflow.tenant_id,
            event_type="workflow.policy_version.created",
            actor_id=created_by,
            resource_type="policy_version",
            resource_id=str(policy_version.id),
            details={
                "workflow_id": str(workflow_id),
                "version": version,
                "name": name,
                "config_hash": config_hash
            }
        )

        return policy_version

    async def activate_policy_version(
        self,
        db: Session,
        version_id: UUID,
        activated_by: UUID,
        set_as_default: bool = False
    ) -> PolicyVersion:
        """Activate a policy version"""

        policy_version = db.query(PolicyVersion).filter(PolicyVersion.id == version_id).first()
        if not policy_version:
            raise ValidationError("Policy version not found")

        if not policy_version.is_valid:
            raise ValidationError("Cannot activate invalid policy version")

        workflow = policy_version.workflow

        # Deactivate other versions
        db.query(PolicyVersion).filter(
            and_(
                PolicyVersion.workflow_id == workflow.id,
                PolicyVersion.id != version_id
            )
        ).update({"is_active": False})

        # Activate this version
        policy_version.is_active = True
        policy_version.published_by = activated_by
        policy_version.published_at = datetime.utcnow()

        if set_as_default:
            # Clear default flag from other versions
            db.query(PolicyVersion).filter(
                and_(
                    PolicyVersion.workflow_id == workflow.id,
                    PolicyVersion.id != version_id
                )
            ).update({"is_default": False})

            policy_version.is_default = True
            workflow.default_policy_version = policy_version.version

        # Update workflow's current version
        workflow.current_policy_version = policy_version.version

        db.commit()

        # Invalidate cache
        self._invalidate_cache(workflow.bank_id)

        # Emit audit event
        await audit_service.log_event(
            tenant_id=workflow.tenant_id,
            event_type="workflow.policy_version.activated",
            actor_id=activated_by,
            resource_type="policy_version",
            resource_id=str(version_id),
            details={
                "workflow_id": str(workflow.id),
                "version": policy_version.version,
                "set_as_default": set_as_default
            }
        )

        return policy_version

    async def get_effective_rules(
        self,
        db: Session,
        bank_id: str,
        workflow_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get effective rules for a bank workflow (base rules + overrides)"""

        cache_key = f"{bank_id}:{workflow_type}"

        # Check cache first
        if cache_key in self.effective_rules_cache:
            cached_entry = self.effective_rules_cache[cache_key]
            if datetime.utcnow() - cached_entry["timestamp"] < self.cache_ttl:
                return cached_entry["rules"]

        # Get base rules
        base_rules = await self._get_base_rules(workflow_type)

        # Get bank workflow
        workflow = db.query(BankWorkflow).filter(
            and_(
                BankWorkflow.bank_id == bank_id,
                BankWorkflow.workflow_type == workflow_type,
                BankWorkflow.status == WorkflowStatus.ACTIVE
            )
        ).first()

        if not workflow:
            # Return base rules if no custom workflow
            return base_rules

        # Get active policy version
        policy_version = db.query(PolicyVersion).filter(
            and_(
                PolicyVersion.workflow_id == workflow.id,
                PolicyVersion.is_active == True
            )
        ).first()

        # Start with base rules
        effective_rules = base_rules.copy()

        # Apply policy version config
        if policy_version and policy_version.policy_config:
            effective_rules = self._merge_configs(effective_rules, policy_version.policy_config)

        # Apply workflow base config
        if workflow.base_config:
            effective_rules = self._merge_configs(effective_rules, workflow.base_config)

        # Get active rule overrides
        now = datetime.utcnow()
        overrides = db.query(RuleOverride).filter(
            and_(
                RuleOverride.workflow_id == workflow.id,
                RuleOverride.effective_from <= now,
                or_(
                    RuleOverride.effective_to.is_(None),
                    RuleOverride.effective_to > now
                ),
                or_(
                    RuleOverride.approved_at.is_not(None),
                    RuleOverride.requires_approval == False
                )
            )
        ).all()

        # Apply overrides
        for override in overrides:
            # Check condition if provided
            if override.condition_expr and context:
                if not self._evaluate_condition(override.condition_expr, context):
                    continue

            # Apply override
            effective_rules = self._apply_rule_override(effective_rules, override)

            # Update usage tracking
            override.applied_count = override.applied_count + 1
            override.last_applied_at = datetime.utcnow()

        db.commit()

        # Cache result
        self.effective_rules_cache[cache_key] = {
            "rules": effective_rules,
            "timestamp": datetime.utcnow()
        }

        return effective_rules

    async def add_escalation_rule(
        self,
        db: Session,
        workflow_id: UUID,
        name: str,
        condition_expr: str,
        target_team: str,
        notification_channels: List[str],
        created_by: UUID,
        description: Optional[str] = None,
        delay_minutes: int = 0,
        priority: str = EscalationPriority.NORMAL,
        target_users: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None
    ) -> EscalationRule:
        """Add escalation rule to workflow"""

        workflow = db.query(BankWorkflow).filter(BankWorkflow.id == workflow_id).first()
        if not workflow:
            raise ValidationError("Workflow not found")

        # Validate condition expression
        if not self._validate_condition_expr(condition_expr):
            raise ValidationError("Invalid condition expression")

        # Create escalation rule
        escalation_rule = EscalationRule(
            workflow_id=workflow_id,
            name=name,
            description=description,
            condition_expr=condition_expr,
            trigger_events=["discrepancy.high", "validation.failed", "timeout.exceeded"],
            delay_minutes=delay_minutes,
            target_team=target_team,
            target_users=target_users,
            target_roles=target_roles,
            notification_channels=notification_channels,
            priority=priority,
            created_by=created_by
        )

        db.add(escalation_rule)
        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=workflow.tenant_id,
            event_type="workflow.escalation_rule.added",
            actor_id=created_by,
            resource_type="escalation_rule",
            resource_id=str(escalation_rule.id),
            details={
                "workflow_id": str(workflow_id),
                "name": name,
                "target_team": target_team,
                "priority": priority
            }
        )

        return escalation_rule

    async def execute_workflow(
        self,
        db: Session,
        workflow_id: UUID,
        trigger_event: str,
        execution_context: Dict[str, Any],
        job_id: Optional[UUID] = None
    ) -> WorkflowExecution:
        """Execute a workflow"""

        workflow = db.query(BankWorkflow).filter(BankWorkflow.id == workflow_id).first()
        if not workflow:
            raise ValidationError("Workflow not found")

        # Get effective rules
        effective_rules = await self.get_effective_rules(
            db, workflow.bank_id, workflow.workflow_type, execution_context
        )

        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            job_id=job_id,
            trigger_event=trigger_event,
            execution_context=execution_context,
            status="started",
            policy_version_used=workflow.current_policy_version
        )

        db.add(execution)
        db.flush()

        try:
            # Execute workflow steps
            result = await self._execute_workflow_logic(
                workflow, effective_rules, execution_context
            )

            # Update execution
            execution.status = "completed"
            execution.finished_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.finished_at - execution.started_at).total_seconds() * 1000
            )
            execution.output_data = result

            # Update workflow usage
            workflow.jobs_processed = workflow.jobs_processed + 1
            workflow.last_used_at = datetime.utcnow()

            db.commit()

            return execution

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")

            execution.status = "failed"
            execution.finished_at = datetime.utcnow()
            execution.error_details = {"error": str(e), "type": type(e).__name__}

            db.commit()
            raise

    async def _get_base_rules(self, workflow_type: str) -> Dict[str, Any]:
        """Get base rules for workflow type"""

        if workflow_type in self.base_rules_cache:
            return self.base_rules_cache[workflow_type]

        # Load base rules from configuration
        base_rules = {
            "lc_validation": {
                "UCP600.Art14.date_format": {
                    "pattern": r"\d{2}[/-]\d{2}[/-]\d{4}",
                    "severity": "error",
                    "message": "Date must be in DD/MM/YYYY or DD-MM-YYYY format"
                },
                "UCP600.Art18.amount_validation": {
                    "max_amount": 10000000,
                    "currency_required": True,
                    "severity": "error"
                }
            },
            "doc_review": {
                "invoice.amount_match": {
                    "tolerance_percent": 5.0,
                    "severity": "warning"
                }
            },
            "risk_assessment": {
                "country_risk.threshold": {
                    "max_score": 70,
                    "severity": "warning"
                }
            }
        }

        rules = base_rules.get(workflow_type, {})
        self.base_rules_cache[workflow_type] = rules
        return rules

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries"""

        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_rule_override(self, rules: Dict[str, Any], override: RuleOverride) -> Dict[str, Any]:
        """Apply a single rule override to the rules configuration"""

        rule_key = override.rule_key
        comparator = override.comparator
        value_data = override.value_data

        # Navigate to the rule using dot notation
        rule_path = rule_key.split('.')
        current = rules

        # Navigate to parent
        for part in rule_path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Apply override based on comparator
        rule_name = rule_path[-1]

        if comparator == RuleComparator.EQUALS:
            current[rule_name] = value_data
        elif comparator == RuleComparator.GREATER_THAN:
            if isinstance(current.get(rule_name), (int, float)):
                current[rule_name] = max(current[rule_name], value_data)
        elif comparator == RuleComparator.LESS_THAN:
            if isinstance(current.get(rule_name), (int, float)):
                current[rule_name] = min(current.get(rule_name, float('inf')), value_data)
        # Add more comparator logic as needed

        # Apply severity override if provided
        if override.override_severity and isinstance(current.get(rule_name), dict):
            current[rule_name]["severity"] = override.override_severity

        return rules

    def _evaluate_condition(self, condition_expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition expression against context"""

        # Simple condition evaluation - in production use a proper expression evaluator
        try:
            # Replace context variables in expression
            for key, value in context.items():
                condition_expr = condition_expr.replace(f"${key}", str(value))

            # Evaluate simple expressions
            if ">" in condition_expr:
                left, right = condition_expr.split(">", 1)
                return float(left.strip()) > float(right.strip())
            elif "<" in condition_expr:
                left, right = condition_expr.split("<", 1)
                return float(left.strip()) < float(right.strip())
            elif "==" in condition_expr:
                left, right = condition_expr.split("==", 1)
                return left.strip().strip('"') == right.strip().strip('"')

            return True

        except Exception:
            logger.warning(f"Failed to evaluate condition: {condition_expr}")
            return False

    async def _execute_workflow_logic(
        self,
        workflow: BankWorkflow,
        effective_rules: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the actual workflow logic"""

        # Simulate workflow execution
        await asyncio.sleep(0.1)

        result = {
            "workflow_id": str(workflow.id),
            "rules_applied": len(effective_rules),
            "execution_time_ms": 100,
            "status": "success"
        }

        return result

    def _validate_condition_expr(self, condition_expr: str) -> bool:
        """Validate condition expression syntax"""
        # Basic validation - in production use proper parser
        return len(condition_expr.strip()) > 0

    def _is_valid_rule_key(self, rule_key: str) -> bool:
        """Validate rule key format"""
        return bool(rule_key and "." in rule_key and len(rule_key.split(".")) >= 2)

    async def _validate_workflow_config(self, workflow_type: str, config: Dict[str, Any]):
        """Validate workflow configuration"""
        # Add validation logic based on workflow type
        pass

    async def _validate_policy_config(self, policy_config: Dict[str, Any]) -> List[str]:
        """Validate policy configuration and return errors"""
        errors = []
        # Add validation logic
        return errors

    async def _create_initial_policy_version(
        self,
        db: Session,
        workflow_id: UUID,
        created_by: UUID
    ):
        """Create initial policy version for new workflow"""

        policy_version = PolicyVersion(
            workflow_id=workflow_id,
            version="1.0",
            name="Initial Version",
            description="Initial policy version",
            policy_config={},
            config_hash=hashlib.sha256(b"{}").hexdigest(),
            is_active=True,
            is_default=True,
            created_by=created_by
        )

        db.add(policy_version)

    def _invalidate_cache(self, bank_id: str):
        """Invalidate cached rules for a bank"""
        keys_to_remove = [k for k in self.effective_rules_cache.keys() if k.startswith(f"{bank_id}:")]
        for key in keys_to_remove:
            del self.effective_rules_cache[key]


# Global service instance
workflow_service = WorkflowService()