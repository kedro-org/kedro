"""Example node functions with Pandera schema type hints.

Since KEP-7 v2, validation is declared on the catalog entry via the
``validator:`` key (see ``examples/catalog.yml``) and applied by the
``DataCatalog`` on load/save. The schema type hints below no longer trigger
validation themselves — they remain as living documentation of each node's
expected input shape.
"""

# The schema imports stay at runtime (not in a TYPE_CHECKING block) so the
# hints remain resolvable via typing.get_type_hints at runtime.
# ruff: noqa: TCH001, TCH002

from __future__ import annotations

import pandas as pd

from .schemas import CompaniesSchema, ReviewsSchema, ShuttlesSchema


def preprocess_companies(companies: CompaniesSchema) -> pd.DataFrame:
    """Preprocess the companies dataset.

    The ``CompaniesSchema`` hint documents the expected input; the actual
    validation happens in the catalog (``validator:`` on the ``companies``
    entry) before this function ever sees the data.
    """
    companies["iata_approved"] = companies["iata_approved"].map({"t": True, "f": False})
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

    Each input dataset declares its own ``validator:`` in the catalog and is
    validated independently when loaded.
    """
    merged = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    merged = merged.merge(companies, left_on="id", right_on="id")
    return merged
