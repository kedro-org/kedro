# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

from kedro.pipeline import node
from kedro.pipeline.modular_pipeline import pipeline
from kedro.io.data_catalog import DataCatalog
from kedro.runner import SequentialRunner, ThreadRunner, ParallelRunner
import time
import numpy as np
import yaml
import pandas as pd
from kedro.io.memory_dataset import MemoryDataset


# Simulate an I/O-bound task
def io_bound_task(input_data):
    time.sleep(2)  # Simulate an I/O wait (e.g., reading from a file)
    output = input_data
    return output


# Simulate a compute-bound task (matrix multiplication)
def compute_bound_task(input_data) -> str:
    # Simulate heavy compute that are not using multicore (not pandas/numpy etc)
    ans = 1
    for i in range(1, 50000):
        ans = ans * i
    return "dummy"


def create_data_catalog():
    """
    Use dataset factory pattern to make sure the benchmark cover the slowest path.
    """
    catalog_conf = """

'output_{pattern}':
    type: pandas.CSVDataset
    filepath: '{pattern}.csv'

'numpy_{pattern}':
    type: pickle.PickleDataset
    filepath: '{pattern}.pkl'

'{catch_all_dataset_pattern}':
    type: pandas.CSVDataset
    filepath: data.csv
"""
    catalog_conf = yaml.safe_load(catalog_conf)
    catalog = DataCatalog.from_config(catalog_conf)
    return catalog


def create_io_bound_node(inputs=None, outputs=None, name=None):
    io_node = node(io_bound_task, inputs=inputs, outputs=outputs, name=name)
    return io_node


def create_io_bound_pipeline():
    dummy_pipeline = pipeline(
        [
            create_io_bound_node("dummy_1", "output_1"),
            create_io_bound_node("dummy_2", "output_2"),
            create_io_bound_node("dummy_3", "output_3"),
            create_io_bound_node("dummy_4", "output_4"),
            create_io_bound_node("dummy_5", "output_5"),
            create_io_bound_node("dummy_6", "output_6"),
            create_io_bound_node("dummy_7", "output_7"),
            create_io_bound_node("dummy_1", "output_8"),
            create_io_bound_node("dummy_1", "output_9"),
            create_io_bound_node("dummy_1", "output_10"),
        ]
    )
    return dummy_pipeline


def create_compute_bound_node(inputs=None, outputs=None, name=None):
    io_node = node(compute_bound_task, inputs=inputs, outputs=outputs, name=name)
    return io_node


def create_compute_bound_pipeline():
    dummy_pipeline = pipeline(
        [
            create_compute_bound_node("dummy_1", "numpy_1"),
            create_compute_bound_node("dummy_2", "numpy_2"),
            create_compute_bound_node("dummy_3", "numpy_3"),
            create_compute_bound_node("dummy_4", "numpy_4"),
            create_compute_bound_node("dummy_5", "numpy_5"),
            create_compute_bound_node("dummy_6", "numpy_6"),
            create_compute_bound_node("dummy_7", "numpy_7"),
            create_compute_bound_node("dummy_1", "numpy_8"),
            create_compute_bound_node("dummy_1", "numpy_9"),
            create_compute_bound_node("dummy_1", "numpy_10"),
        ]
    )
    return dummy_pipeline


class TimeSuite:
    """
    A dummy benchmark suite to test with asv framework.
    """

    def setup(self):
        self.d = {}
        for x in range(500):
            self.d[x] = None

    def time_keys(self):
        for key in self.d.keys():
            pass


if __name__ == "__main__":
    print("===" * 20)
    import time

    result = {}
    runner_class = {
        "SequentialRunner": SequentialRunner,
        "ThreadRunner": ThreadRunner,
        "ParallelRunner": ParallelRunner,
    }
    for name, runner in runner_class.items():
        start = time.time()
        print("==" * 20 + name + "==" * 20)
        catalog = create_data_catalog()
        test_pipeline = create_compute_bound_pipeline()
        runner = runner()
        runner.run(test_pipeline, catalog=catalog)
        end = time.time()
        result[name] = end - start
        print(f"Time spent: {end - start}")

    print("===" * 20 + "Done" + "===" * 20)
    print(result)
