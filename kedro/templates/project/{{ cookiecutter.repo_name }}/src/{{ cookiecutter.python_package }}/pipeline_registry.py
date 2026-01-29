"""Project pipelines."""
from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines(pipeline: str | None = None, existing_pipelines: dict[str, Pipeline] | None = None) -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Args:
        pipeline: Optional pipeline name for selective loading.
        existing_pipelines: Already loaded pipelines to merge with.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines(name=pipeline, raise_errors=True)

    if existing_pipelines:
        all_pipelines = {**existing_pipelines, **pipelines}
    else:
        all_pipelines = pipelines

    named_pipelines = {k: v for k, v in all_pipelines.items() if k != "__default__"}
    if named_pipelines:
        all_pipelines["__default__"] = sum(named_pipelines.values())
    else:
        all_pipelines["__default__"] = pipeline([])

    return all_pipelines
