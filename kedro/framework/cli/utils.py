"""Utilities for use with click."""

from __future__ import annotations

import difflib
import importlib
import logging
import shlex
import shutil
import subprocess
import sys
import textwrap
import traceback
import typing
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
from importlib import import_module
from itertools import chain
from pathlib import Path
from typing import IO, Any, Callable

import click
import importlib_metadata
from omegaconf import OmegaConf

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
MAX_SUGGESTIONS = 3
CUTOFF = 0.5

ENV_HELP = "Kedro configuration environment name. Defaults to `local`."

ENTRY_POINT_GROUPS = {
    "global": "kedro.global_commands",
    "project": "kedro.project_commands",
    "init": "kedro.init",
    "line_magic": "kedro.line_magic",
    "hooks": "kedro.hooks",
    "cli_hooks": "kedro.cli_hooks",
    "starters": "kedro.starters",
}

logger = logging.getLogger(__name__)


def call(cmd: list[str], **kwargs: Any) -> None:  # pragma: no cover
    """Run a subprocess command and raise if it fails.

    Args:
        cmd: List of command parts.
        **kwargs: Optional keyword arguments passed to `subprocess.run`.

    Raises:
        click.exceptions.Exit: If `subprocess.run` returns non-zero code.
    """
    click.echo(shlex.join(cmd))
    code = subprocess.run(cmd, **kwargs).returncode  # noqa: PLW1510, S603
    if code:
        raise click.exceptions.Exit(code=code)


def python_call(
    module: str, arguments: Iterable[str], **kwargs: Any
) -> None:  # pragma: no cover
    """Run a subprocess command that invokes a Python module."""
    call([sys.executable, "-m", module, *list(arguments)], **kwargs)


def forward_command(
    group: Any, name: str | None = None, forward_help: bool = False
) -> Any:
    """A command that receives the rest of the command line as 'args'."""

    def wrapit(func: Any) -> Any:
        func = click.argument("args", nargs=-1, type=click.UNPROCESSED)(func)
        func = command_with_verbosity(
            group,
            name=name,
            context_settings={
                "ignore_unknown_options": True,
                "help_option_names": [] if forward_help else ["-h", "--help"],
            },
        )(func)
        return func

    return wrapit


def _suggest_cli_command(
    original_command_name: str, existing_command_names: Iterable[str]
) -> str:
    matches = difflib.get_close_matches(
        original_command_name, existing_command_names, MAX_SUGGESTIONS, CUTOFF
    )

    if not matches:
        return ""

    if len(matches) == 1:
        suggestion = "\n\nDid you mean this?"
    else:
        suggestion = "\n\nDid you mean one of these?\n"
    suggestion += textwrap.indent("\n".join(matches), " " * 4)
    return suggestion


def validate_conf_source(ctx: click.Context, param: Any, value: str) -> str | None:
    """Validate the conf_source, only checking existence for local paths."""
    if not value:
        return None

    # Check for remote URLs (except file://)
    if "://" in value and not value.startswith("file://"):
        return value

    # For local paths
    try:
        path = Path(value)
        if not path.exists():
            raise click.BadParameter(f"Path '{value}' does not exist.")
        return str(path.resolve())
    except click.BadParameter:
        # Re-raise Click exceptions
        raise
    except Exception as exc:
        # Wrap other exceptions
        raise click.BadParameter(f"Invalid path: {value}. Error: {exc!s}")


class CommandCollection(click.CommandCollection):
    """Modified from the Click one to still run the source groups function."""

    def __init__(self, *groups: tuple[str, Sequence[click.MultiCommand]]):
        self.groups = [
            (title, self._merge_same_name_collections(cli_list))
            for title, cli_list in groups
        ]
        sources = list(chain.from_iterable(cli_list for _, cli_list in self.groups))
        help_texts = [
            cli.help
            for cli_collection in sources
            for cli in cli_collection.sources
            if cli.help
        ]
        super().__init__(
            sources=sources,  # type: ignore[arg-type]
            help="\n\n".join(help_texts),
            context_settings=CONTEXT_SETTINGS,
        )
        self.params = sources[0].params
        self.callback = sources[0].callback

    @staticmethod
    def _merge_same_name_collections(
        groups: Sequence[click.MultiCommand],
    ) -> list[click.CommandCollection]:
        named_groups: defaultdict[str, list[click.MultiCommand]] = defaultdict(list)
        helps: defaultdict[str, list] = defaultdict(list)
        for group in groups:
            named_groups[group.name].append(group)  # type: ignore[index]
            if group.help:
                helps[group.name].append(group.help)  # type: ignore[index]
        return [
            click.CommandCollection(
                name=group_name,
                sources=cli_list,
                help="\n\n".join(helps[group_name]),
                callback=cli_list[0].callback,
                params=cli_list[0].params,
            )
            for group_name, cli_list in named_groups.items()
            if cli_list
        ]

    def resolve_command(
        self, ctx: click.core.Context, args: list
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as exc:
            original_command_name = click.utils.make_str(args[0])
            existing_command_names = self.list_commands(ctx)
            exc.message += _suggest_cli_command(
                original_command_name, existing_command_names
            )
            raise

    def format_commands(
        self, ctx: click.core.Context, formatter: click.formatting.HelpFormatter
    ) -> None:
        for title, cli in self.groups:
            for group in cli:
                if group.sources:
                    formatter.write(
                        click.style(f"\n{title} from {group.name}", fg="green")
                    )
                    group.format_commands(ctx, formatter)


def _update_verbose_flag(ctx: click.Context, param: Any, value: bool) -> None:
    KedroCliError.VERBOSE_ERROR = value


def _click_verbose(func: Any) -> Any:
    """Click option for enabling verbose mode."""
    return click.option(
        "--verbose",
        "-v",
        is_flag=True,
        callback=_update_verbose_flag,
        help="See extensive logging and error stack traces.",
    )(func)


def command_with_verbosity(group: click.core.Group, *args: Any, **kwargs: Any) -> Any:
    """Custom command decorator with verbose flag added."""

    def decorator(func: Any) -> Any:
        func = _click_verbose(func)
        func = group.command(*args, **kwargs)(func)
        return func

    return decorator


class KedroCliError(click.exceptions.ClickException):
    """Exceptions generated from the Kedro CLI.

    Users should pass an appropriate message at the constructor.
    """

    VERBOSE_ERROR = False
    VERBOSE_EXISTS = True
    COOKIECUTTER_EXCEPTIONS_PREFIX = "cookiecutter.exceptions"

    def show(self, file: IO | None = None) -> None:
        if self.VERBOSE_ERROR:
            click.secho(traceback.format_exc(), nl=False, fg="yellow")
        elif self.VERBOSE_EXISTS:
            etype, value, tb = sys.exc_info()
            formatted_exception = "".join(traceback.format_exception_only(etype, value))
            cookiecutter_exception = ""
            for ex_line in traceback.format_exception(etype, value, tb):
                if self.COOKIECUTTER_EXCEPTIONS_PREFIX in ex_line:
                    cookiecutter_exception = ex_line
                    break
            click.secho(
                f"{cookiecutter_exception}{formatted_exception}Run with --verbose to see the full exception",
                fg="yellow",
            )
        else:
            etype, value, _ = sys.exc_info()
            formatted_exception = "".join(traceback.format_exception_only(etype, value))
            click.secho(
                f"{formatted_exception}",
                fg="yellow",
            )


def _clean_pycache(path: Path) -> None:
    """Recursively clean all __pycache__ folders from `path`.

    Args:
        path: Existing local directory to clean __pycache__ folders from.
    """
    to_delete = [each.resolve() for each in path.rglob("__pycache__")]

    for each in to_delete:
        shutil.rmtree(each, ignore_errors=True)


def split_string(ctx: click.Context, param: Any, value: str) -> list[str]:
    """Split string by comma."""
    return [item.strip() for item in value.split(",") if item.strip()]


def split_node_names(ctx: click.Context, param: Any, to_split: str) -> list[str]:
    """Split string by comma, ignoring commas enclosed by square parentheses.
    This avoids splitting the string of nodes names on commas included in
    default node names, which have the pattern
    <function_name>([<input_name>,...]) -> [<output_name>,...])

    Note:
        - `to_split` will have such commas if and only if it includes a
        default node name. User-defined node names cannot include commas
        or square brackets.
        - This function will no longer be necessary from Kedro 0.19.*,
        in which default node names will no longer contain commas

    Args:
        to_split: the string to split safely

    Returns:
        A list containing the result of safe-splitting the string.
    """
    result = []
    argument, match_state = "", 0
    for char in to_split + ",":
        if char == "[":
            match_state += 1
        elif char == "]":
            match_state -= 1
        if char == "," and match_state == 0 and argument:
            argument = argument.strip()
            result.append(argument)
            argument = ""
        else:
            argument += char
    return result


def env_option(func_: Any | None = None, **kwargs: Any) -> Any:
    """Add `--env` CLI option to a function."""
    default_args = {"type": str, "default": None, "help": ENV_HELP}
    kwargs = {**default_args, **kwargs}
    opt = click.option("--env", "-e", **kwargs)
    return opt(func_) if func_ else opt


def _check_module_importable(module_name: str) -> None:
    try:
        import_module(module_name)
    except ImportError as exc:
        raise KedroCliError(
            f"Module '{module_name}' not found. Make sure to install required project "
            f"dependencies by running the 'pip install -r requirements.txt' command first."
        ) from exc


def _get_entry_points(name: str) -> Any:
    """Get all kedro related entry points"""
    return importlib_metadata.entry_points().select(  # type: ignore[no-untyped-call]
        group=ENTRY_POINT_GROUPS[name]
    )


def _safe_load_entry_point(
    entry_point: Any,
) -> Any:
    """Load entrypoint safely, if fails it will just skip the entrypoint."""
    try:
        return entry_point.load()
    except Exception as exc:
        logger.warning(
            "Failed to load %s commands from %s. Full exception: %s",
            entry_point.module,
            entry_point,
            exc,
        )
        return


def load_entry_points(name: str) -> Sequence[click.MultiCommand]:
    """Load package entry point commands.

    Args:
        name: The key value specified in ENTRY_POINT_GROUPS.

    Raises:
        KedroCliError: If loading an entry point failed.

    Returns:
        List of entry point commands.

    """

    entry_point_commands = []
    for entry_point in _get_entry_points(name):
        loaded_entry_point = _safe_load_entry_point(entry_point)
        if loaded_entry_point:
            entry_point_commands.append(loaded_entry_point)
    return entry_point_commands


def find_run_command(package_name: str) -> Callable:
    """Find the run command to be executed.
       This is either the default run command defined in the Kedro framework or a run command defined by
       an installed plugin.

    Args:
        package_name: The name of the package being run.

    Raises:
        KedroCliError: If the run command is not found.

    Returns:
        Run command to be executed.
    """
    try:
        project_cli = importlib.import_module(f"{package_name}.cli")
        # fail gracefully if cli.py does not exist
    except ModuleNotFoundError as exc:
        if f"{package_name}.cli" not in str(exc):
            raise
        plugins = load_entry_points("project")
        run = _find_run_command_in_plugins(plugins) if plugins else None
        if run:
            # use run command from installed plugin if it exists
            return run  # type: ignore[no-any-return]
        # use run command from `kedro.framework.cli.project`
        from kedro.framework.cli.project import run

        return run  # type: ignore[return-value]
    # fail badly if cli.py exists, but has no `cli` in it
    if not hasattr(project_cli, "cli"):
        raise KedroCliError(f"Cannot load commands from {package_name}.cli")
    return project_cli.run  # type: ignore[no-any-return]


def _find_run_command_in_plugins(plugins: Any) -> Any:
    for group in plugins:
        if "run" in group.commands:
            return group.commands["run"]


@typing.no_type_check
def _config_file_callback(ctx: click.Context, param: Any, value: Any) -> Any:
    """CLI callback that replaces command line options
    with values specified in a config file. If command line
    options are passed, they override config file values.
    """

    ctx.default_map = ctx.default_map or {}
    section = ctx.info_name

    if value:
        config = OmegaConf.to_container(OmegaConf.load(value))[section]
        for key, value in config.items():  # noqa: PLR1704
            _validate_config_file(key)
        ctx.default_map.update(config)

    return value


def _validate_config_file(key: str) -> None:
    """Validate the keys provided in the config file against the accepted keys."""
    from kedro.framework.cli.project import run

    run_args = [click_arg.name for click_arg in run.params]
    run_args.remove("config")
    if key not in run_args:
        KedroCliError.VERBOSE_EXISTS = False
        message = _suggest_cli_command(key, run_args)  # type: ignore[arg-type]
        raise KedroCliError(
            f"Key `{key}` in provided configuration is not valid. {message}"
        )


def _split_params(ctx: click.Context, param: Any, value: Any) -> Any:
    if isinstance(value, dict):
        return value
    dot_list = []
    for item in split_string(ctx, param, value):
        equals_idx = item.find("=")
        if equals_idx == -1:
            # If an equals sign is not found, fail with an error message.
            ctx.fail(
                f"Invalid format of `{param.name}` option: "
                f"Item `{item}` must contain a key and a value separated by `=`."
            )
        # Split the item into key and value
        key, _, val = item.partition("=")
        key = key.strip()
        if not key:
            # If the key is empty after stripping whitespace, fail with an error message.
            ctx.fail(
                f"Invalid format of `{param.name}` option: Parameter key "
                f"cannot be an empty string."
            )
        # Add "key=value" pair to dot_list.
        dot_list.append(f"{key}={val}")

    conf = OmegaConf.from_dotlist(dot_list)
    return OmegaConf.to_container(conf)


def _split_load_versions(ctx: click.Context, param: Any, value: str) -> dict[str, str]:
    """Split and format the string coming from the --load-versions
    flag in kedro run, e.g.:
    "dataset1:time1,dataset2:time2" -> {"dataset1": "time1", "dataset2": "time2"}

    Args:
        value: the string with the contents of the --load-versions flag.

    Returns:
        A dictionary with the formatted load versions data.
    """
    if not value:
        return {}

    lv_tuple = tuple(chain.from_iterable(value.split(",") for value in [value]))

    load_versions_dict = {}
    for load_version in lv_tuple:
        load_version = load_version.strip()  # noqa: PLW2901
        load_version_list = load_version.split(":", 1)
        if len(load_version_list) != 2:  # noqa: PLR2004
            raise KedroCliError(
                f"Expected the form of 'load_versions' to be "
                f"'dataset_name:YYYY-MM-DDThh.mm.ss.sssZ',"
                f"found {load_version} instead"
            )
        load_versions_dict[load_version_list[0]] = load_version_list[1]

    return load_versions_dict


class LazyGroup(click.Group):
    """A click Group that supports lazy loading of subcommands."""

    def __init__(
        self,
        *args: Any,
        lazy_subcommands: dict[str, str] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        # lazy_subcommands is a map of the form:
        #
        #   {command-name} -> {module-name}.{command-object-name}
        #
        self.lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = list(super().list_commands(ctx))
        lazy = sorted(self.lazy_subcommands.keys())
        return base + lazy

    def get_command(  # type: ignore[override]
        self, ctx: click.Context, cmd_name: str
    ) -> click.BaseCommand | click.Command | None:
        if cmd_name in self.lazy_subcommands:
            return self._lazy_load(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _lazy_load(self, cmd_name: str) -> click.BaseCommand:
        # lazily loading a command, first get the module name and attribute name
        import_path = self.lazy_subcommands[cmd_name]
        modname, cmd_object_name = import_path.rsplit(".", 1)
        # do the import
        mod = import_module(modname)
        # get the Command object from that module
        cmd_object = getattr(mod, cmd_object_name)
        return cmd_object  # type: ignore[no-any-return]
