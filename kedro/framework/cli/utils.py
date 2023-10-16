"""Utilities for use with click."""
from __future__ import annotations

import difflib
import logging
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import traceback
from collections import defaultdict
from importlib import import_module
from itertools import chain
from pathlib import Path
from typing import Iterable, Sequence

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


def call(cmd: list[str], **kwargs):  # pragma: no cover
    """Run a subprocess command and raise if it fails.

    Args:
        cmd: List of command parts.
        **kwargs: Optional keyword arguments passed to `subprocess.run`.

    Raises:
        click.exceptions.Exit: If `subprocess.run` returns non-zero code.
    """
    click.echo(" ".join(shlex.quote(c) for c in cmd))
    # noqa: subprocess-run-check
    code = subprocess.run(cmd, **kwargs).returncode
    if code:
        raise click.exceptions.Exit(code=code)


def python_call(module: str, arguments: Iterable[str], **kwargs):  # pragma: no cover
    """Run a subprocess command that invokes a Python module."""
    call([sys.executable, "-m", module] + list(arguments), **kwargs)


def find_stylesheets() -> Iterable[str]:  # pragma: no cover
    """Fetch all stylesheets used in the official Kedro documentation"""
    css_path = Path(__file__).resolve().parents[1] / "html" / "_static" / "css"
    return (
        str(css_path / "copybutton.css"),
        str(css_path / "qb1-sphinx-rtd.css"),
        str(css_path / "theme-overrides.css"),
    )


def forward_command(group, name=None, forward_help=False):
    """A command that receives the rest of the command line as 'args'."""

    def wrapit(func):
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
    suggestion += textwrap.indent("\n".join(matches), " " * 4)  # type: ignore
    return suggestion


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
        self._dedupe_commands(sources)
        super().__init__(
            sources=sources,
            help="\n\n".join(help_texts),
            context_settings=CONTEXT_SETTINGS,
        )
        self.params = sources[0].params
        self.callback = sources[0].callback

    @staticmethod
    def _dedupe_commands(cli_collections: Sequence[click.CommandCollection]):
        """Deduplicate commands by keeping the ones from the last source
        in the list.
        """
        seen_names: set[str] = set()
        for cli_collection in reversed(cli_collections):
            for cmd_group in reversed(cli_collection.sources):
                cmd_group.commands = {  # type: ignore
                    cmd_name: cmd
                    for cmd_name, cmd in cmd_group.commands.items()  # type: ignore
                    if cmd_name not in seen_names
                }
                seen_names |= cmd_group.commands.keys()  # type: ignore

        # remove empty command groups
        for cli_collection in cli_collections:
            cli_collection.sources = [
                cmd_group
                for cmd_group in cli_collection.sources
                if cmd_group.commands  # type: ignore
            ]

    @staticmethod
    def _merge_same_name_collections(groups: Sequence[click.MultiCommand]):
        named_groups: defaultdict[str, list[click.MultiCommand]] = defaultdict(list)
        helps: defaultdict[str, list] = defaultdict(list)
        for group in groups:
            named_groups[group.name].append(group)
            if group.help:
                helps[group.name].append(group.help)

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

    def resolve_command(self, ctx: click.core.Context, args: list):
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
    ):
        for title, cli in self.groups:
            for group in cli:
                if group.sources:
                    formatter.write(
                        click.style(f"\n{title} from {group.name}", fg="green")
                    )
                    group.format_commands(ctx, formatter)


def get_pkg_version(reqs_path: (str | Path), package_name: str) -> str:
    """Get package version from requirements.txt.

    Args:
        reqs_path: Path to requirements.txt file.
        package_name: Package to search for.

    Returns:
        Package and its version as specified in requirements.txt.

    Raises:
        KedroCliError: If the file specified in ``reqs_path`` does not exist
            or ``package_name`` was not found in that file.
    """
    reqs_path = Path(reqs_path).absolute()
    if not reqs_path.is_file():
        raise KedroCliError(f"Given path '{reqs_path}' is not a regular file.")

    pattern = re.compile(package_name + r"([^\w]|$)")
    with reqs_path.open("r", encoding="utf-8") as reqs_file:
        for req_line in reqs_file:
            req_line = req_line.strip()  # noqa: redefined-loop-name
            if pattern.search(req_line):
                return req_line

    raise KedroCliError(f"Cannot find '{package_name}' package in '{reqs_path}'.")


def _update_verbose_flag(ctx, param, value):  # noqa: unused-argument
    KedroCliError.VERBOSE_ERROR = value


def _click_verbose(func):
    """Click option for enabling verbose mode."""
    return click.option(
        "--verbose",
        "-v",
        is_flag=True,
        callback=_update_verbose_flag,
        help="See extensive logging and error stack traces.",
    )(func)


def command_with_verbosity(group: click.core.Group, *args, **kwargs):
    """Custom command decorator with verbose flag added."""

    def decorator(func):
        func = _click_verbose(func)
        func = group.command(*args, **kwargs)(func)
        return func

    return decorator


class KedroCliError(click.exceptions.ClickException):
    """Exceptions generated from the Kedro CLI.

    Users should pass an appropriate message at the constructor.
    """

    VERBOSE_ERROR = False

    def show(self, file=None):
        if file is None:
            # noqa: protected-access
            file = click._compat.get_text_stderr()
        if self.VERBOSE_ERROR:
            click.secho(traceback.format_exc(), nl=False, fg="yellow")
        else:
            etype, value, _ = sys.exc_info()
            formatted_exception = "".join(traceback.format_exception_only(etype, value))
            click.secho(
                f"{formatted_exception}Run with --verbose to see the full exception",
                fg="yellow",
            )
        click.secho(f"Error: {self.message}", fg="red", file=file)


def _clean_pycache(path: Path):
    """Recursively clean all __pycache__ folders from `path`.

    Args:
        path: Existing local directory to clean __pycache__ folders from.
    """
    to_delete = [each.resolve() for each in path.rglob("__pycache__")]

    for each in to_delete:
        shutil.rmtree(each, ignore_errors=True)


def split_string(ctx, param, value):  # noqa: unused-argument
    """Split string by comma."""
    return [item.strip() for item in value.split(",") if item.strip()]


# noqa: unused-argument,missing-param-doc,missing-type-doc
def split_node_names(ctx, param, to_split: str) -> list[str]:
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


def env_option(func_=None, **kwargs):
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


def _get_entry_points(name: str) -> importlib_metadata.EntryPoints:
    """Get all kedro related entry points"""
    return importlib_metadata.entry_points().select(group=ENTRY_POINT_GROUPS[name])


def _safe_load_entry_point(  # noqa: inconsistent-return-statements
    entry_point,
):
    """Load entrypoint safely, if fails it will just skip the entrypoint."""
    try:
        return entry_point.load()
    except Exception as exc:  # noqa: broad-except
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


def _config_file_callback(ctx, param, value):  # noqa: unused-argument
    """CLI callback that replaces command line options
    with values specified in a config file. If command line
    options are passed, they override config file values.
    """
    # for performance reasons
    import anyconfig  # noqa: import-outside-toplevel

    ctx.default_map = ctx.default_map or {}
    section = ctx.info_name

    if value:
        config = anyconfig.load(value)[section]
        ctx.default_map.update(config)

    return value


def _reformat_load_versions(ctx, param, value) -> dict[str, str]:
    """Reformat data structure from tuple to dictionary for `load-version`, e.g.:
    ('dataset1:time1', 'dataset2:time2') -> {"dataset1": "time1", "dataset2": "time2"}.
    """
    if param.name == "load_version":
        _deprecate_options(ctx, param, value)

    load_versions_dict = {}
    for load_version in value:
        load_version = load_version.strip()  # noqa: PLW2901
        load_version_list = load_version.split(":", 1)
        if len(load_version_list) != 2:  # noqa: PLR2004
            raise KedroCliError(
                f"Expected the form of 'load_version' to be "
                f"'dataset_name:YYYY-MM-DDThh.mm.ss.sssZ',"
                f"found {load_version} instead"
            )
        load_versions_dict[load_version_list[0]] = load_version_list[1]

    return load_versions_dict


def _split_params(ctx, param, value):
    if isinstance(value, dict):
        return value
    dot_list = []
    for item in split_string(ctx, param, value):
        equals_idx = item.find("=")
        colon_idx = item.find(":")
        if equals_idx != -1 and colon_idx != -1 and equals_idx < colon_idx:
            # For cases where key-value pair is separated by = and the value contains a colon
            # which should not be replaced by =
            pass
        else:
            item = item.replace(":", "=", 1)  # noqa: redefined-loop-name
        items = item.split("=", 1)
        if len(items) != 2:  # noqa: PLR2004
            ctx.fail(
                f"Invalid format of `{param.name}` option: "
                f"Item `{items[0]}` must contain "
                f"a key and a value separated by `:` or `=`."
            )
        key = items[0].strip()
        if not key:
            ctx.fail(
                f"Invalid format of `{param.name}` option: Parameter key "
                f"cannot be an empty string."
            )
        dot_list.append(item)
    conf = OmegaConf.from_dotlist(dot_list)
    return OmegaConf.to_container(conf)


def _split_load_versions(ctx, param, value):
    lv_tuple = _get_values_as_tuple([value])
    return _reformat_load_versions(ctx, param, lv_tuple) if value else {}


def _get_values_as_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(chain.from_iterable(value.split(",") for value in values))


def _deprecate_options(ctx, param, value):
    deprecated_flag = {
        "node_names": "--node",
        "tag": "--tag",
        "load_version": "--load-version",
    }
    new_flag = {
        "node_names": "--nodes",
        "tag": "--tags",
        "load_version": "--load-versions",
    }
    shorthand_flag = {
        "node_names": "-n",
        "tag": "-t",
        "load_version": "-lv",
    }
    if value:
        deprecation_message = (
            f"DeprecationWarning: 'kedro run' flag '{deprecated_flag[param.name]}' is deprecated "
            "and will not be available from Kedro 0.19.0. "
            f"Use the flag '{new_flag[param.name]}' instead. Shorthand "
            f"'{shorthand_flag[param.name]}' will be updated to use "
            f"'{new_flag[param.name]}' in Kedro 0.19.0."
        )
        click.secho(deprecation_message, fg="red")
    return value
