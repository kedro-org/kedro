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
from importlib import import_module
from pathlib import Path
from textwrap import indent
from typing import NamedTuple, Tuple
from zipfile import ZipFile

import click
import yaml
from setuptools.dist import Distribution

import kedro
from kedro.framework.cli.cli import _assert_pkg_name_ok, _handle_exception
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    _filter_deprecation_warnings,
    call,
    env_option,
    python_call,
)
from kedro.framework.context import KedroContext, load_context

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


@click.group()
def pipeline():
    """Commands for working with pipelines."""


def _check_pipeline_name(ctx, param, value):  # pylint: disable=unused-argument
    if value:
        _assert_pkg_name_ok(value)
    return value


@pipeline.command("create")
@click.argument("name", nargs=1, callback=_check_pipeline_name)
@click.option(
    "--skip-config",
    is_flag=True,
    help="Skip creation of config files for the new pipeline(s).",
)
@env_option(help="Environment to create pipeline configuration in. Defaults to `base`.")
def create_pipeline(name, skip_config, env):
    """Create a new modular pipeline by providing the new pipeline name as an argument."""
    try:
        context = load_context(Path.cwd(), env=env)
    except Exception as err:  # pylint: disable=broad-except
        _handle_exception(
            f"Unable to load Kedro context with environment `{env}`. "
            f"Make sure it exists in the project configuration.\nError: {err}"
        )

    package_dir = _get_project_package_dir(context)
    output_dir = package_dir / "pipelines"

    result_path = _create_pipeline(name, context.project_version, output_dir)
    _copy_pipeline_tests(name, result_path, package_dir)
    _copy_pipeline_configs(name, result_path, context, skip_config, env=env)
    click.secho(f"\nPipeline `{name}` was successfully created.\n", fg="green")

    click.secho(
        f"To be able to run the pipeline `{name}`, you will need to add it "
        f"to `register_pipelines()` in `{package_dir / 'hooks.py'}`.",
        fg="yellow",
    )


@pipeline.command("delete")
@click.argument("name", nargs=1, callback=_check_pipeline_name)
@env_option(
    help="Environment to delete pipeline configuration from. Defaults to `base`."
)
@click.option(
    "-y", "--yes", is_flag=True, help="Confirm deletion of pipeline non-interactively."
)
def delete_pipeline(name, env, yes):
    """Delete a modular pipeline by providing the pipeline name as an argument."""
    try:
        context = load_context(Path.cwd(), env=env)
    except Exception as err:  # pylint: disable=broad-except
        _handle_exception(
            f"Unable to load Kedro context with environment `{env}`. "
            f"Make sure it exists in the project configuration.\nError: {err}"
        )

    package_dir = _get_project_package_dir(context)

    env = env or "base"
    pipeline_artifacts = _get_pipeline_artifacts(context, pipeline_name=name, env=env)
    dirs = [path for path in pipeline_artifacts if path.is_dir()]

    if not yes:
        click.echo(
            "The following directories and everything within them will be removed:\n"
        )
        click.echo(indent("\n".join(str(dir_) for dir_ in dirs), " " * 2))
        click.echo()
        yes = click.confirm(f"Are you sure you want to delete pipeline `{name}`?")
        click.echo()

    if not yes:
        raise KedroCliError("Deletion aborted!")

    _delete_dirs(*dirs)
    click.secho(f"\nPipeline `{name}` was successfully deleted.\n", fg="green")
    click.secho(
        f"If you added the pipeline `{name}` to `register_pipelines()` in "
        f"`{package_dir / 'hooks.py'}`, you will need to remove it.`",
        fg="yellow",
    )


@pipeline.command("list")
@env_option
def list_pipelines(env):
    """List all pipelines defined in your hooks.py file."""
    context = load_context(Path.cwd(), env=env)
    project_pipelines = context.pipelines
    click.echo(yaml.dump(sorted(project_pipelines)))


@pipeline.command("describe")
@env_option
@click.argument("name", nargs=1)
def describe_pipeline(name, env):
    """Describe a pipeline by providing the pipeline name as an argument."""
    context = load_context(Path.cwd(), env=env)
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


@pipeline.command("pull")
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
def pull_package(package_path, env, alias):
    """Pull a modular pipeline package, unpack it and install the files to corresponding
    locations.
    """
    # pylint: disable=import-outside-toplevel
    import fsspec

    from kedro.io.core import get_protocol_and_path

    protocol, _ = get_protocol_and_path(package_path)
    filesystem = fsspec.filesystem(protocol)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()
        if package_path.endswith(".whl") and filesystem.exists(package_path):
            with filesystem.open(package_path) as fs_file:
                ZipFile(fs_file).extractall(temp_dir_path)
        else:
            python_call(
                "pip",
                ["download", "--no-deps", "--dest", str(temp_dir_path), package_path],
            )
            wheel_file = list(temp_dir_path.glob("*.whl"))
            # `--no-deps` should fetch only one wheel file, and CLI should fail if that's
            # not the case.
            if len(wheel_file) != 1:
                file_names = [wf.name for wf in wheel_file]
                raise KedroCliError(
                    f"More than 1 or no wheel files found: {str(file_names)}. "
                    "There has to be exactly one distribution file."
                )
            ZipFile(wheel_file[0]).extractall(temp_dir_path)

        dist_info_file = list(temp_dir_path.glob("*.dist-info"))
        if len(dist_info_file) != 1:
            raise KedroCliError(
                f"More than 1 or no dist-info files found from {package_path}. "
                "There has to be exactly one dist-info directory."
            )
        # Extract package name, based on the naming convention for wheel files
        # https://www.python.org/dev/peps/pep-0427/#file-name-convention
        package_name = dist_info_file[0].stem.split("-")[0]

        _clean_pycache(temp_dir_path)
        _install_files(package_name, temp_dir_path, env, alias)


def _install_files(
    package_name: str, source_path: Path, env: str = None, alias: str = None
):
    env = env or "base"
    context = load_context(Path.cwd(), env=env)

    package_source, test_source, conf_source = _get_package_artifacts(
        source_path, package_name
    )

    pipeline_name = alias or package_name
    package_dest, test_dest, conf_dest = _get_pipeline_artifacts(
        context, pipeline_name=pipeline_name, env=env
    )

    if conf_source.is_dir():
        _sync_dirs(conf_source, conf_dest)
        # `config` was packaged under `package_name` directory with `kedro pipeline package`.
        # Since `config` was already synced, we don't want to send it again
        # when syncing the package, so we remove it.
        shutil.rmtree(str(conf_source))

    if test_source.is_dir():
        _sync_dirs(test_source, test_dest)

    # Sync everything under package directory, except `config` since we already sent it.
    if package_source.is_dir():
        _sync_dirs(package_source, package_dest)


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
def package_pipeline(name, env, alias, destination, version):
    """Package up a pipeline for easy distribution. A .whl file
    will be created in a `<source_dir>/dist/`."""
    context = load_context(Path.cwd(), env=env)

    result_path = _package_pipeline(
        name,
        context,
        package_name=alias,
        destination=destination,
        env=env,
        version=version,
    )

    as_alias = f" as `{alias}`" if alias else ""
    message = f"Pipeline `{name}` packaged{as_alias}! Location: {result_path}"
    click.secho(message, fg="green")


def _package_pipeline(  # pylint: disable=too-many-arguments
    name: str,
    context: KedroContext,
    package_name: str = None,
    destination: str = None,
    env: str = None,
    version: str = None,
) -> Path:
    package_dir = _get_project_package_dir(context)
    env = env or "base"
    package_name = package_name or name
    version = version or "0.1"

    artifacts_to_package = _get_pipeline_artifacts(context, pipeline_name=name, env=env)
    # Check that pipeline directory exists and not empty
    _validate_dir(artifacts_to_package.pipeline_dir)
    destination = Path(destination) if destination else package_dir.parent / "dist"

    _generate_wheel_file(package_name, destination, artifacts_to_package, version)

    _clean_pycache(package_dir)
    _clean_pycache(context.project_path)

    return destination


def _validate_dir(path: Path) -> None:
    if not path.is_dir():
        raise KedroCliError(f"Directory '{path}' doesn't exist.")
    if not list(path.iterdir()):
        raise KedroCliError(f"'{path}' is an empty directory.")


def _get_wheel_name(**kwargs):
    # https://stackoverflow.com/questions/51939257/how-do-you-get-the-filename-of-a-python-wheel-when-running-setup-py
    dist = Distribution(attrs=kwargs)
    bdist_wheel_cmd = dist.get_command_obj("bdist_wheel")
    bdist_wheel_cmd.ensure_finalized()

    distname = bdist_wheel_cmd.wheel_dist_name
    tag = "-".join(bdist_wheel_cmd.get_tag())
    return f"{distname}-{tag}.whl"


def _generate_wheel_file(
    package_name: str, destination: Path, source_paths: Tuple[Path, ...], version: str
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()

        # Copy source folders
        target_paths = _get_package_artifacts(temp_dir_path, package_name)
        for source, target in zip(source_paths, target_paths):
            if source.is_dir():
                _sync_dirs(source, target)

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


def _create_pipeline(name: str, kedro_version: str, output_dir: Path) -> Path:
    with _filter_deprecation_warnings():
        # pylint: disable=import-outside-toplevel
        from cookiecutter.main import cookiecutter

    template_path = Path(kedro.__file__).parent / "templates" / "pipeline"
    cookie_context = {"pipeline_name": name, "kedro_version": kedro_version}

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
    """Recursively copies `source` directory into `target` directory without
    overwriting any existing files/directories in the target using the following
    rules:
        1) Skip any files/directories from source have same names as files in target.
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

    for source_path in source.iterdir():
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
            double_prefix = (prefix or " ") * 2
            _sync_dirs(source_path, target_path, prefix=double_prefix)


def _get_project_package_dir(context: KedroContext) -> Path:
    # import the module of the current Kedro project
    project_package = import_module(context.package_name)
    # locate the directory of the project Python package
    package_dir = Path(project_package.__file__).parent
    return package_dir


def _get_pipeline_artifacts(
    context: KedroContext, pipeline_name: str, env: str
) -> PipelineArtifacts:
    """From existing project, returns in order: source_path, tests_path, config_path"""
    package_dir = _get_project_package_dir(context)
    artifacts = PipelineArtifacts(
        package_dir / "pipelines" / pipeline_name,
        package_dir.parent / "tests" / "pipelines" / pipeline_name,
        context.project_path / context.CONF_ROOT / env / "pipelines" / pipeline_name,
    )
    return artifacts


def _get_package_artifacts(
    source_path: Path, package_name: str
) -> Tuple[Path, Path, Path]:
    """From existing unpacked wheel, returns in order: source_path, tests_path, config_path"""
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
    pipe_name: str,
    result_path: Path,
    context: KedroContext,
    skip_config: bool,
    env: str = None,
):
    config_source = result_path / "config"
    env = env or "base"
    try:
        if not skip_config:
            config_target = (
                context.project_path / context.CONF_ROOT / env / "pipelines" / pipe_name
            )
            _sync_dirs(config_source, config_target)
    finally:
        shutil.rmtree(config_source)


def _delete_dirs(*dirs):
    for dir_ in dirs:
        click.echo(f"Deleting `{dir_}`: ", nl=False)
        try:
            shutil.rmtree(dir_)
        except Exception as exc:
            click.secho("FAILED", fg="red")
            cls = exc.__class__
            raise KedroCliError(f"{cls.__module__}.{cls.__qualname__}: {exc}") from exc
        else:
            click.secho("OK", fg="green")
