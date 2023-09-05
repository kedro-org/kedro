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

if "1" not in selected_add_ons_list:  # If Linting not selected
    setup_cfg_path = current_dir / "setup.cfg"
    if setup_cfg_path.exists():
        setup_cfg_path.unlink()
    # TODO ADD CODE TO UPDATE SETUP.PY TO REMOVE LINTING DEPENDENCIES

if "2" not in selected_add_ons_list:  # If Testing not selected
    tests_path = current_dir / "tests"
    if tests_path.exists():
        shutil.rmtree(str(tests_path))
    # TODO ADD CODE TO UPDATE SETUP.PY TO REMOVE TEST DEPENDENCIES

if "3" not in selected_add_ons_list:  # If Logging not selected
    logging_yml_path = current_dir / "logging.yml"
    if logging_yml_path.exists():
        logging_yml_path.unlink()

if "4" not in selected_add_ons_list:  # If Documentation not selected
    docs_path = current_dir / "docs"
    if docs_path.exists():
        shutil.rmtree(str(docs_path))
    # TODO ADD CODE TO UPDATE SETUP.PY TO REMOVE DOCS DEPENDENCIES

if "5" not in selected_add_ons_list:  # If Data Structure not selected
    data_path = current_dir / "data"
    if data_path.exists():
        shutil.rmtree(str(data_path))
