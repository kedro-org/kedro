"""Example node functions with Pandera schema type hints.

By annotating a node input with a Pandera DataFrameModel subclass, the
framework automatically validates the DataFrame against that schema when
the dataset is loaded — no hooks, no catalog changes required.
"""

from __future__ import annotations

import pandas as pd

from .schemas import CompaniesSchema, ReviewsSchema, ShuttlesSchema


def preprocess_companies(companies: CompaniesSchema) -> pd.DataFrame:
    """Preprocess the companies dataset.

    The ``CompaniesSchema`` type hint causes automatic validation of the
    ``companies`` DataFrame before this function executes.
    """
    companies["iata_approved"] = companies["iata_approved"].map(
        {"t": True, "f": False}
    )
    return companies


def preprocess_shuttles(shuttles: ShuttlesSchema) -> pd.DataFrame:
    """Preprocess the shuttles dataset."""
    shuttles["d_check_complete"] = shuttles["d_check_complete"].astype(bool)
    return shuttles


def join_data(
    companies: CompaniesSchema,
    shuttles: ShuttlesSchema,
    reviews: ReviewsSchema,
) -> pd.DataFrame:
    """Join all three datasets.

    Multiple Pandera schemas on the same node — each is validated independently.
    """
    merged = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    merged = merged.merge(companies, left_on="id", right_on="id")
    return merged
