from pathlib import Path

import pytest

from kedro.server.utils import (
    KEDRO_PROJECT_PATH_ENV,
    ServerSettingsError,
    _resolve_project_path,
)


def test_resolve_project_path_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(KEDRO_PROJECT_PATH_ENV, str(tmp_path))

    assert _resolve_project_path() == Path(tmp_path).resolve()


def test_resolve_project_path_from_argument(tmp_path):
    assert _resolve_project_path(tmp_path) == Path(tmp_path).resolve()


def test_resolve_project_path_argument_takes_precedence_over_env_var(
    tmp_path, monkeypatch, tmp_path_factory
):
    other_path = tmp_path_factory.mktemp("other")
    monkeypatch.setenv(KEDRO_PROJECT_PATH_ENV, str(other_path))

    assert _resolve_project_path(tmp_path) == Path(tmp_path).resolve()


def test_resolve_project_path_raises_when_environment_variable_missing(monkeypatch):
    monkeypatch.delenv(KEDRO_PROJECT_PATH_ENV, raising=False)

    with pytest.raises(ServerSettingsError, match="is not set"):
        _resolve_project_path()


def test_resolve_project_path_raises_when_path_does_not_exist(monkeypatch):
    monkeypatch.setenv(KEDRO_PROJECT_PATH_ENV, "/tmp/nonexistent_kedro_path_xyz")

    with pytest.raises(ServerSettingsError, match="does not exist"):
        _resolve_project_path()


def test_resolve_project_path_raises_when_argument_path_does_not_exist():
    with pytest.raises(ServerSettingsError, match="does not exist"):
        _resolve_project_path("/tmp/nonexistent_kedro_path_xyz")
