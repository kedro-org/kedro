from pathlib import Path, PurePosixPath

import pandas as pd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import ExcelDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_excel(tmp_path):
    return (tmp_path / "test.xlsx").as_posix()


@pytest.fixture
def excel_data_set(filepath_excel, load_args, save_args, fs_args):
    return ExcelDataSet(
        filepath=filepath_excel,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def excel_multisheet_data_set(filepath_excel, save_args, fs_args):
    load_args = {"sheet_name": None}
    return ExcelDataSet(
        filepath=filepath_excel,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_excel_data_set(filepath_excel, load_version, save_version):
    return ExcelDataSet(
        filepath=filepath_excel, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def another_dummy_dataframe():
    return pd.DataFrame({"x": [10, 20], "y": ["hello", "world"]})


class TestExcelDataSet:
    def test_save_and_load(self, excel_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        excel_data_set.save(dummy_dataframe)
        reloaded = excel_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)

    def test_save_and_load_multiple_sheets(
        self, excel_multisheet_data_set, dummy_dataframe, another_dummy_dataframe
    ):
        """Test saving and reloading the data set with multiple sheets."""
        dummy_multisheet = {
            "sheet 1": dummy_dataframe,
            "sheet 2": another_dummy_dataframe,
        }
        excel_multisheet_data_set.save(dummy_multisheet)
        reloaded = excel_multisheet_data_set.load()
        assert_frame_equal(dummy_multisheet["sheet 1"], reloaded["sheet 1"])
        assert_frame_equal(dummy_multisheet["sheet 2"], reloaded["sheet 2"])

    def test_exists(self, excel_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not excel_data_set.exists()
        excel_data_set.save(dummy_dataframe)
        assert excel_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, excel_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert excel_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, excel_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert excel_data_set._save_args[key] == value

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

        ds = ExcelDataSet(filepath=filepath, load_args=load_args, save_args=save_args)

        records = [r for r in caplog.records if r.levelname == "WARNING"]
        expected_log_message = (
            f"Dropping `storage_options` for {filepath}, "
            f"please specify them under `fs_args` or `credentials`."
        )
        assert records[0].getMessage() == expected_log_message
        assert "storage_options" not in ds._save_args
        assert "storage_options" not in ds._load_args

    def test_load_missing_file(self, excel_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set ExcelDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            excel_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type,load_path",
        [
            ("s3://bucket/file.xlsx", S3FileSystem, "s3://bucket/file.xlsx"),
            ("file:///tmp/test.xlsx", LocalFileSystem, "/tmp/test.xlsx"),
            ("/tmp/test.xlsx", LocalFileSystem, "/tmp/test.xlsx"),
            ("gcs://bucket/file.xlsx", GCSFileSystem, "gcs://bucket/file.xlsx"),
            (
                "https://example.com/file.xlsx",
                HTTPFileSystem,
                "https://example.com/file.xlsx",
            ),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type, load_path, mocker):
        data_set = ExcelDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

        mock_pandas_call = mocker.patch("pandas.read_excel")
        data_set.load()
        assert mock_pandas_call.call_count == 1
        assert mock_pandas_call.call_args_list[0][0][0] == load_path

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.xlsx"
        data_set = ExcelDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestExcelDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.xlsx"
        ds = ExcelDataSet(filepath=filepath)
        ds_versioned = ExcelDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "ExcelDataSet" in str(ds_versioned)
        assert "ExcelDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
        assert "writer_args" in str(ds_versioned)
        assert "writer_args" in str(ds)
        # Default save_args and load_args
        assert "save_args={'index': False}" in str(ds)
        assert "save_args={'index': False}" in str(ds_versioned)
        assert "load_args={'engine': openpyxl}" in str(ds_versioned)
        assert "load_args={'engine': openpyxl}" in str(ds)

    def test_save_and_load(self, versioned_excel_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_excel_data_set.save(dummy_dataframe)
        reloaded_df = versioned_excel_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_excel_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ExcelDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_excel_data_set.load()

    def test_versioning_not_supported_in_append_mode(
        self, tmp_path, load_version, save_version
    ):
        filepath = str(tmp_path / "test.xlsx")
        save_args = {"writer": {"mode": "a"}}

        pattern = "`ExcelDataSet` doesn't support versioning in append mode."
        with pytest.raises(DataSetError, match=pattern):
            ExcelDataSet(
                filepath=filepath,
                version=Version(load_version, save_version),
                save_args=save_args,
            )

    def test_exists(self, versioned_excel_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_excel_data_set.exists()
        versioned_excel_data_set.save(dummy_dataframe)
        assert versioned_excel_data_set.exists()

    def test_prevent_overwrite(self, versioned_excel_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding Excel file for a given save version already exists."""
        versioned_excel_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for ExcelDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_excel_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_excel_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            fr"Save version `{save_version}` did not match load version "
            fr"`{load_version}` for ExcelDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_excel_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            ExcelDataSet(
                filepath="https://example.com/file.xlsx", version=Version(None, None)
            )

    def test_versioning_existing_dataset(
        self, excel_data_set, versioned_excel_data_set, dummy_dataframe
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        excel_data_set.save(dummy_dataframe)
        assert excel_data_set.exists()
        assert excel_data_set._filepath == versioned_excel_data_set._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_excel_data_set._filepath.parent.as_posix()})"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_excel_data_set.save(dummy_dataframe)

        # Remove non-versioned dataset and try again
        Path(excel_data_set._filepath.as_posix()).unlink()
        versioned_excel_data_set.save(dummy_dataframe)
        assert versioned_excel_data_set.exists()
