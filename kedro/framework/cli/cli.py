"""kedro is a CLI for managing Kedro projects.

This module implements commands available from the kedro CLI.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from collections.abc import Sequence

from kedro import __version__ as version
from kedro.framework.cli import BRIGHT_BLACK, ORANGE
from kedro.framework.cli.hooks import get_cli_hook_manager
from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    ENTRY_POINT_GROUPS,
    CommandCollection,
    KedroCliError,
    LazyGroup,
    _get_entry_points,
    load_entry_points,
)
from kedro.framework.project import LOGGING  # noqa: F401
from kedro.framework.startup import bootstrap_project
from kedro.utils import find_kedro_project, is_kedro_project

LOGO = rf"""
 _            _
| | _____  __| |_ __ ___
| |/ / _ \/ _` | '__/ _ \
|   <  __/ (_| | | | (_) |
|_|\_\___|\__,_|_|  \___/
v{version}
"""


@click.group(context_settings=CONTEXT_SETTINGS, name="kedro")
@click.version_option(version, "--version", "-V", help="Show version and exit")
def cli() -> None:  # pragma: no cover
    """Kedro is a CLI for creating and using Kedro projects. For more
    information, type ``kedro info``.

    NOTE: If a command from a plugin conflicts with a built-in command from Kedro,
    the command from the plugin will take precedence.

    """
    pass


@cli.command()
def info() -> None:
    """Get more information about kedro."""
    click.secho(LOGO, fg="green")
    click.echo(
        "Kedro is a Python framework for\n"
        "creating reproducible, maintainable\n"
        "and modular data science code."
    )

    plugin_versions = {}
    plugin_entry_points = defaultdict(set)
    for plugin_entry_point in ENTRY_POINT_GROUPS:
        for entry_point in _get_entry_points(plugin_entry_point):
            module_name = entry_point.module.split(".")[0]
            plugin_versions[module_name] = entry_point.dist.version
            plugin_entry_points[module_name].add(plugin_entry_point)

    click.echo()
    if plugin_versions:
        click.echo("Installed plugins:")
        for plugin_name, plugin_version in sorted(plugin_versions.items()):
            entrypoints_str = ",".join(sorted(plugin_entry_points[plugin_name]))
            click.echo(
                f"{plugin_name}: {plugin_version} (entry points:{entrypoints_str})"
            )
    else:  # pragma: no cover
        click.echo("No plugins installed")


@click.group(
    context_settings=CONTEXT_SETTINGS,
    cls=LazyGroup,
    name="kedro",
    lazy_subcommands={
        "registry": "kedro.framework.cli.registry.registry",
        "catalog": "kedro.framework.cli.catalog.catalog",
        "ipython": "kedro.framework.cli.project.ipython",
        "run": "kedro.framework.cli.project.run",
        "package": "kedro.framework.cli.project.package",
        "jupyter": "kedro.framework.cli.jupyter.jupyter",
        "pipeline": "kedro.framework.cli.pipeline.pipeline",
    },
)
def project_commands() -> None:
    pass  # pragma: no cover


@click.group(
    context_settings=CONTEXT_SETTINGS,
    name="kedro",
    cls=LazyGroup,
    lazy_subcommands={
        "new": "kedro.framework.cli.starters.new",
        "starter": "kedro.framework.cli.starters.starter",
    },
)
def global_commands() -> None:
    pass  # pragma: no cover


def _init_plugins() -> None:
    init_hooks = load_entry_points("init")
    for init_hook in init_hooks:
        init_hook()


class KedroCLI(CommandCollection):
    """A CommandCollection class to encapsulate the KedroCLI command
    loading.
    """

    def __init__(self, project_path: Path):
        self._metadata = None  # running in package mode
        if is_kedro_project(project_path):
            self._metadata = bootstrap_project(project_path)
        self._cli_hook_manager = get_cli_hook_manager()

        super().__init__(
            ("Global commands", self.global_groups),
            ("Project specific commands", self.project_groups),
        )

    def main(
        self,
        args: Any | None = None,
        prog_name: Any | None = None,
        complete_var: Any | None = None,
        standalone_mode: bool = True,
        **extra: Any,
    ) -> Any:
        if self._metadata:
            extra.update(obj=self._metadata)

        # This is how click's internals parse sys.argv, which include the command,
        # subcommand, arguments and options. click doesn't store this information anywhere
        # so we have to re-do it.
        args = sys.argv[1:] if args is None else list(args)
        self._cli_hook_manager.hook.before_command_run(
            project_metadata=self._metadata, command_args=args
        )

        try:
            super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=standalone_mode,
                **extra,
            )
        # click.core.main() method exits by default, we capture this and then
        # exit as originally intended

        except SystemExit as exc:
            self._cli_hook_manager.hook.after_command_run(
                project_metadata=self._metadata, command_args=args, exit_code=exc.code
            )

            # When CLI is run outside of a project, project_groups are not registered
            catch_exception = "click.exceptions.UsageError: No such command"
            # click convert exception handles to error message
            if catch_exception in traceback.format_exc() and not self.project_groups:
                warn = click.style(
                    "\nKedro project not found in this directory. ",
                    fg=ORANGE,
                    bold=True,
                )
                result = (
                    click.style("Project specific commands such as ")
                    + click.style("'run' ", fg="cyan")
                    + "or "
                    + click.style("'jupyter' ", fg="cyan")
                    + "are only available within a project directory."
                )
                message = warn + result
                hint = (
                    click.style(
                        "\nHint: Kedro is looking for a file called ", fg=BRIGHT_BLACK
                    )
                    + click.style("'pyproject.toml", fg="magenta")
                    + click.style(
                        ", is one present in your current working directory?",
                        fg=BRIGHT_BLACK,
                    )
                )
                click.echo(message)
                click.echo(hint)
            sys.exit(exc.code)
        except Exception:
            self._cli_hook_manager.hook.after_command_run(
                project_metadata=self._metadata, command_args=args, exit_code=1
            )
            raise

    @property
    def global_groups(self) -> Sequence[click.MultiCommand]:
        """Property which loads all global command groups from plugins and
        combines them with the built-in ones (eventually overriding the
        built-in ones if they are redefined by plugins).
        """
        return [cli, *load_entry_points("global"), global_commands]

    @property
    def project_groups(self) -> Sequence[click.MultiCommand]:
        """Property which loads all project command groups from the
        project and the plugins, then combines them with the built-in ones.
        Built-in commands can be overridden by plugins, which can be
        overridden by a custom project cli.py.
        See https://docs.kedro.org/en/stable/extend_kedro/common_use_cases.html#use-case-3-how-to-add-or-modify-cli-commands
        on how to add this.
        """
        if not self._metadata:
            return []

        plugins = load_entry_points("project")

        try:
            project_cli = importlib.import_module(f"{self._metadata.package_name}.cli")
            # fail gracefully if cli.py does not exist
        except ModuleNotFoundError:
            # return only built-in commands and commands from plugins
            # (plugins can override built-in commands)
            return [*plugins, project_commands]

        # fail badly if cli.py exists, but has no `cli` in it
        if not hasattr(project_cli, "cli"):
            raise KedroCliError(
                f"Cannot load commands from {self._metadata.package_name}.cli"
            )
        user_defined = project_cli.cli
        # return built-in commands, plugin commands and user defined commands
        # (overriding happens as follows built-in < plugins < cli.py)
        return [user_defined, *plugins, project_commands]


def main() -> None:  # pragma: no cover
    """Main entry point. Look for a ``cli.py``, and, if found, add its
    commands to `kedro`'s before invoking the CLI.
    """
    _init_plugins()
    cli_collection = KedroCLI(project_path=find_kedro_project(Path.cwd()) or Path.cwd())
    cli_collection()
