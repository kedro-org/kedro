"""``JSONDataSet`` saves data to a JSON file using an underlying
filesystem (e.g.: local, S3, GCS). It uses native json to handle the JSON file.
The ``JSONDataSet`` is part of Kedro Experiment Tracking. The dataset is versioned by default.
"""
from typing import NoReturn

from kedro.extras.datasets.json import JSONDataSet as JDS
from kedro.io.core import DatasetError

# NOTE: kedro.extras.datasets will be removed in Kedro 0.19.0.
# Any contribution to datasets should be made in kedro-datasets
# in kedro-plugins (https://github.com/kedro-org/kedro-plugins)


class JSONDataSet(JDS):
    """``JSONDataSet`` saves data to a JSON file using an underlying
    filesystem (e.g.: local, S3, GCS). It uses native json to handle the JSON file.
    The ``JSONDataSet`` is part of Kedro Experiment Tracking.
    The dataset is write-only and it is versioned by default.

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog_yaml_examples.html>`_:


    .. code-block:: yaml

        cars:
          type: tracking.JSONDataSet
          filepath: data/09_tracking/cars.json

    Example usage for the
    `Python API <https://kedro.readthedocs.io/en/stable/data/\
    advanced_data_catalog_usage.html>`_:
    ::

        >>> from kedro.extras.datasets.tracking import JSONDataSet
        >>>
        >>> data = {'col1': 1, 'col2': 0.23, 'col3': 0.002}
        >>>
        >>> data_set = JSONDataSet(filepath="test.json")
        >>> data_set.save(data)

    """

    versioned = True

    def _load(self) -> NoReturn:
        raise DatasetError(f"Loading not supported for '{self.__class__.__name__}'")
