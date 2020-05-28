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
import shutil
from importlib import import_module
from pathlib import Path
from textwrap import indent

import click
import yaml
from click import secho

import kedro
from kedro.framework.cli.cli import _assert_pkg_name_ok, _handle_exception
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    _filter_deprecation_warnings,
    env_option,
)
from kedro.framework.context import KedroContext, load_context


@click.group()
def pipeline():
    """Commands for working with pipelines."""


def _check_pipeline_name(ctx, param, value):  # pylint: disable=unused-argument
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
    secho(f"\nPipeline `{name}` was successfully created.\n", fg="green")

    secho(
        f"To be able to run the pipeline `{name}`, you will need to add it "
        f"to `create_pipelines()` in `{package_dir / 'pipeline.py'}`.",
        fg="yellow",
    )


@pipeline.command("list")
@env_option
def list_pipelines(env):
    """List all pipelines defined in your pipeline.py file."""
    context = load_context(Path.cwd(), env=env)
    project_pipelines = context.pipelines
    secho(yaml.dump(sorted(project_pipelines)))


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

    result = {}
    result["Nodes"] = [
        f"{node.short_name} ({node._func_name})"  # pylint: disable=protected-access
        for node in pipeline_obj.nodes
    ]

    secho(yaml.dump(result))


def _create_pipeline(name: str, kedro_version: str, output_dir: Path) -> Path:
    with _filter_deprecation_warnings():
        # pylint: disable=import-outside-toplevel
        from cookiecutter.main import cookiecutter

    template_path = Path(kedro.__file__).parent / "templates" / "pipeline"
    cookie_context = {"pipeline_name": name, "kedro_version": kedro_version}

    secho(f"Creating the pipeline `{name}`: ", nl=False)

    try:
        result_path = cookiecutter(
            str(template_path),
            output_dir=str(output_dir),
            no_input=True,
            extra_context=cookie_context,
        )
    except Exception as ex:
        secho("FAILED", fg="red")
        cls = ex.__class__
        raise KedroCliError(f"{cls.__module__}.{cls.__qualname__}: {ex}")

    secho("OK", fg="green")
    result_path = Path(result_path)
    message = indent(f"Location: `{result_path.resolve()}`", " " * 2)
    secho(message, bold=True)

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
        secho(indent(f"Creating `{target_path}`: ", prefix), nl=False)

        if (  # rule #1
            source_name in existing_files
            or source_path.is_file()
            and source_name in existing_folders
        ):
            secho("SKIPPED (already exists)", fg="yellow")
        elif source_path.is_file():  # rule #2
            try:
                target.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(str(source_path), str(target_path))
            except Exception:
                secho("FAILED", fg="red")
                raise
            secho("OK", fg="green")
        else:  # source_path is a directory, rule #3
            secho()
            double_prefix = (prefix or " ") * 2
            _sync_dirs(source_path, target_path, prefix=double_prefix)


def _get_project_package_dir(context: KedroContext) -> Path:
    # import the module of the current Kedro project
    project_package = import_module(context.package_name)
    # locate the directory of the project Python package
    package_dir = Path(project_package.__file__).parent
    return package_dir


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
