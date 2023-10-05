"""A collection of CLI commands for working with Kedro micro-packages."""
# ruff: noqa: I001
from __future__ import annotations

import logging
import re
import shutil
import sys
import tarfile
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Tuple, Union

import click
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from rope.base.project import Project
from rope.contrib import generate
from rope.refactor.move import MoveModule
from rope.refactor.rename import Rename
from setuptools.discovery import FlatLayoutPackageFinder

from build.util import project_wheel_metadata
from kedro.framework.cli.pipeline import (
    _assert_pkg_name_ok,
    _check_pipeline_name,
    _get_artifacts_to_package,
    _sync_dirs,
)
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    call,
    command_with_verbosity,
    env_option,
    python_call,
)
from kedro.framework.startup import ProjectMetadata

_PYPROJECT_TOML_TEMPLATE = """
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "{version}"
description = "Micro-package `{name}`"
dependencies = {install_requires}

[tool.setuptools.packages]
find = {{}}
"""

logger = logging.getLogger(__name__)


class _EquivalentRequirement(Requirement):
    """Parse a requirement according to PEP 508.

    This class overrides __eq__ to be backwards compatible with pkg_resources.Requirement
    while making __str__ and __hash__ use the non-canonicalized name
    as agreed in https://github.com/pypa/packaging/issues/644,

    Implementation taken from https://github.com/pypa/packaging/pull/696/
    """

    def _iter_parts(self, name: str) -> Iterator[str]:
        yield name

        if self.extras:
            formatted_extras = ",".join(sorted(self.extras))
            yield f"[{formatted_extras}]"

        if self.specifier:
            yield str(self.specifier)

        if self.url:
            yield f"@ {self.url}"
            if self.marker:
                yield " "

        if self.marker:
            yield f"; {self.marker}"

    def __str__(self) -> str:
        return "".join(self._iter_parts(self.name))

    def __hash__(self) -> int:
        return hash(
            (
                self.__class__.__name__,
                *self._iter_parts(canonicalize_name(self.name)),
            )
        )

    def __eq__(self, other: Any) -> bool:
        return (
            canonicalize_name(self.name) == canonicalize_name(other.name)
            and self.extras == other.extras
            and self.specifier == other.specifier
            and self.url == other.url
            and self.marker == other.marker
        )


def _check_module_path(ctx, param, value):  # noqa: unused-argument
    if value and not re.match(r"^[\w.]+$", value):
        message = (
            "The micro-package location you provided is not a valid Python module path"
        )
        raise KedroCliError(message)
    return value


# noqa: missing-function-docstring
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
def pull_package(  # noqa: unused-argument, too-many-arguments
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
            "'pyproject.toml' package manifest section."
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
    as_alias = f" as '{alias}'" if alias else ""
    message = f"Micro-package {package_path} pulled and unpacked{as_alias}!"
    click.secho(message, fg="green")


def _pull_package(  # noqa: too-many-arguments
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

        # temp_dir_path is the parent directory of the project root dir
        contents = [member for member in temp_dir_path.iterdir() if member.is_dir()]
        if len(contents) != 1:
            raise KedroCliError(
                "Invalid sdist was extracted: exactly one directory was expected, "
                f"got {contents}"
            )
        project_root_dir = contents[0]

        # This is much slower than parsing the requirements
        # directly from the metadata files
        # because it installs the package in an isolated environment,
        # but it's the only reliable way of doing it
        # without making assumptions on the project metadata.
        library_meta = project_wheel_metadata(project_root_dir)

        # Project name will be `my-pipeline` even if `pyproject.toml` says `my_pipeline`
        # because standards mandate normalization of names for comparison,
        # see https://packaging.python.org/en/latest/specifications/core-metadata/#name
        # The proper way to get it would be
        # project_name = library_meta.get("Name")
        # However, the rest of the code expects the non-normalized package name,
        # so we have to find it.
        packages = [
            package
            for package in FlatLayoutPackageFinder().find(project_root_dir)
            if "." not in package
        ]
        if len(packages) != 1:
            # Should not happen if user is calling `micropkg pull`
            # with the result of a `micropkg package`,
            # and in general if the distribution only contains one package (most likely),
            # but helps give a sensible error message otherwise
            raise KedroCliError(
                "Invalid package contents: exactly one package was expected, "
                f"got {packages}"
            )
        package_name = packages[0]

        package_reqs = _get_all_library_reqs(library_meta)

        if package_reqs:
            requirements_txt = metadata.project_path / "requirements.txt"
            _append_package_reqs(requirements_txt, package_reqs, package_name)

        _clean_pycache(temp_dir_path)
        _install_files(
            metadata,
            package_name,
            project_root_dir,
            env,
            alias,
            destination,
        )


def _pull_packages_from_manifest(metadata: ProjectMetadata) -> None:
    # noqa: import-outside-toplevel
    import anyconfig  # for performance reasons

    config_dict = anyconfig.load(metadata.config_file)
    config_dict = config_dict["tool"]["kedro"]
    build_specs = config_dict.get("micropkg", {}).get("pull")

    if not build_specs:
        click.secho(
            "Nothing to pull. Please update the 'pyproject.toml' package manifest section.",
            fg="yellow",
        )
        return

    for package_path, specs in build_specs.items():
        if "alias" in specs:
            _assert_pkg_name_ok(specs["alias"].split(".")[-1])
        _pull_package(package_path, metadata, **specs)
        click.secho(f"Pulled and unpacked '{package_path}'!")

    click.secho("Micro-packages pulled and unpacked!", fg="green")


def _package_micropkgs_from_manifest(metadata: ProjectMetadata) -> None:
    # noqa: import-outside-toplevel
    import anyconfig  # for performance reasons

    config_dict = anyconfig.load(metadata.config_file)
    config_dict = config_dict["tool"]["kedro"]
    build_specs = config_dict.get("micropkg", {}).get("package")

    if not build_specs:
        click.secho(
            "Nothing to package. Please update the 'pyproject.toml' package manifest section.",
            fg="yellow",
        )
        return

    for package_name, specs in build_specs.items():
        if "alias" in specs:
            _assert_pkg_name_ok(specs["alias"])
        _package_micropkg(package_name, metadata, **specs)
        click.secho(f"Packaged '{package_name}' micro-package!")

    click.secho("Micro-packages packaged!", fg="green")


@command_with_verbosity(micropkg, "package")
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
def package_micropkg(  # noqa: too-many-arguments
    metadata: ProjectMetadata,
    module_path,
    env,
    alias,
    destination,
    all_flag,
    **kwargs,
):
    """Package up a modular pipeline or micro-package as a Python source distribution."""
    if not module_path and not all_flag:
        click.secho(
            "Please specify a micro-package name or add '--all' to package all micro-packages in "
            "the 'pyproject.toml' package manifest section."
        )
        sys.exit(1)

    if all_flag:
        _package_micropkgs_from_manifest(metadata)
        return

    result_path = _package_micropkg(
        module_path, metadata, alias=alias, destination=destination, env=env
    )

    as_alias = f" as '{alias}'" if alias else ""
    message = (
        f"'{metadata.package_name}.{module_path}' packaged{as_alias}! "
        f"Location: {result_path}"
    )
    click.secho(message, fg="green")


def _get_fsspec_filesystem(location: str, fs_args: str | None):
    # noqa: import-outside-toplevel
    import anyconfig
    import fsspec

    from kedro.io.core import get_protocol_and_path

    protocol, _ = get_protocol_and_path(location)
    fs_args_config = anyconfig.load(fs_args) if fs_args else {}

    try:
        return fsspec.filesystem(protocol, **fs_args_config)
    except Exception as exc:  # noqa: broad-except
        # Specified protocol is not supported by `fsspec`
        # or requires extra dependencies
        click.secho(str(exc), fg="red")
        click.secho("Trying to use 'pip download'...", fg="red")
        return None


def _is_within_directory(directory, target):
    abs_directory = directory.resolve()
    abs_target = target.resolve()
    return abs_directory in abs_target.parents


def safe_extract(tar, path):
    for member in tar.getmembers():
        member_path = path / member.name
        if not _is_within_directory(path, member_path):
            # noqa: broad-exception-raised
            raise Exception("Failed to safely extract tar file.")
    tar.extractall(path)  # nosec B202


def _unpack_sdist(location: str, destination: Path, fs_args: str | None) -> None:
    filesystem = _get_fsspec_filesystem(location, fs_args)

    if location.endswith(".tar.gz") and filesystem and filesystem.exists(location):
        with filesystem.open(location) as fs_file:
            with tarfile.open(fileobj=fs_file, mode="r:gz") as tar_file:
                safe_extract(tar_file, destination)
    else:
        python_call(
            "pip",
            [
                "download",
                "--no-deps",
                "--no-binary",  # the micropackaging expects an sdist,
                ":all:",  # wheels are not supported
                "--dest",
                str(destination),
                location,
            ],
        )
        sdist_file = list(destination.glob("*.tar.gz"))
        # `--no-deps --no-binary :all:` should fetch only one source distribution file,
        # and CLI should fail if that's not the case.
        if len(sdist_file) != 1:
            file_names = [sf.name for sf in sdist_file]
            raise KedroCliError(
                f"More than 1 or no sdist files found: {file_names}. "
                f"There has to be exactly one source distribution file."
            )
        with tarfile.open(sdist_file[0], "r:gz") as fs_file:
            safe_extract(fs_file, destination)


def _rename_files(conf_source: Path, old_name: str, new_name: str):
    config_files_to_rename = (
        each
        for each in conf_source.rglob("*")
        if each.is_file() and old_name in each.name
    )
    for config_file in config_files_to_rename:
        new_config_name = config_file.name.replace(old_name, new_name)
        config_file.rename(config_file.parent / new_config_name)


def _refactor_code_for_unpacking(  # noqa: too-many-arguments
    project: Project,
    package_path: Path,
    tests_path: Path,
    alias: str | None,
    destination: str | None,
    project_metadata: ProjectMetadata,
) -> tuple[Path, Path]:
    """This is the reverse operation of `_refactor_code_for_package`, i.e
    we go from:
    <temp_dir>  # also the root of the Rope project
    |__ <micro_package>  # or <alias>
        |__ __init__.py
    |__ tests  # only tests for <micro_package>
        |__ __init__.py
        |__ tests.py

    to:
    <temp_dir>  # also the root of the Rope project
    |__ <package_name>
        |__ __init__.py
        |__ <path_to_micro_package>
            |__ __init__.py
            |__ <micro_package>
                |__ __init__.py
    |__ tests
        |__ __init__.py
        |__ <path_to_micro_package>
            |__ __init__.py
            |__ <micro_package>
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

    package_name = package_path.stem
    package_target = Path(project_metadata.package_name)
    tests_target = Path("tests")

    if destination:
        destination_path = Path(destination)
        package_target = package_target / destination_path
        tests_target = tests_target / destination_path

    if alias and alias != package_name:
        _rename_package(project, package_name, alias)
        package_name = alias

    if package_name == project_metadata.package_name:
        full_path = _move_package_with_conflicting_name(package_target, package_name)
    else:
        full_path = _create_nested_package(project, package_target)
        _move_package(project, package_name, package_target.as_posix())

    refactored_package_path = full_path / package_name

    if not tests_path.exists():
        return refactored_package_path, tests_path

    # we can't rename the tests package to <package_name>
    # because it will conflict with existing top-level package;
    # hence we give it a temp name, create the expected
    # nested folder structure, move the contents there,
    # then rename the temp name to <package_name>.
    full_path = _move_package_with_conflicting_name(
        tests_target, original_name="tests", desired_name=package_name
    )

    refactored_tests_path = full_path / package_name

    return refactored_package_path, refactored_tests_path


def _install_files(  # noqa: too-many-arguments, too-many-locals
    project_metadata: ProjectMetadata,
    package_name: str,
    source_path: Path,
    env: str = None,
    alias: str = None,
    destination: str = None,
):
    env = env or "base"

    package_source, test_source, conf_source = _get_package_artifacts(
        source_path, package_name
    )

    if conf_source.is_dir() and alias:
        _rename_files(conf_source, package_name, alias)

    module_path = alias or package_name
    if destination:
        module_path = f"{destination}.{module_path}"

    package_dest, test_dest, conf_dest = _get_artifacts_to_package(
        project_metadata, module_path=module_path, env=env
    )

    if conf_source.is_dir():
        _sync_dirs(conf_source, conf_dest)
        # `config` dir was packaged under `package_name` directory with
        # `kedro micropkg package`. Since `config` was already synced,
        # we don't want to copy it again when syncing the package, so we remove it.
        shutil.rmtree(str(conf_source))

    project = Project(source_path)
    refactored_package_source, refactored_test_source = _refactor_code_for_unpacking(
        project, package_source, test_source, alias, destination, project_metadata
    )
    project.close()

    if refactored_test_source.is_dir():
        _sync_dirs(refactored_test_source, test_dest)

    # Sync everything under package directory, except `config`
    # since it has already been copied.
    if refactored_package_source.is_dir():
        _sync_dirs(refactored_package_source, package_dest)


def _find_config_files(
    source_config_dir: Path, glob_patterns: list[str]
) -> list[tuple[Path, str]]:
    config_files: list[tuple[Path, str]] = []

    if source_config_dir.is_dir():
        config_files = [
            (path, path.parent.relative_to(source_config_dir).as_posix())
            for glob_pattern in glob_patterns
            for path in source_config_dir.glob(glob_pattern)
            if path.is_file()
        ]

    return config_files


def _get_default_version(metadata: ProjectMetadata, micropkg_module_path: str) -> str:
    # default to micropkg package version
    try:
        micropkg_module = import_module(
            f"{metadata.package_name}.{micropkg_module_path}"
        )
        return micropkg_module.__version__  # type: ignore
    except (AttributeError, ModuleNotFoundError):
        logger.warning(
            "Micropackage version not found in '%s.%s', will take the top-level one in '%s'",
            metadata.package_name,
            micropkg_module_path,
            metadata.package_name,
        )
        # if micropkg version doesn't exist, take the project one
        project_module = import_module(f"{metadata.package_name}")
        return project_module.__version__  # type: ignore


def _package_micropkg(
    micropkg_module_path: str,
    metadata: ProjectMetadata,
    alias: str = None,
    destination: str = None,
    env: str = None,
) -> Path:
    micropkg_name = micropkg_module_path.split(".")[-1]
    package_dir = metadata.source_dir / metadata.package_name
    env = env or "base"

    package_source, package_tests, package_conf = _get_artifacts_to_package(
        metadata, module_path=micropkg_module_path, env=env
    )
    # as the source distribution will only contain parameters, we aren't listing other
    # config files not to confuse users and avoid useless file copies
    # collect configs to package not only from parameters folder, but from core conf folder also
    # because parameters had been moved from foldername to yml filename
    configs_to_package = _find_config_files(
        package_conf,
        [
            f"**/parameters_{micropkg_name}.yml",
            f"**/{micropkg_name}/**/*",
            f"parameters*/**/{micropkg_name}.yml",
            f"parameters*/**/{micropkg_name}/**/*",
        ],
    )

    source_paths = (package_source, package_tests, configs_to_package)

    # Check that micropkg directory exists and not empty
    _validate_dir(package_source)

    destination = Path(destination) if destination else metadata.project_path / "dist"
    version = _get_default_version(metadata, micropkg_module_path)

    _generate_sdist_file(
        micropkg_name=micropkg_name,
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


def _sync_path_list(source: list[tuple[Path, str]], target: Path) -> None:
    for source_path, suffix in source:
        target_with_suffix = (target / suffix).resolve()
        _sync_dirs(source_path, target_with_suffix)


def _drop_comment(line):
    # https://github.com/pypa/setuptools/blob/b545fc7/\
    # pkg_resources/_vendor/jaraco/text/__init__.py#L554-L566
    return line.partition(" #")[0]


def _make_install_requires(requirements_txt: Path) -> list[str]:
    """Parses each line of requirements.txt into a version specifier valid to put in
    install_requires.
    Matches pkg_resources.parse_requirements"""
    if not requirements_txt.exists():
        return []
    return [
        str(_EquivalentRequirement(_drop_comment(requirement_line)))
        for requirement_line in requirements_txt.read_text().splitlines()
        if requirement_line and not requirement_line.startswith("#")
    ]


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
    alias: str | None,
    project_metadata: ProjectMetadata,
) -> None:
    """In order to refactor the imports properly, we need to recreate
    the same nested structure as in the project. Therefore, we create:
    <temp_dir>  # also the root of the Rope project
    |__ <package_name>
        |__ __init__.py
        |__ <path_to_micro_package>
            |__ __init__.py
            |__ <micro_package>
                |__ __init__.py
    |__ tests
        |__ __init__.py
        |__ path_to_micro_package
            |__ __init__.py
            |__ <micro_package>
                |__ __init__.py
    We then move <micro_package> outside of package src to top level ("")
    in temp_dir, and rename folder & imports if alias provided.

    For tests, we need to extract all the contents of <micro_package>
    at into top-level `tests` folder. This is not possible in one go with
    the Rope API, so we have to do it in a bit of a hacky way.
    We rename <micro_package> to a `tmp_name` and move it at top-level ("")
    in temp_dir. We remove the old `tests` folder and rename `tmp_name` to `tests`.

    The final structure should be:
    <temp_dir>  # also the root of the Rope project
    |__ <micro_package>  # or <alias>
        |__ __init__.py
    |__ tests  # only tests for <micro_package>
        |__ __init__.py
        |__ test.py
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

    # Refactor imports in src/package_name/.../micro_package
    # and imports of `micro_package` in tests.
    micro_package_name = package_target.stem
    if micro_package_name == project_metadata.package_name:
        _move_package_with_conflicting_name(package_target, micro_package_name)
    else:
        _move_package(project, package_target.as_posix(), "")
        shutil.rmtree(Path(project.address) / project_metadata.package_name)

    if alias:
        _rename_package(project, micro_package_name, alias)

    if tests_path.exists():
        # we can't move the relevant tests folder as is because
        # it will conflict with the top-level package <micro_package>;
        # we can't rename it "tests" and move it, because it will conflict
        # with the existing "tests" folder at top level;
        # hence we give it a temp name, move it, delete tests/ and
        # rename the temp name to tests.
        _move_package_with_conflicting_name(tests_target, "tests")


_SourcePathType = Union[Path, List[Tuple[Path, str]]]


def _generate_sdist_file(  # noqa: too-many-arguments,too-many-locals
    micropkg_name: str,
    destination: Path,
    source_paths: tuple[_SourcePathType, ...],
    version: str,
    metadata: ProjectMetadata,
    alias: str = None,
) -> None:
    package_name = alias or micropkg_name
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
            _rename_files(conf_target, micropkg_name, alias)

        # Build a pyproject.toml on the fly
        try:
            install_requires = _make_install_requires(
                package_source / "requirements.txt"  # type: ignore
            )
        except Exception as exc:
            click.secho("FAILED", fg="red")
            cls = exc.__class__
            raise KedroCliError(f"{cls.__module__}.{cls.__qualname__}: {exc}") from exc

        _generate_manifest_file(temp_dir_path)
        _generate_pyproject_file(package_name, version, install_requires, temp_dir_path)

        package_file = destination / _get_sdist_name(name=package_name, version=version)

        if package_file.is_file():
            click.secho(
                f"Package file {package_file} will be overwritten!", fg="yellow"
            )

        # python -m build --outdir <destination>
        call(
            [
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--outdir",
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


def _generate_pyproject_file(
    package_name: str, version: str, install_requires: list[str], output_dir: Path
) -> Path:
    pyproject_file = output_dir / "pyproject.toml"

    pyproject_file_context = {
        "name": package_name,
        "version": version,
        "install_requires": install_requires,
    }

    pyproject_file.write_text(_PYPROJECT_TOML_TEMPLATE.format(**pyproject_file_context))
    return pyproject_file


def _get_package_artifacts(
    source_path: Path, package_name: str
) -> tuple[Path, Path, Path]:
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


def _append_package_reqs(
    requirements_txt: Path, package_reqs: list[str], package_name: str
) -> None:
    """Appends micro-package requirements to project level requirements.txt"""
    incoming_reqs = _safe_parse_requirements(package_reqs)
    if requirements_txt.is_file():
        existing_reqs = _safe_parse_requirements(requirements_txt.read_text())
        reqs_to_add = set(incoming_reqs) - set(existing_reqs)
        if not reqs_to_add:
            return

        sorted_reqs = sorted(str(req) for req in reqs_to_add)
        sep = "\n"
        with open(requirements_txt, "a", encoding="utf-8") as file:
            file.write(
                f"\n\n# Additional requirements from micro-package `{package_name}`:\n"
            )
            file.write(sep.join(sorted_reqs))
        click.secho(
            f"Added the following requirements from micro-package '{package_name}' to "
            f"requirements.txt:\n{sep.join(sorted_reqs)}"
        )
    else:
        click.secho(
            "No project requirements.txt found. Copying contents from project requirements.txt..."
        )
        sorted_reqs = sorted(str(req) for req in incoming_reqs)
        sep = "\n"
        with open(requirements_txt, "a", encoding="utf-8") as file:
            file.write(sep.join(sorted_reqs))

    click.secho(
        "Use 'pip-compile requirements.txt --output-file requirements.lock' to compile "
        "and 'pip install -r requirements.lock' to install the updated list of requirements."
    )


def _get_all_library_reqs(metadata):
    """Get all library requirements from metadata, leaving markers intact."""
    # See https://discuss.python.org/t/\
    # programmatically-getting-non-optional-requirements-of-current-directory/26963/2
    return [
        str(_EquivalentRequirement(dep_str))
        for dep_str in metadata.get_all("Requires-Dist", [])
    ]


def _safe_parse_requirements(
    requirements: str | Iterable[str],
) -> set[_EquivalentRequirement]:
    """Safely parse a requirement or set of requirements. This avoids blowing up when it
    encounters a requirement it cannot parse (e.g. `-r requirements.txt`). This way
    we can still extract all the parseable requirements out of a set containing some
    unparseable requirements.
    """
    parseable_requirements = set()
    if isinstance(requirements, str):
        requirements = requirements.splitlines()
    # TODO: Properly handle continuation lines,
    # see https://github.com/pypa/setuptools/blob/v67.8.0/setuptools/_reqs.py
    for requirement_line in requirements:
        if (
            requirement_line
            and not requirement_line.startswith("#")
            and not requirement_line.startswith("-e")
        ):
            try:
                parseable_requirements.add(
                    _EquivalentRequirement(_drop_comment(requirement_line))
                )
            except InvalidRequirement:
                continue
    return parseable_requirements
