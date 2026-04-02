import os
import asyncio
from uuid import UUID

os.environ["DEBUG"] = "false"

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import security


class _FakeQuery:
    def __init__(self, db):
        self._db = db

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if self._db.query_results:
            return self._db.query_results.pop(0)
        return None


class _FakeDB:
    def __init__(self, query_results=None):
        self.added = []
        self.query_results = list(query_results or [])
        self.rollback_called = False

    def query(self, *args, **kwargs):
        return _FakeQuery(self)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None

    def rollback(self):
        self.rollback_called = True
        return None


class _FlakyFlushDB(_FakeDB):
    def flush(self):
        raise RuntimeError("simulated flush failure")


def test_upsert_external_user_uses_non_null_password_placeholder():
    db = _FakeDB()
    claims = {
        "sub": "9b88cb4f-842a-4bd4-a8f3-687d5340383c",
        "email": "probe-liveauth@example.com",
        "user_metadata": {"full_name": "Probe Live Auth"},
        "app_metadata": {"role": "importer"},
    }

    user = security._upsert_external_user(db, claims)

    assert user.email == "probe-liveauth@example.com"
    assert user.role == "importer"
    assert user.hashed_password == ""
    assert user.auth_user_id == UUID("9b88cb4f-842a-4bd4-a8f3-687d5340383c")


def test_hash_password_falls_back_to_pbkdf2_when_bcrypt_paths_fail(monkeypatch):
    def _primary_fail(password):
        raise ValueError("password cannot be longer than 72 bytes")

    def _bcrypt_fail(password):
        raise RuntimeError("bcrypt backend unavailable")

    monkeypatch.setattr(security.pwd_context, "hash", _primary_fail)
    monkeypatch.setattr(security.bcrypt_fallback_context, "hash", _bcrypt_fail)

    hashed = security.hash_password("ProbePass123!")

    assert hashed.startswith("$pbkdf2-sha256$")
    assert security.verify_password("ProbePass123!", hashed) is True


def test_upsert_external_user_recovers_existing_user_after_flush_failure():
    existing_user = security.User(
        id=UUID("9b88cb4f-842a-4bd4-a8f3-687d5340383c"),
        email="probe-liveauth@example.com",
        auth_user_id=UUID("9b88cb4f-842a-4bd4-a8f3-687d5340383c"),
        hashed_password="",
        full_name="Probe Live Auth",
        role="importer",
        is_active=True,
    )
    db = _FlakyFlushDB(query_results=[None, None, None, existing_user])
    claims = {
        "sub": "9b88cb4f-842a-4bd4-a8f3-687d5340383c",
        "email": "probe-liveauth@example.com",
        "user_metadata": {"full_name": "Probe Live Auth"},
        "app_metadata": {"role": "importer"},
    }

    user = security._upsert_external_user(db, claims)

    assert user is existing_user
    assert db.rollback_called is True


def test_upsert_external_user_raises_provisioning_error_when_create_and_recovery_fail():
    db = _FlakyFlushDB(query_results=[None, None, None, None, None, None])
    claims = {
        "sub": "9b88cb4f-842a-4bd4-a8f3-687d5340383c",
        "email": "probe-liveauth@example.com",
        "user_metadata": {"full_name": "Probe Live Auth"},
        "app_metadata": {"role": "importer"},
    }

    try:
        security._upsert_external_user(db, claims)
    except security.ExternalAuthProvisioningError as exc:
        assert "probe-liveauth@example.com" in str(exc)
    else:
        raise AssertionError("Expected ExternalAuthProvisioningError")


def test_get_current_user_surfaces_provisioning_failures_as_server_errors(monkeypatch):
    async def _raise_provisioning(*args, **kwargs):
        raise security.ExternalAuthProvisioningError("db write failed")

    monkeypatch.setattr(security, "authenticate_external_token", _raise_provisioning)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="external-token",
    )

    try:
        asyncio.run(security.get_current_user(credentials=credentials, db=_FakeDB()))
    except HTTPException as exc:
        assert exc.status_code == 500
        assert "External authentication provisioning failed" in str(exc.detail)
    else:
        raise AssertionError("Expected HTTPException")
