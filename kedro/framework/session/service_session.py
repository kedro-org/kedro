"""KedroServiceSession for managing concurrent pipeline runs."""

from __future__ import annotations

import asyncio
import logging
import traceback
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

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

from .abstract_session import AbstractSession, KedroSessionError, _describe_git, _jsonify_cli_context

if TYPE_CHECKING:
    from collections.abc import Iterable

    import click

    from kedro.framework.context import KedroContext


@dataclass
class RunConfig:
    """Configuration for a single run in a multirun session.

    Attributes:
        run_id: Unique identifier for this run.
        pipeline_names: List of pipeline names to run.
        tags: Optional list of node tags to filter.
        runner: Optional runner instance.
        node_names: Optional list of specific node names to run.
        from_nodes: Optional starting nodes.
        to_nodes: Optional ending nodes.
        from_inputs: Optional starting inputs.
        to_outputs: Optional ending outputs.
        load_versions: Optional dataset version mapping.
        namespaces: Optional namespaces to include.
        only_missing_outputs: Whether to run only missing outputs.
        runtime_params: Optional runtime parameters for this run.
        env: Optional environment override for this run.
    """

    run_id: str
    pipeline_names: list[str] | None = None
    tags: Iterable[str] | None = None
    runner: AbstractRunner | None = None
    node_names: Iterable[str] | None = None
    from_nodes: Iterable[str] | None = None
    to_nodes: Iterable[str] | None = None
    from_inputs: Iterable[str] | None = None
    to_outputs: Iterable[str] | None = None
    load_versions: dict[str, str] | None = None
    namespaces: Iterable[str] | None = None
    only_missing_outputs: bool = False
    runtime_params: dict[str, Any] | None = None
    env: str | None = None


@dataclass
class RunResult:
    """Result of a single run in a multirun session.

    Attributes:
        run_id: Unique identifier for the run.
        status: Status of the run ('success', 'failed', 'skipped').
        outputs: Pipeline outputs if successful.
        exception: Exception object if failed.
        start_time: Start time of the run.
        end_time: End time of the run.
        metadata: Additional metadata about the run.
    """

    run_id: str
    status: str  # 'success', 'failed', 'skipped'
    outputs: dict[str, Any] | None = None
    exception: Exception | None = None
    start_time: str | None = None
    end_time: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class KedroServiceSession(AbstractSession):
    """``KedroServiceSession`` enables concurrent pipeline runs within a single session.

    Unlike ``KedroSession`` which enforces a 1:1 mapping between sessions and runs,
    ``KedroServiceSession`` allows multiple concurrent or sequential runs with
    independent data catalogs and optional environment overrides per run.

    The session manages run coordination, error handling, and result aggregation.

    Example:
    ``` python
    from kedro.framework.session import KedroServiceSession
    from kedro.framework.startup import bootstrap_project
    from pathlib import Path

    bootstrap_project(Path("<project_root>"))
    with KedroServiceSession.create() as session:
        run_configs = [
            session.create_run_config(pipeline_names=["pipeline_1"]),
            session.create_run_config(pipeline_names=["pipeline_2"]),
        ]
        results = session.run_all(run_configs, max_workers=2)
        for result in results:
            print(f"Run {result.run_id}: {result.status}")
    ```
    """

    def __init__(
        self,
        session_id: str,
        package_name: str | None = None,
        project_path: Path | str | None = None,
        save_on_close: bool = False,
        conf_source: str | None = None,
        max_workers: int = 1,
    ):
        """Initialize a KedroServiceSession.

        Args:
            session_id: A unique identifier for the session.
            package_name: The package name of the Kedro project.
            project_path: Path to the project root directory.
            save_on_close: Whether to save the session when closed.
            conf_source: Path to the configuration source directory.
            max_workers: Maximum number of concurrent worker threads for multirun.
        """
        super().__init__(
            session_id=session_id,
            package_name=package_name,
            project_path=project_path,
            save_on_close=save_on_close,
            conf_source=conf_source,
        )
        self.max_workers = max_workers
        self._run_results: list[RunResult] = []
        self._executor: ThreadPoolExecutor | None = None

    @classmethod
    def create(
        cls,
        project_path: Path | str | None = None,
        save_on_close: bool = True,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
        conf_source: str | None = None,
        max_workers: int = 1,
    ) -> KedroServiceSession:
        """Create a new instance of ``KedroServiceSession`` with the session data.

        Args:
            project_path: Path to the project root directory.
            save_on_close: Whether to save the session when closed.
            env: Default environment for the session.
            runtime_params: Default runtime parameters for the session.
            conf_source: Path to configuration source.
            max_workers: Maximum concurrent workers for multirun.

        Returns:
            A new ``KedroServiceSession`` instance.
        """
        validate_settings()

        session = cls(
            project_path=project_path,
            session_id=generate_timestamp(),
            save_on_close=save_on_close,
            conf_source=conf_source,
            max_workers=max_workers,
        )

        session_data: dict[str, Any] = {
            "project_path": session._project_path,
            "session_id": session.session_id,
            "max_workers": max_workers,
        }

        import click

        ctx = click.get_current_context(silent=True)
        if ctx:
            session_data["cli"] = _jsonify_cli_context(ctx)

        import os

        env = env or os.getenv("KEDRO_ENV")
        if env:
            session_data["env"] = env

        if runtime_params:
            session_data["runtime_params"] = runtime_params

        try:
            import getpass

            session_data["username"] = getpass.getuser()
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Unable to get username. Full exception: %s", exc
            )

        session_data.update(**_describe_git(session._project_path))
        session._store.update(session_data)

        return session

    def create_run_config(
        self,
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
        runtime_params: dict[str, Any] | None = None,
        env: str | None = None,
    ) -> RunConfig:
        """Create a RunConfig for a single run.

        Args:
            pipeline_names: Names of pipelines to run.
            tags: Optional node tags to filter.
            runner: Optional runner instance.
            node_names: Optional specific node names.
            from_nodes: Optional starting nodes.
            to_nodes: Optional ending nodes.
            from_inputs: Optional starting inputs.
            to_outputs: Optional ending outputs.
            load_versions: Optional dataset versions to load.
            namespaces: Optional namespaces.
            only_missing_outputs: Whether to run only nodes with missing outputs.
            runtime_params: Optional runtime parameters for this run.
            env: Optional environment override.

        Returns:
            A RunConfig instance.
        """
        return RunConfig(
            run_id=generate_timestamp(),
            pipeline_names=pipeline_names,
            tags=tags,
            runner=runner,
            node_names=node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_versions,
            namespaces=namespaces,
            only_missing_outputs=only_missing_outputs,
            runtime_params=runtime_params,
            env=env,
        )

    def _execute_run(self, config: RunConfig) -> RunResult:
        """Execute a single run with the given configuration.

        Args:
            config: The RunConfig for this run.

        Returns:
            A RunResult with the outcome.
        """
        result = RunResult(
            run_id=config.run_id,
            status="running",
            start_time=generate_timestamp(),
        )

        try:
            # Create fresh context for this run
            context = self.load_context(env=config.env, runtime_params=config.runtime_params)

            # Get pipeline
            names = config.pipeline_names or ["__default__"]
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

            # Filter pipeline
            filtered_pipeline = combined_pipelines.filter(
                tags=config.tags,
                from_nodes=config.from_nodes,
                to_nodes=config.to_nodes,
                node_names=config.node_names,
                from_inputs=config.from_inputs,
                to_outputs=config.to_outputs,
                node_namespaces=config.namespaces,
            )

            # Get catalog
            runner = config.runner or SequentialRunner()
            if not isinstance(runner, AbstractRunner):
                raise KedroSessionError(
                    "KedroServiceSession expects an instance of Runner instead of a class. "
                    "Have you forgotten the `()` at the end of the statement?"
                )

            catalog_class = (
                SharedMemoryDataCatalog
                if isinstance(runner, ParallelRunner)
                else settings.DATA_CATALOG_CLASS
            )

            catalog = context._get_catalog(
                catalog_class=catalog_class,
                save_version=config.run_id,
                load_versions=config.load_versions,
            )

            # Prepare run params
            record_data = {
                "session_id": self.session_id,
                "run_id": config.run_id,
                "project_path": self._project_path.as_posix(),
                "env": context.env,
                "kedro_version": kedro_version,
                "tags": config.tags,
                "from_nodes": config.from_nodes,
                "to_nodes": config.to_nodes,
                "node_names": config.node_names,
                "from_inputs": config.from_inputs,
                "to_outputs": config.to_outputs,
                "load_versions": config.load_versions,
                "runtime_params": config.runtime_params or {},
                "pipeline_names": config.pipeline_names,
                "namespaces": config.namespaces,
                "runner": getattr(runner, "__name__", str(runner)),
                "only_missing_outputs": config.only_missing_outputs,
            }

            # Execute pipeline
            hook_manager = self._hook_manager
            hook_manager.hook.before_pipeline_run(
                run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
            )

            run_output = runner.run(
                filtered_pipeline,
                catalog,
                hook_manager,
                run_id=config.run_id,
                only_missing_outputs=config.only_missing_outputs,
            )

            hook_manager.hook.after_pipeline_run(
                run_params=record_data,
                run_result=run_output,
                pipeline=filtered_pipeline,
                catalog=catalog,
            )

            result.status = "success"
            result.outputs = run_output
            result.metadata = record_data

        except Exception as exc:
            self._logger.error(f"Run {config.run_id} failed: {exc}")
            result.status = "failed"
            result.exception = exc

        finally:
            result.end_time = generate_timestamp()

        return result

    def run(
        self,
        config: RunConfig | None = None,
        **kwargs: Any,
    ) -> RunResult:
        """Execute a single run.

        This is a convenience method that wraps _execute_run for compatibility
        with AbstractSession.

        Args:
            config: RunConfig for the run. If None, creates one from kwargs.
            **kwargs: Alternative parameters if config is not provided.

        Returns:
            A RunResult with the outcome.
        """
        if config is None:
            config = self.create_run_config(**kwargs)
        return self._execute_run(config)

    def run_all(
        self,
        configs: list[RunConfig],
        continue_on_error: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[RunResult]:
        """Execute multiple runs concurrently or sequentially.

        Args:
            configs: List of RunConfig objects for each run.
            continue_on_error: If False, stop on first failure. If True, continue.
            progress_callback: Optional callback(completed, total) for progress tracking.

        Returns:
            List of RunResult objects in the order they were requested.

        Raises:
            KedroSessionError: If continue_on_error is False and any run fails.
        """
        self._run_results = []
        results_map: dict[Future, int] = {}

        self._logger.info(
            f"Starting {len(configs)} runs with max {self.max_workers} workers"
        )

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self._executor = executor

                # Submit all runs
                for idx, config in enumerate(configs):
                    future = executor.submit(self._execute_run, config)
                    results_map[future] = idx

                # Collect results as they complete
                results_by_index: dict[int, RunResult] = {}
                completed = 0

                for future in as_completed(results_map):
                    idx = results_map[future]
                    try:
                        result = future.result()
                        results_by_index[idx] = result
                        completed += 1

                        self._logger.info(
                            f"Run {result.run_id} completed with status: {result.status}"
                        )

                        if progress_callback:
                            progress_callback(completed, len(configs))

                        if result.status == "failed" and not continue_on_error:
                            raise KedroSessionError(
                                f"Run {result.run_id} failed: {result.exception}"
                            )

                    except Exception as exc:
                        self._logger.error(f"Error collecting result for run {idx}: {exc}")
                        if not continue_on_error:
                            raise

                # Return results in original order
                self._run_results = [results_by_index[i] for i in range(len(configs))]

        finally:
            self._executor = None

        # Log summary
        successful = sum(1 for r in self._run_results if r.status == "success")
        failed = sum(1 for r in self._run_results if r.status == "failed")
        self._logger.info(
            f"Multirun completed: {successful} successful, {failed} failed out of {len(configs)} runs"
        )

        return self._run_results

    def run_sequential(
        self,
        configs: list[RunConfig],
        continue_on_error: bool = False,
    ) -> list[RunResult]:
        """Execute runs sequentially (same as run_all with max_workers=1).

        Args:
            configs: List of RunConfig objects for each run.
            continue_on_error: If False, stop on first failure.

        Returns:
            List of RunResult objects.
        """
        return self.run_all(configs, continue_on_error=continue_on_error)

    def get_results(self) -> list[RunResult]:
        """Get results from all runs executed in this session.

        Returns:
            List of RunResult objects.
        """
        return self._run_results.copy()

    def close(self) -> None:
        """Close the session, cleanup executor, and save store if configured."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

        # Optionally extend store with aggregated results
        if self._run_results:
            self._store["runs"] = [
                {
                    "run_id": r.run_id,
                    "status": r.status,
                    "start_time": r.start_time,
                    "end_time": r.end_time,
                }
                for r in self._run_results
            ]

        super().close()
