from pathlib import Path
import shutil

current_dir = Path.cwd()

lint_requirements = "black\nruff\n"
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
ignore = ["E501"]  # Black take care off line-too-long
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


def setup_template_add_ons(selected_add_ons_list, requirements_file_path, pyproject_file_path, pyproject_src_file_path):
    """Removes directories and files related to unwanted addons from
    a Kedro project template. Adds the necessary requirements for
    the addons that were selected.

    Args:
        selected_add_ons_list: a list containing numbers from 1 to 5,
        representing specific add-ons.
        requirements_file_path: the path to the requirements.txt file.
        pyproject_file_path: the path to the pyproject.toml file
        located on the the root of the template.
        pyproject_src_file_path: the path to the pyproject.toml file
        located inside the `src` directory.
    """
    if "1" not in selected_add_ons_list:  # If Linting not selected
        pass
    else:
        with open(requirements_file_path, 'a') as file:
            file.write(lint_requirements)
        with open(pyproject_file_path, 'a') as file:
            file.write(lint_pyproject_requirements)

    if "2" not in selected_add_ons_list:  # If Testing not selected
        tests_path = current_dir / "src" / "tests"
        if tests_path.exists():
            shutil.rmtree(str(tests_path))
    else:
        with open(requirements_file_path, 'a') as file:
            file.write(test_requirements)
        with open(pyproject_file_path, 'a') as file:
            file.write(test_pyproject_requirements)

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
            file.write(docs_pyproject_requirements)

    if "5" not in selected_add_ons_list:  # If Data Structure not selected
        data_path = current_dir / "data"
        if data_path.exists():
            shutil.rmtree(str(data_path))


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

