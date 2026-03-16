from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import sme, sme_templates


class _FakeDB:
    def __init__(self, bind: object) -> None:
        self._bind = bind

    def get_bind(self) -> object:
        return self._bind


def test_workspace_storage_bootstrap_creates_missing_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    bind = object()
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        sme,
        "inspect",
        lambda received_bind: SimpleNamespace(
            has_table=lambda name: name not in {"lc_workspaces", "drafts", "amendments"}
        ),
    )

    def fake_create_all(*, bind: object, tables: list[object], checkfirst: bool) -> None:
        observed["bind"] = bind
        observed["tables"] = [table.name for table in tables]
        observed["checkfirst"] = checkfirst

    monkeypatch.setattr(sme.LCWorkspace.metadata, "create_all", fake_create_all)

    sme.ensure_sme_workspace_storage(_FakeDB(bind))

    assert observed == {
        "bind": bind,
        "tables": ["lc_workspaces", "drafts", "amendments"],
        "checkfirst": True,
    }


def test_template_storage_bootstrap_creates_missing_table(monkeypatch: pytest.MonkeyPatch) -> None:
    bind = object()
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        sme_templates,
        "inspect",
        lambda received_bind: SimpleNamespace(has_table=lambda name: False),
    )

    def fake_create_all(*, bind: object, tables: list[object], checkfirst: bool) -> None:
        observed["bind"] = bind
        observed["tables"] = [table.name for table in tables]
        observed["checkfirst"] = checkfirst

    monkeypatch.setattr(sme_templates.SMETemplate.metadata, "create_all", fake_create_all)

    sme_templates.ensure_sme_template_storage(_FakeDB(bind))

    assert observed == {
        "bind": bind,
        "tables": ["sme_templates"],
        "checkfirst": True,
    }


def test_workspace_storage_bootstrap_surfaces_beta_unavailable_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bind = object()

    monkeypatch.setattr(
        sme,
        "inspect",
        lambda received_bind: SimpleNamespace(has_table=lambda name: False),
    )

    def fake_create_all(*, bind: object, tables: list[object], checkfirst: bool) -> None:
        raise RuntimeError("permission denied")

    monkeypatch.setattr(sme.LCWorkspace.metadata, "create_all", fake_create_all)

    with pytest.raises(HTTPException) as exc:
        sme.ensure_sme_workspace_storage(_FakeDB(bind))

    assert exc.value.status_code == 503
    assert "temporarily unavailable" in str(exc.value.detail)
