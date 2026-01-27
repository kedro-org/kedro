"""Project pipelines."""
from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines(pipeline: str | None = None) -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Args:
        pipeline: Optional pipeline name for selective loading.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """

    pipelines = find_pipelines(name=pipeline, raise_errors=True)
    if pipeline is None and "__default__" in pipelines:
        named_pipelines = {k: v for k, v in pipelines.items() if k != "__default__"}
        if named_pipelines:
            pipelines["__default__"] = sum(named_pipelines.values())

    return pipelines
