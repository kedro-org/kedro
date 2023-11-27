"""``MemoryDataset`` is a data set implementation which handles in-memory data.
"""
from __future__ import annotations

import copy
from typing import Any

from kedro.io.core import AbstractDataset, DatasetError

_EMPTY = object()


class MemoryDataset(AbstractDataset):
    """``MemoryDataset`` loads and saves data from/to an in-memory
    Python object.

    Example:
    ::

        >>> from kedro.io import MemoryDataset
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>> dataset = MemoryDataset(data=data)
        >>>
        >>> loaded_data = dataset.load()
        >>> assert loaded_data.equals(data)
        >>>
        >>> new_data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5]})
        >>> dataset.save(new_data)
        >>> reloaded_data = dataset.load()
        >>> assert reloaded_data.equals(new_data)

    """

    def __init__(
        self, data: Any = _EMPTY, copy_mode: str = None, metadata: dict[str, Any] = None
    ):
        """Creates a new instance of ``MemoryDataset`` pointing to the
        provided Python object.

        Args:
            data: Python object containing the data.
            copy_mode: The copy mode used to copy the data. Possible
                values are: "deepcopy", "copy" and "assign". If not
                provided, it is inferred based on the data type.
            metadata: Any arbitrary metadata.
                This is ignored by Kedro, but may be consumed by users or external plugins.
        """
        self._data = _EMPTY
        self._copy_mode = copy_mode
        self.metadata = metadata
        if data is not _EMPTY:
            self._save(data)

    def _load(self) -> Any:
        if self._data is _EMPTY:
            raise DatasetError("Data for MemoryDataset has not been saved yet.")

        copy_mode = self._copy_mode or _infer_copy_mode(self._data)
        data = _copy_with_mode(self._data, copy_mode=copy_mode)
        return data

    def _save(self, data: Any):
        copy_mode = self._copy_mode or _infer_copy_mode(data)
        self._data = _copy_with_mode(data, copy_mode=copy_mode)

    def _exists(self) -> bool:
        return self._data is not _EMPTY

    def _release(self) -> None:
        self._data = _EMPTY

    def _describe(self) -> dict[str, Any]:
        if self._data is not _EMPTY:
            return {"data": f"<{type(self._data).__name__}>"}
        # the string representation of datasets leaves out __init__
        # arguments that are empty/None, equivalent here is _EMPTY
        return {"data": None}  # pragma: no cover


def _infer_copy_mode(data: Any) -> str:
    """Infers the copy mode to use given the data type.

    Args:
        data: The data whose type will be used to infer the copy mode.

    Returns:
        One of "copy", "assign" or "deepcopy" as the copy mode to use.
    """
    # noqa: import-outside-toplevel
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        pd = None  # pragma: no cover
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        np = None  # pragma: no cover

    if pd and isinstance(data, pd.DataFrame) or np and isinstance(data, np.ndarray):
        copy_mode = "copy"
    elif type(data).__name__ == "DataFrame":
        copy_mode = "assign"
    else:
        copy_mode = "deepcopy"
    return copy_mode


def _copy_with_mode(data: Any, copy_mode: str) -> Any:
    """Returns the copied data using the copy mode specified.
    If no copy mode is provided, then it is inferred based on the type of the data.

    Args:
        data: The data to copy.
        copy_mode: The copy mode to use, one of "deepcopy", "copy" and "assign".

    Raises:
        DatasetError: If copy_mode is specified, but isn't valid
            (i.e: not one of deepcopy, copy, assign)

    Returns:
        The data copied according to the specified copy mode.
    """
    if copy_mode == "deepcopy":
        copied_data = copy.deepcopy(data)
    elif copy_mode == "copy":
        copied_data = data.copy()
    elif copy_mode == "assign":
        copied_data = data
    else:
        raise DatasetError(
            f"Invalid copy mode: {copy_mode}. "
            f"Possible values are: deepcopy, copy, assign."
        )

    return copied_data
