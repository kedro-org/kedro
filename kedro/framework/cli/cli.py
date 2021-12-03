"""kedro is a CLI for managing Kedro projects.

This module implements commands available from the kedro CLI.
"""
import importlib
import warnings
import webbrowser
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

import click
import pkg_resources
from click.utils import get_os_args

# pylint: disable=unused-import
import kedro.config.default_logger  # noqa
from kedro import __version__ as version
from kedro.framework.cli.catalog import catalog_cli
from kedro.framework.cli.hooks import get_cli_hook_manager
from kedro.framework.cli.jupyter import jupyter_cli
from kedro.framework.cli.pipeline import pipeline_cli
from kedro.framework.cli.project import project_group
from kedro.framework.cli.registry import registry_cli
from kedro.framework.cli.starters import create_cli
from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    ENTRY_POINT_GROUPS,
    CommandCollection,
    KedroCliError,
    load_entry_points,
)
from kedro.framework.context.context import load_context
from kedro.framework.startup import _is_project, bootstrap_project

LOGO = rf"""
 _            _
| | _____  __| |_ __ ___
| |/ / _ \/ _` | '__/ _ \
|   <  __/ (_| | | | (_) |
|_|\_\___|\__,_|_|  \___/
v{version}
"""


@click.group(context_settings=CONTEXT_SETTINGS, name="Kedro")
@click.version_option(version, "--version", "-V", help="Show version and exit")
def cli():  # pragma: no cover
    """Kedro is a CLI for creating and using Kedro projects. For more
    information, type ``kedro info``.

    When inside a Kedro project (created with ``kedro new``) commands from
    the project's ``cli.py`` file will also be available here.
    """
    pass


@cli.command()
def info():
    """Get more information about kedro."""
    click.secho(LOGO, fg="green")
    click.echo(
        "kedro allows teams to create analytics\n"
        "projects. It is developed as part of\n"
        "the Kedro initiative at QuantumBlack."
    )

    plugin_versions = {}
    plugin_entry_points = defaultdict(set)
    for plugin_entry_point, group in ENTRY_POINT_GROUPS.items():
        for entry_point in pkg_resources.iter_entry_points(group=group):
            module_name = entry_point.module_name.split(".")[0]
            plugin_version = pkg_resources.get_distribution(module_name).version
            plugin_versions[module_name] = plugin_version
            plugin_entry_points[module_name].add(plugin_entry_point)

    click.echo()
    if plugin_versions:
        click.echo("Installed plugins:")
        for plugin_name, plugin_version in sorted(plugin_versions.items()):
            entrypoints_str = ",".join(sorted(plugin_entry_points[plugin_name]))
            click.echo(
                f"{plugin_name}: {plugin_version} (entry points:{entrypoints_str})"
            )
    else:
        click.echo("No plugins installed")


@cli.command(short_help="See the kedro API docs and introductory tutorial.")
def docs():
    """Display the API docs and introductory tutorial in the browser,
    using the packaged HTML doc files."""
    html_path = str((Path(__file__).parent.parent / "html" / "index.html").resolve())
    index_path = f"file://{html_path}"
    click.echo(f"Opening {index_path}")
    webbrowser.open(index_path)


def get_project_context(
    key: str = "context", project_path: Path = None, **kwargs
) -> Any:
    """Gets the context value from context associated with the key.

    Args:
        key: Optional key to get associated value from Kedro context.
            Supported keys are "verbose" and "context", and it defaults to "context".
        project_path: Optional path to where the project root is to load the context.
            If omitted, the current working directory will be used.
        **kwargs: Optional custom arguments defined by users, which will be passed into
            the constructor of the projects KedroContext subclass.

    Returns:
        Requested value from Kedro context dictionary or the default if the key
            was not found.

    Raises:
        KedroCliError: When the key is not found and the default value was not
            specified.
    """
    warnings.warn(
        "`get_project_context` is now deprecated and will be removed in Kedro 0.18.0. "
        "Please use `KedroSession.load_context()` to access the "
        "`KedroContext` object. For more information, please visit "
        "https://kedro.readthedocs.io/en/stable/04_kedro_project_setup/03_session.html",
        DeprecationWarning,
    )
    project_path = project_path or Path.cwd()
    context = load_context(project_path, **kwargs)
    # Dictionary to be compatible with existing Plugins. Future plugins should
    # retrieve necessary Kedro project properties from context
    value = {"context": context, "verbose": KedroCliError.VERBOSE_ERROR}[key]

    return deepcopy(value)


def _init_plugins():
    group = ENTRY_POINT_GROUPS["init"]
    for entry_point in pkg_resources.iter_entry_points(group=group):
        try:
            init_hook = entry_point.load()
            init_hook()
        except Exception as exc:
            raise KedroCliError(f"Initializing {entry_point}") from exc


class KedroCLI(CommandCollection):
    """A CommandCollection class to encapsulate the KedroCLI command
    loading.
    """

    def __init__(self, project_path: Path):
        self._metadata = None  # running in package mode
        if _is_project(project_path):
            self._metadata = bootstrap_project(project_path)
        self._cli_hook_manager = get_cli_hook_manager()

        super().__init__(
            ("Global commands", self.global_groups),
            ("Project specific commands", self.project_groups),
        )

    def main(
        self,
        args=None,
        prog_name=None,
        complete_var=None,
        standalone_mode=True,
        **extra,
    ):
        if self._metadata:
            extra.update(obj=self._metadata)

        # This is how click's internals parse sys.argv, which include the command,
        # subcommand, arguments and options. click doesn't store this information anywhere
        # so we have to re-do it.
        # https://github.com/pallets/click/blob/main/src/click/core.py#L942-L945
        args = get_os_args() if args is None else list(args)
        self._cli_hook_manager.hook.before_command_run(  # pylint: disable=no-member
            project_metadata=self._metadata, command_args=args
        )

        super().main(
            args=args,
            prog_name=prog_name,
            complete_var=complete_var,
            standalone_mode=standalone_mode,
            **extra,
        )

    @property
    def global_groups(self) -> Sequence[click.MultiCommand]:
        """Property which loads all global command groups from plugins and
        combines them with the built-in ones (eventually overriding the
        built-in ones if they are redefined by plugins).
        """
        return [cli, create_cli, *load_entry_points("global")]

    @property
    def project_groups(self) -> Sequence[click.MultiCommand]:
        """Property which loads all project command groups from the
        project and the plugins, then combines them with the built-in ones.
        Built-in commands can be overridden by plugins, which can be
        overridden by the project's cli.py.
        """
        if not self._metadata:
            return []

        built_in = [catalog_cli, jupyter_cli, pipeline_cli, project_group, registry_cli]

        plugins = load_entry_points("project")

        try:
            project_cli = importlib.import_module(f"{self._metadata.package_name}.cli")
            # fail gracefully if cli.py does not exist
        except ModuleNotFoundError:
            # return only built-in commands and commands from plugins
            # (plugins can override built-in commands)
            return [*built_in, *plugins]

        # fail badly if cli.py exists, but has no `cli` in it
        if not hasattr(project_cli, "cli"):
            raise KedroCliError(
                f"Cannot load commands from {self._metadata.package_name}.cli"
            )
        user_defined = project_cli.cli  # type: ignore
        # return built-in commands, plugin commands and user defined commands
        # (overriding happens as follows built-in < plugins < cli.py)
        return [*built_in, *plugins, user_defined]


def main():  # pragma: no cover
    """Main entry point. Look for a ``cli.py``, and, if found, add its
    commands to `kedro`'s before invoking the CLI.
    """
    _init_plugins()
    cli_collection = KedroCLI(project_path=Path.cwd())
    cli_collection()
