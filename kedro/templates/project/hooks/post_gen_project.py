import json
from pathlib import Path
import shutil


def parse_add_ons_input(add_ons_str):
    """Parse the add-ons input string.

    Args:
        add_ons_str: Input string from prompts.yml.

    Returns:
        list: List of selected add-ons as strings.
    """
    if add_ons_str == "all":
        return ["1", "2", "3", "4", "5"]
    if add_ons_str == "none":
        return []

    # Split by comma
    add_ons_choices = add_ons_str.split(",")
    selected = []

    for choice in add_ons_choices:
        if "-" in choice:
            start, end = choice.split("-")
            selected.extend(str(i) for i in range(int(start), int(end) + 1))
        else:
            selected.append(choice.strip())

    return selected


# Get the selected add-ons from cookiecutter
selected_add_ons = "{{ cookiecutter.add_ons }}"

# Parse the add-ons to get a list
selected_add_ons_list = parse_add_ons_input(selected_add_ons)

current_dir = Path.cwd()
requirements_file_path = current_dir / "src/requirements.txt"
pyproject_file_path = current_dir / "src/pyproject.toml"

if "1" not in selected_add_ons_list:  # If Linting not selected
    setup_cfg_path = current_dir / "setup.cfg"
    if setup_cfg_path.exists():
        setup_cfg_path.unlink()
else:
    with open(requirements_file_path, 'a') as file:
        file.write(
            "black~=22.0\nflake8>=3.7.9, <5.0\nisort~=5.0")

if "2" not in selected_add_ons_list:  # If Testing not selected
    tests_path = current_dir / "tests"
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
    logging_yml_path = current_dir / "logging.yml"
    if logging_yml_path.exists():
        logging_yml_path.unlink()

if "4" not in selected_add_ons_list:  # If Documentation not selected
    docs_path = current_dir / "docs"
    if docs_path.exists():
        shutil.rmtree(str(docs_path))
else:
    with open(pyproject_file_path, 'a') as file:
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

with open (requirements_file_path, 'r') as requirements:
    lines = requirements.readlines()

lines.sort()

with open (requirements_file_path, 'w') as requirements:
    requirements.writelines(lines)
