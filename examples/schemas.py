"""Example validators for KEP-7 v2 catalog-native dataset validation.

Pandera ``DataFrameModel`` schemas using the modern ``pandera.pandas``
namespace (the top-level ``pandera.DataFrameModel`` is deprecated as of
pandera 0.30), plus a non-tabular ``MetricsValidator`` showing that any
object with a ``validate(data) -> data`` method plugs into the same
catalog ``validator:`` key.

Declared in the catalog as, e.g.::

    companies:
      type: pandas.CSVDataset
      filepath: data/01_raw/companies.csv
      validator: examples.schemas.CompaniesSchema
"""

from __future__ import annotations

from typing import Any

import pandera.pandas as pa


class CompaniesSchema(pa.DataFrameModel):
    """Schema for the companies dataset."""

    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1)

    class Config:
        strict = False  # allow extra columns not listed here
        coerce = True  # coerce dtypes (e.g. float64 ids from CSV -> int64)


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
        coerce = True


class ReviewsSchema(pa.DataFrameModel):
    """Schema for the reviews dataset."""

    shuttle_id: int = pa.Field(nullable=False)
    review_scores_rating: float = pa.Field(ge=0, le=100)

    class Config:
        strict = False
        coerce = True


class MetricsValidator:
    """Non-tabular validator: checks a metrics dict for required keys.

    Demonstrates the ``Validator`` protocol — no pandera, no DataFrame.
    Any class whose instances expose ``validate(data) -> data`` (raising on
    failure) can be declared in the catalog::

        model_metrics:
          type: json.JSONDataset
          filepath: data/08_reporting/metrics.json
          validator:
            class: examples.schemas.MetricsValidator
            options:
              required_keys: [accuracy, f1]
    """

    def __init__(self, required_keys: list[str] | None = None) -> None:
        """Initialise the validator.

        Args:
            required_keys: Keys that must be present in the metrics dict.
        """
        self._required_keys = tuple(required_keys or ())

    def validate(self, data: Any) -> Any:
        """Validate that ``data`` is a dict containing every required key.

        Args:
            data: The in-memory data of the dataset.

        Returns:
            The data, unchanged, when validation passes.

        Raises:
            TypeError: If ``data`` is not a dict.
            ValueError: If any required key is missing.
        """
        if not isinstance(data, dict):
            raise TypeError(
                f"Expected metrics to be a dict, got {type(data).__name__}."
            )
        missing = sorted(key for key in self._required_keys if key not in data)
        if missing:
            raise ValueError(f"Metrics dict is missing required key(s): {missing}.")
        return data
