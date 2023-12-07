from pathlib import Path
import shutil
import toml

current_dir = Path.cwd()

# Requirements for linting tools
lint_requirements = "black~=22.0\nruff~=0.0.290\n"  # For requirements.txt
lint_pyproject_requirements = ["tool.ruff"]  # For pyproject.toml

# Requirements and configurations for testing tools and coverage reporting
test_requirements = "pytest-cov~=3.0\npytest-mock>=1.7.1, <2.0\npytest~=7.2"  # For requirements.txt
test_pyproject_requirements = ["tool.pytest.ini_options", "tool.coverage.report"]  # For pyproject.toml

# Configuration key for documentation dependencies
docs_pyproject_requirements = ["project.optional-dependencies"]  # For pyproject.toml


# Helper Functions
def _remove_from_file(file_path: Path, content_to_remove: str) -> None:
    """Remove specified content from the file.

    Args:
        file_path (Path): The path of the file from which to remove content.
        content_to_remove (str): The content to be removed from the file.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Split the content to remove into lines and remove trailing whitespaces/newlines
    content_to_remove_lines = [line.strip() for line in content_to_remove.split('\n')]

    # Keep lines that are not in content_to_remove
    lines = [line for line in lines if line.strip() not in content_to_remove_lines]

    with open(file_path, 'w') as file:
        file.writelines(lines)


def _remove_nested_section(data: dict, nested_key: str) -> None:
    """Remove a nested section from a dictionary representing a TOML file.

    Args:
        data (dict): The dictionary from which to remove the section.
        nested_key (str): The dotted path key representing the nested section to remove.
    """
    keys = nested_key.split('.')
    current_data = data
    # Look for Parent section
    for key in keys[:-1]:  # Iterate over all but last element
        if key in current_data:
            current_data = current_data[key]
        else:
            return  # Parent section not found, nothing to remove

    # Remove the nested section and any empty parent sections
    current_data.pop(keys[-1], None)  # Remove last element otherwise return None
    for key in reversed(keys[:-1]):
        parent_section = data
        for key_part in keys[:keys.index(key)]:
            parent_section = parent_section[key_part]
        if not current_data:  # If the section is empty, remove it
            parent_section.pop(key, None)
            current_data = parent_section
        else:
            break  # If the section is not empty, stop removing


def _remove_from_toml(file_path: Path, sections_to_remove: list) -> None:
    """Remove specified sections from a TOML file.

    Args:
        file_path (Path): The path to the TOML file.
        sections_to_remove (list): A list of section keys to remove from the TOML file.
    """
    # Load the TOML file
    with open(file_path, 'r') as file:
        data = toml.load(file)

    # Remove the specified sections
    for section in sections_to_remove:
        _remove_nested_section(data, section)

    with open(file_path, 'w') as file:
        toml.dump(data, file)


def _remove_dir(path: Path) -> None:
    """Remove a directory if it exists.

    Args:
        path (Path): The path of the directory to remove.
    """
    if path.exists():
        shutil.rmtree(str(path))


def _remove_file(path: Path) -> None:
    """Remove a file if it exists.

    Args:
        path (Path): The path of the file to remove.
    """
    if path.exists():
        path.unlink()


def _remove_pyspark_viz_starter_files(is_viz: bool, python_package_name: str) -> None:
    """Clean up the unnecessary files in the starters template.

    Args:
        is_viz (bool): if Viz included in starter, then need to remove "reporting" folder.
        python_package_name (str): The name of the python package.
    """
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
    parameter_file_patterns = ["parameters_*.yml", "parameters/*.yml"]
    for pattern in parameter_file_patterns:
        for param_file in conf_base_path.glob(pattern):
            _remove_file(param_file)

    # Remove the pipelines subdirectories, if Viz - also "reporting" folder
    pipelines_to_remove = ["data_science", "data_processing"] + (["reporting"] if is_viz else [])

    pipelines_path = current_dir / f"src/{python_package_name}/pipelines/"
    for pipeline_subdir in pipelines_to_remove:
        _remove_dir(pipelines_path / pipeline_subdir)

    # Remove all test files from tests/pipelines/
    test_pipeline_path = current_dir / "tests/pipelines/test_data_science.py"
    _remove_file(test_pipeline_path)


def setup_template_tools(selected_tools_list: str, requirements_file_path: str, pyproject_file_path: str, python_package_name: str, example_pipeline: str) -> None:
    """Setup the templates according to the choice of tools.

    Args:
        selected_tools_list (str): A string contains the selected tools.
        requirements_file_path (str): The path of the `requiremenets.txt` in the template.
        pyproject_file_path (str): The path of the `pyproject.toml` in the template
        python_package_name (str): The name of the python package.
        example_pipeline (str): 'True' if example pipeline was selected
    """
    if "Linting" not in selected_tools_list:
        _remove_from_file(requirements_file_path, lint_requirements)
        _remove_from_toml(pyproject_file_path, lint_pyproject_requirements)

    if "Testing" not in selected_tools_list:
        _remove_from_file(requirements_file_path, test_requirements)
        _remove_from_toml(pyproject_file_path, test_pyproject_requirements)
        _remove_dir(current_dir / "tests")

    if "Logging" not in selected_tools_list:
        _remove_file(current_dir / "conf/logging.yml")

    if "Documentation" not in selected_tools_list:
        _remove_from_toml(pyproject_file_path, docs_pyproject_requirements)
        _remove_dir(current_dir / "docs")

    if "Data Structure" not in selected_tools_list and example_pipeline != "True":
        _remove_dir(current_dir / "data")

    if ("PySpark" in selected_tools_list or "Kedro Viz" in selected_tools_list) and example_pipeline != "True":
        _remove_pyspark_viz_starter_files("Kedro Viz" in selected_tools_list, python_package_name)

def sort_requirements(requirements_file_path: Path) -> None:
    """Sort the requirements.txt file alphabetically and write it back to the file.

    Args:
        requirements_file_path (Path): The path to the `requirements.txt` file.
    """
    with open(requirements_file_path, 'r') as requirements:
        lines = requirements.readlines()

    lines = [line.strip() for line in lines]
    lines.sort()
    sorted_content = '\n'.join(lines)

    with open(requirements_file_path, 'w') as requirements:
        requirements.write(sorted_content)
