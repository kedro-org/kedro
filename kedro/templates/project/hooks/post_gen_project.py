import json
from pathlib import Path
import shutil

from kedro.templates.project.hooks.utils import parse_add_ons_input

# Get the selected add-ons from cookiecutter
selected_add_ons = "{{ cookiecutter.add_ons }}"

# Parse the add-ons to get a list
selected_add_ons_list = parse_add_ons_input(selected_add_ons)

current_dir = Path.cwd()
requirements_file_path = current_dir / "src/requirements.txt"
pyproject_file_path = current_dir / "pyproject.toml"
pyproject_src_file_path = current_dir / "src/pyproject.toml"

if "1" not in selected_add_ons_list:  # If Linting not selected
    pass
else:
    with open(requirements_file_path, 'a') as file:
        file.write(
            "black\nruff\n")
    with open(pyproject_file_path, 'a') as file:
        pyproject_test_requirements = """
[tool.ruff]
select = [
    "F",  # Pyflakes
    "E",  # Pycodestyle
    "W",  # Pycodestyle
    "UP",  # pyupgrade
    "I",  # isort
    "PL", # Pylint
]
ignore = ["E501"]  # Black take care off line-too-long
"""
        file.write(pyproject_test_requirements)

if "2" not in selected_add_ons_list:  # If Testing not selected
    tests_path = current_dir / "src" / "tests"
    if tests_path.exists():
        shutil.rmtree(str(tests_path))
else:
    with open(requirements_file_path, 'a') as file:
        file.write(
            "pytest-cov~=3.0\npytest-mock>=1.7.1, <2.0\npytest~=7.2")
    with open(pyproject_file_path, 'a') as file:
        pyproject_test_requirements = """
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
        file.write(pyproject_test_requirements)

if "3" not in selected_add_ons_list:  # If Logging not selected
    logging_yml_path = current_dir / "conf/logging.yml"
    if logging_yml_path.exists():
        logging_yml_path.unlink()

if "4" not in selected_add_ons_list:  # If Documentation not selected
    docs_path = current_dir / "docs"
    if docs_path.exists():
        shutil.rmtree(str(docs_path))
else:
    with open(pyproject_src_file_path, 'a') as file:
        pyproject_test_requirements = """
docs = [
    "docutils<0.18.0",
    "sphinx~=3.4.3",
    "sphinx_rtd_theme==0.5.1",
    "nbsphinx==0.8.1",
    "nbstripout~=0.4",
    "sphinx-autodoc-typehints==1.11.1",
    "sphinx_copybutton==0.3.1",
    "ipykernel>=5.3, <7.0",
    "Jinja2<3.1.0",
    "myst-parser~=0.17.2",
]
"""
        file.write(pyproject_test_requirements)

if "5" not in selected_add_ons_list:  # If Data Structure not selected
    data_path = current_dir / "data"
    if data_path.exists():
        shutil.rmtree(str(data_path))

with open(requirements_file_path, 'r') as requirements:
    lines = requirements.readlines()

lines = [line.strip() for line in lines]

lines.sort()

sorted_content = '\n'.join(lines)

with open(requirements_file_path, 'w') as requirements:
    requirements.write(sorted_content)
