from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from pathlib import PurePosixPath
from typing import Any

import pandas as pd
import pytest

from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetError,
    Version,
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
    def __init__(self, var=None):
        self.var = var

    def _describe(self):
        return {"var": self.var}

    def _load(self):
        pass  # pragma: no cover

    def _save(self, data):
        pass  # pragma: no cover


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
        return dict(version=self._version)


class TestCoreFunctions:
    @pytest.mark.parametrize("var", [1, True] + FALSE_BUILTINS)
    def test_str_representation(self, var):
        assert str(MyDataset(var)) == f"MyDataset(var={var})"

    def test_str_representation_none(self):
        assert str(MyDataset()) == "MyDataset()"

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
    pass
