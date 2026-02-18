from __future__ import annotations

import dataclasses

import pytest

from kedro.framework.validation import (
    ModelFactory,
    ParameterSourceFilter,
    TypeExtractor,
)
from kedro.framework.validation.source_filters import DatasetSourceFilter
from kedro.framework.validation.validators.parameter_validator import (
    ParameterValidator,
)


@dataclasses.dataclass
class SampleDataclass:
    name: str
    value: float


try:
    from pydantic import BaseModel, Field

    class SamplePydanticModel(BaseModel):
        test_size: float
        random_state: int

    class ConstrainedModel(BaseModel):
        precision: int = Field(ge=1, le=10)

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


@pytest.fixture
def source_filter():
    return ParameterSourceFilter()


@pytest.fixture
def dataset_filter():
    return DatasetSourceFilter()


@pytest.fixture
def type_extractor(source_filter):
    return TypeExtractor(source_filter)


@pytest.fixture
def model_factory():
    return ModelFactory()


@pytest.fixture
def parameter_validator():
    return ParameterValidator()
