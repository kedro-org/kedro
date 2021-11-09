"""``AppendableExcelDataSet`` loads/saves data from/to a local Excel file opened in append mode.
It uses pandas to handle the Excel file.
"""
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Dict

import pandas as pd

from kedro.io.core import AbstractDataSet, DataSetError


class AppendableExcelDataSet(AbstractDataSet):
    """``AppendableExcelDataSet`` loads/saves data from/to a local Excel file opened in
    append mode. It uses pandas to handle the Excel file.

    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/05_data/\
        01_data_catalog.html#using-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> # AppendableExcelDataSet creates a new sheet for every dataset
        >>> # ExcelDataSet restricts one dataset per file as it is overwritten
        >>>
        >>> preprocessed_companies:
        >>>   type: pandas.AppendableExcelDataSet
        >>>   filepath: data/02_intermediate/preprocessed.xlsx # assumes file already exists
        >>>   save_args:
        >>>     sheet_name: preprocessed_companies
        >>>   load_args:
        >>>     sheet_name: preprocessed_companies
        >>>
        >>> preprocessed_shuttles:
        >>>   type: pandas.AppendableExcelDataSet
        >>>   filepath: data/02_intermediate/preprocessed.xlsx
        >>>   save_args:
        >>>     sheet_name: preprocessed_shuttles
        >>>   load_args:
        >>>     sheet_name: preprocessed_shuttles

    Example using Python API:
    ::

        >>> from kedro.extras.datasets.pandas import AppendableExcelDataSet
        >>> from kedro.extras.datasets.pandas import ExcelDataSet
        >>> import pandas as pd
        >>>
        >>> data_1 = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> data_2 = pd.DataFrame({'col1': [7, 8], 'col2': [5, 7]})
        >>>
        >>> regular_ds = ExcelDataSet(filepath="/tmp/test.xlsx")
        >>> appendable_ds = AppendableExcelDataSet(
        >>>     filepath="/tmp/test.xlsx",
        >>>     save_args={"sheet_name": "my_sheet"},
        >>>     load_args={"sheet_name": "my_sheet"}
        >>> )
        >>>
        >>> regular_ds.save(data_1)
        >>> appendable_ds.save(data_2)
        >>> reloaded = appendable_ds.load()
        >>> assert data_2.equals(reloaded)

    """

    DEFAULT_LOAD_ARGS = {"engine": "openpyxl"}
    DEFAULT_SAVE_ARGS = {"index": False}

    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``AppendableExcelDataSet`` pointing to an existing local
        Excel file to be opened in append mode.

        Args:
            filepath: Filepath in POSIX format to an existing local Excel file.
            load_args: Pandas options for loading Excel files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_excel.html
                All defaults are preserved, but "engine", which is set to "openpyxl".
            save_args: Pandas options for saving Excel files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_excel.html
                All defaults are preserved, but "index", which is set to False.
                If you would like to specify options for the `ExcelWriter`,
                you can include them under "writer" key. Here you can
                find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.ExcelWriter.html
                Note: `mode` option of `ExcelWriter` is set to `a` and it can not be overridden.
        """
        self._filepath = PurePosixPath(filepath)

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)

        save_args = deepcopy(save_args) or {}
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        self._writer_args = save_args.pop("writer", {})  # type: Dict[str, Any]
        self._writer_args.setdefault("engine", "openpyxl")
        if save_args is not None:
            self._save_args.update(save_args)

        # Use only append mode
        self._writer_args["mode"] = "a"

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
            writer_args=self._writer_args,
        )

    def _load(self) -> pd.DataFrame:
        return pd.read_excel(str(self._filepath), **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        # pylint: disable=abstract-class-instantiated
        try:
            with pd.ExcelWriter(str(self._filepath), **self._writer_args) as writer:
                data.to_excel(writer, **self._save_args)
        except FileNotFoundError as exc:
            raise DataSetError(
                f"`{self._filepath}` Excel file not found. The file cannot be opened in "
                f"append mode."
            ) from exc

    def _exists(self) -> bool:
        return Path(self._filepath.as_posix()).is_file()
