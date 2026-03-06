"""Shared fixtures for validation framework tests."""

from __future__ import annotations

import dataclasses

from pydantic import BaseModel


@dataclasses.dataclass
class SampleDataclass:
    name: str
    value: float


class SamplePydanticModel(BaseModel):
    test_size: float
    random_state: int
