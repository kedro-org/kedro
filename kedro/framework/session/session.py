"""This module implements Kedro session responsible for project lifecycle."""

from __future__ import annotations

import getpass
import logging
import logging.config
import os
import traceback
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kedro import __version__ as kedro_version
from kedro.framework.project import (
    pipelines,
    settings,
    validate_settings,
)
from kedro.io.core import generate_timestamp
from kedro.io.data_catalog import SharedMemoryDataCatalog
from kedro.pipeline.pipeline import Pipeline
from kedro.runner import AbstractRunner, ParallelRunner, SequentialRunner

from .abstract_session import (
    AbstractSession,
    KedroSessionError,
    _describe_git,
    _jsonify_cli_context,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    import click

    from kedro.config import AbstractConfigLoader
    from kedro.framework.context import KedroContext
    from kedro.framework.session.store import BaseSessionStore


class KedroSession(AbstractSession):
    """``KedroSession`` is the object that is responsible for managing the lifecycle
    of a Kedro run. Use `KedroSession.create()` as
    a context manager to construct a new KedroSession with session data
    provided (see the example below).

    ``KedroSession`` enforces a 1:1 mapping between sessions and runs,
    meaning only one run can be executed per session.

    Example:
    ``` python
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project
    from pathlib import Path

    # If you are creating a session outside of a Kedro project (i.e. not using
    # `kedro run` or `kedro jupyter`), you need to run `bootstrap_project` to
    # let Kedro find your configuration.
    bootstrap_project(Path("<project_root>"))
    with KedroSession.create() as session:
        session.run()
    ```
    """

    def __init__(
        self,
        session_id: str,
        package_name: str | None = None,
        project_path: Path | str | None = None,
        save_on_close: bool = False,
        conf_source: str | None = None,
    ):
        super().__init__(
            session_id=session_id,
            package_name=package_name,
            project_path=project_path,
            save_on_close=save_on_close,
            conf_source=conf_source,
        )
        self._run_called = False

    @classmethod
    def create(
        cls,
        project_path: Path | str | None = None,
        save_on_close: bool = True,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
        conf_source: str | None = None,
    ) -> KedroSession:
        """Create a new instance of ``KedroSession`` with the session data.

        Args:
            project_path: Path to the project root directory. Default is
                current working directory Path.cwd().
            save_on_close: Whether or not to save the session when it's closed.
            conf_source: Path to a directory containing configuration
            env: Environment for the KedroContext.
            runtime_params: Optional dictionary containing extra project parameters
                for underlying KedroContext. If specified, will update (and therefore
                take precedence over) the parameters retrieved from the project
                configuration.

        Returns:
            A new ``KedroSession`` instance.
        """
        validate_settings()

        session = cls(
            project_path=project_path,
            session_id=generate_timestamp(),
            save_on_close=save_on_close,
            conf_source=conf_source,
        )

        # have to explicitly type session_data otherwise mypy will complain
        # possibly related to this: https://github.com/python/mypy/issues/1430
        session_data: dict[str, Any] = {
            "project_path": session._project_path,
            "session_id": session.session_id,
        }

        import click
        ctx = click.get_current_context(silent=True)
        if ctx:
            session_data["cli"] = _jsonify_cli_context(ctx)

        env = env or os.getenv("KEDRO_ENV")
        if env:
            session_data["env"] = env

        if runtime_params:
            session_data["runtime_params"] = runtime_params

        try:
            session_data["username"] = getpass.getuser()
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Unable to get username. Full exception: %s", exc
            )

        session_data.update(**_describe_git(session._project_path))
        session._store.update(session_data)

        return session

    def run(  # noqa: PLR0913
        self,
        pipeline_name: str | None = None,
        pipeline_names: list[str] | None = None,
        tags: Iterable[str] | None = None,
        runner: AbstractRunner | None = None,
        node_names: Iterable[str] | None = None,
        from_nodes: Iterable[str] | None = None,
        to_nodes: Iterable[str] | None = None,
        from_inputs: Iterable[str] | None = None,
        to_outputs: Iterable[str] | None = None,
        load_versions: dict[str, str] | None = None,
        namespaces: Iterable[str] | None = None,
        only_missing_outputs: bool = False,
    ) -> dict[str, Any]:
        """Runs the pipeline with a specified runner.

        Args:
            pipeline_name: Name of the pipeline that is being run.
            pipeline_names: Name of the pipelines that is being run.
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
            to_outputs: An optional list of output datasets which should be
                used as an end point of the new ``Pipeline``.
            load_versions: An optional flag to specify a particular dataset
                version timestamp to load.
            namespaces: The namespaces of the nodes that are being run.
            only_missing_outputs: Run only nodes with missing outputs.
        Raises:
            ValueError: If the named or `__default__` pipeline is not
                defined by `register_pipelines`.
            Exception: Any uncaught exception during the run will be re-raised
                after being passed to ``on_pipeline_error`` hook.
            KedroSessionError: If more than one run is attempted to be executed during
                a single session.
        Returns:
            Dictionary with pipeline outputs, where keys are dataset names
            and values are dataset objects.
        """
        # Report project name
        project_name = self._package_name or self._project_path.name
        self._logger.info("Kedro project %s", project_name)
        if pipeline_name:
            self._logger.warning(
                "`pipeline_name` is deprecated and will be removed in a future release. "
                "Please use `pipeline_names` instead."
            )
            pipeline_names = [pipeline_name]

        if self._run_called:
            raise KedroSessionError(
                "A run has already been completed as part of the"
                " active KedroSession. KedroSession has a 1-1 mapping with"
                " runs, and thus only one run should be executed per session."
            )

        session_id = self.store["session_id"]
        save_version = session_id
        runtime_params = self.store.get("runtime_params") or {}
        context = self.load_context()

        names = pipeline_names or ["__default__"]
        combined_pipelines = Pipeline([])
        for name in names:
            try:
                combined_pipelines += pipelines[name]
            except KeyError as exc:
                raise ValueError(
                    f"Failed to find the pipeline named '{name}'. "
                    f"It needs to be generated and returned "
                    f"by the 'register_pipelines' function."
                ) from exc

        filtered_pipeline = combined_pipelines.filter(
            tags=tags,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            node_names=node_names,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            node_namespaces=namespaces,
        )

        record_data = {
            "session_id": session_id,
            "project_path": self._project_path.as_posix(),
            "env": context.env,
            "kedro_version": kedro_version,
            "tags": tags,
            "from_nodes": from_nodes,
            "to_nodes": to_nodes,
            "node_names": node_names,
            "from_inputs": from_inputs,
            "to_outputs": to_outputs,
            "load_versions": load_versions,
            "runtime_params": runtime_params,
            "pipeline_names": pipeline_names,
            "namespaces": namespaces,
            "runner": getattr(runner, "__name__", str(runner)),
            "only_missing_outputs": only_missing_outputs,
        }

        runner = runner or SequentialRunner()
        if not isinstance(runner, AbstractRunner):
            raise KedroSessionError(
                "KedroSession expect an instance of Runner instead of a class."
                "Have you forgotten the `()` at the end of the statement?"
            )

        catalog_class = (
            SharedMemoryDataCatalog
            if isinstance(runner, ParallelRunner)
            else settings.DATA_CATALOG_CLASS
        )

        catalog = context._get_catalog(
            catalog_class=catalog_class,
            save_version=save_version,
            load_versions=load_versions,
        )

        # Run the runner
        hook_manager = self._hook_manager
        hook_manager.hook.before_pipeline_run(
            run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
        )
        try:
            run_result = runner.run(
                filtered_pipeline,
                catalog,
                hook_manager,
                run_id=session_id,
                only_missing_outputs=only_missing_outputs,
            )
            self._run_called = True
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
