"""``LambdaDataSet`` is an implementation of ``AbstractDataSet`` which allows for
providing custom load, save, and exists methods without extending
``AbstractDataSet``.
"""
from typing import Any, Callable, Dict, Optional

from kedro.io.core import AbstractDataSet, DataSetError


class LambdaDataSet(AbstractDataSet):
    """``LambdaDataSet`` loads and saves data to a data set.
    It relies on delegating to specific implementation such as csv, sql, etc.

    ``LambdaDataSet`` class captures Exceptions while performing operations on
    composed ``DataSet`` implementations. The composed data set is
    responsible for providing information on how to resolve the issue when
    possible. This information should be available through str(error).

    Example:
    ::

        >>> from kedro.io import LambdaDataSet
        >>> import pandas as pd
        >>>
        >>> file_name = "test.csv"
        >>> def load() -> pd.DataFrame:
        >>>     raise FileNotFoundError("'{}' csv file not found."
        >>>                             .format(file_name))
        >>> data_set = LambdaDataSet(load, None)
    """

    def _describe(self) -> Dict[str, Any]:
        def _to_str(func):
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

    def _save(self, data: Any) -> None:
        if not self.__save:
            raise DataSetError(
                "Cannot save to data set. No `save` function "
                "provided when LambdaDataSet was created."
            )
        self.__save(data)

    def _load(self) -> Any:
        if not self.__load:
            raise DataSetError(
                "Cannot load data set. No `load` function "
                "provided when LambdaDataSet was created."
            )
        return self.__load()

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
        load: Optional[Callable[[], Any]],
        save: Optional[Callable[[Any], None]],
        exists: Callable[[], bool] = None,
        release: Callable[[], None] = None,
    ):
        """Creates a new instance of ``LambdaDataSet`` with references to the
        required input/output data set methods.

        Args:
            load: Method to load data from a data set.
            save: Method to save data to a data set.
            exists: Method to check whether output data already exists.
            release: Method to release any cached information.

        Raises:
            DataSetError: If a method is specified, but is not a Callable.

        """

        for name, value in [
            ("load", load),
            ("save", save),
            ("exists", exists),
            ("release", release),
        ]:
            if value is not None and not callable(value):
                raise DataSetError(
                    f"`{name}` function for LambdaDataSet must be a Callable. "
                    f"Object of type `{value.__class__.__name__}` provided instead."
                )

        self.__load = load
        self.__save = save
        self.__exists = exists
        self.__release = release
