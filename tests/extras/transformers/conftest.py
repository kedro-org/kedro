"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

from typing import Any, Dict

import pytest

from kedro.io import AbstractDataSet, DataCatalog


class FakeDataSet(AbstractDataSet):
    def __init__(self, data):
        self.log = []
        self.data = data

    def _load(self) -> Any:
        self.log.append(("load", self.data))
        return self.data

    def _save(self, data: Any) -> None:
        self.log.append(("save", data))
        self.data = data

    def _describe(self) -> Dict[str, Any]:
        return {"data": self.data}


@pytest.fixture
def fake_data_set():
    return FakeDataSet(123)


@pytest.fixture
def catalog(fake_data_set):
    return DataCatalog({"test": fake_data_set})
