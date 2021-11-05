# pylint: disable=too-many-lines

"""A collection of CLI commands for working with Kedro pipelines."""
import re
import shutil
import sys
import tarfile
import tempfile
from importlib import import_module
from pathlib import Path
from textwrap import indent
from typing import Any, Iterable, List, NamedTuple, Optional, Set, Tuple, Union
from zipfile import ZipFile

import click
import pkg_resources
from rope.base.project import Project
from rope.contrib import generate
from rope.refactor.move import MoveModule
from rope.refactor.rename import Rename

import kedro
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    _filter_deprecation_warnings,
    _get_requirements_in,
    call,
    command_with_verbosity,
    env_option,
    python_call,
)
from kedro.framework.project import settings
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


class PipelineArtifacts(NamedTuple):
    """An ordered collection of source_path, tests_path, config_paths"""

    pipeline_dir: Path
    pipeline_tests: Path
    pipeline_conf: Path


def _assert_pkg_name_ok(pkg_name: str):
    """Check that python package name is in line with PEP8 requirements.

    Args:
        pkg_name: Candidate Python package name.

    Raises:
        KedroCliError: If package name violates the requirements.
    """

    base_message = f"`{pkg_name}` is not a valid Python package name."
    if not re.match(r"^[a-zA-Z_]", pkg_name):
        message = base_message + " It must start with a letter or underscore."
        raise KedroCliError(message)
    if len(pkg_name) < 2:
        message = base_message + " It must be at least 2 characters long."
        raise KedroCliError(message)
    if not re.match(r"^\w+$", pkg_name[1:]):
        message = (
            base_message + " It must contain only letters, digits, and/or underscores."
        )
        raise KedroCliError(message)


def _check_pipeline_name(ctx, param, value):  # pylint: disable=unused-argument
    if value:
        _assert_pkg_name_ok(value)
    return value


def _check_module_path(ctx, param, value):  # pylint: disable=unused-argument
    if value and not re.match(r"^[\w.]+$", value):
        message = "The pipeline location you provided is not a valid Python module path"
        raise KedroCliError(message)
    return value


# pylint: disable=missing-function-docstring
@click.group(name="Kedro")
def pipeline_cli():  # pragma: no cover
    pass


@pipeline_cli.group()
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
    """Create a new modular pipeline by providing a name."""
    package_dir = metadata.source_dir / metadata.package_name
    conf_source = settings.CONF_SOURCE
    project_conf_path = metadata.project_path / conf_source

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
        f"to `register_pipelines()` in `{package_dir / 'pipeline_registry.py'}`.",
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
    """Delete a modular pipeline by providing a name."""
    package_dir = metadata.source_dir / metadata.package_name
    conf_source = settings.CONF_SOURCE
    project_conf_path = metadata.project_path / conf_source

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
        f"`{package_dir / 'pipeline_registry.py'}`, you will need to remove it.",
        fg="yellow",
    )


@command_with_verbosity(pipeline, "pull")
@click.argument("package_path", nargs=1, required=False)
@click.option(
    "--all",
    "-a",
    "all_flag",
    is_flag=True,
    help="Pull and unpack all pipelines in the `pyproject.toml` package manifest section.",
)
@env_option(
    help="Environment to install the pipeline configuration to. Defaults to `base`."
)
@click.option(
    "--alias", type=str, default="", help="Module location to unpackage under."
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
    """Pull and unpack a modular pipeline in your project."""
    if not package_path and not all_flag:
        click.secho(
            "Please specify a package path or add '--all' to pull all pipelines in the "
            "`pyproject.toml` package manifest section."
        )
        sys.exit(1)

    if all_flag:
        _pull_packages_from_manifest(metadata)
        return

    _pull_package(package_path, metadata, env=env, alias=alias, fs_args=fs_args)
    as_alias = f" as `{alias}`" if alias else ""
    message = f"Pipeline {package_path} pulled and unpacked{as_alias}!"
    click.secho(message, fg="green")


# pylint: disable=too-many-locals
def _pull_package(
    package_path: str,
    metadata: ProjectMetadata,
    env: str = None,
    alias: str = None,
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
            requirements_in = _get_requirements_in(
                metadata.source_dir, create_empty=True
            )
            _append_package_reqs(requirements_in, package_reqs, package_name)

        _clean_pycache(temp_dir_path)
        _install_files(metadata, package_name, temp_dir_path / sdist_file_name, env, alias)


def _pull_packages_from_manifest(metadata: ProjectMetadata) -> None:
    # pylint: disable=import-outside-toplevel
    import anyconfig  # for performance reasons

    config_dict = anyconfig.load(metadata.config_file)
    config_dict = config_dict["tool"]["kedro"]
    build_specs = config_dict.get("pipeline", {}).get("pull")

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

    click.secho("Pipelines pulled and unpacked!", fg="green")


def _package_pipelines_from_manifest(metadata: ProjectMetadata) -> None:
    # pylint: disable=import-outside-toplevel
    import anyconfig  # for performance reasons

    config_dict = anyconfig.load(metadata.config_file)
    config_dict = config_dict["tool"]["kedro"]
    build_specs = config_dict.get("pipeline", {}).get("package")

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
        click.secho(f"Packaged `{pipeline_name}` pipeline!")

    click.secho("Pipelines packaged!", fg="green")


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
    help="Location where to create the source distribution file. Defaults to `dist/`.",
)
@click.option(
    "--all",
    "-a",
    "all_flag",
    is_flag=True,
    help="Package all pipelines in the `pyproject.toml` package manifest section.",
)
@click.argument("module_path", nargs=1, required=False, callback=_check_module_path)
@click.pass_obj  # this will pass the metadata as first argument
def package_pipeline(
    metadata: ProjectMetadata, module_path, env, alias, destination, all_flag
):  # pylint: disable=too-many-arguments
    """Package up a modular pipeline as Python source distribution."""
    if not module_path and not all_flag:
        click.secho(
            "Please specify a pipeline name or add '--all' to package all pipelines in "
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


def _echo_deletion_warning(message: str, **paths: List[Path]):
    paths = {key: values for key, values in paths.items() if values}

    if paths:
        click.secho(message, bold=True)

    for key, values in paths.items():
        click.echo(f"\n{key.capitalize()}:")
        paths_str = "\n".join(str(value) for value in values)
        click.echo(indent(paths_str, " " * 2))


def _get_fsspec_filesystem(location: str, fs_args: Optional[str]):
    # pylint: disable=import-outside-toplevel
    import anyconfig
    import fsspec

    from kedro.io.core import get_protocol_and_path

    protocol, _ = get_protocol_and_path(location)
    fs_args_config = anyconfig.load(fs_args) if fs_args else {}

    try:
        return fsspec.filesystem(protocol, **fs_args_config)
    except Exception as exc:  # pylint: disable=broad-except
        # Specified protocol is not supported by `fsspec`
        # or requires extra dependencies
        click.secho(str(exc), fg="red")
        click.secho("Trying to use 'pip download'...", fg="red")
        return None


def _unpack_sdist(location: str, destination: Path, fs_args: Optional[str]) -> None:
    filesystem = _get_fsspec_filesystem(location, fs_args)

    if location.endswith(".tar.gz") and filesystem and filesystem.exists(location):
        with filesystem.open(location) as fs_file:
            with tarfile.open(fileobj=fs_file, mode="r:gz") as tar_file:
                tar_file.extractall(destination)
    else:
        python_call(
            "pip", ["download", "--no-deps", "--dest", str(destination), location]
        )
        sdist_file = list(destination.glob("*.tar.gz"))
        # `--no-deps` should fetch only one source distribution file, and CLI should fail if that's
        # not the case.
        if len(sdist_file) != 1:
            file_names = [sf.name for sf in sdist_file]
            raise KedroCliError(
                f"More than 1 or no sdist files found: {file_names}. "
                f"There has to be exactly one source distribution file."
            )
        with tarfile.open(sdist_file[0], "r:gz") as fs_file:
            fs_file.extractall(destination)


def _rename_files(conf_source: Path, old_name: str, new_name: str):
    config_files_to_rename = (
        each
        for each in conf_source.rglob("*")
        if each.is_file() and old_name in each.name
    )
    for config_file in config_files_to_rename:
        new_config_name = config_file.name.replace(old_name, new_name)
        config_file.rename(config_file.parent / new_config_name)


def _refactor_code_for_unpacking(
    project: Project,
    package_path: Path,
    tests_path: Path,
    alias: Optional[str],
    project_metadata: ProjectMetadata,
) -> Tuple[Path, Path]:
    """This is the reverse operation of `_refactor_code_for_package`, i.e
    we go from:
    <temp_dir>  # also the root of the Rope project
    |__ <pipeline_name>  # or <alias>
        |__ __init__.py
    |__ tests  # only tests for <pipeline_name>
        |__ __init__.py
        |__ test_pipeline.py

    to:
    <temp_dir>  # also the root of the Rope project
    |__ <package>
        |__ __init__.py
        |__ <path_to_pipeline>
            |__ __init__.py
            |__ <pipeline_name>
                |__ __init__.py
    |__ tests
        |__ __init__.py
        |__ <path_to_pipeline>
            |__ __init__.py
            |__ <pipeline_name>
                |__ __init__.py
    """

    def _move_package_with_conflicting_name(
        target: Path, original_name: str, desired_name: str = None
    ) -> Path:
        _rename_package(project, original_name, "tmp_name")
        full_path = _create_nested_package(project, target)
        _move_package(project, "tmp_name", target.as_posix())
        desired_name = desired_name or original_name
        _rename_package(project, (target / "tmp_name").as_posix(), desired_name)
        return full_path

    pipeline_name = package_path.stem
    package_target = Path(project_metadata.package_name)
    tests_target = Path("tests")

    if alias:
        alias_path = Path(*alias.split("."))
        alias_name = alias_path.stem
        _rename_package(project, pipeline_name, alias_name)

        pipeline_name = alias_name
        package_target = package_target / alias_path.parent
        tests_target = tests_target / alias_path.parent

    if pipeline_name == project_metadata.package_name:
        full_path = _move_package_with_conflicting_name(package_target, pipeline_name)
    else:
        full_path = _create_nested_package(project, package_target)
        _move_package(project, pipeline_name, package_target.as_posix())

    refactored_package_path = full_path / pipeline_name

    if not tests_path.exists():
        return refactored_package_path, tests_path

    # we can't rename the tests package to <pipeline_name>
    # because it will conflict with existing top-level package;
    # hence we give it a temp name, create the expected
    # nested folder structure, move the contents there,
    # then rename the temp name to <pipeline_name>.
    full_path = _move_package_with_conflicting_name(
        tests_target, original_name="tests", desired_name=pipeline_name
    )

    refactored_tests_path = full_path / pipeline_name

    return refactored_package_path, refactored_tests_path


def _install_files(  # pylint: disable=too-many-locals
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
        alias_name = alias.split(".")[-1]
        _rename_files(conf_source, package_name, alias_name)

    module_path = alias or package_name
    package_dest, test_dest, conf_dest = _get_artifacts_to_package(
        project_metadata, module_path=module_path, env=env
    )

    if conf_source.is_dir():
        _sync_dirs(conf_source, conf_dest)
        # `config` dir was packaged under `package_name` directory with
        # `kedro pipeline package`. Since `config` was already synced,
        # we don't want to copy it again when syncing the package, so we remove it.
        shutil.rmtree(str(conf_source))

    project = Project(source_path)
    refactored_package_source, refactored_test_source = _refactor_code_for_unpacking(
        project, package_source, test_source, alias, project_metadata
    )
    project.close()

    if refactored_test_source.is_dir():
        _sync_dirs(refactored_test_source, test_dest)

    # Sync everything under package directory, except `config`
    # since it has already been copied.
    if refactored_package_source.is_dir():
        _sync_dirs(refactored_package_source, package_dest)


def _find_config_files(
    source_config_dir: Path, glob_patterns: List[str]
) -> List[Tuple[Path, str]]:
    config_files = []  # type: List[Tuple[Path, str]]

    if source_config_dir.is_dir():
        config_files = [
            (path, path.parent.relative_to(source_config_dir).as_posix())
            for glob_pattern in glob_patterns
            for path in source_config_dir.glob(glob_pattern)
            if path.is_file()
        ]

    return config_files


def _get_default_version(metadata: ProjectMetadata, pipeline_module_path: str) -> str:
    # default to pipeline package version
    try:
        pipeline_module = import_module(
            f"{metadata.package_name}.{pipeline_module_path}"
        )
        return pipeline_module.__version__  # type: ignore
    except (AttributeError, ModuleNotFoundError):
        # if pipeline version doesn't exist, take the project one
        project_module = import_module(f"{metadata.package_name}")
        return project_module.__version__  # type: ignore


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


def _validate_dir(path: Path) -> None:
    if not path.is_dir():
        raise KedroCliError(f"Directory '{path}' doesn't exist.")
    if not list(path.iterdir()):
        raise KedroCliError(f"'{path}' is an empty directory.")


def _get_sdist_name(name, version):
    return f"{name}-{version}.tar.gz"


def _sync_path_list(source: List[Tuple[Path, str]], target: Path) -> None:
    for source_path, suffix in source:
        target_with_suffix = (target / suffix).resolve()
        _sync_dirs(source_path, target_with_suffix)


def _make_install_requires(requirements_txt: Path) -> List[str]:
    """Parses each line of requirements.txt into a version specifier valid to put in
    install_requires."""
    if not requirements_txt.exists():
        return []
    requirements = pkg_resources.parse_requirements(requirements_txt.read_text())
    return [str(requirement) for requirement in requirements]


def _create_nested_package(project: Project, package_path: Path) -> Path:
    # fails if parts of the path exists already
    packages = package_path.parts
    parent = generate.create_package(project, packages[0])
    nested_path = Path(project.address) / packages[0]
    for package in packages[1:]:
        parent = generate.create_package(project, package, sourcefolder=parent)
        nested_path = nested_path / package
    return nested_path


def _move_package(project: Project, source: str, target: str) -> None:
    """
    Move a Python package, refactoring relevant imports along the way.
    A target of empty string means moving to the root of the `project`.

    Args:
        project: rope.base.Project holding the scope of the refactoring.
        source: Name of the Python package to be moved. Can be a fully
            qualified module path relative to the `project` root, e.g.
            "package.pipelines.pipeline" or "package/pipelines/pipeline".
        target: Destination of the Python package to be moved. Can be a fully
            qualified module path relative to the `project` root, e.g.
            "package.pipelines.pipeline" or "package/pipelines/pipeline".
    """
    src_folder = project.get_module(source).get_resource()
    target_folder = project.get_module(target).get_resource()
    change = MoveModule(project, src_folder).get_changes(dest=target_folder)
    project.do(change)


def _rename_package(project: Project, old_name: str, new_name: str) -> None:
    """
    Rename a Python package, refactoring relevant imports along the way,
    as well as references in comments.

    Args:
        project: rope.base.Project holding the scope of the refactoring.
        old_name: Old module name. Can be a fully qualified module path,
            e.g. "package.pipelines.pipeline" or "package/pipelines/pipeline",
            relative to the `project` root.
        new_name: New module name. Can't be a fully qualified module path.
    """
    folder = project.get_folder(old_name)
    change = Rename(project, folder).get_changes(new_name, docs=True)
    project.do(change)


def _refactor_code_for_package(
    project: Project,
    package_path: Path,
    tests_path: Path,
    alias: Optional[str],
    project_metadata: ProjectMetadata,
) -> None:
    """In order to refactor the imports properly, we need to recreate
    the same nested structure as in the project. Therefore, we create:
    <temp_dir>  # also the root of the Rope project
    |__ <package>
        |__ __init__.py
        |__ pipelines
            |__ __init__.py
            |__ <pipeline_name>
                |__ __init__.py
    |__ tests
        |__ __init__.py
        |__ pipelines
            |__ __init__.py
            |__ <pipeline_name>
                |__ __init__.py
    We then move <pipeline_name> outside of package src to top level ("")
    in temp_dir, and rename folder & imports if alias provided.

    For tests, we need to extract all the contents of <pipeline_name>
    at into top-level `tests` folder. This is not possible in one go with
    the Rope API, so we have to do it in a bit of a hacky way.
    We rename <pipeline_name> to a `tmp_name` and move it at top-level ("")
    in temp_dir. We remove the old `tests` folder and rename `tmp_name` to `tests`.

    The final structure should be:
    <temp_dir>  # also the root of the Rope project
    |__ <pipeline_name>  # or <alias>
        |__ __init__.py
    |__ tests  # only tests for <pipeline_name>
        |__ __init__.py
        |__ test_pipeline.py
    """

    def _move_package_with_conflicting_name(target: Path, conflicting_name: str):
        tmp_name = "tmp_name"
        tmp_module = target.parent / tmp_name
        _rename_package(project, target.as_posix(), tmp_name)
        _move_package(project, tmp_module.as_posix(), "")
        shutil.rmtree(Path(project.address) / conflicting_name)
        _rename_package(project, tmp_name, conflicting_name)

    # Copy source in appropriate folder structure
    package_target = package_path.relative_to(project_metadata.source_dir)
    full_path = _create_nested_package(project, package_target)
    # overwrite=True to update the __init__.py files generated by create_package
    _sync_dirs(package_path, full_path, overwrite=True)

    # Copy tests in appropriate folder structure
    if tests_path.exists():
        tests_target = tests_path.relative_to(project_metadata.source_dir)
        full_path = _create_nested_package(project, tests_target)
        # overwrite=True to update the __init__.py files generated by create_package
        _sync_dirs(tests_path, full_path, overwrite=True)

    # Refactor imports in src/package_name/pipelines/pipeline_name
    # and imports of `pipeline_name` in tests.
    pipeline_name = package_target.stem
    if pipeline_name == project_metadata.package_name:
        _move_package_with_conflicting_name(package_target, pipeline_name)
    else:
        _move_package(project, package_target.as_posix(), "")
        shutil.rmtree(Path(project.address) / project_metadata.package_name)

    if alias:
        _rename_package(project, pipeline_name, alias)

    if tests_path.exists():
        # we can't move the relevant tests folder as is because
        # it will conflict with the top-level package <pipeline_name>;
        # we can't rename it "tests" and move it, because it will conflict
        # with the existing "tests" folder at top level;
        # hence we give it a temp name, move it, delete tests/ and
        # rename the temp name to tests.
        _move_package_with_conflicting_name(tests_target, "tests")


_SourcePathType = Union[Path, List[Tuple[Path, str]]]


# pylint: disable=too-many-arguments,too-many-locals
def _generate_sdist_file(
    pipeline_name: str,
    destination: Path,
    source_paths: Tuple[_SourcePathType, ...],
    version: str,
    metadata: ProjectMetadata,
    alias: str = None,
) -> None:
    package_name = alias or pipeline_name
    package_source, tests_source, conf_source = source_paths

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()

        project = Project(temp_dir_path)  # project where to do refactoring
        _refactor_code_for_package(
            project, package_source, tests_source, alias, metadata  # type: ignore
        )
        project.close()

        # Copy & "refactor" config
        _, _, conf_target = _get_package_artifacts(temp_dir_path, package_name)
        _sync_path_list(conf_source, conf_target)  # type: ignore
        if conf_target.is_dir() and alias:
            _rename_files(conf_target, pipeline_name, alias)

        # Build a setup.py on the fly
        try:
            install_requires = _make_install_requires(
                package_source / "requirements.txt"  # type: ignore
            )
        except Exception as exc:
            click.secho("FAILED", fg="red")
            cls = exc.__class__
            raise KedroCliError(f"{cls.__module__}.{cls.__qualname__}: {exc}") from exc

        _generate_manifest_file(temp_dir_path)
        setup_file = _generate_setup_file(
            package_name, version, install_requires, temp_dir_path
        )

        package_file = destination / _get_sdist_name(name=package_name, version=version)

        if package_file.is_file():
            click.secho(
                f"Package file {package_file} will be overwritten!", fg="yellow"
            )

        # python setup.py sdist --formats=gztar --dist-dir <destination>
        call(
            [
                sys.executable,
                str(setup_file.resolve()),
                "sdist",
                "--formats=gztar",
                "--dist-dir",
                str(destination),
            ],
            cwd=temp_dir,
        )


def _generate_manifest_file(output_dir: Path):
    manifest_file = output_dir / "MANIFEST.in"
    manifest_file.write_text(
        """
        global-include README.md
        global-include config/parameters*
        global-include config/**/parameters*
        global-include config/parameters*/**
        global-include config/parameters*/**/*
        """
    )


def _generate_setup_file(
    package_name: str, version: str, install_requires: List[str], output_dir: Path
) -> Path:
    setup_file = output_dir / "setup.py"

    setup_file_context = dict(
        name=package_name, version=version, install_requires=install_requires
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
def _sync_dirs(source: Path, target: Path, prefix: str = "", overwrite: bool = False):
    """Recursively copies `source` directory (or file) into `target` directory without
    overwriting any existing files/directories in the target using the following
    rules:
        1) Skip any files/directories which names match with files in target,
        unless overwrite=True.
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
        # nothing to copy
        content = []  # pragma: no cover

    for source_path in content:
        source_name = source_path.name
        target_path = target / source_name
        click.echo(indent(f"Creating `{target_path}`: ", prefix), nl=False)

        if (  # rule #1
            not overwrite
            and source_name in existing_files
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
    artifacts = _get_artifacts_to_package(
        project_metadata, f"pipelines.{pipeline_name}", env
    )
    return PipelineArtifacts(*artifacts)


def _get_artifacts_to_package(
    project_metadata: ProjectMetadata, module_path: str, env: str
) -> Tuple[Path, Path, Path]:
    """From existing project, returns in order: source_path, tests_path, config_paths"""
    package_dir = project_metadata.source_dir / project_metadata.package_name
    project_conf_path = project_metadata.project_path / settings.CONF_SOURCE
    artifacts = (
        Path(package_dir, *module_path.split(".")),
        Path(package_dir.parent, "tests", *module_path.split(".")),
        project_conf_path / env,
    )
    return artifacts


def _get_package_artifacts(
    source_path: Path, package_name: str
) -> Tuple[Path, Path, Path]:
    """From existing package, returns in order:
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


def _append_package_reqs(
    requirements_in: Path, package_reqs: List[str], pipeline_name: str
) -> None:
    """Appends modular pipeline requirements to project level requirements.in"""
    existing_reqs = _safe_parse_requirements(requirements_in.read_text())
    incoming_reqs = _safe_parse_requirements(package_reqs)
    reqs_to_add = set(incoming_reqs) - set(existing_reqs)
    if not reqs_to_add:
        return

    sorted_reqs = sorted(str(req) for req in reqs_to_add)
    sep = "\n"
    with open(requirements_in, "a", encoding="utf-8") as file:
        file.write(
            f"\n\n# Additional requirements from modular pipeline `{pipeline_name}`:\n"
        )
        file.write(sep.join(sorted_reqs))
    click.secho(
        f"Added the following requirements from modular pipeline `{pipeline_name}` to "
        f"requirements.in:\n{sep.join(sorted_reqs)}"
    )
    click.secho(
        "Use `kedro build-reqs` to compile and `pip install -r src/requirements.txt` to install "
        "the updated list of requirements."
    )


def _safe_parse_requirements(
    requirements: Union[str, Iterable[str]]
) -> Set[pkg_resources.Requirement]:
    """Safely parse a requirement or set of requirements. This effectively replaces
    pkg_resources.parse_requirements, which blows up with a ValueError as soon as it
    encounters a requirement it cannot parse (e.g. `-r requirements.txt`). This way
    we can still extract all the parseable requirements out of a set containing some
    unparseable requirements.
    """
    parseable_requirements = set()
    for requirement in pkg_resources.yield_lines(requirements):
        try:
            parseable_requirements.add(pkg_resources.Requirement.parse(requirement))
        except ValueError:
            continue
    return parseable_requirements
