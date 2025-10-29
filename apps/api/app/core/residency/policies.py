"""
Data Residency Policies

Implements tenant-aware data residency controls and policy enforcement.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...database import get_db
from ...models.compliance import DataResidencyPolicy, ResidencyViolation, ComplianceAuditEvent
from ...core.config import settings

logger = logging.getLogger(__name__)

class ResidencyRegion(str, Enum):
    """Supported data residency regions"""
    BD = "BD"  # Bangladesh
    EU = "EU"  # European Union
    SG = "SG"  # Singapore
    GLOBAL = "GLOBAL"  # No residency restrictions

@dataclass
class PolicyResult:
    """Result of policy evaluation"""
    allowed: bool
    target_region: str
    target_bucket: str
    reason: str
    policy: ResidencyRegion

@dataclass
class ResidencyMapping:
    """Mapping of regions to storage buckets"""
    region: str
    bucket_pattern: str
    description: str

class ResidencyPolicyEngine:
    """Core engine for data residency policy evaluation"""

    def __init__(self, db: Session = None):
        self.db = db or next(get_db())

        # Define region to bucket mappings
        self.region_mappings = {
            ResidencyRegion.BD: ResidencyMapping(
                region="BD",
                bucket_pattern=f"{settings.PROJECT_NAME}-docs-bd-{settings.ENVIRONMENT}",
                description="Bangladesh - Local financial regulatory compliance"
            ),
            ResidencyRegion.EU: ResidencyMapping(
                region="EU",
                bucket_pattern=f"{settings.PROJECT_NAME}-docs-eu-{settings.ENVIRONMENT}",
                description="European Union - GDPR compliance"
            ),
            ResidencyRegion.SG: ResidencyMapping(
                region="SG",
                bucket_pattern=f"{settings.PROJECT_NAME}-docs-sg-{settings.ENVIRONMENT}",
                description="Singapore - ASEAN regulatory compliance"
            ),
            ResidencyRegion.GLOBAL: ResidencyMapping(
                region="GLOBAL",
                bucket_pattern=f"{settings.PROJECT_NAME}-docs-bd-{settings.ENVIRONMENT}",  # Default to BD
                description="Global - No specific residency requirements"
            )
        }

    def get_tenant_policy(self, tenant_id: str) -> Optional[DataResidencyPolicy]:
        """Get the active residency policy for a tenant"""
        return self.db.query(DataResidencyPolicy).filter(
            and_(
                DataResidencyPolicy.tenant_id == tenant_id,
                DataResidencyPolicy.effective_from <= datetime.utcnow()
            )
        ).order_by(DataResidencyPolicy.effective_from.desc()).first()

    def set_tenant_policy(
        self,
        tenant_id: str,
        policy: ResidencyRegion,
        configured_by: str,
        reason: str = None,
        effective_from: datetime = None
    ) -> DataResidencyPolicy:
        """Set or update residency policy for a tenant"""

        effective_from = effective_from or datetime.utcnow()

        try:
            new_policy = DataResidencyPolicy(
                tenant_id=tenant_id,
                policy=policy,
                effective_from=effective_from,
                configured_by=configured_by,
                reason=reason
            )

            self.db.add(new_policy)
            self.db.commit()

            # Log policy change
            self._log_policy_change(
                tenant_id=tenant_id,
                policy=policy,
                configured_by=configured_by,
                reason=reason,
                action="set_policy"
            )

            logger.info(f"Set residency policy for tenant {tenant_id} to {policy.value}")
            return new_policy

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set residency policy: {e}")
            raise

    def evaluate_upload_request(
        self,
        tenant_id: str,
        object_key: str,
        requested_region: str = None,
        actor: str = None
    ) -> PolicyResult:
        """Evaluate if an upload request complies with residency policy"""

        # Get tenant's residency policy
        policy_record = self.get_tenant_policy(tenant_id)

        if not policy_record:
            # No policy set - default to GLOBAL
            policy = ResidencyRegion.GLOBAL
            logger.warning(f"No residency policy found for tenant {tenant_id}, defaulting to GLOBAL")
        else:
            policy = ResidencyRegion(policy_record.policy)

        # Determine target region and bucket
        mapping = self.region_mappings[policy]
        target_region = mapping.region
        target_bucket = mapping.bucket_pattern

        # If a specific region was requested, validate it
        if requested_region:
            if policy == ResidencyRegion.GLOBAL:
                # GLOBAL policy allows any region, but use the requested one
                if requested_region.upper() in [r.value for r in ResidencyRegion if r != ResidencyRegion.GLOBAL]:
                    target_region = requested_region.upper()
                    target_bucket = self.region_mappings[ResidencyRegion(requested_region.upper())].bucket_pattern
            else:
                # Check if requested region matches policy
                if requested_region.upper() != policy.value:
                    # Violation - log it
                    self._log_violation(
                        tenant_id=tenant_id,
                        object_key=object_key,
                        attempted_region=requested_region.upper(),
                        policy=policy,
                        actor=actor or "unknown"
                    )

                    return PolicyResult(
                        allowed=False,
                        target_region=target_region,
                        target_bucket=target_bucket,
                        reason=f"Requested region {requested_region.upper()} violates policy {policy.value}",
                        policy=policy
                    )

        return PolicyResult(
            allowed=True,
            target_region=target_region,
            target_bucket=target_bucket,
            reason=f"Upload allowed to {target_region} per policy {policy.value}",
            policy=policy
        )

    def validate_object_access(
        self,
        tenant_id: str,
        object_key: str,
        object_region: str,
        action: str = "read",
        actor: str = None
    ) -> bool:
        """Validate if accessing an object complies with current residency policy"""

        policy_record = self.get_tenant_policy(tenant_id)

        if not policy_record:
            # No policy - allow access but log it
            logger.warning(f"No residency policy for tenant {tenant_id} accessing {object_key}")
            return True

        policy = ResidencyRegion(policy_record.policy)

        # GLOBAL policy allows access to any region
        if policy == ResidencyRegion.GLOBAL:
            return True

        # Check if object region matches current policy
        if object_region.upper() != policy.value:
            # This might indicate data that was stored before policy change
            # or during a migration - log but potentially allow based on settings
            self._log_policy_mismatch(
                tenant_id=tenant_id,
                object_key=object_key,
                object_region=object_region,
                current_policy=policy,
                action=action,
                actor=actor
            )

            # For now, allow access but log the mismatch
            # In stricter implementations, this could be denied
            return True

        return True

    def get_allowed_regions(self, tenant_id: str) -> List[str]:
        """Get list of regions where tenant data can be stored"""

        policy_record = self.get_tenant_policy(tenant_id)

        if not policy_record:
            return [ResidencyRegion.GLOBAL.value]

        policy = ResidencyRegion(policy_record.policy)

        if policy == ResidencyRegion.GLOBAL:
            return [r.value for r in ResidencyRegion if r != ResidencyRegion.GLOBAL]
        else:
            return [policy.value]

    def get_bucket_for_region(self, region: str) -> str:
        """Get the storage bucket for a specific region"""

        try:
            region_enum = ResidencyRegion(region.upper())
            return self.region_mappings[region_enum].bucket_pattern
        except ValueError:
            # Unknown region - default to BD
            logger.warning(f"Unknown region {region}, defaulting to BD")
            return self.region_mappings[ResidencyRegion.BD].bucket_pattern

    def get_policy_violations(
        self,
        tenant_id: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ResidencyViolation], int]:
        """Get residency policy violations"""

        query = self.db.query(ResidencyViolation)

        if tenant_id:
            query = query.filter(ResidencyViolation.tenant_id == tenant_id)

        total = query.count()
        violations = query.order_by(
            ResidencyViolation.created_at.desc()
        ).offset(offset).limit(limit).all()

        return violations, total

    def get_tenant_compliance_status(self, tenant_id: str) -> Dict[str, any]:
        """Get comprehensive compliance status for a tenant"""

        policy_record = self.get_tenant_policy(tenant_id)
        violations, violation_count = self.get_policy_violations(tenant_id, limit=1)

        # Get object distribution by region (would need to query ObjectMetadata)
        from ...models.compliance import ObjectMetadata

        object_distribution = self.db.query(
            ObjectMetadata.region,
            self.db.func.count(ObjectMetadata.id).label('count'),
            self.db.func.sum(ObjectMetadata.size_bytes).label('total_size')
        ).filter(
            ObjectMetadata.tenant_id == tenant_id
        ).group_by(ObjectMetadata.region).all()

        return {
            'tenant_id': tenant_id,
            'current_policy': policy_record.policy if policy_record else None,
            'policy_effective_from': policy_record.effective_from if policy_record else None,
            'total_violations': violation_count,
            'last_violation': violations[0].created_at if violations else None,
            'object_distribution': [
                {
                    'region': dist.region,
                    'object_count': dist.count,
                    'total_size_bytes': dist.total_size or 0
                }
                for dist in object_distribution
            ],
            'allowed_regions': self.get_allowed_regions(tenant_id),
            'compliance_status': 'compliant' if violation_count == 0 else 'violations'
        }

    def _log_violation(
        self,
        tenant_id: str,
        object_key: str,
        attempted_region: str,
        policy: ResidencyRegion,
        actor: str
    ):
        """Log a residency policy violation"""

        try:
            violation = ResidencyViolation(
                tenant_id=tenant_id,
                object_key=object_key,
                attempted_region=attempted_region,
                policy=policy,
                actor=actor
            )

            self.db.add(violation)
            self.db.commit()

            # Also log to compliance audit trail
            audit_event = ComplianceAuditEvent(
                event_type='residency_violation',
                actor_id=actor,
                actor_type='user',
                tenant_id=tenant_id,
                resource_type='object',
                resource_id=object_key,
                action='upload_attempt',
                outcome='denied',
                reason=f"Attempted upload to {attempted_region} violates policy {policy.value}",
                metadata={
                    'attempted_region': attempted_region,
                    'required_region': policy.value,
                    'policy': policy.value
                }
            )

            self.db.add(audit_event)
            self.db.commit()

            logger.warning(
                f"Residency violation: tenant {tenant_id} attempted upload to {attempted_region}, "
                f"policy requires {policy.value}"
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log residency violation: {e}")

    def _log_policy_change(
        self,
        tenant_id: str,
        policy: ResidencyRegion,
        configured_by: str,
        reason: str,
        action: str
    ):
        """Log residency policy changes"""

        try:
            audit_event = ComplianceAuditEvent(
                event_type='residency_policy_change',
                actor_id=configured_by,
                actor_type='admin',
                tenant_id=tenant_id,
                resource_type='policy',
                resource_id=f"residency_policy_{tenant_id}",
                action=action,
                outcome='success',
                reason=reason,
                metadata={
                    'new_policy': policy.value,
                    'reason': reason
                }
            )

            self.db.add(audit_event)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log policy change: {e}")

    def _log_policy_mismatch(
        self,
        tenant_id: str,
        object_key: str,
        object_region: str,
        current_policy: ResidencyRegion,
        action: str,
        actor: str
    ):
        """Log when object region doesn't match current policy"""

        try:
            audit_event = ComplianceAuditEvent(
                event_type='residency_policy_mismatch',
                actor_id=actor,
                actor_type='user',
                tenant_id=tenant_id,
                resource_type='object',
                resource_id=object_key,
                action=f"{action}_object",
                outcome='success',  # Access allowed but flagged
                reason=f"Object in {object_region} accessed with policy {current_policy.value}",
                metadata={
                    'object_region': object_region,
                    'current_policy': current_policy.value,
                    'action': action
                }
            )

            self.db.add(audit_event)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log policy mismatch: {e}")

def get_residency_engine(db: Session = None) -> ResidencyPolicyEngine:
    """Factory function to get residency policy engine"""
    return ResidencyPolicyEngine(db or next(get_db()))