"""
Onboarding schemas for user onboarding wizard system.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class OnboardingStep(BaseModel):
    """Individual onboarding step information."""
    step_id: str = Field(..., description="Unique identifier for the step")
    title: str = Field(..., description="Step title")
    description: Optional[str] = Field(None, description="Step description")
    completed: bool = Field(default=False, description="Whether step is completed")
    skipped: bool = Field(default=False, description="Whether step was skipped")


class OnboardingProgress(BaseModel):
    """Onboarding progress tracking."""
    current_step: Optional[str] = Field(None, description="Current step identifier")
    completed_steps: List[str] = Field(default_factory=list, description="List of completed step IDs")
    skipped_steps: List[str] = Field(default_factory=list, description="List of skipped step IDs")
    tutorial_views: List[str] = Field(default_factory=list, description="List of viewed tutorial IDs")
    sample_data_views: List[str] = Field(default_factory=list, description="List of viewed sample data IDs")
    last_accessed: Optional[datetime] = Field(None, description="Last time onboarding was accessed")


class OnboardingStatus(BaseModel):
    """Onboarding status response."""
    needs_onboarding: bool = Field(..., description="Whether user needs onboarding")
    onboarding_completed: bool = Field(..., description="Whether onboarding is completed")
    current_progress: Optional[OnboardingProgress] = Field(None, description="Current progress data")
    role: str = Field(..., description="User role for content customization")


class OnboardingContent(BaseModel):
    """Role-specific onboarding content."""
    role: str = Field(..., description="User role")
    steps: List[OnboardingStep] = Field(..., description="List of onboarding steps for this role")
    welcome_message: str = Field(..., description="Welcome message for the role")
    introduction: str = Field(..., description="Role-specific introduction")
    key_features: List[str] = Field(..., description="Key features for this role")
    available_tutorials: List[Dict[str, Any]] = Field(default_factory=list, description="Available tutorials")
    sample_data_available: bool = Field(default=True, description="Whether sample data is available for this role")


class OnboardingProgressUpdate(BaseModel):
    """Request model for updating onboarding progress."""
    current_step: Optional[str] = Field(None, description="Current step identifier")
    completed_steps: Optional[List[str]] = Field(None, description="Step IDs to mark as completed")
    skipped_steps: Optional[List[str]] = Field(None, description="Step IDs to mark as skipped")
    tutorial_viewed: Optional[str] = Field(None, description="Tutorial ID that was viewed")
    sample_data_viewed: Optional[str] = Field(None, description="Sample data ID that was viewed")


class OnboardingCompleteRequest(BaseModel):
    """Request model for completing onboarding."""
    completed: bool = Field(default=True, description="Mark onboarding as completed")

