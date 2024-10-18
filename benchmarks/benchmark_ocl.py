import tempfile
from pathlib import Path

from kedro.config import OmegaConfigLoader


# Helper functions to generate sample configuration data
def _generate_catalog(start_range, end_range, is_local=False, is_versioned=False, add_interpolation=False):
    catalog = {}
    for i in range(start_range, end_range + 1):
        catalog[f"dataset_{i}"] = {
            "type": "pandas.CSVDataset",
            "filepath": f"data{i}{'_local' if is_local else ''}.csv"
        }
        if is_versioned:
            catalog[f"dataset_{i}"]["versioned"] = True
        if add_interpolation:
            catalog[f"dataset_{i}"]["filepath"] = "${_basepath}" + catalog[f"dataset_{i}"]["filepath"]
    return catalog

def _generate_params(start_range, end_range, is_local=False, add_globals=False):
    if add_globals:
        # Generate params with "${globals:global{i}}"
        params = {f"param_{i}": f"${{globals:global_{i}}}" for i in range(start_range, end_range + 1)}
    else:
        # Generate params with "value_{i}" or "value_{i}_local"
        params = {f"param_{i}": f"value_{i}{'_local' if is_local else ''}" for i in range(start_range, end_range + 1)}

    return params

def _generate_globals(start_range, end_range, is_local=False):
    globals_dict = {f"global_{i}": f"value{i}{'_local' if is_local else ''}" for i in range(start_range, end_range + 1)}
    return globals_dict

def _create_config_file(conf_source, env, file_name, data):
    env_path = conf_source / env
    env_path.mkdir(parents=True, exist_ok=True)
    file_path = env_path / file_name

    import yaml
    with open(file_path, "w") as f:
        yaml.dump(data, f)

base_catalog = _generate_catalog(1, 1000, is_versioned=True)
local_catalog = _generate_catalog(501, 1500, is_local=True)
base_params = _generate_params(1, 1000)
local_params = _generate_params(501, 1500, is_local=True)
base_globals = _generate_globals(1, 1000)
local_globals = _generate_globals(501, 1500, is_local=True)

base_catalog_with_interpolations = _generate_catalog(1, 1000, is_versioned=True, add_interpolation=True)
base_catalog_with_interpolations.update({"_basepath": "/path/to/data"})
local_catalog_with_interpolations = _generate_catalog(501, 1500, is_local=True, add_interpolation=True)
local_catalog_with_interpolations.update({"_basepath": "/path/to/data"})

base_params_with_globals = _generate_params(1, 100, add_globals=True)


class TimeOmegaConfigLoader:
    def setup(self):
        # Setup temporary configuration directory with sample config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conf_source = Path(self.temp_dir.name)

        # Create sample config files in the temp directory
        _create_config_file(self.conf_source, "base", "catalog.yml", base_catalog)
        _create_config_file(self.conf_source, "local", "catalog.yml", local_catalog)
        _create_config_file(self.conf_source, "base", "parameters.yml", base_params)
        _create_config_file(self.conf_source, "local", "parameters.yml", local_params)
        _create_config_file(self.conf_source, "base", "globals.yml", base_globals)
        _create_config_file(self.conf_source, "local", "globals.yml", local_globals)

        # Instantiate the OmegaConfigLoader
        self.loader = OmegaConfigLoader(conf_source=self.conf_source, base_env='base', default_run_env='local')

    def teardown(self):
        # Cleanup temporary directory
        self.temp_dir.cleanup()

    def time_loading_catalog(self):
        """Benchmark the time to load the catalog"""
        self.loader["catalog"]

    def time_loading_parameters(self):
        """Benchmark the time to load the parameters"""
        self.loader["parameters"]

    def time_loading_globals(self):
        """Benchmark the time to load global configuration"""
        self.loader["globals"]

    def time_loading_parameters_runtime(self):
        """Benchmark the time to load parameters with runtime configuration"""
        self.loader.runtime_params = _generate_params(2001, 2002)
        self.loader["parameters"]

    def time_merge_soft_strategy(self):
        """Benchmark the time to load and soft-merge configurations"""
        self.loader.merge_strategy = {"catalog": "soft"}
        self.loader["catalog"]


class TimeOmegaConfigLoaderAdvanced:
    def setup(self):
        # Setup temporary configuration directory with sample config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conf_source = Path(self.temp_dir.name)

        # Create sample config files in the temp directory
        _create_config_file(self.conf_source, "base", "catalog.yml", base_catalog_with_interpolations)
        _create_config_file(self.conf_source, "local", "catalog.yml", local_catalog_with_interpolations)
        _create_config_file(self.conf_source, "base", "parameters.yml", base_params_with_globals)
        _create_config_file(self.conf_source, "base", "globals.yml", base_globals)

        # Instantiate the OmegaConfigLoader
        self.loader = OmegaConfigLoader(conf_source=self.conf_source, base_env='base', default_run_env='local')

    def teardown(self):
        # Cleanup temporary directory
        self.temp_dir.cleanup()

    def time_loading_catalog(self):
        """Benchmark the time to load the catalog"""
        self.loader["catalog"]

    def time_loading_parameters(self):
        """Benchmark the time to load parameters with global interpolation"""
        self.loader["parameters"]
