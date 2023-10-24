import importlib
import sys
import textwrap

import pytest

from kedro.config import ConfigLoader, TemplatedConfigLoader
from kedro.framework.context.context import KedroContext
from kedro.framework.project import configure_project, settings, validate_settings
from kedro.framework.session.shelvestore import ShelveStore
from kedro.framework.session.store import BaseSessionStore
from kedro.io import DataCatalog


class MyContext(KedroContext):
    pass


class MyDataCatalog(DataCatalog):
    pass


class ProjectHooks:
    pass


@pytest.fixture
def mock_package_name_with_settings_file(tmpdir):
    """This mock settings file tests everything that can be customised in settings.py.
    Where there are suggestions in the project template settings.py (e.g. as for
    CONFIG_LOADER_CLASS), those suggestions should be tested."""
    old_settings = settings.as_dict()
    settings_file_path = tmpdir.mkdir("test_package").join("settings.py")
    project_path, package_name, _ = str(settings_file_path).rpartition("test_package")
    settings_file_path.write(
        textwrap.dedent(
            f"""
                from {__name__} import ProjectHooks
                HOOKS = (ProjectHooks(),)

                DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

                from kedro.framework.session.shelvestore import ShelveStore
                SESSION_STORE_CLASS = ShelveStore
                SESSION_STORE_ARGS = {{
                    "path": "./sessions"
                }}

                from {__name__} import MyContext
                CONTEXT_CLASS = MyContext
                CONF_SOURCE = "test_conf"

                from kedro.config import TemplatedConfigLoader
                CONFIG_LOADER_CLASS = TemplatedConfigLoader
                CONFIG_LOADER_ARGS = {{
                     "globals_pattern": "*globals.yml",
                }}

                # Class that manages the Data Catalog.
                from {__name__} import MyDataCatalog
                DATA_CATALOG_CLASS = MyDataCatalog
            """
        )
    )
    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)
    # reset side-effect of configure_project
    for key, value in old_settings.items():
        settings.set(key, value)


@pytest.fixture
def mock_package_name_without_settings_file(tmpdir):
    """This mocks a project that doesn't have a settings.py file.
    When configured, the project should have sensible default settings."""
    package_name = "test_package_without_settings"
    project_path, _, _ = str(tmpdir.mkdir(package_name)).rpartition(package_name)

    sys.path.insert(0, project_path)
    yield package_name
    sys.path.pop(0)


def test_settings_without_configure_project_shows_default_values():
    assert len(settings.HOOKS) == 0
    assert settings.DISABLE_HOOKS_FOR_PLUGINS.to_list() == []
    assert settings.SESSION_STORE_CLASS is BaseSessionStore
    assert settings.SESSION_STORE_ARGS == {}
    assert settings.CONTEXT_CLASS is KedroContext
    assert settings.CONF_SOURCE == "conf"
    assert settings.CONFIG_LOADER_CLASS == ConfigLoader
    assert settings.CONFIG_LOADER_ARGS == {}
    assert settings.DATA_CATALOG_CLASS == DataCatalog


def test_settings_after_configuring_project_shows_updated_values(
    mock_package_name_with_settings_file,
):
    configure_project(mock_package_name_with_settings_file)
    assert len(settings.HOOKS) == 1 and isinstance(settings.HOOKS[0], ProjectHooks)
    assert settings.DISABLE_HOOKS_FOR_PLUGINS.to_list() == ["kedro-viz"]
    assert settings.SESSION_STORE_CLASS is ShelveStore
    assert settings.SESSION_STORE_ARGS == {"path": "./sessions"}
    assert settings.CONTEXT_CLASS is MyContext
    assert settings.CONF_SOURCE == "test_conf"
    assert settings.CONFIG_LOADER_CLASS == TemplatedConfigLoader
    assert settings.CONFIG_LOADER_ARGS == {"globals_pattern": "*globals.yml"}
    assert settings.DATA_CATALOG_CLASS == MyDataCatalog


def test_validate_settings_without_settings_file(
    mock_package_name_without_settings_file,
):
    assert (
        importlib.util.find_spec(f"{mock_package_name_without_settings_file}.settings")
        is None
    )
    configure_project(mock_package_name_without_settings_file)
    validate_settings()
    # When a kedro project doesn't have a settings file, the settings should match be the default.
    test_settings_without_configure_project_shows_default_values()


def test_validate_settings_with_empty_package_name():
    with pytest.raises(ValueError):
        configure_project(None)  # Simulate outside of project mode
        validate_settings()
