"""``MetricsDataSet`` saves data to a JSON file using an underlying
filesystem (e.g.: local, S3, GCS). It uses native json to handle the JSON file.
The ``MetricsDataSet`` is part of Kedro Experiment Tracking. The dataset is versioned by default
and only takes metrics of numeric values.
"""
import json
from typing import Dict

from kedro.extras.datasets.json import JSONDataSet
from kedro.io.core import DataSetError, get_filepath_str


class MetricsDataSet(JSONDataSet):
    """``MetricsDataSet`` saves data to a JSON file using an underlying
    filesystem (e.g.: local, S3, GCS). It uses native json to handle the JSON file.
    The ``MetricsDataSet`` is part of Kedro Experiment Tracking. The dataset is versioned by default
    and only takes metrics of numeric values.

        Example:
        ::

        >>> from kedro.extras.datasets.tracking import MetricsDataSet
        >>>
        >>> data = {'col1': 1, 'col2': 0.23, 'col3': 0.002}
        >>>
        >>> # data_set = MetricsDataSet(filepath="gcs://bucket/test.json")
        >>> data_set = MetricsDataSet(filepath="test.json")
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data == reloaded

    """

    versioned = True

    def _load(self) -> Dict:
        raise DataSetError(f"Loading not supported for `{self.__class__.__name__}`")

    def _save(self, data: Dict[str, float]) -> None:
        """Converts all values in the data from a ``MetricsDataSet`` to float to make sure
        they are numeric values which can be displayed in Kedro Viz and then saves the dataset.
        """
        try:
            for key, value in data.items():
                data[key] = float(value)
        except ValueError as exc:
            raise DataSetError(
                f"The MetricsDataSet expects only numeric values. {exc}"
            ) from exc

        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        with self._fs.open(save_path, **self._fs_open_args_save) as fs_file:
            json.dump(data, fs_file, **self._save_args)

        self._invalidate_cache()
