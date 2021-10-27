"""Parallel executor definition.
"""
from typing import Iterable

from kedro.io import AbstractDataSet, DataCatalog
from kedro.pipeline.node import Node
from kedro.symphony.executor.executor import AbstractExecutor

from concurrent.futures import ProcessPoolExecutor


class MultiprocessingExecutor(AbstractExecutor):
    """Executor for running nodes in parallel locally.

    Using the Python multiprocessing library.
    """
    def _run(self, nodes: Iterable[Node], catalog: DataCatalog,
             run_id: str = None) -> None:
        pass

    def create_default_data_set(self, ds_name: str) -> AbstractDataSet:
        pass