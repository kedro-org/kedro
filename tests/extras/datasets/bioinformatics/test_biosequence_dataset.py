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
from kedro.io.core import PROTOCOL_DELIMITER

LOAD_ARGS = {"format": "fasta"}
SAVE_ARGS = {"format": "fasta"}


@pytest.fixture
def filepath_biosequence(tmp_path):
    return str(tmp_path / "test.fasta")


@pytest.fixture
def biosequence_data_set(filepath_biosequence, fs_args):
    return BioSequenceDataSet(
        filepath=filepath_biosequence,
        load_args=LOAD_ARGS,
        save_args=SAVE_ARGS,
        fs_args=fs_args,
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
        assert biosequence_data_set._fs_open_args_load == {"mode": "r"}
        assert biosequence_data_set._fs_open_args_save == {"mode": "w"}

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

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, biosequence_data_set, fs_args):
        assert biosequence_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert biosequence_data_set._fs_open_args_save == {
            "mode": "w"
        }  # default unchanged

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

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.fasta"
        data_set = BioSequenceDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)
