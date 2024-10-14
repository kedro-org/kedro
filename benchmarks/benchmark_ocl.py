import tempfile
from pathlib import Path

from kedro.config import OmegaConfigLoader

base_catalog = {
    "dataset_1": {
        "type": "pandas.CSVDataset",
        "filepath": "data1.csv"
    },
    "dataset_2": {
        "type": "pandas.CSVDataset",
        "filepath": "data2.csv"
    },
    "dataset_3": {
        "type": "pandas.CSVDataset",
        "filepath": "data3.csv"
    },
    "dataset_4": {
        "type": "pandas.CSVDataset",
        "filepath": "data4.csv",
        "versioned": True,
    },
}
local_catalog = {
    "dataset_4" : {
        "filepath": "data4_local.csv",
        "type": "pandas.CSVDataset",
    },
    "dataset_5" : {
        "filepath": "data5_local.csv",
        "type": "pandas.CSVDataset",
    },
}
base_params = {
    "param_1": "value_1",
    "param_2": "value_2",
    "param_3": "value_3",
    "param_4": "value_4",
}
local_params = {
    "param_4": "value_4_local",
    "param_5": "value_5_local",
}
base_globals = {
    "global1": "value1",
    "global2": "value2",
    "global3": "value3",
    "global4": "value4",
}
local_globals = {
    "global4": "value4_local",
    "global5": "value5_local",
}

def _create_config_file(self, env, file_name, data):
        env_path = self.conf_source / env
        env_path.mkdir(parents=True, exist_ok=True)
        file_path = env_path / file_name

        import yaml
        with open(file_path, "w") as f:
            yaml.dump(data, f)


class TimeOmegaConfigLoader:

    def setup(self):
        # Setup temporary configuration directory with sample config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conf_source = Path(self.temp_dir.name)

        # Create sample config files in the temp directory
        _create_config_file("base", "catalog.yml", base_catalog)
        _create_config_file("local", "catalog.yml", local_catalog)
        _create_config_file("base", "parameters.yml", base_params)
        _create_config_file("local", "parameters.yml", local_params)
        _create_config_file("base", "globals.yml", base_globals)
        _create_config_file("local", "globals.yml", local_globals)

        # Instantiate the OmegaConfigLoader
        self.loader = OmegaConfigLoader(conf_source=self.conf_source, base_env='base', default_run_env='local')

    def teardown(self):
        # Cleanup temporary directory
        self.temp_dir.cleanup()

    def time_loading_catalog(self):
        """Benchmark the time to load the catalog"""
        self.loader["catalog"]

    def time_loading_parameters(self):
        """Benchmark the time to load environment-specific configuration"""
        self.loader["parameters"]

    def time_loading_parameters_runtime(self):
        """Benchmark the time to load parameters with runtime configuration"""
        self.loader.runtime_params = {"param_6": "value_6", "param_7": "value_7"}
        self.loader["parameters"]

    def time_loading_globals(self):
        """Benchmark the time to load global configuration"""
        self.loader["globals"]

    def time_merge_soft_strategy(self):
        """Benchmark the time to load and soft-merge configurations"""
        self.loader.merge_strategy = {"catalog": "soft"}
        self.loader["catalog"]

base_catalog_resolvers = {
    "dataset_4": {
        "type": "pandas.CSVDataset",
        "filepath": "${_basepath}/data4.csv",
        "versioned": True,
    },
    "_basepath": "folder",
}
base_params_resolvers = {
    "param_2": "${globals:global4}",
    "param_3": "${my_custom_resolver:custom_resolver}",
}
def custom_resolver(value):
    return f"custom_{value}"

class TimeOmegaConfigLoaderAdvanced:

    def setup(self):
        # Setup temporary configuration directory with sample config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conf_source = Path(self.temp_dir.name)
        custom_resolvers = {"my_custom_resolver": custom_resolver}

        base_catalog.update(base_catalog_resolvers)
        base_params.update(base_params_resolvers)

        # Create sample config files in the temp directory
        _create_config_file("base", "catalog.yml", base_catalog)
        _create_config_file("local", "catalog.yml", local_catalog)
        _create_config_file("base", "parameters.yml", base_params)
        _create_config_file("local", "parameters.yml", local_params)
        _create_config_file("base", "globals.yml", base_globals)
        _create_config_file("local", "globals.yml", local_globals)

        # Instantiate the OmegaConfigLoader
        self.loader = OmegaConfigLoader(conf_source=self.conf_source, base_env='base', default_run_env='local', custom_resolvers=custom_resolvers)

    def teardown(self):
        # Cleanup temporary directory
        self.temp_dir.cleanup()

    def time_loading_catalog(self):
        """Benchmark the time to load the catalog"""
        self.loader["catalog"]

    def time_loading_parameters(self):
        """Benchmark the time to load environment-specific configuration"""
        self.loader["parameters"]

    def time_loading_globals(self):
        """Benchmark the time to load global configuration"""
        self.loader["globals"]
