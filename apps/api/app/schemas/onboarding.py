"""Schemas supporting Supabase-driven onboarding flows."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..models.company import BUSINESS_ACTIVITY_VALUES, BUSINESS_TIER_VALUES


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


class OnboardingCompletePayload(BaseModel):
    """Payload for the 3-question onboarding wizard (Q1 activities × Q2 country × Q3 tier).

    Lands on POST /api/onboarding/complete and drives Company.business_activities,
    Company.country, Company.tier. Activities is multi-select; the first element is
    treated as the user's "primary" for legacy User.role sync.
    """

    activities: List[str] = Field(..., min_length=1, description="1+ business activities")
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    tier: str = Field(..., description="Pricing tier: solo | sme | enterprise")
    company_name: Optional[str] = Field(
        None, description="Optional override. Falls back to existing Company.name."
    )

    @field_validator("activities")
    @classmethod
    def _validate_activities(cls, value: List[str]) -> List[str]:
        allowed = set(BUSINESS_ACTIVITY_VALUES)
        normalized = [v.strip().lower() for v in value]
        bad = [v for v in normalized if v not in allowed]
        if bad:
            raise ValueError(f"Invalid activities: {bad}. Allowed: {sorted(allowed)}")
        # Dedupe while preserving first-seen order (first = primary).
        seen: set[str] = set()
        deduped: List[str] = []
        for v in normalized:
            if v not in seen:
                seen.add(v)
                deduped.append(v)
        return deduped

    @field_validator("country")
    @classmethod
    def _validate_country(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 2 or not code.isalpha():
            raise ValueError(f"country must be ISO 3166-1 alpha-2, got {value!r}")
        return code

    @field_validator("tier")
    @classmethod
    def _validate_tier(cls, value: str) -> str:
        allowed = set(BUSINESS_TIER_VALUES)
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"Invalid tier {value!r}. Allowed: {sorted(allowed)}")
        return normalized

