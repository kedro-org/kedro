# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

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

    Example:
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
