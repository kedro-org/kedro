# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module provides metadata for a Kedro project."""

from pathlib import Path
from typing import NamedTuple, Union

import anyconfig

from kedro import __version__ as kedro_version

_PYPROJECT = "pyproject.toml"


class ProjectMetadata(NamedTuple):
    """Structure holding project metadata derived from `pyproject.toml`"""

    config_file: Path
    package_name: str
    project_name: str
    project_path: Path
    project_version: str
    source_dir: Path


def _version_mismatch_error(project_version) -> str:
    return (
        f"Your Kedro project version {project_version} does not match Kedro package "
        f"version {kedro_version} you are running. Make sure to update your project "
        f"template. See https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md "
        f"for how to migrate your Kedro project."
    )


def _is_project(project_path: Union[str, Path]) -> bool:
    metadata_file = Path(project_path).expanduser().resolve() / _PYPROJECT
    if not metadata_file.is_file():
        return False
    try:
        anyconfig.load(metadata_file)
    except Exception:  # pylint: disable=broad-except
        return False
    return True


def _get_project_metadata(project_path: Union[str, Path]) -> ProjectMetadata:
    """Read project metadata from `<project_path>/pyproject.toml` config file,
    under the `[tool.kedro]` section.

    Args:
        project_path: Local path to project root directory to look up `pyproject.toml` in.

    Raises:
        RuntimeError: `pyproject.toml` was not found or the `[tool.kedro]` section
            is missing, or config file cannot be parsed.
        ValueError: If project version is different from Kedro package version.
            Note: Project version is the Kedro version the project was generated with.

    Returns:
        A named tuple that contains project metadata.
    """
    project_path = Path(project_path).expanduser().resolve()
    pyproject_toml = project_path / _PYPROJECT

    if not pyproject_toml.is_file():
        raise RuntimeError(
            f"Could not find the project configuration file '{_PYPROJECT}' in {project_path}. "
            f"If you have created your project with Kedro "
            f"version <0.17.0, make sure to update your project template. "
            f"See https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md"
            f"#migration-guide-from-kedro-016-to-kedro-0170 "
            f"for how to migrate your Kedro project."
        )

    try:
        metadata_dict = anyconfig.load(pyproject_toml)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse '{_PYPROJECT}' file.") from exc

    try:
        metadata_dict = metadata_dict["tool"]["kedro"]
    except KeyError as exc:
        raise RuntimeError(
            f"There's no '[tool.kedro]' section in the '{_PYPROJECT}'. "
            f"Please add '[tool.kedro]' section to the file with appropriate "
            f"configuration parameters."
        ) from exc

    mandatory_keys = ["package_name", "project_name", "project_version"]
    missing_keys = [key for key in mandatory_keys if key not in metadata_dict]
    if missing_keys:
        raise RuntimeError(f"Missing required keys {missing_keys} from '{_PYPROJECT}'.")

    # check the match for major and minor version (skip patch version)
    if metadata_dict["project_version"].split(".")[:2] != kedro_version.split(".")[:2]:
        raise ValueError(_version_mismatch_error(metadata_dict["project_version"]))

    source_dir = Path(metadata_dict.get("source_dir", "src")).expanduser()
    source_dir = (project_path / source_dir).resolve()
    metadata_dict["source_dir"] = source_dir
    metadata_dict["config_file"] = pyproject_toml
    metadata_dict["project_path"] = project_path

    try:
        return ProjectMetadata(**metadata_dict)
    except TypeError as exc:
        expected_keys = mandatory_keys + ["source_dir"]
        raise RuntimeError(
            f"Found unexpected keys in '{_PYPROJECT}'. Make sure "
            f"it only contains the following keys: {expected_keys}."
        ) from exc
