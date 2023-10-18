from __future__ import annotations

import configparser
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml
from omegaconf import OmegaConf, errors
from omegaconf.errors import InterpolationResolutionError, UnsupportedInterpolationType
from omegaconf.resolvers import oc
from yaml.parser import ParserError

from kedro.config import MissingConfigException, OmegaConfigLoader

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
    base_catalog = tmp_path / _BASE_ENV / "catalog.yml"
    base_logging = tmp_path / _BASE_ENV / "logging.yml"
    base_spark = tmp_path / _BASE_ENV / "spark.yml"

    local_catalog = tmp_path / _DEFAULT_RUN_ENV / "catalog.yml"

    parameters = tmp_path / _BASE_ENV / "parameters.json"
    base_parameters = {"param1": 1, "param2": 2, "interpolated_param": "${test_env}"}
    base_global_parameters = {"test_env": "base"}
    local_global_parameters = {"test_env": "local"}

    _write_yaml(base_catalog, base_config)
    _write_yaml(local_catalog, local_config)

    # Empty Config
    _write_yaml(base_logging, {"version": 1})
    _write_yaml(base_spark, {"dummy": 1})

    _write_json(parameters, base_parameters)
    _write_json(tmp_path / _BASE_ENV / "parameters_global.json", base_global_parameters)
    _write_json(
        tmp_path / _DEFAULT_RUN_ENV / "parameters_global.json", local_global_parameters
    )


@pytest.fixture
def proj_catalog(tmp_path, base_config):
    proj_catalog = tmp_path / _BASE_ENV / "catalog.yml"
    _write_yaml(proj_catalog, base_config)


@pytest.fixture
def proj_catalog_nested(tmp_path):
    path = tmp_path / _BASE_ENV / "catalog" / "dir" / "nested.yml"
    _write_yaml(path, {"nested": {"type": "MemoryDataset"}})


@pytest.fixture
def proj_catalog_env_variable(tmp_path):
    path = tmp_path / _BASE_ENV / "catalog" / "dir" / "nested.yml"
    _write_yaml(path, {"test": {"file_path": "${oc.env:TEST_FILE_PATH}"}})


@pytest.fixture
def proj_credentials_env_variable(tmp_path):
    path = tmp_path / _DEFAULT_RUN_ENV / "credentials.yml"
    _write_yaml(
        path, {"user": {"name": "${oc.env:TEST_USERNAME}", "key": "${oc.env:TEST_KEY}"}}
    )


use_config_dir = pytest.mark.usefixtures("create_config_dir")
use_proj_catalog = pytest.mark.usefixtures("proj_catalog")
use_credentials_env_variable_yml = pytest.mark.usefixtures(
    "proj_credentials_env_variable"
)
use_catalog_env_variable_yml = pytest.mark.usefixtures("proj_catalog_env_variable")


class TestOmegaConfigLoader:
    @use_config_dir
    def test_load_core_config_dict_syntax(self, tmp_path):
        """Make sure core config can be fetched with a dict [] access."""
        conf = OmegaConfigLoader(str(tmp_path))
        params = conf["parameters"]
        catalog = conf["catalog"]

        assert params["param1"] == 1
        assert catalog["trains"]["type"] == "MemoryDataset"

    @use_config_dir
    def test_load_core_config_get_syntax(self, tmp_path):
        """Make sure core config can be fetched with .get()"""
        conf = OmegaConfigLoader(str(tmp_path))
        params = conf.get("parameters")
        catalog = conf.get("catalog")

        assert params["param1"] == 1
        assert catalog["trains"]["type"] == "MemoryDataset"

    @use_config_dir
    def test_load_local_config_overrides_base(self, tmp_path):
        """Make sure that configs from `local/` override the ones
        from `base/`"""
        conf = OmegaConfigLoader(str(tmp_path))
        params = conf["parameters"]
        catalog = conf["catalog"]

        assert params["param1"] == 1
        assert catalog["trains"]["type"] == "MemoryDataset"
        assert catalog["cars"]["type"] == "pandas.CSVDataset"
        assert catalog["boats"]["type"] == "MemoryDataset"
        assert not catalog["cars"]["save_args"]["index"]

    @use_proj_catalog
    def test_load_base_config(self, tmp_path, base_config):
        """Test config loading if `local/` directory is empty"""
        (tmp_path / _DEFAULT_RUN_ENV).mkdir(exist_ok=True)
        catalog = OmegaConfigLoader(str(tmp_path))["catalog"]
        assert catalog == base_config

    @use_proj_catalog
    def test_duplicate_patterns(self, tmp_path, base_config):
        """Test config loading if the glob patterns cover the same file"""
        (tmp_path / _DEFAULT_RUN_ENV).mkdir(exist_ok=True)
        conf = OmegaConfigLoader(str(tmp_path))
        catalog1 = conf["catalog"]
        catalog2 = conf["catalog"]
        assert catalog1 == catalog2 == base_config

    def test_subdirs_dont_exist(self, tmp_path, base_config):
        """Check the error when config paths don't exist"""
        pattern = (
            r"Given configuration path either does not exist "
            r"or is not a valid directory\: {}"
        )
        with pytest.raises(MissingConfigException, match=pattern.format(".*base")):
            OmegaConfigLoader(str(tmp_path))["catalog"]
        with pytest.raises(MissingConfigException, match=pattern.format(".*local")):
            proj_catalog = tmp_path / _BASE_ENV / "catalog.yml"
            _write_yaml(proj_catalog, base_config)
            OmegaConfigLoader(str(tmp_path))["catalog"]

    @pytest.mark.usefixtures("create_config_dir", "proj_catalog", "proj_catalog_nested")
    def test_nested(self, tmp_path):
        """Test loading the config from subdirectories"""
        config_loader = OmegaConfigLoader(str(tmp_path))
        config_loader.default_run_env = "prod"

        prod_catalog = tmp_path / "prod" / "catalog.yml"
        _write_yaml(prod_catalog, {})

        catalog = config_loader["catalog"]
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
            r"Duplicate keys found in "
            r"(.*catalog\.yml and .*nested\.yml|.*nested\.yml and .*catalog\.yml)"
            r"\: cars, trains"
        )
        with pytest.raises(ValueError, match=pattern):
            OmegaConfigLoader(str(tmp_path))["catalog"]

    @use_config_dir
    def test_multiple_nested_subdirs_duplicates(
        self, tmp_path, base_config, local_config
    ):
        """Check the error when several config files from subdirectories contain
        duplicate keys"""
        nested = tmp_path / _BASE_ENV / "catalog" / "dir" / "nested.yml"
        _write_yaml(nested, base_config)

        local = tmp_path / _BASE_ENV / "catalog" / "dir" / "local.yml"
        _write_yaml(local, local_config)

        pattern_catalog_nested = (
            r"Duplicate keys found in "
            r"(.*catalog\.yml and .*nested\.yml|.*nested\.yml and .*catalog\.yml)"
            r"\: cars, trains"
        )
        pattern_catalog_local = (
            r"Duplicate keys found in "
            r"(.*catalog\.yml and .*local\.yml|.*local\.yml and .*catalog\.yml)"
            r"\: cars"
        )
        pattern_nested_local = (
            r"Duplicate keys found in "
            r"(.*nested\.yml and .*local\.yml|.*local\.yml and .*nested\.yml)"
            r"\: cars"
        )

        with pytest.raises(ValueError) as exc:
            OmegaConfigLoader(str(tmp_path))["catalog"]
        assert re.search(pattern_catalog_nested, str(exc.value))
        assert re.search(pattern_catalog_local, str(exc.value))
        assert re.search(pattern_nested_local, str(exc.value))

    @use_config_dir
    def test_bad_config_syntax(self, tmp_path):
        conf_path = tmp_path / _BASE_ENV
        conf_path.mkdir(parents=True, exist_ok=True)
        (conf_path / "catalog.yml").write_text("bad:\nconfig")

        pattern = f"Invalid YAML or JSON file {conf_path.as_posix()}"
        with pytest.raises(ParserError, match=re.escape(pattern)):
            OmegaConfigLoader(str(tmp_path))["catalog"]

    def test_lots_of_duplicates(self, tmp_path):
        data = {str(i): i for i in range(100)}
        _write_yaml(tmp_path / _BASE_ENV / "catalog1.yml", data)
        _write_yaml(tmp_path / _BASE_ENV / "catalog2.yml", data)

        conf = OmegaConfigLoader(str(tmp_path))
        pattern = (
            r"Duplicate keys found in "
            r"(.*catalog2\.yml and .*catalog1\.yml|.*catalog1\.yml and .*catalog2\.yml)"
            r"\: .*\.\.\.$"
        )
        with pytest.raises(ValueError, match=pattern):
            conf["catalog"]

    @use_config_dir
    def test_same_key_in_same_dir(self, tmp_path, base_config):
        """Check the error if 2 files in the same config dir contain
        the same top-level key"""
        dup_json = tmp_path / _BASE_ENV / "catalog.json"
        _write_json(dup_json, base_config)

        pattern = (
            r"Duplicate keys found in "
            r"(.*catalog\.yml and .*catalog\.json|.*catalog\.json and .*catalog\.yml)"
            r"\: cars, trains"
        )
        with pytest.raises(ValueError, match=pattern):
            OmegaConfigLoader(str(tmp_path))["catalog"]

    @use_config_dir
    def test_pattern_key_not_found(self, tmp_path):
        """Check the error if no config files satisfy a given pattern"""
        key = "non-existent-pattern"
        pattern = f"No config patterns were found for '{key}' in your config loader"
        with pytest.raises(KeyError, match=pattern):
            OmegaConfigLoader(str(tmp_path))[key]

    @use_config_dir
    def test_cannot_load_non_yaml_or_json_files(self, tmp_path):
        db_patterns = {"db": ["db*"]}
        db_config_path = tmp_path / _BASE_ENV / "db.ini"
        _write_dummy_ini(db_config_path)

        conf = OmegaConfigLoader(str(tmp_path), config_patterns=db_patterns)
        pattern = (
            r"No files of YAML or JSON format found in "
            r".*base or "
            r".*local "
            r"matching the glob pattern\(s\): "
            r"\[\'db\*\'\]"
        )
        with pytest.raises(MissingConfigException, match=pattern):
            conf["db"]

    @use_config_dir
    def test_no_files_found(self, tmp_path):
        """Check the error if no config files satisfy a given pattern"""
        pattern = (
            r"No files of YAML or JSON format found in "
            r".*base or "
            r".*local "
            r"matching the glob pattern\(s\): "
            r"\[\'credentials\*\', \'credentials\*/\**\', \'\**/credentials\*\'\]"
        )
        with pytest.raises(MissingConfigException, match=pattern):
            OmegaConfigLoader(str(tmp_path))["credentials"]

    def test_empty_catalog_file(self, tmp_path):
        """Check that empty catalog file is read and returns an empty dict"""
        _write_yaml(tmp_path / _BASE_ENV / "catalog_empty.yml", {})
        catalog_patterns = {"catalog": ["catalog*", "catalog*/**", "**/catalog*"]}
        catalog = OmegaConfigLoader(
            conf_source=tmp_path, env="base", config_patterns=catalog_patterns
        )["catalog"]
        assert catalog == {}

    def test_overlapping_patterns(self, tmp_path, mocker):
        """Check that same configuration file is not loaded more than once."""
        _write_yaml(
            tmp_path / _BASE_ENV / "catalog0.yml",
            {"env": _BASE_ENV, "common": "common"},
        )
        _write_yaml(
            tmp_path / "dev" / "catalog1.yml", {"env": "dev", "dev_specific": "wiz"}
        )
        _write_yaml(tmp_path / "dev" / "user1" / "catalog2.yml", {"user1_c2": True})

        catalog_patterns = {
            "catalog": [
                "catalog*",
                "catalog*/**",
                "../**/user1/catalog2*",
                "../**/catalog2*",
            ]
        }

        catalog = OmegaConfigLoader(
            conf_source=str(tmp_path), env="dev", config_patterns=catalog_patterns
        )["catalog"]
        expected_catalog = {
            "env": "dev",
            "common": "common",
            "dev_specific": "wiz",
            "user1_c2": True,
        }
        assert catalog == expected_catalog

        mocked_load = mocker.patch("omegaconf.OmegaConf.load")
        expected_path = (tmp_path / "dev" / "user1" / "catalog2.yml").resolve()
        assert mocked_load.called_once_with(expected_path)

    def test_yaml_parser_error(self, tmp_path):
        conf_path = tmp_path / _BASE_ENV
        conf_path.mkdir(parents=True, exist_ok=True)

        example_catalog = """
        example_iris_data:
              type: pandas.CSVDataset
          filepath: data/01_raw/iris.csv
        """

        (conf_path / "catalog.yml").write_text(example_catalog)

        msg = (
            f"Invalid YAML or JSON file {Path(conf_path, 'catalog.yml').as_posix()}, unable to read"
            f" line 3, position 10."
        )
        with pytest.raises(ParserError, match=re.escape(msg)):
            OmegaConfigLoader(str(tmp_path))["catalog"]

    def test_customised_config_patterns(self, tmp_path):
        config_loader = OmegaConfigLoader(
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

    def test_destructive_merging_strategy(self, tmp_path):
        mlflow_patterns = {"mlflow": ["mlflow*", "mlflow*/**", "**/mlflow*"]}
        base_mlflow = tmp_path / _BASE_ENV / "mlflow.yml"
        base_config = {
            "tracking": {
                "disable_tracking": {"pipelines": "[on_exit_notification]"},
                "experiment": {
                    "name": "name-of-local-experiment",
                },
                "params": {"long_params_strategy": "tag"},
            }
        }
        local_mlflow = tmp_path / _DEFAULT_RUN_ENV / "mlflow.yml"
        local_config = {
            "tracking": {
                "experiment": {
                    "name": "name-of-prod-experiment",
                },
            }
        }

        _write_yaml(base_mlflow, base_config)
        _write_yaml(local_mlflow, local_config)

        conf = OmegaConfigLoader(str(tmp_path), config_patterns=mlflow_patterns)[
            "mlflow"
        ]

        assert conf == {
            "tracking": {
                "experiment": {
                    "name": "name-of-prod-experiment",
                },
            }
        }

    @use_config_dir
    def test_adding_extra_keys_to_confloader(self, tmp_path):
        """Make sure extra keys can be added directly to the config loader instance."""
        conf = OmegaConfigLoader(str(tmp_path))
        catalog = conf["catalog"]
        conf["spark"] = {"spark_config": "emr.blabla"}

        assert catalog["trains"]["type"] == "MemoryDataset"
        assert conf["spark"] == {"spark_config": "emr.blabla"}

    @use_config_dir
    def test_bypass_catalog_config_loading(self, tmp_path):
        """Make sure core config loading can be bypassed by setting the key and values
        directly on the config loader instance."""
        conf = OmegaConfigLoader(str(tmp_path))
        conf["catalog"] = {"catalog_config": "something_new"}

        assert conf["catalog"] == {"catalog_config": "something_new"}

    @use_config_dir
    @use_credentials_env_variable_yml
    def test_load_credentials_from_env_variables(self, tmp_path):
        """Load credentials from environment variables"""
        conf = OmegaConfigLoader(str(tmp_path))
        os.environ["TEST_USERNAME"] = "test_user"
        os.environ["TEST_KEY"] = "test_key"
        assert conf["credentials"]["user"]["name"] == "test_user"
        assert conf["credentials"]["user"]["key"] == "test_key"

    @use_config_dir
    @use_catalog_env_variable_yml
    def test_env_resolver_not_used_for_catalog(self, tmp_path):
        """Check that the oc.env resolver is not used for catalog loading"""
        conf = OmegaConfigLoader(str(tmp_path))
        os.environ["TEST_DATASET"] = "test_dataset"
        with pytest.raises(errors.UnsupportedInterpolationType):
            conf["catalog"]["test"]["file_path"]

    @use_config_dir
    @use_credentials_env_variable_yml
    def test_env_resolver_is_cleared_after_loading(self, tmp_path):
        """Check that the ``oc.env`` resolver is cleared after loading credentials
        in the case that it was not registered beforehand."""
        conf = OmegaConfigLoader(str(tmp_path))
        os.environ["TEST_USERNAME"] = "test_user"
        os.environ["TEST_KEY"] = "test_key"
        assert conf["credentials"]["user"]["name"] == "test_user"
        assert not OmegaConf.has_resolver("oc.env")

    @use_config_dir
    @use_credentials_env_variable_yml
    def test_env_resolver_is_registered_after_loading(self, tmp_path):
        """Check that the ``oc.env`` resolver is registered after loading credentials
        in the case that it was registered beforehand"""
        conf = OmegaConfigLoader(str(tmp_path))
        OmegaConf.register_new_resolver("oc.env", oc.env)
        os.environ["TEST_USERNAME"] = "test_user"
        os.environ["TEST_KEY"] = "test_key"
        assert conf["credentials"]["user"]["name"] == "test_user"
        assert OmegaConf.has_resolver("oc.env")
        OmegaConf.clear_resolver("oc.env")

    @use_config_dir
    def test_load_config_from_tar_file(self, tmp_path):
        subprocess.run(
            [
                "tar",
                "--exclude=local/*.yml",
                "-czf",
                f"{tmp_path}/tar_conf.tar.gz",
                f"--directory={str(tmp_path.parent)}",
                f"{tmp_path.name}",
            ]
        )

        conf = OmegaConfigLoader(conf_source=f"{tmp_path}/tar_conf.tar.gz")
        catalog = conf["catalog"]
        assert catalog["trains"]["type"] == "MemoryDataset"

    @use_config_dir
    def test_load_config_from_zip_file(self, tmp_path):
        def zipdir(path, ziph):
            # This is a helper method to zip up a directory without keeping the complete directory
            # structure with all parent paths.
            # ziph is zipfile handle
            for root, _, files in os.walk(path):
                for file in files:
                    ziph.write(
                        os.path.join(root, file),
                        os.path.relpath(
                            os.path.join(root, file), os.path.join(path, "..")
                        ),
                    )

        with zipfile.ZipFile(
            f"{tmp_path}/Python.zip", "w", zipfile.ZIP_DEFLATED
        ) as zipf:
            zipdir(tmp_path, zipf)

        conf = OmegaConfigLoader(conf_source=f"{tmp_path}/Python.zip")
        catalog = conf["catalog"]
        assert catalog["trains"]["type"] == "MemoryDataset"

    @use_config_dir
    def test_variable_interpolation_with_correct_env(self, tmp_path):
        """Make sure the parameters is interpolated with the correct environment"""
        conf = OmegaConfigLoader(str(tmp_path))
        params = conf["parameters"]
        # Making sure it is not override by local/parameters_global.yml
        assert params["interpolated_param"] == "base"

    @use_config_dir
    def test_runtime_params_override_interpolated_value(self, tmp_path):
        """Make sure interpolated value is updated correctly with runtime_params"""
        conf = OmegaConfigLoader(str(tmp_path), runtime_params={"test_env": "dummy"})
        params = conf["parameters"]
        assert params["interpolated_param"] == "dummy"

    @use_config_dir
    @use_credentials_env_variable_yml
    def test_runtime_params_not_propogate_non_parameters_config(self, tmp_path):
        """Make sure `catalog`, `credentials`, `logging` or any config other than
        `parameters` are not updated by `runtime_params`."""
        # https://github.com/kedro-org/kedro/pull/2467
        key = "test_env"
        runtime_params = {key: "dummy"}
        conf = OmegaConfigLoader(
            str(tmp_path),
            config_patterns={"spark": ["spark*", "spark*/**", "**/spark*"]},
            runtime_params=runtime_params,
        )
        parameters = conf["parameters"]
        catalog = conf["catalog"]
        credentials = conf["credentials"]
        spark = conf["spark"]

        assert key in parameters
        assert key not in catalog
        assert key not in credentials
        assert key not in spark

    def test_ignore_hidden_keys(self, tmp_path):
        """Check that the config key starting with `_` are ignored and also
        don't cause a config merge error"""
        _write_yaml(tmp_path / _BASE_ENV / "catalog1.yml", {"k1": "v1", "_k2": "v2"})
        _write_yaml(tmp_path / _BASE_ENV / "catalog2.yml", {"k3": "v3", "_k2": "v4"})

        conf = OmegaConfigLoader(str(tmp_path))
        conf.default_run_env = ""
        catalog = conf["catalog"]
        assert catalog.keys() == {"k1", "k3"}

        _write_yaml(tmp_path / _BASE_ENV / "catalog3.yml", {"k1": "dup", "_k2": "v5"})
        pattern = (
            r"Duplicate keys found in "
            r"(.*catalog1\.yml and .*catalog3\.yml|.*catalog3\.yml and .*catalog1\.yml)"
            r"\: k1"
        )
        with pytest.raises(ValueError, match=pattern):
            conf["catalog"]

    def test_variable_interpolation_in_catalog_with_templates(self, tmp_path):
        base_catalog = tmp_path / _BASE_ENV / "catalog.yml"
        catalog_config = {
            "companies": {
                "type": "${_pandas.type}",
                "filepath": "data/01_raw/companies.csv",
            },
            "_pandas": {"type": "pandas.CSVDataset"},
        }
        _write_yaml(base_catalog, catalog_config)

        conf = OmegaConfigLoader(str(tmp_path))
        conf.default_run_env = ""
        assert conf["catalog"]["companies"]["type"] == "pandas.CSVDataset"

    def test_variable_interpolation_in_catalog_with_separate_templates_file(
        self, tmp_path
    ):
        base_catalog = tmp_path / _BASE_ENV / "catalog.yml"
        catalog_config = {
            "companies": {
                "type": "${_pandas.type}",
                "filepath": "data/01_raw/companies.csv",
            }
        }
        tmp_catalog = tmp_path / _BASE_ENV / "catalog_temp.yml"
        template = {"_pandas": {"type": "pandas.CSVDataset"}}
        _write_yaml(base_catalog, catalog_config)
        _write_yaml(tmp_catalog, template)

        conf = OmegaConfigLoader(str(tmp_path))
        conf.default_run_env = ""
        assert conf["catalog"]["companies"]["type"] == "pandas.CSVDataset"

    def test_custom_resolvers(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        param_config = {
            "model_options": {
                "param1": "${add: 3, 4}",
                "param2": "${plus_2: 1}",
                "param3": "${oc.env: VAR}",
            }
        }
        _write_yaml(base_params, param_config)
        custom_resolvers = {
            "add": lambda *x: sum(x),
            "plus_2": lambda x: x + 2,
            "oc.env": oc.env,
        }
        os.environ["VAR"] = "my_env_variable"
        conf = OmegaConfigLoader(tmp_path, custom_resolvers=custom_resolvers)
        conf.default_run_env = ""
        assert conf["parameters"]["model_options"]["param1"] == 7
        assert conf["parameters"]["model_options"]["param2"] == 3
        assert conf["parameters"]["model_options"]["param3"] == "my_env_variable"

    def test_globals(self, tmp_path):
        globals_params = tmp_path / _BASE_ENV / "globals.yml"
        globals_config = {
            "x": 0,
        }
        _write_yaml(globals_params, globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        # OmegaConfigLoader has globals resolver
        assert OmegaConf.has_resolver("globals")
        # Globals is readable in a dict way
        assert conf["globals"] == globals_config

    def test_globals_resolution(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_catalog = tmp_path / _BASE_ENV / "catalog.yml"
        globals_params = tmp_path / _BASE_ENV / "globals.yml"
        param_config = {
            "my_param": "${globals:x}",
            "my_param_default": "${globals:y,34}",  # y does not exist in globals
        }
        catalog_config = {
            "companies": {
                "type": "${globals:dataset_type}",
                "filepath": "data/01_raw/companies.csv",
            },
        }
        globals_config = {"x": 34, "dataset_type": "pandas.CSVDataset"}
        _write_yaml(base_params, param_config)
        _write_yaml(globals_params, globals_config)
        _write_yaml(base_catalog, catalog_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        # Globals are resolved correctly in parameter
        assert conf["parameters"]["my_param"] == globals_config["x"]
        # The default value is used if the key does not exist
        assert conf["parameters"]["my_param_default"] == 34
        # Globals are resolved correctly in catalog
        assert conf["catalog"]["companies"]["type"] == globals_config["dataset_type"]

    def test_globals_nested(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        globals_params = tmp_path / _BASE_ENV / "globals.yml"
        param_config = {
            "my_param": "${globals:x}",
            "my_nested_param": "${globals:nested.y}",
        }
        globals_config = {
            "x": 34,
            "nested": {
                "y": 42,
            },
        }
        _write_yaml(base_params, param_config)
        _write_yaml(globals_params, globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        assert conf["parameters"]["my_param"] == globals_config["x"]
        # Nested globals are accessible with dot notation
        assert conf["parameters"]["my_nested_param"] == globals_config["nested"]["y"]

    def test_globals_across_env(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        local_params = tmp_path / _DEFAULT_RUN_ENV / "parameters.yml"
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        local_globals = tmp_path / _DEFAULT_RUN_ENV / "globals.yml"
        base_param_config = {
            "param1": "${globals:y}",
        }
        local_param_config = {
            "param2": "${globals:x}",
        }
        base_globals_config = {
            "x": 34,
            "y": 25,
        }
        local_globals_config = {
            "y": 99,
        }
        _write_yaml(base_params, base_param_config)
        _write_yaml(local_params, local_param_config)
        _write_yaml(base_globals, base_globals_config)
        _write_yaml(local_globals, local_globals_config)
        conf = OmegaConfigLoader(tmp_path)
        # Local global overwrites the base global value
        assert conf["parameters"]["param1"] == local_globals_config["y"]
        # Base global value is accessible to local params
        assert conf["parameters"]["param2"] == base_globals_config["x"]

    def test_globals_default(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        base_param_config = {
            "int": "${globals:x.NOT_EXIST, 1}",
            "str": "${globals: x.NOT_EXIST, '2'}",
            "dummy": "${globals: x.DUMMY.DUMMY, '2'}",
        }
        base_globals_config = {"x": {"DUMMY": 3}}
        _write_yaml(base_params, base_param_config)
        _write_yaml(base_globals, base_globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        # Default value is being used as int
        assert conf["parameters"]["int"] == 1
        # Default value is being used as str
        assert conf["parameters"]["str"] == "2"
        # Test when x.DUMMY is not a dictionary it should still work
        assert conf["parameters"]["dummy"] == "2"

    def test_globals_default_none(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        base_param_config = {
            "zero": "${globals: x.NOT_EXIST, 0}",
            "null": "${globals: x.NOT_EXIST, null}",
            "null2": "${globals: x.y}",
        }
        base_globals_config = {
            "x": {
                "z": 23,
                "y": None,
            },
        }
        _write_yaml(base_params, base_param_config)
        _write_yaml(base_globals, base_globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        # Default value can be 0 or null
        assert conf["parameters"]["zero"] == 0
        assert conf["parameters"]["null"] is None
        # Global value is null
        assert conf["parameters"]["null2"] is None

    def test_globals_missing_default(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        globals_params = tmp_path / _BASE_ENV / "globals.yml"
        param_config = {
            "NOT_OK": "${globals:nested.NOT_EXIST}",
        }
        globals_config = {
            "nested": {
                "y": 42,
            },
        }
        _write_yaml(base_params, param_config)
        _write_yaml(globals_params, globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")

        with pytest.raises(
            InterpolationResolutionError,
            match="Globals key 'nested.NOT_EXIST' not found and no default value provided.",
        ):
            conf["parameters"]["NOT_OK"]

    def test_bad_globals_underscore(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        base_param_config = {
            "param2": "${globals:_ignore}",
        }
        base_globals_config = {
            "_ignore": 45,
        }
        _write_yaml(base_params, base_param_config)
        _write_yaml(base_globals, base_globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        with pytest.raises(
            InterpolationResolutionError,
            match=r"Keys starting with '_' are not supported for globals.",
        ):
            conf["parameters"]["param2"]

    @pytest.mark.parametrize(
        "hidden_path", ["/User/.hidden/dummy.yml", "/User/dummy/.hidden.yml"]
    )
    def test_is_hidden_config(self, tmp_path, hidden_path):
        conf = OmegaConfigLoader(str(tmp_path))
        assert conf._is_hidden(hidden_path)

    @pytest.mark.parametrize(
        "hidden_path, conf_source",
        [
            ("/User/project/conf/base/catalog.yml", "/User/project/conf"),
            ("/User/project/conf/local/catalog/data_science.yml", "/User/project/conf"),
            ("/User/project/notebooks/../conf/base/catalog", "/User/project/conf"),
            (
                "/User/.hidden/project/conf/base/catalog.yml",
                "/User/.hidden/project/conf",
            ),
        ],
    )
    def test_not_hidden_config(self, conf_source, hidden_path):
        conf = OmegaConfigLoader(str(conf_source))
        assert not conf._is_hidden(hidden_path)

    def test_ignore_ipynb_checkpoints(self, tmp_path, mocker):
        conf = OmegaConfigLoader(str(tmp_path), default_run_env=_BASE_ENV)
        base_path = tmp_path / _BASE_ENV / "parameters.yml"
        checkpoints_path = (
            tmp_path / _BASE_ENV / ".ipynb_checkpoints" / "parameters.yml"
        )

        base_config = {"param1": "dummy"}
        checkpoints_config = {"param1": "dummy"}

        _write_yaml(base_path, base_config)
        _write_yaml(checkpoints_path, checkpoints_config)

        # read successfully
        conf["parameters"]

        mocker.patch.object(conf, "_is_hidden", return_value=False)  #
        with pytest.raises(ValueError, match="Duplicate keys found in"):
            # fail because of reading the hidden files and get duplicate keys
            conf["parameters"]

    def test_runtime_params_resolution(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_catalog = tmp_path / _BASE_ENV / "catalog.yml"
        runtime_params = {
            "x": 45,
            "dataset": {
                "type": "pandas.CSVDataset",
            },
        }
        param_config = {
            "my_runtime_param": "${runtime_params:x}",
            "my_param_default": "${runtime_params:y,34}",  # y does not exist in globals
        }
        catalog_config = {
            "companies": {
                "type": "${runtime_params:dataset.type}",
                "filepath": "data/01_raw/companies.csv",
            },
        }
        _write_yaml(base_params, param_config)
        _write_yaml(base_catalog, catalog_config)
        conf = OmegaConfigLoader(
            tmp_path, default_run_env="", runtime_params=runtime_params
        )
        # runtime are resolved correctly in parameter
        assert conf["parameters"]["my_runtime_param"] == runtime_params["x"]
        # The default value is used if the key does not exist
        assert conf["parameters"]["my_param_default"] == 34
        # runtime params are resolved correctly in catalog
        assert conf["catalog"]["companies"]["type"] == runtime_params["dataset"]["type"]

    def test_runtime_params_missing_default(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        runtime_params = {
            "x": 45,
        }
        param_config = {
            "my_runtime_param": "${runtime_params:NOT_EXIST}",
        }
        _write_yaml(base_params, param_config)
        conf = OmegaConfigLoader(
            tmp_path, default_run_env="", runtime_params=runtime_params
        )
        with pytest.raises(
            InterpolationResolutionError,
            match="Runtime parameter 'NOT_EXIST' not found and no default value provided.",
        ):
            conf["parameters"]["my_runtime_param"]

    def test_runtime_params_in_globals_not_allowed(self, tmp_path):
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        local_globals = tmp_path / _DEFAULT_RUN_ENV / "globals.yml"
        runtime_params = {
            "x": 45,
        }
        base_globals_config = {
            "my_global_var": "${runtime_params:x}",
        }
        local_globals_config = {
            "my_local_var": "${runtime_params:x}",  # x does exist but shouldn't be allowed in globals
        }
        _write_yaml(base_globals, base_globals_config)
        _write_yaml(local_globals, local_globals_config)

        with pytest.raises(
            UnsupportedInterpolationType,
            match=r"The `runtime_params:` resolver is not supported for globals.",
        ):
            OmegaConfigLoader(
                tmp_path,
                base_env="",
                default_run_env="local",
                runtime_params=runtime_params,
            )
        with pytest.raises(
            UnsupportedInterpolationType,
            match=r"The `runtime_params:` resolver is not supported for globals.",
        ):
            OmegaConfigLoader(tmp_path, runtime_params=runtime_params)

    def test_runtime_params_default_global(self, tmp_path):
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        base_catalog = tmp_path / _BASE_ENV / "catalog.yml"
        runtime_params = {
            "x": 45,
        }
        globals_config = {
            "dataset": {
                "type": "pandas.CSVDataset",
            }
        }
        catalog_config = {
            "companies": {
                "type": "${runtime_params:type, ${globals:dataset.type, 'MemoryDataset'}}",
                "filepath": "data/01_raw/companies.csv",
            },
        }
        _write_yaml(base_catalog, catalog_config)
        _write_yaml(base_globals, globals_config)
        conf = OmegaConfigLoader(
            tmp_path, default_run_env="", runtime_params=runtime_params
        )
        # runtime params are resolved correctly in catalog using global default
        assert conf["catalog"]["companies"]["type"] == globals_config["dataset"]["type"]

    def test_runtime_params_default_none(self, tmp_path):
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_param_config = {
            "zero": "${runtime_params: x.NOT_EXIST, 0}",
            "null": "${runtime_params: x.NOT_EXIST, null}",
            "null2": "${runtime_params: x.y}",
        }
        runtime_params = {
            "x": {
                "z": 23,
                "y": None,
            },
        }
        _write_yaml(base_params, base_param_config)
        conf = OmegaConfigLoader(
            tmp_path, default_run_env="", runtime_params=runtime_params
        )
        # Default value can be 0 or null
        assert conf["parameters"]["zero"] == 0
        assert conf["parameters"]["null"] is None
        # runtime param value is null
        assert conf["parameters"]["null2"] is None

    def test_unsupported_interpolation_globals(self, tmp_path):
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        local_globals = tmp_path / _DEFAULT_RUN_ENV / "globals.yml"
        runtime_params = {
            "x": 45,
        }
        base_globals_config = {
            "my_global_var": "${non_existent_resolver:33}",
        }
        local_globals_config = {
            "my_local_var": "${non_existent_resolver:x}",
        }
        _write_yaml(local_globals, local_globals_config)
        _write_yaml(base_globals, base_globals_config)
        # Test that the `runtime_params` error message is not shown for cases other than
        # when `runtime_params` resolver is used in `globals`
        with pytest.raises(
            UnsupportedInterpolationType,
            match=r"Unsupported interpolation type non_existent_resolver",
        ):
            OmegaConfigLoader(tmp_path, runtime_params=runtime_params)
        with pytest.raises(
            UnsupportedInterpolationType,
            match=r"Unsupported interpolation type non_existent_resolver",
        ):
            OmegaConfigLoader(
                tmp_path,
                base_env="",
                default_run_env="local",
                runtime_params=runtime_params,
            )

    def test_override_globals(self, tmp_path):
        """When globals are bypassed, make sure that the correct overwritten values are used"""
        base_params = tmp_path / _BASE_ENV / "parameters.yml"
        base_globals = tmp_path / _BASE_ENV / "globals.yml"
        param_config = {
            "my_global": "${globals:x}",
            "my_second_global": "${globals:new_key}",
        }
        globals_config = {
            "x": 45,
        }
        _write_yaml(base_params, param_config)
        _write_yaml(base_globals, globals_config)
        conf = OmegaConfigLoader(tmp_path, default_run_env="")
        conf["globals"] = {
            "x": 89,
            "new_key": 24,
        }
        assert conf["parameters"]["my_global"] == 89
        assert conf["parameters"]["my_second_global"] == 24
