"""
CRUD operations for LC versions.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from ..models.lc_versions import LCVersion, LCVersionStatus
from .. import models
from ..schemas.lc_versions import (
    LCVersionCreate, LCVersionUpdate, LCVersionComparison,
    VersionChanges, ComparisonSummary, DiscrepancyChange,
    AmendedLCInfo, LCExistsResponse
)


class LCVersionCRUD:
    """CRUD operations for LC versions."""

    @staticmethod
    def _apply_owner_scope(base_query, user_id=None, company_id=None):
        """Restrict an LCVersion query to rows the caller is allowed to see.

        LCVersion has no company_id column; ownership is derived from the
        associated ValidationSession (its company_id / user_id) plus the
        version's own uploaded_by. When neither user_id nor company_id is
        supplied (internal callers), the query is returned unscoped.
        """
        if user_id is None and company_id is None:
            return base_query
        scoped = base_query.join(
            models.ValidationSession,
            LCVersion.validation_session_id == models.ValidationSession.id,
        )
        conditions = []
        if company_id is not None:
            conditions.append(models.ValidationSession.company_id == company_id)
        if user_id is not None:
            conditions.append(LCVersion.uploaded_by == user_id)
            conditions.append(models.ValidationSession.user_id == user_id)
        return scoped.filter(or_(*conditions))

    @staticmethod
    def create_new_version(
        db: Session,
        lc_number: str,
        user_id: UUID,
        validation_session_id: UUID,
        files: Optional[List[Dict[str, Any]]] = None
    ) -> LCVersion:
        """
        Create a new LC version automatically incrementing the version number.

        Args:
            db: Database session
            lc_number: LC number
            user_id: User creating the version
            validation_session_id: Associated validation session
            files: File metadata list

        Returns:
            Created LCVersion instance
        """
        # Get the next version number
        max_version = db.query(func.max(LCVersion.version))\
            .filter(LCVersion.lc_number == lc_number)\
            .scalar() or 0

        next_version = max_version + 1

        # Prepare file metadata
        file_metadata = {
            "files": files or [],
            "total_files": len(files) if files else 0,
            "total_size": sum(f.get("size", 0) for f in files) if files else 0,
            "uploaded_at": datetime.utcnow().isoformat()
        }

        # Create new version
        version = LCVersion(
            lc_number=lc_number,
            version=next_version,
            validation_session_id=validation_session_id,
            uploaded_by=user_id,
            status=LCVersionStatus.DRAFT,
            file_metadata=file_metadata
        )

        db.add(version)
        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def get_versions(db: Session, lc_number: str, user_id: UUID = None, company_id: UUID = None) -> List[LCVersion]:
        """
        Get all versions for an LC number, ordered by version number.

        Args:
            db: Database session
            lc_number: LC number to get versions for
            user_id / company_id: caller identity for ownership scoping

        Returns:
            List of LCVersion instances
        """
        query = db.query(LCVersion).filter(LCVersion.lc_number == lc_number)
        query = LCVersionCRUD._apply_owner_scope(query, user_id=user_id, company_id=company_id)
        return query.order_by(LCVersion.version).all()

    @staticmethod
    def get_version_by_id(db: Session, version_id: UUID, user_id: UUID = None, company_id: UUID = None) -> Optional[LCVersion]:
        """
        Get a specific version by ID (scoped to the caller when identity given).

        Args:
            db: Database session
            version_id: Version ID
            user_id / company_id: caller identity for ownership scoping

        Returns:
            LCVersion instance or None
        """
        return LCVersionCRUD._apply_owner_scope(
            db.query(LCVersion).filter(LCVersion.id == version_id),
            user_id=user_id, company_id=company_id
        ).first()

    @staticmethod
    def get_version_by_session(db: Session, session_id: UUID) -> Optional[LCVersion]:
        """
        Get version by validation session ID.

        Args:
            db: Database session
            session_id: Validation session ID

        Returns:
            LCVersion instance or None
        """
        return db.query(LCVersion)\
            .filter(LCVersion.validation_session_id == session_id)\
            .first()

    @staticmethod
    def update_version(
        db: Session,
        version_id: UUID,
        update_data: LCVersionUpdate,
        user_id: UUID = None,
        company_id: UUID = None
    ) -> Optional[LCVersion]:
        """
        Update a version's status or metadata.

        Args:
            db: Database session
            version_id: Version ID to update
            update_data: Update data
            user_id / company_id: caller identity for ownership scoping

        Returns:
            Updated LCVersion instance or None (also None when the version
            exists but is not owned by the caller — callers surface this as 404)
        """
        version = LCVersionCRUD._apply_owner_scope(
            db.query(LCVersion).filter(LCVersion.id == version_id),
            user_id=user_id, company_id=company_id
        ).first()

        if not version:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(version, field, value)

        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def check_lc_exists(db: Session, lc_number: str) -> LCExistsResponse:
        """
        Check if an LC exists and return version info.

        Args:
            db: Database session
            lc_number: LC number to check

        Returns:
            LCExistsResponse with existence info
        """
        versions = db.query(LCVersion)\
            .filter(LCVersion.lc_number == lc_number)\
            .order_by(desc(LCVersion.version))\
            .all()

        if not versions:
            return LCExistsResponse(
                exists=False,
                next_version="V1",
                current_versions=0
            )

        latest_version = versions[0]
        return LCExistsResponse(
            exists=True,
            next_version=f"V{latest_version.version + 1}",
            current_versions=len(versions),
            latest_version_id=latest_version.id
        )

    @staticmethod
    def get_all_amended_lcs(db: Session, user_id: UUID = None, company_id: UUID = None) -> List[AmendedLCInfo]:
        """
        Get all LCs that have multiple versions (amendments), scoped to the
        caller's company/user so this never dumps every LC on the platform.

        Args:
            db: Database session
            user_id / company_id: caller identity for ownership scoping

        Returns:
            List of AmendedLCInfo
        """
        # Query for LCs with more than one version, restricted to the caller.
        base = db.query(
            LCVersion.lc_number,
            func.count(LCVersion.id).label('version_count'),
            func.max(LCVersion.version).label('max_version'),
            func.max(LCVersion.created_at).label('last_updated')
        )
        base = LCVersionCRUD._apply_owner_scope(base, user_id=user_id, company_id=company_id)
        subquery = base.group_by(LCVersion.lc_number)\
         .having(func.count(LCVersion.id) > 1)\
         .subquery()

        amended_lcs = db.query(subquery).all()

        result = []
        for lc in amended_lcs:
            result.append(AmendedLCInfo(
                lc_number=lc.lc_number,
                versions=lc.version_count,
                latest_version=f"V{lc.max_version}",
                last_updated=lc.last_updated
            ))

        return result

    @staticmethod
    def compare_versions(
        db: Session,
        lc_number: str,
        from_version: str,
        to_version: str,
        user_id: UUID = None,
        company_id: UUID = None
    ) -> Optional[LCVersionComparison]:
        """
        Compare two versions of an LC and return differences.

        Args:
            db: Database session
            lc_number: LC number
            from_version: Source version (e.g., "V1", "V2")
            to_version: Target version (e.g., "V2", "V3")
            user_id / company_id: caller identity for ownership scoping

        Returns:
            LCVersionComparison or None if versions not found
        """
        # Parse version numbers
        try:
            from_version_num = int(from_version.replace("V", ""))
            to_version_num = int(to_version.replace("V", ""))
        except ValueError:
            return None

        # Get the versions (scoped to the caller's company/user)
        from_lc_version = LCVersionCRUD._apply_owner_scope(
            db.query(LCVersion)
            .filter(LCVersion.lc_number == lc_number)
            .filter(LCVersion.version == from_version_num),
            user_id=user_id, company_id=company_id
        ).first()

        to_lc_version = LCVersionCRUD._apply_owner_scope(
            db.query(LCVersion)
            .filter(LCVersion.lc_number == lc_number)
            .filter(LCVersion.version == to_version_num),
            user_id=user_id, company_id=company_id
        ).first()

        if not from_lc_version or not to_lc_version:
            return None

        # Get discrepancies for both versions
        from_discrepancies = db.query(models.Discrepancy)\
            .filter(models.Discrepancy.validation_session_id == from_lc_version.validation_session_id)\
            .all()

        to_discrepancies = db.query(models.Discrepancy)\
            .filter(models.Discrepancy.validation_session_id == to_lc_version.validation_session_id)\
            .all()

        # Convert to comparable format
        from_disc_dict = {
            str(d.id): DiscrepancyChange(
                id=str(d.id),
                title=d.rule_name,
                description=d.description,
                severity=d.severity,
                rule_name=d.rule_name,
                field_name=d.field_name,
                expected_value=d.expected_value,
                actual_value=d.actual_value
            ) for d in from_discrepancies
        }

        to_disc_dict = {
            str(d.id): DiscrepancyChange(
                id=str(d.id),
                title=d.rule_name,
                description=d.description,
                severity=d.severity,
                rule_name=d.rule_name,
                field_name=d.field_name,
                expected_value=d.expected_value,
                actual_value=d.actual_value
            ) for d in to_discrepancies
        }

        # Calculate differences
        from_ids = set(from_disc_dict.keys())
        to_ids = set(to_disc_dict.keys())

        added_discrepancies = [to_disc_dict[id] for id in to_ids - from_ids]
        removed_discrepancies = [from_disc_dict[id] for id in from_ids - to_ids]

        # Check for modified discrepancies (same ID but different content)
        modified_discrepancies = []
        common_ids = from_ids & to_ids
        for disc_id in common_ids:
            from_disc = from_disc_dict[disc_id]
            to_disc = to_disc_dict[disc_id]

            if (from_disc.description != to_disc.description or
                from_disc.severity != to_disc.severity):
                modified_discrepancies.append(to_disc)

        # Calculate improvement score
        total_changes = len(added_discrepancies) + len(removed_discrepancies) + len(modified_discrepancies)
        if total_changes == 0:
            improvement_score = 0.0
        else:
            # More removed than added = improvement
            improvement_score = (len(removed_discrepancies) - len(added_discrepancies)) / max(total_changes, 1)
            # Clamp between -1 and 1
            improvement_score = max(-1.0, min(1.0, improvement_score))

        # Status change
        status_change = None
        if from_lc_version.status != to_lc_version.status:
            status_change = {
                "from": from_lc_version.status,
                "to": to_lc_version.status
            }

        return LCVersionComparison(
            lc_number=lc_number,
            from_version=from_version,
            to_version=to_version,
            changes=VersionChanges(
                added_discrepancies=added_discrepancies,
                removed_discrepancies=removed_discrepancies,
                modified_discrepancies=modified_discrepancies,
                status_change=status_change
            ),
            summary=ComparisonSummary(
                total_changes=total_changes,
                improvement_score=improvement_score
            )
        )