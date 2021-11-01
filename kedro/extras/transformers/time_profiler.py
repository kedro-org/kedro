"""``Transformers`` modify the loading and saving of ``DataSets`` in a
``DataCatalog``.
"""

import logging
import time
from typing import Any, Callable

from kedro.io import AbstractTransformer


class ProfileTimeTransformer(AbstractTransformer):
    """A transformer that logs the runtime of data set load and save calls."""

    @property
    def _logger(self):
        return logging.getLogger("ProfileTimeTransformer")

    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        start = time.time()
        data = load()
        self._logger.info(
            "Loading %s took %0.3f seconds", data_set_name, time.time() - start
        )
        return data

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        start = time.time()
        save(data)
        self._logger.info(
            "Saving %s took %0.3f seconds", data_set_name, time.time() - start
        )
