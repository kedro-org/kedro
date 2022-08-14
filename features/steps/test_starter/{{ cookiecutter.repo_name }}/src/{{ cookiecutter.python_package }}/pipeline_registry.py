"""Project pipelines."""
from typing import Dict

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline, pipeline


def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Since Kedro 0.18.3, projects can use the ``find_pipelines`` function
    to autodiscover pipelines. However, projects that require more fine-
    grained control can still construct the pipeline mapping without it.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["__default__"] = sum(pipelines.values())
    pipelines["data_processing"] = pipeline(
        pipelines["data_engineering"], namespace="data_processing"
    )
    return pipelines
