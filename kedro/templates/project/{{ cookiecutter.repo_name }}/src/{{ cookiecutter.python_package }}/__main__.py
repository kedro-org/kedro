"""{{ cookiecutter.project_name }} file for ensuring the package is executable
as `{{ cookiecutter.repo_name }}` and `python -m {{ cookiecutter.python_package }}`
"""
import sys
from pathlib import Path

from kedro.framework.project import configure_project, run


# def main(args=None, **kwargs):
#     package_name = Path(__file__).parent.name
#     configure_project(package_name)
#     run(args or sys.argv[1:], **kwargs)
#     return 0


def main(**kwargs):
    package_name = Path(__file__).parent.name
    configure_project(package_name)
    if kwargs:
        run(**kwargs)
    else:
        run(sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
