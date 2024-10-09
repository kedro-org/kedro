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
def compute_bound_task(input_data: str) -> str:
    # Simulate a heavy computation (e.g., large matrix multiplication)
    matrix_size = 1000
    matrix_a = np.random.rand(matrix_size, matrix_size)
    matrix_b = np.random.rand(matrix_size, matrix_size)
    _ = np.dot(matrix_a, matrix_b)  # Matrix multiplication
    return f"Computed {input_data}"

def create_data_catalog():
    """
    Use dataset factory pattern to make sure the benchmark cover the slowest path.
    """
    catalog_conf = """

'output_{pattern}':
    type: pandas.CSVDataset
    filepath: '{pattern}.csv'

'numpy_{pattern}':
    type: pickle.PickletDataset
    filepath: '{pattern}.pkl'

'{catch_all_dataset_pattern}':
    type: pandas.CSVDataset
    filepath: data.csv
"""
    catalog_conf = yaml.safe_load(catalog_conf)
    catalog = DataCatalog.from_config(catalog_conf)
    return catalog


def create_io_bound_node(inputs=None, outputs=None,name=None):
    io_node = node(io_bound_task, inputs=inputs, outputs=outputs, name=name)
    return io_node


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
    print("==="*20)

    dummy_pipeline = pipeline([
        create_io_bound_node("dummy_1","output_1",name="dummy_1"),
        create_io_bound_node("dummy_2","output_2",name="dummy_2"),
        create_io_bound_node("dummy_3","output_3",name="dummy_3"),
    ])
    runner = SequentialRunner()
    catalog = create_data_catalog()
    runner.run(dummy_pipeline, catalog)

    print("===" * 20 + "Done" + "===" * 20)