from pathlib import Path

import pytest

from kedro.server.utils import ServerSettingsError, get_project_path, is_debug_mode


def test_get_project_path_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("KEDRO_PROJECT_PATH", str(tmp_path))

    assert get_project_path() == Path(tmp_path).resolve()


def test_get_project_path_raises_when_environment_variable_missing(monkeypatch):
    monkeypatch.delenv("KEDRO_PROJECT_PATH", raising=False)

    with pytest.raises(ServerSettingsError, match="is not set"):
        get_project_path()


def test_get_project_path_raises_when_path_does_not_exist(monkeypatch):
    monkeypatch.setenv("KEDRO_PROJECT_PATH", "/tmp/kedro-path-that-does-not-exist")

    with pytest.raises(ServerSettingsError, match="does not exist"):
        get_project_path()


@pytest.mark.parametrize("value", ["1", "true", "yes", "TRUE", "Yes"])
def test_is_debug_mode_truthy_values(monkeypatch, value):
    monkeypatch.setenv("KEDRO_SERVER_DEBUG", value)

    assert is_debug_mode() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_is_debug_mode_falsey_values(monkeypatch, value):
    monkeypatch.setenv("KEDRO_SERVER_DEBUG", value)

    assert is_debug_mode() is False
