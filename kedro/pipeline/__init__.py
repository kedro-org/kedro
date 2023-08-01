"""``kedro.pipeline`` provides functionality to define and execute
data-driven pipelines.
"""

from .modular_pipeline import pipeline
from .node import node
from .pipeline import Pipeline

__all__ = ["pipeline", "node", "Pipeline"]
