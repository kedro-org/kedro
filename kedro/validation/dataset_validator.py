"""Deprecated import shim — contents moved as part of KEP-7 v2.

``DataValidationError`` now lives in ``kedro.validation.core`` and the pandera
model detection helper ``_is_pandera_model`` lives in
``kedro.validation.pandera_validator``. Import from those modules instead;
this shim only keeps existing imports working.

The previous ``validate_dataframe`` function and ``_ValidatingDataset``
wrapper have been removed: dataset validation is now declared in the catalog
via the ``validator:`` key and applied by the ``DataCatalog`` funnel.
"""

from kedro.validation.core import DataValidationError
from kedro.validation.pandera_validator import _is_pandera_model

__all__ = ["DataValidationError", "_is_pandera_model"]
