# Copyright 2021 QuantumBlack Visual Analytics Limited
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

"""kedro is a CLI for managing Kedro projects.

This module implements commands available from the kedro CLI.
"""
import importlib
import webbrowser
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import click
import pkg_resources

# pylint: disable=unused-import
import kedro.config.default_logger  # noqa
from kedro import __version__ as version
from kedro.framework.cli.catalog import catalog_cli
from kedro.framework.cli.jupyter import jupyter_cli
from kedro.framework.cli.pipeline import pipeline_cli
from kedro.framework.cli.project import project_group
from kedro.framework.cli.starters import create_cli
from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    ENTRY_POINT_GROUPS,
    CommandCollection,
    KedroCliError,
    _add_src_to_path,
    load_entry_points,
)
from kedro.framework.project import configure_project
from kedro.framework.startup import _get_project_metadata, _is_project

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
    """Get more information about kedro.
    """
    click.secho(LOGO, fg="green")
    click.echo(
        "kedro allows teams to create analytics\n"
        "projects. It is developed as part of\n"
        "the Kedro initiative at QuantumBlack."
    )

    plugin_versions = {}
    plugin_hooks = defaultdict(set)
    for hook, group in ENTRY_POINT_GROUPS.items():
        for entry_point in pkg_resources.iter_entry_points(group=group):
            module_name = entry_point.module_name.split(".")[0]
            plugin_version = pkg_resources.get_distribution(module_name).version
            plugin_versions[module_name] = plugin_version
            plugin_hooks[module_name].add(hook)

    click.echo()
    if plugin_versions:
        click.echo("Installed plugins:")
        for plugin_name, plugin_version in sorted(plugin_versions.items()):
            hooks = ",".join(sorted(plugin_hooks[plugin_name]))
            click.echo(f"{plugin_name}: {plugin_version} (hooks:{hooks})")
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
        self._metadata = self._load_project(project_path)

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
        super().main(
            args=args,
            prog_name=prog_name,
            complete_var=complete_var,
            standalone_mode=standalone_mode,
            **extra,
        )

    @property
    def global_groups(self) -> Sequence[click.MultiCommand]:
        """Lazy property which loads all global command groups from plugins and
        combines them with the built-in ones (eventually overriding the
        built-in ones if they are redefined by plugins).
        """
        return [cli, create_cli, *load_entry_points("global")]

    @property
    def project_groups(self) -> Sequence[click.MultiCommand]:
        """Lazy property which loads all project command groups from the
        project and the plugins, then combines them with the built-in ones.
        Built-in commands can be overridden by plugins, which can be
        overridden by the project's cli.py.
        """
        if not self._metadata:
            return []

        built_in = [
            catalog_cli,
            jupyter_cli,
            pipeline_cli,
            project_group,
        ]

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

    @staticmethod
    def _load_project(project_path):  # pragma: no cover
        # TODO: This one can potentially become project bootstrap and will be
        #  tested there
        if not _is_project(project_path):
            return None
        metadata = _get_project_metadata(project_path)
        _add_src_to_path(metadata.source_dir, project_path)
        configure_project(metadata.package_name)
        return metadata


def main():  # pragma: no cover
    """Main entry point. Look for a ``cli.py``, and, if found, add its
    commands to `kedro`'s before invoking the CLI.
    """
    _init_plugins()
    cli_collection = KedroCLI(project_path=Path.cwd())
    cli_collection()
