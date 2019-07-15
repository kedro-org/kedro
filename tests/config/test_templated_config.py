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

from kedro.config import TemplatedConfigLoader


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
            "filepath": "${s3_bucket}/${raw_data_folder}/boats.csv",
            "columns": {"id": "${string_type}",
                        "name": "${string_type}",
                        "top_speed": "${float_type}"},
            "users": ["fred",
                      "${write_only_user}"]
        }
    }


@pytest.fixture
def template_config():
    return {
        "s3_bucket": "s3a://boat-and-car-bucket",
        "raw_data_folder": "01_raw",
        "boat_data_type": "SparkDataSet",
        "string_type": "VARCHAR",
        "float_type": "FLOAT",
        "write_only_user": "ron"
    }


@pytest.fixture
def proj_catalog_param(tmp_path, param_config):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config)


@pytest.fixture
def param_config_advanced():
    return {
        "planes": {
            "type": "${plane_data_type}",
            "postgres_credentials": "${credentials}",
            "batch_size": "${batch_size}",
            "need_permission": "${permission_param}",
            "secret_tables": "${secret_table_list}"
        }
    }


@pytest.fixture
def template_config_advanced():
    return {
        "plane_data_type": "SparkJDBCDataSet",
        "credentials": {
            "user": "Fakeuser",
            "password": "F@keP@55word"
        },
        "batch_size": 10000,
        "permission_param": True,
        "secret_table_list": ["models", "pilots", "engines"]
    }


@pytest.fixture
def proj_catalog_param_w_vals_advanced(tmp_path, param_config_advanced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_advanced)


class TestTemplatedConfigLoader:

    @pytest.mark.usefixtures("proj_catalog_param", "template_config")
    def test_catlog_parameterized_w_dict(self, tmp_path, conf_paths, template_config):
        """Test parameterized config with input from dictionary with values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths).resolve(["catalog*.yml"], template_config)

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals_advanced", "template_config_advanced")
    def test_catlog_parameterized_advanced(self, tmp_path, conf_paths, template_config_advanced):
        """Test advanced (i.e. nested dicts, booleans, lists, etc.)"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths).resolve("catalog*.yml",
                                                            template_config_advanced)

        assert catalog["planes"]["type"] == "SparkJDBCDataSet"
        assert catalog["planes"]["postgres_credentials"]["user"] == "Fakeuser"
        assert catalog["planes"]["postgres_credentials"]["password"] == "F@keP@55word"
        assert catalog["planes"]["batch_size"] == 10000
        assert catalog["planes"]["need_permission"]
        assert catalog["planes"]["secret_tables"] == ["models", "pilots", "engines"]
