"""Onboarding service — backs the 3-question wizard.

Single public entry point: ``complete_onboarding(db, user, payload)``.
Writes Company.business_activities / country / tier, marks User onboarded,
syncs User.role from the primary activity for legacy readers.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..models import Company, User
from ..schemas.onboarding import OnboardingCompletePayload


# Primary activity → legacy User.role. Only covers values the existing
# CHECK constraint (``ck_users_role``) already allows. Agent/services users
# keep whatever role they had; frontend derives from business_activities.
_ACTIVITY_TO_LEGACY_ROLE = {
    "exporter": "exporter",
    "importer": "importer",
}


def _ensure_company(db: Session, user: User, name_override: Optional[str]) -> Company:
    """Fetch or create the Company row attached to this user."""
    if user.company_id:
        company = db.query(Company).get(user.company_id)
        if company:
            if name_override:
                company.name = name_override
            return company

    # No linked company — either first-run or orphaned user. Create one.
    display_name = name_override or (user.full_name.split()[0] + " Company" if user.full_name else user.email)
    company = Company(name=display_name, contact_email=user.email)
    db.add(company)
    db.flush()
    user.company_id = company.id
    return company


def complete_onboarding(
    db: Session,
    user: User,
    payload: OnboardingCompletePayload,
) -> Company:
    """Persist the 3-question wizard answers onto Company + User.

    Returns the Company row so the caller can build the response shape.
    Caller is responsible for commit.
    """
    company = _ensure_company(db, user, payload.company_name)

    company.business_activities = list(payload.activities)
    company.country = payload.country
    company.tier = payload.tier

    # Mirror the primary activity into event_metadata so legacy status-restore
    # path (routers/onboarding.py::get_status) stays coherent for old clients.
    primary_activity = payload.activities[0]
    event_meta = dict(company.event_metadata or {})
    if len(payload.activities) > 1 and "exporter" in payload.activities and "importer" in payload.activities:
        event_meta["business_type"] = "both"
    else:
        event_meta["business_type"] = primary_activity
    event_meta["company_size"] = payload.tier
    company.event_metadata = event_meta

    # Legacy role sync — only touch role if the primary activity maps to an
    # allowed value under ck_users_role. Skip for agent/services.
    legacy_role = _ACTIVITY_TO_LEGACY_ROLE.get(primary_activity)
    if legacy_role:
        user.role = legacy_role

    user.onboarding_completed = True
    user.status = user.status if user.status in {"approved", "under_review"} else "active"

    # Persist new-shape summary into onboarding_data for frontend restore paths
    # until Day 2 rewires the wizard to read Company directly.
    onboarding_blob = dict(user.onboarding_data or {})
    onboarding_blob["activities"] = list(payload.activities)
    onboarding_blob["country"] = payload.country
    onboarding_blob["tier"] = payload.tier
    onboarding_blob["business_types"] = list(payload.activities)  # legacy key
    onboarding_blob["company"] = {
        **onboarding_blob.get("company", {}),
        "name": company.name,
        "type": event_meta["business_type"],
        "size": payload.tier,
        "country": payload.country,
    }
    user.onboarding_data = onboarding_blob

    return company
