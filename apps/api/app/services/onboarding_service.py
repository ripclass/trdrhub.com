"""Onboarding service — backs the 3-question wizard.

Single public entry point: ``complete_onboarding(db, user, payload)``.
Writes Company.business_activities / country / tier, marks User onboarded,
syncs User.role from the primary activity for legacy readers.
"""

from __future__ import annotations

from typing import List, Optional

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


# Canonical activity priority — mirrored from
# apps/web/src/api/onboarding.ts::ACTIVITY_PRIORITY. activities[0] drives
# landing dashboard + default active workspace, so we sort here as a
# belt-and-suspenders guard — even if a frontend caller forgets to sort,
# the persisted array is deterministic. Keep in lockstep.
#
# Pre-launch scope-down (2026-04-25): wizard only accepts exporter +
# importer. Stale 'agent' / 'services' values from DB rows still sort
# safely (unknown values land at the end via the rank.get fallback).
_ACTIVITY_PRIORITY = ("exporter", "importer")


def _sort_activities_by_priority(activities: List[str]) -> List[str]:
    rank = {value: idx for idx, value in enumerate(_ACTIVITY_PRIORITY)}
    # Unknown values sort to the end (shouldn't happen — Pydantic validates —
    # but leaves the array in a sane order if the validator is bypassed).
    return sorted(activities, key=lambda a: rank.get(a, len(_ACTIVITY_PRIORITY)))


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

    # Canonicalize activity order before persisting so landing dashboards are
    # deterministic regardless of the order the user clicked checkboxes in.
    sorted_activities = _sort_activities_by_priority(list(payload.activities))

    company.business_activities = sorted_activities
    company.country = payload.country
    company.tier = payload.tier

    # Mirror the primary activity into event_metadata so legacy status-restore
    # path (routers/onboarding.py::get_status) stays coherent for old clients.
    primary_activity = sorted_activities[0]
    event_meta = dict(company.event_metadata or {})
    if len(sorted_activities) > 1 and "exporter" in sorted_activities and "importer" in sorted_activities:
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
    onboarding_blob["activities"] = sorted_activities
    onboarding_blob["country"] = payload.country
    onboarding_blob["tier"] = payload.tier
    onboarding_blob["business_types"] = list(sorted_activities)  # legacy key
    onboarding_blob["company"] = {
        **onboarding_blob.get("company", {}),
        "name": company.name,
        "type": event_meta["business_type"],
        "size": payload.tier,
        "country": payload.country,
    }
    user.onboarding_data = onboarding_blob

    return company
