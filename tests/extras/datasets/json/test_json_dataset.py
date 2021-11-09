from pathlib import Path, PurePosixPath

import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.json import JSONDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_json(tmp_path):
    return (tmp_path / "test.json").as_posix()


@pytest.fixture
def json_data_set(filepath_json, save_args, fs_args):
    return JSONDataSet(filepath=filepath_json, save_args=save_args, fs_args=fs_args)


@pytest.fixture
def versioned_json_data_set(filepath_json, load_version, save_version):
    return JSONDataSet(
        filepath=filepath_json, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_data():
    return {"col1": 1, "col2": 2, "col3": 3}


class TestJSONDataSet:
    def test_save_and_load(self, json_data_set, dummy_data):
        """Test saving and reloading the data set."""
        json_data_set.save(dummy_data)
        reloaded = json_data_set.load()
        assert dummy_data == reloaded
        assert json_data_set._fs_open_args_load == {}
        assert json_data_set._fs_open_args_save == {"mode": "w"}

    def test_exists(self, json_data_set, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not json_data_set.exists()
        json_data_set.save(dummy_data)
        assert json_data_set.exists()

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, json_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert json_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, json_data_set, fs_args):
        assert json_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert json_data_set._fs_open_args_save == {"mode": "w"}  # default unchanged

    def test_load_missing_file(self, json_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set JSONDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            json_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.json", S3FileSystem),
            ("file:///tmp/test.json", LocalFileSystem),
            ("/tmp/test.json", LocalFileSystem),
            ("gcs://bucket/file.json", GCSFileSystem),
            ("https://example.com/file.json", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = JSONDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.json"
        data_set = JSONDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestJSONDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.json"
        ds = JSONDataSet(filepath=filepath)
        ds_versioned = JSONDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "JSONDataSet" in str(ds_versioned)
        assert "JSONDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
        # Default save_args
        assert "save_args={'indent': 2}" in str(ds)
        assert "save_args={'indent': 2}" in str(ds_versioned)

    def test_save_and_load(self, versioned_json_data_set, dummy_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_json_data_set.save(dummy_data)
        reloaded = versioned_json_data_set.load()
        assert dummy_data == reloaded

    def test_no_versions(self, versioned_json_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for JSONDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.load()

    def test_exists(self, versioned_json_data_set, dummy_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_json_data_set.exists()
        versioned_json_data_set.save(dummy_data)
        assert versioned_json_data_set.exists()

    def test_prevent_overwrite(self, versioned_json_data_set, dummy_data):
        """Check the error when attempting to override the data set if the
        corresponding json file for a given save version already exists."""
        versioned_json_data_set.save(dummy_data)
        pattern = (
            r"Save path \`.+\` for JSONDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.save(dummy_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_json_data_set, load_version, save_version, dummy_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            f"Save version `{save_version}` did not match "
            f"load version `{load_version}` for "
            r"JSONDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_json_data_set.save(dummy_data)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            JSONDataSet(
                filepath="https://example.com/file.json", version=Version(None, None)
            )

    def test_versioning_existing_dataset(
        self, json_data_set, versioned_json_data_set, dummy_data
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        json_data_set.save(dummy_data)
        assert json_data_set.exists()
        assert json_data_set._filepath == versioned_json_data_set._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_json_data_set._filepath.parent.as_posix()})"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.save(dummy_data)

        # Remove non-versioned dataset and try again
        Path(json_data_set._filepath.as_posix()).unlink()
        versioned_json_data_set.save(dummy_data)
        assert versioned_json_data_set.exists()
