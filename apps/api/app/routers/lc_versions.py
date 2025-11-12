"""
LC Versions API endpoints for version control.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..auth import get_current_user
from ..crud.lc_versions import LCVersionCRUD
from ..schemas.lc_versions import (
    LCVersionCreate, LCVersionRead, LCVersionUpdate, LCVersionsList,
    LCVersionComparison, AmendedLCInfo, LCExistsResponse
)

router = APIRouter(prefix="/api/lc", tags=["lc-versions"])


@router.post("/{lc_number}/versions", response_model=LCVersionRead, status_code=status.HTTP_201_CREATED)
async def create_lc_version(
    lc_number: str,
    version_data: LCVersionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new version for an LC.

    Creates a new version entry linking to a validation session.
    Version numbers are auto-incremented per LC.
    """
    try:
        version = LCVersionCRUD.create_new_version(
            db=db,
            lc_number=lc_number,
            user_id=current_user.id,
            validation_session_id=version_data.validation_session_id,
            files=version_data.file_metadata.get("files", []) if version_data.file_metadata else None
        )
        return version
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create LC version: {str(e)}"
        )


@router.get("/{lc_number}/versions", response_model=LCVersionsList)
async def get_lc_versions(
    lc_number: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all versions for a specific LC number.

    Returns versions ordered by version number with metadata.
    """
    versions = LCVersionCRUD.get_versions(db=db, lc_number=lc_number)

    if not versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No versions found for LC number: {lc_number}"
        )

    return LCVersionsList(
        lc_number=lc_number,
        versions=versions,
        total_versions=len(versions),
        latest_version=max(v.version for v in versions)
    )


@router.get("/{lc_number}/versions/compare", response_model=LCVersionComparison)
async def compare_lc_versions(
    lc_number: str,
    from_version: str = Query(..., alias="from", description="Source version (e.g., V1)"),
    to_version: str = Query(..., alias="to", description="Target version (e.g., V2)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare two versions of an LC.

    Returns added, removed, and modified discrepancies between versions,
    along with an improvement score.
    """
    comparison = LCVersionCRUD.compare_versions(
        db=db,
        lc_number=lc_number,
        from_version=from_version,
        to_version=to_version
    )

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not compare versions {from_version} to {to_version} for LC {lc_number}"
        )

    return comparison


@router.get("/{lc_number}/check", response_model=LCExistsResponse)
async def check_lc_exists(
    lc_number: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if an LC exists and get version information.

    Used by frontend to show amendment warnings and determine next version number.
    """
    return LCVersionCRUD.check_lc_exists(db=db, lc_number=lc_number)


@router.get("/amended", response_model=List[AmendedLCInfo])
async def get_amended_lcs(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all LCs that have multiple versions (amendments).

    Returns LCs with version counts and latest version info.
    Used by the amendments tab in the dashboard.
    """
    return LCVersionCRUD.get_all_amended_lcs(db=db)


@router.get("/versions/{version_id}", response_model=LCVersionRead)
async def get_version_by_id(
    version_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific version by its ID.

    Useful for direct version access and navigation.
    """
    version = LCVersionCRUD.get_version_by_id(db=db, version_id=version_id)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}"
        )

    return version


@router.put("/versions/{version_id}", response_model=LCVersionRead)
async def update_version(
    version_id: UUID,
    update_data: LCVersionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a version's status or metadata.

    Allows status changes (draft -> validated -> packaged) and metadata updates.
    """
    version = LCVersionCRUD.update_version(
        db=db,
        version_id=version_id,
        update_data=update_data
    )

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version not found: {version_id}"
        )

    return version


@router.get("/session/{session_id}/version", response_model=LCVersionRead)
async def get_version_by_session(
    session_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the LC version associated with a validation session.

    Used to link validation results to version history.
    """
    version = LCVersionCRUD.get_version_by_session(db=db, session_id=session_id)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No version found for session: {session_id}"
        )

    return version