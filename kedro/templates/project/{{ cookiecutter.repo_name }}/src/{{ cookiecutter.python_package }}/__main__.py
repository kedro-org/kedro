"""{{ cookiecutter.project_name }} file for ensuring the package is executable
as `{{ cookiecutter.repo_name }}` and `python -m {{ cookiecutter.python_package }}`
"""
from pathlib import Path

from kedro.framework.cli.project import _find_run_command
from kedro.framework.project import configure_project


def main(*args, **kwargs):
    package_name = Path(__file__).parent.name
    configure_project(package_name)
    run = _find_run_command(package_name)
    run(*args, **kwargs)


if __name__ == "__main__":
    main()
