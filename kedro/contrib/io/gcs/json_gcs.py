from pathlib import PurePosixPath
from typing import Any, Dict, Optional

import gcsfs
import pandas as pd
from google.auth.credentials import Credentials

from kedro.io.core import AbstractVersionedDataSet, DataSetError, Version


class JsonGCSDataSet(AbstractVersionedDataSet):
    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"index": True}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        bucket_name: str,
        credentials: Optional[Credentials] = None,
        project: Optional[str] = None,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
        version: Version = None,
    ) -> None:
        _gcs = gcsfs.GCSFileSystem(credentials=credentials, project=project)

        super().__init__(
            PurePosixPath("{}/{}".format(bucket_name, filepath)),
            version,
            exists_function=_gcs.exists,
            glob_function=_gcs.glob,
        )
        self._bucket_name = bucket_name

        # Handle default load and save arguments
        load_args = {} if load_args is None else load_args
        save_args = {} if save_args is None else save_args

        self._load_args = {**self.DEFAULT_LOAD_ARGS, **load_args}
        self._save_args = {**self.DEFAULT_SAVE_ARGS, **save_args}

        self._gcs = _gcs

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            bucket_name=self._bucket_name,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _load(self) -> pd.DataFrame:
        load_path = PurePosixPath(self._get_load_path())
        with self._gcs.open(str(load_path), mode="rb") as gcs_file:
            return pd.read_json(gcs_file, **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        save_path = PurePosixPath(self._get_save_path())
        data = data.to_json(**self._save_args)

        with self._gcs.open(str(save_path), mode="wb") as gcs_file:
            gcs_file.write(data.encode("utf8"))

        # gcs maintain cache of the directory, so invalidate to
        # see new files
        self._gcs.invalidate_cache()
        load_path = PurePosixPath(self._get_load_path())
        self._check_paths_consistency(load_path, save_path)

    def _exists(self) -> bool:
        try:
            load_path = self._get_load_path()
        except DataSetError:
            return False

        return self._gcs.exists(load_path)
