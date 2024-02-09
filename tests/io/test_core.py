from __future__ import annotations

import importlib
from decimal import Decimal
from fractions import Fraction
from pathlib import PurePosixPath
from typing import Any

import pytest

from kedro import KedroDeprecationWarning
from kedro.io.core import (
    _DEPRECATED_CLASSES,
    AbstractDataset,
    _parse_filepath,
    get_filepath_str,
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


@pytest.mark.parametrize("module_name", ["kedro.io", "kedro.io.core"])
@pytest.mark.parametrize("class_name", _DEPRECATED_CLASSES)
def test_deprecation(module_name, class_name):
    with pytest.warns(
        KedroDeprecationWarning, match=f"{repr(class_name)} has been renamed"
    ):
        getattr(importlib.import_module(module_name), class_name)


class MyDataSet(AbstractDataset):
    def __init__(self, var=None):
        self.var = var

    def _describe(self):
        return {"var": self.var}

    def _load(self):
        pass  # pragma: no cover

    def _save(self, data):
        pass  # pragma: no cover


class TestCoreFunctions:
    @pytest.mark.parametrize("var", [1, True] + FALSE_BUILTINS)
    def test_str_representation(self, var):
        assert str(MyDataSet(var)) == f"MyDataSet(var={var})"

    def test_str_representation_none(self):
        assert str(MyDataSet()) == "MyDataSet()"

    def test_get_filepath_str(self):
        path = get_filepath_str(PurePosixPath("example.com/test.csv"), "http")
        assert isinstance(path, str)
        assert path == "http://example.com/test.csv"

    @pytest.mark.parametrize(
        "filepath,expected_result",
        [
            ("s3://bucket/file.txt", {"protocol": "s3", "path": "bucket/file.txt"}),
            (
                "s3://user@BUCKET/file.txt",
                {"protocol": "s3", "path": "BUCKET/file.txt"},
            ),
            ("gcs://bucket/file.txt", {"protocol": "gcs", "path": "bucket/file.txt"}),
            ("gs://bucket/file.txt", {"protocol": "gs", "path": "bucket/file.txt"}),
            ("adl://bucket/file.txt", {"protocol": "adl", "path": "bucket/file.txt"}),
            ("abfs://bucket/file.txt", {"protocol": "abfs", "path": "bucket/file.txt"}),
            (
                "abfss://bucket/file.txt",
                {"protocol": "abfss", "path": "bucket/file.txt"},
            ),
            (
                "abfss://mycontainer@mystorageaccount.dfs.core.windows.net/mypath",
                {
                    "protocol": "abfss",
                    "path": "mycontainer@mystorageaccount.dfs.core.windows.net/mypath",
                },
            ),
            (
                "hdfs://namenode:8020/file.txt",
                {"protocol": "hdfs", "path": "/file.txt"},
            ),
            ("file:///tmp/file.txt", {"protocol": "file", "path": "/tmp/file.txt"}),
            ("/tmp/file.txt", {"protocol": "file", "path": "/tmp/file.txt"}),
            (
                "C:\\Projects\\file.txt",
                {"protocol": "file", "path": "C:\\Projects\\file.txt"},
            ),
            (
                "file:///C:\\Projects\\file.txt",
                {"protocol": "file", "path": "C:\\Projects\\file.txt"},
            ),
            (
                "https://example.com/file.txt",
                {"protocol": "https", "path": "https://example.com/file.txt"},
            ),
            (
                "http://example.com/file.txt",
                {"protocol": "http", "path": "http://example.com/file.txt"},
            ),
        ],
    )
    def test_parse_filepath(self, filepath, expected_result):
        assert _parse_filepath(filepath) == expected_result
