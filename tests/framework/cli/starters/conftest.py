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
import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from kedro import __version__ as version
from kedro.framework.cli.starters import (
    TEMPLATE_PATH,
    _make_cookiecutter_args_and_fetch_template,
    _parse_tools_input,
    _parse_yes_no_to_bool,
)

# Number of files in the base template when no tools are selected.
# Includes: .gitignore, README.md, requirements.txt, pyproject.toml, and
# the default src/ package structure.
FILES_IN_TEMPLATE_WITH_NO_TOOLS = 15


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


def _mock_determine_repo_dir_impl(*args, **kwargs):
    """Mock determine_repo_dir to return local template path instead of cloning."""
    template = kwargs.get("template", args[0] if args else None)
    if template and (str(template).startswith("git+") or "github.com" in str(template)):
        return str(TEMPLATE_PATH), None
    if template:
        return str(template), None
    return str(TEMPLATE_PATH), None


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


# Shared helper functions for starter tests
def _create_example_pipeline_files(
    result_path_obj: Path, python_package: str, tools: str
):
    """Create expected example pipeline files (data, params, pipelines, tests)."""
    # Create data files (3 raw data files)
    (result_path_obj / "data" / "01_raw").mkdir(parents=True, exist_ok=True)
    for data_file in ["companies.csv", "reviews.csv", "shuttles.xlsx"]:
        (result_path_obj / "data" / "01_raw" / data_file).touch()

    # Create parameters files (3 YAML files)
    (result_path_obj / "conf" / "base").mkdir(parents=True, exist_ok=True)
    for param_file in [
        "parameters_data_science.yml",
        "parameters_reporting.yml",
        "parameters.yml",
    ]:
        (result_path_obj / "conf" / "base" / param_file).write_text("{}")

    # Create pipeline Python files (9 files)
    pipelines_dir = result_path_obj / "src" / python_package / "pipelines"
    pipelines_dir.mkdir(parents=True, exist_ok=True)

    for pipeline_name in ["data_science", "data_engineering", "reporting"]:
        pipeline_dir = pipelines_dir / pipeline_name
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "__init__.py").touch()
        (pipeline_dir / "pipeline.py").write_text(
            "def create_pipeline(**kwargs):\n    return None\n"
        )
        (pipeline_dir / "nodes.py").write_text("# nodes\n")
    (pipelines_dir / "reporting" / "visualizations.py").write_text("# viz\n")

    # Create test file if testing tool is selected
    if "Testing" in tools or "2" in tools:
        test_dir = result_path_obj / "tests" / "pipelines" / "data_science"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "test_pipeline.py").write_text("# test\n")


def mock_make_cookiecutter_args_and_fetch_template(*args, **kwargs):
    """Mock function to force checkout to 'main' and use local template for git URLs."""
    cookiecutter_args, starter_path = _make_cookiecutter_args_and_fetch_template(
        *args, **kwargs
    )
    cookiecutter_args["checkout"] = "main"  # Force the checkout to be "main"

    # If starter_path is a git URL, replace it with local template path
    # and remove directory argument since local template doesn't have starter subdirectories
    if starter_path.startswith("git+") or "github.com" in starter_path:
        starter_path = str(TEMPLATE_PATH)
        # Remove directory argument when using local template
        cookiecutter_args.pop("directory", None)

    return cookiecutter_args, starter_path


def _write_yaml(filepath: Path, config: dict):
    """Write a YAML config file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _default_config(**overrides):
    """Return default config dict for kedro new, with optional overrides."""
    base = {
        "tools": "none",
        "project_name": "My Project",
        "example_pipeline": "no",
        "repo_name": "my-project",
        "python_package": "my_project",
    }
    return {**base, **overrides}


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
