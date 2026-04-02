"""MCP server for exposing Kedro pipelines as tools to AI agents.

This module provides an MCP (Model Context Protocol) server that allows
AI agents to discover and execute Kedro pipelines, inspect their structure,
and list catalog datasets.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.server.config import get_project_path
from kedro.server.runner import execute_pipeline

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
    ) -> str:
        """Execute a Kedro pipeline.

        Runs the specified pipeline using KedroSession. Returns JSON with
        run_id, status, duration_ms, and error details if failed.

        Args:
            pipeline: Pipeline name. Defaults to '__default__'.
            pipeline_names: Run multiple pipelines. Mutually exclusive with pipeline.
            env: Configuration environment (e.g. 'base', 'local').
            conf_source: Path to a custom configuration directory.
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
        result = execute_pipeline(
            project_path,
            pipeline=pipeline,
            pipeline_names=pipeline_names,
            env=env,
            conf_source=conf_source,
            params=params,
            runner=runner,
            is_async=is_async,
            tags=tags,
            node_names=node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_versions,
            namespaces=namespaces,
            only_missing_outputs=only_missing_outputs,
        )
        return json.dumps(result.to_dict())

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
