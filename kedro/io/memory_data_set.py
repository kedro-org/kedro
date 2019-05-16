# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""``MemoryDataSet`` is a data set implementation which handles in-memory data.
"""

import copy
from typing import Any, Dict

import numpy as np
import pandas as pd

from kedro.io.core import AbstractDataSet, DataSetError, ExistsMixin


class MemoryDataSet(AbstractDataSet, ExistsMixin):
    """``MemoryDataSet`` loads and saves data from/to an in-memory\
    Python object.

    Example:
    ::

        >>> from kedro.io import MemoryDataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>> data_set = MemoryDataSet(data=data)
        >>>
        >>> loaded_data = data_set.load()
        >>> assert loaded_data.equals(data)
        >>>
        >>> new_data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5]})
        >>> data_set.save(new_data)
        >>> reloaded_data = data_set.load()
        >>> assert reloaded_data.equals(new_data)

    """

    def _describe(self) -> Dict[str, Any]:
        if self._data is not None:
            return dict(data="<{}>".format(type(self._data).__name__))
        return dict(data=None)  # pragma: no cover

    def __init__(self, data: Any = None, max_loads: int = None):
        """Creates a new instance of ``MemoryDataSet`` pointing to the
        provided Python object.

        Args:
            data: Python object containing the data.
            max_loads: Maximum number of times ``load`` method can be invoked.
                ``MemoryDataSet`` data is reset after this number of calls is
                made. Any number of calls is allowed if the argument is not
                set. ``max_loads`` counter is reset after every ``save``
                method call.

        """
        self._data = None
        self._max_loads = max_loads
        if data is not None:
            self._save(data)

    def _load(self) -> Any:
        if self._data is None:
            if self._max_loads is None:
                message = "Data for MemoryDataSet has not been saved yet."
            else:
                message = (
                    "Maximum number of MemoryDataSet loads exceeded "
                    "the threshold of {}. The data set was cleared "
                    "and holds no data now.".format(self._max_loads)
                )
            raise DataSetError(message)
        if isinstance(self._data, (pd.DataFrame, np.ndarray)):
            data = self._data.copy()
        elif type(self._data).__name__ == "DataFrame":
            data = self._data
        else:
            data = copy.deepcopy(self._data)
        if self._load_counter:
            self._load_counter -= 1
            if self._load_counter == 0:
                self._data = None
        return data

    def _save(self, data: Any):
        if isinstance(data, (pd.DataFrame, np.ndarray)):
            self._data = data.copy()
        elif type(data).__name__ == "DataFrame":
            self._data = data
        else:
            self._data = copy.deepcopy(data)
        self._load_counter = self._max_loads

    def _exists(self) -> bool:
        if self._data is None:
            return False
        return True
