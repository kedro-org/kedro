"""Shared fixtures for validation framework tests."""

from __future__ import annotations

import dataclasses

import pytest
from pydantic import BaseModel

from kedro.validation.model_factory import ModelFactory


@dataclasses.dataclass
class SampleDataclass:
    name: str
    value: float


class SamplePydanticModel(BaseModel):
    test_size: float
    random_state: int


@pytest.fixture
def model_factory():
    return ModelFactory()
