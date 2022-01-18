"""Project pipelines."""
from typing import Dict

from kedro.pipeline import Pipeline, pipeline


def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.
    """
    return {"__default__": pipeline([])}
