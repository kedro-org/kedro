from pathlib import Path

from kedro.templates.project.hooks.utils import (

    setup_template_tools,
    sort_requirements,
)


def main():
    current_dir = Path.cwd()
    requirements_file_path = current_dir / "requirements.txt"
    pyproject_file_path = current_dir / "pyproject.toml"
    python_package_name = '{{ cookiecutter.python_package }}'

    # Get the selected tools from cookiecutter
    selected_tools = "{{ cookiecutter.tools }}"
    example_pipeline = "{{ cookiecutter.example_pipeline }}"

    # Handle template directories and requirements according to selected tools
    setup_template_tools(selected_tools, requirements_file_path, pyproject_file_path, python_package_name, example_pipeline)

    # Sort requirements.txt file in alphabetical order
    sort_requirements(requirements_file_path)

if __name__ == "__main__":
    main()
