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

runtime_patterns = {
    "{placeholder}": {
        "type": "pandas.CSVDataset",
        "filepath": "{placeholder}.csv",
    }
}

class TimeDataCatalog:
    def setup(self):
        self.catalog = DataCatalog.from_config(base_catalog)
        self.dataframe = pd.DataFrame({"column": [1, 2, 3]})
        self.dataframe.to_csv("data.csv", index=False)
        self.datasets = {
            f"dataset_new_{i}": CSVDataset(filepath="data.csv") for i in range(1, 1001)
        }
        self.parameters = {
            f"param_{i}": i for i in range(1, 1001)
        }

    def time_init(self):
        """Benchmark the time to initialize the catalog"""
        DataCatalog.from_config(base_catalog)

    def time_contains(self):
        """Benchmark the time to check if a dataset exists"""
        for i in range(1,1001):
            f"dataset_{i}" in self.catalog

    def time_getitem(self):
        """Benchmark the time to get a dataset"""
        for i in range(1,1001):
            self.catalog[f"dataset_{i}"]


    def time_get(self):
        """Benchmark the time to get a dataset"""
        for i in range(1,1001):
            self.catalog.get(f"dataset_{i}")

    def time_iter(self):
        """Benchmark the time to iterate over the catalog"""
        for dataset in self.catalog:
            pass

    def time_keys(self):
        """Benchmark the time to get the keys of the catalog"""
        self.catalog.keys()

    def time_values(self):
        """Benchmark the time to get the items of the catalog"""
        self.catalog.values()

    def time_items(self):
        """Benchmark the time to get the items of the catalog"""
        self.catalog.items()

    def time_setitem(self):
        """Benchmark the time to set a dataset"""
        for i in range(1,1001):
            self.catalog[f"dataset_new_{i}"] = CSVDataset(filepath="data.csv")

    def time_setitem_raw(self):
        """Benchmark the time to add a memory dataset"""
        for i in range(1,1001):
            self.catalog[f"param_{i}"] = self.parameters[f"param_{i}"]

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

    def time_resolve_factory(self):
        """Benchmark the time to resolve factory"""
        for i in range(1,1001):
            self.catalog.get(f"dataset_factory_{i}")
