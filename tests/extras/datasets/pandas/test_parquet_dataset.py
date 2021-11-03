from pathlib import Path, PurePosixPath

import pandas as pd
import pyarrow.parquet as pq
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from pyarrow.fs import FSSpecHandler, PyFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import ParquetDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version

FILENAME = "test.parquet"


@pytest.fixture
def filepath_parquet(tmp_path):
    return (tmp_path / FILENAME).as_posix()


@pytest.fixture
def parquet_data_set(filepath_parquet, load_args, save_args, fs_args):
    return ParquetDataSet(
        filepath=filepath_parquet,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_parquet_data_set(filepath_parquet, load_version, save_version):
    return ParquetDataSet(
        filepath=filepath_parquet, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestParquetDataSet:
    def test_credentials_propagated(self, mocker):
        """Test propagating credentials for connecting to GCS"""
        mock_fs = mocker.patch("fsspec.filesystem")
        credentials = {"key": "value"}

        ParquetDataSet(filepath=FILENAME, credentials=credentials)

        mock_fs.assert_called_once_with("file", auto_mkdir=True, **credentials)

    def test_save_and_load(self, tmp_path, dummy_dataframe):
        """Test saving and reloading the data set."""
        filepath = (tmp_path / FILENAME).as_posix()
        data_set = ParquetDataSet(filepath=filepath)
        data_set.save(dummy_dataframe)
        reloaded = data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)

        files = [child.is_file() for child in tmp_path.iterdir()]
        assert all(files)
        assert len(files) == 1

    def test_save_and_load_non_existing_dir(self, tmp_path, dummy_dataframe):
        """Test saving and reloading the data set to non-existing directory."""
        filepath = (tmp_path / "non-existing" / FILENAME).as_posix()
        data_set = ParquetDataSet(filepath=filepath)
        data_set.save(dummy_dataframe)
        reloaded = data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)

    def test_exists(self, parquet_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not parquet_data_set.exists()
        parquet_data_set.save(dummy_dataframe)
        assert parquet_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, parquet_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert parquet_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, parquet_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert parquet_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "load_args,save_args",
        [
            ({"storage_options": {"a": "b"}}, {}),
            ({}, {"storage_options": {"a": "b"}}),
            ({"storage_options": {"a": "b"}}, {"storage_options": {"x": "y"}}),
        ],
    )
    def test_storage_options_dropped(self, load_args, save_args, caplog, tmp_path):
        filepath = str(tmp_path / "test.csv")

        ds = ParquetDataSet(filepath=filepath, load_args=load_args, save_args=save_args)

        records = [r for r in caplog.records if r.levelname == "WARNING"]
        expected_log_message = (
            f"Dropping `storage_options` for {filepath}, "
            f"please specify them under `fs_args` or `credentials`."
        )
        assert records[0].getMessage() == expected_log_message
        assert "storage_options" not in ds._save_args
        assert "storage_options" not in ds._load_args

    def test_load_missing_file(self, parquet_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set ParquetDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            parquet_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type,load_path",
        [
            ("s3://bucket/file.parquet", S3FileSystem, "s3://bucket/file.parquet"),
            ("file:///tmp/test.parquet", LocalFileSystem, "/tmp/test.parquet"),
            ("/tmp/test.parquet", LocalFileSystem, "/tmp/test.parquet"),
            ("gcs://bucket/file.parquet", GCSFileSystem, "gcs://bucket/file.parquet"),
            (
                "https://example.com/file.parquet",
                HTTPFileSystem,
                "https://example.com/file.parquet",
            ),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type, load_path, mocker):
        data_set = ParquetDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

        mocker.patch.object(data_set._fs, "isdir", return_value=False)
        mock_pandas_call = mocker.patch("pandas.read_parquet")
        data_set.load()
        assert mock_pandas_call.call_count == 1
        assert mock_pandas_call.call_args_list[0][0][0] == load_path

    @pytest.mark.parametrize(
        "protocol,path", [("https://", "example.com/"), ("s3://", "bucket/")]
    )
    def test_catalog_release(self, protocol, path, mocker):
        filepath = protocol + path + FILENAME
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        data_set = ParquetDataSet(filepath=filepath)
        data_set.release()
        if protocol != "https://":
            filepath = path + FILENAME
        fs_mock.invalidate_cache.assert_called_once_with(filepath)

    def test_read_partitioned_file(self, mocker, tmp_path, dummy_dataframe):
        """Test read partitioned parquet file from local directory."""
        pq_ds_mock = mocker.patch(
            "pyarrow.parquet.ParquetDataset", wraps=pq.ParquetDataset
        )
        dummy_dataframe.to_parquet(str(tmp_path), partition_cols=["col2"])
        data_set = ParquetDataSet(filepath=tmp_path.as_posix())

        reloaded = data_set.load()
        # Sort by columns because reading partitioned file results
        # in different columns order
        reloaded = reloaded.sort_index(axis=1)
        # dtype for partition column is 'category'
        assert_frame_equal(
            dummy_dataframe, reloaded, check_dtype=False, check_categorical=False
        )
        pq_ds_mock.assert_called_once()

    def test_write_to_dir(self, dummy_dataframe, tmp_path):
        data_set = ParquetDataSet(filepath=tmp_path.as_posix())
        pattern = "Saving ParquetDataSet to a directory is not supported"

        with pytest.raises(DataSetError, match=pattern):
            data_set.save(dummy_dataframe)

    def test_read_from_non_local_dir(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        fs_mock.isdir.return_value = True
        pq_ds_mock = mocker.patch("pyarrow.parquet.ParquetDataset")

        data_set = ParquetDataSet(filepath="s3://bucket/dir")

        data_set.load()
        fs_mock.isdir.assert_called_once()
        assert not fs_mock.open.called
        pq_ds_mock.assert_called_once_with("bucket/dir", filesystem=fs_mock)
        pq_ds_mock().read().to_pandas.assert_called_once_with()

    def test_read_from_file(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        fs_mock.isdir.return_value = False
        mocker.patch("pandas.read_parquet")

        data_set = ParquetDataSet(filepath="/tmp/test.parquet")

        data_set.load()
        fs_mock.isdir.assert_called_once()

    def test_arg_partition_cols(self, dummy_dataframe, tmp_path):
        data_set = ParquetDataSet(
            filepath=(tmp_path / FILENAME).as_posix(),
            save_args={"partition_cols": ["col2"]},
        )
        pattern = "does not support save argument `partition_cols`"

        with pytest.raises(DataSetError, match=pattern):
            data_set.save(dummy_dataframe)


class TestParquetDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        ds = ParquetDataSet(filepath=FILENAME)
        ds_versioned = ParquetDataSet(
            filepath=FILENAME, version=Version(load_version, save_version)
        )
        assert FILENAME in str(ds)
        assert "version" not in str(ds)

        assert FILENAME in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "ParquetDataSet" in str(ds_versioned)
        assert "ParquetDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_parquet_data_set, dummy_dataframe, mocker):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        mocker.patch(
            "pyarrow.fs._ensure_filesystem",
            return_value=PyFileSystem(FSSpecHandler(versioned_parquet_data_set._fs)),
        )
        versioned_parquet_data_set.save(dummy_dataframe)
        reloaded_df = versioned_parquet_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_parquet_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ParquetDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.load()

    def test_exists(self, versioned_parquet_data_set, dummy_dataframe, mocker):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_parquet_data_set.exists()
        mocker.patch(
            "pyarrow.fs._ensure_filesystem",
            return_value=PyFileSystem(FSSpecHandler(versioned_parquet_data_set._fs)),
        )
        versioned_parquet_data_set.save(dummy_dataframe)
        assert versioned_parquet_data_set.exists()

    def test_prevent_overwrite(
        self, versioned_parquet_data_set, dummy_dataframe, mocker
    ):
        """Check the error when attempting to override the data set if the
        corresponding parquet file for a given save version already exists."""
        mocker.patch(
            "pyarrow.fs._ensure_filesystem",
            return_value=PyFileSystem(FSSpecHandler(versioned_parquet_data_set._fs)),
        )
        versioned_parquet_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for ParquetDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self,
        versioned_parquet_data_set,
        load_version,
        save_version,
        dummy_dataframe,
        mocker,
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            fr"Save version `{save_version}` did not match load version "
            fr"`{load_version}` for ParquetDataSet\(.+\)"
        )
        mocker.patch(
            "pyarrow.fs._ensure_filesystem",
            return_value=PyFileSystem(FSSpecHandler(versioned_parquet_data_set._fs)),
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_parquet_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            ParquetDataSet(
                filepath="https://example.com/test.parquet", version=Version(None, None)
            )

    def test_versioning_existing_dataset(
        self, parquet_data_set, versioned_parquet_data_set, dummy_dataframe
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        parquet_data_set.save(dummy_dataframe)
        assert parquet_data_set.exists()
        assert parquet_data_set._filepath == versioned_parquet_data_set._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_parquet_data_set._filepath.parent.as_posix()})"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.save(dummy_dataframe)

        # Remove non-versioned dataset and try again
        Path(parquet_data_set._filepath.as_posix()).unlink()
        versioned_parquet_data_set.save(dummy_dataframe)
        assert versioned_parquet_data_set.exists()
