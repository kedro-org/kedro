"""MCP server for exposing Kedro pipelines as tools to AI agents.

This module provides an MCP (Model Context Protocol) server that allows
AI agents to discover and execute Kedro pipelines, inspect their structure,
and list catalog datasets.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from typing import Any

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.server.config import get_project_path, is_debug_mode
from kedro.utils import load_obj

logger = logging.getLogger(__name__)


def create_mcp_server(
    *,
    host: str | None = None,
    port: int | None = None,
) -> Any:
    """Create and configure the Kedro MCP server.

    Bootstraps the Kedro project and registers pipeline execution tools.
    Uses the FastMCP class from the ``mcp`` package (v1 series).

    In v1 FastMCP, host and port are passed to the **constructor** and
    ``run()`` only takes ``transport`` (and optionally ``mount_path``).

    Args:
        host: Bind host for SSE / streamable-http transports.
        port: Bind port for SSE / streamable-http transports.

    Returns:
        Configured FastMCP server instance.
    """
    from mcp.server.fastmcp import FastMCP

    project_path = get_project_path()
    bootstrap_project(project_path)

    constructor_kwargs: dict[str, Any] = {}
    if host is not None:
        constructor_kwargs["host"] = host
    if port is not None:
        constructor_kwargs["port"] = port

    mcp = FastMCP(
        "kedro",
        instructions=(
            "Kedro pipeline execution server. "
            "Use list_pipelines to discover available pipelines, "
            "get_pipeline_info for details, and run_pipeline to execute them."
        ),
        **constructor_kwargs,
    )

    @mcp.tool()
    def list_pipelines() -> str:
        """List all registered Kedro pipelines.

        Returns a JSON array of pipeline names available in the project.
        Use this to discover which pipelines can be executed with run_pipeline.
        """
        from kedro.framework.project import pipelines as pipeline_registry

        names = sorted(pipeline_registry.keys())
        return json.dumps(names, indent=2)

    @mcp.tool()
    def get_pipeline_info(pipeline: str = "__default__") -> str:
        """Get detailed information about a specific Kedro pipeline.

        Returns the pipeline's nodes with their inputs, outputs, and tags.
        Use this to understand what a pipeline does before running it.

        Args:
            pipeline: Name of the pipeline. Defaults to '__default__'.
        """
        from kedro.framework.project import pipelines as pipeline_registry

        if pipeline not in pipeline_registry:
            available = sorted(pipeline_registry.keys())
            return json.dumps(
                {
                    "error": f"Pipeline '{pipeline}' not found",
                    "available_pipelines": available,
                }
            )

        pipe = pipeline_registry[pipeline]
        info = {
            "name": pipeline,
            "num_nodes": len(pipe.nodes),
            "nodes": [
                {
                    "name": node.name,
                    "inputs": sorted(node.inputs),
                    "outputs": sorted(node.outputs),
                    "tags": sorted(node.tags),
                }
                for node in pipe.nodes
            ],
        }
        return json.dumps(info, indent=2)

    @mcp.tool()
    def run_pipeline(  # noqa: PLR0913
        pipeline: str | None = None,
        env: str | None = None,
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
    ) -> str:
        """Execute a Kedro pipeline.

        Runs the specified pipeline using KedroSession. Returns JSON with
        run_id, status, duration_ms, and error details if failed.

        Args:
            pipeline: Pipeline name. Defaults to '__default__'.
            env: Configuration environment (e.g. 'base', 'local').
            params: Extra parameters for the pipeline context.
            runner: Runner class: 'SequentialRunner', 'ParallelRunner', 'ThreadRunner'.
            is_async: Load/save node inputs and outputs asynchronously.
            tags: Run only nodes with these tags.
            node_names: Run only these specific nodes.
            from_nodes: Start execution from these nodes.
            to_nodes: Stop execution at these nodes.
            from_inputs: Start from nodes that produce these datasets.
            to_outputs: Stop at nodes that produce these datasets.
            load_versions: Pin specific dataset versions (name -> timestamp).
            namespaces: Run only nodes within these namespaces.
            only_missing_outputs: Skip nodes whose outputs already exist.
        """
        start_time = time.perf_counter()
        debug_mode = is_debug_mode()
        run_id: str | None = None

        try:
            runner_name = runner or "SequentialRunner"
            runner_class = load_obj(runner_name, "kedro.runner")
            runner_obj = runner_class(is_async=is_async)

            with KedroSession.create(
                project_path=project_path,
                env=env,
                runtime_params=params,
            ) as session:
                run_id = session.session_id

                logger.info(
                    "Starting pipeline run %s (pipeline=%s, env=%s)",
                    run_id,
                    pipeline or "__default__",
                    env,
                )

                session.run(
                    pipeline_name=pipeline,
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

            return json.dumps(
                {
                    "run_id": run_id,
                    "status": "success",
                    "duration_ms": round(duration_ms, 2),
                }
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Pipeline run %s failed: %s",
                run_id or "unknown",
                str(exc),
                exc_info=True,
            )

            error = {
                "type": type(exc).__qualname__,
                "message": str(exc),
            }
            if debug_mode:
                error["traceback"] = traceback.format_tb(exc.__traceback__)

            return json.dumps(
                {
                    "run_id": run_id or "unknown",
                    "status": "failed",
                    "duration_ms": round(duration_ms, 2),
                    "error": error,
                }
            )

    @mcp.tool()
    def list_datasets(env: str | None = None) -> str:
        """List all datasets in the Kedro data catalog.

        Returns a JSON array of dataset names registered in the project.

        Args:
            env: Configuration environment. Defaults to the project default.
        """
        with KedroSession.create(
            project_path=project_path,
            env=env,
        ) as session:
            context = session.load_context()
            datasets = sorted(context.catalog.list())
            return json.dumps(datasets, indent=2)

    return mcp
