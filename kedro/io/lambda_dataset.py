"""``LambdaDataset`` is an implementation of ``AbstractDataset`` which allows for
providing custom load, save, and exists methods without extending
``AbstractDataset``.
"""

from __future__ import annotations

import warnings
from typing import Any, Callable

from kedro import KedroDeprecationWarning
from kedro.io.core import AbstractDataset, DatasetError


class LambdaDataset(AbstractDataset):
    """``LambdaDataset`` loads and saves data to a dataset.
    It relies on delegating to specific implementation such as csv, sql, etc.

    ``LambdaDataset`` class captures Exceptions while performing operations on
    composed ``Dataset`` implementations. The composed dataset is
    responsible for providing information on how to resolve the issue when
    possible. This information should be available through str(error).

    Example:
    ::

        >>> from kedro.io import LambdaDataset
        >>> import pandas as pd
        >>>
        >>> file_name = "test.csv"
        >>> def load() -> pd.DataFrame:
        >>>     raise FileNotFoundError("'{}' csv file not found."
        >>>                             .format(file_name))
        >>> dataset = LambdaDataset(load, None)
    """

    def _describe(self) -> dict[str, Any]:
        def _to_str(func: Any) -> str | None:
            if not func:
                return None
            try:
                return f"<{func.__module__}.{func.__name__}>"
            except AttributeError:  # pragma: no cover
                return str(func)

        descr = {
            "load": _to_str(self.__load),
            "save": _to_str(self.__save),
            "exists": _to_str(self.__exists),
            "release": _to_str(self.__release),
        }

        return descr

    def _load(self) -> Any:
        if not self.__load:
            raise DatasetError(
                "Cannot load dataset. No 'load' function "
                "provided when LambdaDataset was created."
            )
        return self.__load()

    def _save(self, data: Any) -> None:
        if not self.__save:
            raise DatasetError(
                "Cannot save to dataset. No 'save' function "
                "provided when LambdaDataset was created."
            )
        self.__save(data)

    def _exists(self) -> bool:
        if not self.__exists:
            return super()._exists()
        return self.__exists()

    def _release(self) -> None:
        if not self.__release:
            super()._release()
        else:
            self.__release()

    def __init__(
        self,
        load: Callable[[], Any] | None,
        save: Callable[[Any], None] | None,
        exists: Callable[[], bool] | None = None,
        release: Callable[[], None] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Creates a new instance of ``LambdaDataset`` with references to the
        required input/output dataset methods.

        Args:
            load: Method to load data from a dataset.
            save: Method to save data to a dataset.
            exists: Method to check whether output data already exists.
            release: Method to release any cached information.
            metadata: Any arbitrary metadata.
                This is ignored by Kedro, but may be consumed by users or external plugins.

        Raises:
            DatasetError: If a method is specified, but is not a Callable.

        """

        warnings.warn(
            "`LambdaDataset` has been deprecated and will be removed in Kedro 1.0.0.",
            KedroDeprecationWarning,
        )

        for name, value in [
            ("load", load),
            ("save", save),
            ("exists", exists),
            ("release", release),
        ]:
            if value is not None and not callable(value):
                raise DatasetError(
                    f"'{name}' function for LambdaDataset must be a Callable. "
                    f"Object of type '{value.__class__.__name__}' provided instead."
                )

        self.__load = load
        self.__save = save
        self.__exists = exists
        self.__release = release
        self.metadata = metadata
