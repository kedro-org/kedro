"""Utilities for use with click."""
import difflib
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import traceback
import warnings
from collections import defaultdict
from contextlib import contextmanager
from importlib import import_module
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple, Union

import click
import pkg_resources

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
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
}


def call(cmd: List[str], **kwargs):  # pragma: no cover
    """Run a subprocess command and raise if it fails.

    Args:
        cmd: List of command parts.
        **kwargs: Optional keyword arguments passed to `subprocess.run`.

    Raises:
        click.exceptions.Exit: If `subprocess.run` returns non-zero code.
    """
    click.echo(" ".join(shlex.quote(c) for c in cmd))
    # pylint: disable=subprocess-run-check
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
            context_settings=dict(
                ignore_unknown_options=True,
                help_option_names=[] if forward_help else ["-h", "--help"],
            ),
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

    def __init__(self, *groups: Tuple[str, Sequence[click.MultiCommand]]):
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
        seen_names: Set[str] = set()
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
        named_groups: Mapping[str, List[click.MultiCommand]] = defaultdict(list)
        helps: Mapping[str, list] = defaultdict(list)
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

    def resolve_command(self, ctx: click.core.Context, args: List):
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


def get_pkg_version(reqs_path: (Union[str, Path]), package_name: str) -> str:
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
        raise KedroCliError(f"Given path `{reqs_path}` is not a regular file.")

    pattern = re.compile(package_name + r"([^\w]|$)")
    with reqs_path.open("r", encoding="utf-8") as reqs_file:
        for req_line in reqs_file:
            req_line = req_line.strip()
            if pattern.search(req_line):
                return req_line

    raise KedroCliError(f"Cannot find `{package_name}` package in `{reqs_path}`.")


def _update_verbose_flag(ctx, param, value):  # pylint: disable=unused-argument
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
            # pylint: disable=protected-access
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


def split_string(ctx, param, value):  # pylint: disable=unused-argument
    """Split string by comma."""
    return [item.strip() for item in value.split(",") if item.strip()]


def env_option(func_=None, **kwargs):
    """Add `--env` CLI option to a function."""
    default_args = dict(type=str, default=None, help=ENV_HELP)
    kwargs = {**default_args, **kwargs}
    opt = click.option("--env", "-e", **kwargs)
    return opt(func_) if func_ else opt


def ipython_message(all_kernels=True):
    """Show a message saying how we have configured the IPython env."""
    ipy_vars = ["startup_error", "context"]
    click.secho("-" * 79, fg="cyan")
    click.secho("Starting a Kedro session with the following variables in scope")
    click.secho(", ".join(ipy_vars), fg="green")
    line_magic = click.style("%reload_kedro", fg="green")
    click.secho(f"Use the line magic {line_magic} to refresh them")
    click.secho("or to see the error message if they are undefined")

    if not all_kernels:
        click.secho("The choice of kernels is limited to the default one.", fg="yellow")
        click.secho("(restart with --all-kernels to get access to others)", fg="yellow")

    click.secho("-" * 79, fg="cyan")


@contextmanager
def _filter_deprecation_warnings():
    """Temporarily suppress all DeprecationWarnings."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        yield


def _check_module_importable(module_name: str) -> None:
    try:
        import_module(module_name)
    except ImportError as exc:
        raise KedroCliError(
            f"Module `{module_name}` not found. Make sure to install required project "
            f"dependencies by running the `kedro install` command first."
        ) from exc


def load_entry_points(name: str) -> Sequence[click.MultiCommand]:
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


def _add_src_to_path(source_dir: Path, project_path: Path) -> None:  # pragma: no cover
    # for backwards compatibility with ipython & deployment scripts
    # pylint: disable=import-outside-toplevel
    from kedro.framework.startup import _add_src_to_path as real_add_src_to_path

    msg = (
        "kedro.framework.utils._add_src_to_path is deprecated. "
        "Please import from new location kedro.framework.startup "
        "or use `bootstrap_project()` instead for setting up "
        "the Kedro project."
    )
    warnings.warn(msg, FutureWarning)
    real_add_src_to_path(source_dir, project_path)


def _config_file_callback(ctx, param, value):  # pylint: disable=unused-argument
    """CLI callback that replaces command line options
    with values specified in a config file. If command line
    options are passed, they override config file values.
    """
    # for performance reasons
    import anyconfig  # pylint: disable=import-outside-toplevel

    ctx.default_map = ctx.default_map or {}
    section = ctx.info_name

    if value:
        config = anyconfig.load(value)[section]
        ctx.default_map.update(config)

    return value


def _reformat_load_versions(  # pylint: disable=unused-argument
    ctx, param, value
) -> Dict[str, str]:
    """Reformat data structure from tuple to dictionary for `load-version`, e.g.:
    ('dataset1:time1', 'dataset2:time2') -> {"dataset1": "time1", "dataset2": "time2"}.
    """
    load_versions_dict = {}

    for load_version in value:
        load_version_list = load_version.split(":", 1)
        if len(load_version_list) != 2:
            raise KedroCliError(
                f"Expected the form of `load_version` to be "
                f"`dataset_name:YYYY-MM-DDThh.mm.ss.sssZ`,"
                f"found {load_version} instead"
            )
        load_versions_dict[load_version_list[0]] = load_version_list[1]

    return load_versions_dict


def _try_convert_to_numeric(value):
    try:
        value = float(value)
    except ValueError:
        return value
    return int(value) if value.is_integer() else value


def _split_params(ctx, param, value):
    if isinstance(value, dict):
        return value
    result = {}
    for item in split_string(ctx, param, value):
        item = item.split(":", 1)
        if len(item) != 2:
            ctx.fail(
                f"Invalid format of `{param.name}` option: "
                f"Item `{item[0]}` must contain "
                f"a key and a value separated by `:`."
            )
        key = item[0].strip()
        if not key:
            ctx.fail(
                f"Invalid format of `{param.name}` option: Parameter key "
                f"cannot be an empty string."
            )
        value = item[1].strip()
        result = _update_value_nested_dict(
            result, _try_convert_to_numeric(value), key.split(".")
        )
    return result


def _update_value_nested_dict(
    nested_dict: Dict[str, Any], value: Any, walking_path: List[str]
) -> Dict:
    """Update nested dict with value using walking_path as a parse tree to walk
    down the nested dict.

    Example:
    ::
        >>> nested_dict = {"foo": {"hello": "world", "bar": 1}}
        >>> _update_value_nested_dict(nested_dict, value=2, walking_path=["foo", "bar"])
        >>> print(nested_dict)
        >>> {'foo': {'hello': 'world', 'bar': 2}}

    Args:
        nested_dict: dict to be updated
        value: value to update the nested_dict with
        walking_path: list of nested keys to use to walk down the nested_dict

    Returns:
        nested_dict updated with value at path `walking_path`
    """
    key = walking_path.pop(0)
    if not walking_path:
        nested_dict[key] = value
        return nested_dict
    nested_dict[key] = _update_value_nested_dict(
        nested_dict.get(key, {}), value, walking_path
    )
    return nested_dict


def _get_requirements_in(source_path: Path, create_empty: bool = False) -> Path:
    """Get path to project level requirements.in, creating it if required.

    Args:
        source_path: Path to the project `src` folder.
        create_empty: Whether an empty requirements.in file should be created if
            requirements.in does not exist and there is also no requirements.txt to
            copy requirements from.

    Returns:
        Path to requirements.in.

    Raises:
        FileNotFoundError: If neither requirements.in nor requirements.txt is found.

    """
    requirements_in = source_path / "requirements.in"
    if requirements_in.is_file():
        return requirements_in

    requirements_txt = source_path / "requirements.txt"
    if requirements_txt.is_file():
        click.secho(
            "No requirements.in found. Copying contents from requirements.txt..."
        )
        shutil.copyfile(str(requirements_txt), str(requirements_in))
        return requirements_in

    if create_empty:
        click.secho("Creating empty requirements.in...")
        requirements_in.touch()
        return requirements_in

    raise FileNotFoundError(
        "No project requirements.in or requirements.txt found in `/src`. "
        "Please create either and try again."
    )


def _get_values_as_tuple(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(chain.from_iterable(value.split(",") for value in values))
