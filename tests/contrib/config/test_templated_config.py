# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from typing import Dict

import pytest
import yaml

from kedro.contrib.config import TemplatedConfigLoader


def _write_yaml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


@pytest.fixture
def conf_paths(tmp_path):
    return [str(tmp_path / "base"), str(tmp_path / "local")]


@pytest.fixture
def param_config():
    return {
        "boats": {
            "type": "${boat_data_type}",
            "filepath": "${s3_bucket}/${raw_data_folder}/${boat_file_name}",
            "columns": {
                "id": "${string_type}",
                "name": "${string_type}",
                "top_speed": "${float_type}",
            },
            "rows": 5,
            "users": ["fred", "${write_only_user}"],
        }
    }


@pytest.fixture
def template_config():
    return {
        "s3_bucket": "s3a://boat-and-car-bucket",
        "raw_data_folder": "01_raw",
        "boat_file_name": "boats.csv",
        "boat_data_type": "SparkDataSet",
        "string_type": "VARCHAR",
        "float_type": "FLOAT",
        "write_only_user": "ron",
    }


@pytest.fixture
def proj_catalog_param(tmp_path, param_config):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config)


@pytest.fixture
def proj_catalog_globals(tmp_path, template_config):
    global_yml = tmp_path / "base" / "globals.yml"
    _write_yaml(global_yml, template_config)


@pytest.fixture
def normal_config_advanced():
    return {
        "planes": {
            "type": "SparkJDBCDataSet",
            "postgres_credentials": {"user": "Fakeuser", "password": "F@keP@55word"},
            "batch_size": 10000,
            "need_permission": True,
            "secret_tables": ["models", "pilots", "engines"],
        }
    }


@pytest.fixture
def proj_catalog_advanced(tmp_path, normal_config_advanced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, normal_config_advanced)


@pytest.fixture
def param_config_advanced():
    return {
        "planes": {
            "type": "${plane_data_type}",
            "postgres_credentials": "${credentials}",
            "batch_size": "${batch_size}",
            "need_permission": "${permission_param}",
            "secret_tables": "${secret_table_list}",
        }
    }


@pytest.fixture
def template_config_advanced():
    return {
        "plane_data_type": "SparkJDBCDataSet",
        "credentials": {"user": "Fakeuser", "password": "F@keP@55word"},
        "batch_size": 10000,
        "permission_param": True,
        "secret_table_list": ["models", "pilots", "engines"],
    }


@pytest.fixture
def proj_catalog_param_w_vals_advanced(tmp_path, param_config_advanced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_advanced)


@pytest.fixture
def param_config_mixed():
    return {
        "boats": {
            "type": "${boat_data_type}",
            "filepath": "${s3_bucket}/${raw_data_folder}/${boat_file_name}",
            "columns": {
                "id": "${string_type}",
                "name": "${string_type}",
                "top_speed": "${float_type}",
            },
            "users": ["fred", "${USER}"],
        }
    }


@pytest.fixture
def get_environ():
    return {"USER": "ron"}


@pytest.fixture
def proj_catalog_param_mixed(tmp_path, param_config_mixed):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_mixed)


@pytest.fixture
def param_config_namespaced():
    return {
        "boats": {
            "type": "${global.boat_data_type}",
            "filepath": "${global.s3_bucket}/${global.raw_data_folder}/${global.boat_file_name}",
            "columns": {
                "id": "${global.string_type}",
                "name": "${global.string_type}",
                "top_speed": "${global.float_type}",
            },
            "users": ["fred", "${env.USER}"],
        }
    }


@pytest.fixture
def proj_catalog_param_namespaced(tmp_path, param_config_namespaced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_namespaced)


@pytest.fixture
def param_config_exceptional():
    return {"postcode": "${area}${district} ${sector}${unit}"}


@pytest.fixture
def template_config_exceptional():
    return {"area": "NW", "district": 10, "sector": 2, "unit": "JK"}


@pytest.fixture
def proj_catalog_param_w_vals_exceptional(tmp_path, param_config_exceptional):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_exceptional)


class TestTemplatedConfigLoader:
    @pytest.mark.usefixtures("proj_catalog_param")
    def test_catlog_parameterized_w_dict(self, tmp_path, conf_paths, template_config):
        """Test parameterized config with input from dictionary with values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths, globals_dict=template_config).get(
            "catalog*.yml"
        )

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param", "proj_catalog_globals")
    def test_catlog_parameterized_w_globals(self, tmp_path, conf_paths):
        """Test parameterized config with globals yaml file"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths, globals_pattern="*globals.yml").get(
            "catalog*.yml"
        )

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param")
    def test_catlog_parameterized_no_params(self, tmp_path, conf_paths):
        """Test parameterized config without input"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths).get("catalog*.yml")

        assert catalog["boats"]["type"] == "${boat_data_type}"
        assert (
            catalog["boats"]["filepath"]
            == "${s3_bucket}/${raw_data_folder}/${boat_file_name}"
        )
        assert catalog["boats"]["columns"]["id"] == "${string_type}"
        assert catalog["boats"]["columns"]["name"] == "${string_type}"
        assert catalog["boats"]["columns"]["top_speed"] == "${float_type}"
        assert catalog["boats"]["users"] == ["fred", "${write_only_user}"]

    @pytest.mark.usefixtures("proj_catalog_advanced")
    def test_catlog_advanced(self, tmp_path, conf_paths, normal_config_advanced):
        """Test whether it responds well to advanced yaml values
        (i.e. nested dicts, booleans, lists, etc.)"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict=normal_config_advanced
        ).get("catalog*.yml")

        assert catalog["planes"]["type"] == "SparkJDBCDataSet"
        assert catalog["planes"]["postgres_credentials"]["user"] == "Fakeuser"
        assert catalog["planes"]["postgres_credentials"]["password"] == "F@keP@55word"
        assert catalog["planes"]["batch_size"] == 10000
        assert catalog["planes"]["need_permission"]
        assert catalog["planes"]["secret_tables"] == ["models", "pilots", "engines"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals_advanced")
    def test_catlog_parameterized_advanced(
        self, tmp_path, conf_paths, template_config_advanced
    ):
        """Test advanced templating (i.e. nested dicts, booleans, lists, etc.)"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict=template_config_advanced
        ).get("catalog*.yml")

        assert catalog["planes"]["type"] == "SparkJDBCDataSet"
        assert catalog["planes"]["postgres_credentials"]["user"] == "Fakeuser"
        assert catalog["planes"]["postgres_credentials"]["password"] == "F@keP@55word"
        assert catalog["planes"]["batch_size"] == 10000
        assert catalog["planes"]["need_permission"]
        assert catalog["planes"]["secret_tables"] == ["models", "pilots", "engines"]

    @pytest.mark.usefixtures("proj_catalog_param_mixed", "proj_catalog_globals")
    def test_catlog_parameterized_w_dict_mixed(self, tmp_path, conf_paths, get_environ):
        """Test parameterized config with input from dictionary with values
        and globals.yml"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_pattern="*globals.yml", globals_dict=get_environ
        ).get("catalog*.yml")

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_namespaced")
    def test_catlog_parameterized_w_dict_namespaced(
        self, tmp_path, conf_paths, template_config, get_environ
    ):
        """Test parameterized config with namespacing in the template values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict={"global": template_config, "env": get_environ}
        ).get("catalog*.yml")

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals_exceptional")
    def test_catlog_parameterized_exceptional(
        self, tmp_path, conf_paths, template_config_exceptional
    ):
        """Test templating with mixed type replacement values going into one string"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict=template_config_exceptional
        ).get("catalog*.yml")

        assert catalog["postcode"] == "NW10 2JK"
