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
import warnings
import webbrowser
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, List

import click
import pkg_resources

# pylint: disable=unused-import
import kedro.config.default_logger  # noqa
from kedro import __version__ as version
from kedro.framework.cli.starters import create_cli
from kedro.framework.cli.utils import CommandCollection, KedroCliError, _add_src_to_path
from kedro.framework.context.context import load_context
from kedro.framework.project import configure_project
from kedro.framework.startup import _get_project_metadata, _is_project

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

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
def cli():
    """Kedro is a CLI for creating and using Kedro projects
    For more information, type ``kedro info``.

    When inside a Kedro project (created with ``kedro new``) commands
    from the project's ``cli.py`` file will also be available here.
    """
    pass


ENTRY_POINT_GROUPS = {
    "global": "kedro.global_commands",
    "project": "kedro.project_commands",
    "init": "kedro.init",
    "line_magic": "kedro.line_magic",
}


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


def get_project_context(
    key: str = "context", project_path: Path = None, **kwargs
) -> Any:
    """Gets the context value from context associated with the key.

    Args:
        key: Optional key to get associated value from Kedro context.
            Supported keys are "verbose" and "context", and it defaults to "context".
        project_path: Optional path to where the project root is to load the context.
            If omitted, the current working directory will be used.
        kwargs: Optional custom arguments defined by users, which will be passed into
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


def load_entry_points(name: str) -> List[str]:
    """Load package entry point commands.

    Args:
        name: The key value specified in ENTRY_POINT_GROUPS.

    Raises:
        KedroCliError: If loading an entry point failed.

    Returns:
        List of entry point commands.

    """
    entry_points = pkg_resources.iter_entry_points(group=ENTRY_POINT_GROUPS[name])
    entry_point_commands = []
    for entry_point in entry_points:
        try:
            entry_point_commands.append(entry_point.load())
        except Exception as exc:
            raise KedroCliError(f"Loading {name} commands from {entry_point}") from exc
    return entry_point_commands


def _init_plugins():
    group = ENTRY_POINT_GROUPS["init"]
    for entry_point in pkg_resources.iter_entry_points(group=group):
        try:
            init_hook = entry_point.load()
            init_hook()
        except Exception as exc:
            raise KedroCliError(f"Initializing {entry_point}") from exc


def main():  # pragma: no cover
    """Main entry point. Look for a ``cli.py``, and, if found, add its
    commands to `kedro`'s before invoking the CLI.
    """
    _init_plugins()
    global_groups = [cli, create_cli]
    global_groups.extend(load_entry_points("global"))
    project_groups = []
    cli_context = dict()

    path = Path.cwd()
    if _is_project(path):
        # load project commands from cli.py
        metadata = _get_project_metadata(path)
        package_name = metadata.package_name
        cli_context = dict(obj=metadata)
        _add_src_to_path(metadata.source_dir, path)
        configure_project(package_name)

        project_groups.extend(load_entry_points("project"))

        try:
            project_cli = importlib.import_module(f"{package_name}.cli")
            project_groups.append(project_cli.cli)
        except Exception as exc:
            raise KedroCliError(
                f"Cannot load commands from {package_name}.cli"
            ) from exc

    cli_collection = CommandCollection(
        ("Global commands", global_groups),
        ("Project specific commands", project_groups),
    )
    cli_collection(**cli_context)
