"""Abstract base class for Kedro session implementations."""

from __future__ import annotations

import getpass
import logging
import os
import subprocess
import sys
import traceback
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from kedro import __version__ as kedro_version
from kedro.framework import project as kedro_project
from kedro.framework.hooks import _create_hook_manager
from kedro.framework.hooks.manager import _register_hooks, _register_hooks_entry_points
from kedro.framework.project import (
    pipelines,
    settings,
    validate_settings,
)
from kedro.io.core import generate_timestamp
from kedro.io.data_catalog import SharedMemoryDataCatalog
from kedro.pipeline.pipeline import Pipeline
from kedro.runner import AbstractRunner, ParallelRunner, SequentialRunner
from kedro.utils import find_kedro_project

if TYPE_CHECKING:
    from collections.abc import Iterable

    from kedro.config import AbstractConfigLoader
    from kedro.framework.context import KedroContext
    from kedro.framework.session.store import BaseSessionStore


def _describe_git(project_path: Path) -> dict[str, dict[str, Any]]:
    """Retrieve git information for a project path."""
    path = str(project_path)
    try:
        res = subprocess.check_output(  # noqa: S603
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=path,
            stderr=subprocess.STDOUT,
        )
        git_data: dict[str, Any] = {"commit_sha": res.decode().strip()}
        git_status_res = subprocess.check_output(  # noqa: S603
            ["git", "status", "--short"],  # noqa: S607
            cwd=path,
            stderr=subprocess.STDOUT,
        )
        git_data["dirty"] = bool(git_status_res.decode().strip())

    # `subprocess.check_output()` raises `NotADirectoryError` on Windows
    except Exception:
        logger = logging.getLogger(__name__)
        logger.debug("Unable to git describe %s", path)
        logger.debug(traceback.format_exc())
        return {}

    return {"git": git_data}


def _jsonify_cli_context(ctx: click.core.Context) -> dict[str, Any]:
    """Convert click context to a serializable dictionary."""
    return {
        "args": ctx.args,
        "params": ctx.params,
        "command_name": ctx.command.name,
        "command_path": " ".join(["kedro"] + sys.argv[1:]),
    }


class KedroSessionError(Exception):
    """Exception raised by KedroSession for session-related errors."""

    pass


class AbstractSession(ABC):
    """Abstract base class for Kedro session implementations.

    This class defines the common interface and shared functionality for
    different session types (e.g., KedroSession, KedroServiceSession).
    """

    def __init__(
        self,
        session_id: str,
        package_name: str | None = None,
        project_path: Path | str | None = None,
        save_on_close: bool = False,
        conf_source: str | None = None,
    ):
        """Initialize an AbstractSession.

        Args:
            session_id: A unique identifier for the session.
            package_name: The package name of the Kedro project.
            project_path: Path to the project root directory.
            save_on_close: Whether to save the session when closed.
            conf_source: Path to the configuration source directory.
        """
        self._project_path = Path(
            project_path or find_kedro_project(Path.cwd()) or Path.cwd()
        ).resolve()
        self.session_id = session_id
        self.save_on_close = save_on_close
        self._package_name = package_name or kedro_project.PACKAGE_NAME
        self._store = self._init_store()

        hook_manager = _create_hook_manager()
        _register_hooks(hook_manager, settings.HOOKS)
        _register_hooks_entry_points(hook_manager, settings.DISABLE_HOOKS_FOR_PLUGINS)
        self._hook_manager = hook_manager

        self._conf_source = conf_source or str(
            self._project_path / settings.CONF_SOURCE
        )

    def _init_store(self) -> BaseSessionStore:
        """Initialize the session store."""
        store_class = settings.SESSION_STORE_CLASS
        classpath = f"{store_class.__module__}.{store_class.__qualname__}"
        store_args = deepcopy(settings.SESSION_STORE_ARGS)
        store_args.setdefault("path", (self._project_path / "sessions").as_posix())
        store_args["session_id"] = self.session_id

        try:
            return store_class(**store_args)  # type: ignore[no-any-return]
        except TypeError as err:
            raise ValueError(
                f"\n{err}.\nStore config must only contain arguments valid "
                f"for the constructor of '{classpath}'."
            ) from err
        except Exception as err:
            raise ValueError(
                f"\n{err}.\nFailed to instantiate session store of type '{classpath}'."
            ) from err

    def _log_exception(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        """Log an exception to the session store."""
        type_ = [] if exc_type.__module__ == "builtins" else [exc_type.__module__]
        type_.append(exc_type.__qualname__)

        exc_data = {
            "type": ".".join(type_),
            "value": str(exc_value),
            "traceback": traceback.format_tb(exc_tb),
        }
        self._store["exception"] = exc_data

    @property
    def _logger(self) -> logging.Logger:
        """Get the logger for this session."""
        return logging.getLogger(__name__)

    @property
    def store(self) -> dict[str, Any]:
        """Return a copy of internal store."""
        return dict(self._store)

    def load_context(
        self,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
    ) -> KedroContext:
        """Load a KedroContext instance.

        Args:
            env: Environment for the context. If None, uses session's stored env.
            runtime_params: Runtime parameters for the context. If None, uses session's stored params.

        Returns:
            A KedroContext instance.
        """
        env = env or self.store.get("env")
        runtime_params = runtime_params or self.store.get("runtime_params")
        config_loader = self._get_config_loader(env, runtime_params)
        context_class = settings.CONTEXT_CLASS
        context = context_class(
            package_name=self._package_name,
            project_path=self._project_path,
            config_loader=config_loader,
            env=env,
            runtime_params=runtime_params,
            hook_manager=self._hook_manager,
        )
        self._hook_manager.hook.after_context_created(context=context)

        return context  # type: ignore[no-any-return]

    def _get_config_loader(
        self,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
    ) -> AbstractConfigLoader:
        """Get a config loader instance.

        Args:
            env: Environment for the config loader. If None, uses session's stored env.
            runtime_params: Runtime parameters for the config loader. If None, uses session's stored params.

        Returns:
            An AbstractConfigLoader instance.
        """
        env = env or self.store.get("env")
        runtime_params = runtime_params or self.store.get("runtime_params")

        config_loader_class = settings.CONFIG_LOADER_CLASS
        return config_loader_class(  # type: ignore[no-any-return]
            conf_source=self._conf_source,
            env=env,
            runtime_params=runtime_params,
            **settings.CONFIG_LOADER_ARGS,
        )

    def close(self) -> None:
        """Close the session and save its store if configured."""
        if self.save_on_close:
            self._store.save()

    def __enter__(self) -> AbstractSession:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, tb_: Any) -> None:
        """Context manager exit."""
        if exc_type:
            self._log_exception(exc_type, exc_value, tb_)
        self.close()

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a pipeline run.

        Subclasses must implement this method.

        Returns:
            Dictionary with pipeline outputs.
        """
