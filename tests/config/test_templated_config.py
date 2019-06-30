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
def template_config_folders():
    return {
        "s3_bucket": "s3a://boat-and-car-bucket",
        "raw_data_folder": "01_raw",
    }


@pytest.fixture
def template_config_folders_clash():
    return {
        "s3_bucket": "s3a://boat-and-car-bucket-2",
        "raw_data_folder": "02_int",
    }


@pytest.fixture
def template_config_general():
    return {
        "boat_data_type": "SparkDataSet",
        "string_type": "VARCHAR",
        "float_type": "FLOAT",
        "write_only_user": "ron"
    }


@pytest.fixture
def template_config(template_config_folders, template_config_general):
    return {**template_config_folders, **template_config_general}


@pytest.fixture
def proj_catalog_param(tmp_path, param_config):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config)


@pytest.fixture
def proj_catalog_param_w_vals(tmp_path, param_config, template_config):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    values_catalog = tmp_path / "base" / "values.yml"
    _write_yaml(proj_catalog, param_config)
    _write_yaml(values_catalog, template_config)


@pytest.fixture
def proj_catalog_param_w_vals_and_dict(tmp_path, param_config, template_config_general):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    values_catalog = tmp_path / "base" / "values.yml"
    _write_yaml(proj_catalog, param_config)
    _write_yaml(values_catalog, template_config_general)


class TestTemplatedConfigLoader:

    @pytest.mark.usefixtures("proj_catalog_param_w_vals")
    def test_catlog_parameterized_separate(self, tmp_path, conf_paths):
        """Test parameterized config with input from values.yml file inside conf_paths"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths).resolve("catalog*.yml")

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param", "template_config")
    def test_catlog_parameterized_w_dict(self, tmp_path, conf_paths, template_config):
        """Test parameterized config with input from dictionary with values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths) \
            .resolve(["catalog*.yml"], template_config, search_for_values=False)

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals_and_dict", "template_config_folders")
    def test_catlog_parameterized_w_dict_and_vals(self, tmp_path, conf_paths,
                                                  template_config_folders):
        """Test parameterized config with input from values.yml file inside conf_paths and input
        from dictionary with values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths) \
            .resolve(["catalog*.yml"], template_config_folders)

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals", "template_config_folders_clash")
    def test_catlog_parameterized_w_clash(self, tmp_path, conf_paths,
                                          template_config_folders_clash):
        """Test that dictionary config takes precedence over loaded config"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths) \
            .resolve(["catalog*.yml"], template_config_folders_clash)

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket-2/02_int/boats.csv"
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]
