import json
import os
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
    parts = add_ons_str.split(",")
    selected = []

    for part in parts:
        if "-" in part:
            start, end = part.split("-")
            selected.extend(str(i) for i in range(int(start), int(end) + 1))
        else:
            selected.append(part.strip())

    return selected


# Get the selected add-ons from cookiecutter
selected_add_ons = "{{ cookiecutter.add_ons }}"

# Parse the add-ons to get a list
selected_add_ons_list = parse_add_ons_input(selected_add_ons)

if "1" not in selected_add_ons_list:  # If Linting not selected
    setup_cfg_path = os.path.join(os.getcwd(), "setup.cfg")
    if os.path.exists(setup_cfg_path):
        os.remove(os.path.join(os.getcwd(), "setup.cfg"))
    # TODO ADD CODE TO UPDATE SETUP.PY TO REMOVE LINTING DEPENDENCIES

if "2" not in selected_add_ons_list:  # If Testing not selected
    tests_path = os.path.join(os.getcwd(), "tests")
    if os.path.exists(tests_path):
        shutil.rmtree(os.path.join(os.getcwd(), "tests"))
    # TODO ADD CODE TO UPDATE SETUP.PY TO REMOVE TEST DEPENDENCIES

if "3" not in selected_add_ons_list:  # If Logging not selected
    logging_yml_path = os.path.join(os.getcwd(), "logging.yml")
    if os.path.exists(logging_yml_path):
        os.remove(os.path.join(os.getcwd(), "logging.yml"))

if "4" not in selected_add_ons_list:  # If Documentation not selected
    docs_path = os.path.join(os.getcwd(), "docs")
    if os.path.exists(docs_path):
        shutil.rmtree(os.path.join(os.getcwd(), "docs"))
    # TODO ADD CODE TO UPDATE SETUP.PY TO REMOVE DOCS DEPENDENCIES

if "5" not in selected_add_ons_list:  # If Data Structure not selected
    data_path = os.path.join(os.getcwd(), "data")
    if os.path.exists(data_path):
        shutil.rmtree(os.path.join(os.getcwd(), "data"))
