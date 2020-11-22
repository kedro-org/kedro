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

"""``AVRODataSet`` loads/saves data from/to a AVRO file using an underlying
filesystem (e.g.: local, S3, GCS). It uses avro library to handle the AVRO file.
See details about AVRO format: https://avro.apache.org/
"""
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Union

# pylint: disable=import-error
import fsspec  # type: ignore
from avro.datafile import DataFileReader, DataFileWriter  # type: ignore
from avro.io import DatumReader, DatumWriter  # type: ignore
from avro.schema import make_avsc_object  # type: ignore

from kedro.io.core import (  # type: ignore
    AbstractVersionedDataSet,
    DataSetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)


class AVRODataSet(AbstractVersionedDataSet):
    """``AVRODataSet`` loads/saves data from/to an AVRO file using an underlying
    filesystem (e.g.: local, S3, GCS). It uses avro library to handle the AVRO file.

    Example:
    ::

        >>> from kedro.extras.datasets.avro import AVRODataSet
        >>>
        >>> data = [
        >>>     {'col1': 1, 'col2': 3, 'col3': 5},
        >>>     {'col1': 2, 'col2': 4, 'col3': 6},
        >>> ]
        >>>
        >>> schema = {
        >>>     "namespace": "example.avro",
        >>>     "type": "array",
        >>>     "name": "DataArray",
        >>>     "items": {
        >>>         "type": "record",
        >>>         "name": "DataElement",
        >>>         "fields": [
        >>>             {"name": "col1", "type": "int"},
        >>>             {"name": "col2", "type": "int"},
        >>>             {"name": "col3", "type": "int"},
        >>>         ],
        >>>     },
        >>> }
        >>>
        >>> save_ops = {"schema": schema}
        >>>
        >>> # data_set = AVRODataSet(filepath="gcs://bucket/test.avro", save_args=save_ops)
        >>> data_set = AVRODataSet(filepath="test.csv", save_args=save_ops)
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data == reloaded

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``AVRODataSet`` pointing to a concrete AVRO file
        on a specific filesystem.

        Args:
            filepath: Filepath in POSIX format to AVRO file prefixed with a protocol like `s3://`.
                If prefix is not provided, `file` protocol (local filesystem) will be used.
                The prefix should be any protocol supported by ``fsspec``.
                Note: `http(s)` doesn't support versioning.
            load_args: Options for loading AVRO files.
                Here you can find the details:
                https://avro.apache.org/docs/current/
                All defaults are preserved.
            save_args: Options for saving AVRO files.
                Attention! The `schema` attribute MUST be set to save a file.
                See details about AVRO schema here:
                https://avro.apache.org/docs/current/spec.html#schemas
                Here you can find the details:
                https://avro.apache.org/docs/current/
                All defaults are preserved.
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``), as well as
                to pass to the filesystem's `open` method through nested keys
                `open_args_load` and `open_args_save`.
                Here you can find all available arguments for `open`:
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.open
                All defaults are preserved, except `mode`, which is set to `r` when loading
                and to `w` when saving.
        """
        _credentials = deepcopy(credentials) or {}
        _fs_args = deepcopy(fs_args) or {}

        self._fs_open_args_load = _fs_args.pop("open_args_load", {})
        self._fs_open_args_load.setdefault("mode", "rb")

        self._fs_open_args_save = _fs_args.pop("open_args_save", {})
        self._fs_open_args_save.setdefault("mode", "wb")

        protocol, path = get_protocol_and_path(filepath, version)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args:
            self._save_args.update(save_args)

        self._schema = save_args.get("schema", {}) if save_args else {}

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            protocol=self._protocol,
            schema=self._schema,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _load(self) -> List[Dict[str, Any]]:  # type: ignore
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        with self._fs.open(load_path, **self._fs_open_args_load) as fs_file:
            with DataFileReader(fs_file, DatumReader()) as reader:
                self._schema = reader.schema
                for item in reader:
                    return item

    def _save(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        if not self._save_args.get("schema", {}) or not self._schema:
            raise KeyError("Please provide AVRO schema as the save_args' 'schema' attribute")

        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        if Path(save_path).is_dir():
            raise DataSetError(
                f"Saving {self.__class__.__name__} to a directory is not supported."
            )

        schema = make_avsc_object(self._schema)
        codec = self._save_args.get("codec", "null")

        with self._fs.open(save_path, **self._fs_open_args_save) as fs_file:
            with DataFileWriter(fs_file, DatumWriter(), schema, codec) as writer:
                writer.append(data)

        self._invalidate_cache()

    def _exists(self) -> bool:  # type: ignore
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DataSetError:
            return False

    def _release(self) -> None:
        super()._release()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate underlying filesystem caches."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
