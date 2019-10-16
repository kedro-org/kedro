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

import random
from pathlib import Path

import pytest

from kedro.io import DataSetError, TextLocalDataSet
from kedro.io.core import Version


@pytest.fixture
def filepath_txt(tmp_path):
    return str(tmp_path / "test.txt")


@pytest.fixture(params=[dict()])
def txt_data_set(filepath_txt, request):
    return TextLocalDataSet(filepath=filepath_txt, **request.param)


@pytest.fixture(params=[dict()])
def txt_data_set_with_args(filepath_txt, request):
    return TextLocalDataSet(
        filepath=filepath_txt,
        load_args={"errors": "ignore"},
        save_args={"errors": "ignore"},
        **request.param
    )


@pytest.fixture
def versioned_txt_data_set(filepath_txt, load_version, save_version):
    return TextLocalDataSet(
        filepath=filepath_txt, version=Version(load_version, save_version)
    )


@pytest.fixture
def sample_text():
    random_int = random.randint(1, 10 ** 10)
    return "this file has been written with a random_number: {}".format(random_int)


def traditional_write(filepath, sample_text):
    Path(filepath).write_text(sample_text)


class TestTextLocalDataSet:
    def test_should_write_to_file(self, txt_data_set, sample_text, filepath_txt):
        txt_data_set.save(sample_text)
        assert Path(filepath_txt).read_text("utf-8") == sample_text

    def test_should_write_to_file_with_args(
        self, txt_data_set_with_args, sample_text, filepath_txt
    ):
        txt_data_set_with_args.save(sample_text)
        assert Path(filepath_txt).read_text("utf-8") == sample_text

    def test_load_missing_txt_file(self, txt_data_set):
        """Check the error raised when trying to load nonexistent txt file."""
        pattern = r"Failed while loading data from data set TextLocalDataSet"
        with pytest.raises(DataSetError, match=pattern):
            txt_data_set.load()

    def test_should_read_from_file(self, txt_data_set, sample_text, filepath_txt):
        traditional_write(filepath_txt, sample_text)
        assert sample_text == txt_data_set.load()

    def test_should_read_from_file_with_args(
        self, txt_data_set_with_args, sample_text, filepath_txt
    ):
        traditional_write(filepath_txt, sample_text)
        assert sample_text == txt_data_set_with_args.load()

    def test_assess_if_file_exists(self, txt_data_set, sample_text, filepath_txt):
        assert not txt_data_set.exists()
        traditional_write(filepath_txt, sample_text)
        assert txt_data_set.exists()

    def test_filepath_expanduser(self):
        txt_dataset = TextLocalDataSet(filepath="~")
        assert "~" not in str(txt_dataset._filepath)  # pylint: disable=protected-access


class TestTextLocalDataSetVersioned:
    def test_save_and_load(self, versioned_txt_data_set, sample_text):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_txt_data_set.save(sample_text)
        reloaded = versioned_txt_data_set.load()
        assert reloaded == sample_text

    def test_no_versions(self, versioned_txt_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for TextLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_txt_data_set.load()

    def test_exists(self, versioned_txt_data_set, sample_text):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_txt_data_set.exists()

        versioned_txt_data_set.save(sample_text)
        assert versioned_txt_data_set.exists()

    def test_prevent_override(self, versioned_txt_data_set, sample_text):
        """Check the error when attempting to override the data set if the
        corresponding xls file for a given save version already exists."""
        versioned_txt_data_set.save(sample_text)
        pattern = (
            r"Save path \`.+\` for TextLocalDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_txt_data_set.save(sample_text)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_txt_data_set, load_version, save_version, sample_text
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for TextLocalDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_txt_data_set.save(sample_text)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.txt"
        ds = TextLocalDataSet(filepath=filepath)
        ds_versioned = TextLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
