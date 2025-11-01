"""
Onboarding API endpoints.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from app.models import User
from ..schemas.onboarding import (
    OnboardingStatus,
    OnboardingProgress,
    OnboardingContent,
    OnboardingProgressUpdate,
    OnboardingCompleteRequest,
    OnboardingStep
)
from ..core.security import get_current_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _get_default_progress() -> Dict[str, Any]:
    """Get default onboarding progress structure."""
    return {
        "current_step": None,
        "completed_steps": [],
        "skipped_steps": [],
        "tutorial_views": [],
        "sample_data_views": [],
        "last_accessed": None
    }


def _parse_onboarding_data(user: User) -> OnboardingProgress:
    """Parse onboarding_data from user model."""
    if user.onboarding_data is None:
        return OnboardingProgress(**_get_default_progress())
    
    data = user.onboarding_data if isinstance(user.onboarding_data, dict) else {}
    last_accessed = None
    if data.get("last_accessed"):
        last_accessed_value = data["last_accessed"]
        if isinstance(last_accessed_value, str):
            try:
                last_accessed = datetime.fromisoformat(last_accessed_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                last_accessed = None
        elif isinstance(last_accessed_value, datetime):
            last_accessed = last_accessed_value
    
    return OnboardingProgress(
        current_step=data.get("current_step"),
        completed_steps=data.get("completed_steps", []),
        skipped_steps=data.get("skipped_steps", []),
        tutorial_views=data.get("tutorial_views", []),
        sample_data_views=data.get("sample_data_views", []),
        last_accessed=last_accessed
    )


def _get_role_onboarding_content(role: str) -> OnboardingContent:
    """Get role-specific onboarding content."""
    # Base steps that all roles see
    base_steps = [
        OnboardingStep(
            step_id="welcome",
            title="Welcome to LCopilot",
            description="Learn about the platform and how it can help you",
            completed=False,
            skipped=False
        ),
        OnboardingStep(
            step_id="role-introduction",
            title=f"Your Role: {role.title()}",
            description="Discover features tailored to your role",
            completed=False,
            skipped=False
        ),
        OnboardingStep(
            step_id="platform-overview",
            title="Platform Overview",
            description="Navigate the platform and understand key areas",
            completed=False,
            skipped=False
        ),
    ]
    
    # Role-specific additional steps
    role_steps = {
        "exporter": [
            OnboardingStep(
                step_id="exporter-upload",
                title="Upload LC Documents",
                description="Learn how to upload and validate your LC documents",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="exporter-validation",
                title="Review Discrepancies",
                description="Understand how to review and fix discrepancies",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="exporter-reports",
                title="Generate Reports",
                description="Create and download validation reports",
                completed=False,
                skipped=False
            ),
        ],
        "importer": [
            OnboardingStep(
                step_id="importer-review",
                title="Review Supplier Documents",
                description="Learn how to review supplier documents for compliance",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="importer-risk",
                title="Risk Assessment",
                description="Understand risk assessment and compliance checking",
                completed=False,
                skipped=False
            ),
        ],
        "bank_officer": [
            OnboardingStep(
                step_id="bank-monitoring",
                title="Compliance Monitoring",
                description="Monitor compliance across all tenants",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="bank-analytics",
                title="Analytics Dashboard",
                description="Access comprehensive analytics and reports",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="bank-audit",
                title="Audit Trail Access",
                description="Review audit trails and compliance data",
                completed=False,
                skipped=False
            ),
        ],
        "bank_admin": [
            OnboardingStep(
                step_id="bank-admin-monitoring",
                title="System-Wide Monitoring",
                description="Monitor all tenants and users",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="bank-admin-analytics",
                title="Advanced Analytics",
                description="Access advanced analytics and reporting",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="bank-admin-management",
                title="User Management",
                description="Manage users and roles",
                completed=False,
                skipped=False
            ),
        ],
        "system_admin": [
            OnboardingStep(
                step_id="admin-users",
                title="User Management",
                description="Manage all users and roles",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="admin-config",
                title="System Configuration",
                description="Configure system settings",
                completed=False,
                skipped=False
            ),
            OnboardingStep(
                step_id="admin-monitoring",
                title="System Monitoring",
                description="Monitor system health and performance",
                completed=False,
                skipped=False
            ),
        ],
    }
    
    # Combine base steps with role-specific steps
    all_steps = base_steps + role_steps.get(role, [])
    
    # Role-specific messages and features
    role_messages = {
        "exporter": {
            "welcome": "Welcome to LCopilot! Your AI-powered LC validation platform.",
            "introduction": "As an exporter, you can validate LC documents, review discrepancies, and generate reports to ensure bank-ready submissions.",
            "key_features": [
                "Upload and validate LC documents",
                "AI-powered discrepancy detection",
                "Generate validation reports",
                "Track validation history",
                "Export evidence packs"
            ],
            "tutorials": [
                {"id": "upload-lc", "title": "How to Upload LC Documents", "duration": "2 min"},
                {"id": "review-discrepancies", "title": "Reviewing Discrepancies", "duration": "3 min"},
                {"id": "generate-reports", "title": "Generating Reports", "duration": "2 min"}
            ]
        },
        "importer": {
            "welcome": "Welcome to LCopilot! Your supplier document validation platform.",
            "introduction": "As an importer, you can review supplier documents, assess compliance risks, and ensure LC requirements are met.",
            "key_features": [
                "Review supplier documents",
                "Risk assessment and compliance checking",
                "LC requirement validation",
                "Compliance tracking",
                "Document history"
            ],
            "tutorials": [
                {"id": "review-supplier-docs", "title": "Reviewing Supplier Documents", "duration": "3 min"},
                {"id": "risk-assessment", "title": "Risk Assessment", "duration": "4 min"}
            ]
        },
        "bank_officer": {
            "welcome": "Welcome to LCopilot! Your compliance monitoring platform.",
            "introduction": "As a bank officer, you can monitor compliance across all tenants, access analytics, and review audit trails.",
            "key_features": [
                "System-wide compliance monitoring",
                "Analytics and reporting",
                "Audit trail access",
                "Multi-tenant view",
                "Compliance dashboards"
            ],
            "tutorials": [
                {"id": "compliance-monitoring", "title": "Compliance Monitoring", "duration": "5 min"},
                {"id": "analytics-dashboard", "title": "Using Analytics Dashboard", "duration": "4 min"}
            ]
        },
        "bank_admin": {
            "welcome": "Welcome to LCopilot! Your administrative platform.",
            "introduction": "As a bank administrator, you have full access to system monitoring, user management, and advanced analytics.",
            "key_features": [
                "User and role management",
                "System-wide monitoring",
                "Advanced analytics",
                "Audit trail management",
                "Configuration management"
            ],
            "tutorials": [
                {"id": "user-management", "title": "User Management", "duration": "5 min"},
                {"id": "system-monitoring", "title": "System Monitoring", "duration": "4 min"}
            ]
        },
        "system_admin": {
            "welcome": "Welcome to LCopilot! Your system administration platform.",
            "introduction": "As a system administrator, you have full access to all system functions including user management, configuration, and monitoring.",
            "key_features": [
                "Complete user management",
                "System configuration",
                "Performance monitoring",
                "Security management",
                "System-wide analytics"
            ],
            "tutorials": [
                {"id": "admin-overview", "title": "Admin Overview", "duration": "6 min"},
                {"id": "system-config", "title": "System Configuration", "duration": "5 min"}
            ]
        },
    }
    
    role_info = role_messages.get(role, role_messages["exporter"])
    
    return OnboardingContent(
        role=role,
        steps=all_steps,
        welcome_message=role_info["welcome"],
        introduction=role_info["introduction"],
        key_features=role_info["key_features"],
        available_tutorials=role_info.get("tutorials", []),
        sample_data_available=True
    )


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get onboarding status for current user."""
    needs_onboarding = not current_user.onboarding_completed
    progress = _parse_onboarding_data(current_user)
    
    return OnboardingStatus(
        needs_onboarding=needs_onboarding,
        onboarding_completed=current_user.onboarding_completed,
        current_progress=progress,
        role=current_user.role
    )


@router.get("/content/{role}", response_model=OnboardingContent)
async def get_onboarding_content(
    role: str,
    current_user: User = Depends(get_current_user)
):
    """Get role-specific onboarding content."""
    # Validate role access
    if role != current_user.role and not current_user.is_system_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access onboarding content for other roles"
        )
    
    return _get_role_onboarding_content(role)


@router.put("/progress", response_model=OnboardingProgress)
async def update_onboarding_progress(
    progress_update: OnboardingProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update onboarding progress for current user."""
    # Get current progress
    current_progress = _parse_onboarding_data(current_user)
    
    # Update progress fields
    if progress_update.current_step is not None:
        current_progress.current_step = progress_update.current_step
    
    if progress_update.completed_steps is not None:
        # Add new completed steps (avoid duplicates)
        for step_id in progress_update.completed_steps:
            if step_id not in current_progress.completed_steps:
                current_progress.completed_steps.append(step_id)
        # Remove from skipped if completed
        current_progress.skipped_steps = [
            s for s in current_progress.skipped_steps 
            if s not in progress_update.completed_steps
        ]
    
    if progress_update.skipped_steps is not None:
        # Add new skipped steps (avoid duplicates)
        for step_id in progress_update.skipped_steps:
            if step_id not in current_progress.skipped_steps:
                current_progress.skipped_steps.append(step_id)
        # Remove from completed if skipped
        current_progress.completed_steps = [
            s for s in current_progress.completed_steps 
            if s not in progress_update.skipped_steps
        ]
    
    if progress_update.tutorial_viewed is not None:
        if progress_update.tutorial_viewed not in current_progress.tutorial_views:
            current_progress.tutorial_views.append(progress_update.tutorial_viewed)
    
    if progress_update.sample_data_viewed is not None:
        if progress_update.sample_data_viewed not in current_progress.sample_data_views:
            current_progress.sample_data_views.append(progress_update.sample_data_viewed)
    
    # Update last accessed
    current_progress.last_accessed = datetime.now(timezone.utc)
    
    # Save to database - serialize datetime to ISO string
    progress_dict = current_progress.model_dump(mode='json')
    if progress_dict.get('last_accessed'):
        progress_dict['last_accessed'] = progress_dict['last_accessed'].isoformat() if hasattr(progress_dict['last_accessed'], 'isoformat') else progress_dict['last_accessed']
    current_user.onboarding_data = progress_dict
    db.commit()
    db.refresh(current_user)
    
    return current_progress


@router.put("/complete", response_model=OnboardingStatus)
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark onboarding as completed."""
    current_user.onboarding_completed = request.completed
    
    # Update last accessed timestamp
    progress = _parse_onboarding_data(current_user)
    progress.last_accessed = datetime.now(timezone.utc)
    # Serialize datetime to ISO string
    progress_dict = progress.model_dump(mode='json')
    if progress_dict.get('last_accessed'):
        progress_dict['last_accessed'] = progress_dict['last_accessed'].isoformat() if hasattr(progress_dict['last_accessed'], 'isoformat') else progress_dict['last_accessed']
    current_user.onboarding_data = progress_dict
    
    db.commit()
    db.refresh(current_user)
    
    return OnboardingStatus(
        needs_onboarding=not current_user.onboarding_completed,
        onboarding_completed=current_user.onboarding_completed,
        current_progress=progress,
        role=current_user.role
    )


@router.post("/reset")
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset onboarding status (allow re-access)."""
    current_user.onboarding_completed = False
    current_user.onboarding_data = _get_default_progress()
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Onboarding reset successfully",
        "onboarding_completed": False
    }

