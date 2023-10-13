from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from pathlib import PurePosixPath, Path
from typing import Any

import pandas as pd
import pytest

from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetError,
    Version,
    generate_timestamp,
    get_filepath_str,
    get_protocol_and_path,
    validate_on_forbidden_chars,
)

# List sourced from https://docs.python.org/3/library/stdtypes.html#truth-value-testing.
# Excludes None, as None values are not shown in the str representation.
FALSE_BUILTINS: list[Any] = [
    False,
    0,
    0.0,
    0j,
    Decimal(0),
    Fraction(0, 1),
    "",
    (),
    [],
    {},
    set(),
    range(0),
]


class MyDataset(AbstractDataset):
    def __init__(self, filepath="", save_args=None, fs_args=None, var=None):
        self._filepath = PurePosixPath(filepath)
        self.save_args = save_args
        self.fs_args = fs_args
        self.var = var

    def _describe(self):
        return {"filepath": self._filepath, "var": self.var}

    def _exists(self) -> bool:
        return Path(self._filepath.as_posix()).exists()

    def _load(self):
        return pd.read_csv(self._filepath)

    def _save(self, data : pd.DataFrame):
        data.to_csv(str(self._filepath))


class MyVersionedDataset(AbstractVersionedDataset):
    def __init__(self, filepath, version):
        super().__init__(PurePosixPath(filepath), version)

    def _load(self):
        load_path = self._get_load_path()
        return pd.read_csv(load_path)

    def _save(self, data: pd.DataFrame):
        save_path = self._get_save_path()
        data.to_csv(str(save_path))

    def _describe(self):
        return dict(filepath=self._filepath, version=self._version)

    def _exists(self) -> bool:
        return Path(self._filepath.as_posix()).exists()

    # def _exists(self) -> bool:
        # try:
        #     path = self._get_load_path()
        #     load_path = get_filepath_str(path, self._protocol)
        # except DatasetError:
        #     return False

@pytest.fixture(params=[None])
def load_version(request):
    return request.param


@pytest.fixture(params=[None])
def save_version(request):
    return request.param or generate_timestamp()

@pytest.fixture(params=[None])
def load_args(request):
    return request.param


@pytest.fixture(params=[None])
def save_args(request):
    return request.param


@pytest.fixture(params=[None])
def fs_args(request):
    return request.param

@pytest.fixture
def filepath_versioned(tmp_path):
    return (tmp_path / "test.csv").as_posix()

@pytest.fixture
def my_dataset(filepath_versioned, save_args, fs_args):
    return MyDataset(filepath=filepath_versioned, save_args=save_args, fs_args=fs_args)

@pytest.fixture
def my_versioned_dataset(filepath_versioned, load_version, save_version):
    return MyVersionedDataset(filepath=filepath_versioned, version=Version(load_version, save_version))

@pytest.fixture
def dummy_data():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestCoreFunctions:
    @pytest.mark.parametrize("var", [1, True] + FALSE_BUILTINS)
    def test_str_representation(self, var):
        filepath = "."
        assert str(MyDataset(var=var)) == f"MyDataset(filepath={filepath}, var={var})"

    def test_str_representation_none(self):
        assert str(MyDataset()) == "MyDataset(filepath=.)"

    def test_get_filepath_str(self):
        path = get_filepath_str(PurePosixPath("example.com/test.csv"), "http")
        assert isinstance(path, str)
        assert path == "http://example.com/test.csv"

    @pytest.mark.parametrize(
        "filepath,expected_result",
        [
            ("s3://bucket/file.txt", ("s3", "bucket/file.txt")),
            ("s3://user@BUCKET/file.txt", ("s3", "BUCKET/file.txt")),
            ("gcs://bucket/file.txt", ("gcs", "bucket/file.txt")),
            ("gs://bucket/file.txt", ("gs", "bucket/file.txt")),
            ("adl://bucket/file.txt", ("adl", "bucket/file.txt")),
            ("abfs://bucket/file.txt", ("abfs", "bucket/file.txt")),
            ("abfss://bucket/file.txt", ("abfss", "bucket/file.txt")),
            (
                "abfss://mycontainer@mystorageaccount.dfs.core.windows.net/mypath",
                ("abfss", "mycontainer@mystorageaccount.dfs.core.windows.net/mypath"),
            ),
            ("hdfs://namenode:8020/file.txt", ("hdfs", "/file.txt")),
            ("file:///tmp/file.txt", ("file", "/tmp/file.txt")),
            ("/tmp/file.txt", ("file", "/tmp/file.txt")),
            ("C:\\Projects\\file.txt", ("file", "C:\\Projects\\file.txt")),
            ("file:///C:\\Projects\\file.txt", ("file", "C:\\Projects\\file.txt")),
            ("https://example.com/file.txt", ("https", "example.com/file.txt")),
            ("http://example.com/file.txt", ("http", "example.com/file.txt")),
        ],
    )
    def test_get_protocol_and_path(self, filepath, expected_result):
        assert get_protocol_and_path(filepath) == expected_result

    @pytest.mark.parametrize(
        "filepath",
        [
            "http://example.com/file.txt",
            "https://example.com/file.txt",
        ],
    )
    def test_get_protocol_and_path_http_with_verion(self, filepath):
        version = version = Version(load=None, save=None)
        expected_error_message = "Versioning is not supported for HTTP protocols. Please remove the `versioned` flag from the dataset configuration."
        with pytest.raises(DatasetError, match=expected_error_message):
            get_protocol_and_path(filepath, version)

    @pytest.mark.parametrize(
        "input", [{"key1": "invalid value"}, {"key2": "invalid;value"}]
    )
    def test_validate_forbidden_chars(self, input):
        key = list(input.keys())[0]
        expected_error_message = (
            f"Neither white-space nor semicolon are allowed in '{key}'."
        )
        with pytest.raises(DatasetError, match=expected_error_message):
            validate_on_forbidden_chars(**input)


class TestAbstractDataSet:
    pass


class TestAbstractVersionedDataset:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.csv"
        ds_versioned = MyVersionedDataset(
            filepath=filepath, version=Version(load_version, save_version)
        )

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "MyVersionedDataset" in str(ds_versioned)

    def test_save_and_load(self, my_versioned_dataset, dummy_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        my_versioned_dataset.save(dummy_data)
        reloaded = my_versioned_dataset.load()
        assert dummy_data == reloaded

    def test_no_versions(self, my_versioned_dataset):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for MyVersionedDataset\(.+\)"
        with pytest.raises(DatasetError, match=pattern):
            my_versioned_dataset.load()

    def test_exists(self, my_versioned_dataset, dummy_data):
        """Test `exists` method invocation for versioned data set."""
        assert not my_versioned_dataset.exists()
        my_versioned_dataset.save(dummy_data)
        assert my_versioned_dataset.exists()

    def test_prevent_overwrite(self, my_versioned_dataset, dummy_data):
        """Check the error when attempting to override the data set if the
        corresponding json file for a given save version already exists."""
        my_versioned_dataset.save(dummy_data)
        pattern = (
            r"Save path \'.+\' for MyVersionedDataset\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DatasetError, match=pattern):
            my_versioned_dataset.save(dummy_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, my_versioned_dataset, load_version, save_version, dummy_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            f"Save version '{save_version}' did not match "
            f"load version '{load_version}' for "
            r"MyVersionedDataset\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            my_versioned_dataset.save(dummy_data)

    def test_versioning_existing_dataset(
        self, my_dataset, my_versioned_dataset, dummy_data
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        my_dataset.save(dummy_data)
        assert my_dataset.exists()
        assert my_dataset._filepath == my_versioned_dataset._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{my_versioned_dataset._filepath.parent.as_posix()})"
        )
        with pytest.raises(DatasetError, match=pattern):
            my_versioned_dataset.save(dummy_data)

        # Remove non-versioned dataset and try again
        Path(my_dataset._filepath.as_posix()).unlink()
        my_versioned_dataset.save(dummy_data)
        assert my_versioned_dataset.exists()
