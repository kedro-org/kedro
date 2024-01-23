import shutil
from pathlib import Path

import toml
import yaml
from pytest import fixture

from kedro import __version__ as kedro_version
from kedro.framework.cli.starters import (
    TEMPLATE_PATH,
    _make_cookiecutter_args_and_fetch_template,
    _parse_tools_input,
    _parse_yes_no_to_bool,
)

FILES_IN_TEMPLATE_WITH_NO_TOOLS = 15


@fixture
def chdir_to_tmp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


@fixture
def mock_determine_repo_dir(mocker):
    return mocker.patch(
        "cookiecutter.repository.determine_repo_dir",
        return_value=(str(TEMPLATE_PATH), None),
    )


@fixture
def mock_cookiecutter(mocker):
    return mocker.patch("cookiecutter.main.cookiecutter")


@fixture
def patch_cookiecutter_args(mocker):
    mocker.patch(
        "kedro.framework.cli.starters._make_cookiecutter_args_and_fetch_template",
        side_effect=mock_make_cookiecutter_args_and_fetch_template,
    )


def mock_make_cookiecutter_args_and_fetch_template(*args, **kwargs):
    cookiecutter_args, starter_path = _make_cookiecutter_args_and_fetch_template(
        *args, **kwargs
    )
    cookiecutter_args["checkout"] = "main"  # Force the checkout to be "main"
    return cookiecutter_args, starter_path


def _make_cli_prompt_input(
    tools="none",
    project_name="",
    example_pipeline="no",
    repo_name="",
    python_package="",
):
    return "\n".join([project_name, tools, example_pipeline, repo_name, python_package])


def _clean_up_project(project_dir):
    if project_dir.is_dir():
        shutil.rmtree(str(project_dir), ignore_errors=True)


def _write_yaml(filepath: Path, config: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _make_cli_prompt_input_without_tools(
    project_name="", repo_name="", python_package=""
):
    return "\n".join([project_name, repo_name, python_package])


def _make_cli_prompt_input_without_name(tools="none", repo_name="", python_package=""):
    return "\n".join([tools, repo_name, python_package])


def _get_expected_files(tools: str, example_pipeline: str):
    tools_template_files = {
        "1": 0,  # Linting does not add any files
        "2": 3,  # If Testing is selected, we add 2 init.py files and 1 test_run.py
        "3": 1,  # If Logging is selected, we add logging.py
        "4": 2,  # If Documentation is selected, we add conf.py and index.rst
        "5": 8,  # If Data Structure is selected, we add 8 .gitkeep files
        "6": 2,  # If PySpark is selected, we add spark.yml and hooks.py
        "7": 0,  # Kedro Viz does not add any files
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
        2,  # Parameters_ .yml files
        6,  # .py files in pipelines folder
    ]
    if example_pipeline_bool:  # If example option is chosen
        expected_files += sum(example_files_count)
        expected_files += (
            4 if "7" in tools_list else 0
        )  # add 3 .py and 1 parameters files in reporting for Viz
        expected_files += (
            1 if "2" in tools_list else 0
        )  # add 1 test file if tests is chosen in tools

    return expected_files


# noqa: PLR0913
def _assert_template_ok(
    result,
    tools="none",
    project_name="New Kedro Project",
    example_pipeline="no",
    repo_name="new-kedro-project",
    python_package="new_kedro_project",
    kedro_version=kedro_version,
    output_dir=".",
):
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


def _assert_requirements_ok(
    result,
    tools="none",
    repo_name="new-kedro-project",
    output_dir=".",
):
    assert result.exit_code == 0, result.output

    root_path = (Path(output_dir) / repo_name).resolve()

    assert "Congratulations!" in result.output
    assert f"has been created in the directory \n{root_path}" in result.output

    requirements_file_path = root_path / "requirements.txt"
    pyproject_file_path = root_path / "pyproject.toml"

    tools_list = _parse_tools_input(tools)

    if "1" in tools_list:
        with open(requirements_file_path) as requirements_file:
            requirements = requirements_file.read()

        assert "ruff" in requirements

        pyproject_config = toml.load(pyproject_file_path)
        expected = {
            "tool": {
                "ruff": {
                    "line-length": 88,
                    "show-fixes": True,
                    "select": ["F", "W", "E", "I", "UP", "PL", "T201"],
                    "ignore": ["E501"],
                    "format": {"docstring-code-format": True},
                }
            }
        }
        assert expected["tool"]["ruff"] == pyproject_config["tool"]["ruff"]

    if "2" in tools_list:
        with open(requirements_file_path) as requirements_file:
            requirements = requirements_file.read()

        assert "pytest-cov~=3.0" in requirements
        assert "pytest-mock>=1.7.1, <2.0" in requirements
        assert "pytest~=7.2" in requirements

        pyproject_config = toml.load(pyproject_file_path)
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

    if "4" in tools_list:
        pyproject_config = toml.load(pyproject_file_path)
        expected = {
            "optional-dependencies": {
                "docs": [
                    "docutils<0.18.0",
                    "sphinx~=3.4.3",
                    "sphinx_rtd_theme==0.5.1",
                    "nbsphinx==0.8.1",
                    "sphinx-autodoc-typehints==1.11.1",
                    "sphinx_copybutton==0.3.1",
                    "ipykernel>=5.3, <7.0",
                    "Jinja2<3.1.0",
                    "myst-parser~=0.17.2",
                ]
            }
        }
        assert (
            expected["optional-dependencies"]["docs"]
            == pyproject_config["project"]["optional-dependencies"]["docs"]
        )
