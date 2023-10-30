from pathlib import Path
import shutil
import sys
import click

current_dir = Path.cwd()

lint_requirements = "black~=22.12.0\nruff~=0.0.290\n"
lint_pyproject_requirements = """
[tool.ruff]
select = [
    "F",  # Pyflakes
    "E",  # Pycodestyle
    "W",  # Pycodestyle
    "UP",  # pyupgrade
    "I",  # isort
    "PL", # Pylint
]
ignore = ["E501"]  # Black takes care of line-too-long
"""

test_requirements = "pytest-cov~=3.0\npytest-mock>=1.7.1, <2.0\npytest~=7.2"
test_pyproject_requirements = """
[tool.pytest.ini_options]
addopts = \"\"\"
--cov-report term-missing \\
--cov src/{{ cookiecutter.python_package }} -ra
\"\"\"

[tool.coverage.report]
fail_under = 0
show_missing = true
exclude_lines = ["pragma: no cover", "raise NotImplementedError"]
"""

docs_pyproject_requirements = """
[project.optional-dependencies]
docs = [
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
"""


def setup_template_add_ons(selected_add_ons_list, requirements_file_path, pyproject_file_path, python_package_name):
    """Removes directories and files related to unwanted addons from
    a Kedro project template. Adds the necessary requirements for
    the addons that were selected.

    Args:
        selected_add_ons_list: a list containing numbers from 1 to 5,
            representing specific add-ons.
        requirements_file_path: the path to the requirements.txt file.
        pyproject_file_path: the path to the pyproject.toml file
            located on the the root of the template.
    """
    if "Linting" not in selected_add_ons_list:
        pass
    else:
        with open(requirements_file_path, 'a') as file:
            file.write(lint_requirements)
        with open(pyproject_file_path, 'a') as file:
            file.write(lint_pyproject_requirements)

    if "Testing" not in selected_add_ons_list:
        tests_path = current_dir / "tests"
        if tests_path.exists():
            shutil.rmtree(str(tests_path))
    else:
        with open(requirements_file_path, 'a') as file:
            file.write(test_requirements)
        with open(pyproject_file_path, 'a') as file:
            file.write(test_pyproject_requirements)

    if "Logging" not in selected_add_ons_list:
        logging_yml_path = current_dir / "conf/logging.yml"
        if logging_yml_path.exists():
            logging_yml_path.unlink()

    if "Documentation" not in selected_add_ons_list:
        docs_path = current_dir / "docs"
        if docs_path.exists():
            shutil.rmtree(str(docs_path))
    else:
        with open(pyproject_file_path, 'a') as file:
            file.write(docs_pyproject_requirements)

    if "Data Structure" not in selected_add_ons_list:
        data_path = current_dir / "data"
        if data_path.exists():
            shutil.rmtree(str(data_path))

    if "Pyspark" not in selected_add_ons_list:  # If PySpark not selected
        pass
    else:  # Use spaceflights-pyspark to create pyspark template
        # Remove all .csv and .xlsx files from data/01_raw/
        raw_data_path = current_dir / "data/01_raw/"
        if raw_data_path.exists() and raw_data_path.is_dir():
            for file_path in raw_data_path.glob("*.*"):
                if file_path.suffix in [".csv", ".xlsx"]:
                    file_path.unlink()

        # Remove parameter files from conf/base/
        param_files = [
            "parameters_data_processing.yml",
            "parameters_data_science.yml",
        ]
        conf_base_path = current_dir / "conf/base/"
        if conf_base_path.exists() and conf_base_path.is_dir():
            for param_file in param_files:
                file_path = conf_base_path / param_file
                if file_path.exists():
                    file_path.unlink()

        # Remove specific pipeline subdirectories
        pipelines_path = current_dir / f"src/{python_package_name}/pipelines/"
        for pipeline_subdir in ["data_science", "data_processing"]:
            shutil.rmtree(pipelines_path / pipeline_subdir, ignore_errors=True)

        # Remove all test file from tests/pipelines/
        test_pipeline_path = current_dir / "tests/pipelines/test_data_science.py"
        if test_pipeline_path.exists():
            test_pipeline_path.unlink()


def sort_requirements(requirements_file_path):
    """Sort the requirements.txt file in alphabetical order.

    Args:
        requirements_file_path: the path to the requirements.txt file.
    """
    with open(requirements_file_path, 'r') as requirements:
        lines = requirements.readlines()

    lines = [line.strip() for line in lines]
    lines.sort()
    sorted_content = '\n'.join(lines)

    with open(requirements_file_path, 'w') as requirements:
        requirements.write(sorted_content)
