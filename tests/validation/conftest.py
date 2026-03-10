"""Shared fixtures for validation framework tests."""

from __future__ import annotations

import dataclasses

import pytest
from pydantic import BaseModel

from kedro.validation.type_extractor import TypeExtractor


@dataclasses.dataclass
class SampleDataclass:
    name: str
    value: float


class SamplePydanticModel(BaseModel):
    test_size: float
    random_state: int


@pytest.fixture
def type_extractor():
    return TypeExtractor()
