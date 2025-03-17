# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

import importlib
import time
from pathlib import Path

import yaml

from kedro.io.data_catalog import DataCatalog
from kedro.pipeline import node, pipeline


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
    filepath: benchmarks/data/'{pattern}.csv'

'numpy_{pattern}':
    type: pickle.PickleDataset
    filepath: benchmarks/data/'{pattern}.pkl'

'{catch_all_dataset_pattern}':
    type: pandas.CSVDataset
    filepath: benchmarks/data/data.csv
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


class RunnerMemorySuite:
    params = (
        "SequentialRunner",
        "ThreadRunner",
        "ParallelRunner",
    )
    param_names = ("runner",)

    def setup(self, *args, **kwargs):
        data_dir = Path("benchmarks/data")
        data_dir.mkdir(exist_ok=True, parents=True)

        # Create a dummy csv
        with open(data_dir / "data.csv", "w") as f:
            f.write("col1,col2\n1,2\n")

    def mem_runners(self, runner):
        catalog = create_data_catalog()
        test_pipeline = create_compute_bound_pipeline()
        runner_module = importlib.import_module("kedro.runner")
        runner_obj = getattr(runner_module, runner)()
        runner_obj.run(test_pipeline, catalog=catalog)

    def peakmem_runners(self, runner):
        catalog = create_data_catalog()
        test_pipeline = create_compute_bound_pipeline()
        runner_module = importlib.import_module("kedro.runner")
        runner_obj = getattr(runner_module, runner)()
        runner_obj.run(test_pipeline, catalog=catalog)


class RunnerTimeSuite:
    params = (
        "SequentialRunner",
        "ThreadRunner",
        "ParallelRunner",
    )
    param_names = ("runner",)

    def setup(self, *args, **kwargs):
        data_dir = Path("benchmarks/data")
        data_dir.mkdir(exist_ok=True, parents=True)

        # Create a dummy csv
        with open(data_dir / "data.csv", "w") as f:
            f.write("col1,col2\n1,2\n")

    def time_compute_bound_runner(self, runner):
        catalog = create_data_catalog()
        test_pipeline = create_compute_bound_pipeline()
        runner_module = importlib.import_module("kedro.runner")
        runner_obj = getattr(runner_module, runner)()
        runner_obj.run(test_pipeline, catalog=catalog)

    def time_io_bound_runner(self, runner):
        """IO bound pipeline"""
        catalog = create_data_catalog()
        test_pipeline = create_io_bound_pipeline()
        runner_module = importlib.import_module("kedro.runner")
        runner_obj = getattr(runner_module, runner)()
        runner_obj.run(test_pipeline, catalog=catalog)
