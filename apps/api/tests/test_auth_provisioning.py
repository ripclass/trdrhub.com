import os
from uuid import UUID

os.environ["DEBUG"] = "false"

from app.core import security


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeDB:
    def __init__(self):
        self.added = []

    def query(self, *args, **kwargs):
        return _FakeQuery()

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None

    def rollback(self):
        return None


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
