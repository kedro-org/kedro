"""Shared fixtures for validation framework tests."""

from __future__ import annotations

import dataclasses

import pytest
from pydantic import BaseModel

from kedro.validation.source_filters import ParameterSourceFilter


@dataclasses.dataclass
class SampleDataclass:
    name: str
    value: float


class SamplePydanticModel(BaseModel):
    test_size: float
    random_state: int


@pytest.fixture
def source_filter():
    return ParameterSourceFilter()
