"""Shared pipeline execution logic for HTTP and MCP servers.

This module contains the core ``execute_pipeline`` function used by both
the FastAPI HTTP server and the MCP server, ensuring a single execution
path for all server interfaces.
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import asdict, dataclass
from typing import Any

from kedro.framework.session import KedroSession
from kedro.server.config import is_debug_mode
from kedro.utils import load_obj

logger = logging.getLogger(__name__)


@dataclass
class PipelineExecutionError:
    """Structured error information from a failed pipeline run."""

    type: str
    message: str
    traceback: list[str] | None = None


@dataclass
class PipelineExecutionResult:
    """Result of a pipeline execution attempt."""

    run_id: str
    status: str  # "success" | "failed"
    duration_ms: float
    error: PipelineExecutionError | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary, omitting None values."""
        result = asdict(self)
        if result["error"] is None:
            del result["error"]
        # Remove None traceback from error
        elif result["error"]["traceback"] is None:
            del result["error"]["traceback"]
        return result


def execute_pipeline(  # noqa: PLR0913
    project_path: Any,
    *,
    pipeline: str | None = None,
    pipeline_names: list[str] | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    params: dict[str, Any] | None = None,
    runner: str | None = None,
    is_async: bool = False,
    tags: list[str] | None = None,
    node_names: list[str] | None = None,
    from_nodes: list[str] | None = None,
    to_nodes: list[str] | None = None,
    from_inputs: list[str] | None = None,
    to_outputs: list[str] | None = None,
    load_versions: dict[str, str] | None = None,
    namespaces: list[str] | None = None,
    only_missing_outputs: bool = False,
) -> PipelineExecutionResult:
    """Execute a Kedro pipeline and return a structured result.

    This is the shared execution core used by both the HTTP and MCP
    server interfaces.  It creates a fresh ``KedroSession``, resolves
    the runner, calls ``session.run()``, and returns a
    :class:`PipelineExecutionResult`.

    Args:
        project_path: Path to the Kedro project root.
        pipeline: Pipeline name.  Defaults to ``'__default__'``.
        pipeline_names: List of pipeline names (mutually exclusive with
            *pipeline*).  When *pipeline* is given it is normalised into
            this list internally.
        env: Configuration environment (e.g. ``'base'``, ``'local'``).
        conf_source: Path to a custom configuration directory.
        params: Extra parameters for the pipeline context.
        runner: Runner class name: ``'SequentialRunner'``,
            ``'ParallelRunner'``, ``'ThreadRunner'``.
        is_async: Load/save node inputs and outputs asynchronously.
        tags: Run only nodes with these tags.
        node_names: Run only these specific nodes.
        from_nodes: Start execution from these nodes.
        to_nodes: Stop execution at these nodes.
        from_inputs: Start from nodes that produce these datasets.
        to_outputs: Stop at nodes that produce these datasets.
        load_versions: Pin specific dataset versions (name → timestamp).
        namespaces: Run only nodes within these namespaces.
        only_missing_outputs: Skip nodes whose outputs already exist.

    Returns:
        A :class:`PipelineExecutionResult` with run id, status, duration,
        and optional error details.
    """
    start_time = time.perf_counter()
    debug_mode = is_debug_mode()
    run_id: str | None = None

    try:
        if pipeline and pipeline_names:
            raise ValueError(
                "Cannot specify both 'pipeline' and 'pipeline_names'. "
                "Use one or the other."
            )

        # Normalise single pipeline name into the list form to avoid
        # the deprecated ``pipeline_name`` parameter on session.run().
        if pipeline:
            pipeline_names = [pipeline]

        runner_name = runner or "SequentialRunner"
        runner_class = load_obj(runner_name, "kedro.runner")
        runner_obj = runner_class(is_async=is_async)

        with KedroSession.create(
            project_path=project_path,
            env=env,
            conf_source=conf_source,
            runtime_params=params,
        ) as session:
            run_id = session.session_id

            logger.info(
                "Starting pipeline run %s (pipelines=%s, env=%s)",
                run_id,
                pipeline_names or ["__default__"],
                env,
            )

            session.run(
                pipeline_names=pipeline_names,
                tags=tuple(tags) if tags else None,
                runner=runner_obj,
                node_names=tuple(node_names) if node_names else None,
                from_nodes=from_nodes,
                to_nodes=to_nodes,
                from_inputs=from_inputs,
                to_outputs=to_outputs,
                load_versions=load_versions,
                namespaces=namespaces,
                only_missing_outputs=only_missing_outputs,
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Pipeline run %s completed in %.2fms", run_id, duration_ms)

        return PipelineExecutionResult(
            run_id=run_id,
            status="success",
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Pipeline run %s failed: %s",
            run_id or "unknown",
            str(exc),
            exc_info=True,
        )

        error = PipelineExecutionError(
            type=type(exc).__qualname__,
            message=str(exc),
            traceback=traceback.format_tb(exc.__traceback__) if debug_mode else None,
        )

        return PipelineExecutionResult(
            run_id=run_id or "unknown",
            status="failed",
            duration_ms=round(duration_ms, 2),
            error=error,
        )
