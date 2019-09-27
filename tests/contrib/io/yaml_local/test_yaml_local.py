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


import pytest

from kedro.contrib.io.yaml_local import YAMLLocalDataSet
from kedro.io import DataSetError
from kedro.io.core import Version, generate_timestamp


@pytest.fixture(params=[None])
def load_version(request):
    return request.param


@pytest.fixture(params=[None])
def save_version(request):
    return request.param or generate_timestamp()


@pytest.fixture
def filepath_yaml(tmp_path):
    return str(tmp_path / "test.yaml")


@pytest.fixture
def yaml_data_set(filepath_yaml):
    return YAMLLocalDataSet(filepath=filepath_yaml)


@pytest.fixture
def versioned_yaml_data_set(filepath_yaml, load_version, save_version):
    return YAMLLocalDataSet(
        filepath=filepath_yaml, version=Version(load_version, save_version)
    )


@pytest.fixture(params=[[1, 2, 3]])
def yaml_data(request):
    return request.param


class TestYAMLLocalDataSet:
    @pytest.mark.parametrize(
        "yaml_data", {"a_string": "Hello, World!", "a_list": [1, 2, 3]}, indirect=True
    )
    def test_save_and_load(self, yaml_data_set, yaml_data):
        """Test saving and reloading the data set."""
        yaml_data_set.save(yaml_data)
        reloaded = yaml_data_set.load()

        assert yaml_data == reloaded

    def test_load_missing_file(self, yaml_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set " r"YAMLLocalDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            yaml_data_set.load()

    def test_exists(self, yaml_data_set, yaml_data):
        """Test `exists` method invocation."""
        assert not yaml_data_set.exists()

        yaml_data_set.save(yaml_data)
        assert yaml_data_set.exists()


class TestYAMLLocalDataSetVersioned:
    def test_save_and_load(self, versioned_yaml_data_set, yaml_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_yaml_data_set.save(yaml_data)
        reloaded_df = versioned_yaml_data_set.load()
        assert yaml_data == reloaded_df

    def test_no_versions(self, versioned_yaml_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for YAMLLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_yaml_data_set.load()

    def test_exists(self, versioned_yaml_data_set, yaml_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_yaml_data_set.exists()

        versioned_yaml_data_set.save(yaml_data)
        assert versioned_yaml_data_set.exists()

    def test_prevent_overwrite(self, versioned_yaml_data_set, yaml_data):
        """Check the error when attempting to override the data set if the
        corresponding hdf file for a given save version already exists."""
        versioned_yaml_data_set.save(yaml_data)
        pattern = (
            r"Save path \`.+\` for YAMLLocalDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_yaml_data_set.save(yaml_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_yaml_data_set, load_version, save_version, yaml_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save path `.*/{}/test\.yaml` did not match load path "
            r"`.*/{}/test\.yaml` for YAMLLocalDataSet\(.+\)".format(
                save_version, load_version
            )
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_yaml_data_set.save(yaml_data)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.yaml"
        ds = YAMLLocalDataSet(filepath=filepath)
        ds_versioned = YAMLLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
