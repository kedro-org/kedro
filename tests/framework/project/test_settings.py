import sys
import textwrap
from unittest import mock

import pytest

from kedro.framework.context.context import KedroContext
from kedro.framework.project import configure_project, settings
from kedro.framework.session.store import BaseSessionStore

MOCK_CONTEXT_CLASS = mock.patch(
    "kedro.framework.context.context.KedroContext", autospec=True
)


def test_settings_without_configure_project_show_default_values():
    assert settings.CONF_ROOT == "conf"
    assert settings.CONTEXT_CLASS is KedroContext
    assert settings.SESSION_STORE_CLASS is BaseSessionStore
    assert settings.SESSION_STORE_ARGS == {}
    assert len(settings.DISABLE_HOOKS_FOR_PLUGINS) == 0


@pytest.fixture
def mock_package_name_with_settings_file(tmpdir):
    old_settings = settings.as_dict()
    settings_file_path = tmpdir.mkdir("test_package").join("settings.py")
    settings_file_path.write(
        textwrap.dedent(
            f"""
                from {__name__} import MOCK_CONTEXT_CLASS
                CONF_ROOT = "test_conf"
                CONTEXT_CLASS = MOCK_CONTEXT_CLASS
            """
        )
    )
    project_path, package_name, _ = str(settings_file_path).rpartition("test_package")
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)
    # reset side-effect of configure_project
    for key, value in old_settings.items():
        settings.set(key, value)


def test_settings_after_configuring_project_shows_updated_values(
    mock_package_name_with_settings_file,
):
    configure_project(mock_package_name_with_settings_file)
    assert settings.CONF_ROOT == "test_conf"
    assert settings.CONTEXT_CLASS is MOCK_CONTEXT_CLASS
