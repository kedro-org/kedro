"""Project pipelines."""
from typing import Dict

from kedro.pipeline import Pipeline, pipeline

from {{cookiecutter.python_package}}.pipelines import data_engineering as de
from {{cookiecutter.python_package}}.pipelines import data_science as ds


def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.
    """
    data_engineering_pipeline = de.create_pipeline()
    data_processing_pipeline = pipeline(
        de.create_pipeline(), namespace="data_processing"
    )
    data_science_pipeline = ds.create_pipeline()

    return {
        "de": data_engineering_pipeline,
        "ds": data_science_pipeline,
        "dp": data_processing_pipeline,
        "__default__": data_engineering_pipeline + data_science_pipeline,
    }
