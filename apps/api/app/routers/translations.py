"""
Translation management API endpoints for multilingual support.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from app.models import User, UserRole
from ..core.security import get_current_user
from ..core.rbac import require_roles, RoleType
from ..services.translation import translation_service
from ..utils.i18n import get_supported_languages, clear_translation_cache


router = APIRouter(prefix="/translations", tags=["translations"])


class TranslationGenerateRequest(BaseModel):
    target_language: str
    force_regenerate: bool = False


class TranslationVerifyRequest(BaseModel):
    language: str
    key: str
    verified_value: str


class TranslationGenerateResponse(BaseModel):
    status: str
    generated_count: int
    target_language: str
    message: Optional[str] = None


class PendingTranslationsResponse(BaseModel):
    language: str
    pending: Dict[str, Any]
    count: int


class SupportedLanguagesResponse(BaseModel):
    languages: List[str]
    total_count: int


@router.get("/supported", response_model=SupportedLanguagesResponse)
async def get_supported_languages(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported languages."""
    languages = get_supported_languages()
    return SupportedLanguagesResponse(
        languages=languages,
        total_count=len(languages)
    )


@router.post("/generate", response_model=TranslationGenerateResponse)
async def generate_translations(
    request: TranslationGenerateRequest,
    current_user: User = Depends(require_roles([RoleType.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Generate AI-assisted translations for a target language.
    Requires admin role.
    """
    try:
        result = await translation_service.generate_missing_translations(
            target_language=request.target_language,
            db=db,
            user=current_user
        )

        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return TranslationGenerateResponse(
            status=result["status"],
            generated_count=result["generated_count"],
            target_language=request.target_language,
            message=f"Generated {result['generated_count']} translations for {request.target_language}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate translations: {str(e)}"
        )


@router.get("/pending", response_model=PendingTranslationsResponse)
async def get_pending_translations(
    language: str = Query(..., description="Target language code"),
    current_user: User = Depends(require_roles([RoleType.ADMIN]))
):
    """
    Get pending translations that require human verification.
    Requires admin role.
    """
    try:
        result = translation_service.get_pending_translations(language)
        return PendingTranslationsResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending translations: {str(e)}"
        )


@router.post("/verify")
async def verify_translation(
    request: TranslationVerifyRequest,
    current_user: User = Depends(require_roles([RoleType.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Verify and approve an AI-generated translation.
    Requires admin role.
    """
    try:
        result = await translation_service.verify_translation(
            language=request.language,
            key=request.key,
            verified_value=request.verified_value,
            db=db,
            user=current_user
        )

        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "message": f"Translation verified for {request.language}.{request.key}",
            "verified_value": request.verified_value
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify translation: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_translations_cache(
    current_user: User = Depends(require_roles([RoleType.ADMIN]))
):
    """
    Clear translation cache to force reload.
    Requires admin role.
    """
    try:
        clear_translation_cache()
        return {"message": "Translation cache cleared successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/status")
async def get_translation_status(
    current_user: User = Depends(require_roles([RoleType.ADMIN]))
):
    """
    Get overall translation status and statistics.
    Requires admin role.
    """
    try:
        supported_languages = get_supported_languages()
        status_data = {
            "supported_languages": supported_languages,
            "total_languages": len(supported_languages),
            "pending_counts": {}
        }

        # Get pending counts for each language
        for lang in supported_languages:
            if lang != "en":  # Skip English as it's the source
                pending = translation_service.get_pending_translations(lang)
                status_data["pending_counts"][lang] = pending["count"]

        return status_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get translation status: {str(e)}"
        )