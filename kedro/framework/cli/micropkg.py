"""A collection of CLI commands for working with Kedro micro-packages."""

import re
import sys
import tempfile
from pathlib import Path

import click

from kedro.framework.cli.pipeline import (
    _append_package_reqs,
    _assert_pkg_name_ok,
    _check_module_path,
    _check_pipeline_name,
    _find_config_files,
    _generate_wheel_file,
    _get_default_version,
    _get_pipeline_artifacts,
    _install_files,
    _unpack_wheel,
    _validate_dir,
)
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    _get_requirements_in,
    command_with_verbosity,
    env_option,
)
from kedro.framework.startup import ProjectMetadata

_SETUP_PY_TEMPLATE = """# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="{name}",
    version="{version}",
    description="Modular pipeline `{name}`",
    packages=find_packages(),
    include_package_data=True,
    package_data={package_data},
    install_requires={install_requires},
)
"""


# pylint: disable=missing-function-docstring
@click.group(name="Kedro")
def micropkg_cli():  # pragma: no cover
    pass


@micropkg_cli.group()
def micropkg():
    """Commands for working with micro-packages."""


@command_with_verbosity(micropkg, "pull")
@click.argument("package_path", nargs=1, required=False)
@click.option(
    "--all",
    "-a",
    "all_flag",
    is_flag=True,
    help="Pull and unpack all micro-packages in the `pyproject.toml` package manifest section.",
)
@env_option(
    help="Environment to install the micro-package configuration to. Defaults to `base`."
)
@click.option(
    "--alias",
    type=str,
    default="",
    callback=_check_pipeline_name,
    help="Alternative name to unpackage under.",
)
@click.option(
    "--fs-args",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True
    ),
    default=None,
    help="Location of a configuration file for the fsspec filesystem used to pull the package.",
)
@click.pass_obj  # this will pass the metadata as first argument
def pull_package(  # pylint:disable=unused-argument, too-many-arguments
    metadata: ProjectMetadata, package_path, env, alias, fs_args, all_flag, **kwargs
) -> None:
    """Pull and unpack a modular pipeline and other micro-packages in your project."""
    if not package_path and not all_flag:
        click.secho(
            "Please specify a package path or add '--all' to pull all micro-packages in the "
            "`pyproject.toml` package manifest section."
        )
        sys.exit(1)

    if all_flag:
        _pull_packages_from_manifest(metadata)
        return

    _pull_package(package_path, metadata, env=env, alias=alias, fs_args=fs_args)
    as_alias = f" as `{alias}`" if alias else ""
    message = f"Micro-package {package_path} pulled and unpacked{as_alias}!"
    click.secho(message, fg="green")


def _pull_package(
    package_path: str,
    metadata: ProjectMetadata,
    env: str = None,
    alias: str = None,
    fs_args: str = None,
):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()

        _unpack_wheel(package_path, temp_dir_path, fs_args)

        dist_info_file = list(temp_dir_path.glob("*.dist-info"))
        if len(dist_info_file) != 1:
            raise KedroCliError(
                f"More than 1 or no dist-info files found from {package_path}. "
                f"There has to be exactly one dist-info directory."
            )
        # Extract package name, based on the naming convention for wheel files
        # https://www.python.org/dev/peps/pep-0427/#file-name-convention
        package_name = dist_info_file[0].stem.split("-")[0]
        package_metadata = dist_info_file[0] / "METADATA"

        req_pattern = r"Requires-Dist: (.*?)\n"
        package_reqs = re.findall(req_pattern, package_metadata.read_text())
        if package_reqs:
            requirements_in = _get_requirements_in(
                metadata.source_dir, create_empty=True
            )
            _append_package_reqs(requirements_in, package_reqs, package_name)

        _clean_pycache(temp_dir_path)
        _install_files(metadata, package_name, temp_dir_path, env, alias)


def _pull_packages_from_manifest(metadata: ProjectMetadata) -> None:
    # pylint: disable=import-outside-toplevel
    import anyconfig  # for performance reasons

    config_dict = anyconfig.load(metadata.config_file)
    config_dict = config_dict["tool"]["kedro"]
    build_specs = config_dict.get("micropkg", {}).get("pull")

    if not build_specs:
        click.secho(
            "Nothing to pull. Please update the `pyproject.toml` package manifest section.",
            fg="yellow",
        )
        return

    for package_path, specs in build_specs.items():
        if "alias" in specs:
            _assert_pkg_name_ok(specs["alias"])
        _pull_package(package_path, metadata, **specs)
        click.secho(f"Pulled and unpacked `{package_path}`!")

    click.secho("Micro-packages pulled and unpacked!", fg="green")


def _package_pipelines_from_manifest(metadata: ProjectMetadata) -> None:
    # pylint: disable=import-outside-toplevel
    import anyconfig  # for performance reasons

    config_dict = anyconfig.load(metadata.config_file)
    config_dict = config_dict["tool"]["kedro"]
    build_specs = config_dict.get("micropkg", {}).get("package")

    if not build_specs:
        click.secho(
            "Nothing to package. Please update the `pyproject.toml` package manifest section.",
            fg="yellow",
        )
        return

    for pipeline_name, specs in build_specs.items():
        if "alias" in specs:
            _assert_pkg_name_ok(specs["alias"])
        _package_pipeline(pipeline_name, metadata, **specs)
        click.secho(f"Packaged `{pipeline_name}` micro-package!")

    click.secho("Micro-packages packaged!", fg="green")


@micropkg.command("package")
@env_option(
    help="Environment where the micro-package configuration lives. Defaults to `base`."
)
@click.option(
    "--alias",
    type=str,
    default="",
    callback=_check_pipeline_name,
    help="Alternative name to package under.",
)
@click.option(
    "-d",
    "--destination",
    type=click.Path(resolve_path=True, file_okay=False),
    help="Location where to create the wheel file. Defaults to `dist/`.",
)
@click.option(
    "-v",
    "--version",
    type=str,
    help="Version to package under. "
    "Defaults to micro-package package version or, "
    "if that is not defined, the project package version.",
)
@click.option(
    "--all",
    "-a",
    "all_flag",
    is_flag=True,
    help="Package all micro-packages in the `pyproject.toml` package manifest section.",
)
@click.argument("name", nargs=1, required=False, callback=_check_module_path)
@click.pass_obj  # this will pass the metadata as first argument
def package_pipeline(
    metadata: ProjectMetadata, name, env, alias, destination, version, all_flag
):  # pylint: disable=too-many-arguments
    """Package up a modular pipeline or micro-package as a Python .whl."""
    if not name and not all_flag:
        click.secho(
            "Please specify a micro-package name or add '--all' to package all micro-packages in "
            "the `pyproject.toml` package manifest section."
        )
        sys.exit(1)

    if all_flag:
        _package_pipelines_from_manifest(metadata)
        return

    result_path = _package_pipeline(
        name, metadata, alias=alias, destination=destination, env=env, version=version
    )

    as_alias = f" as `{alias}`" if alias else ""
    message = f"Micro-package `{name}` packaged{as_alias}! Location: {result_path}"
    click.secho(message, fg="green")


def _package_pipeline(  # pylint: disable=too-many-arguments
    pipeline_name: str,
    metadata: ProjectMetadata,
    alias: str = None,
    destination: str = None,
    env: str = None,
    version: str = None,
) -> Path:
    package_dir = metadata.source_dir / metadata.package_name
    env = env or "base"

    artifacts_to_package = _get_pipeline_artifacts(
        metadata, pipeline_name=pipeline_name, env=env
    )
    # as the wheel file will only contain parameters, we aren't listing other
    # config files not to confuse users and avoid useless file copies
    configs_to_package = _find_config_files(
        artifacts_to_package.pipeline_conf,
        [f"parameters*/**/{pipeline_name}.yml", f"parameters*/**/{pipeline_name}/**/*"],
    )

    source_paths = (
        artifacts_to_package.pipeline_dir,
        artifacts_to_package.pipeline_tests,
        configs_to_package,
    )

    # Check that pipeline directory exists and not empty
    _validate_dir(artifacts_to_package.pipeline_dir)

    destination = Path(destination) if destination else metadata.project_path / "dist"
    version = version or _get_default_version(metadata, pipeline_name)

    _generate_wheel_file(
        pipeline_name=pipeline_name,
        destination=destination.resolve(),
        source_paths=source_paths,
        version=version,
        metadata=metadata,
        alias=alias,
    )

    _clean_pycache(package_dir)
    _clean_pycache(metadata.project_path)

    return destination
