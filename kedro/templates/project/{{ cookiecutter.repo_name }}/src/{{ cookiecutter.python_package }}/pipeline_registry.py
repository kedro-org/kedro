"""Project pipelines."""

from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines(
    pipelines_to_find: list[str] | None = None,
) -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines(raise_errors=True, pipelines_to_find=pipelines_to_find)
    if pipelines_to_find is None or "__default__" in pipelines_to_find:
        pipelines["__default__"] = sum(pipelines.values())
    return pipelines
