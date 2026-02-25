"""Shared fixtures for validation framework tests."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class SampleDataclass:
    name: str
    value: float


try:
    from pydantic import BaseModel

    class SamplePydanticModel(BaseModel):
        test_size: float
        random_state: int

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
