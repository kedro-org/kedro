from io import StringIO
from pathlib import PurePosixPath

import pytest
from Bio import SeqIO
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.biosequence import BioSequenceDataSet
from kedro.io import DatasetError
from kedro.io.core import PROTOCOL_DELIMITER

LOAD_ARGS = {"format": "fasta"}
SAVE_ARGS = {"format": "fasta"}


@pytest.fixture
def filepath_biosequence(tmp_path):
    return str(tmp_path / "test.fasta")


@pytest.fixture
def biosequence_dataset(filepath_biosequence, fs_args):
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
    def test_save_and_load(self, biosequence_dataset, dummy_data):
        """Test saving and reloading the data set."""
        biosequence_dataset.save(dummy_data)
        reloaded = biosequence_dataset.load()
        assert dummy_data[0].id, reloaded[0].id
        assert dummy_data[0].seq, reloaded[0].seq
        assert len(dummy_data) == len(reloaded)
        assert biosequence_dataset._fs_open_args_load == {"mode": "r"}
        assert biosequence_dataset._fs_open_args_save == {"mode": "w"}

    def test_exists(self, biosequence_dataset, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not biosequence_dataset.exists()
        biosequence_dataset.save(dummy_data)
        assert biosequence_dataset.exists()

    def test_load_save_args_propagation(self, biosequence_dataset):
        """Test overriding the default load arguments."""
        for key, value in LOAD_ARGS.items():
            assert biosequence_dataset._load_args[key] == value

        for key, value in SAVE_ARGS.items():
            assert biosequence_dataset._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, biosequence_dataset, fs_args):
        assert biosequence_dataset._fs_open_args_load == fs_args["open_args_load"]
        assert biosequence_dataset._fs_open_args_save == {
            "mode": "w"
        }  # default unchanged

    def test_load_missing_file(self, biosequence_dataset):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set BioSequenceDataSet\(.*\)"
        with pytest.raises(DatasetError, match=pattern):
            biosequence_dataset.load()

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
        dataset = BioSequenceDataSet(filepath=filepath)
        assert isinstance(dataset._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(dataset._filepath) == path
        assert isinstance(dataset._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.fasta"
        dataset = BioSequenceDataSet(filepath=filepath)
        dataset.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)
