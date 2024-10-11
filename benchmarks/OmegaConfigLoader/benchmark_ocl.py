from pathlib import Path
import os
import tempfile
from kedro.config import OmegaConfigLoader

class TimeOmegaConfigLoader:
    
    def setup(self):
        # Setup temporary configuration directory with sample config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conf_source = Path(self.temp_dir.name)
        self.env = "local"

        # Create sample config files in the temp directory
        self._create_config_file("base", "globals.yml", {"global_param": "value"})
        self._create_config_file("base", "catalog.yml", {"dataset": {"type": "pandas.CSVDataSet"}})
        self._create_config_file("local", "catalog.yml", {"dataset": {"filepath": "data.csv"}})
        
        # Instantiate the OmegaConfigLoader
        self.loader = OmegaConfigLoader(conf_source=self.conf_source.as_posix(), env=self.env)

    def teardown(self):
        # Cleanup temporary directory
        self.temp_dir.cleanup()

    def _create_config_file(self, env, file_name, data):
        env_path = self.conf_source / env
        env_path.mkdir(parents=True, exist_ok=True)
        file_path = env_path / file_name

        import yaml
        with open(file_path, "w") as f:
            yaml.dump(data, f)

    def time_loading_base_config(self):
        """Benchmark the time to load the base configuration"""
        config = self.loader["globals"]
    
    def time_loading_env_config(self):
        """Benchmark the time to load environment-specific configuration"""
        config = self.loader["catalog"]
    
    def time_merge_soft_strategy(self):
        """Benchmark the time to load and soft-merge configurations"""
        self.loader.merge_strategy = {"catalog": "soft"}
        config = self.loader["catalog"]
    
    def time_merge_destructive_strategy(self):
        """Benchmark the time to load and destructively merge configurations"""
        self.loader.merge_strategy = {"catalog": "destructive"}
        config = self.loader["catalog"]

    def peak_memory_loading_config(self):
        """Benchmark peak memory usage during config loading"""
        config = self.loader["catalog"]

    def peak_memory_soft_merge(self):
        """Benchmark peak memory usage during soft merge"""
        self.loader.merge_strategy = {"catalog": "soft"}
        config = self.loader["catalog"]
