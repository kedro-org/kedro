"""
This is a boilerplate pipeline '{{ cookiecutter.pipeline_name }}'
generated using Kedro {{ cookiecutter.kedro_version }}
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
