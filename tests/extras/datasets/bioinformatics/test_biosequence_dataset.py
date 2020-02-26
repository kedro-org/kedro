# Copyright 2020 QuantumBlack Visual Analytics Limited
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

from io import StringIO
from pathlib import PurePosixPath

import pytest
from Bio import SeqIO
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.biosequence import BioSequenceDataSet
from kedro.io import DataSetError

LOAD_ARGS = {"format": "fasta"}
SAVE_ARGS = {"format": "fasta"}


@pytest.fixture
def filepath_biosequence(tmp_path):
    return str(tmp_path / "test.fasta")


@pytest.fixture
def biosequence_data_set(filepath_biosequence):
    return BioSequenceDataSet(
        filepath=filepath_biosequence, load_args=LOAD_ARGS, save_args=SAVE_ARGS
    )


@pytest.fixture(scope="module")
def dummy_data():
    data = ">Alpha\nACCGGATGTA\n>Beta\nAGGCTCGGTTA\n"
    return list(SeqIO.parse(StringIO(data), "fasta"))


class TestBioSequenceDataSet:
    def test_save_and_load(self, biosequence_data_set, dummy_data):
        """Test saving and reloading the data set."""
        biosequence_data_set.save(dummy_data)
        reloaded = biosequence_data_set.load()
        assert dummy_data[0].id, reloaded[0].id
        assert dummy_data[0].seq, reloaded[0].seq
        assert len(dummy_data) == len(reloaded)

    def test_exists(self, biosequence_data_set, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not biosequence_data_set.exists()
        biosequence_data_set.save(dummy_data)
        assert biosequence_data_set.exists()

    def test_load_save_args_propagation(self, biosequence_data_set):
        """Test overriding the default load arguments."""
        for key, value in LOAD_ARGS.items():
            assert biosequence_data_set._load_args[key] == value

        for key, value in SAVE_ARGS.items():
            assert biosequence_data_set._save_args[key] == value

    def test_load_missing_file(self, biosequence_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set BioSequenceDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            biosequence_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.fasta", S3FileSystem),
            ("file:///tmp/test.fasta", LocalFileSystem),
            ("/tmp/test.fasta", LocalFileSystem),
            ("gcs://bucket/file.fasta", GCSFileSystem),
            ("https://example.com/file.fasta", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = BioSequenceDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        # _strip_protocol() doesn't strip http(s) protocol
        if data_set._protocol == "https":
            path = filepath.split("://")[-1]
        else:
            path = data_set._fs._strip_protocol(filepath)

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.fasta"
        data_set = BioSequenceDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)
