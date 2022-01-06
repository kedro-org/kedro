"""Helper to integrate modular pipelines into a master pipeline."""
from typing import Dict, Set, Union, Iterable

from kedro.pipeline.node import Node
from kedro.pipeline.pipeline import (
    Pipeline,
)


def pipeline(
    nodes: Iterable[Union[Node, Pipeline]],
    *,
    tags: Union[str, Iterable[str]] = None,
    inputs: Union[str, Set[str], Dict[str, str]] = None,
    outputs: Union[str, Set[str], Dict[str, str]] = None,
    parameters: Dict[str, str] = None,
    namespace: str = None,
):
    return Pipeline(
        nodes,
        tags=tags,
        inputs=inputs,
        outputs=outputs,
        parameters=parameters,
        namespace=namespace,
    )
