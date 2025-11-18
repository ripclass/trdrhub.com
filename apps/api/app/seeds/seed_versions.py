"""
LC Version seeding utilities for automatic V1 creation.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from ..models import ValidationSession
from ..models.lc_versions import LCVersion, LCVersionStatus
from ..crud.lc_versions import LCVersionCRUD

logger = logging.getLogger(__name__)


class VersionSeeder:
    """Service for automatically creating LC versions during validation."""

    @staticmethod
    def extract_lc_number_from_session(
        db: Session,
        session: ValidationSession
    ) -> Optional[str]:
        """
        Extract LC number from validation session data.

        Args:
            db: Database session
            session: ValidationSession instance

        Returns:
            LC number if found, None otherwise
        """
        # Try to extract from validation results
        if session.validation_results:
            extracted_data = session.validation_results.get("extracted_data", {})

            # Look for LC number in common field names
            for field_name in ["lc_number", "letter_of_credit_number", "lc_no", "credit_number"]:
                lc_number = extracted_data.get(field_name)
                if lc_number:
                    return str(lc_number).strip()

        # Try to extract from extracted_data field
        if session.extracted_data:
            for field_name in ["lc_number", "letter_of_credit_number", "lc_no", "credit_number"]:
                lc_number = session.extracted_data.get(field_name)
                if lc_number:
                    return str(lc_number).strip()

        # Try to extract from documents' extracted fields
        for document in session.documents:
            if document.extracted_fields:
                for field_name in ["lc_number", "letter_of_credit_number", "lc_no", "credit_number"]:
                    lc_number = document.extracted_fields.get(field_name)
                    if lc_number:
                        return str(lc_number).strip()

        logger.warning(f"Could not extract LC number from session {session.id}")
        return None

    @staticmethod
    def extract_file_metadata_from_session(session: ValidationSession) -> List[Dict[str, Any]]:
        """
        Extract file metadata from validation session documents.

        Args:
            session: ValidationSession instance

        Returns:
            List of file metadata dictionaries
        """
        files = []
        for document in session.documents:
            file_info = {
                "name": document.original_filename,
                "size": document.file_size,
                "type": document.content_type,
                "document_type": document.document_type,
                "s3_key": document.s3_key,
                "document_id": str(document.id)
            }
            files.append(file_info)

        return files

    @staticmethod
    def seed_version_on_validation_complete(
        db: Session,
        session: ValidationSession
    ) -> Optional[LCVersion]:
        """
        Automatically create V1 when validation is completed for the first time.

        This should be called when a validation session status changes to 'COMPLETED'.

        Args:
            db: Database session
            session: Completed ValidationSession

        Returns:
            Created LCVersion or None if not created
        """
        try:
            # Check if version already exists for this session
            existing_version = LCVersionCRUD.get_version_by_session(db, session.id)
            if existing_version:
                logger.info(f"Version already exists for session {session.id}")
                return existing_version

            # Extract LC number
            lc_number = VersionSeeder.extract_lc_number_from_session(db, session)
            if not lc_number:
                logger.warning(f"Could not extract LC number from session {session.id}, skipping version creation")
                return None

            # Extract file metadata
            files = VersionSeeder.extract_file_metadata_from_session(session)

            # Create V1 if this is the first version for this LC
            existing_versions = LCVersionCRUD.get_versions(db, lc_number)
            if not existing_versions:
                logger.info(f"Creating V1 for LC {lc_number} from session {session.id}")

                version = LCVersionCRUD.create_new_version(
                    db=db,
                    lc_number=lc_number,
                    user_id=session.user_id,
                    validation_session_id=session.id,
                    files=files
                )

                # Update status to validated
                from ..schemas.lc_versions import LCVersionUpdate
                update_data = LCVersionUpdate(status=LCVersionStatus.VALIDATED)
                version = LCVersionCRUD.update_version(db, version.id, update_data)

                logger.info(f"Successfully created V1 (id: {version.id}) for LC {lc_number}")
                return version
            else:
                logger.info(f"LC {lc_number} already has versions, not creating V1")
                return None

        except Exception as e:
            logger.error(f"Error seeding version for session {session.id}: {str(e)}")
            return None

    @staticmethod
    def seed_version_manually(
        db: Session,
        lc_number: str,
        user_id: UUID,
        session_id: UUID,
        files: Optional[List[Dict[str, Any]]] = None
    ) -> LCVersion:
        """
        Manually create a new version for an LC.

        Used when uploading amendments or creating versions outside the normal flow.

        Args:
            db: Database session
            lc_number: LC number
            user_id: User creating the version
            session_id: Associated validation session
            files: Optional file metadata

        Returns:
            Created LCVersion instance
        """
        logger.info(f"Manually creating version for LC {lc_number}")

        version = LCVersionCRUD.create_new_version(
            db=db,
            lc_number=lc_number,
            user_id=user_id,
            validation_session_id=session_id,
            files=files or []
        )

        logger.info(f"Successfully created V{version.version} (id: {version.id}) for LC {lc_number}")
        return version


def hook_into_validation_pipeline(db: Session, session: ValidationSession) -> None:
    """
    Hook function to integrate with the validation pipeline.

    This should be called whenever a validation session status changes to COMPLETED.

    Args:
        db: Database session
        session: ValidationSession that just completed
    """
    try:
        seeder = VersionSeeder()
        seeder.seed_version_on_validation_complete(db, session)
    except Exception as e:
        logger.error(f"Failed to hook version seeding into validation pipeline: {str(e)}")
        # Don't raise the exception to avoid breaking the validation pipeline