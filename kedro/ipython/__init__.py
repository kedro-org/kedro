"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from IPython import get_ipython
from IPython.core.magic import needs_local_scope, register_line_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from kedro.framework.cli import load_entry_points
from kedro.framework.cli.project import CONF_SOURCE_HELP, PARAMS_ARG_HELP
from kedro.framework.cli.utils import ENV_HELP, _split_params
from kedro.framework.project import (
    LOGGING,  # noqa
    configure_project,
    pipelines,
)
from kedro.framework.session import KedroSession
from kedro.framework.startup import _is_project, bootstrap_project

logger = logging.getLogger(__name__)


def load_ipython_extension(ipython):
    """
    Main entry point when %load_ext kedro.ipython is executed, either manually or
    automatically through `kedro ipython` or `kedro jupyter lab/notebook`.
    IPython will look for this function specifically.
    See https://ipython.readthedocs.io/en/stable/config/extensions/index.html
    """
    ipython.register_magic_function(magic_reload_kedro, magic_name="reload_kedro")

    if _find_kedro_project(Path.cwd()) is None:
        logger.warning(
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        return

    reload_kedro()


@needs_local_scope
@magic_arguments()
@argument(
    "path",
    type=str,
    help=(
        "Path to the project root directory. If not given, use the previously set"
        "project root."
    ),
    nargs="?",
    default=None,
)
@argument("-e", "--env", type=str, default=None, help=ENV_HELP)
@argument(
    "--params",
    type=lambda value: _split_params(None, None, value),
    default=None,
    help=PARAMS_ARG_HELP,
)
@argument("--conf-source", type=str, default=None, help=CONF_SOURCE_HELP)
def magic_reload_kedro(
    line: str, local_ns: dict[str, Any] = None, conf_source: str = None
):
    """
    The `%reload_kedro` IPython line magic.
    See https://kedro.readthedocs.io/en/stable/notebooks_and_ipython/kedro_and_notebooks.html#reload-kedro-line-magic # noqa: line-too-long
    for more.
    """
    args = parse_argstring(magic_reload_kedro, line)
    reload_kedro(args.path, args.env, args.params, local_ns, args.conf_source)


def reload_kedro(
    path: str = None,
    env: str = None,
    extra_params: dict[str, Any] = None,
    local_namespace: dict[str, Any] | None = None,
    conf_source: str = None,
) -> None:  # pragma: no cover
    """Function that underlies the %reload_kedro Line magic. This should not be imported
    or run directly but instead invoked through %reload_kedro."""

    project_path = _resolve_project_path(path, local_namespace)

    metadata = bootstrap_project(project_path)
    _remove_cached_modules(metadata.package_name)
    configure_project(metadata.package_name)

    session = KedroSession.create(
        project_path,
        env=env,
        extra_params=extra_params,
        conf_source=conf_source,
    )
    context = session.load_context()
    catalog = context.catalog

    get_ipython().push(
        variables={
            "context": context,
            "catalog": catalog,
            "session": session,
            "pipelines": pipelines,
        }
    )

    logger.info("Kedro project %s", str(metadata.project_name))
    logger.info(
        "Defined global variable 'context', 'session', 'catalog' and 'pipelines'"
    )

    for line_magic in load_entry_points("line_magic"):
        register_line_magic(needs_local_scope(line_magic))
        logger.info("Registered line magic '%s'", line_magic.__name__)  # type: ignore


def _resolve_project_path(
    path: str | None = None, local_namespace: dict[str, Any] | None = None
) -> Path:
    """
    Resolve the project path to use with reload_kedro, updating or adding it
    (in-place) to the local ipython Namespace (``local_namespace``) if necessary.

    Arguments:
        path: the path to use as a string object
        local_namespace: Namespace with local variables of the scope where the line
            magic is invoked in a dict.
    """
    if path:
        project_path = Path(path).expanduser().resolve()
    else:
        if local_namespace and "context" in local_namespace:
            # noqa: protected-access
            project_path = local_namespace["context"].project_path
        else:
            project_path = _find_kedro_project(Path.cwd())
        if project_path:
            logger.info(
                "Resolved project path as: %s.\nTo set a different path, run "
                "'%%reload_kedro <project_root>'",
                project_path,
            )

    # noqa: protected-access
    if (
        project_path
        and local_namespace
        and "context" in local_namespace
        and project_path != local_namespace["context"].project_path
    ):
        logger.info("Updating path to Kedro project: %s...", project_path)

    return project_path


def _remove_cached_modules(package_name):  # pragma: no cover
    to_remove = [mod for mod in sys.modules if mod.startswith(package_name)]
    # `del` is used instead of `reload()` because: If the new version of a module does not
    # define a name that was defined by the old version, the old definition remains.
    for module in to_remove:
        del sys.modules[module]


def _find_kedro_project(current_dir: Path):  # pragma: no cover
    while current_dir != current_dir.parent:
        if _is_project(current_dir):
            return current_dir
        current_dir = current_dir.parent

    return None
