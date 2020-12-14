# Copyright 2020 QuantumBlack Visual Analytics Limited
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
# pylint: disable=invalid-name,global-statement
"""This module implements Kedro session responsible for project lifecycle."""

import logging
import logging.config
import subprocess
import traceback
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

import click
from pluggy import PluginManager

from kedro import __version__ as kedro_version
from kedro.framework.context import KedroContext
from kedro.framework.context.context import _convert_paths_to_absolute_posix
from kedro.framework.hooks import get_hook_manager
from kedro.framework.hooks.manager import _register_hooks, _register_hooks_setuptools
from kedro.framework.project.settings import _get_project_settings
from kedro.framework.session.store import BaseSessionStore
from kedro.io.core import generate_timestamp
from kedro.runner import AbstractRunner, SequentialRunner

_active_session = None


def _register_all_project_hooks(hook_manager: PluginManager, package_name: str) -> None:
    """Register all hooks from the project settings and from installed plugins
    with the global ``hook_manager``.

    Args:
        hook_manager: Hook manager instance to register the hooks with.
        package_name: Python package name to read the settings for.

    """
    # get the hooks specified in settings.py
    hooks = _get_project_settings(package_name, "HOOKS", ())
    # get the plugins that must be disabled
    disabled_plugins = set(
        _get_project_settings(package_name, "DISABLE_HOOKS_FOR_PLUGINS", ())
    )

    _register_hooks(hook_manager, hooks)
    _register_hooks_setuptools(hook_manager, disabled_plugins)


def get_current_session(silent: bool = False) -> Optional["KedroSession"]:
    """Fetch the active ``KedroSession`` instance.

    Args:
        silent: Indicates to suppress the error if no active session was found.

    Raises:
        RuntimeError: If no active session was found and `silent` is False.

    Returns:
        KedroSession instance.

    """
    if not _active_session and not silent:
        raise RuntimeError("There is no active Kedro session.")

    return _active_session


def _activate_session(session: "KedroSession", force: bool = False) -> None:
    global _active_session

    if _active_session and not force and session is not _active_session:
        raise RuntimeError(
            "Cannot activate the session as another active session already exists."
        )

    _active_session = session


def _deactivate_session() -> None:
    global _active_session
    _active_session = None


def _describe_git(project_path: Path) -> Dict[str, Dict[str, str]]:
    project_path = str(project_path)

    try:
        res = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=project_path
        )
    # `subprocess.check_output()` raises `NotADirectoryError` on Windows
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        logging.getLogger(__name__).warning("Unable to git describe %s", project_path)
        return {}

    git_data = {"commit_sha": res.decode().strip()}

    res = subprocess.check_output(["git", "status", "--short"], cwd=project_path)
    git_data["dirty"] = bool(res.decode().strip())

    return {"git": git_data}


def _jsonify_cli_context(ctx: click.core.Context) -> Dict[str, Any]:
    return {
        "args": ctx.args,
        "params": ctx.params,
        "command_name": ctx.command.name,
        "command_path": ctx.command_path,
    }


class KedroSession:
    """``KedroSession`` is the object that is responsible for managing the lifecycle
    of a Kedro run.
    - Use `KedroSession.create("<your-kedro-project-package-name>")` as
    a context manager to construct a new KedroSession with session data
    provided (see the example below).
    - Use `KedroSession(session_id=<id>)` to instantiate an existing session with a given
    ID.

    Example:
    ::

        >>> from kedro.framework.session import KedroSession
        >>>
        >>> with KedroSession.create("<your-kedro-project-package-name>") as session:
        >>>     session.run()
        >>>
    """

    def __init__(
        self,
        session_id: str,
        package_name: str,
        project_path: Union[Path, str] = None,
        save_on_close: bool = False,
    ):
        self._project_path = Path(project_path or Path.cwd()).resolve()
        self.session_id = session_id
        self.save_on_close = save_on_close
        self._package_name = package_name
        self._store = self._init_store()

    @classmethod
    def create(  # pylint: disable=too-many-arguments
        cls,
        package_name: str,
        project_path: Union[Path, str] = None,
        save_on_close: bool = True,
        env: str = None,
        extra_params: Dict[str, Any] = None,
    ) -> "KedroSession":
        """Create a new instance of ``KedroSession`` with the session data.

        Args:
            package_name: Package name for the Kedro project the session is
                created for.
            project_path: Path to the project root directory. Default is
                current working directory Path.cwd().
            save_on_close: Whether or not to save the session when it's closed.
            env: Environment for the KedroContext.
            extra_params: Optional dictionary containing extra project parameters
            for underlying KedroContext. If specified, will update (and therefore take
            precedence over) the parameters retrieved from the project configuration.

        Returns:
            A new ``KedroSession`` instance.
        """
        # pylint: disable=protected-access
        session = cls(
            package_name=package_name,
            project_path=project_path,
            session_id=generate_timestamp(),
            save_on_close=save_on_close,
        )

        session_data = {
            "package_name": session._package_name,
            "project_path": session._project_path,
            "session_id": session.session_id,
            **_describe_git(session._project_path),
        }

        ctx = click.get_current_context(silent=True)
        if ctx:
            session_data["cli"] = _jsonify_cli_context(ctx)

        if env:
            session_data["env"] = env

        if extra_params:
            session_data["extra_params"] = extra_params

        session._store.update(session_data)

        hook_manager = get_hook_manager()
        _register_all_project_hooks(hook_manager, session._package_name)
        # we need a ConfigLoader registered in order to be able to set up logging
        session._setup_logging()
        return session

    def _get_logging_config(self) -> Dict[str, Any]:
        context = self.load_context()

        conf_logging = context.config_loader.get(
            "logging*", "logging*/**", "**/logging*"
        )
        # turn relative paths in logging config into absolute path
        # before initialising loggers
        conf_logging = _convert_paths_to_absolute_posix(
            project_path=self._project_path, conf_dictionary=conf_logging
        )
        return conf_logging

    def _setup_logging(self) -> None:
        """Register logging specified in logging directory."""
        conf_logging = self._get_logging_config()
        logging.config.dictConfig(conf_logging)

    def _init_store(self) -> BaseSessionStore:
        store_class = _get_project_settings(
            self._package_name, "SESSION_STORE_CLASS", BaseSessionStore
        )
        classpath = f"{store_class.__module__}.{store_class.__qualname__}"

        if not issubclass(store_class, BaseSessionStore):
            raise ValueError(
                f"Store type `{classpath}` is invalid: "
                f"it must extend `BaseSessionStore`."
            )

        store_args = deepcopy(
            _get_project_settings(self._package_name, "SESSION_STORE_ARGS", {})
        )
        store_args.setdefault("path", (self._project_path / "sessions").as_posix())
        store_args["session_id"] = self.session_id

        try:
            return store_class(**store_args)
        except TypeError as err:
            raise ValueError(
                f"\n{err}.\nStore config must only contain arguments valid "
                f"for the constructor of `{classpath}`."
            ) from err
        except Exception as err:
            raise ValueError(
                f"\n{err}.\nFailed to instantiate session store of type `{classpath}`."
            ) from err

    def _log_exception(self, exc_type, exc_value, exc_tb):
        type_ = [] if exc_type.__module__ == "builtins" else [exc_type.__module__]
        type_.append(exc_type.__qualname__)

        exc_data = {
            "type": ".".join(type_),
            "value": str(exc_value),
            "traceback": traceback.format_tb(exc_tb),
        }
        self._store["exception"] = exc_data

    @property
    def store(self) -> Dict[str, Any]:
        """Return a copy of internal store."""
        return dict(self._store)

    def load_context(self) -> KedroContext:
        """An instance of the project context."""
        env = self.store.get("env")
        extra_params = self.store.get("extra_params")

        context_class = _get_project_settings(
            self._package_name, "CONTEXT_CLASS", KedroContext
        )

        context = context_class(
            package_name=self._package_name,
            project_path=self._project_path,
            env=env,
            extra_params=extra_params,
        )
        return context

    def close(self):
        """Close the current session and save its store to disk
        if `save_on_close` attribute is True.
        """
        if self.save_on_close:
            self._store.save()

        if get_current_session(silent=True) is self:
            _deactivate_session()

    def __enter__(self):
        if get_current_session(silent=True) is not self:
            _activate_session(self)
        return self

    def __exit__(self, exc_type, exc_value, tb_):
        if exc_type:
            self._log_exception(exc_type, exc_value, tb_)
        self.close()

    def run(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        pipeline_name: str = None,
        tags: Iterable[str] = None,
        runner: AbstractRunner = None,
        node_names: Iterable[str] = None,
        from_nodes: Iterable[str] = None,
        to_nodes: Iterable[str] = None,
        from_inputs: Iterable[str] = None,
        load_versions: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Runs the pipeline with a specified runner.

        Args:
            pipeline_name: Name of the pipeline that is being run.
            tags: An optional list of node tags which should be used to
                filter the nodes of the ``Pipeline``. If specified, only the nodes
                containing *any* of these tags will be run.
            runner: An optional parameter specifying the runner that you want to run
                the pipeline with.
            node_names: An optional list of node names which should be used to
                filter the nodes of the ``Pipeline``. If specified, only the nodes
                with these names will be run.
            from_nodes: An optional list of node names which should be used as a
                starting point of the new ``Pipeline``.
            to_nodes: An optional list of node names which should be used as an
                end point of the new ``Pipeline``.
            from_inputs: An optional list of input datasets which should be
                used as a starting point of the new ``Pipeline``.
            load_versions: An optional flag to specify a particular dataset
                version timestamp to load.
        Raises:
            Exception: Any uncaught exception during the run will be re-raised
                after being passed to ``on_pipeline_error`` hook.
        Returns:
            Any node outputs that cannot be processed by the ``DataCatalog``.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.
        """
        # pylint: disable=protected-access,no-member
        # Report project name
        logging.info("** Kedro project %s", self._project_path.name)

        save_version = run_id = self.store["session_id"]
        extra_params = self.store.get("extra_params") or {}
        context = self.load_context()

        pipeline = context._get_pipeline(name=pipeline_name)
        filtered_pipeline = context._filter_pipeline(
            pipeline=pipeline,
            tags=tags,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            node_names=node_names,
            from_inputs=from_inputs,
        )

        record_data = {
            "run_id": run_id,
            "project_path": self._project_path.as_posix(),
            "env": context.env,
            "kedro_version": kedro_version,
            "tags": tags,
            "from_nodes": from_nodes,
            "to_nodes": to_nodes,
            "node_names": node_names,
            "from_inputs": from_inputs,
            "load_versions": load_versions,
            "extra_params": extra_params,
            "pipeline_name": pipeline_name,
        }

        catalog = context._get_catalog(
            save_version=save_version, load_versions=load_versions
        )

        # Run the runner
        runner = runner or SequentialRunner()
        hook_manager = get_hook_manager()
        hook_manager.hook.before_pipeline_run(  # pylint: disable=no-member
            run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
        )

        try:
            run_result = runner.run(filtered_pipeline, catalog, run_id)
        except Exception as error:
            hook_manager.hook.on_pipeline_error(
                error=error,
                run_params=record_data,
                pipeline=filtered_pipeline,
                catalog=catalog,
            )
            raise

        hook_manager.hook.after_pipeline_run(
            run_params=record_data,
            run_result=run_result,
            pipeline=filtered_pipeline,
            catalog=catalog,
        )
        return run_result
