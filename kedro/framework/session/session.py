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
"""This module implements Kedro session responsible for project lifecycle."""

import logging
import subprocess
import traceback
from copy import deepcopy
from pathlib import Path
from threading import local
from typing import Any, Dict, Iterable, Optional, Union

import click

from kedro.framework.context import KedroContext, get_static_project_data, load_context
from kedro.framework.hooks import get_hook_manager
from kedro.framework.session.store import BaseSessionStore
from kedro.io.core import generate_timestamp
from kedro.runner import AbstractRunner, SequentialRunner

_local = local()


def get_current_session(silent: bool = False) -> Optional["KedroSession"]:
    """Fetch the most recent ``KedroSession`` instance from internal stack.

    Args:
        silent: Indicates to suppress the error if no active session was found.

    Raises:
        RuntimeError: If no active session was found and `silent` is False.

    Returns:
        KedroSession instance.
    """
    session = None

    if getattr(_local, "stack", []):
        session = _local.stack[-1]
    elif not silent:
        raise RuntimeError("There is no active Kedro session.")

    return session


def _push_session(session):
    _local.__dict__.setdefault("stack", []).append(session)


def _pop_session():
    _local.stack.pop()


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


def _jsonify_cli_context(ctx: click.core.Context):
    return {
        "args": ctx.args,
        "params": ctx.params,
        "command_name": ctx.command.name,
        "command_path": ctx.command_path,
    }


class KedroSession:
    """``KedroSession`` is the object that is responsible for managing the lifecycle
    of a Kedro project.

    IMPORTANT: ``KedroSession`` is currently under development and is not
    integrated into existing Kedro workflow. Its public (and private) interface
    may change between minor releases without notice.
    """

    def __init__(
        self,
        session_id: str,
        project_path: Union[Path, str] = None,
        save_on_close: bool = False,
    ):
        self._project_path = Path(project_path or Path.cwd()).resolve()
        self.session_id = session_id
        self.save_on_close = save_on_close
        self._store = self._init_store()

    @classmethod
    def create(
        cls,
        project_path: Union[Path, str] = None,
        save_on_close: bool = True,
        env: str = None,
    ) -> "KedroSession":
        """Create a new instance of ``KedroSession``.

        Args:
            project_path: Path to the project root directory.
            save_on_close: Whether or not to save the session when it's closed.
            env: Environment for the KedroContext.

        Returns:
            A new ``KedroSession`` instance.
        """
        # pylint: disable=protected-access
        session = cls(
            project_path=project_path,
            session_id=generate_timestamp(),
            save_on_close=save_on_close,
        )

        session_data = get_static_project_data(session._project_path)
        session_data["project_path"] = session._project_path
        session_data["session_id"] = session.session_id
        session_data.update(_describe_git(session._project_path))

        ctx = click.get_current_context(silent=True)
        if ctx:
            session_data["cli"] = _jsonify_cli_context(ctx)

        if env:
            session_data["env"] = env

        session._store.update(session_data)
        return session

    def _init_store(self) -> BaseSessionStore:
        static_data = get_static_project_data(self._project_path)

        config = deepcopy(static_data.get("session_store", {}))
        config.setdefault("path", (self._project_path / "sessions").as_posix())
        config["session_id"] = self.session_id
        store = BaseSessionStore.from_config(config)
        return store

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

    @property
    def context(self) -> KedroContext:
        """An instance of the project context."""
        env = self.store.get("env")
        context = load_context(project_path=self._project_path, env=env)
        return context

    def close(self):
        """Close the current session and save its store to disk
        if `save_on_close` attribute is True.
        """
        if self.save_on_close:
            self._store.save()
        if get_current_session(silent=True) is self:
            _pop_session()

    def __enter__(self):
        if get_current_session(silent=True) is not self:
            _push_session(self)
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
        extra_params: Dict[str, Any] = None,
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
            extra_params: Additional run parameters.
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
        extra_params = deepcopy(extra_params) or dict()
        context = self.context

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
            "kedro_version": self.store["kedro_version"],
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
        hook = get_hook_manager().hook
        hook.before_pipeline_run(
            run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
        )

        try:
            run_result = runner.run(filtered_pipeline, catalog, run_id)
        except Exception as error:
            hook.on_pipeline_error(
                error=error,
                run_params=record_data,
                pipeline=filtered_pipeline,
                catalog=catalog,
            )
            raise

        hook.after_pipeline_run(
            run_params=record_data,
            run_result=run_result,
            pipeline=filtered_pipeline,
            catalog=catalog,
        )
        return run_result
