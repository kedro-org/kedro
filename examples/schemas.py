"""Example Pandera DataFrameModel schemas for the spaceflights dataset.

These schemas define the expected structure and constraints for DataFrames
flowing through the pipeline. Adding a schema type hint to a node function
is all that's needed — validation happens automatically at load time.
"""

from __future__ import annotations

import pandera as pa


class CompaniesSchema(pa.DataFrameModel):
    """Schema for the companies dataset."""

    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1)
    iata_approved: str = pa.Field(isin=["t", "f"])
    company_location: str = pa.Field(nullable=False)
    total_fleet_count: float = pa.Field(ge=0)

    class Config:
        strict = False  # allow extra columns not listed here


class ShuttlesSchema(pa.DataFrameModel):
    """Schema for the shuttles dataset."""

    id: int = pa.Field(nullable=False, unique=True)
    shuttle_location: str = pa.Field(nullable=False)
    shuttle_type: str = pa.Field(nullable=False)
    engine_type: str = pa.Field(nullable=False)
    capacity: int = pa.Field(gt=0)
    d_check_complete: bool = pa.Field()

    class Config:
        strict = False


class ReviewsSchema(pa.DataFrameModel):
    """Schema for the reviews dataset."""

    shuttle_id: int = pa.Field(nullable=False)
    review_scores_rating: float = pa.Field(ge=0, le=100)

    class Config:
        strict = False
