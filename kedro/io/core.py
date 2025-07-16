"""This module provides a set of classes which underpin the data loading and
saving functionality provided by ``kedro.io``.
"""

from __future__ import annotations

import abc
import copy
import logging
import pprint
import sys
import warnings
from collections import namedtuple
from datetime import datetime, timezone
from functools import partial, wraps
from glob import iglob
from inspect import getcallargs
from operator import attrgetter
from pathlib import Path, PurePath, PurePosixPath
from typing import (  # noqa: UP035
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterator,
    List,
    Literal,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from cachetools import Cache, cachedmethod
from cachetools.keys import hashkey
from typing_extensions import Self

# These are re-exported for backward compatibility
from kedro.utils import (  # noqa: F401
    CLOUD_PROTOCOLS,
    HTTP_PROTOCOLS,
    _parse_filepath,
    load_obj,
)

if TYPE_CHECKING:
    import os
    from multiprocessing.managers import SyncManager


VERSION_FORMAT = "%Y-%m-%dT%H.%M.%S.%fZ"
VERSIONED_FLAG_KEY = "versioned"
VERSION_KEY = "version"
PROTOCOL_DELIMITER = "://"
TYPE_KEY = "type"

# Type alias for copy modes
TCopyMode = Literal["deepcopy", "copy", "assign"]


class DatasetError(Exception):
    """``DatasetError`` raised by ``AbstractDataset`` implementations
    in case of failure of input/output methods.

    ``AbstractDataset`` implementations should provide instructive
    information in case of failure.
    """

    pass


class DatasetNotFoundError(DatasetError):
    """``DatasetNotFoundError`` raised by ``DataCatalog``
    class in case of trying to use a non-existing dataset.
    """

    pass


class DatasetAlreadyExistsError(DatasetError):
    """``DatasetAlreadyExistsError`` raised by ``DataCatalog``
    class in case of trying to add a dataset which already exists in the ``DataCatalog``.
    """

    pass


class VersionNotFoundError(DatasetError):
    """``VersionNotFoundError`` raised by ``AbstractVersionedDataset`` implementations
    in case of no load versions available for the dataset.
    """

    pass


class VersionAlreadyExistsError(DatasetError):
    """``VersionAlreadyExistsError`` raised by ``DataCatalog``
    class when attempting to add a dataset to a catalog with a save version
    that conflicts with the save version already set for the catalog.
    """

    pass


_DI = TypeVar("_DI")
_DO = TypeVar("_DO")


class AbstractDataset(abc.ABC, Generic[_DI, _DO]):
    """``AbstractDataset`` is the base class for all dataset implementations.

    All dataset implementations should extend this abstract class
    and implement the methods marked as abstract.
    If a specific dataset implementation cannot be used in conjunction with
    the ``ParallelRunner``, such user-defined dataset should have the
    attribute `_SINGLE_PROCESS = True`.
    Example:
    ``` python
    from pathlib import Path, PurePosixPath
    import pandas as pd
    from kedro.io import AbstractDataset


    class MyOwnDataset(AbstractDataset[pd.DataFrame, pd.DataFrame]):
        def __init__(self, filepath, param1, param2=True):
            self._filepath = PurePosixPath(filepath)
            self._param1 = param1
            self._param2 = param2

        def load(self) -> pd.DataFrame:
            return pd.read_csv(self._filepath)

        def save(self, df: pd.DataFrame) -> None:
            df.to_csv(str(self._filepath))

        def _exists(self) -> bool:
            return Path(self._filepath.as_posix()).exists()

        def _describe(self):
            return dict(param1=self._param1, param2=self._param2)
    ```
    Example catalog.yml specification:
    ``` yaml
    my_dataset:
        type: <path-to-my-own-dataset>.MyOwnDataset
        filepath: data/01_raw/my_data.csv
        param1: <param1-value> # param1 is a required argument
        # param2 will be True by default
    ```
    """

    """
    Datasets are persistent by default. User-defined datasets that
    are not made to be persistent, such as instances of `MemoryDataset`,
    need to change the `_EPHEMERAL` attribute to 'True'.
    """
    _EPHEMERAL = False

    @classmethod
    def from_config(
        cls: type,
        name: str,
        config: dict[str, Any],
        load_version: str | None = None,
        save_version: str | None = None,
    ) -> AbstractDataset:
        """Create a dataset instance using the configuration provided.

        Args:
            name: Data set name.
            config: Data set config dictionary.
            load_version: Version string to be used for ``load`` operation if
                the dataset is versioned. Has no effect on the dataset
                if versioning was not enabled.
            save_version: Version string to be used for ``save`` operation if
                the dataset is versioned. Has no effect on the dataset
                if versioning was not enabled.

        Returns:
            An instance of an ``AbstractDataset`` subclass.

        Raises:
            DatasetError: When the function fails to create the dataset
                from its config.

        """
        try:
            class_obj, config = parse_dataset_definition(
                config, load_version, save_version
            )
        except Exception as exc:
            raise DatasetError(
                f"An exception occurred when parsing config "
                f"for dataset '{name}':\n{exc!s}"
            ) from exc

        try:
            dataset = class_obj(**config)
        except TypeError as err:
            raise DatasetError(
                f"\n{err}.\nDataset '{name}' must only contain arguments valid for the "
                f"constructor of '{class_obj.__module__}.{class_obj.__qualname__}'."
            ) from err
        except Exception as err:
            raise DatasetError(
                f"\n{err}.\nFailed to instantiate dataset '{name}' "
                f"of type '{class_obj.__module__}.{class_obj.__qualname__}'."
            ) from err
        return dataset

    def _init_config(self) -> dict[str, Any]:
        """Internal method to capture the dataset's initial configuration
        as provided during instantiation.

        This configuration reflects only the arguments supplied at `__init__` time
        and does not account for any runtime or dynamic changes to the dataset.

        Adds a key for the dataset's type using its module and class name and
        includes the initialization arguments.

        For `CachedDataset` it extracts the underlying dataset's configuration,
        handles the `versioned` flag and removes unnecessary metadata. It also
        ensures the embedded dataset's configuration is appropriately flattened
        or transformed.

        If the dataset has a version key, it sets the `versioned` flag in the
        configuration.

        Removes the `metadata` key from the configuration if present.

        Returns:
            A dictionary containing the dataset's type and initialization arguments.
        """
        return_config: dict[str, Any] = {
            f"{TYPE_KEY}": f"{type(self).__module__}.{type(self).__name__}"
        }

        if self._init_args:  # type: ignore[attr-defined]
            return_config.update(self._init_args)  # type: ignore[attr-defined]

        if type(self).__name__ == "CachedDataset":
            cached_ds = return_config.pop("dataset")
            cached_ds_return_config: dict[str, Any] = {}
            if isinstance(cached_ds, dict):
                cached_ds_return_config = cached_ds
            elif isinstance(cached_ds, AbstractDataset):
                cached_ds_return_config = cached_ds._init_config()
            if VERSIONED_FLAG_KEY in cached_ds_return_config:
                return_config[VERSIONED_FLAG_KEY] = cached_ds_return_config.pop(
                    VERSIONED_FLAG_KEY
                )
            # Pop metadata from configuration
            cached_ds_return_config.pop("metadata", None)
            return_config["dataset"] = cached_ds_return_config

        # Set `versioned` key if version present in the dataset
        if return_config.pop(VERSION_KEY, None):
            return_config[VERSIONED_FLAG_KEY] = True

        # Pop metadata from configuration
        return_config.pop("metadata", None)

        return return_config

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @classmethod
    def _load_wrapper(cls, load_func: Callable[[Self], _DO]) -> Callable[[Self], _DO]:
        """Decorate `load_func` with logging and error handling code."""

        @wraps(load_func)
        def load(self: Self) -> _DO:
            self._logger.debug("Loading %s", str(self))

            try:
                return load_func(self)
            except DatasetError:
                raise
            except Exception as exc:
                # This exception handling is by design as the composed datasets
                # can throw any type of exception.
                message = f"Failed while loading data from dataset {self!s}.\n{exc!s}"
                raise DatasetError(message) from exc

        load.__annotations__["return"] = load_func.__annotations__.get("return")
        load.__loadwrapped__ = True  # type: ignore[attr-defined]
        return load

    @classmethod
    def _save_wrapper(
        cls, save_func: Callable[[Self, _DI], None]
    ) -> Callable[[Self, _DI], None]:
        """Decorate `save_func` with logging and error handling code."""

        @wraps(save_func)
        def save(self: Self, data: _DI) -> None:
            if data is None:
                raise DatasetError("Saving 'None' to a 'Dataset' is not allowed")

            try:
                self._logger.debug("Saving %s", str(self))
                save_func(self, data)
            except (DatasetError, FileNotFoundError, NotADirectoryError):
                raise
            except Exception as exc:
                message = f"Failed while saving data to dataset {self!s}.\n{exc!s}"
                raise DatasetError(message) from exc

        save.__annotations__["data"] = save_func.__annotations__.get("data", Any)
        save.__annotations__["return"] = save_func.__annotations__.get("return")
        save.__savewrapped__ = True  # type: ignore[attr-defined]
        return save

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Customizes the behavior of subclasses of AbstractDataset during
        their creation. This method is automatically invoked when a subclass
        of AbstractDataset is defined.

        Decorates the `load` and `save` methods provided by the class.
        If `_load` or `_save` are defined, alias them as a prerequisite.
        """

        # Save the original __init__ method of the subclass
        init_func: Callable = cls.__init__

        @wraps(init_func)
        def new_init(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            """Executes the original __init__, then save the arguments used
            to initialize the instance.
            """
            # Call the original __init__ method
            init_func(self, *args, **kwargs)
            # Capture and save the arguments passed to the original __init__
            self._init_args = getcallargs(init_func, self, *args, **kwargs)
            self._init_args.pop("self", None)  # removed to prevent recursion

        # Replace the subclass's __init__ with the new_init
        # A hook for subclasses to capture initialization arguments and save them
        # in the AbstractDataset._init_args field
        cls.__init__ = new_init  # type: ignore[method-assign]

        super().__init_subclass__(**kwargs)

        if hasattr(cls, "_load") and not cls._load.__qualname__.startswith("Abstract"):
            cls.load = cls._load  # type: ignore[method-assign]

        if hasattr(cls, "_save") and not cls._save.__qualname__.startswith("Abstract"):
            cls.save = cls._save  # type: ignore[method-assign]

        if hasattr(cls, "load") and not cls.load.__qualname__.startswith("Abstract"):
            cls.load = cls._load_wrapper(  # type: ignore[assignment]
                cls.load
                if not getattr(cls.load, "__loadwrapped__", False)
                else cls.load.__wrapped__  # type: ignore[attr-defined]
            )

        if hasattr(cls, "save") and not cls.save.__qualname__.startswith("Abstract"):
            cls.save = cls._save_wrapper(  # type: ignore[assignment]
                cls.save
                if not getattr(cls.save, "__savewrapped__", False)
                else cls.save.__wrapped__  # type: ignore[attr-defined]
            )

    def _pretty_repr(self, object_description: dict[str, Any]) -> str:
        str_keys = []
        for arg_name, arg_descr in object_description.items():
            if arg_descr is not None:
                descr = pprint.pformat(
                    arg_descr,
                    sort_dicts=False,
                    compact=True,
                    depth=2,
                    width=sys.maxsize,
                )
                str_keys.append(f"{arg_name}={descr}")

        return f"{type(self).__module__}.{type(self).__name__}({', '.join(str_keys)})"

    def __repr__(self) -> str:
        object_description = self._describe()
        if isinstance(object_description, dict) and all(
            isinstance(key, str) for key in object_description
        ):
            return self._pretty_repr(object_description)

        self._logger.warning(
            f"'{type(self).__module__}.{type(self).__name__}' is a subclass of AbstractDataset and it must "
            f"implement the '_describe' method following the signature of AbstractDataset's '_describe'."
        )
        return f"{type(self).__module__}.{type(self).__name__}()"

    @abc.abstractmethod
    def load(self) -> _DO:
        """Loads data by delegation to the provided load method.

        Returns:
            Data returned by the provided load method.

        Raises:
            DatasetError: When underlying load method raises error.

        """
        raise NotImplementedError(
            f"'{self.__class__.__name__}' is a subclass of AbstractDataset and "
            f"it must implement the 'load' method"
        )

    @abc.abstractmethod
    def save(self, data: _DI) -> None:
        """Saves data by delegation to the provided save method.

        Args:
            data: the value to be saved by provided save method.

        Raises:
            DatasetError: when underlying save method raises error.
            FileNotFoundError: when save method got file instead of dir, on Windows.
            NotADirectoryError: when save method got file instead of dir, on Unix.

        """
        raise NotImplementedError(
            f"'{self.__class__.__name__}' is a subclass of AbstractDataset and "
            f"it must implement the 'save' method"
        )

    @abc.abstractmethod
    def _describe(self) -> dict[str, Any]:
        raise NotImplementedError(
            f"'{self.__class__.__name__}' is a subclass of AbstractDataset and "
            f"it must implement the '_describe' method"
        )

    def exists(self) -> bool:
        """Checks whether a dataset's output already exists by calling
        the provided _exists() method.

        Returns:
            Flag indicating whether the output already exists.

        Raises:
            DatasetError: when underlying exists method raises error.

        """
        try:
            self._logger.debug("Checking whether target of %s exists", str(self))
            return self._exists()
        except Exception as exc:
            message = f"Failed during exists check for dataset {self!s}.\n{exc!s}"
            raise DatasetError(message) from exc

    def _exists(self) -> bool:
        self._logger.warning(
            "'exists()' not implemented for '%s'. Assuming output does not exist.",
            self.__class__.__name__,
        )
        return False

    def release(self) -> None:
        """Release any cached data.

        Raises:
            DatasetError: when underlying release method raises error.

        """
        try:
            self._logger.debug("Releasing %s", str(self))
            self._release()
        except Exception as exc:
            message = f"Failed during release for dataset {self!s}.\n{exc!s}"
            raise DatasetError(message) from exc

    def _release(self) -> None:
        pass

    def _copy(self, **overwrite_params: Any) -> AbstractDataset:
        dataset_copy = copy.deepcopy(self)
        for name, value in overwrite_params.items():
            setattr(dataset_copy, name, value)
        return dataset_copy


def generate_timestamp() -> str:
    """Generate the timestamp to be used by versioning.

    Returns:
        String representation of the current timestamp.

    """
    current_ts = datetime.now(tz=timezone.utc).strftime(VERSION_FORMAT)
    return current_ts[:-4] + current_ts[-1:]  # Don't keep microseconds


class Version(namedtuple("Version", ["load", "save"])):
    """This namedtuple is used to provide load and save versions for versioned
    datasets. If ``Version.load`` is None, then the latest available version
    is loaded. If ``Version.save`` is None, then save version is formatted as
    YYYY-MM-DDThh.mm.ss.sssZ of the current timestamp.
    """

    __slots__ = ()


_CONSISTENCY_WARNING = (
    "Save version '{}' did not match load version '{}' for {}. This is strongly "
    "discouraged due to inconsistencies it may cause between 'save' and "
    "'load' operations. Please refrain from setting exact load version for "
    "intermediate datasets where possible to avoid this warning."
)

_DEFAULT_PACKAGES = ["kedro.io.", "kedro_datasets.", ""]


def parse_dataset_definition(
    config: dict[str, Any],
    load_version: str | None = None,
    save_version: str | None = None,
) -> tuple[type[AbstractDataset], dict[str, Any]]:
    """Parse and instantiate a dataset class using the configuration provided.

    Args:
        config: Data set config dictionary. It *must* contain the `type` key
            with fully qualified class name or the class object.
        load_version: Version string to be used for ``load`` operation if
            the dataset is versioned. Has no effect on the dataset
            if versioning was not enabled.
        save_version: Version string to be used for ``save`` operation if
            the dataset is versioned. Has no effect on the dataset
            if versioning was not enabled.

    Raises:
        DatasetError: If the function fails to parse the configuration provided.

    Returns:
        2-tuple: (Dataset class object, configuration dictionary)
    """
    save_version = save_version or generate_timestamp()
    config = copy.deepcopy(config)
    dataset_type = config.pop(TYPE_KEY)

    # This check prevents the use of dataset types with uppercase 'S' in 'Dataset',
    # which is no longer supported as of kedro-datasets 2.0
    if isinstance(dataset_type, str):
        if dataset_type.endswith("Set"):
            warnings.warn(
                f"Since kedro-datasets 2.0, 'Dataset' is spelled with a lowercase 's'. Got '{dataset_type}'.",
                UserWarning,
            )

    class_obj = None
    error_msg = None
    if isinstance(dataset_type, str):
        if len(dataset_type.strip(".")) != len(dataset_type):
            raise DatasetError(
                "'type' class path does not support relative "
                "paths or paths ending with a dot."
            )
        class_paths = (prefix + dataset_type for prefix in _DEFAULT_PACKAGES)

        for class_path in class_paths:
            tmp, error_msg = _load_obj(
                class_path
            )  # Load dataset class, capture the warning

            if tmp is not None:
                class_obj = tmp
                break

        if class_obj is None:  # If no valid class was found, raise an error
            hint = (
                "\nHint: If you are trying to use a dataset from `kedro-datasets`, "
                "make sure that the package is installed in your current environment. "
                "You can do so by running `pip install kedro-datasets` or "
                "`pip install kedro-datasets[<dataset-group>]` to install `kedro-datasets` along with "
                "related dependencies for the specific dataset group."
            )
            default_error_msg = f"Class '{dataset_type}' not found, is this a typo?"
            raise DatasetError(f"{error_msg if error_msg else default_error_msg}{hint}")

    if not class_obj:
        class_obj = dataset_type

    if not issubclass(class_obj, AbstractDataset):
        raise DatasetError(
            f"Dataset type '{class_obj.__module__}.{class_obj.__qualname__}' "
            f"is invalid: all dataset types must extend 'AbstractDataset'."
        )

    if VERSION_KEY in config:
        # remove "version" key so that it's not passed
        # to the "unversioned" dataset constructor
        message = (
            "'%s' attribute removed from dataset configuration since it is a "
            "reserved word and cannot be directly specified"
        )
        logging.getLogger(__name__).warning(message, VERSION_KEY)
        del config[VERSION_KEY]

    # dataset is either versioned explicitly by the user or versioned is set to true by default
    # on the dataset
    if config.pop(VERSIONED_FLAG_KEY, False) or getattr(
        class_obj, VERSIONED_FLAG_KEY, False
    ):
        config[VERSION_KEY] = Version(load_version, save_version)

    return class_obj, config


def _load_obj(class_path: str) -> tuple[Any | None, str | None]:
    """Try to load an object from a fully-qualified class path.

    Raises:
        DatasetError: If the class is listed in `__all__` but cannot be loaded,
        indicating missing dependencies.

    Returns:
        A tuple of (class object or None, error message or None).
    """
    mod_path, _, class_name = class_path.rpartition(".")
    # Check if the module exists
    try:
        available_classes = load_obj(f"{mod_path}.__all__")
        # ModuleNotFoundError: When `load_obj` can't find `mod_path` (e.g `kedro.io.pandas`)
        #                      this is because we try a combination of all prefixes.
        # AttributeError: When `load_obj` manages to load `mod_path` but it doesn't have an
        #                 `__all__` attribute -- either because it's a custom or a kedro.io dataset
    except (ModuleNotFoundError, AttributeError, ValueError):
        available_classes = None

    try:
        class_obj = load_obj(class_path)
    except ValueError as exc:
        return (
            None,
            f"{exc}. Invalid dataset path: '{class_path}'. Please check if it's correct.",
        )
    except AttributeError as exc:
        # Raise if class exists in __all__ but failed to load (likely due to missing deps)
        if available_classes and class_name in available_classes:
            raise DatasetError(
                f"{exc}. Please see the documentation on how to "
                f"install relevant dependencies for {class_path}:\n"
                f"https://docs.kedro.org/en/stable/kedro_project_setup/"
                f"dependencies.html#install-dependencies-related-to-the-data-catalog"
            ) from exc

        return (
            None,
            f"Dataset '{class_name}' not found in '{mod_path}'. "
            f"Make sure the dataset name is correct.",
        )
    except ModuleNotFoundError as exc:
        return (
            None,
            f"{exc}. Please install the missing dependencies for {class_path}:\n"
            f"https://docs.kedro.org/en/stable/kedro_project_setup/"
            f"dependencies.html#install-dependencies-related-to-the-data-catalog",
        )

    return class_obj, None


def _local_exists(filepath: str) -> bool:  # SKIP_IF_NO_SPARK
    return Path(filepath).exists()


class AbstractVersionedDataset(AbstractDataset[_DI, _DO], abc.ABC):
    """
    ``AbstractVersionedDataset`` is the base class for all versioned dataset
    implementations.

    All datasets that implement versioning should extend this
    abstract class and implement the methods marked as abstract.

    Example:
    ``` python
    from pathlib import Path, PurePosixPath
    import pandas as pd
    from kedro.io import AbstractVersionedDataset


    class MyOwnDataset(AbstractVersionedDataset):
        def __init__(self, filepath, version, param1, param2=True):
            super().__init__(PurePosixPath(filepath), version)
            self._param1 = param1
            self._param2 = param2

        def load(self) -> pd.DataFrame:
            load_path = self._get_load_path()
            return pd.read_csv(load_path)

        def save(self, df: pd.DataFrame) -> None:
            save_path = self._get_save_path()
            df.to_csv(str(save_path))

        def _exists(self) -> bool:
            path = self._get_load_path()
            return Path(path.as_posix()).exists()

        def _describe(self):
            return dict(version=self._version, param1=self._param1, param2=self._param2)
    ```

    Example catalog.yml specification:
    ``` yaml
    my_dataset:
        type: <path-to-my-own-dataset>.MyOwnDataset
        filepath: data/01_raw/my_data.csv
        versioned: true
        param1: <param1-value> # param1 is a required argument
        # param2 will be True by default
    ```
    """

    def __init__(
        self,
        filepath: PurePosixPath,
        version: Version | None,
        exists_function: Callable[[str], bool] | None = None,
        glob_function: Callable[[str], list[str]] | None = None,
    ):
        """Creates a new instance of ``AbstractVersionedDataset``.

        Args:
            filepath: Filepath in POSIX format to a file.
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
            exists_function: Function that is used for determining whether
                a path exists in a filesystem.
            glob_function: Function that is used for finding all paths
                in a filesystem, which match a given pattern.
        """
        self._filepath = filepath
        self._version = version
        self._exists_function = exists_function or _local_exists
        self._glob_function = glob_function or iglob
        # 1 entry for load version, 1 for save version
        self._version_cache = Cache(maxsize=2)  # type: Cache

    # 'key' is set to prevent cache key overlapping for load and save:
    # https://cachetools.readthedocs.io/en/stable/#cachetools.cachedmethod
    @cachedmethod(cache=attrgetter("_version_cache"), key=partial(hashkey, "load"))
    def _fetch_latest_load_version(self) -> str:
        # When load version is unpinned, fetch the most recent existing
        # version from the given path.
        pattern = str(self._get_versioned_path("*"))
        try:
            version_paths = sorted(self._glob_function(pattern), reverse=True)
        except Exception as exc:
            message = (
                f"Did not find any versions for {self}. This could be "
                f"due to insufficient permission. Exception: {exc}"
            )
            raise VersionNotFoundError(message) from exc
        most_recent = next(
            (path for path in version_paths if self._exists_function(path)), None
        )
        if not most_recent:
            message = f"Did not find any versions for {self}"
            raise VersionNotFoundError(message)
        return PurePath(most_recent).parent.name

    # 'key' is set to prevent cache key overlapping for load and save:
    # https://cachetools.readthedocs.io/en/stable/#cachetools.cachedmethod
    @cachedmethod(cache=attrgetter("_version_cache"), key=partial(hashkey, "save"))
    def _fetch_latest_save_version(self) -> str:
        """Generate and cache the current save version"""
        return generate_timestamp()

    def resolve_load_version(self) -> str | None:
        """Compute the version the dataset should be loaded with."""
        if not self._version:
            return None
        if self._version.load:
            return self._version.load  # type: ignore[no-any-return]
        return self._fetch_latest_load_version()

    def _get_load_path(self) -> PurePosixPath:
        if not self._version:
            # When versioning is disabled, load from original filepath
            return self._filepath

        load_version = self.resolve_load_version()
        return self._get_versioned_path(load_version)  # type: ignore[arg-type]

    def resolve_save_version(self) -> str | None:
        """Compute the version the dataset should be saved with."""
        if not self._version:
            return None
        if self._version.save:
            return self._version.save  # type: ignore[no-any-return]
        return self._fetch_latest_save_version()

    def _get_save_path(self) -> PurePosixPath:
        if not self._version:
            # When versioning is disabled, return original filepath
            return self._filepath

        save_version = self.resolve_save_version()
        versioned_path = self._get_versioned_path(save_version)  # type: ignore[arg-type]

        if self._exists_function(str(versioned_path)):
            raise DatasetError(
                f"Save path '{versioned_path}' for {self!s} must not exist if "
                f"versioning is enabled."
            )

        return versioned_path

    def _get_versioned_path(self, version: str) -> PurePosixPath:
        return self._filepath / version / self._filepath.name

    @classmethod
    def _save_wrapper(
        cls, save_func: Callable[[Self, _DI], None]
    ) -> Callable[[Self, _DI], None]:
        """Decorate `save_func` with logging and error handling code."""

        @wraps(save_func)
        def save(self: Self, data: _DI) -> None:
            self._version_cache.clear()
            save_version = (
                self.resolve_save_version()
            )  # Make sure last save version is set
            try:
                super()._save_wrapper(save_func)(self, data)
            except (FileNotFoundError, NotADirectoryError) as err:
                # FileNotFoundError raised in Win, NotADirectoryError raised in Unix
                _default_version = "YYYY-MM-DDThh.mm.ss.sssZ"
                raise DatasetError(
                    f"Cannot save versioned dataset '{self._filepath.name}' to "
                    f"'{self._filepath.parent.as_posix()}' because a file with the same "
                    f"name already exists in the directory. This is likely because "
                    f"versioning was enabled on a dataset already saved previously. Either "
                    f"remove '{self._filepath.name}' from the directory or manually "
                    f"convert it into a versioned dataset by placing it in a versioned "
                    f"directory (e.g. with default versioning format "
                    f"'{self._filepath.as_posix()}/{_default_version}/{self._filepath.name}"
                    f"')."
                ) from err

            load_version = self.resolve_load_version()
            if load_version != save_version:
                warnings.warn(
                    _CONSISTENCY_WARNING.format(save_version, load_version, str(self))
                )
                self._version_cache.clear()

        return save

    def exists(self) -> bool:
        """Checks whether a dataset's output already exists by calling
        the provided _exists() method.

        Returns:
            Flag indicating whether the output already exists.

        Raises:
            DatasetError: when underlying exists method raises error.

        """
        self._logger.debug("Checking whether target of %s exists", str(self))
        try:
            return self._exists()
        except VersionNotFoundError:
            return False
        except Exception as exc:  # SKIP_IF_NO_SPARK
            message = f"Failed during exists check for dataset {self!s}.\n{exc!s}"
            raise DatasetError(message) from exc

    def _release(self) -> None:
        super()._release()
        self._version_cache.clear()


def get_protocol_and_path(
    filepath: str | os.PathLike, version: Version | None = None
) -> tuple[str, str]:
    """Parses filepath on protocol and path.

    .. warning::
        Versioning is not supported for HTTP protocols.

    Args:
        filepath: raw filepath e.g.: ``gcs://bucket/test.json``.
        version: instance of ``kedro.io.core.Version`` or None.

    Returns:
        Protocol and path.

    Raises:
        DatasetError: when protocol is http(s) and version is not None.
    """
    options_dict = _parse_filepath(str(filepath))
    path = options_dict["path"]
    protocol = options_dict["protocol"]

    if protocol in HTTP_PROTOCOLS:
        if version is not None:
            raise DatasetError(
                "Versioning is not supported for HTTP protocols. "
                "Please remove the `versioned` flag from the dataset configuration."
            )
        path = path.split(PROTOCOL_DELIMITER, 1)[-1]

    return protocol, path


def get_filepath_str(raw_path: PurePath, protocol: str) -> str:
    """Returns filepath. Returns full filepath (with protocol) if protocol is HTTP(s).

    Args:
        raw_path: filepath without protocol.
        protocol: protocol.

    Returns:
        Filepath string.
    """
    path = raw_path.as_posix()
    if protocol in HTTP_PROTOCOLS:
        path = "".join((protocol, PROTOCOL_DELIMITER, path))
    return path


def validate_on_forbidden_chars(**kwargs: Any) -> None:
    """Validate that string values do not include white-spaces or ;"""
    for key, value in kwargs.items():
        if " " in value or ";" in value:
            raise DatasetError(
                f"Neither white-space nor semicolon are allowed in '{key}'."
            )


def is_parameter(dataset_name: str) -> bool:
    """Check if dataset is a parameter."""
    return dataset_name.startswith("params:") or dataset_name == "parameters"


_C = TypeVar("_C")
_DS = TypeVar("_DS")


@runtime_checkable
class CatalogProtocol(Protocol[_C, _DS]):
    _datasets: dict[str, _DS]

    def __repr__(self) -> str:
        """Returns the canonical string representation of the object."""
        ...

    def __contains__(self, ds_name: str) -> bool:
        """Check if a dataset is in the catalog."""
        ...

    def keys(self) -> List[str]:  # noqa: UP006
        """List all dataset names registered in the catalog."""
        ...

    def values(self) -> List[_DS]:  # noqa: UP006
        """List all datasets registered in the catalog."""
        ...

    def items(self) -> List[tuple[str, _DS]]:  # noqa: UP006
        """List all dataset names and datasets registered in the catalog."""
        ...

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator for the object."""
        ...

    def __getitem__(self, ds_name: str) -> _DS:
        """Get a dataset by name from an internal collection of datasets."""
        ...

    def __setitem__(self, key: str, value: Any) -> None:
        """Adds dataset using the given key as a dataset name and the provided data as the value."""
        ...

    @classmethod
    def from_config(cls, catalog: dict[str, dict[str, Any]] | None) -> _C:
        """Create a catalog instance from configuration."""
        ...

    def get(self, key: str, fallback_to_runtime_pattern: bool = False) -> _DS | None:
        """Get a dataset by name from an internal collection of datasets."""
        ...

    def save(self, name: str, data: Any) -> None:
        """Save data to a registered dataset."""
        ...

    def load(self, name: str, version: str | None = None) -> Any:
        """Load data from a registered dataset."""
        ...

    def release(self, name: str) -> None:
        """Release any cached data associated with a dataset."""
        ...

    def confirm(self, name: str) -> None:
        """Confirm a dataset by its name."""
        ...

    def exists(self, name: str) -> bool:
        """Checks whether registered dataset exists by calling its `exists()` method."""
        ...


@runtime_checkable
class SharedMemoryCatalogProtocol(CatalogProtocol, Protocol):
    def set_manager_datasets(self, manager: SyncManager) -> None: ...

    def validate_catalog(self) -> None: ...
