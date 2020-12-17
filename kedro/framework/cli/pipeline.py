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

"""A collection of CLI commands for working with Kedro pipelines."""
import json
import shutil
import sys
import tempfile
from pathlib import Path
from textwrap import indent
from typing import Any, List, NamedTuple, Optional, Tuple, Union
from zipfile import ZipFile

import click
import yaml
from setuptools.dist import Distribution

import kedro
from kedro.framework.cli.cli import _assert_pkg_name_ok
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    _filter_deprecation_warnings,
    call,
    command_with_verbosity,
    env_option,
    python_call,
)
from kedro.framework.project.settings import _get_project_settings
from kedro.framework.session import KedroSession
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
)
"""

PipelineArtifacts = NamedTuple(
    "PipelineArtifacts",
    [("pipeline_dir", Path), ("pipeline_tests", Path), ("pipeline_conf", Path)],
)


def _check_pipeline_name(ctx, param, value):  # pylint: disable=unused-argument
    if value:
        _assert_pkg_name_ok(value)
    return value


@click.group()
def pipeline():
    """Commands for working with pipelines."""


@command_with_verbosity(pipeline, "create")
@click.argument("name", nargs=1, callback=_check_pipeline_name)
@click.option(
    "--skip-config",
    is_flag=True,
    help="Skip creation of config files for the new pipeline(s).",
)
@env_option(help="Environment to create pipeline configuration in. Defaults to `base`.")
@click.pass_obj  # this will pass the metadata as first argument
def create_pipeline(
    metadata: ProjectMetadata, name, skip_config, env, **kwargs
):  # pylint: disable=unused-argument
    """Create a new modular pipeline by providing the new pipeline name as an argument."""
    package_dir = metadata.source_dir / metadata.package_name
    conf_root = _get_project_settings(metadata.package_name, "CONF_ROOT", "conf")
    project_conf_path = metadata.project_path / conf_root

    env = env or "base"
    if not skip_config and not (project_conf_path / env).exists():
        raise KedroCliError(
            f"Unable to locate environment `{env}`. "
            f"Make sure it exists in the project configuration."
        )

    result_path = _create_pipeline(name, package_dir / "pipelines")
    _copy_pipeline_tests(name, result_path, package_dir)
    _copy_pipeline_configs(result_path, project_conf_path, skip_config, env=env)
    click.secho(f"\nPipeline `{name}` was successfully created.\n", fg="green")

    click.secho(
        f"To be able to run the pipeline `{name}`, you will need to add it "
        f"to `register_pipelines()` in `{package_dir / 'hooks.py'}`.",
        fg="yellow",
    )


@command_with_verbosity(pipeline, "delete")
@click.argument("name", nargs=1, callback=_check_pipeline_name)
@env_option(
    help="Environment to delete pipeline configuration from. Defaults to `base`."
)
@click.option(
    "-y", "--yes", is_flag=True, help="Confirm deletion of pipeline non-interactively."
)
@click.pass_obj  # this will pass the metadata as first argument
def delete_pipeline(
    metadata: ProjectMetadata, name, env, yes, **kwargs
):  # pylint: disable=unused-argument
    """Delete a modular pipeline by providing the pipeline name as an argument."""
    package_dir = metadata.source_dir / metadata.package_name
    conf_root = _get_project_settings(metadata.package_name, "CONF_ROOT", "conf")
    project_conf_path = metadata.project_path / conf_root

    env = env or "base"
    if not (project_conf_path / env).exists():
        raise KedroCliError(
            f"Unable to locate environment `{env}`. "
            f"Make sure it exists in the project configuration."
        )

    pipeline_artifacts = _get_pipeline_artifacts(metadata, pipeline_name=name, env=env)

    files_to_delete = [
        pipeline_artifacts.pipeline_conf / confdir / f"{name}.yml"
        for confdir in ("parameters", "catalog")
        if (pipeline_artifacts.pipeline_conf / confdir / f"{name}.yml").is_file()
    ]
    dirs_to_delete = [
        path
        for path in (pipeline_artifacts.pipeline_dir, pipeline_artifacts.pipeline_tests)
        if path.is_dir()
    ]

    if not files_to_delete and not dirs_to_delete:
        raise KedroCliError(f"Pipeline `{name}` not found.")

    if not yes:
        _echo_deletion_warning(
            "The following paths will be removed:",
            directories=dirs_to_delete,
            files=files_to_delete,
        )
        click.echo()
        yes = click.confirm(f"Are you sure you want to delete pipeline `{name}`?")
        click.echo()

    if not yes:
        raise KedroCliError("Deletion aborted!")

    _delete_artifacts(*files_to_delete, *dirs_to_delete)
    click.secho(f"\nPipeline `{name}` was successfully deleted.", fg="green")
    click.secho(
        f"\nIf you added the pipeline `{name}` to `register_pipelines()` in "
        f"`{package_dir / 'hooks.py'}`, you will need to remove it.",
        fg="yellow",
    )


@pipeline.command("list")
@env_option
@click.pass_obj
def list_pipelines(metadata: ProjectMetadata, env):
    """List all pipelines defined in your hooks.py file."""
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()
    project_pipelines = context.pipelines
    click.echo(yaml.dump(sorted(project_pipelines)))


@command_with_verbosity(pipeline, "describe")
@env_option
@click.argument("name", nargs=1)
@click.pass_obj
def describe_pipeline(
    metadata: ProjectMetadata, name, env, **kwargs
):  # pylint: disable=unused-argument
    """Describe a pipeline by providing the pipeline name as an argument."""
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()
    pipeline_obj = context.pipelines.get(name)
    if not pipeline_obj:
        existing_pipelines = ", ".join(sorted(context.pipelines.keys()))
        raise KedroCliError(
            f"`{name}` pipeline not found. Existing pipelines: [{existing_pipelines}]"
        )

    result = {
        "Nodes": [
            f"{node.short_name} ({node._func_name})"  # pylint: disable=protected-access
            for node in pipeline_obj.nodes
        ]
    }

    click.echo(yaml.dump(result))


@command_with_verbosity(pipeline, "pull")
@click.argument("package_path", nargs=1)
@env_option(
    help="Environment to install the pipeline configuration to. Defaults to `base`."
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
def pull_package(
    metadata: ProjectMetadata, package_path, env, alias, fs_args, **kwargs
):  # pylint:disable=unused-argument
    """Pull a modular pipeline package, unpack it and install the files to corresponding
    locations.
    """

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

        _clean_pycache(temp_dir_path)
        _install_files(metadata, package_name, temp_dir_path, env, alias)


def _get_fsspec_filesystem(location: str, fs_args: Optional[str]):
    # pylint: disable=import-outside-toplevel
    import anyconfig
    import fsspec

    from kedro.io.core import get_protocol_and_path

    protocol, _ = get_protocol_and_path(location)
    fs_args_config = anyconfig.load(fs_args) if fs_args else {}

    return fsspec.filesystem(protocol, **fs_args_config)


@pipeline.command("package")
@env_option(
    help="Environment where the pipeline configuration lives. Defaults to `base`."
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
    help="Location where to create the wheel file. Defaults to `src/dist`.",
)
@click.option(
    "-v",
    "--version",
    type=str,
    default="0.1",
    show_default=True,
    help="Version to package under.",
)
@click.argument("name", nargs=1)
@click.pass_obj  # this will pass the metadata as first argument
def package_pipeline(
    metadata: ProjectMetadata, name, env, alias, destination, version
):  # pylint: disable=too-many-arguments
    """Package up a pipeline for easy distribution. A .whl file
    will be created in a `<source_dir>/dist/`."""
    result_path = _package_pipeline(
        name, metadata, alias=alias, destination=destination, env=env, version=version,
    )

    as_alias = f" as `{alias}`" if alias else ""
    message = f"Pipeline `{name}` packaged{as_alias}! Location: {result_path}"
    click.secho(message, fg="green")


def _echo_deletion_warning(message: str, **paths: List[Path]):
    paths = {key: values for key, values in paths.items() if values}

    if paths:
        click.secho(message, bold=True)

    for key, values in paths.items():
        click.echo(f"\n{key.capitalize()}:")
        paths_str = "\n".join(str(value) for value in values)
        click.echo(indent(paths_str, " " * 2))


def _unpack_wheel(location: str, destination: Path, fs_args: Optional[str]) -> None:
    filesystem = _get_fsspec_filesystem(location, fs_args)

    if location.endswith(".whl") and filesystem.exists(location):
        with filesystem.open(location) as fs_file:
            ZipFile(fs_file).extractall(destination)
    else:
        python_call(
            "pip", ["download", "--no-deps", "--dest", str(destination), location],
        )
        wheel_file = list(destination.glob("*.whl"))
        # `--no-deps` should fetch only one wheel file, and CLI should fail if that's
        # not the case.
        if len(wheel_file) != 1:
            file_names = [wf.name for wf in wheel_file]
            raise KedroCliError(
                f"More than 1 or no wheel files found: {file_names}. "
                f"There has to be exactly one distribution file."
            )
        ZipFile(wheel_file[0]).extractall(destination)


def _create_session(package_name: str, **kwargs):
    kwargs.setdefault("save_on_close", False)
    try:
        return KedroSession.create(package_name, **kwargs)
    except Exception as exc:
        raise KedroCliError(
            f"Unable to instantiate Kedro session.\nError: {exc}"
        ) from exc


def _rename_files(conf_source: Path, old_name: str, new_name: str):
    config_files_to_rename = (
        each
        for each in conf_source.rglob("*")
        if each.is_file() and old_name in each.name
    )
    for config_file in config_files_to_rename:
        new_config_name = config_file.name.replace(old_name, new_name)
        config_file.rename(config_file.parent / new_config_name)


def _install_files(
    project_metadata: ProjectMetadata,
    package_name: str,
    source_path: Path,
    env: str = None,
    alias: str = None,
):
    env = env or "base"

    package_source, test_source, conf_source = _get_package_artifacts(
        source_path, package_name
    )

    if conf_source.is_dir() and alias:
        _rename_files(conf_source, package_name, alias)

    pipeline_name = alias or package_name
    package_dest, test_dest, conf_dest = _get_pipeline_artifacts(
        project_metadata, pipeline_name=pipeline_name, env=env
    )

    if conf_source.is_dir():
        _sync_dirs(conf_source, conf_dest)
        # `config` dir was packaged under `package_name` directory with
        # `kedro pipeline package`. Since `config` was already synced,
        # we don't want to copy it again when syncing the package, so we remove it.
        shutil.rmtree(str(conf_source))

    if test_source.is_dir():
        _sync_dirs(test_source, test_dest)

    # Sync everything under package directory, except `config`
    # since it has already been copied.
    if package_source.is_dir():
        _sync_dirs(package_source, package_dest)


def _find_config_files(
    source_config_dir: Path, glob_pattern: str
) -> List[Tuple[Path, str]]:
    config_files = []  # type: List[Tuple[Path, str]]

    if source_config_dir.is_dir():
        config_files = [
            (path, path.parent.relative_to(source_config_dir).as_posix())
            for path in source_config_dir.glob(glob_pattern)
            if path.is_file()
        ]

    return config_files


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
    version = version or "0.1"

    artifacts_to_package = _get_pipeline_artifacts(
        metadata, pipeline_name=pipeline_name, env=env
    )
    # as the wheel file will only contain parameters, we aren't listing other
    # config files not to confused users and avoid useless file copies
    configs_to_package = _find_config_files(
        artifacts_to_package.pipeline_conf, f"parameters*/**/*{pipeline_name}*"
    )
    source_paths = (
        artifacts_to_package.pipeline_dir,
        artifacts_to_package.pipeline_tests,
        configs_to_package,
    )

    # Check that pipeline directory exists and not empty
    _validate_dir(artifacts_to_package.pipeline_dir)
    destination = Path(destination) if destination else package_dir.parent / "dist"

    _generate_wheel_file(pipeline_name, destination, source_paths, version, alias=alias)

    _clean_pycache(package_dir)
    _clean_pycache(metadata.project_path)

    return destination


def _validate_dir(path: Path) -> None:
    if not path.is_dir():
        raise KedroCliError(f"Directory '{path}' doesn't exist.")
    if not list(path.iterdir()):
        raise KedroCliError(f"'{path}' is an empty directory.")


def _get_wheel_name(**kwargs: Any) -> str:
    # https://stackoverflow.com/q/51939257/3364156
    dist = Distribution(attrs=kwargs)
    bdist_wheel_cmd = dist.get_command_obj("bdist_wheel")
    bdist_wheel_cmd.ensure_finalized()

    distname = bdist_wheel_cmd.wheel_dist_name
    tag = "-".join(bdist_wheel_cmd.get_tag())
    return f"{distname}-{tag}.whl"


def _sync_path_list(source: List[Tuple[Path, str]], target: Path) -> None:
    for source_path, suffix in source:
        target_with_suffix = (target / suffix).resolve()
        _sync_dirs(source_path, target_with_suffix)


_SourcePathType = Union[Path, List[Tuple[Path, str]]]


def _generate_wheel_file(
    pipeline_name: str,
    destination: Path,
    source_paths: Tuple[_SourcePathType, ...],
    version: str,
    alias: str = None,
) -> None:
    package_name = alias or pipeline_name

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()

        # Copy source folders
        target_paths = _get_package_artifacts(temp_dir_path, package_name)
        for source, target in zip(source_paths, target_paths):
            sync_func = _sync_path_list if isinstance(source, list) else _sync_dirs
            sync_func(source, target)  # type: ignore

        conf_target = target_paths[-1]
        if conf_target.is_dir() and alias:
            _rename_files(conf_target, pipeline_name, alias)

        # Build a setup.py on the fly
        setup_file = _generate_setup_file(package_name, version, temp_dir_path)

        package_file = destination / _get_wheel_name(name=package_name, version=version)
        if package_file.is_file():
            click.secho(
                f"Package file {package_file} will be overwritten!", fg="yellow"
            )

        # python setup.py bdist_wheel --dist-dir <destination>
        call(
            [
                sys.executable,
                str(setup_file.resolve()),
                "bdist_wheel",
                "--dist-dir",
                str(destination),
            ],
            cwd=temp_dir,
        )


def _generate_setup_file(package_name: str, version: str, output_dir: Path) -> Path:
    setup_file = output_dir / "setup.py"
    package_data = {
        package_name: [
            "README.md",
            "config/parameters*",
            "config/**/parameters*",
            "config/parameters*/**",
        ]
    }
    setup_file_context = dict(
        name=package_name, version=version, package_data=json.dumps(package_data)
    )
    setup_file.write_text(_SETUP_PY_TEMPLATE.format(**setup_file_context))
    return setup_file


def _create_pipeline(name: str, output_dir: Path) -> Path:
    with _filter_deprecation_warnings():
        # pylint: disable=import-outside-toplevel
        from cookiecutter.main import cookiecutter

    template_path = Path(kedro.__file__).parent / "templates" / "pipeline"
    cookie_context = {"pipeline_name": name, "kedro_version": kedro.__version__}

    click.echo(f"Creating the pipeline `{name}`: ", nl=False)

    try:
        result_path = cookiecutter(
            str(template_path),
            output_dir=str(output_dir),
            no_input=True,
            extra_context=cookie_context,
        )
    except Exception as exc:
        click.secho("FAILED", fg="red")
        cls = exc.__class__
        raise KedroCliError(f"{cls.__module__}.{cls.__qualname__}: {exc}") from exc

    click.secho("OK", fg="green")
    result_path = Path(result_path)
    message = indent(f"Location: `{result_path.resolve()}`", " " * 2)
    click.secho(message, bold=True)

    _clean_pycache(result_path)

    return result_path


# pylint: disable=missing-raises-doc
def _sync_dirs(source: Path, target: Path, prefix: str = ""):
    """Recursively copies `source` directory (or file) into `target` directory without
    overwriting any existing files/directories in the target using the following
    rules:
        1) Skip any files/directories which names match with files in target.
        2) Copy all files from source to target.
        3) Recursively copy all directories from source to target.

    Args:
        source: A local directory to copy from, must exist.
        target: A local directory to copy to, will be created if doesn't exist yet.
        prefix: Prefix for CLI message indentation.
    """

    existing = list(target.iterdir()) if target.is_dir() else []
    existing_files = {f.name for f in existing if f.is_file()}
    existing_folders = {f.name for f in existing if f.is_dir()}

    if source.is_dir():
        content = list(source.iterdir())
    elif source.is_file():
        content = [source]
    else:
        content = []  # nothing to copy

    for source_path in content:
        source_name = source_path.name
        target_path = target / source_name
        click.echo(indent(f"Creating `{target_path}`: ", prefix), nl=False)

        if (  # rule #1
            source_name in existing_files
            or source_path.is_file()
            and source_name in existing_folders
        ):
            click.secho("SKIPPED (already exists)", fg="yellow")
        elif source_path.is_file():  # rule #2
            try:
                target.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(str(source_path), str(target_path))
            except Exception:
                click.secho("FAILED", fg="red")
                raise
            click.secho("OK", fg="green")
        else:  # source_path is a directory, rule #3
            click.echo()
            new_prefix = (prefix or "") + " " * 2
            _sync_dirs(source_path, target_path, prefix=new_prefix)


def _get_pipeline_artifacts(
    project_metadata: ProjectMetadata, pipeline_name: str, env: str
) -> PipelineArtifacts:
    """From existing project, returns in order: source_path, tests_path, config_paths"""
    package_dir = project_metadata.source_dir / project_metadata.package_name
    conf_root = _get_project_settings(
        project_metadata.package_name, "CONF_ROOT", "conf"
    )
    project_conf_path = project_metadata.project_path / conf_root
    artifacts = PipelineArtifacts(
        package_dir / "pipelines" / pipeline_name,
        package_dir.parent / "tests" / "pipelines" / pipeline_name,
        project_conf_path / env,
    )
    return artifacts


def _get_package_artifacts(
    source_path: Path, package_name: str
) -> Tuple[Path, Path, Path]:
    """From existing unpacked wheel, returns in order:
    source_path, tests_path, config_path
    """
    artifacts = (
        source_path / package_name,
        source_path / "tests",
        # package_data (non-python files) needs to live inside one of the packages
        source_path / package_name / "config",
    )
    return artifacts


def _copy_pipeline_tests(pipeline_name: str, result_path: Path, package_dir: Path):
    tests_source = result_path / "tests"
    tests_target = package_dir.parent / "tests" / "pipelines" / pipeline_name
    try:
        _sync_dirs(tests_source, tests_target)
    finally:
        shutil.rmtree(tests_source)


def _copy_pipeline_configs(
    result_path: Path, conf_path: Path, skip_config: bool, env: str
):
    config_source = result_path / "config"
    try:
        if not skip_config:
            config_target = conf_path / env
            _sync_dirs(config_source, config_target)
    finally:
        shutil.rmtree(config_source)


def _delete_artifacts(*artifacts: Path):
    for artifact in artifacts:
        click.echo(f"Deleting `{artifact}`: ", nl=False)
        try:
            if artifact.is_dir():
                shutil.rmtree(artifact)
            else:
                artifact.unlink()
        except Exception as exc:
            click.secho("FAILED", fg="red")
            cls = exc.__class__
            raise KedroCliError(f"{cls.__module__}.{cls.__qualname__}: {exc}") from exc
        else:
            click.secho("OK", fg="green")
