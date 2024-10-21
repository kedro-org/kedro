import pandas as pd
from kedro_datasets.pandas import CSVDataset

from kedro.io import DataCatalog

base_catalog = {
    f"dataset_{i}": {
        "type": "pandas.CSVDataset",
        "filepath": f"data_{i}.csv",
    } for i in range(1, 1001)
}
# Add datasets with the same filepath for loading
base_catalog.update({
    f"dataset_load_{i}": {
        "type": "pandas.CSVDataset",
        "filepath": "data.csv",
    } for i in range(1, 1001)
})
# Add a factory pattern
base_catalog.update({
    "dataset_factory_{placeholder}": {
        "type": "pandas.CSVDataset",
        "filepath": "data_{placeholder}.csv",
    }
})

class TimeDataCatalog:
    def setup(self):
        self.catalog = DataCatalog.from_config(base_catalog)
        self.dataframe = pd.DataFrame({"column": [1, 2, 3]})
        self.dataframe.to_csv("data.csv", index=False)
        self.datasets = {
            f"dataset_new_{i}": CSVDataset(filepath="data.csv") for i in range(1, 1001)
        }
        self.feed_dict = {
            f"param_{i}": i for i in range(1, 1001)
        }

    def time_init(self):
        """Benchmark the time to initialize the catalog"""
        DataCatalog.from_config(base_catalog)

    def time_save(self):
        """Benchmark the time to save datasets"""
        for i in range(1,1001):
            self.catalog.save(f"dataset_{i}", self.dataframe)

    def time_load(self):
        """Benchmark the time to load datasets"""
        for i in range(1,1001):
            self.catalog.load(f"dataset_load_{i}")

    def time_exists(self):
        """Benchmark the time to check if datasets exist"""
        for i in range(1,1001):
            self.catalog.exists(f"dataset_{i}")

    def time_release(self):
        """Benchmark the time to release datasets"""
        for i in range(1,1001):
            self.catalog.release(f"dataset_{i}")

    def time_add_all(self):
        """Benchmark the time to add all datasets"""
        # Have to initialise a new DataCatalog to avoid failing with DatasetAlreadyExistsError
        catalog = DataCatalog.from_config(base_catalog)
        catalog.add_all(self.datasets)

    def time_feed_dict(self):
        """Benchmark the time to add feed dict"""
        # Have to initialise a new DataCatalog to avoid failing with DatasetAlreadyExistsError
        catalog = DataCatalog.from_config(base_catalog)
        catalog.add_feed_dict(self.feed_dict)

    def time_list(self):
        """Benchmark the time to list all datasets"""
        self.catalog.list()

    def time_shallow_copy(self):
        """Benchmark the time to shallow copy the catalog"""
        self.catalog.shallow_copy()

    def time_resolve_factory(self):
        """Benchmark the time to resolve factory"""
        for i in range(1,1001):
            self.catalog._get_dataset(f"dataset_factory_{i}")
