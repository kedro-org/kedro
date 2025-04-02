from __future__ import annotations

import logging
import pprint
import shutil
from decimal import Decimal
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any

import fsspec
import pandas as pd
import pytest

from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetError,
    Version,
    VersionNotFoundError,
    generate_timestamp,
    get_filepath_str,
    get_protocol_and_path,
    parse_dataset_definition,
    validate_on_forbidden_chars,
)
from kedro.io.lambda_dataset import LambdaDataset

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

    def _save(self, data: str) -> None:
        with open(self._filepath, mode="w") as file:
            file.write(data)


class MyVersionedDataset(AbstractVersionedDataset[str, str]):
    def __init__(
        self,
        filepath: str,
        version: Version = None,
    ) -> None:
        _fs_args: dict[Any, Any] = {}
        _fs_args.setdefault("auto_mkdir", True)
        protocol, path = get_protocol_and_path(filepath, version)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

    def _describe(self) -> dict[str, Any]:
        return dict(filepath=self._filepath, version=self._version)

    def _load(self) -> str:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        with self._fs.open(load_path, mode="r") as fs_file:
            return fs_file.read()

    def _save(self, data: str) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        with self._fs.open(save_path, mode="w") as fs_file:
            fs_file.write(data)

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DatasetError:
            return False

        return self._fs.exists(load_path)


class MyLocalVersionedDataset(AbstractVersionedDataset[str, str]):
    def __init__(
        self,
        filepath: str,
        version: Version = None,
    ) -> None:
        _fs_args: dict[Any, Any] = {}
        _fs_args.setdefault("auto_mkdir", True)
        protocol, path = get_protocol_and_path(filepath, version)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            glob_function=self._fs.glob,
        )  # Not passing exists_function so it'll use _local_exists() instead.

    def _describe(self) -> dict[str, Any]:
        return dict(filepath=self._filepath, version=self._version)

    def _load(self) -> str:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        with self._fs.open(load_path, mode="r") as fs_file:
            return fs_file.read()

    def _save(self, data: str) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        with self._fs.open(save_path, mode="w") as fs_file:
            fs_file.write(data)

    def _exists(self) -> bool:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)
        # no try catch - will return a VersionNotFoundError to be caught be AbstractVersionedDataset.exists()
        return self._fs.exists(load_path)


class MyOtherVersionedDataset(MyLocalVersionedDataset):
    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except VersionNotFoundError:
            raise NameError("Raising a NameError instead")
        return self._fs.exists(load_path)


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
    return MyVersionedDataset(
        filepath=filepath_versioned, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_data():
    return "col1 : [1, 2], col2 : [4, 5], col3 : [5, 6]}"


class TestCoreFunctions:
    @pytest.mark.parametrize("var", [1, True, *FALSE_BUILTINS])
    def test_str_representation(self, var):
        var_str = pprint.pformat(var)
        filepath_str = pprint.pformat(PurePosixPath("."))
        assert str(MyDataset(var=var)) == f"MyDataset(filepath=., var={var})"
        assert (
            repr(MyDataset(var=var))
            == f"tests.io.test_core.MyDataset(filepath={filepath_str}, var={var_str})"
        )

    def test_str_representation_none(self):
        assert str(MyDataset()) == "MyDataset(filepath=.)"
        filepath_str = pprint.pformat(PurePosixPath("."))
        assert (
            repr(MyDataset())
            == f"tests.io.test_core.MyDataset(filepath={filepath_str})"
        )

    @pytest.mark.parametrize(
        "describe_return",
        [None, {"key_1": "val_1", 2: "val_2"}],
    )
    def test_repr_bad_describe(self, describe_return, caplog):
        class BadDescribeDataset(MyDataset):
            def _describe(self):
                return describe_return

        warning_message = (
            "'tests.io.test_core.BadDescribeDataset' is a subclass of AbstractDataset and it must "
            "implement the '_describe' method following the signature of AbstractDataset's '_describe'."
        )

        with caplog.at_level(logging.WARNING):
            assert (
                repr(BadDescribeDataset()) == "tests.io.test_core.BadDescribeDataset()"
            )
            assert warning_message in caplog.text

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
            ("oci://bucket@namespace/file.txt", ("oci", "bucket@namespace/file.txt")),
            ("hdfs://namenode:8020/file.txt", ("hdfs", "/file.txt")),
            ("file:///tmp/file.txt", ("file", "/tmp/file.txt")),
            ("/tmp/file.txt", ("file", "/tmp/file.txt")),
            ("C:\\Projects\\file.txt", ("file", "C:\\Projects\\file.txt")),
            ("file:///C:\\Projects\\file.txt", ("file", "C:\\Projects\\file.txt")),
            ("https://example.com/file.txt", ("https", "example.com/file.txt")),
            ("http://example.com/file.txt", ("http", "example.com/file.txt")),
            (
                "https://example.com/search?query=books&category=fiction#reviews",
                ("https", "example.com/search?query=books&category=fiction#reviews"),
            ),
            (
                "https://example.com/search#reviews",
                ("https", "example.com/search#reviews"),
            ),
            (
                "http://example.com/search?query=books&category=fiction",
                ("http", "example.com/search?query=books&category=fiction"),
            ),
            (
                "s3://some/example?query=query#filename",
                ("s3", "some/example?query=query#filename"),
            ),
            ("s3://some/example#filename", ("s3", "some/example#filename")),
            ("s3://some/example?query=query", ("s3", "some/example?query=query")),
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
    def test_get_protocol_and_path_http_with_version(self, filepath):
        version = Version(load=None, save=None)
        expected_error_message = "Versioning is not supported for HTTP protocols. Please remove the `versioned` flag from the dataset configuration."
        with pytest.raises(DatasetError, match=expected_error_message):
            get_protocol_and_path(filepath, version)

    @pytest.mark.parametrize(
        "input", [{"key1": "invalid value"}, {"key2": "invalid;value"}]
    )
    def test_validate_forbidden_chars(self, input):
        key = next(iter(input.keys()))
        expected_error_message = (
            f"Neither white-space nor semicolon are allowed in '{key}'."
        )
        with pytest.raises(DatasetError, match=expected_error_message):
            validate_on_forbidden_chars(**input)

    def test_dataset_name_typo(self, mocker):
        # If the module doesn't exist, it return None instead ModuleNotFoundError
        mocker.patch("kedro.io.core.load_obj", return_value=None)
        dataset_name = "lAmbDaDaTAsET"

        with pytest.raises(
            DatasetError, match=f"Class '{dataset_name}' not found, is this a typo?"
        ):
            parse_dataset_definition({"type": dataset_name})

    def test_dataset_missing_dependencies(self, mocker):
        # If the module is found but import the dataset trigger ModuleNotFoundError
        dataset_name = "LambdaDataset"

        def side_effect_function(value):
            if "__all__" in value:
                return [dataset_name]
            else:
                raise ModuleNotFoundError

        mocker.patch("kedro.io.core.load_obj", side_effect=side_effect_function)

        pattern = "Please see the documentation on how to install relevant dependencies"
        with pytest.raises(DatasetError, match=pattern):
            parse_dataset_definition({"type": dataset_name})

    def test_parse_dataset_definition(self):
        config = {"type": "LambdaDataset"}
        dataset, _ = parse_dataset_definition(config)
        assert dataset is LambdaDataset

    def test_parse_dataset_definition_with_python_class_type(self):
        config = {"type": MyDataset}
        parse_dataset_definition(config)

    def test_load_and_save_are_wrapped_once(self):
        assert not getattr(
            MyOtherVersionedDataset.load.__wrapped__, "__loadwrapped__", False
        )
        assert not getattr(
            MyOtherVersionedDataset.save.__wrapped__, "__savewrapped__", False
        )


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
        the versioned dataset."""
        my_versioned_dataset.save(dummy_data)
        reloaded = my_versioned_dataset.load()
        assert dummy_data == reloaded

    def test_resolve_save_version(self, dummy_data):
        ds = MyVersionedDataset("test.csv", Version(None, None))
        ds.save(dummy_data)
        assert ds._filepath

        # teardown
        shutil.rmtree(ds._filepath)

    def test_no_versions(self, my_versioned_dataset):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for MyVersionedDataset\(.+\)"
        with pytest.raises(DatasetError, match=pattern):
            my_versioned_dataset.load()

    def test_local_exists(self, dummy_data):
        """Check the error if no versions are available for load (_local_exists())."""
        version = Version(load=None, save=None)
        my_versioned_dataset = MyLocalVersionedDataset("test.csv", version=version)
        assert my_versioned_dataset.exists() is False
        my_versioned_dataset.save(dummy_data)  # _local_exists is used by save
        assert my_versioned_dataset.exists() is True
        shutil.rmtree(my_versioned_dataset._filepath)

    def test_exists_general_exception(self):
        """Check if all exceptions are shown as DatasetError for exists() check"""
        version = Version(load=None, save=None)
        my_other_versioned_dataset = MyOtherVersionedDataset(
            "test.csv", version=version
        )
        # Override the _exists() function to return a different exception
        with pytest.raises(DatasetError):
            my_other_versioned_dataset.exists()

    def test_exists(self, my_versioned_dataset, dummy_data):
        """Test `exists` method invocation for versioned dataset."""
        assert not my_versioned_dataset.exists()
        my_versioned_dataset.save(dummy_data)
        assert my_versioned_dataset.exists()
        shutil.rmtree(my_versioned_dataset._filepath)

    def test_prevent_overwrite(self, my_versioned_dataset, dummy_data):
        """Check the error when attempting to override the dataset if the
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

    def test_cache_release(self, my_versioned_dataset):
        my_versioned_dataset._version_cache["index"] = "value"
        assert my_versioned_dataset._version_cache.currsize > 0

        my_versioned_dataset._release()
        assert my_versioned_dataset._version_cache.currsize == 0


class MyLegacyDataset(AbstractDataset):
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

    def _save(self, data: str) -> None:
        with open(self._filepath, mode="w") as file:
            file.write(data)


class MyLegacyVersionedDataset(AbstractVersionedDataset[str, str]):
    def __init__(
        self,
        filepath: str,
        version: Version = None,
    ) -> None:
        _fs_args: dict[Any, Any] = {}
        _fs_args.setdefault("auto_mkdir", True)
        protocol, path = get_protocol_and_path(filepath, version)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

    def _describe(self) -> dict[str, Any]:
        return dict(filepath=self._filepath, version=self._version)

    def _load(self) -> str:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        with self._fs.open(load_path, mode="r") as fs_file:
            return fs_file.read()

    def _save(self, data: str) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        with self._fs.open(save_path, mode="w") as fs_file:
            fs_file.write(data)

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DatasetError:
            return False

        return self._fs.exists(load_path)


@pytest.fixture
def my_legacy_dataset(filepath_versioned, save_args, fs_args):
    return MyLegacyDataset(
        filepath=filepath_versioned, save_args=save_args, fs_args=fs_args
    )


@pytest.fixture
def my_legacy_versioned_dataset(filepath_versioned, load_version, save_version):
    return MyLegacyVersionedDataset(
        filepath=filepath_versioned, version=Version(load_version, save_version)
    )


class TestLegacyLoadAndSave:
    def test_saving_none(self, my_legacy_dataset):
        """Check the error when attempting to save the dataset without
        providing the data"""
        pattern = r"Saving 'None' to a 'Dataset' is not allowed"
        with pytest.raises(DatasetError, match=pattern):
            my_legacy_dataset.save(None)

    def test_saving_invalid_data(self, my_legacy_dataset, dummy_data):
        pattern = r"Failed while saving data to dataset"
        with pytest.raises(DatasetError, match=pattern):
            my_legacy_dataset.save(pd.DataFrame())

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, my_legacy_versioned_dataset, load_version, save_version, dummy_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            f"Save version '{save_version}' did not match "
            f"load version '{load_version}' for "
            r"MyLegacyVersionedDataset\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            my_legacy_versioned_dataset.save(dummy_data)

    def test_versioning_existing_dataset(
        self, my_legacy_dataset, my_legacy_versioned_dataset, dummy_data
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        my_legacy_dataset.save(dummy_data)
        assert my_legacy_dataset.exists()
        assert my_legacy_dataset._filepath == my_legacy_versioned_dataset._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{my_legacy_versioned_dataset._filepath.parent.as_posix()})"
        )
        with pytest.raises(DatasetError, match=pattern):
            my_legacy_versioned_dataset.save(dummy_data)

        # Remove non-versioned dataset and try again
        Path(my_legacy_dataset._filepath.as_posix()).unlink()
        my_legacy_versioned_dataset.save(dummy_data)
        assert my_legacy_versioned_dataset.exists()
