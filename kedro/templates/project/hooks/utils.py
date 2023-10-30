from pathlib import Path
import shutil

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


# Helper Functions
def append_to_file(file_path, content):
    with open(file_path, 'a') as file:
        file.write(content)


def remove_dir(path):
    if path.exists():
        shutil.rmtree(str(path))


def remove_file(path):
    if path.exists():
        path.unlink()


def handle_starter_setup(python_package_name):
    # Remove all .csv and .xlsx files from data/01_raw/
    raw_data_path = current_dir / "data/01_raw/"
    for file_path in raw_data_path.glob("*.*"):
        if file_path.suffix in [".csv", ".xlsx"]:
            file_path.unlink()

    # Empty the contents of conf/base/catalog.yml
    catalog_yml_path = current_dir / "conf/base/catalog.yml"
    if catalog_yml_path.exists():
        catalog_yml_path.write_text('')
    # Remove parameter files from conf/base
    conf_base_path = current_dir / "conf/base/"
    for param_file in ["parameters_data_processing.yml", "parameters_data_science.yml"]:
        remove_file(conf_base_path / param_file)

    # Remove the pipelines subdirectories
    pipelines_path = current_dir / f"src/{python_package_name}/pipelines/"
    for pipeline_subdir in ["data_science", "data_processing"]:
        remove_dir(pipelines_path / pipeline_subdir)

    # Remove all test files from tests/pipelines/
    test_pipeline_path = current_dir / "tests/pipelines/test_data_science.py"
    remove_file(test_pipeline_path)


def setup_template_add_ons(selected_add_ons_list, requirements_file_path, pyproject_file_path, python_package_name):
    if "Linting" in selected_add_ons_list:
        append_to_file(requirements_file_path, lint_requirements)
        append_to_file(pyproject_file_path, lint_pyproject_requirements)

    if "Testing" in selected_add_ons_list:
        append_to_file(requirements_file_path, test_requirements)
        append_to_file(pyproject_file_path, test_pyproject_requirements)
    else:
        remove_dir(current_dir / "tests")

    if "Logging" not in selected_add_ons_list:
        remove_file(current_dir / "conf/logging.yml")

    if "Documentation" in selected_add_ons_list:
        append_to_file(pyproject_file_path, docs_pyproject_requirements)
    else:
        remove_dir(current_dir / "docs")

    if "Data Structure" not in selected_add_ons_list:
        remove_dir(current_dir / "data")

    if "Pyspark" in selected_add_ons_list:
        handle_starter_setup(python_package_name)

    if "Kedro Viz" in selected_add_ons_list:
        handle_starter_setup(python_package_name)


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
