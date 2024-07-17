"""{{ cookiecutter.project_name }} file for ensuring the package is executable
as `{{ cookiecutter.repo_name }}` and `python -m {{ cookiecutter.python_package }}`
"""
from pathlib import Path

from kedro.framework.project import configure_project, run


def main(*args, **kwargs):
    package_name = Path(__file__).parent.name
    configure_project(package_name)
    run(*args, **kwargs)


if __name__ == "__main__":
    main()
