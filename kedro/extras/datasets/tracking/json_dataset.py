"""``JSONDataSet`` saves data to a JSON file using an underlying
filesystem (e.g.: local, S3, GCS). It uses native json to handle the JSON file.
The ``JSONDataSet`` is part of Kedro Experiment Tracking. The dataset is versioned by default.
"""
from typing import Dict

from kedro.extras.datasets.json import JSONDataSet as JDS
from kedro.io.core import DataSetError


class JSONDataSet(JDS):
    """``JSONDataSet`` saves data to a JSON file using an underlying
    filesystem (e.g.: local, S3, GCS). It uses native json to handle the JSON file.
    The ``JSONDataSet`` is part of Kedro Experiment Tracking.
    The dataset is versioned by default.

        Example:
        ::

        >>> from kedro.extras.datasets.tracking import JSONDataSet
        >>>
        >>> data = {'col1': 1, 'col2': 0.23, 'col3': 0.002}
        >>>
        >>> # data_set = JSONDataSet(filepath="gcs://bucket/test.json")
        >>> data_set = JSONDataSet(filepath="test.json")
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data == reloaded

    """

    versioned = True

    def _load(self) -> Dict:
        raise DataSetError(f"Loading not supported for `{self.__class__.__name__}`")
