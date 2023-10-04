from pathlib import Path, PurePosixPath

import numpy as np
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.svmlight import SVMLightDataSet
from kedro.io import DatasetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_svm(tmp_path):
    return (tmp_path / "test.svm").as_posix()


@pytest.fixture
def svm_dataset(filepath_svm, save_args, load_args, fs_args):
    return SVMLightDataSet(
        filepath=filepath_svm, save_args=save_args, load_args=load_args, fs_args=fs_args
    )


@pytest.fixture
def versioned_svm_dataset(filepath_svm, load_version, save_version):
    return SVMLightDataSet(
        filepath=filepath_svm, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_data():
    features = np.array([[1, 2, 10], [1, 0.4, 3.2], [0, 0, 0]])
    label = np.array([1, 0, 3])
    return features, label


class TestSVMLightDataSet:
    def test_save_and_load(self, svm_dataset, dummy_data):
        """Test saving and reloading the data set."""
        svm_dataset.save(dummy_data)
        reloaded_features, reloaded_label = svm_dataset.load()
        original_features, original_label = dummy_data
        assert (original_features == reloaded_features).all()
        assert (original_label == reloaded_label).all()
        assert svm_dataset._fs_open_args_load == {"mode": "rb"}
        assert svm_dataset._fs_open_args_save == {"mode": "wb"}

    def test_exists(self, svm_dataset, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not svm_dataset.exists()
        svm_dataset.save(dummy_data)
        assert svm_dataset.exists()

    @pytest.mark.parametrize(
        "save_args", [{"zero_based": False, "comment": "comment"}], indirect=True
    )
    def test_save_extra_save_args(self, svm_dataset, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert svm_dataset._save_args[key] == value

    @pytest.mark.parametrize(
        "load_args", [{"zero_based": False, "n_features": 3}], indirect=True
    )
    def test_save_extra_load_args(self, svm_dataset, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert svm_dataset._load_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, svm_dataset, fs_args):
        assert svm_dataset._fs_open_args_load == fs_args["open_args_load"]
        assert svm_dataset._fs_open_args_save == {"mode": "wb"}  # default unchanged

    def test_load_missing_file(self, svm_dataset):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set SVMLightDataSet\(.*\)"
        with pytest.raises(DatasetError, match=pattern):
            svm_dataset.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.svm", S3FileSystem),
            ("file:///tmp/test.svm", LocalFileSystem),
            ("/tmp/test.svm", LocalFileSystem),
            ("gcs://bucket/file.svm", GCSFileSystem),
            ("https://example.com/file.svm", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        dataset = SVMLightDataSet(filepath=filepath)
        assert isinstance(dataset._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(dataset._filepath) == path
        assert isinstance(dataset._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.svm"
        dataset = SVMLightDataSet(filepath=filepath)
        dataset.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestSVMLightDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.svm"
        ds = SVMLightDataSet(filepath=filepath)
        ds_versioned = SVMLightDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "SVMLightDataSet" in str(ds_versioned)
        assert "SVMLightDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_svm_dataset, dummy_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_svm_dataset.save(dummy_data)
        reloaded_features, reloaded_label = versioned_svm_dataset.load()
        original_features, original_label = dummy_data
        assert (original_features == reloaded_features).all()
        assert (original_label == reloaded_label).all()

    def test_no_versions(self, versioned_svm_dataset):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for SVMLightDataSet\(.+\)"
        with pytest.raises(DatasetError, match=pattern):
            versioned_svm_dataset.load()

    def test_exists(self, versioned_svm_dataset, dummy_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_svm_dataset.exists()
        versioned_svm_dataset.save(dummy_data)
        assert versioned_svm_dataset.exists()

    def test_prevent_overwrite(self, versioned_svm_dataset, dummy_data):
        """Check the error when attempting to override the data set if the
        corresponding json file for a given save version already exists."""
        versioned_svm_dataset.save(dummy_data)
        pattern = (
            r"Save path \'.+\' for SVMLightDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DatasetError, match=pattern):
            versioned_svm_dataset.save(dummy_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_svm_dataset, load_version, save_version, dummy_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            f"Save version '{save_version}' did not match "
            f"load version '{load_version}' for "
            r"SVMLightDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_svm_dataset.save(dummy_data)

    def test_http_filesystem_no_versioning(self):
        pattern = "Versioning is not supported for HTTP protocols."

        with pytest.raises(DatasetError, match=pattern):
            SVMLightDataSet(
                filepath="https://example.com/file.svm", version=Version(None, None)
            )

    def test_versioning_existing_dataset(
        self, svm_dataset, versioned_svm_dataset, dummy_data
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        svm_dataset.save(dummy_data)
        assert svm_dataset.exists()
        assert svm_dataset._filepath == versioned_svm_dataset._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_svm_dataset._filepath.parent.as_posix()})"
        )
        with pytest.raises(DatasetError, match=pattern):
            versioned_svm_dataset.save(dummy_data)

        # Remove non-versioned dataset and try again
        Path(svm_dataset._filepath.as_posix()).unlink()
        versioned_svm_dataset.save(dummy_data)
        assert versioned_svm_dataset.exists()
