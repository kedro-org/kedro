import os
import re
import requests
from pathlib import Path

VERSION_MATCHSTR = r'\s*__version__\s*=\s*"(\d+\.\d+\.\d+)"'
INIT_FILE_PATH = "kedro/kedro/__init__.py"


def get_package_version():
    init_file_path = Path(INIT_FILE_PATH)
    match_obj = re.search(VERSION_MATCHSTR, init_file_path.read_text())
    if match_obj:
        return match_obj.group(1)


def check_no_version_pypi(kedro_version):
    pypi_endpoint = f"https://pypi.org/pypi/kedro/{kedro_version}/json/"
    print(f"Check if Kedro {kedro_version} is on PyPI")
    response = requests.get(pypi_endpoint, timeout=10)
    if response.status_code == 404:
        print(f"Starting the release of Kedro {kedro_version}")
        return True
    else:
        print(f"Skipped: Kedro {kedro_version} already exists on PyPI")
        return False


if __name__ == "__main__":
    kedro_version = get_package_version()
    new_release = check_no_version_pypi(kedro_version)

    env_file = os.getenv('GITHUB_ENV')
    with open(env_file, "a") as file:
        file.write(f"NEW_RELEASE={'true' if new_release else 'false'}\n")
        if new_release:
            file.write(f"KEDRO_VERSION={kedro_version}\n")
