from pathlib import Path, PurePosixPath

import pandas as pd
import pytest
from adlfs import AzureBlobFileSystem
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import XMLDataSet
from kedro.io import DatasetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_xml(tmp_path):
    return (tmp_path / "test.xml").as_posix()


@pytest.fixture
def xml_dataset(filepath_xml, load_args, save_args, fs_args):
    return XMLDataSet(
        filepath=filepath_xml,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_xml_dataset(filepath_xml, load_version, save_version):
    return XMLDataSet(
        filepath=filepath_xml, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestXMLDataSet:
    def test_save_and_load(self, xml_dataset, dummy_dataframe):
        """Test saving and reloading the data set."""
        xml_dataset.save(dummy_dataframe)
        reloaded = xml_dataset.load()
        assert_frame_equal(dummy_dataframe, reloaded)

    def test_exists(self, xml_dataset, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not xml_dataset.exists()
        xml_dataset.save(dummy_dataframe)
        assert xml_dataset.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, xml_dataset, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert xml_dataset._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, xml_dataset, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert xml_dataset._save_args[key] == value

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

        ds = XMLDataSet(filepath=filepath, load_args=load_args, save_args=save_args)

        records = [r for r in caplog.records if r.levelname == "WARNING"]
        expected_log_message = (
            f"Dropping 'storage_options' for {filepath}, "
            f"please specify them under 'fs_args' or 'credentials'."
        )
        assert records[0].getMessage() == expected_log_message
        assert "storage_options" not in ds._save_args
        assert "storage_options" not in ds._load_args

    def test_load_missing_file(self, xml_dataset):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set XMLDataSet\(.*\)"
        with pytest.raises(DatasetError, match=pattern):
            xml_dataset.load()

    @pytest.mark.parametrize(
        "filepath,instance_type,credentials,load_path",
        [
            ("s3://bucket/file.xml", S3FileSystem, {}, "s3://bucket/file.xml"),
            ("file:///tmp/test.xml", LocalFileSystem, {}, "/tmp/test.xml"),
            ("/tmp/test.xml", LocalFileSystem, {}, "/tmp/test.xml"),
            ("gcs://bucket/file.xml", GCSFileSystem, {}, "gcs://bucket/file.xml"),
            (
                "https://example.com/file.xml",
                HTTPFileSystem,
                {},
                "https://example.com/file.xml",
            ),
            (
                "abfs://bucket/file.csv",
                AzureBlobFileSystem,
                {"account_name": "test", "account_key": "test"},
                "abfs://bucket/file.csv",
            ),
        ],
    )
    def test_protocol_usage(
        self, filepath, instance_type, credentials, load_path, mocker
    ):
        dataset = XMLDataSet(filepath=filepath, credentials=credentials)
        assert isinstance(dataset._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(dataset._filepath) == path
        assert isinstance(dataset._filepath, PurePosixPath)

        mock_pandas_call = mocker.patch("pandas.read_xml")
        dataset.load()
        assert mock_pandas_call.call_count == 1
        assert mock_pandas_call.call_args_list[0][0][0] == load_path

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.xml"
        dataset = XMLDataSet(filepath=filepath)
        dataset.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestXMLDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.xml"
        ds = XMLDataSet(filepath=filepath)
        ds_versioned = XMLDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "XMLDataSet" in str(ds_versioned)
        assert "XMLDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_xml_dataset, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_xml_dataset.save(dummy_dataframe)
        reloaded_df = versioned_xml_dataset.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_xml_dataset):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for XMLDataSet\(.+\)"
        with pytest.raises(DatasetError, match=pattern):
            versioned_xml_dataset.load()

    def test_exists(self, versioned_xml_dataset, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_xml_dataset.exists()
        versioned_xml_dataset.save(dummy_dataframe)
        assert versioned_xml_dataset.exists()

    def test_prevent_overwrite(self, versioned_xml_dataset, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding hdf file for a given save version already exists."""
        versioned_xml_dataset.save(dummy_dataframe)
        pattern = (
            r"Save path \'.+\' for XMLDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DatasetError, match=pattern):
            versioned_xml_dataset.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_xml_dataset, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            rf"Save version '{save_version}' did not match "
            rf"load version '{load_version}' for XMLDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_xml_dataset.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = "Versioning is not supported for HTTP protocols."

        with pytest.raises(DatasetError, match=pattern):
            XMLDataSet(
                filepath="https://example.com/file.xml", version=Version(None, None)
            )

    def test_versioning_existing_dataset(
        self, xml_dataset, versioned_xml_dataset, dummy_dataframe
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        xml_dataset.save(dummy_dataframe)
        assert xml_dataset.exists()
        assert xml_dataset._filepath == versioned_xml_dataset._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_xml_dataset._filepath.parent.as_posix()})"
        )
        with pytest.raises(DatasetError, match=pattern):
            versioned_xml_dataset.save(dummy_dataframe)

        # Remove non-versioned dataset and try again
        Path(xml_dataset._filepath.as_posix()).unlink()
        versioned_xml_dataset.save(dummy_dataframe)
        assert versioned_xml_dataset.exists()
