"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

if sys.version_info >= (3, 11):
    pass
else:
    pass


from kedro.framework.cli.starters import (
    TEMPLATE_PATH,
)
from tests.framework.cli.starters.utils import (
    _create_example_pipeline_files,
    _mock_determine_repo_dir_impl,
    mock_make_cookiecutter_args_and_fetch_template,
)


# Override parent's entry_points/entry_point to avoid mocker dependency
@pytest.fixture
def entry_points():
    """Mock importlib.metadata.entry_points for starter plugin tests."""
    with patch("importlib.metadata.entry_points", spec=True) as mock:
        yield mock


@pytest.fixture
def entry_point(entry_points):
    """Mock importlib.metadata.EntryPoint for starter plugin tests."""
    with patch("importlib.metadata.EntryPoint", spec=True) as mock_ep:
        entry_points.return_value.select.return_value = [mock_ep]
        yield mock_ep


# Shared fixtures for starter tests
@pytest.fixture
def chdir_to_tmp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def template_in_cwd(tmp_path, chdir_to_tmp):
    """Copy template to 'template' in cwd for tests using local starter."""
    template_path = tmp_path / "template"
    shutil.copytree(TEMPLATE_PATH, template_path)
    return template_path


@pytest.fixture
def mock_determine_repo_dir():
    """Mock cookiecutter's determine_repo_dir to avoid git interactions."""
    with patch(
        "cookiecutter.repository.determine_repo_dir",
        return_value=(str(TEMPLATE_PATH), None),
    ) as mock:
        yield mock


@pytest.fixture
def mock_cookiecutter():
    """Mock cookiecutter.main.cookiecutter to avoid actual project creation."""
    with patch("cookiecutter.main.cookiecutter") as mock:
        yield mock


@pytest.fixture
def patch_cookiecutter_args():
    """Patch cookiecutter args to force checkout to 'main' and prevent git cloning."""
    original_cookiecutter = None
    try:
        from cookiecutter.main import cookiecutter as original_cookiecutter_func

        original_cookiecutter = original_cookiecutter_func
    except ImportError:
        pass

    def mock_cookiecutter_with_example_files(template, **kwargs):
        """Mock cookiecutter that creates expected files for example pipeline."""
        extra_context = kwargs.get("extra_context", {})
        output_dir = Path(kwargs.get("output_dir", "."))
        repo_name = extra_context.get("repo_name", "new-kedro-project")
        python_package = extra_context.get("python_package", "new_kedro_project")
        project_path = output_dir / repo_name
        example_pipeline = extra_context.get("example_pipeline", "False")

        kwargs_without_directory = {k: v for k, v in kwargs.items() if k != "directory"}

        if original_cookiecutter:
            result_path = original_cookiecutter(
                template=template, **kwargs_without_directory
            )
        else:
            template_path = Path(template)
            if template_path.exists() and template_path.is_dir():
                shutil.copytree(
                    template_path,
                    project_path,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                result_path = str(project_path)
            else:
                result_path = str(project_path)
                project_path.mkdir(parents=True, exist_ok=True)

        if example_pipeline == "True":
            tools_str = extra_context.get("tools", "['None']")
            _create_example_pipeline_files(Path(result_path), python_package, tools_str)

        return result_path

    with (
        patch(
            "cookiecutter.repository.determine_repo_dir",
            side_effect=_mock_determine_repo_dir_impl,
        ),
        patch(
            "cookiecutter.main.cookiecutter",
            side_effect=mock_cookiecutter_with_example_files,
        ),
        patch(
            "kedro.framework.cli.starters._make_cookiecutter_args_and_fetch_template",
            side_effect=mock_make_cookiecutter_args_and_fetch_template,
        ),
    ):
        yield
