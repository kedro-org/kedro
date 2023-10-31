from __future__ import annotations

import configparser
import json
import re
from pathlib import Path

import pytest
import yaml
from yaml.parser import ParserError

from kedro.config import BadConfigException, ConfigLoader, MissingConfigException

_DEFAULT_RUN_ENV = "local"
_BASE_ENV = "base"


def _write_yaml(filepath: Path, config: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _write_json(filepath: Path, config: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(config)
    filepath.write_text(json_str)


def _write_dummy_ini(filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config["prod"] = {"url": "postgresql://user:pass@url_prod/db"}
    config["staging"] = {"url": "postgresql://user:pass@url_staging/db"}
    with filepath.open("wt") as configfile:  # save
        config.write(configfile)


@pytest.fixture
def base_config(tmp_path):
    filepath = str(tmp_path / "cars.csv")
    return {
        "trains": {"type": "MemoryDataset"},
        "cars": {
            "type": "pandas.CSVDataset",
            "filepath": filepath,
            "save_args": {"index": True},
        },
    }


@pytest.fixture
def local_config(tmp_path):
    filepath = str(tmp_path / "cars.csv")
    return {
        "cars": {
            "type": "pandas.CSVDataset",
            "filepath": filepath,
            "save_args": {"index": False},
        },
        "boats": {"type": "MemoryDataset"},
    }


@pytest.fixture
def create_config_dir(tmp_path, base_config, local_config):
    proj_catalog = tmp_path / _BASE_ENV / "catalog.yml"
    local_catalog = tmp_path / _DEFAULT_RUN_ENV / "catalog.yml"
    parameters = tmp_path / _BASE_ENV / "parameters.json"
    db_config_path = tmp_path / _BASE_ENV / "db.ini"
    project_parameters = {"param1": 1, "param2": 2}

    _write_yaml(proj_catalog, base_config)
    _write_yaml(local_catalog, local_config)
    _write_json(parameters, project_parameters)
    _write_dummy_ini(db_config_path)


@pytest.fixture
def proj_catalog(tmp_path, base_config):
    proj_catalog = tmp_path / _BASE_ENV / "catalog.yml"
    _write_yaml(proj_catalog, base_config)


@pytest.fixture
def proj_catalog_nested(tmp_path):
    path = tmp_path / _BASE_ENV / "catalog" / "dir" / "nested.yml"
    _write_yaml(path, {"nested": {"type": "MemoryDataset"}})


use_config_dir = pytest.mark.usefixtures("create_config_dir")
use_proj_catalog = pytest.mark.usefixtures("proj_catalog")


class TestConfigLoader:
    @use_config_dir
    def test_load_core_config_dict_get(self, tmp_path):
        """Make sure core config can be fetched with a dict [] access."""
        conf = ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV)
        params = conf["parameters"]
        catalog = conf["catalog"]

        assert params["param1"] == 1
        assert catalog["trains"]["type"] == "MemoryDataset"
        assert catalog["cars"]["type"] == "pandas.CSVDataset"
        assert catalog["boats"]["type"] == "MemoryDataset"
        assert not catalog["cars"]["save_args"]["index"]

    @use_config_dir
    def test_load_local_config(self, tmp_path):
        """Make sure that configs from `local/` override the ones
        from `base/`"""
        conf = ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV)
        params = conf.get("parameters*")
        db_conf = conf.get("db*")
        catalog = conf.get("catalog*")

        assert params["param1"] == 1
        assert db_conf["prod"]["url"] == "postgresql://user:pass@url_prod/db"

        assert catalog["trains"]["type"] == "MemoryDataset"
        assert catalog["cars"]["type"] == "pandas.CSVDataset"
        assert catalog["boats"]["type"] == "MemoryDataset"
        assert not catalog["cars"]["save_args"]["index"]

    @use_proj_catalog
    def test_load_base_config(self, tmp_path, base_config):
        """Test config loading if `local/` directory is empty"""
        (tmp_path / _DEFAULT_RUN_ENV).mkdir(exist_ok=True)
        catalog = ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV).get("catalog*.yml")
        assert catalog == base_config

    @use_proj_catalog
    def test_duplicate_patterns(self, tmp_path, base_config):
        """Test config loading if the glob patterns cover the same file"""
        (tmp_path / _DEFAULT_RUN_ENV).mkdir(exist_ok=True)
        conf = ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV)
        catalog1 = conf.get("catalog*.yml", "catalog*.yml")
        catalog2 = conf.get("catalog*.yml", "catalog.yml")
        assert catalog1 == catalog2 == base_config

    def test_subdirs_dont_exist(self, tmp_path, base_config):
        """Check the error when config paths don't exist"""
        pattern = (
            r"Given configuration path either does not exist "
            r"or is not a valid directory\: {}"
        )
        with pytest.raises(ValueError, match=pattern.format(".*base")):
            ConfigLoader(str(tmp_path)).get("catalog*")
        with pytest.raises(ValueError, match=pattern.format(".*local")):
            proj_catalog = tmp_path / _BASE_ENV / "catalog.yml"
            _write_yaml(proj_catalog, base_config)
            ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV).get("catalog*")

    @pytest.mark.usefixtures("create_config_dir", "proj_catalog", "proj_catalog_nested")
    def test_nested(self, tmp_path):
        """Test loading the config from subdirectories"""
        config_loader = ConfigLoader(str(tmp_path))
        config_loader.default_run_env = ""
        catalog = config_loader.get("catalog*", "catalog*/**")
        assert catalog.keys() == {"cars", "trains", "nested"}
        assert catalog["cars"]["type"] == "pandas.CSVDataset"
        assert catalog["cars"]["save_args"]["index"] is True
        assert catalog["nested"]["type"] == "MemoryDataset"

    @use_config_dir
    def test_nested_subdirs_duplicate(self, tmp_path, base_config):
        """Check the error when the configs from subdirectories contain
        duplicate keys"""
        nested = tmp_path / _BASE_ENV / "catalog" / "dir" / "nested.yml"
        _write_yaml(nested, base_config)

        pattern = (
            r"Duplicate keys found in .*catalog\.yml "
            r"and\:\n\- .*nested\.yml\: cars, trains"
        )
        with pytest.raises(ValueError, match=pattern):
            ConfigLoader(str(tmp_path)).get("catalog*", "catalog*/**")

    def test_ignore_hidden_keys(self, tmp_path):
        """Check that the config key starting with `_` are ignored and also
        don't cause a config merge error"""
        _write_yaml(tmp_path / _BASE_ENV / "catalog1.yml", {"k1": "v1", "_k2": "v2"})
        _write_yaml(tmp_path / _BASE_ENV / "catalog2.yml", {"k3": "v3", "_k2": "v4"})

        conf = ConfigLoader(str(tmp_path))
        conf.default_run_env = ""
        catalog = conf.get("**/catalog*")
        assert catalog.keys() == {"k1", "k3"}

        _write_yaml(tmp_path / _BASE_ENV / "catalog3.yml", {"k1": "dup", "_k2": "v5"})
        pattern = (
            r"^Duplicate keys found in .*catalog3\.yml and\:\n\- .*catalog1\.yml\: k1$"
        )
        with pytest.raises(ValueError, match=pattern):
            conf.get("**/catalog*")

    def test_bad_config_syntax(self, tmp_path):
        conf_path = tmp_path / _BASE_ENV
        conf_path.mkdir(parents=True, exist_ok=True)
        (conf_path / "catalog.yml").write_text("bad;config")

        pattern = f"Couldn't load config file: {conf_path / 'catalog.yml'}"
        with pytest.raises(BadConfigException, match=re.escape(pattern)):
            ConfigLoader(str(tmp_path)).get("catalog*.yml")

    def test_lots_of_duplicates(self, tmp_path):
        """Check that the config key starting with `_` are ignored and also
        don't cause a config merge error"""
        data = {str(i): i for i in range(100)}
        _write_yaml(tmp_path / _BASE_ENV / "catalog1.yml", data)
        _write_yaml(tmp_path / _BASE_ENV / "catalog2.yml", data)

        conf = ConfigLoader(str(tmp_path))
        pattern = r"^Duplicate keys found in .*catalog2\.yml and\:\n\- .*catalog1\.yml\: .*\.\.\.$"
        with pytest.raises(ValueError, match=pattern):
            conf.get("**/catalog*")

    @use_config_dir
    def test_same_key_in_same_dir(self, tmp_path, base_config):
        """Check the error if 2 files in the same config dir contain
        the same top-level key"""
        dup_json = tmp_path / _BASE_ENV / "catalog.json"
        _write_json(dup_json, base_config)

        pattern = (
            r"Duplicate keys found in .*catalog\.yml "
            r"and\:\n\- .*catalog\.json\: cars, trains"
        )
        with pytest.raises(ValueError, match=pattern):
            ConfigLoader(str(tmp_path)).get("catalog*")

    @use_config_dir
    def test_empty_patterns(self, tmp_path):
        """Check the error if no config patterns were specified"""
        pattern = (
            r"'patterns' must contain at least one glob pattern "
            r"to match config filenames against"
        )
        with pytest.raises(ValueError, match=pattern):
            ConfigLoader(str(tmp_path)).get()

    @use_config_dir
    def test_no_files_found(self, tmp_path):
        """Check the error if no config files satisfy a given pattern"""
        pattern = (
            r"No files found in "
            r"\[\'.*base\', "
            r"\'.*local\'\] "
            r"matching the glob pattern\(s\): "
            r"\[\'non\-existent\-pattern\'\]"
        )
        with pytest.raises(MissingConfigException, match=pattern):
            ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV).get("non-existent-pattern")

    @use_config_dir
    def test_key_not_found_dict_get(self, tmp_path):
        """Check the error if no config files satisfy a given pattern"""
        with pytest.raises(KeyError):
            ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV)["non-existent-pattern"]

    @use_config_dir
    def test_no_files_found_dict_get(self, tmp_path):
        """Check the error if no config files satisfy a given pattern"""
        pattern = (
            r"No files found in "
            r"\[\'.*base\', "
            r"\'.*local\'\] "
            r"matching the glob pattern\(s\): "
            r"\[\'credentials\*\', \'credentials\*/\**\', \'\**/credentials\*\'\]"
        )
        with pytest.raises(MissingConfigException, match=pattern):
            ConfigLoader(str(tmp_path), _DEFAULT_RUN_ENV)["credentials"]

    def test_duplicate_paths(self, tmp_path, caplog):
        """Check that trying to load the same environment config multiple times logs a
        warning and skips the reload"""
        _write_yaml(tmp_path / _BASE_ENV / "catalog.yml", {"env": _BASE_ENV, "a": "a"})
        config_loader = ConfigLoader(str(tmp_path), _BASE_ENV)

        with pytest.warns(UserWarning, match="Duplicate environment detected"):
            config_paths = config_loader.conf_paths
        assert config_paths == [str(tmp_path / _BASE_ENV)]

        config_loader.get("catalog*", "catalog*/**")
        log_messages = [record.getMessage() for record in caplog.records]
        assert not log_messages

    def test_overlapping_patterns(self, tmp_path, caplog):
        """Check that same configuration file is not loaded more than once."""
        _write_yaml(
            tmp_path / _BASE_ENV / "catalog0.yml",
            {"env": _BASE_ENV, "common": "common"},
        )
        _write_yaml(
            tmp_path / "dev" / "catalog1.yml", {"env": "dev", "dev_specific": "wiz"}
        )
        _write_yaml(tmp_path / "dev" / "user1" / "catalog2.yml", {"user1_c2": True})
        _write_yaml(tmp_path / "dev" / "user1" / "catalog3.yml", {"user1_c3": True})

        catalog = ConfigLoader(str(tmp_path), "dev").get(
            "catalog*", "catalog*/**", "user1/catalog2*", "../**/catalog2*"
        )
        expected_catalog = {
            "env": "dev",
            "common": "common",
            "dev_specific": "wiz",
            "user1_c2": True,
        }
        assert catalog == expected_catalog

        log_messages = [record.getMessage() for record in caplog.records]
        expected_path = (tmp_path / "dev" / "user1" / "catalog2.yml").resolve()
        expected_message = (
            f"Config file(s): {expected_path} already processed, skipping loading..."
        )
        assert expected_message in log_messages

    def test_yaml_parser_error(self, tmp_path):
        conf_path = tmp_path / _BASE_ENV
        conf_path.mkdir(parents=True, exist_ok=True)

        example_catalog = """
        example_iris_data:
              type: pandas.CSVDataset
          filepath: data/01_raw/iris.csv
        """

        (conf_path / "catalog.yml").write_text(example_catalog)

        msg = f"Invalid YAML file {conf_path / 'catalog.yml'}, unable to read line 3, position 10."
        with pytest.raises(ParserError, match=re.escape(msg)):
            ConfigLoader(str(tmp_path)).get("catalog*.yml")

    def test_customised_config_patterns(self, tmp_path):
        config_loader = ConfigLoader(
            conf_source=str(tmp_path),
            config_patterns={
                "spark": ["spark*/"],
                "parameters": ["params*", "params*/**", "**/params*"],
            },
        )
        assert config_loader.config_patterns["catalog"] == [
            "catalog*",
            "catalog*/**",
            "**/catalog*",
        ]
        assert config_loader.config_patterns["spark"] == ["spark*/"]
        assert config_loader.config_patterns["parameters"] == [
            "params*",
            "params*/**",
            "**/params*",
        ]

    @use_config_dir
    def test_adding_extra_keys_to_confloader(self, tmp_path):
        """Make sure extra keys can be added directly to the config loader instance."""
        conf = ConfigLoader(str(tmp_path))
        catalog = conf["catalog"]
        conf["spark"] = {"spark_config": "emr.blabla"}

        assert catalog["trains"]["type"] == "MemoryDataset"
        assert conf["spark"] == {"spark_config": "emr.blabla"}

    @use_config_dir
    def test_bypass_catalog_config_loading(self, tmp_path):
        """Make sure core config loading can be bypassed by setting the key and values
        directly on the config loader instance."""
        conf = ConfigLoader(str(tmp_path))
        conf["catalog"] = {"catalog_config": "something_new"}

        assert conf["catalog"] == {"catalog_config": "something_new"}
