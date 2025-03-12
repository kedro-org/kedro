"""``kedro.pipeline`` provides functionality to define and execute
data-driven pipelines.
"""

from .node import node
from .pipeline import Pipeline

__all__ = ["node", "Pipeline"]
