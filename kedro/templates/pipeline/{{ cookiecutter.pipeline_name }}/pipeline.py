"""
This is a boilerplate pipeline '{{ cookiecutter.pipeline_name }}'
generated using Kedro {{ cookiecutter.kedro_version }}
"""

from kedro.pipeline import node, Pipeline, pipeline  # noqa


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([])
