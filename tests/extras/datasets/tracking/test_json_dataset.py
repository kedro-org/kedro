import json
from pathlib import Path, PurePosixPath

import pytest
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.tracking import JSONDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_json(tmp_path):
    return (tmp_path / "test.json").as_posix()


@pytest.fixture
def json_dataset(filepath_json, save_args, fs_args):
    return JSONDataSet(filepath=filepath_json, save_args=save_args, fs_args=fs_args)


@pytest.fixture
def explicit_versioned_json_dataset(filepath_json, load_version, save_version):
    return JSONDataSet(
        filepath=filepath_json, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_data():
    return {"col1": 1, "col2": 2, "col3": "mystring"}


class TestJSONDataSet:
    def test_save(self, filepath_json, dummy_data, tmp_path, save_version):
        """Test saving and reloading the data set."""
        json_dataset = JSONDataSet(
            filepath=filepath_json, version=Version(None, save_version)
        )
        json_dataset.save(dummy_data)

        actual_filepath = Path(json_dataset._filepath.as_posix())
        test_filepath = tmp_path / "locally_saved.json"

        test_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(test_filepath, "w", encoding="utf-8") as file:
            json.dump(dummy_data, file)

        with open(test_filepath, encoding="utf-8") as file:
            test_data = json.load(file)

        with open(
            (actual_filepath / save_version / "test.json"), encoding="utf-8"
        ) as actual_file:
            actual_data = json.load(actual_file)

        assert actual_data == test_data
        assert json_dataset._fs_open_args_load == {}
        assert json_dataset._fs_open_args_save == {"mode": "w"}

    def test_load_fail(self, json_dataset, dummy_data):
        json_dataset.save(dummy_data)
        pattern = r"Loading not supported for `JSONDataSet`"
        with pytest.raises(DataSetError, match=pattern):
            json_dataset.load()

    def test_exists(self, json_dataset, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not json_dataset.exists()
        json_dataset.save(dummy_data)
        assert json_dataset.exists()

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, json_dataset, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert json_dataset._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, json_dataset, fs_args):
        assert json_dataset._fs_open_args_load == fs_args["open_args_load"]
        assert json_dataset._fs_open_args_save == {"mode": "w"}  # default unchanged

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.json", S3FileSystem),
            ("file:///tmp/test.json", LocalFileSystem),
            ("/tmp/test.json", LocalFileSystem),
            ("gcs://bucket/file.json", GCSFileSystem),
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

    def test_not_version_str_repr(self):
        """Test that version is not in string representation of the class instance."""
        filepath = "test.json"
        ds = JSONDataSet(filepath=filepath)

        assert filepath in str(ds)
        assert "version" not in str(ds)
        assert "JSONDataSet" in str(ds)
        assert "protocol" in str(ds)
        # Default save_args
        assert "save_args={'indent': 2}" in str(ds)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance."""
        filepath = "test.json"
        ds_versioned = JSONDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "JSONDataSet" in str(ds_versioned)
        assert "protocol" in str(ds_versioned)
        # Default save_args
        assert "save_args={'indent': 2}" in str(ds_versioned)

    def test_prevent_overwrite(self, explicit_versioned_json_dataset, dummy_data):
        """Check the error when attempting to override the data set if the
        corresponding json file for a given save version already exists."""
        explicit_versioned_json_dataset.save(dummy_data)
        pattern = (
            r"Save path \`.+\` for JSONDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            explicit_versioned_json_dataset.save(dummy_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self,
        explicit_versioned_json_dataset,
        load_version,
        save_version,
        dummy_data,
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            f"Save version `{save_version}` did not match "
            f"load version `{load_version}` for "
            r"JSONDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            explicit_versioned_json_dataset.save(dummy_data)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            JSONDataSet(
                filepath="https://example.com/file.json", version=Version(None, None)
            )
