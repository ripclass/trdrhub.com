from __future__ import annotations

import ast
import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
MAIN_PATH = ROOT / "main.py"
CONFIG_PATH = ROOT / "app" / "config.py"


def _load_get_user_optional(settings_obj: Any, demo_user_result: Any = None, get_current_user_impl: Any = None):
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_user_optional"
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    fake_security_module = types.ModuleType("app.core.security")

    async def _default_get_current_user(*_args, **_kwargs):
        return {"user": "ok"}

    fake_security_module.get_current_user = get_current_user_impl or _default_get_current_user
    sys.modules["app.core.security"] = fake_security_module

    namespace: dict[str, Any] = {
        "Optional": Optional,
        "Header": lambda default=None: default,
        "Depends": lambda dep=None: dep,
        "Session": object,
        "User": object,
        "get_db": lambda: None,
        "HTTPException": HTTPException,
        "HTTPAuthorizationCredentials": HTTPAuthorizationCredentials,
        "status": status,
        "settings": settings_obj,
        "get_or_create_demo_user": lambda _db: demo_user_result,
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return namespace["get_user_optional"]


def test_public_validate_demo_flag_exists_in_settings() -> None:
    source = CONFIG_PATH.read_text(encoding="utf-8")
    assert "ENABLE_PUBLIC_VALIDATE_DEMO" in source


def test_get_user_optional_requires_auth_when_demo_mode_disabled() -> None:
    get_user_optional = _load_get_user_optional(
        settings_obj=SimpleNamespace(
            ENABLE_PUBLIC_VALIDATE_DEMO=False,
            is_production=lambda: False,
        ),
        demo_user_result={"user": "demo"},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_user_optional(authorization=None, db=None))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Authentication required"


def test_get_user_optional_allows_demo_only_when_flag_enabled_and_not_production() -> None:
    get_user_optional = _load_get_user_optional(
        settings_obj=SimpleNamespace(
            ENABLE_PUBLIC_VALIDATE_DEMO=True,
            is_production=lambda: False,
        ),
        demo_user_result={"user": "demo"},
    )

    result = asyncio.run(get_user_optional(authorization=None, db=None))

    assert result == {"user": "demo"}


def test_get_user_optional_does_not_fallback_to_demo_for_invalid_bearer_token() -> None:
    async def _failing_get_current_user(*_args, **_kwargs):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    get_user_optional = _load_get_user_optional(
        settings_obj=SimpleNamespace(
            ENABLE_PUBLIC_VALIDATE_DEMO=True,
            is_production=lambda: False,
        ),
        demo_user_result={"user": "demo"},
        get_current_user_impl=_failing_get_current_user,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_user_optional(authorization="Bearer bad-token", db=None))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid token"


def test_main_no_longer_exempts_validate_from_audit_or_csrf() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")
    assert '"/api/validate",  # TEMPORARY - Exempt for demo mode' not in source
    assert '"/api/validate",  # TEMPORARY - Exempt for demo mode (validation works without auth)' not in source
