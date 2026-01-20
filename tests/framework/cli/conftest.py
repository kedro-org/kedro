"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

import os
import shutil
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml
from click.testing import CliRunner
from pytest import fixture

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from kedro import __version__ as kedro_version
from kedro import __version__ as version
from kedro.framework.cli.catalog import catalog_cli
from kedro.framework.cli.cli import cli
from kedro.framework.cli.jupyter import jupyter_cli
from kedro.framework.cli.pipeline import pipeline_cli
from kedro.framework.cli.project import project_group
from kedro.framework.cli.registry import registry_cli
from kedro.framework.cli.starters import (
    TEMPLATE_PATH,
    _convert_tool_short_names_to_numbers,
    _make_cookiecutter_args_and_fetch_template,
    _parse_tools_input,
    _parse_yes_no_to_bool,
    create_cli,
)
from kedro.framework.project import configure_project, pipelines, settings
from kedro.framework.startup import ProjectMetadata

REPO_NAME = "dummy_project"
PACKAGE_NAME = "dummy_package"

FILES_IN_TEMPLATE_WITH_NO_TOOLS = 15


@fixture
def entry_points(mocker):
    return mocker.patch("importlib.metadata.entry_points", spec=True)


@fixture
def entry_point(mocker, entry_points):
    ep = mocker.patch("importlib.metadata.EntryPoint", spec=True)
    entry_points.return_value.select.return_value = [ep]
    return ep


@fixture(scope="module")
def fake_root_dir():
    # using tempfile as tmp_path fixture doesn't support module scope
    tmpdir = tempfile.mkdtemp()
    try:
        yield Path(tmpdir).resolve()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@fixture(scope="module")
def fake_package_path(fake_root_dir):
    return fake_root_dir.resolve() / REPO_NAME / "src" / PACKAGE_NAME


@fixture(scope="module")
def fake_repo_path(fake_root_dir):
    return fake_root_dir.resolve() / REPO_NAME


@fixture(scope="module")
def dummy_config(fake_root_dir, fake_metadata):
    config = {
        "project_name": fake_metadata.project_name,
        "repo_name": REPO_NAME,
        "python_package": fake_metadata.package_name,
        "output_dir": str(fake_root_dir),
    }

    config_path = fake_root_dir / "dummy_config.yml"
    with config_path.open("w") as f:
        yaml.dump(config, f)

    return config_path


@fixture(scope="module")
def fake_metadata(fake_root_dir):
    metadata = ProjectMetadata(
        config_file=fake_root_dir / REPO_NAME / "pyproject.toml",
        package_name=PACKAGE_NAME,
        project_name="CLI Testing Project",
        project_path=fake_root_dir / REPO_NAME,
        kedro_init_version=kedro_version,
        source_dir=fake_root_dir / REPO_NAME / "src",
        tools=None,
        example_pipeline=None,
    )
    return metadata


# This is needed just for the tests, those CLI groups are merged in our
# code when invoking `kedro` but when imported, they still need to be merged
@fixture(scope="module")
def fake_kedro_cli():
    return click.CommandCollection(
        name="Kedro",
        sources=[
            cli,
            create_cli,
            catalog_cli,
            jupyter_cli,
            pipeline_cli,
            project_group,
            registry_cli,
        ],
    )


@fixture(scope="module")
def fake_project_cli(
    fake_repo_path: Path,
    dummy_config: Path,
    fake_kedro_cli: click.CommandCollection,
):
    old_settings = settings.as_dict()
    starter_path = Path(__file__).resolve().parents[3]
    starter_path = starter_path / "features" / "test_starter"
    modules_before = sys.modules.copy()
    CliRunner().invoke(
        fake_kedro_cli, ["new", "-c", str(dummy_config), "--starter", str(starter_path)]
    )
    # Delete the project logging.yml, which leaves behind info.log and error.log files.
    # This leaves logging config as the framework default.
    try:
        (fake_repo_path / "conf" / "logging.yml").unlink()
    except FileNotFoundError:
        pass

    # NOTE: Here we load a couple of modules, as they would be imported in
    # the code and tests.
    # It's safe to remove the new entries from path due to the python
    # module caching mechanism. Any `reload` on it will not work though.
    old_path = sys.path.copy()
    sys.path = [str(fake_repo_path / "src"), *sys.path]

    import_module(PACKAGE_NAME)
    with patch(
        "kedro.framework.project.LOGGING.set_project_logging", return_value=None
    ):
        configure_project(PACKAGE_NAME)
        yield fake_kedro_cli

    # reset side-effects of configure_project
    pipelines.configure()

    for key, value in old_settings.items():
        settings.set(key, value)
    sys.path = old_path

    # Restore sys.modules to its previous state
    sys.modules.clear()
    sys.modules.update(modules_before)


@fixture
def chdir_to_dummy_project(fake_repo_path, monkeypatch):
    monkeypatch.chdir(str(fake_repo_path))


# Shared fixtures for starter tests
@pytest.fixture
def chdir_to_tmp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def mock_determine_repo_dir(mocker):
    """Mock cookiecutter's determine_repo_dir to avoid git interactions."""
    return mocker.patch(
        "cookiecutter.repository.determine_repo_dir",
        return_value=(str(TEMPLATE_PATH), None),
    )


@pytest.fixture
def mock_cookiecutter(mocker):
    """Mock cookiecutter.main.cookiecutter to avoid actual project creation."""
    return mocker.patch("cookiecutter.main.cookiecutter")


@pytest.fixture
def patch_cookiecutter_args(mocker):
    """Patch cookiecutter args to force checkout to 'main'."""
    mocker.patch(
        "kedro.framework.cli.starters._make_cookiecutter_args_and_fetch_template",
        side_effect=mock_make_cookiecutter_args_and_fetch_template,
    )


@pytest.fixture
def mock_env_vars(mocker):
    """Fixture to mock environment variables"""
    mocker.patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}, clear=True)


# Shared helper functions for starter tests
def mock_make_cookiecutter_args_and_fetch_template(*args, **kwargs):
    """Mock function to force checkout to 'main'."""
    cookiecutter_args, starter_path = _make_cookiecutter_args_and_fetch_template(
        *args, **kwargs
    )
    cookiecutter_args["checkout"] = "main"  # Force the checkout to be "main"
    return cookiecutter_args, starter_path


def _clean_up_project(project_dir):
    """Clean up a project directory."""
    if project_dir.is_dir():
        shutil.rmtree(str(project_dir), ignore_errors=True)


def _write_yaml(filepath: Path, config: dict):
    """Write a YAML config file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _make_cli_prompt_input(
    tools="none",
    project_name="",
    example_pipeline="no",
    repo_name="",
    python_package="",
):
    """Create CLI prompt input string."""
    return "\n".join([project_name, tools, example_pipeline, repo_name, python_package])


def _make_cli_prompt_input_without_tools(
    project_name="", repo_name="", python_package=""
):
    """Create CLI prompt input string without tools."""
    return "\n".join([project_name, repo_name, python_package])


def _make_cli_prompt_input_without_name(tools="none", repo_name="", python_package=""):
    """Create CLI prompt input string without project name."""
    return "\n".join([tools, repo_name, python_package])


def _get_expected_files(tools: str, example_pipeline: str):
    """Calculate expected number of files based on tools and example pipeline."""
    tools_template_files = {
        "1": 0,  # Linting does not add any files
        "2": 3,  # If Testing is selected, we add 2 init.py files and 1 test_run.py
        "3": 1,  # If Logging is selected, we add logging.py
        "4": 2,  # If Documentation is selected, we add conf.py and index.rst
        "5": 8,  # If Data Structure is selected, we add 8 .gitkeep files
        "6": 0,  # PySpark selection no longer adds extra starter files
    }  # files added to template by each tool
    tools_list = _parse_tools_input(tools)
    example_pipeline_bool = _parse_yes_no_to_bool(example_pipeline)
    expected_files = FILES_IN_TEMPLATE_WITH_NO_TOOLS

    for tool in tools_list:
        expected_files = expected_files + tools_template_files[tool]
    # If example pipeline was chosen we don't need to delete /data folder
    if example_pipeline_bool and "5" not in tools_list:
        expected_files += tools_template_files["5"]
    example_files_count = [
        3,  # Raw data files
        3,  # Parameters_ .yml files, including 1 extra for viz
        9,  # .py files in pipelines folder, including 3 .py from reporting for Viz
    ]
    if example_pipeline_bool:  # If example option is chosen
        expected_files += sum(example_files_count)
        expected_files += (
            1 if "2" in tools_list else 0
        )  # add 1 test file if tests is chosen in tools

    return expected_files


def _assert_requirements_ok(
    result,
    tools="none",
    repo_name="new-kedro-project",
    output_dir=".",
):
    """Assert that requirements in pyproject.toml are correct."""
    assert result.exit_code == 0, result.output

    root_path = (Path(output_dir) / repo_name).resolve()

    assert "Congratulations!" in result.output
    assert f"has been created in the directory \n{root_path}" in result.output

    pyproject_file_path = root_path / "pyproject.toml"
    with pyproject_file_path.open("rb") as f:
        pyproject_config = tomllib.load(f)

    tools_list = _parse_tools_input(tools)

    if "1" in tools_list:
        expected = {
            "tool": {
                "ruff": {
                    "line-length": 88,
                    "show-fixes": True,
                    "lint": {
                        "select": ["F", "W", "E", "I", "UP", "PL", "T201"],
                        "ignore": ["E501"],
                    },
                    "format": {"docstring-code-format": True},
                },
            }
        }
        assert expected["tool"]["ruff"] == pyproject_config["tool"]["ruff"]
        assert (
            "ruff~=0.12.0"
            in pyproject_config["project"]["optional-dependencies"]["dev"]
        )

    if "2" in tools_list:
        expected = {
            "pytest": {
                "ini_options": {
                    "addopts": "--cov-report term-missing --cov src/new_kedro_project -ra"
                }
            },
            "coverage": {
                "report": {
                    "fail_under": 0,
                    "show_missing": True,
                    "exclude_lines": ["pragma: no cover", "raise NotImplementedError"],
                }
            },
        }
        assert expected["pytest"] == pyproject_config["tool"]["pytest"]
        assert expected["coverage"] == pyproject_config["tool"]["coverage"]

        assert (
            "pytest-cov>=3,<7"
            in pyproject_config["project"]["optional-dependencies"]["dev"]
        )
        assert (
            "pytest-mock>=1.7.1, <2.0"
            in pyproject_config["project"]["optional-dependencies"]["dev"]
        )
        assert (
            "pytest~=7.2" in pyproject_config["project"]["optional-dependencies"]["dev"]
        )

    if "4" in tools_list:
        expected = {
            "optional-dependencies": {
                "docs": [
                    "docutils<0.21",
                    "sphinx>=5.3,<7.3",
                    "sphinx_rtd_theme==2.0.0",
                    "nbsphinx==0.8.1",
                    "sphinx-autodoc-typehints==1.20.2",
                    "sphinx_copybutton==0.5.2",
                    "ipykernel>=5.3, <7.0",
                    "Jinja2<3.2.0",
                    "myst-parser>=1.0,<2.1",
                ]
            }
        }
        assert (
            expected["optional-dependencies"]["docs"]
            == pyproject_config["project"]["optional-dependencies"]["docs"]
        )


def _assert_template_ok(
    result,
    tools="none",
    project_name="New Kedro Project",
    example_pipeline="no",
    repo_name="new-kedro-project",
    python_package="new_kedro_project",
    kedro_version=version,
    output_dir=".",
):
    """Assert that the generated project template is correct."""
    assert result.exit_code == 0, result.output

    full_path = (Path(output_dir) / repo_name).resolve()

    assert "Congratulations!" in result.output
    assert (
        f"Your project '{project_name}' has been created in the directory \n{full_path}"
        in result.output
    )

    if "y" in example_pipeline.lower():
        assert "It has been created with an example pipeline." in result.output
    else:
        assert "It has been created with an example pipeline." not in result.output

    generated_files = [
        p for p in full_path.rglob("*") if p.is_file() and p.name != ".DS_Store"
    ]

    assert len(generated_files) == _get_expected_files(tools, example_pipeline)
    assert full_path.exists()
    assert (full_path / ".gitignore").is_file()
    assert project_name in (full_path / "README.md").read_text(encoding="utf-8")
    assert "KEDRO" in (full_path / ".gitignore").read_text(encoding="utf-8")
    assert kedro_version in (full_path / "requirements.txt").read_text(encoding="utf-8")
    assert (full_path / "src" / python_package / "__init__.py").is_file()


def _assert_name_ok(
    result,
    project_name="New Kedro Project",
):
    """Assert that project name is correctly displayed."""
    assert result.exit_code == 0
    assert "Congratulations!" in result.output
    assert (
        f"Your project '{project_name}' has been created in the directory"
        in result.output
    )
