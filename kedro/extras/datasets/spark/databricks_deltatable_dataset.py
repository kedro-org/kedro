"""Databricks specific DataSets"""
import logging
from typing import Any, Dict

from delta.tables import DeltaTable

from kedro.extras.datasets.spark import SparkDataSet
from kedro.io.core import Version

logger = logging.getLogger(__name__)


class DeltaTableDataset(SparkDataSet):
    """
    Schema validation: https://docs.databricks.com/delta/delta-batch.html#schema-validation-1
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        filepath: str,
        delta_options: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
    ) -> None:
        super().__init__(
            filepath=filepath,
            file_format="delta",
            load_args=load_args,
            save_args=save_args,
            version=version,
            credentials=credentials,
        )
        self._delta_options = delta_options

    def _load(self):
        load_path = self._fs_prefix + str(self._get_load_path())
        return DeltaTable.forPath(self._get_spark(), load_path)

    def _save(self, data: Any):
        pass  # TBD

    @staticmethod
    def confirm():
        logger.info(
            "Saving was performed on `DeltaTable` object within the context of the node function"
        )
