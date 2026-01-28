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
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines
