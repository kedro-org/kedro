"""``PickleDataSet`` loads/saves data from/to a Pickle file using an underlying
filesystem (e.g.: local, S3, GCS). The underlying functionality is supported by
the specified backend library passed in (defaults to the ``pickle`` library), so it
supports all allowed options for loading and saving pickle files.
"""
import importlib
from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any, Dict

import fsspec

from kedro.io.core import (
    AbstractVersionedDataSet,
    DataSetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)


class PickleDataSet(AbstractVersionedDataSet):
    """``PickleDataSet`` loads/saves data from/to a Pickle file using an underlying
    filesystem (e.g.: local, S3, GCS). The underlying functionality is supported by
    the specified backend library passed in (defaults to the ``pickle`` library), so it
    supports all allowed options for loading and saving pickle files.

    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/05_data/\
        01_data_catalog.html#using-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> test_model: # simple example without compression
        >>>   type: pickle.PickleDataSet
        >>>   filepath: data/07_model_output/test_model.pkl
        >>>   backend: pickle
        >>>
        >>> final_model: # example with load and save args
        >>>   type: pickle.PickleDataSet
        >>>   filepath: s3://your_bucket/final_model.pkl.lz4
        >>>   backend: joblib
        >>>   credentials: s3_credentials
        >>>   save_args:
        >>>     compression: lz4
        >>>   load_args:
        >>>     compression: lz4

    Example using Python API:
    ::

        >>> from kedro.extras.datasets.pickle import PickleDataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> # data_set = PickleDataSet(filepath="gcs://bucket/test.pkl")
        >>> data_set = PickleDataSet(filepath="test.pkl", backend="pickle")
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data.equals(reloaded)
        >>>
        >>> # Add "compress_pickle[lz4]" to requirements.txt
        >>> data_set = PickleDataSet(filepath="test.pickle.lz4",
        >>>                          backend="compress_pickle",
        >>>                          load_args={"compression":"lz4"},
        >>>                          save_args={"compression":"lz4"})
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data.equals(reloaded)
    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(
        self,
        filepath: str,
        backend: str = "pickle",
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``PickleDataSet`` pointing to a concrete Pickle
        file on a specific filesystem. ``PickleDataSet`` supports custom backends to
        serialize/deserialize objects.

        Example backends that are compatible (non-exhaustive):
            * `pickle`
            * `joblib`
            * `dill`
            * `compress_pickle`

        Example backends that are incompatible:
            * `torch`

        Args:
            filepath: Filepath in POSIX format to a Pickle file prefixed with a protocol like
                `s3://`. If prefix is not provided, `file` protocol (local filesystem) will be used.
                The prefix should be any protocol supported by ``fsspec``.
                Note: `http(s)` doesn't support versioning.
            backend: Backend to use, must be an import path to a module which satisfies the
                ``pickle`` interface. That is, contains a `load` and `dump` function.
                Defaults to 'pickle'.
            load_args: Pickle options for loading pickle files.
                You can pass in arguments that the backend load function specified accepts, e.g:
                pickle.load: https://docs.python.org/3/library/pickle.html#pickle.load
                joblib.load: https://joblib.readthedocs.io/en/latest/generated/joblib.load.html
                dill.load: https://dill.readthedocs.io/en/latest/dill.html#dill._dill.load
                compress_pickle.load:
                https://lucianopaz.github.io/compress_pickle/html/api/compress_pickle.html#compress_pickle.compress_pickle.load
                All defaults are preserved.
            save_args: Pickle options for saving pickle files.
                You can pass in arguments that the backend dump function specified accepts, e.g:
                pickle.dump: https://docs.python.org/3/library/pickle.html#pickle.dump
                joblib.dump: https://joblib.readthedocs.io/en/latest/generated/joblib.dump.html
                dill.dump: https://dill.readthedocs.io/en/latest/dill.html#dill._dill.dump
                compress_pickle.dump:
                https://lucianopaz.github.io/compress_pickle/html/api/compress_pickle.html#compress_pickle.compress_pickle.dump
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
                All defaults are preserved, except `mode`, which is set to `wb` when saving.

        Raises:
            ValueError: If ``backend`` does not satisfy the `pickle` interface.
            ImportError: If the ``backend`` module could not be imported.
        """
        try:
            imported_backend = importlib.import_module(backend)
        except ImportError as exc:
            raise ImportError(
                f"Selected backend '{backend}' could not be imported. "
                "Make sure it is installed and importable."
            ) from exc

        if not (
            hasattr(imported_backend, "load") and hasattr(imported_backend, "dump")
        ):
            raise ValueError(
                f"Selected backend '{backend}' should satisfy the pickle interface. "
                "Missing one of `load` and `dump` on the backend."
            )

        _fs_args = deepcopy(fs_args) or {}
        _fs_open_args_load = _fs_args.pop("open_args_load", {})
        _fs_open_args_save = _fs_args.pop("open_args_save", {})
        _credentials = deepcopy(credentials) or {}

        protocol, path = get_protocol_and_path(filepath, version)
        if protocol == "file":
            _fs_args.setdefault("auto_mkdir", True)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        self._backend = imported_backend

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        _fs_open_args_save.setdefault("mode", "wb")
        self._fs_open_args_load = _fs_open_args_load
        self._fs_open_args_save = _fs_open_args_save

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            backend=self._backend,
            protocol=self._protocol,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _load(self) -> Any:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        with self._fs.open(load_path, **self._fs_open_args_load) as fs_file:
            return self._backend.load(fs_file, **self._load_args)  # type: ignore

    def _save(self, data: Any) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        with self._fs.open(save_path, **self._fs_open_args_save) as fs_file:
            try:
                self._backend.dump(data, fs_file, **self._save_args)  # type: ignore
            except Exception as exc:
                raise DataSetError(
                    f"{data.__class__} was not serialized due to: {exc}"
                ) from exc

        self._invalidate_cache()

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DataSetError:
            return False

        return self._fs.exists(load_path)

    def _release(self) -> None:
        super()._release()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate underlying filesystem caches."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
