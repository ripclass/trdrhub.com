"""Schemas supporting Supabase-driven onboarding flows."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CompanyPayload(BaseModel):
    """Incoming company metadata from onboarding wizard."""

    name: str
    type: Optional[str] = Field(None, description="Primary business type or segment")
    size: Optional[str] = Field(None, description="Company size tier (sme, medium, large)")
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    regulator_id: Optional[str] = None
    country: Optional[str] = None


class OnboardingProgressPayload(BaseModel):
    """Payload for saving onboarding wizard progress."""

    role: Optional[str] = Field(None, description="Selected user role")
    business_types: Optional[List[str]] = Field(None, description="Selected business categories")
    onboarding_step: Optional[str] = Field(None, description="Current step identifier")
    company: Optional[CompanyPayload] = Field(None, description="Company metadata")
    submit_for_review: Optional[bool] = Field(False, description="Submit bank onboarding for review")
    complete: Optional[bool] = Field(False, description="Mark onboarding as complete (SME path)")
    approved: Optional[bool] = Field(False, description="Administrative approval toggle")


class OnboardingRequirements(BaseModel):
    """Describes outstanding requirements for a user."""

    basic: List[str] = Field(default_factory=list)
    legal: List[str] = Field(default_factory=list)
    docs: List[str] = Field(default_factory=list)


class OnboardingStatus(BaseModel):
    """Status payload returned to the frontend wizard."""

    user_id: str
    role: Optional[str]
    company_id: Optional[str] = None
    completed: bool = False
    step: Optional[str] = None
    status: Optional[str] = Field(None, description="Current approval status")
    kyc_status: Optional[str] = Field(None, description="KYC processing status")
    required: OnboardingRequirements = Field(default_factory=OnboardingRequirements)
    details: Dict[str, Any] = Field(default_factory=dict)

