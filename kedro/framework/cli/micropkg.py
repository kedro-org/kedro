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
    _generate_sdist_file,
    _get_artifacts_to_package,
    _get_default_version,
    _install_files,
    _unpack_sdist,
    _validate_dir,
)
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
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
@click.option("--alias", type=str, default="", help="Rename the package.")
@click.option(
    "-d",
    "--destination",
    type=click.Path(file_okay=False, dir_okay=False),
    default=None,
    help="Module location where to unpack under.",
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
    metadata: ProjectMetadata,
    package_path,
    env,
    alias,
    destination,
    fs_args,
    all_flag,
    **kwargs,
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

    _pull_package(
        package_path,
        metadata,
        env=env,
        alias=alias,
        destination=destination,
        fs_args=fs_args,
    )
    as_alias = f" as `{alias}`" if alias else ""
    message = f"Micro-package {package_path} pulled and unpacked{as_alias}!"
    click.secho(message, fg="green")


# pylint: disable=too-many-arguments, too-many-locals
def _pull_package(
    package_path: str,
    metadata: ProjectMetadata,
    env: str = None,
    alias: str = None,
    destination: str = None,
    fs_args: str = None,
):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()

        _unpack_sdist(package_path, temp_dir_path, fs_args)

        sdist_file_name = Path(package_path).name.rstrip(".tar.gz")
        egg_info_file = list((temp_dir_path / sdist_file_name).glob("*.egg-info"))
        if len(egg_info_file) != 1:
            raise KedroCliError(
                f"More than 1 or no egg-info files found from {package_path}. "
                f"There has to be exactly one egg-info directory."
            )
        package_name = egg_info_file[0].stem
        package_requirements = temp_dir_path / sdist_file_name / "setup.py"

        # Finds a string representation of 'install_requires' list from setup.py
        reqs_list_pattern = r"install_requires\=(.*?)\,\n"
        list_reqs = re.findall(
            reqs_list_pattern, package_requirements.read_text(encoding="utf-8")
        )

        # Finds all elements from the above string representation of a list
        reqs_element_pattern = r"\'(.*?)\'"
        package_reqs = re.findall(reqs_element_pattern, list_reqs[0])

        if package_reqs:
            requirements_txt = metadata.source_dir / "requirements.txt"
            _append_package_reqs(requirements_txt, package_reqs, package_name)

        _clean_pycache(temp_dir_path)
        _install_files(
            metadata,
            package_name,
            temp_dir_path / sdist_file_name,
            env,
            alias,
            destination,
        )


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
            _assert_pkg_name_ok(specs["alias"].split(".")[-1])
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
    help="Location where to create the source distribution file. Defaults to `dist/`.",
)
@click.option(
    "--all",
    "-a",
    "all_flag",
    is_flag=True,
    help="Package all micro-packages in the `pyproject.toml` package manifest section.",
)
@click.argument("module_path", nargs=1, required=False, callback=_check_module_path)
@click.pass_obj  # this will pass the metadata as first argument
def package_pipeline(
    metadata: ProjectMetadata, module_path, env, alias, destination, all_flag
):  # pylint: disable=too-many-arguments
    """Package up a modular pipeline or micro-package as a Python source distribution."""
    if not module_path and not all_flag:
        click.secho(
            "Please specify a micro-package name or add '--all' to package all micro-packages in "
            "the `pyproject.toml` package manifest section."
        )
        sys.exit(1)

    if all_flag:
        _package_pipelines_from_manifest(metadata)
        return

    result_path = _package_pipeline(
        module_path, metadata, alias=alias, destination=destination, env=env
    )

    as_alias = f" as `{alias}`" if alias else ""
    message = (
        f"`{metadata.package_name}.{module_path}` packaged{as_alias}! "
        f"Location: {result_path}"
    )
    click.secho(message, fg="green")


def _package_pipeline(
    pipeline_module_path: str,
    metadata: ProjectMetadata,
    alias: str = None,
    destination: str = None,
    env: str = None,
) -> Path:
    pipeline_name = pipeline_module_path.split(".")[-1]
    package_dir = metadata.source_dir / metadata.package_name
    env = env or "base"

    package_source, package_tests, package_conf = _get_artifacts_to_package(
        metadata, module_path=pipeline_module_path, env=env
    )
    # as the source distribution will only contain parameters, we aren't listing other
    # config files not to confuse users and avoid useless file copies
    configs_to_package = _find_config_files(
        package_conf,
        [f"parameters*/**/{pipeline_name}.yml", f"parameters*/**/{pipeline_name}/**/*"],
    )

    source_paths = (package_source, package_tests, configs_to_package)

    # Check that pipeline directory exists and not empty
    _validate_dir(package_source)

    destination = Path(destination) if destination else metadata.project_path / "dist"
    version = _get_default_version(metadata, pipeline_module_path)

    _generate_sdist_file(
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
