from pathlib import PurePosixPath

import plotly.express as px
import pytest
from adlfs import AzureBlobFileSystem
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.plotly import JSONDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER


@pytest.fixture
def filepath_json(tmp_path):
    return (tmp_path / "test.json").as_posix()


@pytest.fixture
def json_data_set(filepath_json, load_args, save_args, fs_args):
    return JSONDataSet(
        filepath=filepath_json,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def dummy_plot():
    return px.scatter(x=[1, 2, 3], y=[1, 3, 2], title="Test")


class TestJSONDataSet:
    def test_save_and_load(self, json_data_set, dummy_plot):
        """Test saving and reloading the data set."""
        json_data_set.save(dummy_plot)
        reloaded = json_data_set.load()
        assert dummy_plot == reloaded
        assert json_data_set._fs_open_args_load == {}
        assert json_data_set._fs_open_args_save == {"mode": "w"}

    def test_exists(self, json_data_set, dummy_plot):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not json_data_set.exists()
        json_data_set.save(dummy_plot)
        assert json_data_set.exists()

    def test_load_missing_file(self, json_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set JSONDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            json_data_set.load()

    @pytest.mark.parametrize("save_args", [{"pretty": True}])
    def test_save_extra_params(self, json_data_set, save_args):
        """Test overriding default save args"""
        for k, v in save_args.items():
            assert json_data_set._save_args[k] == v

    @pytest.mark.parametrize(
        "load_args", [{"output_type": "FigureWidget", "skip_invalid": True}]
    )
    def test_load_extra_params(self, json_data_set, load_args):
        """Test overriding default save args"""
        for k, v in load_args.items():
            assert json_data_set._load_args[k] == v

    @pytest.mark.parametrize(
        "filepath,instance_type,credentials",
        [
            ("s3://bucket/file.json", S3FileSystem, {}),
            ("file:///tmp/test.json", LocalFileSystem, {}),
            ("/tmp/test.json", LocalFileSystem, {}),
            ("gcs://bucket/file.json", GCSFileSystem, {}),
            ("https://example.com/file.json", HTTPFileSystem, {}),
            (
                "abfs://bucket/file.csv",
                AzureBlobFileSystem,
                {"account_name": "test", "account_key": "test"},
            ),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type, credentials):
        data_set = JSONDataSet(filepath=filepath, credentials=credentials)
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
