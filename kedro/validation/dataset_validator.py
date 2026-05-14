"""Dataset validation using Pandera DataFrameModel schemas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kedro.io import AbstractDataset

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when dataset validation against a Pandera schema fails."""

    pass


def _is_pandera_model(cls: type) -> bool:
    """Check if a type is a Pandera DataFrameModel subclass.

    Returns False if pandera is not installed.
    """
    try:
        import inspect

        import pandera as pa

        return inspect.isclass(cls) and issubclass(cls, pa.DataFrameModel)
    except ImportError:
        return False


def validate_dataframe(dataset_name: str, data: Any, schema_class: type) -> Any:
    """Validate a DataFrame against a Pandera DataFrameModel schema.

    Args:
        dataset_name: Name of the dataset being validated (for error messages).
        data: The data to validate (expected to be a DataFrame).
        schema_class: A Pandera DataFrameModel subclass to validate against.

    Returns:
        The validated data if valid, or the original data unchanged if
        ``schema_class`` is not a Pandera DataFrameModel.

    Raises:
        DataValidationError: If validation fails.
    """
    if not _is_pandera_model(schema_class):
        logger.debug(
            "Schema class %s is not a Pandera DataFrameModel, skipping validation "
            "for dataset '%s'",
            getattr(schema_class, "__name__", repr(schema_class)),
            dataset_name,
        )
        return data

    try:
        validated = schema_class.validate(data, lazy=True)
        logger.debug(
            "Dataset '%s' passed validation against %s",
            dataset_name,
            schema_class.__name__,
        )
        return validated
    except Exception as exc:
        raise DataValidationError(
            f"Dataset '{dataset_name}' failed validation against "
            f"{schema_class.__name__}: {exc}"
        ) from exc


class _ValidatingDataset:
    """Wraps an existing catalog dataset to add Pandera validation on load.

    When ``load()`` is called, the data is first loaded from the wrapped
    dataset and then validated against the given Pandera ``DataFrameModel``
    schema.  All other attribute access is delegated to the wrapped dataset.
    """

    def __init__(
        self,
        wrapped_dataset: AbstractDataset,
        schema_class: type,
        dataset_name: str,
    ) -> None:
        self._wrapped = wrapped_dataset
        self._schema_class = schema_class
        self._dataset_name = dataset_name

    def load(self) -> Any:
        data = self._wrapped.load()
        return validate_dataframe(self._dataset_name, data, self._schema_class)

    def save(self, data: Any) -> None:
        self._wrapped.save(data)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)
