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
from decimal import Decimal
from json import JSONEncoder
from math import inf

import pytest

from kedro.io import DataSetError, JSONLocalDataSet
from kedro.io.core import Version


@pytest.fixture
def filepath_json(tmp_path):
    return str(tmp_path / "test.json")


@pytest.fixture
def json_data_set(filepath_json):
    return JSONLocalDataSet(filepath=filepath_json)


@pytest.fixture
def json_data_set_with_load_args(filepath_json):
    return JSONLocalDataSet(filepath=filepath_json, load_args={"parse_float": Decimal})


@pytest.fixture
def versioned_json_data_set(filepath_json, load_version, save_version):
    return JSONLocalDataSet(
        filepath=filepath_json, version=Version(load_version, save_version)
    )


@pytest.fixture(params=[[1, 2, 3]])
def json_data(request):
    return request.param


class DecimalEncoder(JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            return int(o)
        return super(DecimalEncoder, self).default(o)  # pragma: no cover


class TestJSONLocalDataSet:
    @pytest.mark.parametrize(
        "json_data",
        [42, [1, 2, 3], ["1", "2", "3"], {"foo": 1, "bar": 2}],
        indirect=True,
    )
    def test_save_and_load(self, json_data_set, json_data):
        """Test saving and reloading the data set."""
        json_data_set.save(json_data)
        reloaded = json_data_set.load()

        assert json_data == reloaded

    def test_load_missing_file(self, json_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set " r"JSONLocalDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            json_data_set.load()

    def test_exists(self, json_data_set, json_data):
        """Test `exists` method invocation."""
        assert not json_data_set.exists()

        json_data_set.save(json_data)
        assert json_data_set.exists()

    def test_load_args(self, json_data_set_with_load_args):
        """Test reloading the data set with load arguments specified."""
        json_data_set_with_load_args.save([1.1])
        assert json_data_set_with_load_args.load() == [Decimal("1.1")]

    def test_allow_nan(self, json_data_set, filepath_json):
        """Strict JSON specification does not allow out of range float values,
        however the python implementation accepts them by default. Test both
        those cases."""

        # default python
        json_data_set.save([inf])
        assert json_data_set.load() == [inf]

        # strict JSON
        json_data_set_strict = JSONLocalDataSet(
            filepath=filepath_json, save_args=dict(allow_nan=False)
        )
        pattern = "Out of range float values are not JSON compliant"
        with pytest.raises(DataSetError, match=pattern):
            json_data_set_strict.save([inf])

    @pytest.mark.parametrize(
        "json_data",
        [
            {
                "float": 1.23,
                "dec_float": Decimal("1.23"),
                "int": 123,
                "dec_int": Decimal("123"),
            }
        ],
        indirect=True,
    )
    def test_custom_encoder(self, json_data_set, filepath_json, json_data):
        """Test using a custom JSONEncoder when saving the data."""
        pattern = (
            r"Failed while saving data to data set "
            r"JSONLocalDataSet\(.+\).*\n.*Decimal.* is not "
            r"JSON serializable"
        )
        with pytest.raises(DataSetError, match=pattern):
            json_data_set.save(json_data)

        json_data_set_decimal_enc = JSONLocalDataSet(
            filepath=filepath_json, save_args=dict(cls=DecimalEncoder)
        )
        json_data_set_decimal_enc.save(json_data)
        reloaded = json_data_set_decimal_enc.load()
        assert reloaded["float"] == reloaded["dec_float"]
        assert reloaded["int"] == reloaded["dec_int"]


class TestJSONLocalDataSetVersioned:
    def test_save_and_load(self, versioned_json_data_set, json_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_json_data_set.save(json_data)
        reloaded_df = versioned_json_data_set.load()
        assert json_data == reloaded_df

    def test_no_versions(self, versioned_json_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for JSONLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.load()

    def test_exists(self, versioned_json_data_set, json_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_json_data_set.exists()

        versioned_json_data_set.save(json_data)
        assert versioned_json_data_set.exists()

    def test_prevent_overwrite(self, versioned_json_data_set, json_data):
        """Check the error when attempting to override the data set if the
        corresponding hdf file for a given save version already exists."""
        versioned_json_data_set.save(json_data)
        pattern = (
            r"Save path \`.+\` for JSONLocalDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.save(json_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_json_data_set, load_version, save_version, json_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save path `.*/{}/test\.json` did not match load path "
            r"`.*/{}/test\.json` for JSONLocalDataSet\(.+\)".format(
                save_version, load_version
            )
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_json_data_set.save(json_data)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.json"
        ds = JSONLocalDataSet(filepath=filepath)
        ds_versioned = JSONLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
